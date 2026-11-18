"""
Phase 3 - Train a Cat / Dog / Other classifier with transfer learning.

Model : MobileNetV3-Small pretrained on ImageNet (torchvision)
Stage 1 (head)     : pretrained layers frozen, only the classifier learns   (lr 1e-3)
Stage 2 (finetune) : last few feature blocks unfrozen as well               (lr 1e-4)

Outputs
  models/cat_dog_model.pth          best checkpoint (by validation accuracy) + metadata
  training/outputs/history.csv      loss / accuracy for every epoch

Run from the project root:
    python training/train.py
"""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "training" / "dataset"
OUT_DIR = ROOT / "training" / "outputs"
MODEL_PATH = ROOT / "models" / "cat_dog_model.pth"

IMAGE_SIZE = 224
# ImageNet statistics: the pretrained weights expect inputs normalized this way.
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


# ----------------------------------------------------------------- transforms
def train_transform() -> transforms.Compose:
    """Random augmentation: every epoch sees a slightly different version of each photo."""
    return transforms.Compose([
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.6, 1.0)),  # random crop + resize
        transforms.RandomHorizontalFlip(),                            # mirror left/right
        transforms.RandomRotation(15),                                # tilt up to ±15°
        transforms.ColorJitter(0.3, 0.3, 0.3, 0.05),                  # brightness/contrast/...
        transforms.RandomApply([transforms.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.2),  # blur
        transforms.ToTensor(),                                        # PIL -> float tensor 0..1
        transforms.Normalize(MEAN, STD),
    ])


def eval_transform() -> transforms.Compose:
    """Deterministic: the SAME preprocessing is used by evaluate.py and the backend."""
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


# ---------------------------------------------------------------------- model
def build_model(num_classes: int, pretrained: bool = True) -> nn.Module:
    weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.mobilenet_v3_small(weights=weights)
    # classifier = [Linear(576,1024), Hardswish, Dropout, Linear(1024,1000)]
    # Replace the last layer: 1000 ImageNet classes -> our 3 classes.
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model


def set_trainable(model: nn.Module, unfreeze_blocks: int) -> None:
    """Freeze all feature blocks except the last `unfreeze_blocks`; classifier always trains."""
    blocks = list(model.features)
    for i, block in enumerate(blocks):
        trainable = i >= len(blocks) - unfreeze_blocks
        for p in block.parameters():
            p.requires_grad = trainable
    for p in model.classifier.parameters():
        p.requires_grad = True


def train_mode(model: nn.Module) -> None:
    """model.train(), but keep FROZEN blocks in eval mode so their BatchNorm stats don't drift."""
    model.train()
    for block in model.features:
        if not any(p.requires_grad for p in block.parameters()):
            block.eval()


# --------------------------------------------------------------- train / eval
def run_epoch(model, loader, criterion, optimizer=None) -> tuple[float, float]:
    """One pass over `loader`. Trains if an optimizer is given, otherwise just measures."""
    training = optimizer is not None
    total_loss, correct, seen = 0.0, 0, 0
    with torch.set_grad_enabled(training):
        for images, labels in loader:
            logits = model(images)
            loss = criterion(logits, labels)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * labels.size(0)
            correct += (logits.argmax(1) == labels).sum().item()
            seen += labels.size(0)
    return total_loss / seen, correct / seen


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--head-epochs", type=int, default=3)
    p.add_argument("--finetune-epochs", type=int, default=6)
    p.add_argument("--unfreeze-blocks", type=int, default=4, help="feature blocks to fine-tune")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--max-batches", type=int, default=0, help="debug: limit batches per epoch")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ImageFolder: sub-folder names become class names, sorted -> ['cat', 'dog', 'other']
    train_ds = datasets.ImageFolder(DATA_DIR / "train", transform=train_transform())
    val_ds = datasets.ImageFolder(DATA_DIR / "val", transform=eval_transform())
    if args.max_batches:  # tiny run to check the code / measure speed
        n = args.max_batches * args.batch_size
        train_ds = torch.utils.data.Subset(train_ds, torch.randperm(len(train_ds))[:n].tolist())
        val_ds = torch.utils.data.Subset(val_ds, torch.randperm(len(val_ds))[:n].tolist())
    class_names = datasets.ImageFolder(DATA_DIR / "train").classes
    print(f"classes={class_names} train={len(train_ds)} val={len(val_ds)} "
          f"threads={torch.get_num_threads()}")

    loader_kw = dict(batch_size=args.batch_size, num_workers=args.workers,
                     persistent_workers=args.workers > 0)
    train_dl = DataLoader(train_ds, shuffle=True, **loader_kw)
    val_dl = DataLoader(val_ds, shuffle=False, **loader_kw)

    model = build_model(len(class_names))
    criterion = nn.CrossEntropyLoss()

    stages = [("head", args.head_epochs, 0, 1e-3),
              ("finetune", args.finetune_epochs, args.unfreeze_blocks, 1e-4)]
    history, best_acc, epoch_no = [], -1.0, 0
    start = time.time()

    for stage, n_epochs, unfreeze, lr in stages:
        set_trainable(model, unfreeze)
        params = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.Adam(params, lr=lr)
        n_trainable = sum(p.numel() for p in params)
        print(f"\n=== Stage '{stage}': {n_epochs} epochs, lr={lr}, "
              f"trainable params={n_trainable:,} ===")

        for _ in range(n_epochs):
            epoch_no += 1
            t0 = time.time()
            train_mode(model)
            tr_loss, tr_acc = run_epoch(model, train_dl, criterion, optimizer)
            model.eval()
            va_loss, va_acc = run_epoch(model, val_dl, criterion)

            is_best = va_acc > best_acc
            if is_best:
                best_acc = va_acc
                torch.save({
                    "model_state": model.state_dict(),
                    "architecture": "mobilenet_v3_small",
                    "model_version": "1.0.0",
                    "class_names": class_names,
                    "image_size": IMAGE_SIZE,
                    "resize_size": 256,
                    "normalization": {"mean": MEAN, "std": STD},
                    "confidence_threshold": 0.5,  # placeholder; tuned on val by evaluate.py
                    "best_val_accuracy": va_acc,
                    "epoch": epoch_no,
                    "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }, MODEL_PATH)

            history.append({"epoch": epoch_no, "stage": stage, "train_loss": tr_loss,
                            "train_acc": tr_acc, "val_loss": va_loss, "val_acc": va_acc})
            pd.DataFrame(history).to_csv(OUT_DIR / "history.csv", index=False)
            print(f"epoch {epoch_no:2d} [{stage:8s}] "
                  f"train loss {tr_loss:.4f} acc {tr_acc:.4f} | "
                  f"val loss {va_loss:.4f} acc {va_acc:.4f} | "
                  f"{time.time() - t0:5.0f}s{'  <- best, saved' if is_best else ''}", flush=True)

    print(f"\nFinished in {(time.time() - start) / 60:.1f} min. "
          f"Best val accuracy {best_acc:.4f} -> {MODEL_PATH}")


if __name__ == "__main__":  # required on Windows when DataLoader uses worker processes
    main()
