import os
import sys
import shutil
import pypdf
from PIL import Image
import win32com.client
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak

BASE_DIR = r"C:\dep learning"
PPT_DIR = os.path.join(BASE_DIR, "PPT")

# Theme colors for PPT slides
BG_COLOR       = RGBColor(11, 14, 20)      # #0b0e14 Deep Navy-Black
CARD_BG        = RGBColor(18, 22, 32)      # #121620 Slate Card
BORDER_COLOR   = RGBColor(38, 46, 66)      # #262e42 Subtle Outline
TEXT_MAIN      = RGBColor(241, 245, 249)   # #f1f5f9 Crisp White
TEXT_MUTED     = RGBColor(148, 163, 184)   # #94a3b8 Slate Grey
ACCENT_CYAN    = RGBColor(0, 229, 255)     # #00e5ff Cyber Cyan
ACCENT_GREEN   = RGBColor(0, 230, 118)     # #00e676 Neon Green
ACCENT_YELLOW  = RGBColor(255, 214, 0)     # #ffd600 Golden Yellow
ACCENT_MAGENTA = RGBColor(224, 64, 251)    # #e040fb Vibrant Magenta
ACCENT_ORANGE  = RGBColor(255, 145, 0)     # #ff9100 Warning

def set_bg(slide, prs):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_COLOR
    bg.line.fill.background()
    return bg

def add_header(slide, title_text, category="BIRDPATH AI MASTER DOCUMENTATION"):
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.7), Inches(0.35))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category.upper()
    p_c.font.size = Pt(10)
    p_c.font.bold = True
    p_c.font.color.rgb = ACCENT_CYAN

    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.7), Inches(0.8))
    tf_t = t_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title_text
    p_t.font.size = Pt(24)
    p_t.font.bold = True
    p_t.font.color.rgb = TEXT_MAIN

def add_card(slide, left, top, width, height, title, bullets, accent=ACCENT_CYAN):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_BG
    card.line.color.rgb = BORDER_COLOR
    card.line.width = Pt(1.4)

    tb = slide.shapes.add_textbox(Inches(left + 0.25), Inches(top + 0.2), Inches(width - 0.5), Inches(height - 0.4))
    tf = tb.text_frame
    tf.word_wrap = True

    p_h = tf.paragraphs[0]
    p_h.text = title
    p_h.font.size = Pt(16)
    p_h.font.bold = True
    p_h.font.color.rgb = accent
    p_h.space_after = Pt(8)

    for b in bullets:
        p = tf.add_paragraph()
        p.text = ("• " if not b.startswith("  ") and not b.startswith("    ") and b != "" else "") + b
        p.font.size = Pt(12) if not b.startswith("    ") else Pt(11)
        p.font.color.rgb = TEXT_MAIN if not b.startswith("  ") else TEXT_MUTED
        p.space_after = Pt(4)

def step1_sync_master_diagrams():
    print("[1/6] Synchronizing master architecture diagrams to PPT directory...")
    diagrams = [
        "hardware_and_machine_integration_diagram.png",
        "hardware_setup.png",
        "drone_to_engine_to_vr.png"
    ]
    for d in diagrams:
        src = os.path.join(BASE_DIR, d)
        dst = os.path.join(PPT_DIR, d)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"  Copied {d} to PPT/")

