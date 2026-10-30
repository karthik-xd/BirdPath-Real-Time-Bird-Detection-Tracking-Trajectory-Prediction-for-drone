"""
camera_compensation.py
Estimates global camera ego-motion using Lucas-Kanade optical flow on background
features with RANSAC affine estimation, and compensates track histories.
"""

from typing import List, Optional, Tuple
import cv2
import numpy as np


class CameraMotionCompensator:
    """
    Estimates affine transformation (dx, dy, rotation, scale) between consecutive
    frames caused by camera pan/tilt/zoom, excluding foreground bird detections.
    """

    def __init__(
        self,
        max_corners: int = 200,
        quality_level: float = 0.01,
        min_distance: float = 15.0,
        downscale_w: int = 640,
        downscale_h: int = 360,
    ):
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.downscale_w = downscale_w
        self.downscale_h = downscale_h
        self.prev_gray: Optional[np.ndarray] = None

    def reset(self):
        self.prev_gray = None

    def estimate_motion(
        self,
        frame_bgr_or_rgb: np.ndarray,
        exclude_boxes: List[Tuple[float, float, float, float]],
    ) -> Optional[np.ndarray]:
        """
        Calculates affine transformation matrix M (2x3) from prev_frame to cur_frame.
        exclude_boxes: list of [x1, y1, x2, y2] in normalized or original coordinates.
        """
        if len(frame_bgr_or_rgb.shape) == 3:
            gray = cv2.cvtColor(frame_bgr_or_rgb, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame_bgr_or_rgb

        h_orig, w_orig = gray.shape[:2]
        small_gray = cv2.resize(
            gray, (self.downscale_w, self.downscale_h), interpolation=cv2.INTER_LINEAR
        )

        if self.prev_gray is None:
            self.prev_gray = small_gray
            return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

        # Build mask excluding bird boxes (so bird movement doesn't contaminate camera motion)
        mask = np.ones((self.downscale_h, self.downscale_w), dtype=np.uint8) * 255
        scale_x = self.downscale_w / float(w_orig)
        scale_y = self.downscale_h / float(h_orig)

        for b in exclude_boxes:
            # If coordinates are normalized (<= 1.0), scale to pixels
            if b[2] <= 1.0 and b[3] <= 1.0:
                bx1 = int(b[0] * self.downscale_w)
                by1 = int(b[1] * self.downscale_h)
                bx2 = int(b[2] * self.downscale_w)
                by2 = int(b[3] * self.downscale_h)
            else:
                bx1 = int(b[0] * scale_x)
                by1 = int(b[1] * scale_y)
                bx2 = int(b[2] * scale_x)
                by2 = int(b[3] * scale_y)

            # Dilate exclusion zone around bird box by 10 pixels
            bx1 = max(0, bx1 - 10)
            by1 = max(0, by1 - 10)
            bx2 = min(self.downscale_w, bx2 + 10)
            by2 = min(self.downscale_h, by2 + 10)
            mask[by1:by2, bx1:bx2] = 0

        # Find reliable corner features on background
        prev_pts = cv2.goodFeaturesToTrack(
            self.prev_gray,
            maxCorners=self.max_corners,
            qualityLevel=self.quality_level,
            minDistance=self.min_distance,
            mask=mask,
        )

        affine_matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

        if prev_pts is not None and len(prev_pts) >= 8:
            curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
                self.prev_gray,
                small_gray,
                prev_pts,
                None,
                winSize=(21, 21),
                maxLevel=3,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
            )

            good_prev = prev_pts[status == 1]
            good_curr = curr_pts[status == 1]

            if len(good_prev) >= 6:
                M, inliers = cv2.estimateAffinePartial2D(
                    good_prev, good_curr, method=cv2.RANSAC, ransacReprojThreshold=3.0
                )
                if M is not None:
                    # Normalize translation vector (tx, ty) relative to full frame size
                    M[0, 2] = M[0, 2] * (w_orig / float(self.downscale_w))
                    M[1, 2] = M[1, 2] * (h_orig / float(self.downscale_h))
                    affine_matrix = M

        self.prev_gray = small_gray
        return affine_matrix

    @staticmethod
    def warp_points(points: np.ndarray, M: np.ndarray) -> np.ndarray:
        """
        Warps an array of (N, 2) points by the camera motion matrix M.
        Points can be center coordinates (cx, cy).
        """
        if points is None or len(points) == 0:
            return points
        pts = points.reshape(-1, 1, 2).astype(np.float32)
        # Invert affine transform to warp previous positions into current camera frame
        M_inv = cv2.invertAffineTransform(M)
        warped = cv2.transform(pts, M_inv)
        return warped.reshape(-1, 2)
