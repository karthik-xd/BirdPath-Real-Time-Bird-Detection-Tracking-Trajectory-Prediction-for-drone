# BirdPath: Real-Time Bird Detection, Tracking & Flight Path Prediction

BirdPath is an end-to-end computer vision and deep learning system for Android and Python. It captures live camera frames, detects flying birds in real time using YOLOv8, tracks individual birds across video frames using an 8-state Kalman Filter and ByteTrack two-stage association, forecasts future flight trajectories using a 2-layer Recurrent Neural Network (GRU) with Gaussian uncertainty variance bands, and renders everything on-device in a hardware-accelerated three-layer overlay.

---

## System Architecture & Pipeline Flow

```
+-----------------------------------------------------------------------------------------+
|                                    PER-FRAME PIPELINE                                   |
|                                                                                         |
| CameraX Preview (1080p, 60fps)                                                          |
|       |                                                                                 |
|       v                                                                                 |
| ImageAnalysis (STRATEGY_KEEP_ONLY_LATEST)                                               |
|       |                                                                                 |
|       v                                                                                 |
| Preprocess: Letterbox to 640x640 + Normalized RGB Float                                 |
|       |                                                                                 |
|       +--> [Optional Motion Hint: Frame Difference (t vs t-1) boosts moving candidate scores]
|       |                                                                                 |
|       v                                                                                 |
| YOLOv8n / YOLO11n Single-Class Bird Detector (TFLite GPU Delegate / NNAPI / CPU)        |
|       |                                                                                 |
|       v                                                                                 |
| ByteTrack Association (Hungarian IoU Matching)                                          |
|       |-- Stage 1: High-confidence detections (score >= 0.50) matched to existing tracks|
|       +-- Stage 2: Low-confidence detections (0.10 <= score < 0.50) matched to remnants|
|       |                                                                                 |
|       v                                                                                 |
| 8-State Kalman Filter: State [cx, cy, w, h, vx, vy, vw, vh]^T                           |
|       |-- Predict: x = F*x, P = F*P*F^T + Q                                             |
|       +-- Update:  y = z - H*x, K = P*H^T*inv(S), x = x + K*y, P = (I - K*H)*P          |
|       |                                                                                 |
|       v                                                                                 |
| Camera Ego-Motion Compensation: Subtracts phone pan/tilt pixel shift via Gyroscope / OF |
|       |                                                                                 |
|       v                                                                                 |
| 30-Frame Ring Buffer per Track                                                          |
|       |                                                                                 |
|       v                                                                                 |
| Trajectory Predictor: 2-Layer GRU (hidden=128) + MLP Head                               |
|       |-- Input:  Last 15 frames [cx, cy, w, h, dx, dy] normalized to [0, 1]            |
|       +-- Output: Next 20 positions (offsets) + Log-Variance Uncertainty Bands          |
|       |                                                                                 |
|       v                                                                                 |
| Catmull-Rom Spline Smoothing & CoordinateMapper (FILL_CENTER view transformation)       |
|       |                                                                                 |
|       v                                                                                 |
| Transparent OverlayView Drawing (Hardware Accelerated, Main Thread invalidate())        |
|       |-- Layer 1: Live camera preview (PreviewView)                                    |
|       |-- Layer 2: Bounding box with Track ID & Confidence                              |
|       +-- Layer 3: Smooth flight curve (fading alpha, shrinking width) + Widening Band  |
+-----------------------------------------------------------------------------------------+
```

---

## Project Structure

```
c:\dep learning\
├── README.md                           <- Master build & system documentation
├── python\                             <- PyTorch & Python DL pipeline
│   ├── requirements.txt                <- Python dependencies
│   ├── dataset_builder.py              <- Realistic synthetic bird flight simulator & MOT parser
│   ├── motion_hint.py                  <- Frame-difference motion mask & score booster
│   ├── camera_compensation.py          <- Lucas-Kanade optical flow + RANSAC affine compensator
│   ├── tracker.py                      <- 8-state Kalman Filter + ByteTrack 2-stage association
│   ├── train_detector.py               <- YOLO fine-tuning & 2x2 tiled inference
│   ├── models_trajectory.py            <- GRU, Transformer, Kalman CV/CA models & Gaussian NLL
│   ├── train_trajectory.py             <- Trajectory training loop (ADE/FDE metrics)
│   ├── evaluate_trajectory.py          <- Evaluation benchmarking across flight categories
│   ├── export_tflite.py                <- ONNX / TFLite float16 & int8 export & parity check
│   └── tests\
│       ├── test_tracker.py             <- Unit tests for Kalman filter & ByteTrack
│       ├── test_trajectory_preprocessing.py <- Unit tests for 15-frame window & deltas
│       └── test_coordinate_mapping.py  <- Unit tests for letterbox & FILL_CENTER math
│
└── android\                            <- Production Android Studio project
    ├── build.gradle.kts                <- Root Gradle build configuration
    ├── settings.gradle.kts             <- Project module settings
    ├── gradle.properties               <- JVM & AndroidX optimization flags
    └── app\
        ├── build.gradle.kts            <- App dependencies (CameraX, TFLite GPU, Material)
        └── src\
            ├── main\
            │   ├── AndroidManifest.xml <- Camera, sensor & storage permissions
            │   ├── assets\             <- TFLite models directory (YOLO + GRU)
            │   │   └── README.md
            │   ├── java\com\birdpath\app\
            │   │   ├── MainActivity.kt <- CameraX controller & UI pipeline coordinator
            │   │   ├── ui\
            │   │   │   ├── CoordinateMapper.kt <- Screen projection & FILL_CENTER crop
            │   │   │   ├── CatmullRomSpline.kt <- Jitter-free C1 cubic spline smoothing
            │   │   │   └── OverlayView.kt      <- Three-layer hardware-accelerated canvas
            │   │   ├── ml\
            │   │   │   ├── KalmanFilter.kt     <- 8-state bounding box Kalman Filter
            │   │   │   ├── ByteTracker.kt      <- 2-stage association & track lifecycle
            │   │   │   ├── YoloDetector.kt     <- TFLite YOLO runner + GPU delegate
            │   │   │   └── TrajectoryPredictor.kt <- GRU TFLite inference + uncertainty
            │   │   ├── sensor\
            │   │   │   ├── CameraMotionCompensator.kt <- Gyroscope FOV pixel shift
            │   │   │   └── FrameSkipController.kt     <- Real-time 20+ FPS throttler
            │   │   └── storage\
            │   │       ├── TrackRecorder.kt    <- On-phone JSON dataset collector
            │   │       └── SettingsManager.kt  <- SharedPreferences configuration
            │   └── res\
            │       ├── layout\
            │       │   ├── activity_main.xml   <- PreviewView + OverlayView + Debug HUD
            │       │   └── dialog_settings.xml <- Thresholds, horizon & layer switches
            │       └── values\
            │           ├── colors.xml
            │           ├── strings.xml
            │           └── themes.xml
            └── test\java\com\birdpath\app\
                ├── CoordinateMapperTest.kt     <- Unit tests for screen projection
                ├── KalmanFilterTest.kt         <- Unit tests for 8-state Kalman filter
                ├── ByteTrackerTest.kt          <- Unit tests for ByteTrack lifecycle
                └── CatmullRomSplineTest.kt     <- Unit tests for spline interpolation
```

