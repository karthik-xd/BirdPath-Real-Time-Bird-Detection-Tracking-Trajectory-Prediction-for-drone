# BirdPath // Computer Learning Studio (YouTube Web UI)

This studio allows you to train and monitor the Bird Flight Trajectory Prediction model directly on your computer from **YouTube videos** or local clips via an interactive Web UI.

---

## 3-Layer Real-Time Monitor

The Web UI features a real-time monitor rendering:
* **Layer 1: Video Playing** - The live video stream at user-selected pixel quality (e.g. 720p, 1080p, 480p, 360p, or best available).
* **Layer 2: Boxing the Bird** - Bounding box around each bird with track ID, confidence score, and color-coded identification.
* **Layer 3: Flight Paths** - 
  * 🟢 **Predicted Flight Path**: The future trajectory line forecasted by the 2-layer GRU neural network.
  * 🟣 **Actual Flight Path**: The ground-truth trajectory line the bird actually moves in the video.
  * 🔵 **Uncertainty Band**: Widening Gaussian variance envelope.

**Joined View = Layer 1 + Layer 2 + Layer 3**

### Dynamic Visibility Toggles
You can switch OFF/ON Layer 1, Layer 2, or Layer 3 independently from the checkboxes on the monitor in real time:
* **Switching OFF Layer 1 (Video)**: Shows a clean, high-contrast dark telemetry studio grid with only the bounding boxes and trajectory lines floating.
* **Switching OFF Layer 2 (Boxes)**: Hides the bounding boxes and labels to focus exclusively on flight paths.
* **Switching OFF Layer 3 (Flight Paths)**: Hides the predicted and actual lines to focus on raw detections.

---

## Continuous Online Learning

While the video plays:
1. Birds are detected with YOLO and tracked with ByteTracker + Kalman Filtering.
2. For every bird, a 15-frame history window is fed into the GRU model to forecast the next 20 positions.
3. As the video continues playing for 20 more frames, the bird's **actual future positions** become known.
4. An online training step runs backpropagation (`loss.backward()`, `optimizer.step()`) comparing the predicted path against the actual flight path.
5. The live dashboard displays updating **Loss**, **ADE@20**, **FDE@20**, and **Samples Learned**.
6. Click **"Save Learned Model Checkpoint"** at any time to export the updated weights to `checkpoints/learned_bird_gru.pt`.

---

## How to Run

### Option 1: Double-Click Batch File
Double-click:
```
C:\dep learning\computer learning\run_web_ui.bat
```

### Option 2: Command Line
```powershell
cd "C:\dep learning\computer learning"
python server.py
```
Then open your web browser to:
👉 **`http://localhost:8000`**
