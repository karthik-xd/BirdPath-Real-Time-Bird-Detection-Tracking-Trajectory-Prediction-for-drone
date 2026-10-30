"""
test_trajectory_preprocessing.py
Unit tests for trajectory window extraction, deltas, and normalization.
"""

import numpy as np
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dataset_builder import extract_windows_from_track


def test_trajectory_window_dimensions():
    # Synthetic track of 50 frames: [cx, cy, w, h]
    num_frames = 50
    t = np.linspace(0, 1, num_frames)
    track = np.zeros((num_frames, 4), dtype=np.float32)
    track[:, 0] = 0.5 + 0.2 * t  # cx
    track[:, 1] = 0.5 + 0.1 * t  # cy
    track[:, 2] = 0.05  # w
    track[:, 3] = 0.04  # h

    X, Y = extract_windows_from_track(track, history_len=15, future_len=20)

    # Number of possible sliding windows: 50 - 15 - 20 + 1 = 16
    assert X.shape == (16, 15, 6)
    assert Y.shape == (16, 20, 2)


def test_deltas_correctness():
    track = np.zeros((35, 4), dtype=np.float32)
    # Moving uniformly by 0.01 in cx and 0.02 in cy per frame
    track[:, 0] = np.arange(35) * 0.01
    track[:, 1] = np.arange(35) * 0.02
    track[:, 2] = 0.05
    track[:, 3] = 0.04

    X, Y = extract_windows_from_track(track, history_len=15, future_len=20)
    assert len(X) == 1

    # In X: cols 4 and 5 are dx and dy
    # Expect dx = 0.01 and dy = 0.02
    np.testing.assert_allclose(X[0, 1:, 4], 0.01, atol=1e-5)
    np.testing.assert_allclose(X[0, 1:, 5], 0.02, atol=1e-5)

    # In Y: offsets from last center:
    # future step k (0..19) should have offset (k+1)*0.01 and (k+1)*0.02
    expected_offsets_x = (np.arange(20) + 1) * 0.01
    expected_offsets_y = (np.arange(20) + 1) * 0.02
    np.testing.assert_allclose(Y[0, :, 0], expected_offsets_x, atol=1e-5)
    np.testing.assert_allclose(Y[0, :, 1], expected_offsets_y, atol=1e-5)


def test_short_track_rejection():
    short_track = np.zeros((25, 4), dtype=np.float32)
    X, Y = extract_windows_from_track(short_track, history_len=15, future_len=20)
    assert len(X) == 0
    assert len(Y) == 0
