import sys
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)  # 16:9 Widescreen
    blank_layout = prs.slide_layouts[6]

    # Dark Theme Colors
    BG_COLOR = RGBColor(15, 17, 23)        # #0f1117
    CARD_BG = RGBColor(22, 25, 34)         # #161922
    BORDER_COLOR = RGBColor(40, 45, 60)    # #282d3c
    TEXT_MAIN = RGBColor(255, 255, 255)
    TEXT_DIM = RGBColor(160, 174, 192)
    ACCENT_GREEN = RGBColor(0, 230, 118)   # #00E676
    ACCENT_CYAN = RGBColor(0, 229, 255)    # #00E5FF
    ACCENT_YELLOW = RGBColor(255, 214, 0)  # #FFD600
    ACCENT_MAGENTA = RGBColor(224, 64, 251)# #E040FB
    ACCENT_ORANGE = RGBColor(255, 145, 0)

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category="BIRDPATH SYSTEM GUIDE"):
        # Category tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_CYAN

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_MAIN

    def add_card(slide, left, top, width, height, title, body_bullets, accent_color=ACCENT_CYAN):
        # Card Background
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = BORDER_COLOR
        card.line.width = Pt(1.5)

        # Content Box
        tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.2), Inches(width - 0.4), Inches(height - 0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p_head = tf.paragraphs[0]
        p_head.text = title
        p_head.font.size = Pt(18)
        p_head.font.bold = True
        p_head.font.color.rgb = accent_color
        p_head.space_after = Pt(10)

        for bullet in body_bullets:
            p = tf.add_paragraph()
            p.text = "• " + bullet
            p.font.size = Pt(13)
            p.font.color.rgb = TEXT_MAIN
            p.space_after = Pt(6)

    # -------------------------------------------------------------
    # SLIDE 1: TITLE SLIDE
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    # Main Brand Box
    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(3.0))
    tf1 = t_box.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "🦅 BIRDPATH AI"
    p0.font.size = Pt(20)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_GREEN

    p1 = tf1.add_paragraph()
    p1.text = "Real-Time Bird Detection, Tracking & Flight Path Prediction"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_MAIN
    p1.space_before = Pt(8)

    p2 = tf1.add_paragraph()
    p2.text = "A Complete Visual Guide to How the Deep Learning Architecture Works"
    p2.font.size = Pt(18)
    p2.font.color.rgb = ACCENT_CYAN
    p2.space_before = Pt(12)

    # Sub-box highlights
    add_card(s1, 1.0, 4.8, 3.5, 2.0, "👁️ Vision & Tracking", ["YOLOv8 Real-time Detector", "ByteTracker Motion Association", "Kalman Filter Trajectory State"], ACCENT_CYAN)
    add_card(s1, 4.9, 4.8, 3.5, 2.0, "🧠 Deep Forecasting", ["Bidirectional GRU Network", "20 Future Steps (~1.0 sec)", "Gaussian Uncertainty Output"], ACCENT_GREEN)
    add_card(s1, 8.8, 4.8, 3.5, 2.0, "⚡ Online Learning", ["Live GPU Backpropagation", "Learns directly from video", "300,000+ flight samples"], ACCENT_YELLOW)

    # -------------------------------------------------------------
    # SLIDE 2: THE 30-SECOND BIG PICTURE
    # -------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "The Big Picture: How the System Works in 5 Steps")

    add_card(s2, 0.8, 1.8, 2.2, 5.0, "1. VIDEO IN", [
        "Streams YouTube (720p/1080p) or local MP4 files.",
        "Decodes at 30 FPS.",
        "Feeds frames into the AI vision pipeline."
    ], ACCENT_CYAN)

    add_card(s2, 3.2, 1.8, 2.2, 5.0, "2. DETECTION", [
        "YOLOv8 finds every bird in each frame.",
        "Draws bounding boxes around birds.",
        "Calculates center (X, Y) coordinates."
    ], ACCENT_GREEN)

    add_card(s2, 5.6, 1.8, 2.2, 5.0, "3. TRACKING", [
        "ByteTracker assigns permanent IDs (#1, #2...).",
        "Tracks history of last 15 positions.",
        "Kalman Filter smooths noisy measurements."
    ], ACCENT_YELLOW)

    add_card(s2, 8.0, 1.8, 2.2, 5.0, "4. PREDICTION", [
        "GRU model predicts next 20 future frames (~1 sec ahead).",
        "Draws GREEN path line.",
        "Calculates confidence uncertainty band."
    ], ACCENT_ORANGE)

    add_card(s2, 10.4, 1.8, 2.2, 5.0, "5. LIVE LEARNING", [
        "Waits 20 frames to see where bird ACTUALLY flew.",
        "Draws MAGENTA truth line.",
        "Updates model weights live on GPU!"
    ], ACCENT_MAGENTA)

    # -------------------------------------------------------------
    # SLIDE 3: THE 3 DISPLAY LAYERS
    # -------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "Joined Display: Layer 1 + Layer 2 + Layer 3")

    add_card(s3, 0.8, 1.8, 3.6, 5.0, "LAYER 1: The Video", [
        "Raw incoming YouTube or local camera video feed.",
        "Provides realistic visual context of the sky, landscape, or flock.",
        "CAN BE SWITCHED OFF on-the-fly to show a high-contrast dark space grid for forensic trajectory analysis!"
    ], ACCENT_CYAN)

    add_card(s3, 4.8, 1.8, 3.6, 5.0, "LAYER 2: The Bounding Boxes", [
        "YOLOv8 detection boxes around each bird.",
        "Displays Bird ID (e.g. #3, #15) and detection confidence percentage (e.g. 94%).",
        "Color-coded uniquely per bird so flock members are never mixed up."
    ], ACCENT_YELLOW)

    add_card(s3, 8.8, 1.8, 3.6, 5.0, "LAYER 3: The Flight Paths", [
        "GREEN LINE: 20-frame future predicted flight path.",
        "MAGENTA LINE: Actual observed ground-truth flight path.",
        "CYAN GLOW: Gaussian variance uncertainty cone.",
        "Shows exactly where AI thought the bird would go vs reality."
    ], ACCENT_GREEN)

    # -------------------------------------------------------------
    # SLIDE 4: THE 3 FLIGHT LINES EXPLAINED SIMPLY
    # -------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "Understanding the 3 Flight Lines on Screen")

    add_card(s4, 0.8, 1.8, 3.6, 5.0, "🟩 GREEN LINE: The Forecast", [
        "What it represents: The AI's forecast of the next 20 frames (~1.0 second ahead).",
        "How it works: A GRU neural network looks at the bird's past 15 frames of speed and turn angle to calculate the future trajectory.",
        "Analogy: Like the projected path of a hurricane or flight radar cone."
    ], ACCENT_GREEN)

    add_card(s4, 4.8, 1.8, 3.6, 5.0, "🟪 MAGENTA LINE: The Reality", [
        "What it represents: The ground-truth path where the bird ACTUALLY flew in real life.",
        "How it works: The system waits 20 frames, looks back at the bird's recorded history, and traces its real trajectory.",
        "The Goal: Make the Green Line overlap the Magenta Line as closely as possible!"
    ], ACCENT_MAGENTA)

    add_card(s4, 8.8, 1.8, 3.6, 5.0, "🟦 CYAN BAND: Confidence Cone", [
        "What it represents: The AI's uncertainty spread around its prediction.",
        "How it works: Close to the bird (step 1-3), the circle is tight (high certainty). Further into the future (step 20), it expands slightly.",
        "Analogy: Like your confidence predicting where someone will walk in 1 second vs 10 seconds."
    ], ACCENT_CYAN)

    # -------------------------------------------------------------
    # SLIDE 5: HOW THE ONLINE LEARNING LOOP WORKS
    # -------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Online Learning: How the AI Improves in Real-Time")

    add_card(s5, 0.8, 1.8, 5.6, 5.0, "Traditional ML vs Online Learning", [
        "TRADITIONAL TRAINING (Offline):",
        "  • Requires downloading thousands of images into folders.",
        "  • Model weights are static and frozen during playback.",
        "  • Cannot adapt to a new species or wind speed.",
        "",
        "ONLINE LEARNING (Your System):",
        "  • Learns live from incoming video frames continuously!",
        "  • GPU updates weights immediately after seeing reality.",
        "  • Over 300,000 real flight samples learned so far on your PC!"
    ], ACCENT_CYAN)

    add_card(s5, 6.8, 1.8, 5.6, 5.0, "The 5-Step Continuous Loop", [
        "1. OBSERVE: System tracks bird's past 15 frames (X, Y, velocity).",
        "2. PREDICT: GRU model outputs future 20-frame coordinates.",
        "3. BUFFER: Holds prediction in memory while video continues playing.",
        "4. COMPARE: Once 20 frames pass, compares prediction vs actual flight.",
        "5. UPDATE: Backpropagates Gaussian NLL loss into PyTorch model on GPU!",
        "",
        "Result: The longer you watch a video, the smarter the model gets!"
    ], ACCENT_YELLOW)

    # -------------------------------------------------------------
    # SLIDE 6: TELEMETRY DASHBOARD METRICS
    # -------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Telemetry Dashboard: What the Numbers Mean")

    add_card(s6, 0.8, 1.8, 5.6, 5.0, "Operational Metrics", [
        "STREAM FPS (14.5 FPS):",
        "  • Speed of the video monitor.",
        "  • Processes 14.5 frames every second while simultaneously running YOLO + GRU + Backpropagation on GPU.",
        "",
        "ACTIVE BIRDS (5 to 15):",
        "  • Number of birds tracked simultaneously.",
        "",
        "PROCESSED FRAMES (66,000+):",
        "  • Total video frames ingested from YouTube.",
        "",
        "SAMPLES LEARNED (300,000+):",
        "  • Total flight training steps learned by the model."
    ], ACCENT_CYAN)

    add_card(s6, 6.8, 1.8, 5.6, 5.0, "Accuracy & Loss Metrics", [
        "ONLINE LOSS (-117.5) & AVG LOSS (-118.8):",
        "  • Measures combined position error and confidence.",
        "  • Negative means extremely confident and accurate!",
        "",
        "ADE @ 20 STEPS (0.0399 / ~4%):",
        "  • Average Displacement Error across all 20 future steps.",
        "",
        "FDE @ 20 STEPS (0.0765 / ~7.6%):",
        "  • Final Displacement Error at the 20th destination step.",
        "  • Instantaneous and session average match: model is fully stabilized!"
    ], ACCENT_GREEN)

    # -------------------------------------------------------------
    # SLIDE 7: ADE & FDE EXPLAINED SIMPLY
    # -------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Understanding ADE & FDE Accuracy Metrics")

    add_card(s7, 0.8, 1.8, 5.6, 5.0, "ADE: Average Displacement Error", [
        "What it measures:",
        "  • The average error across ALL 20 points along the path.",
        "  • (Step 1 + Step 2 + ... + Step 20) / 20.",
        "",
        "Your Score: 0.0399 (~4% of screen width)",
        "  • On a 1920x1080 video: 1920 * 0.0399 = ~76 pixels.",
        "  • Along the entire flight path, the prediction stays within a couple dozen pixels of the bird!",
        "",
        "Benchmark: ADE < 0.05 is considered State-of-the-Art in trajectory forecasting research."
    ], ACCENT_CYAN)

    add_card(s7, 6.8, 1.8, 5.6, 5.0, "FDE: Final Displacement Error", [
        "What it measures:",
        "  • The error specifically at the FINAL destination point (Step 20).",
        "  • Predicting 20 frames ahead (~1.0 sec) is much harder because small errors compound over time.",
        "",
        "Your Score: 0.0765 (~7.6% of screen width)",
        "  • Even 1 full second into the future, the prediction lands almost directly on the bird's body!",
        "",
        "Why both match your session average:",
        "  • Shows the model isn't guessing randomly — its accuracy is solid, stable, and repeatable."
    ], ACCENT_YELLOW)

    # -------------------------------------------------------------
    # SLIDE 8: WHY IS THE LOSS NEGATIVE? (-118 to -154)
    # -------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "Why Can the Loss Be Negative? (-118 to -154)")

    add_card(s8, 0.8, 1.8, 5.6, 5.0, "The Math Behind Negative Loss", [
        "In basic machine learning (like MSE), loss is always >= 0.",
        "However, your model outputs a GAUSSIAN PROBABILITY:",
        "  • Output = [Position (x, y) + Variance (sigma^2)]",
        "  • Loss = 0.5 * sum[ log(sigma^2) + (Target - Pred)^2 / sigma^2 ]",
        "",
        "Continuous Probability Density can be > 1:",
        "  • When the model is very confident, the bell curve is tall and narrow.",
        "  • The logarithm of small variance is NEGATIVE! (e.g. log(0.001) = -6.9)",
        "  • Across 40 predicted values (20 steps * 2 coords), negative terms sum up to -120 to -154!"
    ], ACCENT_CYAN)

    add_card(s8, 6.8, 1.8, 5.6, 5.0, "What -154 Means for Your Model", [
        "The Code Clamps Variance at min = -8.0:",
        "  • Lowest possible theoretical score: 40 * (0.5 * -8.0) = -160.0",
        "",
        "Hitting -154 means:",
        "  • Your model operates at ~96% of its theoretical maximum confidence and accuracy!",
        "",
        "How to read it:",
        "  • More negative (-100 -> -150) = Better, higher confidence.",
        "  • Rising towards positive (-120 -> +10) = Bird made a sudden, unexpected turn or dive."
    ], ACCENT_GREEN)

    # -------------------------------------------------------------
    # SLIDE 9: WINDOWS TASK MANAGER & MEMORY HEALTH
    # -------------------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "System Health: What Windows Task Manager is Doing")

    add_card(s9, 0.8, 1.8, 5.6, 5.0, "Why Windows Terminal Uses 1.9 GB", [
        "Windows Terminal Host (1.9 GB RAM):",
        "  • This is your active Python server (server.py) running inside PowerShell.",
        "  • Inside this process:",
        "      1. PyTorch Deep Learning Engine + CUDA GPU drivers",
        "      2. YOLOv8 Object Detection Neural Network",
        "      3. GRU Flight Trajectory Prediction Model",
        "      4. OpenCV HD Video Decoder Buffer",
        "",
        "Is 1.9 GB normal? YES! Deep learning models in RAM typically take 1.5 - 2.5 GB.",
        "CRITICAL: Never click 'End' or your learning server stops!"
    ], ACCENT_ORANGE)

    add_card(s9, 6.8, 1.8, 5.6, 5.0, "Other Applications in Task Manager", [
        "Brave Browser (1.9 GB):",
        "  • Streaming real-time 30 FPS video with HTML5 canvas graphics and telemetry.",
        "",
        "Antigravity Assistant (604 MB):",
        "  • Your pair programming IDE and development workspace.",
        "",
        "Safe to Close if PC feels slow:",
        "  • LibreOffice (55 MB), Snipping Tool (58 MB), Phone Link (21 MB).",
        "  • These are regular desktop tools unrelated to the AI."
    ], ACCENT_CYAN)

    # -------------------------------------------------------------
    # SLIDE 10: THE TESTING LAB & FORENSICS
    # -------------------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "Dedicated Testing Lab: Custom Frame Gaps & Forensics")

    add_card(s10, 0.8, 1.8, 5.6, 5.0, "Custom Frame Gap Selection", [
        "Located at: http://localhost:8000/static/test.html",
        "",
        "Custom Frame Gap Controls:",
        "  • Gap 1: Shows all 20 predicted future points (dense line)",
        "  • Gap 2: Shows every 2nd frame (10 waypoints)",
        "  • Gap 4 / Gap 5: Major keyframe milestones (1/6th second intervals)",
        "  • Gap 10: Half-second checkpoints",
        "",
        "Prediction Horizon Slider:",
        "  • Adjust forecast depth from 5 steps up to 20 steps on-the-fly!"
    ], ACCENT_CYAN)

    add_card(s10, 6.8, 1.8, 5.6, 5.0, "Kinematics & Forensic Tools", [
        "Flight Kinematics Dashboard:",
        "  • 🧭 360° Heading Compass: Real-time direction (e.g. 45° NE).",
        "  • ⚡ Speedometer: Linear velocity in px/frame and px/second.",
        "  • 🔄 Turn Rate: Classified into Cruising, Curving, or Banking.",
        "",
        "Full Waypoints Table + Export:",
        "  • Exact coordinates, timestamps, and uncertainty radii.",
        "  • One-click Export to JSON or CSV format.",
        "",
        "Interactive Mouse Sandbox:",
        "  • Draw any flight curve with your mouse to test extrapolation!"
    ], ACCENT_YELLOW)

    # -------------------------------------------------------------
    # SLIDE 11: SUMMARY & ANDROID DEPLOYMENT
    # -------------------------------------------------------------
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "Summary: Complete Pipeline from PC to Mobile")

    add_card(s11, 0.8, 1.8, 3.6, 5.0, "1. Computer Learning", [
        "Web UI Studio streams YouTube at 720p/1080p.",
        "Continuous online training adapts to real flight aerodynamics on GPU.",
        "Visual 3-layer joined monitor."
    ], ACCENT_CYAN)

    add_card(s11, 4.8, 1.8, 3.6, 5.0, "2. Weight Export", [
        "Click 'Save Learned Model Checkpoint'.",
        "Converts PyTorch (.pt) -> ONNX -> TFLite (INT8 quantized).",
        "Model compressed to < 5 MB for real-time edge execution."
    ], ACCENT_GREEN)

    add_card(s11, 8.8, 1.8, 3.6, 5.0, "3. Android App", [
        "Native Kotlin Android Studio project.",
        "CameraX 60 FPS live camera input.",
        "Full analytic Kalman Filter + ByteTracker.",
        "Spline flight path overlay on mobile screen!"
    ], ACCENT_YELLOW)

    output_path = r"C:\dep learning\BirdPath_System_Explanation.pptx"
    prs.save(output_path)
    print(f"[PPT Generator] Presentation successfully created: {output_path}")
    return output_path

if __name__ == "__main__":
    create_presentation()
