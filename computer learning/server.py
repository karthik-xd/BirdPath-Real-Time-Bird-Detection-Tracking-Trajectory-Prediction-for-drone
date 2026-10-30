"""
server.py
FastAPI Web UI backend providing independent Dual Studio Sessions:
1. Learning Studio Session:
   - Dedicated video monitor streaming (/video_feed/learning)
   - Real-time online backpropagation & weight training
   - Continuous ADE / FDE telemetry & layer switches
2. Testing Studio Session:
   - Dedicated video monitor streaming (/video_feed/testing)
   - Pure inference & evaluation mode (no weight alteration)
   - Full actual (blue) & predicted (red) flight paths
   - Detected birds list with individual visibility on/off toggles
   - Frame gap sampling & comparative trajectory profile plot
"""

import asyncio
import math
import os
import sys
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from youtube_loader import YouTubeStreamLoader
from online_trainer import OnlineTrajectoryTrainer
from tracker_engine import VideoTrackerEngine
from visualizer import LayerVisualizer

app = FastAPI(title="BirdPath Computer Learning & Testing Studio")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Computer Learning Downloads Directory (Local to studio)
DOWNLOADS_DIR = os.path.join(CURRENT_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Shared Core Assets
yt_loader = YouTubeStreamLoader(download_dir=DOWNLOADS_DIR)
trainer = OnlineTrajectoryTrainer()


# Request Schemas
class StartRequest(BaseModel):
    url: str
    quality: str = "720p"

class TestStartRequest(BaseModel):
    url: str
    quality: str = "720p"
    frame_gap: int = 1

class FrameGapRequest(BaseModel):
    gap: int

class FrameSplitRequest(BaseModel):
    split: str  # 'frame', '0.25s', '0.5s', '1s', '2s'
    gap: Optional[int] = None
    auto_switch_model: Optional[bool] = False

class PredictionHorizonRequest(BaseModel):
    horizon: int

class LayerToggleRequest(BaseModel):
    layer1: Optional[bool] = None  # L1: Video
    layer2: Optional[bool] = None  # L2: Bounding Boxes & IDs
    layer3: Optional[bool] = None  # L3: Actual Flight Path
    layer4: Optional[bool] = None  # L4: Predicted Flight Path Line
    layer5: Optional[bool] = None  # L5: 3D Cylinder Glow Tunnel
    layer6: Optional[bool] = None  # L6: 3D Cylinder Rib Rings & Milestone Badges
    layer7: Optional[bool] = None  # L7: Inset HUD Trajectory Graph

class DroneVRRequest(BaseModel):
    enabled: bool
    sbs_mode: Optional[bool] = False
    ipd_offset: Optional[int] = 14

class BirdVisibilityRequest(BaseModel):
    bird_id: Optional[int] = None
    visible_ids: Optional[list] = None

class SelectModelRequest(BaseModel):
    model_name: str

class SaveModelRequest(BaseModel):
    model_name: Optional[str] = None

BirdVisibilityRequest.model_rebuild()


# -------------------------------------------------------------
# StudioSession: Independent runner for Learning & Testing
# -------------------------------------------------------------
class StudioSession:
    def __init__(self, name: str, is_testing: bool, trainer: OnlineTrajectoryTrainer):
        self.name = name
        self.is_testing = is_testing
        self.trainer = trainer
        self.tracker_engine = VideoTrackerEngine(trainer=trainer)
        self.tracker_engine.testing_mode = is_testing
        self.visualizer = LayerVisualizer()
        self.visualizer.show_full_path = is_testing  # False for Learning Area (current sliding plot), True for Testing Studio (permanent full plot)
        self.frame_split: str = "frame"
        self.active_model_name: str = "learned_bird_gru_frame.pt"
        self.prediction_horizon: int = 20

        # Session State
        self.is_running: bool = False
        self.is_paused: bool = False
        self.is_finished: bool = False
        self.current_url: str = ""
        self.current_quality: str = "720p"
        self.video_path: Optional[str] = None
        self.video_title: str = "No video loaded"
        self.current_fps: float = 0.0
        self.processed_frames: int = 0
        self.active_birds: int = 0
        self.latest_jpeg: Optional[bytes] = None
        self.latest_birds: list = []
        self.last_frame: Optional[np.ndarray] = None
        self._loop_task: Optional[asyncio.Task] = None

    async def start(self, url: str, quality: str = "720p", frame_gap: int = 1):
        # Stop existing task if running
        self.is_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            await asyncio.sleep(0.15)

        self.current_url = url
        self.current_quality = quality
        self.is_paused = False
        self.is_finished = False
        self.last_frame = None
        self.tracker_engine.reset_tracks()
        self.visualizer.visible_bird_ids = None
        self.visualizer.frame_gap = max(1, frame_gap)

        video_path, title, w, h = yt_loader.resolve_video(url, quality=quality)
        self.video_path = video_path
        self.video_title = title
        self.is_running = True
        self.processed_frames = 0
        self.latest_jpeg = None

        self._loop_task = asyncio.create_task(self._run_loop())
        return {
            "status": "success",
            "message": f"{self.name.capitalize()} started: {title}",
            "quality": quality,
            "resolution": f"{w}x{h}",
            "mode": "TESTING (Evaluation Only)" if self.is_testing else "ONLINE LEARNING"
        }

    async def pause(self):
        self.is_paused = True
        return {"status": "paused", "session": self.name}

    async def resume(self):
        self.is_paused = False
        return {"status": "resumed", "session": self.name}

    async def stop(self):
        self.is_running = False
        self.is_paused = False
        self.is_finished = False
        self.latest_jpeg = None
        self.last_frame = None
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        return {"status": "stopped", "session": self.name}

    async def _run_loop(self):
        if not self.video_path or not os.path.exists(self.video_path):
            self.is_running = False
            return

        cap = cv2.VideoCapture(self.video_path)
        fps_counter = 0
        fps_start_time = time.time()
        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        video_fps = float(raw_fps) if (raw_fps is not None and 1.0 <= raw_fps <= 120.0) else 30.0

        try:
            while self.is_running and cap.isOpened():
                if self.is_paused:
                    await asyncio.sleep(0.1)
                    continue

                ret, frame = cap.read()
                if not ret:
                    # Single pass completed! DO NOT loop and create duplicate birds!
                    print(f"[{self.name.capitalize()}] 1-pass playback completed ({self.processed_frames} frames). Remembering all {len(self.tracker_engine.bird_meta)} birds.")
                    self.is_finished = True
                    self.is_running = False
                    break

                self.last_frame = frame.copy()

                self.processed_frames += 1
                fps_counter += 1

                # Track & Predict (+ Online learning step if not testing mode)
                rendered_birds, active_count = self.tracker_engine.process_frame(frame)
                self.active_birds = active_count
                self.latest_birds = rendered_birds

                # Sync live FPS to visualizer for tunnel time labels & inset graph
                self.visualizer.stream_fps = max(1.0, self.current_fps) if self.current_fps > 0 else video_fps

                # Visual overlay
                composite_frame = self.visualizer.render(
                    frame, rendered_birds, prediction_horizon=self.prediction_horizon
                )

                # JPEG encode
                ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret_enc:
                    self.latest_jpeg = jpeg_bytes.tobytes()

                # Rolling FPS
                elapsed = time.time() - fps_start_time
                if elapsed >= 1.0:
                    self.current_fps = fps_counter / elapsed
                    fps_counter = 0
                    fps_start_time = time.time()

                await asyncio.sleep(0.015)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[{self.name.capitalize()}] Error in frame loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cap.release()
            self.is_running = False

    async def generate_mjpeg(self):
        while True:
            frame_bytes = self.latest_jpeg
            if frame_bytes is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            await asyncio.sleep(0.033)

    def get_stats(self):
        t_stats = self.trainer.get_stats()
        # Active birds visible in current frame
        active_in_frame = [b for b in self.latest_birds if b.get("box") is not None]
        # Confirmed genuine flying birds
        confirmed_birds = list(self.tracker_engine.bird_meta.values())

        birds_summary = []
        for b in self.latest_birds[:6]:
            box = b.get("box")
            cx = round(box[0], 1) if box is not None else 0.0
            cy = round(box[1], 1) if box is not None else 0.0
            birds_summary.append({
                "id": b["track_id"],
                "cx": cx,
                "cy": cy,
                "speed": b.get("speed_px", 0.0),
                "heading": b.get("heading_deg", 0.0),
                "actual_pts_count": len(b.get("actual_points", [])),
                "pred_pts_count": len(b.get("predicted_points", [])),
                "predicted_points": b.get("predicted_points", []),
                "actual_points": b.get("actual_points", []),
            })

        if len(confirmed_birds) == 0:
            display_active = 0
            test_acc = 0.0
            test_ade = 0.0
            test_fde = 0.0
        else:
            display_active = len(active_in_frame) if (self.is_running and active_in_frame) else len(confirmed_birds)
            test_acc = round(self.tracker_engine.latest_accuracy, 1)
            test_ade = round(self.tracker_engine.latest_ade, 4)
            test_fde = round(self.tracker_engine.latest_fde, 4)

        return {
            "session": self.name,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "is_finished": getattr(self, "is_finished", False),
            "is_testing_mode": self.is_testing,
            "frame_gap": self.visualizer.frame_gap,
            "frame_split": self.frame_split,
            "active_model": getattr(self, "active_model_name", "learned_bird_gru_frame.pt"),
            "prediction_horizon": self.tracker_engine.prediction_horizon,
            "video_title": self.video_title,
            "fps": round(self.current_fps, 1),
            "frame_count": self.processed_frames,
            "active_birds": display_active,
            "total_detected": len(confirmed_birds),
            "quality": self.current_quality,
            "layer1_video": self.visualizer.show_layer1_video,
            "layer2_boxes": self.visualizer.show_layer2_boxes,
            "layer3_paths": self.visualizer.show_layer3_paths,
            "test_ade": test_ade,
            "test_fde": test_fde,
            "test_accuracy": test_acc,
            "has_flying_birds": len(confirmed_birds) > 0,
            "birds": birds_summary,
            "drone_evasion": self.get_drone_evasion_telemetry(),
            **t_stats
        }

    def get_drone_evasion_telemetry(self) -> dict:
        """
        Generates simulated collision avoidance telemetry and drone evasion dispatch data
        to escape from attacking birds based on predicted trajectory, actual coordinates,
        and moving zone keep-out tunnels.
        NOTE: Simulation display only — no physical RF broadcast is executed.
        """
        fps = max(1.0, self.current_fps) if self.current_fps > 0 else 30.0
        threats = []
        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        for b in self.latest_birds:
            box = b.get("box")
            if box is None:
                continue
            cx, cy, bw, bh = box
            spd = float(b.get("speed_px", 0.0))
            heading = float(b.get("heading_deg", 0.0))
            pred_pts = b.get("predicted_points", [])
            radii = b.get("uncertainty_radii", [])

            base_dim = max(24.0, max(bw, bh) * 0.50)
            tunnel_rad = min(130.0, max(base_dim * 0.8, base_dim * 0.35 + 15.0))
            safe_margin = tunnel_rad * 1.6

            # Compute predicted coordinates at milestone horizons (0.5s, 1s, 2s, 3s, 4s)
            milestones = {}
            for s in [0.5, 1.0, 2.0, 3.0, 4.0]:
                idx = int(round(s * fps))
                if 0 <= idx < len(pred_pts):
                    px, py = pred_pts[idx]
                elif len(pred_pts) > 0:
                    rad_h = math.radians(heading)
                    extra_f = idx - len(pred_pts)
                    px = pred_pts[-1][0] + math.cos(rad_h) * spd * extra_f
                    py = pred_pts[-1][1] + math.sin(rad_h) * spd * extra_f
                else:
                    rad_h = math.radians(heading)
                    px = cx + math.cos(rad_h) * spd * (s * fps)
                    py = cy + math.sin(rad_h) * spd * (s * fps)
                milestones[f"{s}s"] = {"x": round(float(px), 1), "y": round(float(py), 1)}

            # Threat analysis & Evasion vector calculation
            # Break orthogonally at 90° away from the bird's flight heading
            escape_angle = (heading + 90.0) % 360.0
            rad_esc = math.radians(escape_angle)
            evade_dist = safe_margin + 60.0
            evade_dx = round(math.cos(rad_esc) * evade_dist, 1)
            evade_dy = round(math.sin(rad_esc) * evade_dist, 1)
            target_drone_x = round(cx + evade_dx, 1)
            target_drone_y = round(cy + evade_dy, 1)

            # TCPA (Time to Closest Point of Approach)
            spd_px_sec = max(1.0, spd * fps)
            tcpa = round(max(0.3, min(6.0, (safe_margin * 2.0) / spd_px_sec)), 2)

            # Threat level
            if spd >= 8.0:
                threat_level = "CRITICAL_ATTACK_DIVE"
                maneuver = "MAX_POWER_CLIMB_AND_LATERAL_BREAK"
                throttle = 95
            elif spd >= 3.0:
                threat_level = "ACTIVE_PURSUIT_VECTOR"
                maneuver = "ORTHOGONAL_EVASION_BREAK"
                throttle = 85
            else:
                threat_level = "MONITORED_AIRSPACE_PROXIMITY"
                maneuver = "LATERAL_STANDOFF_ADJUSTMENT"
                throttle = 65

            # Simulated MAVLink v2.0 Packet
            sim_mavlink = {
                "protocol": "MAVLink_v2.0_UDP:14550",
                "msg_id": 147,
                "msg_name": "TRAJECTORY_REPRESENTATION_WAYPOINTS",
                "target_system": 1,
                "target_component": 1,
                "threat_bird_id": b["track_id"],
                "keepout_radius_px": round(tunnel_rad, 1),
                "safe_margin_px": round(safe_margin, 1),
                "target_evasion_point": {"x": target_drone_x, "y": target_drone_y, "z_rel_alt_m": 15.0},
                "evasion_vector": {"dx": evade_dx, "dy": evade_dy, "escape_heading_deg": round(escape_angle, 1)},
                "recommended_throttle_pct": throttle,
                "time_to_intercept_sec": tcpa,
                "dispatch_status": "SIMULATION_BROADCAST_ONLY (NO_RF_TRANSMISSION)"
            }

            threats.append({
                "bird_id": b["track_id"],
                "actual_coords": {"x": round(float(cx), 1), "y": round(float(cy), 1)},
                "speed_px_f": round(spd, 1),
                "speed_px_sec": round(spd * fps, 1),
                "heading_deg": round(heading, 1),
                "predicted_milestones": milestones,
                "tunnel_keepout": {
                    "base_radius_px": round(base_dim, 1),
                    "tube_radius_px": round(tunnel_rad, 1),
                    "airspace_clearance_px": round(safe_margin, 1)
                },
                "threat_level": threat_level,
                "time_to_intercept_sec": tcpa,
                "evasion_maneuver": maneuver,
                "evasion_heading_deg": round(escape_angle, 1),
                "evasion_target_point": {"x": target_drone_x, "y": target_drone_y},
                "evasion_vector": {"dx": evade_dx, "dy": evade_dy},
                "recommended_throttle_pct": throttle,
                "simulated_mavlink_packet": sim_mavlink
            })

        return {
            "timestamp": now_str,
            "mode": "SIMULATION_ONLY (NO PHYSICAL TRANSMIT)",
            "threats_count": len(threats),
            "threats": threats
        }

    def set_frame_split(self, split: str, auto_switch_model: bool = False):
        # Frame split options: 2 sec, 1 sec, 0.5 sec, 0.25 sec, frame split (current)
        SPLIT_MAP = {
            "frame": 1,
            "1f": 1,
            "0.25s": 8,
            "0.5s": 15,
            "1s": 30,
            "2s": 60,
        }
        clean_split = split.lower().strip()
        gap = SPLIT_MAP.get(clean_split, 1)
        self.frame_split = clean_split
        self.visualizer.frame_gap = gap
        self.visualizer.split_name = clean_split
        self.tracker_engine.frame_split_gap = gap

        if auto_switch_model:
            split_model = f"learned_bird_gru_{clean_split}.pt"
            candidate = os.path.abspath(os.path.join(CURRENT_DIR, "checkpoints", split_model))
            if os.path.exists(candidate):
                self.select_model(split_model)

        if self.last_frame is not None and self.latest_birds:
            composite = self.visualizer.render(self.last_frame, self.latest_birds,
                                               prediction_horizon=self.prediction_horizon)
            ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret_enc:
                self.latest_jpeg = jpeg_bytes.tobytes()
        return {
            "status": "success",
            "session": self.name,
            "frame_split": clean_split,
            "frame_gap": gap,
            "active_model": getattr(self, "active_model_name", "learned_bird_gru_frame.pt")
        }

    def set_prediction_horizon(self, horizon: int):
        h = max(5, min(240, horizon))
        self.prediction_horizon = h
        self.tracker_engine.prediction_horizon = h
        if self.last_frame is not None and self.latest_birds:
            composite = self.visualizer.render(self.last_frame, self.latest_birds,
                                               prediction_horizon=self.prediction_horizon)
            ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret_enc:
                self.latest_jpeg = jpeg_bytes.tobytes()
        return {"status": "success", "session": self.name, "prediction_horizon": h}

    def select_model(self, model_name: str):
        candidates = [
            os.path.abspath(os.path.join(CURRENT_DIR, "checkpoints", model_name)),
            os.path.abspath(os.path.join(CURRENT_DIR, "..", "checkpoints", model_name)),
            os.path.abspath(os.path.join(CURRENT_DIR, model_name)),
        ]
        target_path = None
        for c in candidates:
            if os.path.exists(c):
                target_path = c
                break

        if not target_path:
            return {"status": "error", "message": f"Model checkpoint '{model_name}' not found."}

        success = self.trainer.load_checkpoint(target_path)
        if success:
            self.active_model_name = os.path.basename(target_path)
            print(f"[{self.name.capitalize()}] Activated model '{self.active_model_name}' (Samples: {self.trainer.total_samples_learned:,})")
            return {
                "status": "success",
                "session": self.name,
                "model_name": self.active_model_name,
                "total_samples": self.trainer.total_samples_learned,
                "latest_loss": getattr(self.trainer, "latest_loss", 0.0),
                "latest_ade": getattr(self.trainer, "latest_ade", 0.0),
            }
        else:
            return {"status": "error", "message": f"Failed to load checkpoint '{model_name}'."}

    def reload_model(self, model_name: Optional[str] = None):
        target = model_name or getattr(self, "active_model_name", "learned_bird_gru_frame.pt")
        return self.select_model(target)

    def save_model(self, model_name: Optional[str] = None):
        if model_name:
            # Sanitize: strip path separators, ensure .pt extension
            safe_name = os.path.basename(model_name.strip())
            if not safe_name.endswith(".pt"):
                safe_name += ".pt"
            target_path = os.path.abspath(os.path.join(CURRENT_DIR, "checkpoints", safe_name))
        else:
            target_path = None
        save_path = self.trainer.save_checkpoint(
            path=target_path,
            split_name=self.frame_split
        )
        self.active_model_name = os.path.basename(save_path)
        return {
            "status": "saved",
            "session": self.name,
            "path": save_path,
            "model_name": self.active_model_name,
            "total_samples": self.trainer.total_samples_learned
        }

    def get_detected_birds(self):
        # Return only confirmed flying birds sorted by lifespan
        birds = list(self.tracker_engine.bird_meta.values())
        birds.sort(key=lambda b: b.get("total_frames", 0), reverse=True)
        all_ids = [b["id"] for b in birds]
        vis_ids = list(self.visualizer.visible_bird_ids) if self.visualizer.visible_bird_ids is not None else all_ids
        return {
            "birds": birds,
            "visible_ids": vis_ids,
            "total_detected": len(birds)
        }

    def toggle_bird_visibility(self, req: BirdVisibilityRequest):
        all_ids = set(self.tracker_engine.bird_meta.keys())
        if req.visible_ids is not None:
            self.visualizer.visible_bird_ids = set(req.visible_ids)
            self.tracker_engine.visible_bird_ids = set(req.visible_ids)
        elif req.bird_id is not None:
            if self.visualizer.visible_bird_ids is None:
                self.visualizer.visible_bird_ids = set(all_ids)
            if req.bird_id in self.visualizer.visible_bird_ids:
                self.visualizer.visible_bird_ids.remove(req.bird_id)
            else:
                self.visualizer.visible_bird_ids.add(req.bird_id)
            self.tracker_engine.visible_bird_ids = set(self.visualizer.visible_bird_ids)

        vis_ids = list(self.visualizer.visible_bird_ids) if self.visualizer.visible_bird_ids is not None else list(all_ids)

        # If playback is finished, re-render the final frame immediately with new visibility!
        if self.last_frame is not None and self.latest_birds:
            composite_frame = self.visualizer.render(self.last_frame, self.latest_birds,
                                                     prediction_horizon=self.prediction_horizon)
            ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret_enc:
                self.latest_jpeg = jpeg_bytes.tobytes()

        return {
            "status": "success",
            "visible_ids": vis_ids
        }

    def render_bird_plot(self, bird_id: int):
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy.ndimage import gaussian_filter1d
        from fastapi.responses import Response

        act_pts = self.tracker_engine.full_actual_paths.get(bird_id, [])
        pred_pts = self.tracker_engine.full_predicted_paths.get(bird_id, [])

        fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=100)
        fig.patch.set_facecolor('#0d1017')
        ax.set_facecolor('#141824')

        if len(act_pts) < 2:
            ax.text(0.5, 0.5, f"Bird #{bird_id}: Tracking flight path...", ha="center", va="center", color='#94a3b8', fontsize=12)
        else:
            y_act = [p[1] for p in act_pts]
            y_pred = [p[1] for p in pred_pts]
            min_len = min(len(y_act), len(y_pred))

            meta = self.tracker_engine.bird_meta.get(bird_id, {})
            acc_val = meta.get("accuracy", self.tracker_engine.latest_accuracy)

            if min_len > 0:
                steps = list(range(min_len))
                y_act_arr = np.array(y_act[:min_len])
                y_pred_arr = np.array(y_pred[:min_len])
                
                # Apply aerodynamic smoothing to eliminate flapping wing vibrations in the plot
                if len(y_act_arr) >= 6:
                    y_act_smooth = gaussian_filter1d(y_act_arr, sigma=2.2)
                    y_pred_smooth = gaussian_filter1d(y_pred_arr, sigma=2.2)
                else:
                    y_act_smooth = y_act_arr
                    y_pred_smooth = y_pred_arr

                mean_err_px = float(np.mean(np.abs(y_pred_smooth - y_act_smooth)))

                # Moving Zone Prediction Tunnel Envelope (shaded big tunnel on graph)
                tunnel_band = np.maximum(14.0, 10.0 + 0.12 * np.array(steps) + np.abs(y_pred_smooth - y_act_smooth) * 0.40)
                ax.fill_between(
                    steps,
                    y_pred_smooth - tunnel_band,
                    y_pred_smooth + tunnel_band,
                    color='#ef4444',
                    alpha=0.18,
                    label='Predicted Flight Tunnel (Moving Zone)'
                )

                ax.plot(steps, y_pred_smooth, color='#ef4444', linewidth=2.4, label=f'Smooth Prediction (Err: {mean_err_px:.1f}px)')
                ax.plot(steps, y_act_smooth, color='#3b82f6', linewidth=2.4, label='Aerodynamic Flight Path (Wings & Body)')

                # Time markers for 1s, 2s, 3s, 4s along the flight horizon
                fps_val = max(1.0, self.current_fps) if self.current_fps > 0 else 30.0
                ymin, ymax = float(np.min(y_act_smooth)), float(np.max(y_act_smooth))
                for s_mark in [1.0, 2.0, 3.0, 4.0]:
                    f_idx = int(round(s_mark * fps_val))
                    if f_idx < min_len:
                        ax.axvline(f_idx, color='#38bdf8', linestyle=':', alpha=0.65, linewidth=1.2)
                        ax.text(f_idx + 1, ymax - (ymax - ymin) * 0.08, f"+{int(s_mark)}s", color='#38bdf8', fontsize=8, fontweight='bold', alpha=0.90)
            else:
                y_act_arr = np.array(y_act)
                y_act_smooth = gaussian_filter1d(y_act_arr, sigma=2.2) if len(y_act_arr) >= 6 else y_act_arr
                ax.plot(range(len(y_act)), y_act_smooth, color='#3b82f6', linewidth=2.4, label='Aerodynamic Flight Path (Wings & Body)')

            ax.set_title(f"Bird #{bird_id} Smoothed Flight Trajectory (Flap-Damped)  |  Accuracy: {acc_val:.1f}%", color='white', fontsize=11, pad=10, fontweight='bold')
            ax.set_xlabel("Time Step (Frames)", color='#94a3b8', fontsize=9)
            ax.set_ylabel("Vertical Position (Pixels)", color='#94a3b8', fontsize=9)
            ax.tick_params(colors='#94a3b8', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('#283248')
            ax.grid(True, linestyle='--', alpha=0.25, color='#475569')
            ax.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='upper left')

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")