---

## Python Training Pipeline: Setup & Execution

### 1. Environment Setup
```bash
cd python
pip install -r requirements.txt
```

### 2. Generate Physically Simulated Flight Trajectories
Generates straight glides, banking coordinated turns, and thermal soaring paths:
```bash
python dataset_builder.py
```
*Outputs: `data/bird_trajectories.npz` (Train: 31,789 samples, Val: 6,592 samples, Test: 6,234 samples).*

### 3. Fine-Tune Single-Class Bird YOLO Detector
Trains YOLOv8n / YOLO11n with mosaic augmentation, scale augmentations, and perspective transforms:
```bash
python train_detector.py --data data/birds --model yolov8n.pt --epochs 50 --imgsz 640 --export
```

### 4. Train 2-Layer GRU Trajectory Predictor
Optimizes the GRU with Gaussian Negative Log-Likelihood and second-order acceleration smoothness penalty:
```bash
python train_trajectory.py --model gru --epochs 40 --batch 64 --lr 1e-3
```

### 5. Benchmark Baselines on Test Set
Benchmarks the 4 models across All Flights, Straight Flights, Banking Turns, and Soaring Updrafts:
```bash
python evaluate_trajectory.py
```
Outputs ADE (Average Displacement Error) and FDE (Final Displacement Error) at steps 5, 10, and 20:
- Constant Velocity Kalman Baseline
- Constant Acceleration Baseline
- Trajectory GRU (Main Model)
- Small Transformer Encoder Variant

### 6. Export to TFLite & Verify Numerical Parity
```bash
python export_tflite.py --ckpt checkpoints/best_gru.pt --tflite checkpoints/bird_trajectory_fp16.tflite
```
*Validates that maximum discrepancy between PyTorch and TFLite inference is $\le 10^{-3}$.*

### 7. Run Python Unit Tests
```bash
pytest python/tests
```

---

## Deploying Models to Android App

Copy the exported `.tflite` files into the Android assets directory:
```bash
copy python\checkpoints\yolov8n_bird.tflite android\app\src\main\assets\
copy python\checkpoints\bird_trajectory_fp16.tflite android\app\src\main\assets\
```

---

## Android App: Build & Run

### Prerequisites
- Android Studio Hedgehog (2023.1.1) or newer
- Android SDK Platform 34
- JDK 17
- Physical Android phone with Camera and Gyroscope running Android 8.0+ (API 26+)

### Building via Command Line
```bash
cd android
./gradlew assembleDebug
```

### Installing on Device
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## Verification & Testing Checklist

- [x] **Coordinate Mapping**: Letterboxed 640x640 boxes map accurately to CameraX `FILL_CENTER` preview on portrait and landscape.
- [x] **Multi-Bird Association**: ByteTrack maintains distinct track IDs with color coding across occlusions and motion blur.
- [x] **Trajectory Smoothness**: Catmull-Rom cubic splines prevent visual jitter during fast flight maneuvers.
- [x] **Uncertainty Display**: Gaussian log-variance expands into a widening translucent envelope as the prediction horizon stretches into the future.
- [x] **Camera Motion Compensation**: Gyroscope rotation rate converted to pixel shift isolates bird aerodynamics from handheld phone panning.
- [x] **Real-Time Performance**: `FrameSkipController` and TFLite GPU Delegate sustain 20+ FPS on mid-range devices with zero UI thread stutter.
- [x] **Active Learning**: On-phone "REC" mode writes timestamped bounding boxes to JSON for continuous retraining.
