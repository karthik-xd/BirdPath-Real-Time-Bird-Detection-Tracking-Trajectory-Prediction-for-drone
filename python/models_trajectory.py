"""
models_trajectory.py
PyTorch implementations of:
1. BirdTrajectoryGRU (Main model with mean and log-variance uncertainty)
2. BirdTrajectoryTransformer (Attention-based comparative model)
3. ConstantVelocityKalmanBaseline (Kinematic baseline)
4. ConstantAccelerationBaseline (Kinematic baseline)
5. Gaussian Negative Log Likelihood + 2nd-order Smoothness Regularization Loss
"""

import math
from typing import Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class BirdTrajectoryGRU(nn.Module):
    """
    2-layer GRU with hidden size 128 and MLP prediction head.
    Input: (B, 15, 6) -> [cx, cy, w, h, dx, dy]
    Output: (B, 20, 4) -> [mean_dx, mean_dy, logvar_dx, logvar_dy]
    """

    def __init__(
        self,
        input_dim: int = 6,
        hidden_dim: int = 128,
        num_layers: int = 2,
        future_steps: int = 20,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.future_steps = future_steps
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self.mlp = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, future_steps * 4),  # (mean_x, mean_y, logvar_x, logvar_y)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 15, 6)
        out, _ = self.gru(x)  # out: (B, 15, 128)
        last_hidden = out[:, -1, :]  # (B, 128)
        pred = self.mlp(last_hidden)  # (B, 20 * 4)
        return pred.view(-1, self.future_steps, 4)


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 50):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1)]


class BirdTrajectoryTransformer(nn.Module):
    """
    Small Transformer Encoder variant for trajectory prediction.
    """

    def __init__(
        self,
        input_dim: int = 6,
        d_model: int = 128,
        nhead: int = 4,
        num_layers: int = 2,
        future_steps: int = 20,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.future_steps = future_steps
        self.embedding = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=256,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.mlp = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, future_steps * 4),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 15, 6)
        x_emb = self.embedding(x)
        x_emb = self.pos_encoder(x_emb)
        feat = self.transformer(x_emb)  # (B, 15, 128)
        last_feat = feat[:, -1, :]  # (B, 128)
        pred = self.mlp(last_feat)
        return pred.view(-1, self.future_steps, 4)


class ConstantVelocityKalmanBaseline:
    """
    Kinematic baseline: computes average velocity over history and extrapolates linearly.
    """

    def __init__(self, future_steps: int = 20):
        self.future_steps = future_steps

    def predict(self, x: np.ndarray) -> np.ndarray:
        """
        x: (B, 15, 6) or (15, 6)
        Returns: (B, 20, 2) offsets
        """
        single = x.ndim == 2
        if single:
            x = np.expand_dims(x, 0)

        # Average velocity from last 5 frames of deltas (dx, dy at cols 4, 5)
        mean_vel = np.mean(x[:, -5:, 4:6], axis=1, keepdims=True)  # (B, 1, 2)
        step_multipliers = np.arange(1, self.future_steps + 1).reshape(1, -1, 1)  # (1, 20, 1)
        pred_offsets = mean_vel * step_multipliers  # (B, 20, 2)

        return pred_offsets[0] if single else pred_offsets


class ConstantAccelerationBaseline:
    """
    Kinematic baseline: estimates velocity and acceleration from history.
    """

    def __init__(self, future_steps: int = 20):
        self.future_steps = future_steps

    def predict(self, x: np.ndarray) -> np.ndarray:
        single = x.ndim == 2
        if single:
            x = np.expand_dims(x, 0)

        # deltas (dx, dy)
        v = x[:, -1, 4:6]  # last velocity (B, 2)
        v_prev = x[:, -5, 4:6]  # velocity 4 steps ago (B, 2)
        a = (v - v_prev) / 4.0  # estimated acceleration (B, 2)

        preds = []
        for k in range(1, self.future_steps + 1):
            offset_k = k * v + 0.5 * (k**2) * a
            preds.append(offset_k)

        out = np.stack(preds, axis=1)  # (B, 20, 2)
        return out[0] if single else out


class GaussianNLLWithSmoothness(nn.Module):
    """
    Gaussian Negative Log Likelihood + 2nd-order Smoothness Penalty:
    Loss = NLL(pred_mean, pred_logvar, target) + lambda * || d^2(pred_mean)/dt^2 ||^2
    """

    def __init__(self, lambda_smoothness: float = 0.05):
        super().__init__()
        self.lambda_smoothness = lambda_smoothness

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        pred: (B, 20, 4) -> [mean_x, mean_y, logvar_x, logvar_y]
        target: (B, 20, 2) -> [target_x, target_y]
        """
        mean = pred[:, :, 0:2]
        logvar = torch.clamp(pred[:, :, 2:4], min=-8.0, max=4.0)
        var = torch.exp(logvar)

        # Gaussian Negative Log-Likelihood: 0.5 * (log(var) + (y - mu)^2 / var)
        nll = 0.5 * (logvar + (target - mean) ** 2 / (var + 1e-7))
        loss_nll = torch.mean(torch.sum(nll, dim=(1, 2)))

        # Smoothness penalty on second differences of predicted trajectory:
        # a_k = (mean_{k+2} - mean_{k+1}) - (mean_{k+1} - mean_k)
        accel = (mean[:, 2:, :] - mean[:, 1:-1, :]) - (
            mean[:, 1:-1, :] - mean[:, :-2, :]
        )
        loss_smooth = torch.mean(torch.sum(accel**2, dim=(1, 2)))

        total_loss = loss_nll + self.lambda_smoothness * loss_smooth
        return total_loss


class HuberWithSmoothness(nn.Module):
    """
    Alternative Huber loss on position offsets + 2nd-order smoothness penalty.
    """

    def __init__(self, delta: float = 0.01, lambda_smoothness: float = 0.05):
        super().__init__()
        self.huber = nn.HuberLoss(delta=delta, reduction="mean")
        self.lambda_smoothness = lambda_smoothness

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        mean = pred[:, :, 0:2]
        loss_huber = self.huber(mean, target)

        accel = (mean[:, 2:, :] - mean[:, 1:-1, :]) - (
            mean[:, 1:-1, :] - mean[:, :-2, :]
        )
        loss_smooth = torch.mean(accel**2)

        return loss_huber + self.lambda_smoothness * loss_smooth