# Instantiate Dedicated Studio Sessions
learning_trainer = OnlineTrajectoryTrainer()
testing_trainer = OnlineTrajectoryTrainer()
learning_session = StudioSession("learning", is_testing=False, trainer=learning_trainer)
testing_session = StudioSession("testing", is_testing=True, trainer=testing_trainer)


# -------------------------------------------------------------
# Web Page Navigation Routes
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/test", response_class=HTMLResponse)
async def serve_test(request: Request):
    test_path = os.path.join(STATIC_DIR, "test.html")
    if os.path.exists(test_path):
        with open(test_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Test page not found</h1>", status_code=404)


@app.get("/vr", response_class=HTMLResponse)
async def serve_vr(request: Request):
    vr_path = os.path.join(STATIC_DIR, "vr.html")
    if os.path.exists(vr_path):
        with open(vr_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Drone VR page not found</h1>", status_code=404)


@app.get("/favicon.ico")
async def favicon():
    return HTMLResponse(content="", status_code=204)


# -------------------------------------------------------------
# Independent Video Feed Endpoints
# -------------------------------------------------------------
@app.get("/video_feed/learning")
async def video_feed_learning():
    """Independent video feed dedicated strictly to Learning Studio."""
    return StreamingResponse(
        learning_session.generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video_feed/testing")
async def video_feed_testing():
    """Independent video feed dedicated strictly to Testing Studio."""
    return StreamingResponse(
        testing_session.generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/video_feed")
async def video_feed_default():
    """Default fallback feed: routes to whichever session is actively running."""
    if testing_session.is_running and not learning_session.is_running:
        gen = testing_session.generate_mjpeg()
    else:
        gen = learning_session.generate_mjpeg()
    return StreamingResponse(
        gen,
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# -------------------------------------------------------------
# Learning Studio API Endpoints
# -------------------------------------------------------------
@app.post("/api/learning/start")
@app.post("/api/start_learning")
async def start_learning(req: StartRequest):
    try:
        return await learning_session.start(req.url, req.quality)
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.post("/api/learning/pause")
async def pause_learning():
    return await learning_session.pause()


@app.post("/api/learning/resume")
async def resume_learning():
    return await learning_session.resume()


@app.post("/api/learning/stop")
async def stop_learning():
    return await learning_session.stop()


@app.post("/api/learning/toggle_layers")
async def toggle_learning_layers(req: LayerToggleRequest):
    learning_session.visualizer.set_layer_visibility(
        layer1=req.layer1,
        layer2=req.layer2,
        layer3=req.layer3,
        layer4=req.layer4,
        layer5=req.layer5,
        layer6=req.layer6,
        layer7=req.layer7,
    )
    return {
        "status": "success",
        "session": "learning",
        **learning_session.visualizer.get_layer_visibility()
    }


@app.get("/api/learning/layers")
async def get_learning_layers():
    return learning_session.visualizer.get_layer_visibility()


@app.post("/api/learning/set_drone_vr")
async def set_learning_drone_vr(req: DroneVRRequest):
    learning_session.visualizer.set_drone_vr(req.enabled, req.sbs_mode, req.ipd_offset)
    return {
        "status": "success",
        "session": "learning",
        "drone_vr_enabled": learning_session.visualizer.show_drone_vr,
        "vr_sbs_mode": learning_session.visualizer.vr_sbs_mode,
        "vr_ipd_offset": learning_session.visualizer.vr_ipd_offset
    }


@app.get("/api/learning/stats")
async def get_learning_stats():
    return learning_session.get_stats()


@app.post("/api/learning/set_frame_split")
@app.post("/api/set_frame_split")
async def set_learning_frame_split(req: FrameSplitRequest):
    return learning_session.set_frame_split(req.split, auto_switch_model=bool(req.auto_switch_model))


@app.post("/api/learning/set_prediction_horizon")
@app.post("/api/set_prediction_horizon")
async def set_learning_prediction_horizon(req: PredictionHorizonRequest):
    return learning_session.set_prediction_horizon(req.horizon)


class PredictionSecRequest(BaseModel):
    seconds: float   # 0.5, 1.0, 2.0, 3.0, 4.0 etc.

@app.post("/api/learning/set_prediction_seconds")
async def set_learning_prediction_seconds(req: PredictionSecRequest):
    fps = max(1.0, learning_session.current_fps) if learning_session.current_fps > 0 else 30.0
    frames = max(5, min(240, int(round(req.seconds * fps))))
    return learning_session.set_prediction_horizon(frames)

@app.post("/api/testing/set_prediction_seconds")
async def set_testing_prediction_seconds(req: PredictionSecRequest):
    fps = max(1.0, testing_session.current_fps) if testing_session.current_fps > 0 else 30.0
    frames = max(5, min(240, int(round(req.seconds * fps))))
    return testing_session.set_prediction_horizon(frames)


@app.post("/api/learning/select_model")
async def select_learning_model(req: SelectModelRequest):
    return learning_session.select_model(req.model_name)


@app.post("/api/learning/save_model")
async def save_learning_model(req: Optional[SaveModelRequest] = None):
    model_name = req.model_name if req and req.model_name else None
    return learning_session.save_model(model_name)


# -------------------------------------------------------------
# Testing Studio API Endpoints
# -------------------------------------------------------------
@app.post("/api/testing/start")
@app.post("/api/start_testing")
async def start_testing(req: TestStartRequest):
    try:
        return await testing_session.start(req.url, req.quality, req.frame_gap)
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.post("/api/testing/pause")
async def pause_testing():
    return await testing_session.pause()


@app.post("/api/testing/resume")
async def resume_testing():
    return await testing_session.resume()


@app.post("/api/testing/stop")
async def stop_testing():
    return await testing_session.stop()


@app.post("/api/testing/toggle_layers")
async def toggle_testing_layers(req: LayerToggleRequest):
    testing_session.visualizer.set_layer_visibility(
        layer1=req.layer1,
        layer2=req.layer2,
        layer3=req.layer3,
        layer4=req.layer4,
        layer5=req.layer5,
        layer6=req.layer6,
        layer7=req.layer7,
    )
    if testing_session.last_frame is not None and testing_session.latest_birds:
        composite = testing_session.visualizer.render(testing_session.last_frame, testing_session.latest_birds,
                                                      prediction_horizon=testing_session.prediction_horizon)
        ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret_enc:
            testing_session.latest_jpeg = jpeg_bytes.tobytes()
    return {
        "status": "success",
        "session": "testing",
        **testing_session.visualizer.get_layer_visibility()
    }


@app.get("/api/testing/layers")
async def get_testing_layers():
    return testing_session.visualizer.get_layer_visibility()


@app.post("/api/testing/set_drone_vr")
async def set_testing_drone_vr(req: DroneVRRequest):
    testing_session.visualizer.set_drone_vr(req.enabled, req.sbs_mode, req.ipd_offset)
    if testing_session.last_frame is not None and testing_session.latest_birds:
        composite = testing_session.visualizer.render(
            testing_session.last_frame, testing_session.latest_birds,
            prediction_horizon=testing_session.prediction_horizon
        )
        ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret_enc:
            testing_session.latest_jpeg = jpeg_bytes.tobytes()
    return {
        "status": "success",
        "session": "testing",
        "drone_vr_enabled": testing_session.visualizer.show_drone_vr,
        "vr_sbs_mode": testing_session.visualizer.vr_sbs_mode,
        "vr_ipd_offset": testing_session.visualizer.vr_ipd_offset
    }


@app.post("/api/testing/set_frame_split")
async def set_testing_frame_split(req: FrameSplitRequest):
    return testing_session.set_frame_split(req.split, auto_switch_model=bool(req.auto_switch_model))


@app.post("/api/testing/set_prediction_horizon")
async def set_testing_prediction_horizon(req: PredictionHorizonRequest):
    return testing_session.set_prediction_horizon(req.horizon)


@app.post("/api/testing/select_model")
async def select_testing_model(req: SelectModelRequest):
    return testing_session.select_model(req.model_name)


@app.post("/api/testing/reload_model")
async def reload_testing_model(req: Optional[SelectModelRequest] = None):
    model_name = req.model_name if req and req.model_name else None
    return testing_session.reload_model(model_name)


@app.post("/api/testing/set_frame_gap")
@app.post("/api/set_frame_gap")
async def set_testing_frame_gap(req: FrameGapRequest):
    testing_session.visualizer.frame_gap = max(1, req.gap)
    if testing_session.last_frame is not None and testing_session.latest_birds:
        composite = testing_session.visualizer.render(testing_session.last_frame, testing_session.latest_birds,
                                                      prediction_horizon=testing_session.prediction_horizon)
        ret_enc, jpeg_bytes = cv2.imencode(".jpg", composite, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret_enc:
            testing_session.latest_jpeg = jpeg_bytes.tobytes()
    return {"status": "success", "frame_gap": testing_session.visualizer.frame_gap}


@app.get("/api/testing/stats")
async def get_testing_stats():
    return testing_session.get_stats()


@app.get("/api/testing/detected_birds")
@app.get("/api/detected_birds")
async def get_testing_detected_birds():
    return testing_session.get_detected_birds()


@app.post("/api/testing/toggle_bird_visibility")
@app.post("/api/toggle_bird_visibility")
async def toggle_testing_bird_visibility(req: BirdVisibilityRequest):
    return testing_session.toggle_bird_visibility(req)


@app.get("/api/testing/bird_plot_image/{bird_id}")
@app.get("/api/bird_plot_image/{bird_id}")
async def get_testing_bird_plot_image(bird_id: int):
    return testing_session.render_bird_plot(bird_id)


@app.get("/api/learning/bird_plot_image/{bird_id}")
async def get_learning_bird_plot_image(bird_id: int):
    return learning_session.render_bird_plot(bird_id)


# -------------------------------------------------------------
# Common Utilities & File System Endpoints
# -------------------------------------------------------------
@app.get("/api/local_videos")
async def list_local_videos():
    """Returns all stored videos in C:\dep learning\computer learning\downloads for instant testing."""
    videos = []
    d = DOWNLOADS_DIR
    TITLES = {
        "CJHP6dPjuGY": "Birds Take Flight (Animators Reference)",
        "C4EeH27TqFI": "Robin Flying SlowMotion",
        "fdw77vFfcbQ": "Lovely birds flying up high",
        "qDIl9KaALgg": "Birds flying on sky",
        "VxuSWrFbYAc": "Birds flying in the air"
    }
    if os.path.exists(d):
        for f in sorted(os.listdir(d)):
            if f.endswith((".mp4", ".mkv", ".webm")):
                fp = os.path.join(d, f)
                if os.path.isfile(fp):
                    sz_mb = round(os.path.getsize(fp) / (1024 * 1024), 2)
                    vid_id = f.split("_")[0]
                    readable_title = TITLES.get(vid_id, f)
                    videos.append({
                        "name": f,
                        "title": readable_title,
                        "path": fp,
                        "size_mb": sz_mb
                    })
    # Sort largest/main video first
    videos.sort(key=lambda x: x["size_mb"], reverse=True)
    return {"videos": videos, "download_folder": d}


@app.get("/api/available_models")
async def get_available_models():
    """Returns all available model checkpoints with sample counts and metadata."""
    ckpt_dirs = [
        os.path.abspath(os.path.join(CURRENT_DIR, "checkpoints")),
        os.path.abspath(os.path.join(CURRENT_DIR, "..", "checkpoints")),
    ]
    seen_files = set()
    models = []
    
    display_order = [
        ("learned_bird_gru_frame.pt", "Frame Split Model (1f native)", "frame"),
        ("learned_bird_gru_0.25s.pt", "0.25 sec Split Model (8f gap)", "0.25s"),
        ("learned_bird_gru_0.5s.pt", "0.5 sec Split Model (15f gap)", "0.5s"),
        ("learned_bird_gru_1s.pt", "1 sec Split Model (30f gap)", "1s"),
        ("learned_bird_gru_2s.pt", "2 sec Split Model (60f gap)", "2s"),
        ("learned_bird_gru.pt", "General Learned Model (Default)", "frame"),
        ("best_gru.pt", "Base Pretrained Model", "base"),
    ]
    
    found_map = {}
    for c_dir in ckpt_dirs:
        if not os.path.exists(c_dir):
            continue
        for fname in os.listdir(c_dir):
            if fname.endswith(".pt") and fname not in seen_files:
                fpath = os.path.join(c_dir, fname)
                seen_files.add(fname)
                size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
                samples = 0
                frame_split = "custom"
                try:
                    import torch
                    ckpt = torch.load(fpath, map_location="cpu", weights_only=False)
                    if isinstance(ckpt, dict):
                        samples = ckpt.get("total_samples", 0)
                        frame_split = ckpt.get("frame_split", "custom")
                except Exception:
                    pass
                found_map[fname] = {
                    "filename": fname,
                    "path": fpath,
                    "size_mb": size_mb,
                    "samples": samples,
                    "frame_split": frame_split,
                }
                
    for fname, friendly_name, split in display_order:
        if fname in found_map:
            item = found_map.pop(fname)
            models.append({
                "id": fname,
                "name": friendly_name,
                "split": split,
                "samples": item["samples"],
                "size_mb": item["size_mb"],
                "path": item["path"]
            })
            
    for fname, item in found_map.items():
        models.append({
            "id": fname,
            "name": f"Custom Checkpoint ({fname})",
            "split": item["frame_split"],
            "samples": item["samples"],
            "size_mb": item["size_mb"],
            "path": item["path"]
        })
        
    return {
        "status": "success",
        "models": models,
        "active_learning_model": getattr(learning_session, "active_model_name", "learned_bird_gru_frame.pt"),
        "active_testing_model": getattr(testing_session, "active_model_name", "learned_bird_gru_frame.pt"),
    }


@app.post("/api/open_folder")
async def open_downloads_folder():
    """Opens Windows File Explorer showing the saved videos folder."""
    if os.path.exists(DOWNLOADS_DIR) and sys.platform == "win32":
        os.startfile(DOWNLOADS_DIR)
        return {"status": "success", "folder": DOWNLOADS_DIR}
    return {"status": "error", "message": "Folder not found"}


@app.post("/api/save_model")
async def save_model():
    return learning_session.save_model()


# Legacy Global Fallback Endpoints (For backwards-compatibility)
@app.get("/api/stats")
async def get_general_stats():
    if testing_session.is_running and not learning_session.is_running:
        return testing_session.get_stats()
    return learning_session.get_stats()


@app.post("/api/pause")
async def general_pause():
    if testing_session.is_running and not learning_session.is_running:
        return await testing_session.pause()
    return await learning_session.pause()


@app.post("/api/resume")
async def general_resume():
    if testing_session.is_running and not learning_session.is_running:
        return await testing_session.resume()
    return await learning_session.resume()


@app.post("/api/stop")
async def general_stop():
    if testing_session.is_running and not learning_session.is_running:
        return await testing_session.stop()
    return await learning_session.stop()


@app.post("/api/toggle_layers")
async def general_toggle_layers(req: LayerToggleRequest):
    if testing_session.is_running and not learning_session.is_running:
        testing_session.visualizer.set_layer_visibility(req.layer1, req.layer2, req.layer3)
    else:
        learning_session.visualizer.set_layer_visibility(req.layer1, req.layer2, req.layer3)
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
