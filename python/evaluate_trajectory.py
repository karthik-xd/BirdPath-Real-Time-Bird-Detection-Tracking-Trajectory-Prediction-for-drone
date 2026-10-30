"""
evaluate_trajectory.py
Evaluates and benchmarks all 4 trajectory models:
1. Constant Velocity (Kalman baseline)
2. Constant Acceleration baseline
3. BirdTrajectoryGRU (Main model)
4. BirdTrajectoryTransformer
Reports ADE & FDE at horizons 5, 10, and 20 steps, broken down across:
- Straight flight
- Turning flight
- Soaring / hovering flight
"""

import argparse
import numpy as np
import torch
from models_trajectory import (
    BirdTrajectoryGRU,
    BirdTrajectoryTransformer,
    ConstantVelocityKalmanBaseline,
    ConstantAccelerationBaseline,
)
from train_trajectory import compute_metrics


def evaluate_all(
    data_path: str = "data/bird_trajectories.npz",
    gru_ckpt: str = "checkpoints/best_gru.pt",
    transformer_ckpt: str = "checkpoints/best_transformer.pt",
):
    data = np.load(data_path)
    X_test = data["X_test"]
    Y_test = data["Y_test"]
    cat_test = data["cat_test"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load GRU
    gru_model = BirdTrajectoryGRU(input_dim=6, hidden_dim=128, num_layers=2).to(device)
    if gru_ckpt and os.path.exists(gru_ckpt):
        ckpt = torch.load(gru_ckpt, map_location=device, weights_only=False)
        gru_model.load_state_dict(ckpt["model_state_dict"])
    gru_model.eval()

    # Load Transformer
    tf_model = BirdTrajectoryTransformer(input_dim=6, d_model=128, num_layers=2).to(device)
    if transformer_ckpt and os.path.exists(transformer_ckpt):
        ckpt = torch.load(transformer_ckpt, map_location=device, weights_only=False)
        tf_model.load_state_dict(ckpt["model_state_dict"])
    tf_model.eval()

    # Baselines
    cv_baseline = ConstantVelocityKalmanBaseline(future_steps=20)
    ca_baseline = ConstantAccelerationBaseline(future_steps=20)

    # Predictions
    print(f"Evaluating {len(X_test)} test trajectory samples...")
    with torch.no_grad():
        tx = torch.from_numpy(X_test).to(device)
        gru_preds = gru_model(tx)[:, :, 0:2].cpu().numpy()
        tf_preds = tf_model(tx)[:, :, 0:2].cpu().numpy()

    cv_preds = cv_baseline.predict(X_test)
    ca_preds = ca_baseline.predict(X_test)

    models = {
        "1. Constant Velocity (Kalman)": cv_preds,
        "2. Constant Acceleration": ca_preds,
        "3. Trajectory GRU (Main)": gru_preds,
        "4. Small Transformer": tf_preds,
    }

    subsets = {
        "ALL FLIGHT TYPES": np.ones(len(cat_test), dtype=bool),
        "Straight Flight": (cat_test == "straight"),
        "Turning Flight": (cat_test == "turning"),
        "Soaring / Hovering": (cat_test == "soaring"),
    }

    header = f"{'Model':<30} | {'ADE@5':<7} | {'ADE@10':<7} | {'ADE@20':<7} | {'FDE@5':<7} | {'FDE@10':<7} | {'FDE@20':<7}"
    separator = "-" * len(header)

    print("\n" + "=" * 80)
    print("BIRD FLIGHT TRAJECTORY PREDICTION EVALUATION REPORT (ADE / FDE)")
    print("=" * 80)

    for subset_name, mask in subsets.items():
        if not np.any(mask):
            continue
        print(f"\n--- Subset: {subset_name} (N = {np.sum(mask)}) ---")
        print(header)
        print(separator)
        sub_Y = Y_test[mask]

        for model_name, preds in models.items():
            sub_preds = preds[mask]
            m = compute_metrics(sub_preds, sub_Y)
            print(
                f"{model_name:<30} | "
                f"{m['ade_5']:<7.4f} | {m['ade_10']:<7.4f} | {m['ade_20']:<7.4f} | "
                f"{m['fde_5']:<7.4f} | {m['fde_10']:<7.4f} | {m['fde_20']:<7.4f}"
            )
        print(separator)


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="data/bird_trajectories.npz")
    parser.add_argument("--gru", type=str, default="checkpoints/best_gru.pt")
    parser.add_argument("--transformer", type=str, default="checkpoints/best_transformer.pt")
    args = parser.parse_args()

    evaluate_all(args.data, args.gru, args.transformer)