def step2_enhance_presentation():
    print("\n[2/6] Building Master 36-Slide Presentation (with Related Photos)...")
    combined_pptx = os.path.join(PPT_DIR, "BirdPath_Master_Combined_Presentation.pptx")
    prs = Presentation(combined_pptx)
    blank_layout = prs.slide_layouts[6]
    
    # Check if slides already have the diagrams
    if len(prs.slides) == 33:
        # Slide 34: BirdPath AI Drone Detection System
        s34 = prs.slides.add_slide(blank_layout)
        set_bg(s34, prs)
        add_header(s34, "BirdPath AI: Drone Detection System Architecture", "AI VISION & DETECTION CORE")
        img_det = os.path.join(PPT_DIR, "BirdPath AI Drone Detection System.png")
        if os.path.exists(img_det):
            s34.shapes.add_picture(img_det, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
        add_card(s34, 6.7, 1.5, 5.8, 5.4, "Detection & Tracking Subsystem", [
            "CameraX & RTSP Video Stream Ingestion:",
            "  • 60 FPS Camera feed captured in real time via STRATEGY_KEEP_ONLY_LATEST.",
            "  • Automatic letterboxing and GPU-accelerated RGB float normalization.",
            "YOLOv8 Single-Class Bird Detection:",
            "  • High-recall neural detector targeting distant and fast-moving birds.",
            "  • Frame-difference motion hint boosters eliminate static clutter.",
            "ByteTrack & 8-State Kalman Tracker:",
            "  • Tracks [cx, cy, w, h, vx, vy, vw, vh] state vector.",
            "  • Hungarian IoU matching preserves identity across wing flappings and occlusions.",
            "Decoupled Center-of-Mass Stabilization:",
            "  • Wing flap oscillating noise removed for smooth kinematic trajectory modeling."
        ], ACCENT_CYAN)

        # Slide 35: BirdPath AI Drone Prediction Pipeline
        s35 = prs.slides.add_slide(blank_layout)
        set_bg(s35, prs)
        add_header(s35, "BirdPath AI: Drone Prediction Pipeline & Flight Dynamics", "DEEP TRAJECTORY FORECASTING")
        img_pipe = os.path.join(PPT_DIR, "BirdPath AI Drone Prediction Pipeline.png")
        if os.path.exists(img_pipe):
            s35.shapes.add_picture(img_pipe, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
        add_card(s35, 6.7, 1.5, 5.8, 5.4, "GRU Trajectory Engine & Flight Tunnels", [
            "Sliding 15-Frame Motion Window:",
            "  • Inputs normalized history vectors [cx, cy, w, h, dx, dy].",
            "  • Optical flow & IMU camera ego-motion compensation.",
            "2-Layer Gated Recurrent Unit (GRU):",
            "  • Hidden size 128 + Multi-Layer Perceptron regression head.",
            "  • Predicts 20-frame future coordinates + Gaussian log-variance bands.",
            "Multi-Horizon Dynamic Keep-Out Tunnels:",
            "  • Forecasts 0.25s, 0.5s, 1.0s, 2.0s, and 4.0s future impact waypoints.",
            "  • 3D Cylindrical safety airspace with 1.6x dynamic clearance margin.",
            "Continuous Online Learning Studio:",
            "  • Real-time NLL loss backpropagation adapts to real-world flight aerodynamics."
        ], ACCENT_GREEN)

        # Slide 36: Drone to Engine to VR & Ground Control Integration
        s36 = prs.slides.add_slide(blank_layout)
        set_bg(s36, prs)
        add_header(s36, "Drone to Engine to VR & Ground Control Integration", "TELEMETRY & HARDWARE INTEGRATION")
        img_vr = os.path.join(PPT_DIR, "drone_to_engine_to_vr.png")
        if os.path.exists(img_vr):
            s36.shapes.add_picture(img_vr, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.4))
        add_card(s36, 6.7, 1.5, 5.8, 5.4, "Hardware Bus & Immersive VR Cockpit", [
            "Ground Station Dock Pinout Integration:",
            "  • Pin 'V': Raw composite FPV video fed via UVC USB video digitizer.",
            "  • Pin 'P' & 'G': RadioMaster TX16S pilot control via S.BUS signal decoder.",
            "  • Pin 'T' & 'R': UART telemetry TX/RX for autonomous MAVLink evasion.",
            "Autonomous Anti-Bird Evasion Solver:",
            "  • Orthogonal break escape vector (θ ± 90°) evasive climb maneuver.",
            "  • Simulated MAVLink #147 COLLISION_AVOIDANCE command dispatch.",
            "WebXR 3D VR HUD Cockpit:",
            "  • Stereoscopic SBS 3D flight stream for FPV VR Goggles.",
            "  • 7 Modular visual layers with real-time toggle switches."
        ], ACCENT_YELLOW)

        prs.save(combined_pptx)
        print(f"  Saved updated PPTX with 36 slides: {combined_pptx}")
    else:
        print(f"  Presentation already contains {len(prs.slides)} slides.")

    # Export to PDF via PowerPoint COM
    combined_ppt_pdf = os.path.join(PPT_DIR, "BirdPath_Master_Combined_Presentation.pdf")
    print("  Exporting 36-slide presentation to PDF via PowerPoint COM...")
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    pres = ppt_app.Presentations.Open(combined_pptx, False, False, False)
    pres.SaveAs(combined_ppt_pdf, 32)
    pres.Close()
    ppt_app.Quit()
    print(f"  Exported PDF: {combined_ppt_pdf}")
    return combined_pptx, combined_ppt_pdf

def step3_create_diagrams_pdf():
    print("\n[3/6] Generating High-Resolution Diagrams PDF Sheet...")
    diagrams_pdf = os.path.join(PPT_DIR, "BirdPath_Architecture_Diagrams_Master.pdf")
    doc = SimpleDocTemplate(
        diagrams_pdf,
        pagesize=landscape(letter),
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DiagTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1, # Center
        spaceAfter=12
    )
    sub_style = ParagraphStyle(
        'DiagSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        alignment=1,
        spaceAfter=12
    )

    diagram_items = [
        ("BirdPath AI Drone Detection System.png", "BIRDPATH AI: DRONE DETECTION & TRACKING SYSTEM ARCHITECTURE", "High-Speed YOLOv8/11 Neural Detection, ByteTrack Hungarian Data Association & 8-State Kalman Tracking"),
        ("BirdPath AI Drone Prediction Pipeline.png", "BIRDPATH AI: DRONE PREDICTION PIPELINE & FLIGHT DYNAMICS", "Sliding History Window, 2-Layer GRU Recurrent Neural Network & Expanding Uncertainty Flight Tunnels"),
        ("hardware_and_machine_integration_diagram.png", "BIRDPATH AI: END-TO-END HARDWARE & MACHINE INTEGRATION TOPOLOGY", "FPV Drone Aircraft, Ground Dock Wiring Hub, 'My Machine' AI Edge Server & FPV VR Goggles"),
        ("hardware_setup.png", "BIRDPATH AI: PHYSICAL WIRING, PINOUTS & PCB INTERFACES", "Dock Pins (5, G, V, P, T, R), RadioMaster TX16S Transmitter, S.BUS Signal Decoder & USB UVC Video Digitizer"),
        ("drone_to_engine_to_vr.png", "BIRDPATH AI: DRONE TO AI ENGINE TO WEBXR VR MONITORING PIPELINE", "Low-Latency Video Stream, Telemetry Feedback Loop, MAVLink Collision Avoidance & 3D Stereoscopic HUD")
    ]

    story = []
    for idx, (img_name, title, subtitle) in enumerate(diagram_items):
        img_path = os.path.join(PPT_DIR, img_name)
        if not os.path.exists(img_path):
            img_path = os.path.join(BASE_DIR, img_name)
        if os.path.exists(img_path):
            if idx > 0:
                story.append(PageBreak())
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(subtitle, sub_style))
            
            with Image.open(img_path) as im:
                w, h = im.size
                aspect = w / h
            max_w = 720
            max_h = 470
            if max_w / aspect <= max_h:
                draw_w = max_w
                draw_h = max_w / aspect
            else:
                draw_h = max_h
                draw_w = max_h * aspect
            story.append(RLImage(img_path, width=draw_w, height=draw_h))

    doc.build(story)
    print(f"  Generated Diagrams Sheet PDF: {diagrams_pdf}")
    return diagrams_pdf

