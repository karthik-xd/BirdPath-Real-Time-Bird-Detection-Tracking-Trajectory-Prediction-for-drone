"""
tracker_engine.py
Runs YOLO detection + ByteTrack + Kalman filtering on each video frame.
Maintains sliding trajectory buffers, triggers online learning steps when actual
future paths are realized, and extracts both predicted and actual flight paths.
"""

import os
import sys
from collections import deque
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

# Add python directory for ByteTracker
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from tracker import ByteTracker, TrackState
from online_trainer import OnlineTrajectoryTrainer


class VideoTrackerEngine:
    def __init__(
        self,
        trainer: OnlineTrajectoryTrainer,
        yolo_model_path: str = "yolov8n.pt",
        conf_thresh: float = 0.25,
        target_classes: Optional[List[int]] = None
    ):
        self.trainer = trainer
        self.conf_thresh = conf_thresh
        # COCO 14: bird strictly (reject airplanes, kites, cartoon clutter)
        self.target_classes = target_classes or [14]

        # Load YOLO detector
        print(f"[TrackerEngine] Loading YOLO model: {yolo_model_path}")
        self.yolo = YOLO(yolo_model_path)

        # ByteTracker instance with distance fallback & 90-frame persistence
        self.tracker = ByteTracker(high_thresh=0.30, low_thresh=0.10, match_thresh=0.20, max_time_lost=90)

        # Per-track timeline buffers: track_id -> deque of (frame_idx, cx_norm, cy_norm, w_norm, h_norm)
        self.track_timelines: Dict[int, deque] = {}
        # Track stitching map: raw trk.id -> canonical_id
        self.track_id_map: Dict[int, int] = {}
        # Completed pairs ready for online learning: list of (X_15x6, Y_20x2)
        self.training_queue: List[Tuple[np.ndarray, np.ndarray]] = []
        self.testing_mode: bool = False
        self.latest_ade: float = 0.0
        self.latest_fde: float = 0.0
        self.latest_accuracy: float = 0.0

        # Custom Prediction Horizon & Frame Split Gap
        self.prediction_horizon: int = 20
        self.frame_split_gap: int = 1

        # Wing & Body Center of Mass (CoM) Stabilizer states
        self.com_states: Dict[int, dict] = {}

        # Full un-truncated flight paths across the entire video for each bird
        self.full_actual_paths: Dict[int, List[Tuple[float, float]]] = {}
        self.full_predicted_paths: Dict[int, List[Tuple[float, float]]] = {}
        self.next_step_pred: Dict[int, Tuple[float, float]] = {}
        self.bird_meta: Dict[int, dict] = {}
        self.visible_bird_ids: Optional[set] = None
        self.frame_index: int = 0

    def reset_tracks(self):
        self.track_timelines.clear()
        self.full_actual_paths.clear()
        self.full_predicted_paths.clear()
        self.next_step_pred.clear()
        self.track_id_map.clear()
        self.bird_meta.clear()
        self.com_states.clear()
        self.training_queue.clear()
        self.visible_bird_ids = None
        self.frame_index = 0
        self.latest_ade = 0.0
        self.latest_fde = 0.0
        self.latest_accuracy = 0.0

    def process_frame(
        self, frame_bgr: np.ndarray
    ) -> Tuple[List[dict], int]:
        """
        Processes one video frame:
        1. Runs YOLO detection for birds
        2. Associates detections with ByteTracker
        3. Extracts Layer 2 boxes & Layer 3 flight paths (predicted and actual)
        4. Harvests training samples and triggers online model learning
        """
        self.frame_index += 1
        h, w = frame_bgr.shape[:2]

        # 1. YOLO Detection
        results = self.yolo.predict(
            frame_bgr,
            conf=self.conf_thresh,
            classes=self.target_classes,
            verbose=False,
            imgsz=640
        )

        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                xywh = boxes.xywh[i].cpu().numpy()
                score = float(boxes.conf[i].cpu().numpy())
                cx, cy, bw, bh = xywh
                detections.append((cx, cy, bw, bh, score))

        # 2. ByteTracker Association
        active_tracks = self.tracker.update(detections)

        # 3. Track Timeline & Trajectory Extraction
        rendered_birds = []
        active_canonical_ids = set()

        for trk in active_tracks:
            # Reject phantom dead-reckoning tracks when bird exits frame or loses detection
            if trk.time_since_update > 0:
                continue

            box = trk.get_state()  # [cx, cy, w, h] in pixels
            score = float(trk.score)
            curr_cx, curr_cy = float(box[0]), float(box[1])

            # Screen boundary check: ignore out-of-bounds phantom drifts
            if curr_cx < -10.0 or curr_cx > (w + 10.0) or curr_cy < -10.0 or curr_cy > (h + 10.0):
                continue

            # Canonical ID assignment (stitching recently lost tracks)
            if trk.id not in self.track_id_map:
                best_cid = None
                best_dist = 160.0
                for old_cid, old_meta in self.bird_meta.items():
                    if old_cid not in active_canonical_ids:
                        frames_since = self.frame_index - old_meta.get("last_frame", 0)
                        if 0 < frames_since <= 90:
                            last_pos = old_meta.get("current_pos", (0, 0))
                            dist = np.sqrt((curr_cx - last_pos[0])**2 + (curr_cy - last_pos[1])**2)
                            if dist < best_dist:
                                best_dist = dist
                                best_cid = old_cid
                if best_cid is not None:
                    self.track_id_map[trk.id] = best_cid
                else:
                    self.track_id_map[trk.id] = trk.id

            cid = self.track_id_map[trk.id]
            active_canonical_ids.add(cid)

            # Wing & Body Center of Mass (CoM) Stabilizer:
            # Treats wings and body as ONE united aerodynamic object.
            # Decouples high-frequency flapping wing expansion/contraction from the body center,
            # eliminating vibrating jitter in trajectory extraction and plotting.
            curr_w = float(box[2])
            curr_h = float(box[3])

            if cid not in self.com_states:
                self.com_states[cid] = {
                    "pos": np.array([curr_cx, curr_cy], dtype=np.float64),
                    "vel": np.array([0.0, 0.0], dtype=np.float64),
                    "smoothed_w": curr_w,
                    "smoothed_h": curr_h,
                }
                stable_cx, stable_cy = curr_cx, curr_cy
            else:
                c_state = self.com_states[cid]
                # Track wing expansion/contraction envelope
                c_state["smoothed_w"] = 0.85 * c_state["smoothed_w"] + 0.15 * curr_w
                c_state["smoothed_h"] = 0.85 * c_state["smoothed_h"] + 0.15 * curr_h

                # Inertial aerodynamic momentum tracking
                pred_pos = c_state["pos"] + c_state["vel"]
                innovation = np.array([curr_cx, curr_cy]) - pred_pos

                # Flap-damping alpha-beta filter
                # alpha=0.28, beta=0.04 absorbs flapping wingbeat vibration while tracking turns/dives
                c_state["pos"] = pred_pos + 0.28 * innovation
                c_state["vel"] = c_state["vel"] + 0.04 * innovation

                stable_cx = float(c_state["pos"][0])
                stable_cy = float(c_state["pos"][1])

            # Store in normalized timeline
            norm_cx = stable_cx / float(w)
            norm_cy = stable_cy / float(h)
            norm_w = float(box[2]) / float(w)
            norm_h = float(box[3]) / float(h)

            if cid not in self.track_timelines:
                self.track_timelines[cid] = deque(maxlen=80)
            self.track_timelines[cid].append((self.frame_index, norm_cx, norm_cy, norm_w, norm_h))

            timeline = list(self.track_timelines[cid])

            predicted_pixels = []
            uncertainty_radii = []

            # 1. Actual Flight Path Traveled
            if cid not in self.full_actual_paths:
                self.full_actual_paths[cid] = []
                self.full_predicted_paths[cid] = []

            self.full_actual_paths[cid].append((stable_cx, stable_cy))
            # Trailing sliding window for real-time live learning display
            actual_pixels = list(self.full_actual_paths[cid])[-25:]

            # 2. Synchronized Continuous Predicted Flight Path
            if cid in self.next_step_pred:
                self.full_predicted_paths[cid].append(self.next_step_pred[cid])
            else:
                self.full_predicted_paths[cid].append((stable_cx, stable_cy))

            # 3. Kinematics (Speed & Direction)
            speed_px = 0.0
            heading_deg = 0.0
            if len(timeline) >= 2:
                dx_px = (timeline[-1][1] - timeline[-2][1]) * float(w)
                dy_px = (timeline[-1][2] - timeline[-2][2]) * float(h)
                speed_px = float(np.sqrt(dx_px**2 + dy_px**2))
                heading_deg = float((np.degrees(np.arctan2(dy_px, dx_px)) + 360) % 360)

            # Flight Motion Gate Assessment
            # Real birds fly across space. Stationary objects (cartoon flowers, scenery, paws)
            # jitter in place (net_disp < 20 px, speed < 1.0 px/f) and must never be admitted.
            track_pts = self.full_actual_paths[cid]
            track_len = len(track_pts)
            net_disp = float(np.linalg.norm(np.array(track_pts[-1]) - np.array(track_pts[0]))) if track_len >= 2 else 0.0
            is_flying_bird = (net_disp >= 25.0 and track_len >= 5) or (track_len >= 10 and (net_disp >= 20.0 or speed_px >= 1.0))

            # 4. Trajectory Prediction & Ground Truth Evaluation (Strictly for flying birds)
            future_pred_pts = []
            if is_flying_bird and len(timeline) >= 2:
                # Physics Kinematics: Smoothed velocity over recent window
                pts_norm = np.array([[p[1], p[2]] for p in timeline], dtype=np.float32)
                k_win = min(5, len(pts_norm))
                v_smooth = (pts_norm[-1] - pts_norm[-k_win]) / float(max(1, k_win - 1))

                # Clamped acceleration
                if len(pts_norm) >= 6:
                    v_prev = (pts_norm[-3] - pts_norm[-6]) / 3.0
                    a_smooth = np.clip((v_smooth - v_prev) / 3.0, -0.003, 0.003)
                else:
                    a_smooth = np.zeros(2, dtype=np.float32)

                k_steps = np.arange(1, self.prediction_horizon + 1, dtype=np.float32).reshape(-1, 1)
                kin_offsets = k_steps * v_smooth + 0.5 * (k_steps ** 2) * a_smooth  # (H, 2)

                # Neural Network GRU prediction
                if len(timeline) >= 15:
                    hist_15 = np.array([[item[1], item[2], item[3], item[4]] for item in timeline[-15:]], dtype=np.float32)
                    deltas = np.zeros((15, 2), dtype=np.float32)
                    deltas[1:, 0] = hist_15[1:, 0] - hist_15[:-1, 0]
                    deltas[1:, 1] = hist_15[1:, 1] - hist_15[:-1, 1]
                    deltas[0] = deltas[1]
                    X_feat = np.hstack([hist_15, deltas])  # (15, 6)

                    pred_means, pred_logvars = self.trainer.predict(X_feat)  # (20, 2)
                    if self.prediction_horizon <= 20:
                        gru_offsets = pred_means[:self.prediction_horizon]
                        gru_logvars = pred_logvars[:self.prediction_horizon]
                    else:
                        extra_steps = self.prediction_horizon - 20
                        ext_offsets = pred_means[-1:] + (np.arange(1, extra_steps + 1).reshape(-1, 1) * v_smooth)
                        gru_offsets = np.vstack([pred_means, ext_offsets])
                        gru_logvars = np.vstack([pred_logvars, np.full((extra_steps, 2), pred_logvars[-1, 0])])

                    # Blend 85% Kinematics + 15% GRU non-linear residual
                    blended_offsets = 0.85 * kin_offsets + 0.15 * gru_offsets
                else:
                    blended_offsets = kin_offsets
                    gru_logvars = np.full((self.prediction_horizon, 2), -4.0, dtype=np.float32)

                # Prediction starts from the bird's STABLE aerodynamic center
                predicted_pixels.append((stable_cx, stable_cy))
                uncertainty_radii.append(4.0)

                for k in range(len(blended_offsets)):
                    px = stable_cx + blended_offsets[k, 0] * float(w)
                    py = stable_cy + blended_offsets[k, 1] * float(h)
                    predicted_pixels.append((float(px), float(py)))
                    future_pred_pts.append((float(px), float(py)))

                    # Uncertainty radius
                    std = np.sqrt(np.exp(np.clip(gru_logvars[k], -8.0, 4.0)))
                    rad = max(4.0, float(np.mean(std) * float(w)))
                    uncertainty_radii.append(float(rad))

                # Store 1-step prediction for the very next frame
                if len(future_pred_pts) > 0:
                    self.next_step_pred[cid] = future_pred_pts[0]

                # Ground Truth Verification / Accuracy Calculation
                eval_H = min(self.prediction_horizon, 20)
                if len(timeline) >= (15 + eval_H):
                    anchor_idx = len(timeline) - (eval_H + 1)
                    if anchor_idx >= 14:
                        train_hist = np.array([[item[1], item[2], item[3], item[4]] for item in timeline[anchor_idx - 14 : anchor_idx + 1]], dtype=np.float32)
                        train_deltas = np.zeros((15, 2), dtype=np.float32)
                        train_deltas[1:, 0] = train_hist[1:, 0] - train_hist[:-1, 0]
                        train_deltas[1:, 1] = train_hist[1:, 1] - train_hist[:-1, 1]
                        train_deltas[0] = train_deltas[1]
                        train_X = np.hstack([train_hist, train_deltas])  # (15, 6)

                        future_actual = np.array([[item[1], item[2]] for item in timeline[anchor_idx + 1 : anchor_idx + eval_H + 1]], dtype=np.float32)
                        anchor_center = train_hist[-1, 0:2]
                        train_Y_actual = future_actual - anchor_center  # (eval_H, 2)

                        # Actual flight displacement in normalized screen coords over eval horizon
                        flight_disp_norm = float(np.linalg.norm(train_Y_actual[-1]))

                        # Condition accuracy strictly on actual flight displacement (>= 0.025, ~16 px)
                        # Static objects that do not move must never produce 99% accuracy scores
                        if flight_disp_norm >= 0.025:
                            v_eval = (train_hist[-1, 0:2] - train_hist[-5, 0:2]) / 4.0
                            k_eval_steps = np.arange(1, eval_H + 1, dtype=np.float32).reshape(-1, 1)
                            kin_eval = k_eval_steps * v_eval
                            p_means, _ = self.trainer.predict(train_X)
                            p_hybrid_eval = 0.85 * kin_eval + 0.15 * p_means[:eval_H]

                            err_dists = np.linalg.norm(p_hybrid_eval - train_Y_actual, axis=-1)  # normalized (eval_H,)
                            ade_val = float(np.mean(err_dists))
                            fde_val = float(err_dists[-1])

                            self.latest_ade = ade_val
                            self.latest_fde = fde_val
                            
                            # Trajectory Accuracy: Percentage accuracy over flight horizon
                            # Strictly computed for verified flying birds with displacement >= 0.025
                            self.latest_accuracy = max(0.0, min(100.0, (1.0 - ade_val) * 100.0))

                            # In online training mode, harvest training sample
                            if not self.testing_mode:
                                self.training_queue.append((train_X, train_Y_actual))

            # Only register and render confirmed flying birds
            if is_flying_bird:
                full_pred_curve = list(self.full_predicted_paths[cid])
                if len(future_pred_pts) > 0 and not getattr(self, "testing_mode_finished", False):
                    full_pred_curve = full_pred_curve + future_pred_pts

                is_vis = (cid in self.visible_bird_ids) if self.visible_bird_ids is not None else True
                self.bird_meta[cid] = {
                    "id": cid,
                    "total_frames": len(self.full_actual_paths[cid]),
                    "current_pos": (round(stable_cx, 1), round(stable_cy, 1)),
                    "speed": round(speed_px, 1),
                    "heading": round(heading_deg, 1),
                    "is_active": True,
                    "visible": is_vis,
                    "ade": round(self.latest_ade, 4),
                    "fde": round(self.latest_fde, 4),
                    "accuracy": round(self.latest_accuracy, 1),
                    "actual_pts_count": len(self.full_actual_paths[cid]),
                    "pred_pts_count": len(full_pred_curve),
                    "last_frame": self.frame_index,
                }

                rendered_birds.append({
                    "track_id": cid,
                    "box": [stable_cx, stable_cy, float(box[2]), float(box[3])],
                    "score": score,
                    "speed_px": round(speed_px, 1),
                    "heading_deg": round(heading_deg, 1),
                    "predicted_points": predicted_pixels,
                    "uncertainty_radii": uncertainty_radii,
                    "actual_points": actual_pixels,
                    "full_actual_points": list(self.full_actual_paths[cid]),
                    "full_predicted_points": full_pred_curve,
                    "is_visible": is_vis,
                })

        # In testing mode, also retain and render full flight paths for confirmed birds detected during this pass
        if self.testing_mode:
            for b_id, meta in self.bird_meta.items():
                if b_id not in active_canonical_ids:
                    meta["is_active"] = False
                    is_vis = (b_id in self.visible_bird_ids) if self.visible_bird_ids is not None else True
                    meta["visible"] = is_vis
                    rendered_birds.append({
                        "track_id": b_id,
                        "box": None,
                        "score": 1.0,
                        "speed_px": meta.get("speed", 0.0),
                        "heading_deg": meta.get("heading", 0.0),
                        "predicted_points": [],
                        "uncertainty_radii": [],
                        "actual_points": list(self.full_actual_paths.get(b_id, []))[-25:],
                        "full_actual_points": list(self.full_actual_paths.get(b_id, [])),
                        "full_predicted_points": list(self.full_predicted_paths.get(b_id, [])),
                        "is_visible": is_vis,
                    })

        # 4. Perform Online Training Step ONLY IF NOT IN TESTING MODE
        if not self.testing_mode and len(self.training_queue) >= 4:
            batch_X = np.stack([item[0] for item in self.training_queue], axis=0)
            batch_Y = np.stack([item[1] for item in self.training_queue], axis=0)
            self.trainer.train_step(batch_X, batch_Y)
            self.training_queue.clear()

        active_flying = len([b for b in rendered_birds if b.get("box") is not None])
        return rendered_birds, active_flying
