"""
Loads the trained model ONCE and classifies PIL images.

All preprocessing settings (image size, normalization, class names, threshold)
are read from the checkpoint saved by training/train.py, so the backend always
matches what the model was trained with.
"""

import logging
import threading
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

logger = logging.getLogger(__name__)


class CatDogClassifier:
    def __init__(self, model_path: Path, threshold_override: float | None = None):
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        ckpt = torch.load(model_path, map_location="cpu", weights_only=False)

        if ckpt["architecture"] != "mobilenet_v3_small":
            raise ValueError(f"Unsupported architecture {ckpt['architecture']}")
        self.class_names: list[str] = ckpt["class_names"]
        self.version: str = ckpt["model_version"]
        self.threshold: float = (
            threshold_override if threshold_override is not None else ckpt["confidence_threshold"]
        )
        self.other_label = "other"

        # Same network shape as training, then load the learned weights.
        model = models.mobilenet_v3_small(weights=None)
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(self.class_names))
        model.load_state_dict(ckpt["model_state"])
        model.eval()  # inference mode: dropout off, BatchNorm uses saved statistics
        self.model = model

        norm = ckpt["normalization"]
        self.transform = transforms.Compose([
            transforms.Resize(ckpt["resize_size"]),
            transforms.CenterCrop(ckpt["image_size"]),
            transforms.ToTensor(),
            transforms.Normalize(norm["mean"], norm["std"]),
        ])
        self._lock = threading.Lock()  # one inference at a time keeps CPU usage predictable
        logger.info("model loaded", extra={"model_version": self.version, "event": "model_loaded"})

    @torch.inference_mode()
    def predict(self, image: Image.Image) -> dict:
        x = self.transform(image.convert("RGB")).unsqueeze(0)  # shape [1, 3, 224, 224]
        with self._lock:
            probs = torch.softmax(self.model(x), dim=1)[0]
        probabilities = {name: round(float(p), 6) for name, p in zip(self.class_names, probs)}

        top_idx = int(probs.argmax())
        confidence = float(probs[top_idx])
        label = self.class_names[top_idx]
        low_confidence = confidence < self.threshold
        if low_confidence:
            label = self.other_label  # unsure -> "Neither / Unknown"

        return {
            "label": label,
            "confidence": round(confidence, 6),
            "probabilities": probabilities,
            "low_confidence": low_confidence,
            "threshold": self.threshold,
            "model_version": self.version,
        }