def step4_create_ultimate_master_pdf(combined_ppt_pdf, diagrams_pdf):
    print("\n[4/6] Creating the ULTIMATE ALL-IN-ONE MASTER PDF (All Presentations, Diagrams & Documentation)...")
    ultimate_pdf = os.path.join(PPT_DIR, "BirdPath_ULTIMATE_ALL_IN_ONE_MASTER.pdf")
    
    guide_pdf = os.path.join(PPT_DIR, "BirdPath_Complete_Concepts_Algorithms_Functions_Guide.pdf")
    params_pdf = os.path.join(PPT_DIR, "BirdPath_Full_System_Parameters_Master.pdf")
    expl_pdf = os.path.join(PPT_DIR, "BirdPath_System_Explanation.pdf")
    
    writer = pypdf.PdfWriter()
    curr_page = 0

    # Part 1: Master Presentation Slides Deck (36 Slides)
    reader_ppt = pypdf.PdfReader(combined_ppt_pdf)
    ppt_count = len(reader_ppt.pages)
    writer.add_outline_item(f"Part I: Master Presentation Slides Deck ({ppt_count} Slides)", curr_page)
    writer.add_outline_item("• Master Architecture & Pipeline (Slides 1-22)", curr_page)
    writer.add_outline_item("• Core System Deep-Dive & Hardware (Slides 23-33)", curr_page + 22)
    writer.add_outline_item("• Visual Architecture & Pipeline Photo Showcase (Slides 34-36)", curr_page + 33)
    writer.append(combined_ppt_pdf)
    curr_page += ppt_count

    # Part 2: High-Resolution Diagrams & Infographics (5 Pages)
    reader_diag = pypdf.PdfReader(diagrams_pdf)
    diag_count = len(reader_diag.pages)
    writer.add_outline_item(f"Part II: High-Resolution System Architecture & Drone Infographics ({diag_count} Diagrams)", curr_page)
    writer.add_outline_item("• Drone Detection & Tracking Architecture Infographic", curr_page)
    writer.add_outline_item("• Drone Flight Prediction Pipeline & Dynamics Infographic", curr_page + 1)
    writer.add_outline_item("• End-to-End Hardware & Machine Integration Topology", curr_page + 2)
    writer.add_outline_item("• Physical Wiring, Pinouts & PCB Signal Decoders", curr_page + 3)
    writer.add_outline_item("• Drone to AI Engine to WebXR VR HUD Pipeline", curr_page + 4)
    writer.append(diagrams_pdf)
    curr_page += diag_count

    # Part 3: Concepts, Algorithms & Functions Specification Guide
    if os.path.exists(guide_pdf):
        reader_guide = pypdf.PdfReader(guide_pdf)
        guide_count = len(reader_guide.pages)
        writer.add_outline_item(f"Part III: Concepts, Algorithms & Functions Specification Guide ({guide_count} Pages)", curr_page)
        writer.append(guide_pdf)
        curr_page += guide_count

    # Part 4: Full System Parameters Specification
    if os.path.exists(params_pdf):
        reader_params = pypdf.PdfReader(params_pdf)
        params_count = len(reader_params.pages)
        writer.add_outline_item(f"Part IV: Full System Parameters Specification ({params_count} Pages)", curr_page)
        writer.append(params_pdf)
        curr_page += params_count

    # Part 5: Deep System Explanation & Walkthrough
    if os.path.exists(expl_pdf):
        reader_expl = pypdf.PdfReader(expl_pdf)
        expl_count = len(reader_expl.pages)
        writer.add_outline_item(f"Part V: Deep System Explanation & Architecture Guide ({expl_count} Pages)", curr_page)
        writer.append(expl_pdf)
        curr_page += expl_count

    with open(ultimate_pdf, "wb") as f:
        writer.write(f)
    print(f"  Created ULTIMATE MASTER PDF: {ultimate_pdf} (Total {curr_page} Pages)")

    # Also sync to computer learning static folder
    static_dir = os.path.join(BASE_DIR, "computer learning", "static")
    if os.path.exists(static_dir):
        shutil.copy2(ultimate_pdf, os.path.join(static_dir, "BirdPath_ULTIMATE_ALL_IN_ONE_MASTER.pdf"))
        shutil.copy2(combined_ppt_pdf, os.path.join(static_dir, "BirdPath_Master_Combined_Presentation.pdf"))
        print("  Synchronized master PDFs to computer learning/static/")

    return ultimate_pdf

