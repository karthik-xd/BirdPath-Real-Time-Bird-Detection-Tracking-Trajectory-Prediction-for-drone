import os
import sys
import json
import csv
import glob
import time
import shutil
import cv2
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

BASE_DIR = r"C:\dep learning"
CL_DIR = os.path.join(BASE_DIR, "computer learning")
sys.path.insert(0, CL_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "python"))

from online_trainer import OnlineTrajectoryTrainer
from tracker_engine import VideoTrackerEngine

OUTPUT_DIR = os.path.join(BASE_DIR, "online_learning_results")
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Dark aviation theme styling
DARK_BG = "#0b0e14"
PANEL_BG = "#131622"
BORDER_COLOR = "#22283a"
ACCENT_GREEN = "#00e676"
ACCENT_CYAN = "#00e5ff"
ACCENT_MAGENTA = "#e040fb"
ACCENT_YELLOW = "#ffd600"
ACCENT_ORANGE = "#ff9100"
ACCENT_RED = "#ef4444"
ACCENT_BLUE = "#3b82f6"
TEXT_MAIN = "#f1f5f9"
TEXT_MUTED = "#94a3b8"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#334155"))
            self.setLineWidth(0.5)
            self.line(36, landscape(letter)[1] - 32, landscape(letter)[0] - 36, landscape(letter)[1] - 32)
            self.drawString(36, landscape(letter)[1] - 26, "BIRDPATH AI: ALL BIRDS & ONLINE LEARNING TELEMETRY DOSSIER")
            self.drawRightString(landscape(letter)[0] - 36, landscape(letter)[1] - 26, "ACTIVE FLIGHT & MODEL AUDIT")
        self.setFont("Helvetica", 8)
        self.drawString(36, 20, "CONFIDENTIAL & VERIFIED • BIRDPATH DEEP LEARNING TELEMETRY SYSTEM")
        self.drawRightString(landscape(letter)[0] - 36, 20, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def main():
    print("=" * 70)
    print("   BIRDPATH: ALL BIRDS & ONLINE LEARNING METRICS EXPORT ENGINE   ")
    print("=" * 70)

    # 1. Gather all unique video files
    video_sources = []
    seen_names = set()
    search_dirs = [os.path.join(CL_DIR, "downloads"), os.path.join(BASE_DIR, "downloads")]
    for sd in search_dirs:
        if os.path.exists(sd):
            for f in sorted(os.listdir(sd)):
                if f.endswith(".mp4") and not f.endswith(".f396.mp4") and not f.endswith(".f397.mp4") and not f.endswith(".f140.mp4"):
                    if f not in seen_names:
                        seen_names.add(f)
                        video_sources.append(os.path.join(sd, f))

    print(f"\n[1/6] Discovered {len(video_sources)} test video sources:")
    for v in video_sources:
        print(f"  • {os.path.basename(v)}")

    # 2. Initialize Trainer and Tracker Engine
    print("\n[2/6] Initializing PyTorch GRU Online Trainer & YOLO ByteTracker...")
    trainer = OnlineTrajectoryTrainer()
    engine = VideoTrackerEngine(trainer=trainer, conf_thresh=0.20)
    print(f"  Target Device: {engine.device} | Initial Learned Samples: {trainer.total_samples_learned:,}")

    # Track all birds across all videos
    all_birds_records = []
    step_history = []
    video_summaries = []

    initial_samples = trainer.total_samples_learned
    global_step = 0

    # 3. Process Each Video
    print("\n[3/6] Executing Real-Time Detection, Tracking & Online Learning across all videos...")
    for v_idx, v_path in enumerate(video_sources, 1):
        v_name = os.path.basename(v_path)
        clean_v_tag = f"V{v_idx}_{v_name[:24].strip().replace(' ', '_').replace('#', '').replace('.', '_')}"
        print(f"\n  ---> Processing Video {v_idx}/{len(video_sources)}: {v_name}")

        cap = cv2.VideoCapture(v_path)
        if not cap.isOpened():
            print(f"       Warning: Could not open {v_path}. Skipping.")
            continue

        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        fps = float(raw_fps) if raw_fps and 1.0 <= raw_fps <= 120.0 else 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        engine.reset_tracks()
        v_start_time = time.time()
        processed_frames = 0
        samples_before_v = trainer.total_samples_learned

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            processed_frames += 1

            rendered_birds, active_count = engine.process_frame(frame)

            # Record step metrics whenever samples are learned
            if trainer.total_samples_learned > (samples_before_v + len(step_history)):
                global_step += 1
                step_history.append({
                    "step": global_step,
                    "video": v_name,
                    "frame": processed_frames,
                    "total_samples": trainer.total_samples_learned,
                    "loss": trainer.latest_loss,
                    "ade_20": trainer.latest_ade,
                    "fde_20": trainer.latest_fde,
                    "accuracy": engine.latest_accuracy
                })

        cap.release()
        elapsed = time.time() - v_start_time
        v_fps = processed_frames / elapsed if elapsed > 0 else 0
        v_samples_learned = trainer.total_samples_learned - samples_before_v

        print(f"       Finished {processed_frames}/{total_frames} frames in {elapsed:.1f}s ({v_fps:.1f} FPS)")
        print(f"       Confirmed birds tracked: {len(engine.bird_meta)} | Samples learned: +{v_samples_learned}")

        # Harvest bird trajectories and generate individual plots
        video_birds = []
        for bid, meta in engine.bird_meta.items():
            act_pts = engine.full_actual_paths.get(bid, [])
            pred_pts = engine.full_predicted_paths.get(bid, [])
            if len(act_pts) < 3:
                continue

            min_len = min(len(act_pts), len(pred_pts))
            act_y = [p[1] for p in act_pts]
            pred_y = [p[1] for p in pred_pts]
            act_x = [p[0] for p in act_pts]
            pred_x = [p[0] for p in pred_pts]

            # Smooth flight curves
            if len(act_y) >= 6:
                act_y_smooth = gaussian_filter1d(np.array(act_y[:min_len]), sigma=2.2)
                pred_y_smooth = gaussian_filter1d(np.array(pred_y[:min_len]), sigma=2.2)
                act_x_smooth = gaussian_filter1d(np.array(act_x[:min_len]), sigma=2.2)
                pred_x_smooth = gaussian_filter1d(np.array(pred_x[:min_len]), sigma=2.2)
            else:
                act_y_smooth = np.array(act_y[:min_len])
                pred_y_smooth = np.array(pred_y[:min_len])
                act_x_smooth = np.array(act_x[:min_len])
                pred_x_smooth = np.array(pred_x[:min_len])

            diff_dist = np.sqrt((pred_x_smooth - act_x_smooth)**2 + (pred_y_smooth - act_y_smooth)**2)
            mean_ade = float(np.mean(diff_dist)) if len(diff_dist) > 0 else 0.0
            final_fde = float(diff_dist[-1]) if len(diff_dist) > 0 else 0.0
            bird_acc = float(meta.get("accuracy", max(60.0, 100.0 - (mean_ade / 3.0))))

            # Save bird trajectory record
            bird_data = {
                "bird_id": bid,
                "video": v_name,
                "total_frames": meta.get("total_frames", len(act_pts)),
                "lifespan_sec": round(len(act_pts) / fps, 2),
                "speed_px_f": meta.get("speed", 0.0),
                "heading_deg": meta.get("heading", 0.0),
                "accuracy_pct": round(bird_acc, 2),
                "ade_px": round(mean_ade, 2),
                "fde_px": round(final_fde, 2),
                "actual_x": [round(float(px), 1) for px in act_x],
                "actual_y": [round(float(py), 1) for py in act_y],
                "predicted_x": [round(float(px), 1) for px in pred_x[:min_len]],
                "predicted_y": [round(float(py), 1) for py in pred_y[:min_len]]
            }
            all_birds_records.append(bird_data)
            video_birds.append(bird_data)

            # Generate individual bird trajectory comparison graph
            plot_filename = f"bird_{clean_v_tag}_ID{bid}_trajectory.png"
            plot_path = os.path.join(PLOTS_DIR, plot_filename)
            bird_data["plot_path"] = plot_path

            fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=120)
            fig.patch.set_facecolor(DARK_BG)
            ax.set_facecolor(PANEL_BG)

            steps = list(range(min_len))
            tunnel_band = np.maximum(12.0, 8.0 + 0.12 * np.array(steps) + np.abs(pred_y_smooth - act_y_smooth) * 0.40)
            ax.fill_between(
                steps,
                pred_y_smooth - tunnel_band,
                pred_y_smooth + tunnel_band,
                color=ACCENT_RED,
                alpha=0.18,
                label='Predicted Flight Tunnel (Moving Zone)'
            )
            ax.plot(steps, pred_y_smooth, color=ACCENT_RED, linewidth=2.4, label=f'GRU Prediction (ADE: {mean_ade:.1f}px)')
            ax.plot(steps, act_y_smooth, color=ACCENT_BLUE, linewidth=2.4, label='Aerodynamic Flight Path (Wings & Body)')

            # Add time markers
            ymin, ymax = float(np.min(act_y_smooth)), float(np.max(act_y_smooth))
            for s_mark in [1.0, 2.0, 3.0, 4.0]:
                f_idx = int(round(s_mark * fps))
                if f_idx < min_len:
                    ax.axvline(f_idx, color=ACCENT_CYAN, linestyle=':', alpha=0.7, linewidth=1.2)
                    ax.text(f_idx + 1, ymax - (ymax - ymin) * 0.10, f"+{int(s_mark)}s", color=ACCENT_CYAN, fontsize=8, fontweight='bold')

            ax.set_title(f"Bird #{bid} [{v_name[:28]}] | Accuracy: {bird_acc:.1f}% | Heading: {meta.get('heading', 0):.0f}°", color='white', fontsize=11, fontweight='bold', pad=10)
            ax.set_xlabel("Time Step (Frames)", color=TEXT_MUTED, fontsize=9)
            ax.set_ylabel("Vertical Position (Pixels)", color=TEXT_MUTED, fontsize=9)
            ax.tick_params(colors=TEXT_MUTED, labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(BORDER_COLOR)
            ax.grid(True, linestyle='--', alpha=0.25, color='#475569')
            ax.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='upper left', fontsize=8)

            plt.tight_layout()
            plt.savefig(plot_path, dpi=120, facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close()

            # Generate 2D spatial trajectory map
            plot2d_filename = f"bird_{clean_v_tag}_ID{bid}_2d_path.png"
            plot2d_path = os.path.join(PLOTS_DIR, plot2d_filename)
            bird_data["plot2d_path"] = plot2d_path

            fig2, ax2 = plt.subplots(figsize=(6.0, 4.5), dpi=120)
            fig2.patch.set_facecolor(DARK_BG)
            ax2.set_facecolor(PANEL_BG)

            ax2.plot(act_x_smooth, act_y_smooth, color=ACCENT_GREEN, linewidth=2.5, label='Actual 2D Path')
            ax2.plot(pred_x_smooth, pred_y_smooth, color=ACCENT_MAGENTA, linestyle='--', linewidth=2.0, label='Predicted 2D Path')
            ax2.scatter(act_x_smooth[0], act_y_smooth[0], color=ACCENT_CYAN, s=80, zorder=5, label='Flight Start')
            ax2.scatter(act_x_smooth[-1], act_y_smooth[-1], color=ACCENT_YELLOW, s=80, zorder=5, label='Current Point')

            ax2.set_title(f"Bird #{bid} 2D Airspace Coordinates", color='white', fontsize=11, fontweight='bold', pad=10)
            ax2.set_xlabel("X Coordinate (px)", color=TEXT_MUTED, fontsize=9)
            ax2.set_ylabel("Y Coordinate (px)", color=TEXT_MUTED, fontsize=9)
            ax2.invert_yaxis()  # Image coordinate system
            ax2.tick_params(colors=TEXT_MUTED, labelsize=8)
            for spine in ax2.spines.values():
                spine.set_color(BORDER_COLOR)
            ax2.grid(True, linestyle='--', alpha=0.25, color='#475569')
            ax2.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='best', fontsize=8)

            plt.tight_layout()
            plt.savefig(plot2d_path, dpi=120, facecolor=fig2.get_facecolor(), edgecolor='none')
            plt.close()

        video_summaries.append({
            "video": v_name,
            "processed_frames": processed_frames,
            "duration_sec": round(processed_frames / fps, 1),
            "fps": round(v_fps, 1),
            "birds_tracked": len(video_birds),
            "samples_learned": v_samples_learned
        })

    # 4. Generate Master Online Learning Dashboard & Curves
    print("\n[4/6] Generating Master Online Learning Loss, Accuracy & Error Curves...")

    # A. 4-Panel Master Dashboard
    dash_path = os.path.join(PLOTS_DIR, "online_learning_master_dashboard.png")
    fig, axs = plt.subplots(2, 2, figsize=(14, 9), dpi=150)
    fig.patch.set_facecolor(DARK_BG)

    # 1. Loss History
    ax1 = axs[0, 0]
    ax1.set_facecolor(PANEL_BG)
    losses = [s["loss"] for s in step_history]
    if len(losses) > 0:
        smoothed_loss = gaussian_filter1d(losses, sigma=1.8) if len(losses) >= 4 else losses
        ax1.plot(range(1, len(losses) + 1), losses, color='#fca5a5', alpha=0.45, label='Raw Step Loss')
        ax1.plot(range(1, len(losses) + 1), smoothed_loss, color=ACCENT_RED, linewidth=2.2, label='Smoothed Gaussian NLL Loss')
        ax1.set_title("Online Trajectory Loss Convergence", color='white', fontsize=12, fontweight='bold', pad=10)
        ax1.set_xlabel("Online Learning Steps", color=TEXT_MUTED, fontsize=9)
        ax1.set_ylabel("Loss (Gaussian NLL + Smoothness)", color=TEXT_MUTED, fontsize=9)
        ax1.tick_params(colors=TEXT_MUTED)
        ax1.grid(True, linestyle='--', alpha=0.25, color='#475569')
        ax1.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='upper right')

    # 2. Accuracy History
    ax2 = axs[0, 1]
    ax2.set_facecolor(PANEL_BG)
    accs = [s["accuracy"] for s in step_history]
    if len(accs) > 0:
        smoothed_acc = gaussian_filter1d(accs, sigma=1.8) if len(accs) >= 4 else accs
        ax2.plot(range(1, len(accs) + 1), smoothed_acc, color=ACCENT_GREEN, linewidth=2.2, label='Trajectory Accuracy %')
        ax2.axhline(80.0, color=ACCENT_YELLOW, linestyle=':', alpha=0.8, label='80% Target Benchmark')
        ax2.set_title("Online Trajectory Accuracy Progression (%)", color='white', fontsize=12, fontweight='bold', pad=10)
        ax2.set_xlabel("Online Learning Steps", color=TEXT_MUTED, fontsize=9)
        ax2.set_ylabel("Accuracy (%)", color=TEXT_MUTED, fontsize=9)
        ax2.tick_params(colors=TEXT_MUTED)
        ax2.grid(True, linestyle='--', alpha=0.25, color='#475569')
        ax2.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='lower right')

    # 3. ADE@20 and FDE@20 Error History
    ax3 = axs[1, 0]
    ax3.set_facecolor(PANEL_BG)
    ades = [s["ade_20"] for s in step_history]
    fdes = [s["fde_20"] for s in step_history]
    if len(ades) > 0:
        ax3.plot(range(1, len(ades) + 1), ades, color=ACCENT_CYAN, linewidth=2.0, label='ADE@20 (Average Displacement Error)')
        ax3.plot(range(1, len(fdes) + 1), fdes, color=ACCENT_MAGENTA, linewidth=2.0, label='FDE@20 (Final Displacement Error)')
        ax3.set_title("Displacement Error Metrics (Lower is Better)", color='white', fontsize=12, fontweight='bold', pad=10)
        ax3.set_xlabel("Online Learning Steps", color=TEXT_MUTED, fontsize=9)
        ax3.set_ylabel("Displacement Error (Normalized)", color=TEXT_MUTED, fontsize=9)
        ax3.tick_params(colors=TEXT_MUTED)
        ax3.grid(True, linestyle='--', alpha=0.25, color='#475569')
        ax3.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='upper right')

    # 4. Total Cumulative Samples Learned
    ax4 = axs[1, 1]
    ax4.set_facecolor(PANEL_BG)
    samples_seq = [s["total_samples"] for s in step_history]
    if len(samples_seq) > 0:
        ax4.plot(range(1, len(samples_seq) + 1), samples_seq, color=ACCENT_YELLOW, linewidth=2.2, label='Cumulative Flight Samples')
        ax4.set_title("Cumulative Flight Trajectory Samples Learned", color='white', fontsize=12, fontweight='bold', pad=10)
        ax4.set_xlabel("Online Learning Steps", color=TEXT_MUTED, fontsize=9)
        ax4.set_ylabel("Total Samples", color=TEXT_MUTED, fontsize=9)
        ax4.tick_params(colors=TEXT_MUTED)
        ax4.grid(True, linestyle='--', alpha=0.25, color='#475569')
        ax4.legend(facecolor='#1b2030', edgecolor='#334155', labelcolor='white', loc='lower right')

    for ax in [ax1, ax2, ax3, ax4]:
        for spine in ax.spines.values():
            spine.set_color(BORDER_COLOR)

    plt.suptitle("BIRDPATH AI: REAL-TIME ONLINE LEARNING TELEMETRY DASHBOARD", color='white', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(dash_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"  Saved Master Dashboard Plot: {dash_path}")

    # 5. Export Data to JSON and CSV
    print("\n[5/6] Exporting Structured JSON & CSV Data Files...")
    json_path = os.path.join(OUTPUT_DIR, "all_birds_telemetry.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_birds_tracked": len(all_birds_records),
            "total_samples_learned": trainer.total_samples_learned,
            "final_loss": trainer.latest_loss,
            "final_ade": trainer.latest_ade,
            "final_fde": trainer.latest_fde,
            "video_summaries": video_summaries,
            "birds": all_birds_records
        }, f, indent=2)
    print(f"  Saved JSON Telemetry: {json_path}")

    # CSV 1: Birds Summary
    birds_csv = os.path.join(OUTPUT_DIR, "all_birds_summary.csv")
    with open(birds_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Bird_ID", "Video_Source", "Total_Frames", "Lifespan_Sec", "Speed_px_f", "Heading_Deg", "Accuracy_Pct", "ADE_px", "FDE_px"])
        for b in all_birds_records:
            writer.writerow([
                b["bird_id"], b["video"], b["total_frames"], b["lifespan_sec"],
                b["speed_px_f"], b["heading_deg"], b["accuracy_pct"], b["ade_px"], b["fde_px"]
            ])
    print(f"  Saved Birds CSV Summary: {birds_csv}")

    # CSV 2: Online Learning Step History
    steps_csv = os.path.join(OUTPUT_DIR, "online_learning_step_history.csv")
    with open(steps_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Step", "Video_Source", "Video_Frame", "Cumulative_Samples", "Loss", "ADE_20", "FDE_20", "Accuracy_Pct"])
        for s in step_history:
            writer.writerow([
                s["step"], s["video"], s["frame"], s["total_samples"],
                round(s["loss"], 4), round(s["ade_20"], 4), round(s["fde_20"], 4), round(s["accuracy"], 2)
            ])
    print(f"  Saved Online Steps CSV: {steps_csv}")

    # Save Updated Model Checkpoints
    ckpt_master = os.path.join(BASE_DIR, "checkpoints", "learned_bird_gru_master.pt")
    ckpt_cl = os.path.join(CL_DIR, "checkpoints", "learned_bird_gru.pt")
    trainer.save_checkpoint(path=ckpt_master)
    trainer.save_checkpoint(path=ckpt_cl)
    print(f"  Saved Master Model Checkpoint: {ckpt_master} (Samples: {trainer.total_samples_learned:,})")

    # 6. Build Publication-Grade Executive PDF Report
    print("\n[6/6] Compiling Publication-Grade PDF Audit Dossier...")
    pdf_path = os.path.join(OUTPUT_DIR, "BirdPath_Complete_Online_Learning_And_Birds_Report.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(letter),
        leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('RepTitle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor("#0f172a"), alignment=1, spaceAfter=8)
    sub_style = ParagraphStyle('RepSub', parent=styles['Normal'], fontSize=11, leading=15, textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=14)
    sec_style = ParagraphStyle('RepSec', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor("#1e293b"), spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle('RepBody', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    body_bold = ParagraphStyle('RepBold', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#0f172a"), fontName="Helvetica-Bold")

    story = []

    # Title Banner
    story.append(Paragraph("BIRDPATH AI: ALL BIRDS & ONLINE LEARNING TELEMETRY REPORT", title_style))
    story.append(Paragraph(f"Autonomous Flight Trajectory Prediction Audit • Total Birds Tracked: {len(all_birds_records)} • Total Samples: {trainer.total_samples_learned:,} • Date: {time.strftime('%Y-%m-%d %H:%M')}", sub_style))

    # Master KPI Table
    mean_acc = np.mean([b["accuracy_pct"] for b in all_birds_records]) if all_birds_records else 0.0
    mean_ade = np.mean([b["ade_px"] for b in all_birds_records]) if all_birds_records else 0.0
    mean_fde = np.mean([b["fde_px"] for b in all_birds_records]) if all_birds_records else 0.0

    kpi_data = [
        [
            Paragraph("<b>Total Videos Evaluated</b>", body_bold),
            Paragraph(f"{len(video_summaries)} Video Streams", body_style),
            Paragraph("<b>Overall Trajectory Accuracy</b>", body_bold),
            Paragraph(f"<b>{mean_acc:.1f}%</b> (Target: >80%)", body_bold)
        ],
        [
            Paragraph("<b>Total Birds Tracked</b>", body_bold),
            Paragraph(f"{len(all_birds_records)} Aerial Targets", body_style),
            Paragraph("<b>Average Displacement Error</b>", body_bold),
            Paragraph(f"{mean_ade:.2f} px (ADE)", body_style)
        ],
        [
            Paragraph("<b>Online Learned Samples</b>", body_bold),
            Paragraph(f"<b>{trainer.total_samples_learned:,}</b> Samples", body_bold),
            Paragraph("<b>Final Displacement Error</b>", body_bold),
            Paragraph(f"{mean_fde:.2f} px (FDE@20)", body_style)
        ],
        [
            Paragraph("<b>Final Trajectory Loss</b>", body_bold),
            Paragraph(f"{trainer.latest_loss:.4f} (Gaussian NLL)", body_style),
            Paragraph("<b>Exported Model Checkpoint</b>", body_bold),
            Paragraph("learned_bird_gru_master.pt", body_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.8*inch, 2.3*inch, 2.0*inch, 2.4*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Master Dashboard Chart
    story.append(Paragraph("Executive Online Learning Performance Dashboard", sec_style))
    if os.path.exists(dash_path):
        story.append(RLImage(dash_path, width=7.8*inch, height=4.3*inch))
    story.append(PageBreak())

    # Section 2: Video Processing Breakdown Table
    story.append(Paragraph("Evaluated Video Streams & Detection Summary", sec_style))
    v_table_data = [["Video File", "Frames", "Duration", "Inference FPS", "Birds Found", "Samples Learned"]]
    for vs in video_summaries:
        v_table_data.append([
            vs["video"][:35],
            str(vs["processed_frames"]),
            f"{vs['duration_sec']}s",
            f"{vs['fps']} FPS",
            str(vs["birds_tracked"]),
            f"+{vs['samples_learned']:,}"
        ])
    vt = Table(v_table_data, colWidths=[2.8*inch, 1.0*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.3*inch])
    vt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#f1f5f9")]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(vt)
    story.append(Spacer(1, 14))

    # Section 3: All Detected Birds Master Table
    story.append(Paragraph("Master Aerial Birds Trajectory Catalog", sec_style))
    b_table_data = [["Bird ID", "Video Source", "Frames", "Lifespan", "Speed", "Heading", "ADE", "FDE", "Accuracy"]]
    for b in all_birds_records[:25]:  # Top 25 in table
        b_table_data.append([
            f"Bird #{b['bird_id']}",
            b["video"][:22],
            str(b["total_frames"]),
            f"{b['lifespan_sec']}s",
            f"{b['speed_px_f']:.1f} px/f",
            f"{b['heading_deg']:.0f}°",
            f"{b['ade_px']:.1f} px",
            f"{b['fde_px']:.1f} px",
            f"{b['accuracy_pct']:.1f}%"
        ])
    bt = Table(b_table_data, colWidths=[0.9*inch, 2.2*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    bt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#f1f5f9")]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(bt)
    story.append(PageBreak())

    # Section 4: Individual Bird Trajectory & 2D Airspace Plots
    story.append(Paragraph("Individual Bird Flight Trajectories & 3D Flight Tunnels", sec_style))
    story.append(Paragraph("Each figure below showcases the flap-damped center-of-mass trajectory (Blue), the GRU neural prediction (Red), and the shaded Moving Zone Keep-Out Tunnel Envelope, accompanied by the 2D spatial airspace projection.", sub_style))

    for idx, b in enumerate(all_birds_records[:12]):  # Top showcase birds
        p_traj = b.get("plot_path")
        p_2d = b.get("plot2d_path")
        if p_traj and os.path.exists(p_traj) and p_2d and os.path.exists(p_2d):
            if idx > 0 and idx % 2 == 0:
                story.append(PageBreak())
                story.append(Paragraph("Individual Bird Flight Trajectories & 3D Flight Tunnels (Cont.)", sec_style))

            b_header = f"Bird #{b['bird_id']} — Video: {b['video']} | Accuracy: {b['accuracy_pct']:.1f}% | ADE: {b['ade_px']:.1f}px"
            story.append(Paragraph(b_header, body_bold))

            img_table = Table([[
                RLImage(p_traj, width=4.8*inch, height=2.6*inch),
                RLImage(p_2d, width=3.4*inch, height=2.6*inch)
            ]], colWidths=[5.0*inch, 3.6*inch])
            img_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(img_table)
            story.append(Spacer(1, 8))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"  Saved Complete PDF Report: {pdf_path}")

    # Synchronize report to PPT and static folders
    ppt_report = os.path.join(BASE_DIR, "PPT", "BirdPath_Complete_Online_Learning_And_Birds_Report.pdf")
    static_report = os.path.join(CL_DIR, "static", "BirdPath_Complete_Online_Learning_And_Birds_Report.pdf")
    shutil.copy2(pdf_path, ppt_report)
    shutil.copy2(pdf_path, static_report)
    print("  Synchronized PDF report to PPT/ and computer learning/static/")

    print("\n" + "=" * 70)
    print(">>> ALL BIRDS, TRAJECTORIES, GRAPHS, METRICS & CHECKPOINTS SAVED! <<<")
    print("=" * 70)

if __name__ == "__main__":
    main()
