"""
tracker.py
Implements an 8-state Kalman Filter and ByteTrack two-stage association
for multi-bird tracking with a 30-frame ring buffer.
"""

from collections import deque
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment


class TrackState(Enum):
    TENTATIVE = 1
    CONFIRMED = 2
    LOST = 3
    REMOVED = 4


class KalmanBoxTracker:
    """
    Kalman filter tracking bounding box state:
    x = [cx, cy, w, h, vx, vy, vw, vh]^T
    """

    count = 0

    def __init__(self, bbox: np.ndarray, score: float, dt: float = 1.0):
        # bbox: [cx, cy, w, h]
        self.dt = dt
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1

        # State vector (8x1)
        self.x = np.zeros((8, 1), dtype=np.float32)
        self.x[0:4, 0] = bbox

        # State Transition Matrix F (8x8)
        self.F = np.eye(8, dtype=np.float32)
        for i in range(4):
            self.F[i, i + 4] = self.dt

        # Measurement Matrix H (4x8)
        self.H = np.zeros((4, 8), dtype=np.float32)
        for i in range(4):
            self.H[i, i] = 1.0

        # State Covariance P (8x8)
        self.P = np.eye(8, dtype=np.float32) * 10.0
        self.P[4:, 4:] *= 100.0  # high uncertainty on initial velocities

        # Process Noise Covariance Q (8x8)
        self.Q = np.eye(8, dtype=np.float32)
        # Position process noise is small, velocity noise accounts for maneuvering
        self.Q[0:4, 0:4] *= 1.0
        self.Q[4:, 4:] *= 4.0

        # Measurement Noise Covariance R (4x4)
        self.R = np.eye(4, dtype=np.float32) * 2.0

        self.score = score
        self.state = TrackState.TENTATIVE
        self.hits = 1
        self.age = 0
        self.time_since_update = 0

        # 30-frame ring buffer for trajectory history: stores [cx, cy, w, h]
        self.history = deque(maxlen=30)
        self.history.append(bbox.copy())

    def predict(self) -> np.ndarray:
        """Projects the state and covariance forward by dt."""
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        self.age += 1
        self.time_since_update += 1
        # Store predicted state in history if not updated by detection
        return self.x[0:4, 0].copy()

    def update(self, bbox: np.ndarray, score: float):
        """Updates the state with a matched detection [cx, cy, w, h]."""
        self.time_since_update = 0
        self.hits += 1
        self.score = score

        if self.state == TrackState.TENTATIVE and self.hits >= 3:
            self.state = TrackState.CONFIRMED

        z = bbox.reshape(4, 1)
        # Residual y = z - H * x
        y = z - np.dot(self.H, self.x)

        # Residual covariance S = H * P * H^T + R
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R

        # Kalman gain K = P * H^T * inv(S)
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))

        # Update state: x = x + K * y
        self.x = self.x + np.dot(K, y)

        # Update covariance: P = (I - K * H) * P
        I = np.eye(8, dtype=np.float32)
        self.P = np.dot(I - np.dot(K, self.H), self.P)

        # Update ring buffer with refined estimate
        self.history.append(self.x[0:4, 0].copy())

    def get_state(self) -> np.ndarray:
        """Returns [cx, cy, w, h]."""
        return self.x[0:4, 0].copy()

    def get_velocity(self) -> np.ndarray:
        """Returns [vx, vy, vw, vh]."""
        return self.x[4:8, 0].copy()


