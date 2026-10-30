"""
online_trainer.py
Continuously updates the PyTorch BirdTrajectoryGRU model weights in real-time
as actual flight trajectories are observed in the video stream.
"""

import os
import sys
from collections import deque
from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn

# Ensure python directory is in sys.path to reuse model architecture
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from models_trajectory import BirdTrajectoryGRU, GaussianNLLWithSmoothness


class OnlineTrajectoryTrainer:
    """
    Performs on-the-fly learning:
    Takes historical 15-frame features X and actual observed future 20-frame offsets Y,
    computes Gaussian NLL + smoothness loss, and backpropagates gradient updates.
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        learning_rate: float = 1e-4,
        device: Optional[str] = None
    ):
        if device is None:
            self.device = torch.device("cpu")
            if torch.cuda.is_available():
                try:
                    t_test = torch.zeros(1, device="cuda")
                    torch.cuda.synchronize()
                    self.device = torch.device("cuda")
                except Exception as ce:
                    print(f"[OnlineTrainer] CUDA health check failed ({ce}). Defaulting to CPU.")
                    self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        print(f"[OnlineTrainer] Initializing model on device: {self.device}")

        self.model = BirdTrajectoryGRU(input_dim=6, hidden_dim=128, num_layers=2).to(self.device)
        self.criterion = GaussianNLLWithSmoothness(lambda_smoothness=0.05)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=1e-4)

        # Learning telemetry (initialize before loading checkpoint)
        self.total_samples_learned = 0
        self.loss_history = deque(maxlen=200)
        self.ade_history = deque(maxlen=200)
        self.fde_history = deque(maxlen=200)
        self.latest_loss = 0.0
        self.latest_ade = 0.0
        self.latest_fde = 0.0
        self.loaded_checkpoint_name = "learned_bird_gru.pt"
        self.loaded_checkpoint_path = ""

        # Attempt to load checkpoint in priority order:
        # 1. Explicit checkpoint_path
        # 2. learned_bird_gru.pt (holds 329,221+ samples)
        # 3. best_gru.pt (base pretrained model)
        candidates = []
        if checkpoint_path:
            candidates.append(checkpoint_path)
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "checkpoints", "learned_bird_gru.pt")))
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "checkpoints", "learned_bird_gru.pt")))
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "checkpoints", "best_gru.pt")))
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "checkpoints", "best_gru.pt")))

        loaded = False
        for ckpt_p in candidates:
            if os.path.exists(ckpt_p):
                if self.load_checkpoint(ckpt_p):
                    loaded = True
                    break

        if not loaded:
            print("[OnlineTrainer] Initializing with fresh weights.")

    def load_checkpoint(self, path: str) -> bool:
        """
        Dynamically loads model weights from a specified checkpoint path.
        Returns True on success, False on failure.
        """
        if not os.path.exists(path):
            print(f"[OnlineTrainer] Checkpoint does not exist: {path}")
            return False
        try:
            ckpt = torch.load(path, map_location=self.device, weights_only=False)
            # Always reset stats first so the new model's values are shown (including 0 for base model)
            self.total_samples_learned = 0
            self.latest_loss = 0.0
            self.latest_ade = 0.0
            self.latest_fde = 0.0
            self.loss_history.clear()
            self.ade_history.clear()
            self.fde_history.clear()

            if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                self.model.load_state_dict(ckpt["model_state_dict"])
                if "optimizer_state_dict" in ckpt:
                    try:
                        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
                    except Exception:
                        pass
                # Restore telemetry from checkpoint (only if present; stays 0 for base_gru.pt)
                if "total_samples" in ckpt:
                    self.total_samples_learned = int(ckpt["total_samples"])
                if "latest_loss" in ckpt:
                    self.latest_loss = float(ckpt["latest_loss"])
                if "latest_ade" in ckpt:
                    self.latest_ade = float(ckpt["latest_ade"])
                if "latest_fde" in ckpt:
                    self.latest_fde = float(ckpt["latest_fde"])
            else:
                self.model.load_state_dict(ckpt)

            self.loaded_checkpoint_path = os.path.abspath(path)
            self.loaded_checkpoint_name = os.path.basename(path)
            print(f"[OnlineTrainer] Successfully loaded checkpoint from {path} (Total Samples: {self.total_samples_learned:,})")
            return True
        except Exception as e:
            print(f"[OnlineTrainer] Failed loading {path}: {e}")
            return False

    def fallback_to_cpu(self):
        """Switches model and tensors to CPU when CUDA errors occur."""
        if self.device != torch.device("cpu"):
            print("[OnlineTrainer] Switching GRU Trajectory model to CPU...")
            self.device = torch.device("cpu")
            self.model = self.model.to(self.device)

    def predict(self, x_history: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Inference: Given x_history (15, 6) or (B, 15, 6),
        returns predicted means (20, 2) and log-variances (20, 2).
        """
        self.model.eval()
        single = (x_history.ndim == 2)
        if single:
            x_arr = np.expand_dims(x_history, axis=0)
        else:
            x_arr = x_history

        try:
            with torch.no_grad():
                tx = torch.from_numpy(x_arr.astype(np.float32)).to(self.device)
                out = self.model(tx)  # (B, 20, 4)
                means = out[:, :, 0:2].cpu().numpy()
                logvars = out[:, :, 2:4].cpu().numpy()

            if single:
                return means[0], logvars[0]
            return means, logvars
        except Exception as e:
            if "cuda" in str(e).lower() or "accelerator" in str(e).lower():
                self.fallback_to_cpu()
                with torch.no_grad():
                    tx = torch.from_numpy(x_arr.astype(np.float32)).to(self.device)
                    out = self.model(tx)
                    means = out[:, :, 0:2].cpu().numpy()
                    logvars = out[:, :, 2:4].cpu().numpy()
                if single:
                    return means[0], logvars[0]
                return means, logvars
            raise e

    def train_step(self, x_samples: np.ndarray, y_actual_samples: np.ndarray) -> Dict[str, float]:
        """
        Executes an online training step on newly verified trajectory samples.
        x_samples: (B, 15, 6)
        y_actual_samples: (B, 20, 2)
        """
        if len(x_samples) == 0:
            return {}

        try:
            self.model.train()
            tx = torch.from_numpy(x_samples.astype(np.float32)).to(self.device)
            ty = torch.from_numpy(y_actual_samples.astype(np.float32)).to(self.device)

            self.optimizer.zero_grad()
            out = self.model(tx)  # (B, 20, 4)
            loss = self.criterion(out, ty)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
        except Exception as e:
            if "cuda" in str(e).lower() or "accelerator" in str(e).lower():
                self.fallback_to_cpu()
                tx = torch.from_numpy(x_samples.astype(np.float32)).to(self.device)
                ty = torch.from_numpy(y_actual_samples.astype(np.float32)).to(self.device)
                self.optimizer.zero_grad()
                out = self.model(tx)
                loss = self.criterion(out, ty)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
            else:
                raise e

        # Compute instantaneous metrics
        pred_means = out[:, :, 0:2].detach().cpu().numpy()
        actuals = y_actual_samples
        diffs = np.linalg.norm(pred_means - actuals, axis=-1)  # (B, 20)
        ade_20 = float(np.mean(diffs))
        fde_20 = float(np.mean(diffs[:, -1]))
        loss_val = float(loss.item())

        self.total_samples_learned += len(x_samples)
        self.latest_loss = loss_val
        self.latest_ade = ade_20
        self.latest_fde = fde_20

        self.loss_history.append(loss_val)
        self.ade_history.append(ade_20)
        self.fde_history.append(fde_20)

        return {
            "loss": loss_val,
            "ade_20": ade_20,
            "fde_20": fde_20,
            "samples_learned": self.total_samples_learned
        }

    def save_checkpoint(self, path: Optional[str] = None, split_name: Optional[str] = None) -> str:
        if path is None:
            if split_name:
                filename = f"learned_bird_gru_{split_name}.pt"
            else:
                filename = "learned_bird_gru.pt"
            path = os.path.abspath(os.path.join(os.path.dirname(__file__), "checkpoints", filename))
        
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        ckpt_payload = {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "total_samples": self.total_samples_learned,
            "latest_loss": self.latest_loss,
            "latest_ade": self.latest_ade,
            "latest_fde": self.latest_fde,
            "frame_split": split_name or "frame",
        }
        torch.save(ckpt_payload, path)
        self.loaded_checkpoint_path = os.path.abspath(path)
        self.loaded_checkpoint_name = os.path.basename(path)
        print(f"[OnlineTrainer] Checkpoint saved successfully to: {path} (Samples: {self.total_samples_learned:,})")

        # Also mirror to root checkpoints directory
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "checkpoints"))
            os.makedirs(root_dir, exist_ok=True)
            root_path = os.path.join(root_dir, os.path.basename(path))
            torch.save(ckpt_payload, root_path)
            # Also mirror to default learned_bird_gru.pt if this is the frame split
            if split_name == "frame":
                torch.save(ckpt_payload, os.path.join(root_dir, "learned_bird_gru.pt"))
                torch.save(ckpt_payload, os.path.abspath(os.path.join(os.path.dirname(__file__), "checkpoints", "learned_bird_gru.pt")))
        except Exception:
            pass

        return path

    def get_stats(self) -> dict:
        return {
            "loss": round(self.latest_loss, 4),
            "ade_20": round(self.latest_ade, 4),
            "fde_20": round(self.latest_fde, 4),
            "total_samples": self.total_samples_learned,
            "device": str(self.device),
            "active_model": getattr(self, "loaded_checkpoint_name", "learned_bird_gru.pt"),
            "loss_history": list(self.loss_history)[-30:],
            "ade_history": list(self.ade_history)[-30:],
        }
