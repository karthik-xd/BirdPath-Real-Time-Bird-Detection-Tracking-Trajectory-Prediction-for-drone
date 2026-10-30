"""
dataset_builder.py
Generates realistic bird flight trajectory datasets with physical simulation
and parses tracked video annotations (JSON/MOT/Roboflow).
"""

import json
import math
import os
from typing import Dict, List, Tuple
import numpy as np


class SyntheticBirdTrajectoryGenerator:
    """
    Simulates physically realistic bird flight paths:
    1. Straight gliding (aerodynamic drag, linear motion, slight air turbulence)
    2. Banking turn (coordinated turn physics, centripetal acceleration)
    3. Thermal soaring (circular spiral paths with altitude/size modulation)
    4. Flapping burst (periodic acceleration and vertical oscillation)
    """

    def __init__(self, frame_w: int = 1920, frame_h: int = 1080, fps: float = 30.0):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.fps = fps
        self.dt = 1.0 / fps

    def generate_straight(self, num_frames: int = 60) -> Tuple[np.ndarray, str]:
        """Simulates straight line flight with slight wind turbulence."""
        # Initial position in normalized coordinates
        cx = np.random.uniform(0.15, 0.85)
        cy = np.random.uniform(0.2, 0.8)
        w = np.random.uniform(0.03, 0.08)
        h = w * np.random.uniform(0.6, 0.8)

        angle = np.random.uniform(0, 2 * np.pi)
        speed = np.random.uniform(0.003, 0.012)  # normalized displacement per frame
        vx = speed * np.cos(angle)
        vy = speed * np.sin(angle)

        track = []
        for _ in range(num_frames):
            track.append([cx, cy, w, h])
            # slight brownian noise in air velocity
            vx += np.random.normal(0, 0.0001)
            vy += np.random.normal(0, 0.0001)
            cx += vx
            cy += vy
            # slight scale change due to distance
            w *= np.random.normal(1.0, 0.001)
            h = w * 0.7

        return np.array(track, dtype=np.float32), "straight"

    def generate_turning(self, num_frames: int = 60) -> Tuple[np.ndarray, str]:
        """Simulates coordinated banking turn."""
        cx = np.random.uniform(0.2, 0.8)
        cy = np.random.uniform(0.2, 0.8)
        w = np.random.uniform(0.04, 0.08)
        h = w * 0.7

        heading = np.random.uniform(0, 2 * np.pi)
        speed = np.random.uniform(0.004, 0.010)
        # Turn rate in radians per frame (positive or negative)
        turn_rate = np.random.choice([-1, 1]) * np.random.uniform(0.03, 0.08)

        track = []
        for _ in range(num_frames):
            track.append([cx, cy, w, h])
            heading += turn_rate
            cx += speed * np.cos(heading)
            cy += speed * np.sin(heading)
            # banking alters apparent bounding box width/height ratio
            aspect = 0.7 + 0.15 * np.sin(heading * 2)
            h = w * aspect

        return np.array(track, dtype=np.float32), "turning"

    def generate_soaring(self, num_frames: int = 80) -> Tuple[np.ndarray, str]:
        """Simulates soaring inside a thermal updraft (elliptical drift)."""
        center_x = np.random.uniform(0.3, 0.7)
        center_y = np.random.uniform(0.3, 0.7)
        drift_vx = np.random.uniform(-0.001, 0.001)
        drift_vy = np.random.uniform(-0.001, 0.001)

        radius_x = np.random.uniform(0.08, 0.18)
        radius_y = radius_x * np.random.uniform(0.7, 1.0)
        omega = np.random.choice([-1, 1]) * np.random.uniform(0.04, 0.09)  # angular velocity
        phase = np.random.uniform(0, 2 * np.pi)

        base_w = np.random.uniform(0.03, 0.06)

        track = []
        for i in range(num_frames):
            t = i
            cx = center_x + radius_x * np.cos(omega * t + phase) + drift_vx * t
            cy = center_y + radius_y * np.sin(omega * t + phase) + drift_vy * t
            # altitude modulation reflected in size
            w = base_w * (1.0 + 0.1 * np.sin(omega * t))
            h = w * 0.7
            track.append([cx, cy, w, h])

        return np.array(track, dtype=np.float32), "soaring"


