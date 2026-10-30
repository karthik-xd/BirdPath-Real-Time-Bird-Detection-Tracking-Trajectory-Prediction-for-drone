"""
motion_hint.py
Computes frame differences between consecutive video frames to produce a motion mask.
Boosts detection confidence of small birds that overlap moving regions.
"""

from typing import List, Tuple
import cv2
import numpy as np


class MotionHintExtractor:
    """
    Downscales frames to a lightweight resolution (e.g. 320x180) to compute temporal
    differences with low compute overhead. Returns motion energy for proposed bounding boxes.
    """

    def __init__(
        self,
        diff_threshold: int = 25,
        downsample_w: int = 320,
        downsample_h: int = 180,
        boost_factor: float = 0.20,
    ):
        self.diff_threshold = diff_threshold
        self.downsample_w = downsample_w
        self.downsample_h = downsample_h
        self.boost_factor = boost_factor
        self.prev_gray: np.ndarray = None
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    def reset(self):
        self.prev_gray = None

    def process_frame(self, frame_bgr_or_rgb: np.ndarray) -> np.ndarray:
        """
        Takes current full-size frame, converts to small grayscale, computes diff mask.
        Returns binary motion mask of size (downsample_h, downsample_w).
        """
        if len(frame_bgr_or_rgb.shape) == 3:
            gray = cv2.cvtColor(frame_bgr_or_rgb, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame_bgr_or_rgb

        small_gray = cv2.resize(
            gray, (self.downsample_w, self.downsample_h), interpolation=cv2.INTER_LINEAR
        )

        if self.prev_gray is None:
            self.prev_gray = small_gray
            return np.zeros((self.downsample_h, self.downsample_w), dtype=np.uint8)

        # Frame difference
        diff = cv2.absdiff(small_gray, self.prev_gray)
        _, thresh = cv2.threshold(diff, self.diff_threshold, 255, cv2.THRESH_BINARY)
        # Morphological opening to remove isolated noise, dilation to group components
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, self.kernel)
        dilated = cv2.dilate(cleaned, self.kernel, iterations=1)

        self.prev_gray = small_gray
        return dilated

    def boost_detections(
        self,
        detections: List[Tuple[float, float, float, float, float]],
        motion_mask: np.ndarray,
        orig_w: int,
        orig_h: int,
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Detections format: list of (x1, y1, x2, y2, score) in original image coordinates.
        Returns updated detections with boosted confidence if overlapping significant motion.
        """
        if motion_mask is None or motion_mask.max() == 0:
            return detections

        scale_x = self.downsample_w / float(orig_w)
        scale_y = self.downsample_h / float(orig_h)

        updated_detections = []
        for x1, y1, x2, y2, score in detections:
            # Map box to motion mask coordinates
            mx1 = max(0, min(self.downsample_w - 1, int(x1 * scale_x)))
            my1 = max(0, min(self.downsample_h - 1, int(y1 * scale_y)))
            mx2 = max(0, min(self.downsample_w, int(x2 * scale_x) + 1))
            my2 = max(0, min(self.downsample_h, int(y2 * scale_y) + 1))

            if mx2 > mx1 and my2 > my1:
                roi = motion_mask[my1:my2, mx1:mx2]
                motion_ratio = np.count_nonzero(roi) / float(roi.size)
                if motion_ratio > 0.05:  # Over 5% pixels in box moving
                    boosted_score = min(1.0, score + self.boost_factor * motion_ratio)
                    updated_detections.append((x1, y1, x2, y2, boosted_score))
                    continue

            updated_detections.append((x1, y1, x2, y2, score))

        return updated_detections
