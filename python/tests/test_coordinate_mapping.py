"""
test_coordinate_mapping.py
Unit tests verifying letterbox transform, FILL_CENTER view scaling,
and sensor coordinate transformations.
"""

import numpy as np
import pytest


def letterbox_box(
    box: np.ndarray, orig_w: int, orig_h: int, target_size: int = 640
) -> Tuple_like:
    """
    Transforms [cx, cy, w, h] from orig image coordinates into 640x640 letterbox coordinates.
    """
    scale = min(target_size / orig_w, target_size / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    pad_x = (target_size - new_w) / 2.0
    pad_y = (target_size - new_h) / 2.0

    cx_m = box[0] * scale + pad_x
    cy_m = box[1] * scale + pad_y
    w_m = box[2] * scale
    h_m = box[3] * scale
    return np.array([cx_m, cy_m, w_m, h_m], dtype=np.float32), (scale, pad_x, pad_y)


def unletterbox_box(
    box_m: np.ndarray, orig_w: int, orig_h: int, target_size: int = 640
) -> np.ndarray:
    """
    Inverts letterboxing to restore original frame coordinates.
    """
    scale = min(target_size / orig_w, target_size / orig_h)
    pad_x = (target_size - int(orig_w * scale)) / 2.0
    pad_y = (target_size - int(orig_h * scale)) / 2.0

    cx = (box_m[0] - pad_x) / scale
    cy = (box_m[1] - pad_y) / scale
    w = box_m[2] / scale
    h = box_m[3] / scale
    return np.array([cx, cy, w, h], dtype=np.float32)


def map_frame_to_screen_fill_center(
    point: np.ndarray, frame_w: int, frame_h: int, view_w: int, view_h: int
) -> np.ndarray:
    """
    CameraX PreviewView FILL_CENTER scale type:
    Crops the frame symmetrically to fill the view without distortion.
    """
    scale = max(view_w / float(frame_w), view_h / float(frame_h))
    scaled_w = frame_w * scale
    scaled_h = frame_h * scale

    offset_x = (scaled_w - view_w) / 2.0
    offset_y = (scaled_h - view_h) / 2.0

    screen_x = point[0] * scale - offset_x
    screen_y = point[1] * scale - offset_y
    return np.array([screen_x, screen_y], dtype=np.float32)


def test_letterbox_roundtrip():
    orig_w, orig_h = 1920, 1080
    test_box = np.array([960.0, 540.0, 120.0, 80.0], dtype=np.float32)

    lb_box, _ = letterbox_box(test_box, orig_w, orig_h, target_size=640)
    # The center (960, 540) in 16:9 should map exactly to center of 640x640 (320, 320)
    assert abs(lb_box[0] - 320.0) < 1.0
    assert abs(lb_box[1] - 320.0) < 1.0

    restored_box = unletterbox_box(lb_box, orig_w, orig_h, target_size=640)
    np.testing.assert_allclose(restored_box, test_box, atol=1e-3)


def test_screen_fill_center_mapping():
    # Frame 1920x1080 mapped onto portrait screen 1080x2400
    # In FILL_CENTER, scale = max(1080/1920, 2400/1080) = 2400/1080 = 2.222
    # The center of the camera frame must map to the center of the phone screen (540, 1200)
    frame_w, frame_h = 1920, 1080
    view_w, view_h = 1080, 2400

    frame_center = np.array([960.0, 540.0], dtype=np.float32)
    screen_pt = map_frame_to_screen_fill_center(
        frame_center, frame_w, frame_h, view_w, view_h
    )

    np.testing.assert_allclose(screen_pt, [540.0, 1200.0], atol=1e-3)
