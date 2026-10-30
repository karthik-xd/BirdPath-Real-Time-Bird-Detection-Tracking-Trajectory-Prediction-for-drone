"""
train_trajectory.py
Training pipeline for GRU and Transformer flight path models.
Evaluates ADE and FDE metrics at 5, 10, and 20 steps and saves best checkpoints.
"""

import argparse
import os
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from models_trajectory import (
    BirdTrajectoryGRU,
    BirdTrajectoryTransformer,
    GaussianNLLWithSmoothness,
)


def compute_metrics(pred_mean: np.ndarray, target: np.ndarray):
    """
    Computes ADE and FDE at horizons 5, 10, 20.
    pred_mean: (N, 20, 2)
    target: (N, 20, 2)
    """
    diffs = np.linalg.norm(pred_mean - target, axis=-1)  # (N, 20)

    ade_5 = np.mean(diffs[:, :5])
    ade_10 = np.mean(diffs[:, :10])
    ade_20 = np.mean(diffs[:, :20])

    fde_5 = np.mean(diffs[:, 4])
    fde_10 = np.mean(diffs[:, 9])
    fde_20 = np.mean(diffs[:, 19])

    return {
        "ade_5": ade_5,
        "ade_10": ade_10,
        "ade_20": ade_20,
        "fde_5": fde_5,
        "fde_10": fde_10,
        "fde_20": fde_20,
    }


def train_model(
    model_type: str = "gru",
    data_path: str = "data/bird_trajectories.npz",
    epochs: int = 40,
    batch_size: int = 64,
    lr: float = 1e-3,
    save_dir: str = "checkpoints",
):
    os.makedirs(save_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    # Load dataset
    data = np.load(data_path)
    X_train, Y_train = torch.from_numpy(data["X_train"]), torch.from_numpy(data["Y_train"])
    X_val, Y_val = torch.from_numpy(data["X_val"]), torch.from_numpy(data["Y_val"])

    train_loader = DataLoader(
        TensorDataset(X_train, Y_train), batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(X_val, Y_val), batch_size=batch_size, shuffle=False
    )

    if model_type == "gru":
        model = BirdTrajectoryGRU(input_dim=6, hidden_dim=128, num_layers=2).to(device)
    elif model_type == "transformer":
        model = BirdTrajectoryTransformer(input_dim=6, d_model=128, num_layers=2).to(device)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    criterion = GaussianNLLWithSmoothness(lambda_smoothness=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_ade20 = float("inf")
    best_path = os.path.join(save_dir, f"best_{model_type}.pt")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * len(bx)
        scheduler.step()
        train_loss /= len(X_train)

        # Validation
        model.eval()
        val_loss = 0.0
        all_preds = []
        all_targets = []
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                out = model(bx)
                loss = criterion(out, by)
                val_loss += loss.item() * len(bx)
                all_preds.append(out[:, :, 0:2].cpu().numpy())
                all_targets.append(by.cpu().numpy())

        val_loss /= len(X_val)
        all_preds = np.concatenate(all_preds, axis=0)
        all_targets = np.concatenate(all_targets, axis=0)
        metrics = compute_metrics(all_preds, all_targets)

        print(
            f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | "
            f"ADE@20: {metrics['ade_20']:.4f} | FDE@20: {metrics['fde_20']:.4f}"
        )

        if metrics["ade_20"] < best_val_ade20:
            best_val_ade20 = metrics["ade_20"]
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "metrics": metrics,
                    "model_type": model_type,
                },
                best_path,
            )
            print(f"  --> Saved new best checkpoint to {best_path}")

    print(f"\nTraining completed for {model_type}. Best Val ADE@20: {best_val_ade20:.4f}")
    return best_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bird Flight Trajectory Model Training")
    parser.add_argument("--model", type=str, default="gru", choices=["gru", "transformer"])
    parser.add_argument("--data", type=str, default="data/bird_trajectories.npz")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    train_model(
        model_type=args.model,
        data_path=args.data,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
    )
