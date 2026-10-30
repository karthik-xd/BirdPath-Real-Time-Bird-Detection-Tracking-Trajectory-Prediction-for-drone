"""
test_tracker.py
Unit tests for 8-state Kalman Filter and ByteTrack two-stage association.
"""

import numpy as np
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tracker import KalmanBoxTracker, ByteTracker, TrackState, bbox_iou


def test_kalman_filter_predict_and_update():
    init_box = np.array([100.0, 100.0, 50.0, 40.0], dtype=np.float32)
    tracker = KalmanBoxTracker(bbox=init_box, score=0.9)

    # Initial state verification
    state = tracker.get_state()
    np.testing.assert_allclose(state, init_box, atol=1e-5)

    # Predict step
    pred = tracker.predict()
    assert tracker.age == 1
    assert tracker.time_since_update == 1

    # Update with observed movement: bird moved to [105, 102, 50, 40]
    new_box = np.array([105.0, 102.0, 50.0, 40.0], dtype=np.float32)
    tracker.update(new_box, score=0.92)

    assert tracker.time_since_update == 0
    assert tracker.hits == 2
    # Verify velocity estimate picked up positive motion
    vel = tracker.get_velocity()
    assert vel[0] > 0.0  # vx > 0
    assert vel[1] > 0.0  # vy > 0


def test_bytetrack_association_two_stages():
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1, match_thresh=0.3)

    # Frame 1: High confidence detection
    dets_f1 = [(100.0, 100.0, 50.0, 40.0, 0.85)]
    tracks_f1 = tracker.update(dets_f1)
    # 1 tentative track created, not yet confirmed (needs 3 hits)
    assert len(tracker.tracks) == 1
    assert tracker.tracks[0].state == TrackState.TENTATIVE

    # Frame 2: High confidence detection matches
    dets_f2 = [(104.0, 102.0, 50.0, 40.0, 0.88)]
    tracker.update(dets_f2)
    assert tracker.tracks[0].hits == 2

    # Frame 3: Low confidence detection (e.g. motion blur, score=0.35)
    # Should still match in Stage 2 ByteTrack!
    dets_f3 = [(108.0, 104.0, 50.0, 40.0, 0.35)]
    active = tracker.update(dets_f3)
    assert tracker.tracks[0].hits == 3
    assert tracker.tracks[0].state == TrackState.CONFIRMED
    assert len(active) == 1


def test_track_lifecycle_removal_after_30_misses():
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1, max_time_lost=30)

    # Bring track to confirmed state
    for i in range(3):
        tracker.update([(100.0 + i * 2, 100.0, 40.0, 30.0, 0.9)])

    assert tracker.tracks[0].state == TrackState.CONFIRMED

    # Miss detections for 30 consecutive frames
    for _ in range(30):
        active = tracker.update([])

    # Track is still kept as LOST up to frame 30
    assert len(tracker.tracks) == 1
    assert tracker.tracks[0].state == TrackState.LOST

    # Frame 31: Miss again -> track must be removed
    tracker.update([])
    assert len(tracker.tracks) == 0


def test_ring_buffer_maintains_30_positions():
    box = np.array([200.0, 200.0, 60.0, 50.0], dtype=np.float32)
    trk = KalmanBoxTracker(box, 0.9)

    for i in range(50):
        trk.predict()
        trk.update(box + float(i), 0.9)

    assert len(trk.history) == 30