def bbox_iou(box1: np.ndarray, box2: np.ndarray) -> float:
    """
    Computes Intersection over Union (IoU) of two boxes in [cx, cy, w, h] format.
    """
    b1_x1, b1_x2 = box1[0] - box1[2] / 2.0, box1[0] + box1[2] / 2.0
    b1_y1, b1_y2 = box1[1] - box1[3] / 2.0, box1[1] + box1[3] / 2.0
    b2_x1, b2_x2 = box2[0] - box2[2] / 2.0, box2[0] + box2[2] / 2.0
    b2_y1, b2_y2 = box2[1] - box2[3] / 2.0, box2[1] + box2[3] / 2.0

    inter_x1 = max(b1_x1, b2_x1)
    inter_y1 = max(b1_y1, b2_y1)
    inter_x2 = min(b1_x2, b2_x2)
    inter_y2 = min(b1_y2, b2_y2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area1 = box1[2] * box1[3]
    area2 = box2[2] * box2[3]
    union = area1 + area2 - inter_area
    if union <= 0.0:
        return 0.0
    return inter_area / union


class ByteTracker:
    """
    Two-stage association tracker:
    - Stage 1: High confidence detections (>= high_thresh) matched to tracks with IoU.
    - Stage 2: Low confidence detections (low_thresh .. high_thresh) matched to remaining tracks.
    - Unmatched tracks kept up to max_time_lost (30 frames).
    """

    def __init__(
        self,
        high_thresh: float = 0.5,
        low_thresh: float = 0.1,
        match_thresh: float = 0.5,
        max_time_lost: int = 30,
    ):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.max_time_lost = max_time_lost
        self.tracks: List[KalmanBoxTracker] = []

    def update(
        self, detections: List[Tuple[float, float, float, float, float]]
    ) -> List[KalmanBoxTracker]:
        """
        Detections format: list of (cx, cy, w, h, score).
        Returns list of active confirmed tracks.
        """
        # Step 1: Predict all active tracks with Kalman
        for t in self.tracks:
            t.predict()

        # Step 2: Separate detections into High and Low score groups
        high_dets = [d for d in detections if d[4] >= self.high_thresh]
        low_dets = [
            d for d in detections if self.low_thresh <= d[4] < self.high_thresh
        ]

        # Stage 1: Match High score detections to tracks
        matched_tracks_1, unmatched_tracks_1, unmatched_dets_1 = self._associate(
            self.tracks, high_dets, self.match_thresh
        )

        for track_idx, det_idx in matched_tracks_1:
            det = high_dets[det_idx]
            self.tracks[track_idx].update(np.array(det[0:4], dtype=np.float32), det[4])

        # Stage 2: Match Low score detections to remaining unmatched tracks
        remaining_tracks = [self.tracks[i] for i in unmatched_tracks_1]
        matched_tracks_2, unmatched_tracks_2, _ = self._associate(
            remaining_tracks, low_dets, self.match_thresh
        )

        for rem_track_idx, det_idx in matched_tracks_2:
            det = low_dets[det_idx]
            remaining_tracks[rem_track_idx].update(
                np.array(det[0:4], dtype=np.float32), det[4]
            )

        # Update track states for unmatched tracks
        still_unmatched = [remaining_tracks[i] for i in unmatched_tracks_2]
        for t in still_unmatched:
            if t.state == TrackState.CONFIRMED:
                t.state = TrackState.LOST
            elif t.state == TrackState.TENTATIVE:
                t.state = TrackState.REMOVED

        # Create new tentative tracks from unmatched High detections
        for det_idx in unmatched_dets_1:
            det = high_dets[det_idx]
            new_track = KalmanBoxTracker(
                np.array(det[0:4], dtype=np.float32), score=det[4]
            )
            self.tracks.append(new_track)

        # Filter out tracks that have been lost for more than max_time_lost
        active_tracks = []
        for t in self.tracks:
            if t.time_since_update > self.max_time_lost or t.state == TrackState.REMOVED:
                t.state = TrackState.REMOVED
            else:
                active_tracks.append(t)
        self.tracks = active_tracks

        # Return confirmed tracks (or lost tracks within 0.5s fade window)
        return [
            t for t in self.tracks if t.state in (TrackState.CONFIRMED, TrackState.LOST)
        ]

    def _associate(
        self,
        track_list: List[KalmanBoxTracker],
        det_list: List[Tuple[float, float, float, float, float]],
        iou_thresh: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """IoU + Distance-gated cost matrix with Hungarian matching algorithm."""
        if len(track_list) == 0 or len(det_list) == 0:
            return [], list(range(len(track_list))), list(range(len(det_list)))

        cost_matrix = np.zeros((len(track_list), len(det_list)), dtype=np.float32)
        for i, trk in enumerate(track_list):
            trk_box = trk.get_state()
            box_diag = np.sqrt(trk_box[2]**2 + trk_box[3]**2)
            gate_dist = max(100.0, box_diag * 2.5)
            for j, det in enumerate(det_list):
                det_box = np.array(det[0:4], dtype=np.float32)
                iou = bbox_iou(trk_box, det_box)
                dist = np.sqrt((trk_box[0] - det_box[0])**2 + (trk_box[1] - det_box[1])**2)
                if iou >= iou_thresh:
                    cost_matrix[i, j] = 1.0 - iou
                elif dist <= gate_dist:
                    cost_matrix[i, j] = 0.80 + (dist / gate_dist) * 0.19
                else:
                    cost_matrix[i, j] = 2.0

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matched = []
        unmatched_tracks = set(range(len(track_list)))
        unmatched_dets = set(range(len(det_list)))

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < 1.0:
                matched.append((r, c))
                unmatched_tracks.discard(r)
                unmatched_dets.discard(c)

        return matched, sorted(list(unmatched_tracks)), sorted(list(unmatched_dets))
