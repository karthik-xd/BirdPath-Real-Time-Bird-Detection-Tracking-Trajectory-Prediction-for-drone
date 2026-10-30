import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_system_diagram():
    # Canvas dimensions: 2560 x 1600 (High-Resolution 16:10)
    W, H = 2560, 1600
    img = Image.new("RGBA", (W, H), (11, 14, 22, 255)) # Futuristic dark slate
    draw = ImageDraw.Draw(img)

    # Load system fonts
    font_dir = "C:/Windows/Fonts/"
    try:
        font_title = ImageFont.truetype(font_dir + "segoeuib.ttf", 52)
        font_sub = ImageFont.truetype(font_dir + "segoeui.ttf", 24)
        font_header = ImageFont.truetype(font_dir + "segoeuib.ttf", 32)
        font_section = ImageFont.truetype(font_dir + "segoeuib.ttf", 26)
        font_body = ImageFont.truetype(font_dir + "segoeui.ttf", 20)
        font_bold = ImageFont.truetype(font_dir + "segoeuib.ttf", 21)
        font_mono = ImageFont.truetype(font_dir + "consola.ttf", 19)
        font_mono_bold = ImageFont.truetype(font_dir + "consolab.ttf", 22)
        font_small = ImageFont.truetype(font_dir + "segoeui.ttf", 17)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_header = font_title
        font_section = font_title
        font_body = font_title
        font_bold = font_title
        font_mono = font_title
        font_mono_bold = font_title
        font_small = font_title

    # Theme colors
    C_BG_CARD = (18, 24, 38, 255)
    C_CARD_BORDER = (45, 58, 85, 255)
    C_CYAN = (0, 229, 255, 255)
    C_GREEN = (0, 230, 118, 255)
    C_YELLOW = (255, 214, 0, 255)
    C_RED = (239, 68, 68, 255)
    C_MAGENTA = (224, 64, 251, 255)
    C_ORANGE = (255, 145, 0, 255)
    C_TEXT = (241, 245, 249, 255)
    C_MUTED = (148, 163, 184, 255)

    # 1. Subtle background grid
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(20, 26, 40, 255), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(20, 26, 40, 255), width=1)

    # 2. Header Banner
    draw.rounded_rectangle([(40, 30), (W - 40, 130)], radius=16, fill=(15, 20, 32, 255), outline=C_CYAN, width=2)
    # Category tag
    draw.rounded_rectangle([(65, 45), (280, 75)], radius=6, fill=(0, 229, 255, 30), outline=C_CYAN, width=1)
    draw.text((80, 50), "SYSTEM ARCHITECTURE", font=font_mono_bold, fill=C_CYAN)

    draw.text((310, 42), "FPV DRONE & 'MY MACHINE' AI INTEGRATION DIAGRAM", font=font_title, fill=C_TEXT)
    draw.text((65, 88), "Physical Drone Hardware Setup  •  Ground Relay Dock [V G P G G 5 T R]  •  Deep Learning Trajectory & Collision Avoidance Server", font=font_sub, fill=C_MUTED)

    # 3. Left Panel: Physical Hardware Setup
    # Left card background
    draw.rounded_rectangle([(40, 150), (1200, 1380)], radius=20, fill=C_BG_CARD, outline=C_CARD_BORDER, width=2)
    
    # Left Header
    draw.rounded_rectangle([(60, 170), (450, 215)], radius=8, fill=(0, 229, 255, 25), outline=C_CYAN, width=1)
    draw.text((80, 175), "1. OPERATOR HARDWARE SETUP", font=font_header, fill=C_CYAN)

    # Load and place user hardware setup image
    hw_img_path = r"C:\dep learning\hardware_setup.png"
    if os.path.exists(hw_img_path):
        hw_img = Image.open(hw_img_path).convert("RGBA")
        # Resize to fit nicely
        hw_target_w = 660
        hw_aspect = hw_img.height / hw_img.width
        hw_target_h = int(hw_target_w * hw_aspect)
        if hw_target_h > 660:
            hw_target_h = 660
            hw_target_w = int(hw_target_h / hw_aspect)
        
        hw_img_resized = hw_img.resize((hw_target_w, hw_target_h), Image.Resampling.LANCZOS)
        
        # Draw frame around image
        img_x = 60
        img_y = 230
        draw.rounded_rectangle([(img_x - 4, img_y - 4), (img_x + hw_target_w + 4, img_y + hw_target_h + 4)], radius=12, fill=(10, 14, 22, 255), outline=C_CARD_BORDER, width=2)
        img.paste(hw_img_resized, (img_x, img_y), hw_img_resized)

        # Callouts pointing to items in the image
        # Callout A: Quadcopter Drone
        draw.line([(730, 290), (770, 290), (790, 270), (1170, 270)], fill=C_CYAN, width=2)
        draw.ellipse([(725, 285), (735, 295)], fill=C_CYAN)
        draw.rounded_rectangle([(790, 230), (1170, 310)], radius=8, fill=(15, 22, 36, 255), outline=C_CYAN, width=1)
        draw.text((805, 238), "AIRBORNE FPV QUADCOPTER", font=font_bold, fill=C_CYAN)
        draw.text((805, 262), "• 6S LiPo Flight Battery (Top-mounted)", font=font_small, fill=C_TEXT)
        draw.text((805, 282), "• Underslung Payload Canister / Body", font=font_small, fill=C_MUTED)

        # Callout B: Ground Dock Station
        draw.line([(730, 520), (770, 520), (790, 480), (1170, 480)], fill=C_YELLOW, width=2)
        draw.ellipse([(725, 515), (735, 525)], fill=C_YELLOW)
        draw.rounded_rectangle([(790, 440), (1170, 560)], radius=8, fill=(15, 22, 36, 255), outline=C_YELLOW, width=1)
        draw.text((805, 448), "GROUND RELAY DOCK STATION", font=font_bold, fill=C_YELLOW)
        draw.text((805, 472), "• Docked Base Station Smart Battery", font=font_small, fill=C_TEXT)
        draw.text((805, 492), "• Breakout Terminal: V G P G G 5 T R", font=font_small, fill=C_CYAN)
        draw.text((805, 512), "• Coaxial RF / BNC Video Output to Goggles", font=font_small, fill=C_MUTED)
        draw.text((805, 532), "• Tether / Umbilical Link to Airborne Drone", font=font_small, fill=C_MUTED)

        # Callout C: RadioMaster TX16S & PCB
        draw.line([(730, 710), (770, 710), (790, 680), (1170, 680)], fill=C_MAGENTA, width=2)
        draw.ellipse([(725, 705), (735, 715)], fill=C_MAGENTA)
        draw.rounded_rectangle([(790, 650), (1170, 750)], radius=8, fill=(15, 22, 36, 255), outline=C_MAGENTA, width=1)
        draw.text((805, 658), "PILOT RC & TRANSCODER PCB", font=font_bold, fill=C_MAGENTA)
        draw.text((805, 682), "• RadioMaster TX16S 16-Ch Transmitter", font=font_small, fill=C_TEXT)
        draw.text((805, 702), "• PPM -> S-BUS Decoder Interface Board", font=font_small, fill=C_CYAN)
        draw.text((805, 722), "• Red: +5V  |  Black: GND  |  Green: S.BUS", font=font_small, fill=C_YELLOW)

        # Callout D: FPV VR Goggles
        draw.line([(730, 830), (770, 830), (790, 810), (1170, 810)], fill=C_ORANGE, width=2)
        draw.ellipse([(725, 825), (735, 835)], fill=C_ORANGE)
        draw.rounded_rectangle([(790, 780), (1170, 865)], radius=8, fill=(15, 22, 36, 255), outline=C_ORANGE, width=1)
        draw.text((805, 788), "PILOT FPV VR GOGGLES", font=font_bold, fill=C_ORANGE)
        draw.text((805, 812), "• Dual-Antenna Box-Style FPV Goggles", font=font_small, fill=C_TEXT)
        draw.text((805, 834), "• Augmented Cockpit HUD / SBS 3D Display", font=font_small, fill=C_CYAN)

    # 4. Breakout Pinout Matrix Box (Bottom of Left Card)
    pin_box_y = 920
    draw.rounded_rectangle([(60, pin_box_y), (1180, 1350)], radius=14, fill=(13, 17, 28, 255), outline=C_CARD_BORDER, width=2)
    draw.text((80, pin_box_y + 15), "GROUND DOCK TERMINAL PINOUT: [ V  G  P  G  G  5  T  R ]", font=font_section, fill=C_YELLOW)
    
    # 8 Pin cards
    pins = [
        ("V", "Video Out", "Analog CVBS", "TO MY MACHINE (Video In)", C_CYAN),
        ("G", "Video GND", "0V Ground", "TO MY MACHINE (GND)", (100, 116, 139, 255)),
        ("P", "PPM / SBUS", "Control Signal", "FROM PCB (Green Wire)", C_GREEN),
        ("G", "Sig GND", "0V Ground", "FROM PCB (Black Wire)", (100, 116, 139, 255)),
        ("G", "Pwr GND", "0V Ground", "System Power Common", (100, 116, 139, 255)),
        ("5", "+5V DC", "+5.0V Power", "TO PCB (Red Wire)", C_RED),
        ("T", "UART TX", "Telemetry Down", "TO MY MACHINE (Serial RX)", C_ORANGE),
        ("R", "UART RX", "Override Up", "FROM MY MACHINE (MAVLink #147)", C_GREEN),
    ]

    px_start = 80
    pw = 132
    for i, (p_name, p_func, p_volt, p_dest, p_col) in enumerate(pins):
        cx = px_start + i * (pw + 6)
        cy = pin_box_y + 60
        # Pin pill
        draw.rounded_rectangle([(cx, cy), (cx + pw, cy + 180)], radius=8, fill=(19, 25, 42, 255), outline=p_col, width=2)
        # Big pin letter
        draw.rounded_rectangle([(cx + 4, cy + 4), (cx + pw - 4, cy + 50)], radius=6, fill=p_col)
        draw.text((cx + (pw - 20) // 2, cy + 10), p_name, font=font_header, fill=(10, 14, 22, 255))
        # Details
        draw.text((cx + 10, cy + 58), p_func, font=font_bold, fill=C_TEXT)
        draw.text((cx + 10, cy + 85), p_volt, font=font_small, fill=p_col)
        draw.line([(cx + 10, cy + 110), (cx + pw - 10, cy + 110)], fill=C_CARD_BORDER, width=1)
        
        # Word wrap destination
        words = p_dest.split(" ")
        line1 = " ".join(words[:2])
        line2 = " ".join(words[2:]) if len(words) > 2 else ""
        draw.text((cx + 8, cy + 118), line1, font=font_small, fill=C_MUTED)
        if line2:
            draw.text((cx + 8, cy + 138), line2, font=font_small, fill=C_MUTED)

    # Note at bottom of pin matrix
    draw.rounded_rectangle([(80, pin_box_y + 260), (1160, pin_box_y + 300)], radius=6, fill=(0, 230, 118, 20), outline=C_GREEN, width=1)
    draw.text((95, pin_box_y + 268), "✓ HARDWARE VERIFIED: Clean isolation between pilot manual control (P, 5, G) and AI evasion injection (V, G, T, R)", font=font_body, fill=C_GREEN)


    # 5. Right Panel: "MY MACHINE" (AI Deep Learning & Collision Avoidance Server)
    draw.rounded_rectangle([(1240, 150), (W - 40, 1380)], radius=20, fill=(16, 22, 34, 255), outline=C_GREEN, width=3)
    
    # Right Header
    draw.rounded_rectangle([(1265, 170), (1960, 215)], radius=8, fill=(0, 230, 118, 25), outline=C_GREEN, width=1)
    draw.text((1285, 175), "★ 2. 'MY MACHINE' (AI DEEP LEARNING & COLLISION AVOIDANCE SERVER)", font=font_header, fill=C_GREEN)

    # Two Main Sub-Screens of My Machine
    # Screen A: Dual Studio Web UI (Learning Area & Testing Studio)
    screen_a_x, screen_a_y = 1265, 235
    screen_a_w, screen_a_h = 600, 390
    draw.rounded_rectangle([(screen_a_x, screen_a_y), (screen_a_x + screen_a_w, screen_a_y + screen_a_h)], radius=12, fill=(8, 12, 18, 255), outline=C_CYAN, width=2)
    # Title bar
    draw.rounded_rectangle([(screen_a_x + 1, screen_a_y + 1), (screen_a_x + screen_a_w - 1, screen_a_y + 36)], radius=10, fill=(20, 28, 44, 255))
    draw.ellipse([(screen_a_x + 12, screen_a_y + 12), (screen_a_x + 24, screen_a_y + 24)], fill=C_RED)
    draw.ellipse([(screen_a_x + 30, screen_a_y + 12), (screen_a_x + 42, screen_a_y + 24)], fill=C_YELLOW)
    draw.ellipse([(screen_a_x + 48, screen_a_y + 12), (screen_a_x + 60, screen_a_y + 24)], fill=C_GREEN)
    draw.text((screen_a_x + 80, screen_a_y + 7), "BIRDPATH AI: LEARNING AREA & TESTING STUDIO (http://localhost:8000/)", font=font_mono, fill=C_TEXT)

    # Inner preview graphic for Screen A: simulated detection, 1s-4s paths, cylinder tunnel
    draw.rectangle([(screen_a_x + 10, screen_a_y + 45), (screen_a_x + screen_a_w - 10, screen_a_y + screen_a_h - 10)], fill=(5, 8, 14, 255))
    # Synthetic horizon & dark airspace grid
    for gy in range(screen_a_y + 60, screen_a_y + screen_a_h - 20, 40):
        draw.line([(screen_a_x + 10, gy), (screen_a_x + screen_a_w - 10, gy)], fill=(15, 22, 35, 255), width=1)
    
    # 3D Moving Zone Cylinder Tunnel
    tunnel_pts = [
        (screen_a_x + 60, screen_a_y + 280),
        (screen_a_x + 160, screen_a_y + 220),
        (screen_a_x + 280, screen_a_y + 170),
        (screen_a_x + 420, screen_a_y + 140),
        (screen_a_x + 550, screen_a_y + 120),
    ]
    # Draw cylinder glow
    for i in range(len(tunnel_pts) - 1):
        draw.line([tunnel_pts[i], tunnel_pts[i+1]], fill=(0, 230, 118, 120), width=36)
        draw.line([tunnel_pts[i], tunnel_pts[i+1]], fill=(0, 229, 255, 220), width=6)
    
    # Cylinder Rib Rings (Layer 6)
    for ptx, pty in tunnel_pts:
        draw.ellipse([(ptx - 22, pty - 34), (ptx + 22, pty + 34)], outline=C_CYAN, width=3)
    
    # Milestones badges
    draw.text((tunnel_pts[1][0] - 15, tunnel_pts[1][1] - 50), "+1.0s", font=font_mono_bold, fill=C_GREEN)
    draw.text((tunnel_pts[2][0] - 15, tunnel_pts[2][1] - 50), "+2.0s", font=font_mono_bold, fill=C_GREEN)
    draw.text((tunnel_pts[3][0] - 15, tunnel_pts[3][1] - 50), "+3.0s", font=font_mono_bold, fill=C_GREEN)
    draw.text((tunnel_pts[4][0] - 15, tunnel_pts[4][1] - 50), "+4.0s", font=font_mono_bold, fill=C_GREEN)

    # Bird Bounding Box & Target Lock
    bx, by = tunnel_pts[0]
    draw.rectangle([(bx - 30, by - 25), (bx + 30, by + 25)], outline=C_YELLOW, width=3)
    draw.text((bx - 28, by - 48), "🦅 BIRD 98%", font=font_mono_bold, fill=C_YELLOW)
    draw.ellipse([(bx - 6, by - 6), (bx + 6, by + 6)], fill=C_RED)

    # Inset Trajectory Graph (Layer 7)
    draw.rounded_rectangle([(screen_a_x + screen_a_w - 180, screen_a_y + screen_a_h - 130), (screen_a_x + screen_a_w - 20, screen_a_y + screen_a_h - 20)], radius=6, fill=(10, 16, 26, 230), outline=C_CYAN, width=1)
    draw.text((screen_a_x + screen_a_w - 170, screen_a_y + screen_a_h - 124), "L7: FLIGHT INSET", font=font_mono, fill=C_CYAN)
    # Sine wave graph line
    for gx in range(screen_a_x + screen_a_w - 170, screen_a_x + screen_a_w - 30, 4):
        gy_val = screen_a_y + screen_a_h - 75 + int(np.sin((gx - screen_a_x) * 0.1) * 25)
        draw.point((gx, gy_val), fill=C_GREEN)

    # Screen B: Drone VR Flight Mode (Standalone & Headset View)
    screen_b_x, screen_b_y = 1890, 235
    screen_b_w, screen_b_h = 600, 390
    draw.rounded_rectangle([(screen_b_x, screen_b_y), (screen_b_x + screen_b_w, screen_b_y + screen_b_h)], radius=12, fill=(8, 12, 18, 255), outline=C_ORANGE, width=2)
    # Title bar
    draw.rounded_rectangle([(screen_b_x + 1, screen_b_y + 1), (screen_b_x + screen_b_w - 1, screen_b_y + 36)], radius=10, fill=(28, 22, 38, 255))
    draw.ellipse([(screen_b_x + 12, screen_b_y + 12), (screen_b_x + 24, screen_b_y + 24)], fill=C_RED)
    draw.ellipse([(screen_b_x + 30, screen_b_y + 12), (screen_b_x + 42, screen_b_y + 24)], fill=C_YELLOW)
    draw.ellipse([(screen_b_x + 48, screen_b_y + 12), (screen_b_x + 60, screen_b_y + 24)], fill=C_GREEN)
    draw.text((screen_b_x + 80, screen_b_y + 7), "DRONE VR FPV COCKPIT & SBS 3D HUD (/vr)", font=font_mono, fill=C_ORANGE)

    # Inner preview graphic for Screen B: FPV VR Cockpit HUD with Artificial Horizon & Threat Lock
    draw.rectangle([(screen_b_x + 10, screen_b_y + 45), (screen_b_x + screen_b_w - 10, screen_b_y + screen_b_h - 10)], fill=(6, 8, 16, 255))
    center_x = screen_b_x + screen_b_w // 2
    center_y = screen_b_y + screen_b_h // 2 + 10

    # Artificial Horizon Waterline
    draw.line([(center_x - 140, center_y), (center_x - 40, center_y)], fill=C_CYAN, width=2)
    draw.line([(center_x + 40, center_y), (center_x + 140, center_y)], fill=C_CYAN, width=2)
    draw.line([(center_x - 40, center_y), (center_x - 40, center_y + 15)], fill=C_CYAN, width=2)
    draw.line([(center_x + 40, center_y), (center_x + 40, center_y + 15)], fill=C_CYAN, width=2)
    # Center Crosshair
    draw.ellipse([(center_x - 6, center_y - 6), (center_x + 6, center_y + 6)], outline=C_CYAN, width=2)

    # Compass Tape (Top)
    draw.rectangle([(center_x - 120, screen_b_y + 55), (center_x + 120, screen_b_y + 85)], fill=(12, 18, 30, 200), outline=C_CYAN, width=1)
    draw.text((center_x - 100, screen_b_y + 60), "240   255   [ 270° W ]   285   300", font=font_mono, fill=C_CYAN)

    # Pitch Ladder
    for step in [-40, 40]:
        draw.line([(center_x - 50, center_y + step), (center_x - 20, center_y + step)], fill=C_CYAN, width=1)
        draw.line([(center_x + 20, center_y + step), (center_x + 50, center_y + step)], fill=C_CYAN, width=1)

    # Threat Lock & Collision Warning
    draw.rectangle([(center_x + 50, center_y - 70), (center_x + 130, center_y + 10)], outline=C_RED, width=3)
    draw.text((center_x + 55, center_y - 92), "⚠ THREAT INTERCEPT", font=font_mono_bold, fill=C_RED)
    
    # Glowing Evasion Vector Arrow (θ ± 90° Orthogonal Break)
    draw.line([(center_x, center_y), (center_x - 110, center_y - 90)], fill=C_GREEN, width=4)
    # Arrow head
    draw.polygon([(center_x - 110, center_y - 90), (center_x - 90, center_y - 85), (center_x - 105, center_y - 70)], fill=C_GREEN)
    draw.text((center_x - 170, center_y - 120), "ESCAPE VECTOR (θ + 90°)", font=font_bold, fill=C_GREEN)
    draw.text((center_x - 170, center_y - 98), "THROTTLE: 90% BURST", font=font_mono_bold, fill=C_YELLOW)


    # Core Architectural Modules of "My Machine"
    mod_y = 650
    mod_w = (screen_a_w * 2 + 25 - 60) // 4
    
    modules = [
        ("1. VISION CORE", "YOLOv8 + ByteTrack", "• 60 FPS live video ingestion\n• Center-of-Mass (CoM) decoupling\n• Completely cancels wing flap jitter\n• High-precision centroid tracking", C_CYAN),
        ("2. TRAJECTORY AI", "PyTorch GRU Models", "• 1.0s, 2.0s, 3.0s, 4.0s forecasting\n• Trained on 764,000+ flight samples\n• Physics-informed velocity tensor\n• Continuous online loss backprop", C_GREEN),
        ("3. SAFETY TUNNEL", "3D Moving Zone Corridor", "• Volumetric cylinder keep-out zone\n• Outer/inner Gaussian glow tubes\n• 3D circular rib rings & time badges\n• 7 independent layer toggles (L1-L7)", C_YELLOW),
        ("4. EVASION ENGINE", "Autonomous Kinematics", "• Orthogonal break escape solver\n• 85% to 95% vertical climb burst\n• Displaces drone outside tunnel\n• Generates MAVLink #147 packets", C_RED),
    ]

    for i, (m_title, m_sub, m_desc, m_col) in enumerate(modules):
        mx = 1265 + i * (mod_w + 20)
        draw.rounded_rectangle([(mx, mod_y), (mx + mod_w, mod_y + 240)], radius=12, fill=(12, 17, 28, 255), outline=m_col, width=2)
        # Header tag
        draw.rounded_rectangle([(mx + 8, mod_y + 8), (mx + mod_w - 8, mod_y + 44)], radius=6, fill=m_col)
        draw.text((mx + 16, mod_y + 14), m_title, font=font_bold, fill=(10, 14, 22, 255))
        draw.text((mx + 16, mod_y + 54), m_sub, font=font_mono_bold, fill=m_col)
        draw.line([(mx + 16, mod_y + 82), (mx + mod_w - 16, mod_y + 82)], fill=C_CARD_BORDER, width=1)
        
        # Multiline description
        lines = m_desc.split("\n")
        for li, line in enumerate(lines):
            draw.text((mx + 16, mod_y + 95 + li * 28), line, font=font_small, fill=C_TEXT)


    # Bottom Section of My Machine: Live Drone Evasion & Dispatch Console
    console_y = 920
    console_w = screen_a_w * 2 + 25
    draw.rounded_rectangle([(1265, console_y), (1265 + console_w, 1350)], radius=14, fill=(10, 14, 22, 255), outline=C_CYAN, width=2)
    
    # Console header
    draw.rounded_rectangle([(1285, console_y + 15), (1700, console_y + 50)], radius=6, fill=(0, 229, 255, 30), outline=C_CYAN, width=1)
    draw.text((1300, console_y + 20), "DRONE ANTI-BIRD ATTACK EVASION & DISPATCH TELEMETRY", font=font_bold, fill=C_CYAN)

    # 4 Status KPI cards inside console
    kpis = [
        ("THREAT DISTANCE", "42.8 m", "CLOSING SPEED: 18.4 m/s", C_YELLOW),
        ("TIME TO INTERCEPT", "2.32 s", "COLLISION HAZARD: CRITICAL", C_RED),
        ("RECOMMENDED ESCAPE", "HDG: 345°", "ORTHOGONAL LATERAL BREAK", C_GREEN),
        ("BURST THROTTLE", "92 %", "VERTICAL CLIMB BURST ESCAPE", C_CYAN),
    ]
    kpi_w = (console_w - 60) // 4
    for ki, (k_title, k_val, k_sub, k_col) in enumerate(kpis):
        kx = 1285 + ki * (kpi_w + 12)
        ky = console_y + 65
        draw.rounded_rectangle([(kx, ky), (kx + kpi_w, ky + 90)], radius=8, fill=(15, 20, 32, 255), outline=k_col, width=1)
        draw.text((kx + 12, ky + 8), k_title, font=font_small, fill=C_MUTED)
        draw.text((kx + 12, ky + 30), k_val, font=font_header, fill=k_col)
        draw.text((kx + 12, ky + 66), k_sub, font=font_mono, fill=C_TEXT)

    # Console terminal lines
    term_y = console_y + 175
    draw.rounded_rectangle([(1285, term_y), (1265 + console_w - 20, 1330)], radius=8, fill=(5, 8, 12, 255), outline=C_CARD_BORDER, width=1)
    
    term_lines = [
        ("[00:14.281] [RADAR] Bird Centroid acquired at X=482.4, Y=310.2 | Velocity=16.8 m/s | Heading=255°", C_MUTED),
        ("[00:14.314] [GRU-4S] Trajectory projected: +1s(440,285)  +2s(395,260)  +3s(350,235)  +4s(305,210)", C_CYAN),
        ("[00:14.348] [CYLINDER] 3D Keep-Out Corridor constructed: Base_Radius=85px  Safety_Clearance=136px", C_GREEN),
        ("[00:14.380] [WARNING] Drone within predicted collision boundary! Time-to-Intercept: 2.32s!", C_RED),
        ("[00:14.412] [EVASION] Solved Escape Vector: Angle=345° (Orthogonal 90° Break) | Throttle=92% Climb", C_YELLOW),
        ("[00:14.445] [MAVLINK #147] TRAJECTORY_REPRESENTATION_WAYPOINTS dispatched -> UART Pin 'R' [SIMULATION ONLY]", C_GREEN),
    ]

    for ti, (t_text, t_col) in enumerate(term_lines):
        draw.text((1305, term_y + 12 + ti * 23), t_text, font=font_mono, fill=t_col)


    # 6. Physical Interconnection Cables (Left Hardware <---> Right Machine)
    # Cable 1: Video Ingestion (Ground Dock Pin 'V' -> My Machine USB Capture Card)
    # Draw glowing multi-segment cable
    c1_path = [(145, 980), (145, 900), (1210, 900), (1210, 320), (1265, 320)]
    for w_i in [7, 4, 2]:
        alpha = 60 if w_i == 7 else (150 if w_i == 4 else 255)
        col = (0, 229, 255, alpha)
        draw.line(c1_path, fill=col, width=w_i)
    draw.rounded_rectangle([(1120, 880), (1235, 905)], radius=4, fill=C_CYAN)
    draw.text((1130, 886), "VIDEO (V, G)", font=font_small, fill=(10, 14, 22, 255))

    # Cable 2: Telemetry & Evasion Injection (My Machine Serial -> Ground Dock Pin 'R' & 'T')
    c2_path = [(1265, 1260), (1220, 1260), (1220, 1070), (1050, 1070), (1050, 980)]
    for w_i in [7, 4, 2]:
        alpha = 60 if w_i == 7 else (150 if w_i == 4 else 255)
        col = (0, 230, 118, alpha)
        draw.line(c2_path, fill=col, width=w_i)
    draw.rounded_rectangle([(1110, 1050), (1235, 1075)], radius=4, fill=C_GREEN)
    draw.text((1120, 1056), "MAVLINK (T, R)", font=font_small, fill=(10, 14, 22, 255))

    # Cable 3: Augmented VR Stream (My Machine -> FPV VR Goggles)
    c3_path = [(1890, 420), (1225, 420), (1225, 830), (1170, 830)]
    for w_i in [7, 4, 2]:
        alpha = 60 if w_i == 7 else (150 if w_i == 4 else 255)
        col = (255, 145, 0, alpha)
        draw.line(c3_path, fill=col, width=w_i)
    draw.rounded_rectangle([(1180, 520), (1240, 545)], radius=4, fill=C_ORANGE)
    draw.text((1188, 526), "VR HUD", font=font_small, fill=(10, 14, 22, 255))

    # 7. Bottom Legend & Status Bar
    draw.rounded_rectangle([(40, 1420), (W - 40, 1560)], radius=14, fill=(13, 17, 26, 255), outline=C_CARD_BORDER, width=2)
    
    # Legend badges
    leg_x = 70
    draw.text((leg_x, 1440), "CABLE & DATA PROTOCOL LEGEND:", font=font_bold, fill=C_CYAN)
    
    legends = [
        ("YELLOW/CYAN", "Analog CVBS Video (60 FPS) from Drone Camera via Dock Pin 'V' -> My Machine Capture Card", C_CYAN),
        ("NEON GREEN", "MAVLink #147 Evasion Override & Telemetry via Dock Pin 'R' & 'T' <-> My Machine Serial", C_GREEN),
        ("ORANGE", "Augmented VR FPV Video Stream (L1-L7 Layers + HUD) from My Machine -> Pilot VR Goggles", C_ORANGE),
        ("MAGENTA", "Pilot Manual RC Control from RadioMaster TX16S -> PPM->SBUS PCB -> Ground Dock Pin 'P'", C_MAGENTA),
    ]

    for li, (l_tag, l_desc, l_col) in enumerate(legends):
        lx = leg_x + (li % 2) * 1150
        ly = 1475 + (li // 2) * 35
        draw.ellipse([(lx, ly + 4), (lx + 16, ly + 20)], fill=l_col)
        draw.text((lx + 26, ly + 2), f"[{l_tag}]", font=font_bold, fill=l_col)
        draw.text((lx + 180, ly + 2), l_desc, font=font_small, fill=C_TEXT)

    # Save output image
    out_dir = r"C:\dep learning"
    out_file = os.path.join(out_dir, "hardware_and_machine_integration_diagram.png")
    img.save(out_file, "PNG", quality=95)
    print(f"[Diagram Generator] Successfully created: {out_file} (Size: {W}x{H})")

    # Also copy to artifacts directory
    artifact_dir = r"C:\Users\karth\.gemini\antigravity\brain\ba499a31-6a2c-40bf-9e93-bea53f28f617"
    artifact_img = os.path.join(artifact_dir, "hardware_and_machine_integration_diagram.png")
    img.save(artifact_img, "PNG", quality=95)
    print(f"[Diagram Generator] Copied to artifact directory: {artifact_img}")

    return out_file

if __name__ == "__main__":
    create_system_diagram()
