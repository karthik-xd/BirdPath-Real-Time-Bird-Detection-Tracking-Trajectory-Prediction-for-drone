import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def generate_clean_pipeline_image():
    # Dimensions: 2400 x 950 (Crisp widescreen horizontal flow)
    W, H = 2400, 950
    img = Image.new("RGB", (W, H), (10, 14, 22))
    draw = ImageDraw.Draw(img)

    # Fonts
    font_dir = "C:/Windows/Fonts/"
    try:
        font_title = ImageFont.truetype(font_dir + "segoeuib.ttf", 36)
        font_box_title = ImageFont.truetype(font_dir + "segoeuib.ttf", 26)
        font_body = ImageFont.truetype(font_dir + "segoeui.ttf", 18)
        font_bold = ImageFont.truetype(font_dir + "segoeuib.ttf", 19)
        font_mono = ImageFont.truetype(font_dir + "consola.ttf", 17)
        font_mono_bold = ImageFont.truetype(font_dir + "consolab.ttf", 20)
        font_arrow = ImageFont.truetype(font_dir + "segoeuib.ttf", 20)
        font_cable = ImageFont.truetype(font_dir + "consolab.ttf", 22)
    except Exception:
        font_title = font_box_title = font_body = font_bold = font_mono = font_mono_bold = font_arrow = font_cable = ImageFont.load_default()

    # Colors
    C_BG_CARD = (18, 24, 38)
    C_BORDER = (45, 58, 85)
    C_CYAN = (0, 229, 255)
    C_GREEN = (0, 230, 118)
    C_YELLOW = (255, 214, 0)
    C_RED = (239, 68, 68)
    C_ORANGE = (255, 145, 0)
    C_TEXT = (241, 245, 249)
    C_MUTED = (148, 163, 184)

    # Subtle grid lines
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(16, 22, 34), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(16, 22, 34), width=1)

    # Title Banner at Top
    draw.rounded_rectangle([(40, 25), (W - 40, 105)], radius=12, fill=(14, 19, 30), outline=C_CYAN, width=2)
    draw.text((70, 35), "END-TO-END HARDWARE & AI FLIGHT PIPELINE", font=font_title, fill=C_TEXT)
    draw.text((70, 75), "FPV Drone  ───►  Ground Dock [V G P G G 5 T R]  ───►  Detect & Prediction Engine ('My Machine')  ──[ Video Cable ]──►  VR Goggles", font=font_body, fill=C_CYAN)

    # 4 Main Stages:
    # 1. DRONE (x: 40 to 480)
    # Arrow 1 (x: 480 to 570)
    # 2. GROUND DOCK (x: 570 to 1010)
    # Arrow 2 (x: 1010 to 1100)
    # 3. DETECT & PREDICTION ENGINE (x: 1100 to 1750)
    # Arrow 3 [ VIDEO CABLE ] (x: 1750 to 1920)
    # 4. VR GOGGLES (x: 1920 to 2360)

    card_y = 135
    card_h = 750

    # =========================================================================
    # STAGE 1: DRONE
    # =========================================================================
    b1_x1, b1_x2 = 40, 480
    draw.rounded_rectangle([(b1_x1, card_y), (b1_x2, card_y + card_h)], radius=16, fill=C_BG_CARD, outline=C_CYAN, width=2)
    
    # Title badge
    draw.rounded_rectangle([(b1_x1 + 15, card_y + 15), (b1_x2 - 15, card_y + 65)], radius=8, fill=(0, 229, 255, 30), outline=C_CYAN, width=1)
    draw.text((b1_x1 + 25, card_y + 24), "1. FPV DRONE", font=font_box_title, fill=C_CYAN)

    # Place cropped drone photo
    drone_path = r"C:\dep learning\crop_drone.png"
    if os.path.exists(drone_path):
        d_img = Image.open(drone_path).convert("RGB")
        target_w = (b1_x2 - b1_x1) - 30
        target_h = int(target_w * (d_img.height / d_img.width))
        d_resized = d_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img.paste(d_resized, (b1_x1 + 15, card_y + 80))

    # Details
    det_y = card_y + 80 + target_h + 20
    draw.rounded_rectangle([(b1_x1 + 15, det_y), (b1_x2 - 15, card_y + card_h - 20)], radius=10, fill=(12, 16, 26), outline=C_BORDER, width=1)
    draw.text((b1_x1 + 30, det_y + 15), "Airborne Flight Unit:", font=font_bold, fill=C_TEXT)
    draw.text((b1_x1 + 30, det_y + 45), "• FPV Quadcopter Carbon Frame", font=font_body, fill=C_MUTED)
    draw.text((b1_x1 + 30, det_y + 75), "• Top-Mounted 6S LiPo Battery", font=font_body, fill=C_MUTED)
    draw.text((b1_x1 + 30, det_y + 105), "• Underslung Payload Canister", font=font_body, fill=C_MUTED)
    draw.text((b1_x1 + 30, det_y + 135), "• Front-Nose 60 FPS FPV Camera", font=font_body, fill=C_CYAN)
    draw.text((b1_x1 + 30, det_y + 165), "• Video Downlink Tether / RF Link", font=font_body, fill=C_YELLOW)


    # =========================================================================
    # ARROW 1: Drone -> Ground Dock
    # =========================================================================
    arr1_x1, arr1_x2 = 490, 560
    arr_y = card_y + 240
    # Glowing arrow line
    for w_i in [6, 3]:
        draw.line([(arr1_x1, arr_y), (arr1_x2, arr_y)], fill=C_CYAN, width=w_i)
    draw.polygon([(arr1_x2, arr_y), (arr1_x2 - 16, arr_y - 12), (arr1_x2 - 16, arr_y + 12)], fill=C_CYAN)
    # Label
    draw.text((arr1_x1 - 10, arr_y - 45), "RF Video /", font=font_arrow, fill=C_CYAN)
    draw.text((arr1_x1 - 10, arr_y - 22), "Tether", font=font_arrow, fill=C_CYAN)


    # =========================================================================
    # STAGE 2: GROUND DOCK (The "_____" in user request)
    # =========================================================================
    b2_x1, b2_x2 = 570, 1020
    draw.rounded_rectangle([(b2_x1, card_y), (b2_x2, card_y + card_h)], radius=16, fill=C_BG_CARD, outline=C_YELLOW, width=2)
    
    # Title badge
    draw.rounded_rectangle([(b2_x1 + 15, card_y + 15), (b2_x2 - 15, card_y + 65)], radius=8, fill=(255, 214, 0, 30), outline=C_YELLOW, width=1)
    draw.text((b2_x1 + 25, card_y + 24), "2. GROUND DOCK / RECEIVER", font=font_box_title, fill=C_YELLOW)

    # Place cropped dock photo
    dock_path = r"C:\dep learning\crop_dock.png"
    if os.path.exists(dock_path):
        dk_img = Image.open(dock_path).convert("RGB")
        target_w = (b2_x2 - b2_x1) - 30
        target_h = int(target_w * (dk_img.height / dk_img.width))
        dk_resized = dk_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img.paste(dk_resized, (b2_x1 + 15, card_y + 80))

    # Breakout Pin Header Visual: [ V G P G G 5 T R ]
    pin_y = card_y + 80 + target_h + 15
    draw.rounded_rectangle([(b2_x1 + 15, pin_y), (b2_x2 - 15, card_y + card_h - 20)], radius=10, fill=(12, 16, 26), outline=C_YELLOW, width=1)
    draw.text((b2_x1 + 25, pin_y + 12), "Breakout Terminal Header:", font=font_bold, fill=C_YELLOW)

    # Draw the pin chips
    pin_names = ["V", "G", "P", "G", "G", "5", "T", "R"]
    pin_colors = [C_CYAN, (120, 140, 160), C_GREEN, (120, 140, 160), (120, 140, 160), C_RED, C_ORANGE, C_GREEN]
    chip_w = ((b2_x2 - b2_x1) - 60) // 8
    for pi, (pn, pc) in enumerate(zip(pin_names, pin_colors)):
        cx = b2_x1 + 25 + pi * (chip_w + 3)
        cy = pin_y + 40
        draw.rounded_rectangle([(cx, cy), (cx + chip_w, cy + 34)], radius=4, fill=pc)
        draw.text((cx + 10, cy + 6), pn, font=font_mono_bold, fill=(10, 14, 22))

    draw.text((b2_x1 + 25, pin_y + 85), "• V & G: Composite Video Out to AI Engine", font=font_body, fill=C_CYAN)
    draw.text((b2_x1 + 25, pin_y + 115), "• P, 5, G: PPM / S.BUS Pilot RC Control in", font=font_body, fill=C_MUTED)
    draw.text((b2_x1 + 25, pin_y + 145), "• T & R: UART Telemetry / MAVLink Override", font=font_body, fill=C_GREEN)
    draw.text((b2_x1 + 25, pin_y + 175), "• Coaxial RF / BNC Video Port to Goggles", font=font_body, fill=C_ORANGE)


    # =========================================================================
    # ARROW 2: Ground Dock -> Detect & Prediction Engine
    # =========================================================================
    arr2_x1, arr2_x2 = 1030, 1090
    for w_i in [6, 3]:
        draw.line([(arr2_x1, arr_y), (arr2_x2, arr_y)], fill=C_GREEN, width=w_i)
    draw.polygon([(arr2_x2, arr_y), (arr2_x2 - 16, arr_y - 12), (arr2_x2 - 16, arr_y + 12)], fill=C_GREEN)
    draw.text((arr2_x1 - 5, arr_y - 45), "Analog", font=font_arrow, fill=C_GREEN)
    draw.text((arr2_x1 - 5, arr_y - 22), "Video (V,G)", font=font_arrow, fill=C_GREEN)


    # =========================================================================
    # STAGE 3: DETECT & PREDICTION ENGINE ("MY MACHINE")
    # =========================================================================
    b3_x1, b3_x2 = 1100, 1750
    draw.rounded_rectangle([(b3_x1, card_y), (b3_x2, card_y + card_h)], radius=16, fill=(14, 22, 34), outline=C_GREEN, width=3)
    
    # Title badge
    draw.rounded_rectangle([(b3_x1 + 15, card_y + 15), (b3_x2 - 15, card_y + 65)], radius=8, fill=(0, 230, 118, 30), outline=C_GREEN, width=1)
    draw.text((b3_x1 + 25, card_y + 24), "3. DETECT & PREDICTION ENGINE ('MY MACHINE')", font=font_box_title, fill=C_GREEN)

    # Inner Simulated AI Screen: Shows Bird Detection, 1s-4s Path, 3D Cylinder Tunnel
    scr_w = (b3_x2 - b3_x1) - 30
    scr_h = 320
    scr_x = b3_x1 + 15
    scr_y = card_y + 80
    draw.rounded_rectangle([(scr_x, scr_y), (scr_x + scr_w, scr_y + scr_h)], radius=12, fill=(6, 9, 15), outline=C_CYAN, width=2)
    
    # Dark airspace grid
    for gy in range(scr_y + 30, scr_y + scr_h - 10, 35):
        draw.line([(scr_x + 5, gy), (scr_x + scr_w - 5, gy)], fill=(15, 22, 35), width=1)

    # 3D Moving Zone Cylinder Tunnel
    pts = [
        (scr_x + 60, scr_y + 240),
        (scr_x + 180, scr_y + 180),
        (scr_x + 320, scr_y + 130),
        (scr_x + 460, scr_y + 95),
        (scr_x + 570, scr_y + 75),
    ]
    # Cylinder glow
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=(0, 230, 118), width=24)
        draw.line([pts[i], pts[i+1]], fill=(0, 229, 255), width=4)
    # Circular rib rings
    for px, py in pts:
        draw.ellipse([(px - 18, py - 28), (px + 18, py + 28)], outline=C_CYAN, width=2)

    # Milestone badges: 1s, 2s, 3s, 4s
    draw.text((pts[1][0] - 15, pts[1][1] - 44), "+1.0s", font=font_mono_bold, fill=C_GREEN)
    draw.text((pts[2][0] - 15, pts[2][1] - 44), "+2.0s", font=font_mono_bold, fill=C_GREEN)
    draw.text((pts[3][0] - 15, pts[3][1] - 44), "+3.0s", font=font_mono_bold, fill=C_GREEN)
    draw.text((pts[4][0] - 15, pts[4][1] - 44), "+4.0s", font=font_mono_bold, fill=C_GREEN)

    # Bird Bounding Box & Centroid
    bx, by = pts[0]
    draw.rectangle([(bx - 32, by - 26), (bx + 32, by + 26)], outline=C_YELLOW, width=3)
    draw.text((bx - 30, by - 48), "🦅 BIRD 98%", font=font_mono_bold, fill=C_YELLOW)
    draw.ellipse([(bx - 6, by - 6), (bx + 6, by + 6)], fill=C_RED)

    # Description of AI Capabilities
    desc_y = scr_y + scr_h + 15
    draw.rounded_rectangle([(b3_x1 + 15, desc_y), (b3_x2 - 15, card_y + card_h - 20)], radius=10, fill=(12, 16, 26), outline=C_BORDER, width=1)
    draw.text((b3_x1 + 30, desc_y + 15), "Deep Learning Trajectory & Collision Avoidance Core:", font=font_bold, fill=C_TEXT)
    draw.text((b3_x1 + 30, desc_y + 45), "• YOLOv8 Real-Time Bird Detection @ 60 FPS (Wing-flap decoupled CoM)", font=font_body, fill=C_CYAN)
    draw.text((b3_x1 + 30, desc_y + 75), "• GRU Multi-Step Forecaster: 1.0s, 2.0s, 3.0s, 4.0s predicted milestones", font=font_body, fill=C_GREEN)
    draw.text((b3_x1 + 30, desc_y + 105), "• 3D Cylindrical Moving Zone Safety Tunnel with 3D rib rings (L5 & L6)", font=font_body, fill=C_YELLOW)
    draw.text((b3_x1 + 30, desc_y + 135), "• Kinematic Evasion Solver: 90° Orthogonal Break Vector + 90% Burst Throttle", font=font_body, fill=C_RED)
    draw.text((b3_x1 + 30, desc_y + 165), "• 7 Modular Visual Layers: Selected layers rendered into VR output stream!", font=font_body, fill=C_ORANGE)


    # =========================================================================
    # ARROW 3: [ VIDEO CABLE ] (Highlighted prominent cable requested by user!)
    # =========================================================================
    arr3_x1, arr3_x2 = 1760, 1910
    # Bold glowing HDMI / AV Video Cable
    for w_i in [10, 6, 2]:
        col = (255, 145, 0) if w_i <= 6 else (255, 200, 50)
        draw.line([(arr3_x1, arr_y), (arr3_x2, arr_y)], fill=col, width=w_i)
    draw.polygon([(arr3_x2, arr_y), (arr3_x2 - 20, arr_y - 14), (arr3_x2 - 20, arr_y + 14)], fill=C_ORANGE)
    
    # Glowing Video Cable Badge
    draw.rounded_rectangle([(arr3_x1 - 10, arr_y - 65), (arr3_x2 + 5, arr_y - 20)], radius=6, fill=C_ORANGE)
    draw.text((arr3_x1 - 2, arr_y - 58), "VIDEO CABLE", font=font_cable, fill=(10, 14, 22))
    draw.text((arr3_x1 + 5, arr_y + 25), "(HDMI / AV)", font=font_mono_bold, fill=C_ORANGE)


    # =========================================================================
    # STAGE 4: VR GOGGLES
    # =========================================================================
    b4_x1, b4_x2 = 1920, 2360
    draw.rounded_rectangle([(b4_x1, card_y), (b4_x2, card_y + card_h)], radius=16, fill=C_BG_CARD, outline=C_ORANGE, width=2)
    
    # Title badge
    draw.rounded_rectangle([(b4_x1 + 15, card_y + 15), (b4_x2 - 15, card_y + 65)], radius=8, fill=(255, 145, 0, 30), outline=C_ORANGE, width=1)
    draw.text((b4_x1 + 25, card_y + 24), "4. VR GOGGLES", font=font_box_title, fill=C_ORANGE)

    # Place cropped VR goggles photo
    vr_path = r"C:\dep learning\crop_vr.png"
    if os.path.exists(vr_path):
        v_img = Image.open(vr_path).convert("RGB")
        target_w = (b4_x2 - b4_x1) - 30
        target_h = int(target_w * (v_img.height / v_img.width))
        v_resized = v_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img.paste(v_resized, (b4_x1 + 15, card_y + 80))

    # Details
    vr_det_y = card_y + 80 + target_h + 20
    draw.rounded_rectangle([(b4_x1 + 15, vr_det_y), (b4_x2 - 15, card_y + card_h - 20)], radius=10, fill=(12, 16, 26), outline=C_BORDER, width=1)
    draw.text((b4_x1 + 30, vr_det_y + 15), "Pilot Head-Mounted Display:", font=font_bold, fill=C_TEXT)
    draw.text((b4_x1 + 30, vr_det_y + 45), "• Dual-Antenna FPV VR Goggles", font=font_body, fill=C_MUTED)
    draw.text((b4_x1 + 30, vr_det_y + 75), "• FPV Cockpit HUD (Horizon & Pitch)", font=font_body, fill=C_CYAN)
    draw.text((b4_x1 + 30, vr_det_y + 105), "• Stereoscopic SBS 3D Dual-Eye Mode", font=font_body, fill=C_ORANGE)
    draw.text((b4_x1 + 30, vr_det_y + 135), "• Threat Intercept Lock Reticle", font=font_body, fill=C_RED)
    draw.text((b4_x1 + 30, vr_det_y + 165), "• Glowing Evasion Vector Guidance", font=font_body, fill=C_GREEN)
    draw.text((b4_x1 + 30, vr_det_y + 195), "• SELECTED LAYERS ONLY DISPLAYED", font=font_bold, fill=C_YELLOW)


    # Output paths
    out_file1 = r"C:\dep learning\computer learning\static\drone_to_engine_to_vr.png"
    out_file2 = r"C:\dep learning\drone_to_engine_to_vr.png"
    out_file3 = r"C:\Users\karth\.gemini\antigravity\brain\ba499a31-6a2c-40bf-9e93-bea53f28f617\drone_to_engine_to_vr.png"
    
    img.save(out_file1, "PNG", quality=95)
    img.save(out_file2, "PNG", quality=95)
    img.save(out_file3, "PNG", quality=95)
    print(f"[Pipeline Generator] Successfully created clean pipeline picture: {out_file1}")
    return out_file1

if __name__ == "__main__":
    generate_clean_pipeline_image()
