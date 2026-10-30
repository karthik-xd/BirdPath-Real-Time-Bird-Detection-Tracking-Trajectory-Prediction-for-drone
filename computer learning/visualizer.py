"""
visualizer.py
Renders the three visual layers with real-time toggle visibility controls:
- Layer 1: Live Video Playing (can be switched off to show clean telemetry canvas)
- Layer 2: Bird Bounding Boxes (track ID, confidence, color-coded per bird)
- Layer 3: Flight Paths (Predicted flight path line + Actual ground-truth flight path line +
           Moving Tunnel (1σ / 2σ corridor) + Inset time-horizon mini-graph)
Joined == Layer 1 + Layer 2 + Layer 3.
"""

from typing import List, Tuple, Optional
import cv2
import numpy as np


class LayerVisualizer:
    def __init__(self):
        # 7 Distinct Visual Layers
        self.show_layer1_video: bool = True
        self.show_layer2_boxes: bool = True
        self.show_layer3_actual_path: bool = True
        self.show_layer4_pred_path: bool = True
        self.show_layer5_tunnel: bool = True
        self.show_layer6_rings: bool = True
        self.show_layer7_inset_graph: bool = True

        # Drone VR Cockpit & Stereoscopic SBS Options
        self.show_drone_vr: bool = False
        self.vr_sbs_mode: bool = False
        self.vr_ipd_offset: int = 14

        self.frame_gap: int = 1
        self.split_name: str = "frame"
        self.visible_bird_ids = None
        self.show_full_path: bool = True

        # Live stream FPS (updated by StudioSession so tunnel labels are accurate)
        self.stream_fps: float = 30.0

        # Vibrant distinct color palette for bird IDs
        self.palette = [
            (0, 230, 118),   # Neon Green (BGR)
            (255, 229, 0),   # Cyan
            (0, 214, 255),   # Yellow
            (129, 64, 255),  # Pink
            (255, 77, 124),  # Purple
            (0, 109, 255),   # Orange
            (182, 233, 29),  # Teal
        ]

    @property
    def show_layer3_paths(self) -> bool:
        """Backwards compatibility property: True if any path layer is active."""
        return (
            self.show_layer3_actual_path or
            self.show_layer4_pred_path or
            self.show_layer5_tunnel or
            self.show_layer6_rings or
            self.show_layer7_inset_graph
        )

    @show_layer3_paths.setter
    def show_layer3_paths(self, val: bool):
        b = bool(val)
        self.show_layer3_actual_path = b
        self.show_layer4_pred_path = b
        self.show_layer5_tunnel = b
        self.show_layer6_rings = b
        self.show_layer7_inset_graph = b

    def set_layer_visibility(
        self,
        layer1: Optional[bool] = None,
        layer2: Optional[bool] = None,
        layer3: Optional[bool] = None,
        layer4: Optional[bool] = None,
        layer5: Optional[bool] = None,
        layer6: Optional[bool] = None,
        layer7: Optional[bool] = None,
    ):
        """Sets visibility for any or all of the 7 visual layers."""
        if layer1 is not None:
            self.show_layer1_video = bool(layer1)
        if layer2 is not None:
            self.show_layer2_boxes = bool(layer2)

        # Legacy 3-layer support: if only layer1, layer2, layer3 provided (and layer4..7 are None),
        # layer3 controls all trajectory layers.
        if layer4 is None and layer5 is None and layer6 is None and layer7 is None:
            if layer3 is not None:
                b = bool(layer3)
                self.show_layer3_actual_path = b
                self.show_layer4_pred_path = b
                self.show_layer5_tunnel = b
                self.show_layer6_rings = b
                self.show_layer7_inset_graph = b
        else:
            if layer3 is not None:
                self.show_layer3_actual_path = bool(layer3)
            if layer4 is not None:
                self.show_layer4_pred_path = bool(layer4)
            if layer5 is not None:
                self.show_layer5_tunnel = bool(layer5)
            if layer6 is not None:
                self.show_layer6_rings = bool(layer6)
            if layer7 is not None:
                self.show_layer7_inset_graph = bool(layer7)

    def get_layer_visibility(self) -> dict:
        return {
            "layer1": self.show_layer1_video,
            "layer2": self.show_layer2_boxes,
            "layer3": self.show_layer3_actual_path,
            "layer4": self.show_layer4_pred_path,
            "layer5": self.show_layer5_tunnel,
            "layer6": self.show_layer6_rings,
            "layer7": self.show_layer7_inset_graph,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 3D CYLINDER TUNNEL: Smooth tubular cylinder corridor expanding along flight path
    # Tubular overlapping Gaussian disks + 3D circular rib rings + 1s, 2s, 3s, 4s time gates
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_tunnel(self, canvas: np.ndarray,
                     pred_pts: list, radii: list,
                     color: tuple, fps: float,
                     prediction_horizon: int,
                     bird_box: list = None):
        if not self.show_layer5_tunnel and not self.show_layer6_rings:
            return

        n = min(len(pred_pts), len(radii))
        if n < 2:
            return

        # Base width scaled to bird dimensions
        if bird_box is not None and len(bird_box) >= 4:
            bw = float(bird_box[2])
            bh = float(bird_box[3])
            base_dim = max(24.0, max(bw, bh) * 0.50)
        else:
            base_dim = 28.0

        tunnel_color = (255, 229, 0)  # Classic Cyan Glow (BGR)

        # ── LAYER 5: 3D CYLINDER GLOW TUNNEL (Outer & Inner tubes) ───────────
        if self.show_layer5_tunnel:
            # 1. Outer Translucent Cylindrical Glow Tube (overlapping circular disks along 3D flight path)
            overlay = canvas.copy()
            for k in range(n):
                px, py = int(pred_pts[k][0]), int(pred_pts[k][1])
                r_val = float(radii[k]) if k < len(radii) else 6.0
                rad = int(max(base_dim * 0.8, r_val * 1.5 + base_dim * 0.35 + 0.30 * k))
                rad = min(rad, 130)
                cv2.circle(overlay, (px, py), rad, tunnel_color, -1, cv2.LINE_AA)

            cv2.addWeighted(overlay, 0.20, canvas, 0.80, 0, canvas)

            # 2. Inner Core Cylinder (brighter core tube)
            overlay_core = canvas.copy()
            for k in range(n):
                px, py = int(pred_pts[k][0]), int(pred_pts[k][1])
                r_val = float(radii[k]) if k < len(radii) else 6.0
                rad_core = int(max(6, (r_val * 1.5 + base_dim * 0.35 + 0.30 * k) * 0.50))
                cv2.circle(overlay_core, (px, py), rad_core, tunnel_color, -1, cv2.LINE_AA)

            cv2.addWeighted(overlay_core, 0.16, canvas, 0.84, 0, canvas)

        # ── LAYER 6: 3D CYLINDRICAL RIB RINGS & TIME MILESTONES ─────────────
        if self.show_layer6_rings:
            fps_safe = max(1.0, fps)
            rib_step = max(3, int(round(fps_safe * 0.25)))  # ring every ~0.25 sec
            for k in range(0, n, rib_step):
                px, py = int(pred_pts[k][0]), int(pred_pts[k][1])
                r_val = float(radii[k]) if k < len(radii) else 6.0
                rad = int(max(base_dim * 0.8, r_val * 1.5 + base_dim * 0.35 + 0.30 * k))
                rad = min(rad, 130)
                cv2.circle(canvas, (px, py), rad, (0, 230, 118), 1, cv2.LINE_AA)

            # 4. Milestone Time Cylinder Rings & Badges at 0.5s, 1s, 2s, 3s, 4s
            for t_sec in [0.5, 1.0, 2.0, 3.0, 4.0]:
                k_step = int(round(t_sec * fps_safe))
                if 0 < k_step < n:
                    px, py = int(pred_pts[k_step][0]), int(pred_pts[k_step][1])
                    r_val = float(radii[k_step]) if k_step < len(radii) else 6.0
                    rad = int(max(base_dim * 0.8, r_val * 1.5 + base_dim * 0.35 + 0.30 * k_step))
                    rad = min(rad, 130)

                    # Accentuated glowing cylinder ring at time milestone
                    cv2.circle(canvas, (px, py), rad, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.circle(canvas, (px, py), rad + 2, (0, 229, 255), 1, cv2.LINE_AA)

                    # Time milestone badge
                    lbl = f"+{t_sec:.1f}s" if t_sec < 1.0 else f"+{int(t_sec)}s"
                    (lw, lh), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
                    bx = px + rad + 4
                    by = py
                    cv2.rectangle(canvas, (bx - 2, by - lh - 4), (bx + lw + 4, by + 4), (12, 16, 24), -1)
                    cv2.rectangle(canvas, (bx - 2, by - lh - 4), (bx + lw + 4, by + 4), (0, 229, 255), 1)
                    cv2.putText(canvas, lbl, (bx + 1, by - 1),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 220), 1, cv2.LINE_AA)


    # ─────────────────────────────────────────────────────────────────────────
    # INSET MINI-GRAPH: X-position & Y-position vs time-ahead (seconds)
    # drawn in bottom-right of the video
    # ─────────────────────────────────────────────────────────────────────────
    def _draw_inset_graph(self, canvas: np.ndarray,
                          pred_pts: list, actual_pts: list,
                          fps: float, prediction_horizon: int,
                          color_pred: tuple, color_actual: tuple):
        h, w = canvas.shape[:2]

        GW, GH = 220, 110   # graph pixel size
        GAP = 12            # margin from edge
        gx1 = w - GW - GAP
        gy1 = h - GH - GAP
        gx2, gy2 = gx1 + GW, gy1 + GH

        # Background panel
        cv2.rectangle(canvas, (gx1 - 4, gy1 - 16), (gx2 + 4, gy2 + 4), (10, 12, 20), -1)
        cv2.rectangle(canvas, (gx1 - 4, gy1 - 16), (gx2 + 4, gy2 + 4), (40, 50, 70), 1)

        # Title
        cv2.putText(canvas, "TRAJECTORY GRAPH  (X & Y vs time)",
                    (gx1 - 2, gy1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (160, 200, 255), 1, cv2.LINE_AA)

        fps_safe = max(1.0, fps)
        n_pred = len(pred_pts)
        n_actual = len(actual_pts)

        if n_pred < 2:
            cv2.putText(canvas, "No prediction data yet",
                        (gx1 + 10, gy1 + GH // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (120, 120, 120), 1)
            return

        # X coords of prediction
        pred_x = [p[0] for p in pred_pts]
        pred_y = [p[1] for p in pred_pts]
        act_x  = [p[0] for p in actual_pts[-n_pred:]] if n_actual >= 2 else []
        act_y  = [p[1] for p in actual_pts[-n_pred:]] if n_actual >= 2 else []

        all_vals = pred_x + pred_y + act_x + act_y
        vmin = min(all_vals) if all_vals else 0
        vmax = max(all_vals) if all_vals else 1
        vrange = max(1.0, vmax - vmin)

        def to_graph(val, idx, total):
            gx = gx1 + int(idx / max(1, total - 1) * GW)
            gy = gy2 - int((val - vmin) / vrange * GH)
            return gx, gy

        # Grid lines
        for yi in range(4):
            gy_line = gy1 + int(yi * GH / 3)
            cv2.line(canvas, (gx1, gy_line), (gx2, gy_line), (30, 35, 50), 1)
        for xi in range(5):
            gx_line = gx1 + int(xi * GW / 4)
            cv2.line(canvas, (gx_line, gy1), (gx_line, gy2), (30, 35, 50), 1)

        # Actual X (solid thin)
        if len(act_x) >= 2:
            for i in range(len(act_x) - 1):
                cv2.line(canvas,
                         to_graph(act_x[i],  i,   len(act_x)),
                         to_graph(act_x[i+1], i+1, len(act_x)),
                         color_actual, 1, cv2.LINE_AA)

        # Actual Y
        if len(act_y) >= 2:
            for i in range(len(act_y) - 1):
                cv2.line(canvas,
                         to_graph(act_y[i],  i,   len(act_y)),
                         to_graph(act_y[i+1], i+1, len(act_y)),
                         (color_actual[0]//2, color_actual[1]//2, color_actual[2]//2), 1, cv2.LINE_AA)

        # Predicted X (bright)
        for i in range(n_pred - 1):
            cv2.line(canvas,
                     to_graph(pred_x[i],  i,   n_pred),
                     to_graph(pred_x[i+1], i+1, n_pred),
                     color_pred, 2, cv2.LINE_AA)

        # Predicted Y (dimmer)
        for i in range(n_pred - 1):
            cv2.line(canvas,
                     to_graph(pred_y[i],  i,   n_pred),
                     to_graph(pred_y[i+1], i+1, n_pred),
                     (color_pred[0]//2, color_pred[1]//2 + 60, color_pred[2]), 1, cv2.LINE_AA)

        # Time axis labels
        for t in [0.5, 1.0, 2.0, 3.0, 4.0]:
            frame_idx = int(t * fps_safe)
            if frame_idx >= n_pred:
                break
            tx = gx1 + int(frame_idx / max(1, n_pred - 1) * GW)
            cv2.line(canvas, (tx, gy2 - 3), (tx, gy2 + 3), (100, 120, 140), 1)
            cv2.putText(canvas, f"{t:.1f}s", (tx - 8, gy2 + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, (150, 180, 200), 1, cv2.LINE_AA)

        # Legend
        cv2.line(canvas, (gx1, gy1 + 6), (gx1 + 14, gy1 + 6), color_pred, 2, cv2.LINE_AA)
        cv2.putText(canvas, "Pred-X", (gx1 + 17, gy1 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.27, (200, 220, 255), 1, cv2.LINE_AA)
        cv2.line(canvas, (gx1 + 70, gy1 + 6), (gx1 + 84, gy1 + 6), color_actual, 1, cv2.LINE_AA)
        cv2.putText(canvas, "Act-X", (gx1 + 87, gy1 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.27, (200, 220, 255), 1, cv2.LINE_AA)

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN RENDER
    # ─────────────────────────────────────────────────────────────────────────
    def render(self, frame_bgr: np.ndarray, birds: List[dict],
               prediction_horizon: int = 20) -> np.ndarray:
        h, w = frame_bgr.shape[:2]
        fps = max(1.0, self.stream_fps)

        # --- Layer 1: Video Playing ---
        if self.show_layer1_video:
            canvas = frame_bgr.copy()
        else:
            canvas = np.full((h, w, 3), (22, 22, 28), dtype=np.uint8)
            for gy in range(0, h, 60):
                cv2.line(canvas, (0, gy), (w, gy), (35, 35, 45), 1)
            for gx in range(0, w, 60):
                cv2.line(canvas, (gx, 0), (gx, h), (35, 35, 45), 1)

        primary_bird = None   # first visible flying bird — used for inset graph

        for bird in birds:
            trk_id = bird["track_id"]

            if self.visible_bird_ids is not None and trk_id not in self.visible_bird_ids:
                continue
            if not bird.get("is_visible", True):
                continue

            color = self.palette[trk_id % len(self.palette)]

            # --- Layer 2: Boxing the Bird ---
            if self.show_layer2_boxes and bird.get("box") is not None:
                cx, cy, bw, bh = bird["box"]
                x1 = int(cx - bw / 2.0)
                y1 = int(cy - bh / 2.0)
                x2 = int(cx + bw / 2.0)
                y2 = int(cy + bh / 2.0)

                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

                score_pct = int(bird["score"] * 100)
                spd = bird.get("speed_px", 0.0)
                heading = int(bird.get("heading_deg", 0.0))
                label = f"Bird #{trk_id} ({score_pct}%) | {spd}px/f | {heading} deg"
                (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)

                cv2.rectangle(canvas, (x1, max(0, y1 - th - 6)), (x1 + tw + 8, y1), color, -1)
                cv2.putText(
                    canvas, label, (x1 + 4, max(th, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (10, 10, 10), 1, cv2.LINE_AA
                )

            # --- Layer 3, 4, 5, 6: Trajectory & Tunnel Visuals ---
            if self.show_full_path:
                actual_pts   = bird.get("full_actual_points",    bird.get("actual_points", []))
                pred_pts     = bird.get("full_predicted_points", bird.get("predicted_points", []))
                actual_color = (255, 60, 0)    # Royal Blue BGR
                pred_color   = (0, 0, 255)     # Vibrant Red BGR
            else:
                actual_pts   = bird.get("actual_points", [])[-25:]
                pred_pts     = bird.get("predicted_points", [])
                actual_color = (255, 64, 224)  # Vibrant Magenta BGR
                pred_color   = (0, 230, 118)   # Neon Green BGR

            radii = bird.get("uncertainty_radii", [])
            gap   = max(1, self.frame_gap)

            # ── LAYER 5 (Cylinder Tunnel) & LAYER 6 (Cylinder Rings) ──
            if (self.show_layer5_tunnel or self.show_layer6_rings) and len(pred_pts) >= 2 and len(radii) >= 2:
                tunnel_color = pred_color
                self._draw_tunnel(canvas, pred_pts, radii,
                                  tunnel_color, fps, prediction_horizon,
                                  bird_box=bird.get("box"))

            # ── LAYER 3: ACTUAL FLIGHT PATH LINE ────────────────────────
            if self.show_layer3_actual_path and len(actual_pts) >= 2:
                for j in range(len(actual_pts) - 1):
                    ap1 = (int(actual_pts[j][0]),     int(actual_pts[j][1]))
                    ap2 = (int(actual_pts[j+1][0]),   int(actual_pts[j+1][1]))
                    cv2.line(canvas, ap1, ap2, actual_color, 3, cv2.LINE_AA)
                for j, (apx, apy) in enumerate(actual_pts):
                    if j % gap == 0 or j == len(actual_pts) - 1:
                        cv2.circle(canvas, (int(apx), int(apy)), 3, (255, 255, 255), -1, cv2.LINE_AA)
                        cv2.circle(canvas, (int(apx), int(apy)), 4, actual_color, 1, cv2.LINE_AA)

            # ── LAYER 4: PREDICTED FLIGHT PATH LINE ─────────────────────
            if self.show_layer4_pred_path and len(pred_pts) >= 2:
                for i in range(len(pred_pts) - 1):
                    p1 = (int(pred_pts[i][0]),   int(pred_pts[i][1]))
                    p2 = (int(pred_pts[i+1][0]), int(pred_pts[i+1][1]))
                    cv2.line(canvas, p1, p2, pred_color, 3, cv2.LINE_AA)

                for i, (px, py) in enumerate(pred_pts):
                    if i % gap == 0 or i == len(pred_pts) - 1:
                        cv2.circle(canvas, (int(px), int(py)), 3, (255, 255, 255), -1, cv2.LINE_AA)
                        cv2.circle(canvas, (int(px), int(py)), 4, pred_color, 1, cv2.LINE_AA)

                        # If Layer 6 rings are off, keep time marker badges on predicted path
                        if not self.show_layer6_rings:
                            for t_mark in [0.5, 1.0, 2.0, 3.0, 4.0]:
                                frame_at = int(t_mark * fps)
                                if i == frame_at and frame_at < len(pred_pts):
                                    cv2.circle(canvas, (int(px), int(py)), 6, pred_color, 2, cv2.LINE_AA)
                                    cv2.putText(canvas, f"+{t_mark:.1f}s",
                                                (int(px) + 8, int(py) - 4),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                                                (255, 255, 180), 1, cv2.LINE_AA)

            # Track primary bird for inset graph
            if primary_bird is None and len(pred_pts) >= 2:
                primary_bird = {
                    "pred_pts":    pred_pts,
                    "actual_pts":  actual_pts,
                    "pred_color":  pred_color,
                    "actual_color": actual_color,
                }

        # ── LAYER 7: INSET MINI TIME-HORIZON GRAPH ───────────────────────────
        if self.show_layer7_inset_graph and primary_bird is not None:
            self._draw_inset_graph(
                canvas,
                primary_bird["pred_pts"],
                primary_bird["actual_pts"],
                fps,
                prediction_horizon,
                primary_bird["pred_color"],
                primary_bird["actual_color"],
            )

        # ── HUD Layer Watermark ───────────────────────────────────────────────
        layer_status = []
        if self.show_layer1_video:       layer_status.append("L1")
        if self.show_layer2_boxes:       layer_status.append("L2")
        if self.show_layer3_actual_path: layer_status.append("L3")
        if self.show_layer4_pred_path:   layer_status.append("L4")
        if self.show_layer5_tunnel:      layer_status.append("L5")
        if self.show_layer6_rings:       layer_status.append("L6")
        if self.show_layer7_inset_graph: layer_status.append("L7")
        hud_text  = "+".join(layer_status) if layer_status else "OFF"
        hud_label = f"LAYERS: {hud_text}"
        (htw, hth), _ = cv2.getTextSize(hud_label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
        cv2.rectangle(canvas, (10, 10), (10 + htw + 14, 10 + hth + 14), (15, 18, 26), -1)
        cv2.rectangle(canvas, (10, 10), (10 + htw + 14, 10 + hth + 14), (0, 230, 118), 1)
        cv2.putText(canvas, hud_label, (17, 10 + hth + 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 230, 118), 1, cv2.LINE_AA)

        # ── Comparison Legend Box ─────────────────────────────────────────────
        lw = 200 if not self.show_full_path else 175
        lh = 88  if not self.show_full_path else 60
        lx1 = max(10 + htw + 20, w - lw - 10)
        ly1 = 10
        cv2.rectangle(canvas, (lx1, ly1), (lx1 + lw, ly1 + lh), (15, 18, 26), -1)
        cv2.rectangle(canvas, (lx1, ly1), (lx1 + lw, ly1 + lh), (40, 48, 65), 1)

        if self.show_full_path:
            cv2.line(canvas, (lx1+10, ly1+18), (lx1+35, ly1+18), (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(canvas, "Prediction", (lx1+42, ly1+22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1, cv2.LINE_AA)
            cv2.line(canvas, (lx1+10, ly1+38), (lx1+35, ly1+38), (255, 60, 0), 2, cv2.LINE_AA)
            cv2.putText(canvas, "Actual", (lx1+42, ly1+42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1, cv2.LINE_AA)
        else:
            cv2.line(canvas, (lx1+10, ly1+18), (lx1+35, ly1+18), (0, 230, 118), 2, cv2.LINE_AA)
            cv2.putText(canvas, "Predicted Path",   (lx1+42, ly1+22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255,255,255), 1, cv2.LINE_AA)
            cv2.line(canvas, (lx1+10, ly1+38), (lx1+35, ly1+38), (255, 64, 224), 2, cv2.LINE_AA)
            cv2.putText(canvas, "Current Actual",   (lx1+42, ly1+42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255,255,255), 1, cv2.LINE_AA)
            # Cylinder Tunnel legend
            cv2.rectangle(canvas, (lx1+10, ly1+52), (lx1+35, ly1+60), (255, 229, 0), -1)
            cv2.putText(canvas, "Cylinder Tunnel",       (lx1+42, ly1+60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255,255,255), 1, cv2.LINE_AA)
            cv2.circle(canvas, (lx1+22, ly1+70), 5, (0, 230, 118), 1, cv2.LINE_AA)
            cv2.putText(canvas, "Cylinder Rings",        (lx1+42, ly1+74),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255,255,255), 1, cv2.LINE_AA)

        # ── DRONE VR OPTION (Selected layers only appear + FPV Cockpit / SBS Dual-Eye) ──
        if self.show_drone_vr:
            self._draw_drone_vr_hud(canvas, birds, fps)
            if self.vr_sbs_mode:
                canvas = self._make_sbs_vr(canvas, ipd=self.vr_ipd_offset)

        return canvas

    def set_drone_vr(self, enabled: bool, sbs_mode: bool = False, ipd: int = 14):
        """Toggles the Drone VR FPV Cockpit mode and stereoscopic SBS dual-lens projection."""
        self.show_drone_vr = bool(enabled)
        self.vr_sbs_mode = bool(sbs_mode)
        self.vr_ipd_offset = max(0, min(50, int(ipd)))

    def _draw_drone_vr_hud(self, canvas: np.ndarray, birds: List[dict], fps: float):
        """Draws an authentic UAV FPV Cockpit HUD with artificial horizon, crosshairs, and evasion vector."""
        h, w = canvas.shape[:2]
        cx, cy = w // 2, h // 2
        hud_color = (0, 230, 118)   # Neon Green
        warn_color = (0, 69, 255)   # Threat Alert Red-Orange

        # 1. Central Aircraft Crosshair Reticle
        cv2.circle(canvas, (cx, cy), 18, hud_color, 1, cv2.LINE_AA)
        cv2.circle(canvas, (cx, cy), 3, hud_color, -1, cv2.LINE_AA)
        cv2.line(canvas, (cx - 30, cy), (cx - 18, cy), hud_color, 2, cv2.LINE_AA)
        cv2.line(canvas, (cx + 18, cy), (cx + 30, cy), hud_color, 2, cv2.LINE_AA)
        cv2.line(canvas, (cx, cy - 30), (cx, cy - 18), hud_color, 2, cv2.LINE_AA)
        cv2.line(canvas, (cx, cy + 18), (cx, cy + 30), hud_color, 2, cv2.LINE_AA)

        # 2. Artificial Horizon Line (Waterline)
        cv2.line(canvas, (cx - 140, cy), (cx - 50, cy), (100, 255, 100), 1, cv2.LINE_AA)
        cv2.line(canvas, (cx + 50, cy), (cx + 140, cy), (100, 255, 100), 1, cv2.LINE_AA)

        # Pitch Ladder (+10 deg and -10 deg)
        for offset_y, lbl in [(-45, "+10"), (45, "-10")]:
            py_ladder = cy + offset_y
            cv2.line(canvas, (cx - 70, py_ladder), (cx - 40, py_ladder), (80, 220, 120), 1, cv2.LINE_AA)
            cv2.line(canvas, (cx + 40, py_ladder), (cx + 70, py_ladder), (80, 220, 120), 1, cv2.LINE_AA)
            cv2.putText(canvas, lbl, (cx - 95, py_ladder + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 255, 140), 1, cv2.LINE_AA)
            cv2.putText(canvas, lbl, (cx + 75, py_ladder + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 255, 140), 1, cv2.LINE_AA)

        # 3. Heading Compass Tape (Top)
        top_y = 28
        cv2.rectangle(canvas, (cx - 160, 8), (cx + 160, top_y + 16), (10, 14, 22), -1)
        cv2.rectangle(canvas, (cx - 160, 8), (cx + 160, top_y + 16), (40, 60, 80), 1)
        compass_text = "· 240 · · 270 · · 300 · · 330 · · [ N ] · · 030 · · 060 · · 090 ·"
        cv2.putText(canvas, compass_text, (cx - 145, top_y + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 230, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, "▼", (cx - 6, top_y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 230, 118), 1, cv2.LINE_AA)

        # 4. Threat Intercept Cue & Drone Escape Vector Arrow
        active_threat = None
        for b in birds:
            if b.get("speed_px", 0.0) >= 2.0 and b.get("box") is not None:
                active_threat = b
                break

        if active_threat:
            bx, by, bw, bh = active_threat["box"]
            trk_id = active_threat["track_id"]
            heading = float(active_threat.get("heading_deg", 0.0))
            spd = float(active_threat.get("speed_px", 0.0))

            # Target Lock Corners around Threat Bird
            l_len = 12
            bx1, by1 = int(bx - bw/2), int(by - bh/2)
            bx2, by2 = int(bx + bw/2), int(by + bh/2)
            cv2.line(canvas, (bx1, by1), (bx1 + l_len, by1), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx1, by1), (bx1, by1 + l_len), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx2, by1), (bx2 - l_len, by1), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx2, by1), (bx2, by1 + l_len), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx1, by2), (bx1 + l_len, by2), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx1, by2), (bx1, by2 - l_len), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx2, by2), (bx2 - l_len, by2), warn_color, 2, cv2.LINE_AA)
            cv2.line(canvas, (bx2, by2), (bx2, by2 - l_len), warn_color, 2, cv2.LINE_AA)

            lock_text = f"THREAT #{trk_id} | CLOSING: {spd:.1f}px/f | HDG: {int(heading)}°"
            cv2.putText(canvas, lock_text, (bx1, max(15, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, warn_color, 1, cv2.LINE_AA)

            # Evasion Vector Arrow (orthogonal escape heading)
            escape_angle = (heading + 90.0) % 360.0
            rad_esc = np.radians(escape_angle)
            arrow_len = 95
            ex = int(cx + np.cos(rad_esc) * arrow_len)
            ey = int(cy + np.sin(rad_esc) * arrow_len)

            cv2.arrowedLine(canvas, (cx, cy), (ex, ey), (0, 230, 118), 3, cv2.LINE_AA, tipLength=0.25)
            cv2.putText(canvas, f"EVADE -> {int(escape_angle)}° (CLIMB 90%)",
                        (ex + 8, ey), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 230, 118), 1, cv2.LINE_AA)

        # 5. Bottom VR Cockpit Status Banner
        cv2.rectangle(canvas, (10, h - 30), (w - 10, h - 8), (10, 14, 22), -1)
        cv2.rectangle(canvas, (10, h - 30), (w - 10, h - 8), (40, 60, 80), 1)
        status_bar = f"DRONE VR FPV • ALT: 45m • AIRSPEED: 38 km/h • BATT: 86% • MODE: COLLISION_EVASION • [SIMULATED]"
        cv2.putText(canvas, status_bar, (20, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 220, 255), 1, cv2.LINE_AA)

    def _make_sbs_vr(self, canvas: np.ndarray, ipd: int = 14) -> np.ndarray:
        """Transforms canvas into Stereoscopic Side-by-Side (SBS) dual-eye VR format for headsets."""
        h, w = canvas.shape[:2]
        half_w = w // 2

        # Scale down original canvas to fit half-width
        eye_view = cv2.resize(canvas, (half_w, h), interpolation=cv2.INTER_AREA)

        # Left eye and Right eye with horizontal stereoscopic disparity
        M_left = np.float32([[1, 0, -ipd], [0, 1, 0]])
        M_right = np.float32([[1, 0, ipd], [0, 1, 0]])
        left_eye = cv2.warpAffine(eye_view, M_left, (half_w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        right_eye = cv2.warpAffine(eye_view, M_right, (half_w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))

        # Circular lens vignette for authentic VR goggles barrel effect
        y, x = np.ogrid[:h, :half_w]
        center_x, center_y = half_w // 2, h // 2
        r_max = min(center_x, center_y) * 1.05
        dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        vignette = np.clip(1.0 - np.maximum(0, dist - r_max * 0.75) / (r_max * 0.35), 0.0, 1.0)
        vignette = np.repeat(vignette[:, :, np.newaxis], 3, axis=2)

        left_eye = (left_eye * vignette).astype(np.uint8)
        right_eye = (right_eye * vignette).astype(np.uint8)

        # Combine side-by-side
        sbs = np.hstack([left_eye, right_eye])

        # Center separator line
        cv2.line(sbs, (half_w, 0), (half_w, h), (15, 20, 30), 2)
        cv2.putText(sbs, "L EYE", (15, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100, 140, 180), 1, cv2.LINE_AA)
        cv2.putText(sbs, "R EYE", (half_w + 15, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100, 140, 180), 1, cv2.LINE_AA)
        return sbs