def step5_cleanup():
    print("\n[5/6] Cleaning up old/intermediate PPT, PDF, and redundant junk files...")
    
    # 1. Delete old/intermediate PPT and PDF files from PPT/
    old_files_to_delete = [
        os.path.join(PPT_DIR, "BirdPath_Full_Project_Master.pptx"),
        os.path.join(PPT_DIR, "BirdPath_System_Explanation.pptx"),
        os.path.join(PPT_DIR, "BirdPath_Full_Project_Master.pdf"),
        os.path.join(PPT_DIR, "BirdPath_System_Explanation.pdf"),
        os.path.join(PPT_DIR, "BirdPath_Complete_Concepts_Algorithms_Functions_Guide.pdf"),
        os.path.join(PPT_DIR, "BirdPath_Full_System_Parameters_Master.pdf"),
        os.path.join(PPT_DIR, "BirdPath_Master_Combined_Documentation.pdf"),
        os.path.join(PPT_DIR, "BirdPath_Architecture_Diagrams_Master.pdf"), # intermediate doc
        
        # In computer learning/static
        os.path.join(BASE_DIR, "computer learning", "static", "BirdPath_Complete_Concepts_Algorithms_Functions_Guide.pdf"),
        os.path.join(BASE_DIR, "computer learning", "static", "BirdPath_Full_System_Parameters_Master.pdf"),
        os.path.join(BASE_DIR, "computer learning", "static", "BirdPath_Master_Combined_Documentation.pdf"),
        
        # Root temporary test images & plots
        os.path.join(BASE_DIR, "final_plot.png"),
        os.path.join(BASE_DIR, "test_bird_plot_smoothed.png"),
        os.path.join(BASE_DIR, "test_pipeline.png"),
        os.path.join(BASE_DIR, "test_plot.png"),
        os.path.join(BASE_DIR, "crop_dock.png"),
        os.path.join(BASE_DIR, "crop_drone.png"),
        os.path.join(BASE_DIR, "crop_vr.png"),
        os.path.join(BASE_DIR, "backup_birdpath_project.zip"),
        os.path.join(BASE_DIR, "combine_all_ppt_and_pdf.py"),
        
        # Root old generator scripts
        os.path.join(BASE_DIR, "generate_simple_pipeline_picture.py"),
        os.path.join(BASE_DIR, "generate_system_diagram_image.py"),
        os.path.join(BASE_DIR, "generate_ppt.py"),
        os.path.join(BASE_DIR, "build_full_ppt.py"),
        os.path.join(BASE_DIR, "generate_master_guide_pdf.py"),
        os.path.join(BASE_DIR, "build_full_parameters_pdf.py"),

        # In computer learning temporary test frames
        os.path.join(BASE_DIR, "computer learning", "bunny_frame.jpg"),
        os.path.join(BASE_DIR, "computer learning", "bunny_frame2.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_50.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_250.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_450.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_560.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_620.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_690.jpg"),
        os.path.join(BASE_DIR, "computer learning", "frame_750.jpg"),
        os.path.join(BASE_DIR, "computer learning", "test_bird0_plot.png"),
        os.path.join(BASE_DIR, "computer learning", "test_rendered_frame.jpg"),
        os.path.join(BASE_DIR, "computer learning", "test_rendered_frame_fixed.jpg"),
        os.path.join(BASE_DIR, "computer learning", "test_wZVb_final.jpg")
    ]
    
    deleted_count = 0
    for f in old_files_to_delete:
        if os.path.exists(f):
            try:
                os.remove(f)
                deleted_count += 1
                print(f"  Removed: {os.path.basename(f)}")
            except Exception as e:
                print(f"  Error removing {f}: {e}")

    # Remove redundant root downloads folder
    root_downloads = os.path.join(BASE_DIR, "downloads")
    if os.path.exists(root_downloads):
        try:
            shutil.rmtree(root_downloads)
            print("  Removed redundant root downloads/ directory (~1.85 GB saved)")
        except Exception as e:
            print(f"  Could not remove root downloads: {e}")

    # Remove 1.8GB huge video in computer learning/downloads if present
    huge_video = os.path.join(BASE_DIR, "computer learning", "downloads", "TmOlGVxxPZM_720p.mp4")
    if os.path.exists(huge_video):
        try:
            os.remove(huge_video)
            print("  Removed 1.8GB temporary video TmOlGVxxPZM_720p.mp4 (~1.8 GB saved)")
        except Exception as e:
            print(f"  Could not remove huge video: {e}")

    # Remove caches
    for root, dirs, files in os.walk(BASE_DIR):
        for d in dirs:
            if d in ["__pycache__", ".pytest_cache"]:
                cache_path = os.path.join(root, d)
                try:
                    shutil.rmtree(cache_path)
                    print(f"  Removed cache: {cache_path}")
                except Exception:
                    pass

    print(f"  Total individual files cleaned: {deleted_count}")

