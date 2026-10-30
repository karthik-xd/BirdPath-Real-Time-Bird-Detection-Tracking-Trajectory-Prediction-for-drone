"""
train_detector.py
Fine-tunes YOLOv8n / YOLO11n for single-class bird detection with mosaic,
scale augmentations, and exports to float16 / int8 TFLite.
"""

import argparse
import os
import yaml
import numpy as np


def create_dataset_yaml(data_dir: str, yaml_out: str = "bird_detector.yaml"):
    """Creates a standard YOLO dataset YAML configuration file."""
    config = {
        "path": os.path.abspath(data_dir),
        "train": "images/train",
        "val": "images/val",
        "names": {0: "bird"},
    }
    with open(yaml_out, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Created dataset config at {yaml_out}")
    return yaml_out


def train_yolo(
    data_yaml: str,
    model_name: str = "yolov8n.pt",
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 16,
    project: str = "runs/detect",
    name: str = "bird_finetune",
):
    """
    Fine-tunes YOLO model on bird dataset with augmentations optimized for small birds.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        raise ImportError(
            "ultralytics is required for YOLO training. Install with: pip install ultralytics"
        )

    model = YOLO(model_name)

    # Train with mosaic and strong scale augmentation for small bird precision
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=project,
        name=name,
        # Augmentations for small bird detection
        mosaic=1.0,
        scale=0.5,
        degrees=10.0,
        fliplr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        close_mosaic=10,
        workers=4,
    )

    best_weights = os.path.join(project, name, "weights", "best.pt")
    print(f"Training completed. Best weights saved at: {best_weights}")
    return best_weights


def export_yolo_to_tflite(weights_path: str, imgsz: int = 640):
    """
    Exports trained YOLO weights to TFLite (Float16 first, then Int8).
    """
    from ultralytics import YOLO

    model = YOLO(weights_path)

    # 1. Export Float16 TFLite
    print("Exporting Float16 TFLite...")
    f16_export = model.export(
        format="tflite", imgsz=imgsz, half=True, int8=False, nms=True
    )
    print(f"Float16 TFLite exported: {f16_export}")

    # 2. Export Int8 Quantized TFLite (with representative dataset)
    print("Exporting Int8 Quantized TFLite...")
    int8_export = model.export(
        format="tflite", imgsz=imgsz, half=False, int8=True, nms=True
    )
    print(f"Int8 TFLite exported: {int8_export}")


class TiledInference:
    """
    Performs 2x2 tiled inference with overlap to detect tiny birds far away.
    Splits 1920x1080 into overlapping 640x640 crops, runs YOLO, and merges boxes with NMS.
    """

    def __init__(self, detector_func, crop_size: int = 640, overlap: float = 0.2):
        self.detector_func = detector_func
        self.crop_size = crop_size
        self.overlap = overlap

    def infer_tiled(
        self, frame_bgr: np.ndarray, conf_thresh: float = 0.25
    ) -> list:
        h, w = frame_bgr.shape[:2]
        step = int(self.crop_size * (1.0 - self.overlap))
        all_boxes = []

        y_coords = list(range(0, h - self.crop_size + 1, step))
        if len(y_coords) == 0 or y_coords[-1] + self.crop_size < h:
            y_coords.append(max(0, h - self.crop_size))

        x_coords = list(range(0, w - self.crop_size + 1, step))
        if len(x_coords) == 0 or x_coords[-1] + self.crop_size < w:
            x_coords.append(max(0, w - self.crop_size))

        for y in y_coords:
            for x in x_coords:
                crop = frame_bgr[y : y + self.crop_size, x : x + self.crop_size]
                dets = self.detector_func(crop, conf_thresh)
                for cx_c, cy_c, bw, bh, score in dets:
                    # Translate to global coordinates
                    all_boxes.append((cx_c + x, cy_c + y, bw, bh, score))

        # Merge overlapping detections across tiles
        return self._nms_global(all_boxes, iou_thresh=0.5)

    def _nms_global(self, boxes, iou_thresh=0.5):
        if len(boxes) == 0:
            return []
        from tracker import bbox_iou

        boxes_sorted = sorted(boxes, key=lambda b: b[4], reverse=True)
        picked = []
        while len(boxes_sorted) > 0:
            best = boxes_sorted.pop(0)
            picked.append(best)
            boxes_sorted = [
                b
                for b in boxes_sorted
                if bbox_iou(np.array(best[:4]), np.array(b[:4])) < iou_thresh
            ]
        return picked


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bird YOLO Detector Fine-Tuning")
    parser.add_argument("--data", type=str, default="data/birds", help="Path to bird dataset")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Pretrained model")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--export", action="store_true", help="Export to TFLite after training")
    args = parser.parse_args()

    yaml_path = create_dataset_yaml(args.data)
    best_weights = train_yolo(
        data_yaml=yaml_path,
        model_name=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
    )
    if args.export:
        export_yolo_to_tflite(best_weights, imgsz=args.imgsz)