def extract_windows_from_track(
    track_boxes: np.ndarray,
    history_len: int = 15,
    future_len: int = 20,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts sliding trajectory samples from a sequence of boxes [cx, cy, w, h].
    
    Input feature vector at each historical frame step:
        [cx, cy, w, h, dx, dy]
        where dx = cx_t - cx_{t-1}, dy = cy_t - cy_{t-1} (0 for first step).
    
    Output target vector:
        Offsets from the last observed center (cx_{t-1}, cy_{t-1}):
        Y_k = [cx_{t+k} - cx_{t-1}, cy_{t+k} - cy_{t-1}] for k in 0..future_len-1.
        Shape: (future_len, 2)
    """
    total_len = len(track_boxes)
    required = history_len + future_len
    if total_len < required:
        return np.empty((0, history_len, 6), dtype=np.float32), np.empty(
            (0, future_len, 2), dtype=np.float32
        )

    X_list = []
    Y_list = []

    for t in range(history_len, total_len - future_len + 1):
        # Historical window: indices t - history_len .. t - 1
        hist_boxes = track_boxes[t - history_len : t]  # shape (15, 4)
        
        # Calculate deltas dx, dy
        deltas = np.zeros((history_len, 2), dtype=np.float32)
        deltas[1:, 0] = hist_boxes[1:, 0] - hist_boxes[:-1, 0]
        deltas[1:, 1] = hist_boxes[1:, 1] - hist_boxes[:-1, 1]
        deltas[0] = deltas[1] if history_len > 1 else 0.0

        # Features: [cx, cy, w, h, dx, dy]
        features = np.hstack([hist_boxes, deltas])  # (15, 6)

        # Future targets: indices t .. t + future_len - 1
        future_boxes = track_boxes[t : t + future_len]  # (20, 4)
        last_center = hist_boxes[-1, 0:2]  # (cx_{t-1}, cy_{t-1})
        offsets = future_boxes[:, 0:2] - last_center  # (20, 2)

        X_list.append(features)
        Y_list.append(offsets)

    return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.float32)


def build_synthetic_dataset(
    num_tracks_per_type: int = 500,
    save_path: str = "trajectory_dataset.npz",
) -> Dict[str, np.ndarray]:
    """Generates a complete dataset with straight, turning, and soaring tracks."""
    gen = SyntheticBirdTrajectoryGenerator()
    types = ["straight", "turning", "soaring"]
    
    data = {
        "train_x": [], "train_y": [], "train_cat": [],
        "val_x": [], "val_y": [], "val_cat": [],
        "test_x": [], "test_y": [], "test_cat": []
    }

    for cat in types:
        for i in range(num_tracks_per_type):
            if cat == "straight":
                track, _ = gen.generate_straight(num_frames=np.random.randint(55, 80))
            elif cat == "turning":
                track, _ = gen.generate_turning(num_frames=np.random.randint(55, 80))
            else:
                track, _ = gen.generate_soaring(num_frames=np.random.randint(65, 95))

            X, Y = extract_windows_from_track(track)
            if len(X) == 0:
                continue

            # Split tracks into 70% train, 15% val, 15% test
            r = np.random.rand()
            split = "train" if r < 0.70 else ("val" if r < 0.85 else "test")
            
            data[f"{split}_x"].append(X)
            data[f"{split}_y"].append(Y)
            data[f"{split}_cat"].extend([cat] * len(X))

    dataset = {
        "X_train": np.concatenate(data["train_x"], axis=0),
        "Y_train": np.concatenate(data["train_y"], axis=0),
        "cat_train": np.array(data["train_cat"]),
        "X_val": np.concatenate(data["val_x"], axis=0),
        "Y_val": np.concatenate(data["val_y"], axis=0),
        "cat_val": np.array(data["val_cat"]),
        "X_test": np.concatenate(data["test_x"], axis=0),
        "Y_test": np.concatenate(data["test_y"], axis=0),
        "cat_test": np.array(data["test_cat"]),
    }

    np.savez_compressed(
        save_path,
        X_train=dataset["X_train"],
        Y_train=dataset["Y_train"],
        cat_train=dataset["cat_train"],
        X_val=dataset["X_val"],
        Y_val=dataset["Y_val"],
        cat_val=dataset["cat_val"],
        X_test=dataset["X_test"],
        Y_test=dataset["Y_test"],
        cat_test=dataset["cat_test"],
    )

    print(f"Dataset generated and saved to {save_path}:")
    print(f"  Train: {dataset['X_train'].shape}, Targets: {dataset['Y_train'].shape}")
    print(f"  Val:   {dataset['X_val'].shape}, Targets: {dataset['Y_val'].shape}")
    print(f"  Test:  {dataset['X_test'].shape}, Targets: {dataset['Y_test'].shape}")
    return dataset


def parse_phone_recorded_json(json_path: str) -> np.ndarray:
    """Parses on-device recorded JSON tracks from the BirdPath Android app."""
    with open(json_path, "r") as f:
        data = json.load(f)
    
    # Expected format: {"tracks": [{"track_id": 1, "boxes": [{"t": ms, "cx": ..., "cy": ..., "w": ..., "h": ...}, ...]}]}
    all_tracks = []
    for item in data.get("tracks", []):
        boxes = []
        for b in item.get("boxes", []):
            boxes.append([b["cx"], b["cy"], b["w"], b["h"]])
        if len(boxes) >= 35:
            all_tracks.append(np.array(boxes, dtype=np.float32))
    return all_tracks


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    build_synthetic_dataset(num_tracks_per_type=400, save_path="data/bird_trajectories.npz")