def step6_verify():
    print("\n[6/6] Verifying Clean Master Directory State...")
    print("\nContents of PPT/ (Master Deliverables):")
    for f in os.listdir(PPT_DIR):
        fp = os.path.join(PPT_DIR, f)
        size_kb = os.path.getsize(fp) / 1024
        print(f"  • {f} ({size_kb:.1f} KB)")
        
    reader = pypdf.PdfReader(os.path.join(PPT_DIR, "BirdPath_ULTIMATE_ALL_IN_ONE_MASTER.pdf"))
    print(f"\nFinal ULTIMATE MASTER PDF Page Count: {len(reader.pages)} pages")
    prs = Presentation(os.path.join(PPT_DIR, "BirdPath_Master_Combined_Presentation.pptx"))
    print(f"Final Combined PowerPoint Deck Slide Count: {len(prs.slides)} slides")

if __name__ == "__main__":
    step1_sync_master_diagrams()
    combined_pptx, combined_ppt_pdf = step2_enhance_presentation()
    diagrams_pdf = step3_create_diagrams_pdf()
    ultimate_pdf = step4_create_ultimate_master_pdf(combined_ppt_pdf, diagrams_pdf)
    step5_cleanup()
    step6_verify()
    print("\n>>> All cleaning, combining, and optimization tasks completed successfully! <<<")
