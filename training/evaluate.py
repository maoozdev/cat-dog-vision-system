"""
Phase 3 - Evaluate the trained model and tune the confidence threshold.

  1. Tune the confidence threshold on the VALIDATION set (never on test).
     Rule used by the app: if the top probability < threshold -> answer "other"
     (shown to users as "Neither / Unknown").
  2. Measure the model ONCE on the untouched TEST set:
     accuracy, precision, recall, F1 (per class + macro), confusion matrix.
  3. Plot training curves from history.csv.
  4. Write the tuned threshold into models/cat_dog_model.pth.

Outputs (training/outputs/):
  evaluation_report.md, evaluation_report.json,
  confusion_matrix.png, training_curves.png

Run from the project root (after train.py):
    python training/evaluate.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             ConfusionMatrixDisplay, f1_score)
from torch.utils.data import DataLoader
from torchvision import datasets

from train import DATA_DIR, MODEL_PATH, OUT_DIR, build_model, eval_transform


@torch.no_grad()
def predict_split(model, split: str) -> tuple[np.ndarray, np.ndarray]:
    """Return (probabilities [N,3], true labels [N]) for one dataset split."""
    ds = datasets.ImageFolder(DATA_DIR / split, transform=eval_transform())
    dl = DataLoader(ds, batch_size=64, num_workers=2)
    probs, labels = [], []
    for images, y in dl:
        probs.append(torch.softmax(model(images), dim=1))
        labels.append(y)
    return torch.cat(probs).numpy(), torch.cat(labels).numpy()


def apply_threshold(probs: np.ndarray, threshold: float, other_idx: int) -> np.ndarray:
    """argmax prediction, but low-confidence predictions become 'other'."""
    preds = probs.argmax(1)
    preds[probs.max(1) < threshold] = other_idx
    return preds


def tune_threshold(probs, labels, other_idx) -> tuple[float, list[dict]]:
    """Pick the threshold with the best macro-F1 on validation; ties -> the higher (safer) one."""
    rows = []
    for t in np.round(np.arange(0.34, 0.991, 0.01), 2):
        preds = apply_threshold(probs, t, other_idx)
        rows.append({"threshold": float(t),
                     "macro_f1": f1_score(labels, preds, average="macro"),
                     "accuracy": accuracy_score(labels, preds),
                     "unknown_rate": float((probs.max(1) < t).mean())})
    best = max(rows, key=lambda r: (round(r["macro_f1"], 4), r["threshold"]))
    return best["threshold"], rows


def metrics(labels, preds, class_names) -> dict:
    rep = classification_report(labels, preds, target_names=class_names,
                                output_dict=True, zero_division=0)
    return {"accuracy": rep["accuracy"],
            "macro_precision": rep["macro avg"]["precision"],
            "macro_recall": rep["macro avg"]["recall"],
            "macro_f1": rep["macro avg"]["f1-score"],
            "per_class": {c: {k: rep[c][k] for k in ("precision", "recall", "f1-score", "support")}
                          for c in class_names},
            "confusion_matrix": confusion_matrix(labels, preds).tolist()}


def plot_curves(history: pd.DataFrame, path: Path) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    for col, name in (("train_loss", "train"), ("val_loss", "validation")):
        a1.plot(history.epoch, history[col], marker="o", label=name)
    for col, name in (("train_acc", "train"), ("val_acc", "validation")):
        a2.plot(history.epoch, history[col], marker="o", label=name)
    switch = history[history.stage == "finetune"].epoch.min()
    for ax, title in ((a1, "Loss"), (a2, "Accuracy")):
        if not np.isnan(switch):
            ax.axvline(switch - 0.5, color="grey", ls="--", lw=1)
            ax.text(switch - 0.4, ax.get_ylim()[1], " fine-tune →", va="top", fontsize=8)
        ax.set_title(title); ax.set_xlabel("epoch"); ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(path, dpi=100)


def plot_confusion(cm_raw, cm_thr, class_names, threshold, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, cm, title in ((axes[0], cm_raw, "Test set - argmax"),
                          (axes[1], cm_thr, f"Test set - threshold {threshold:.2f}")):
        ConfusionMatrixDisplay(np.array(cm), display_labels=class_names).plot(
            ax=ax, cmap="Blues", colorbar=False, values_format="d")
        ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=100)


def main() -> None:
    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    class_names = ckpt["class_names"]
    other_idx = class_names.index("other")
    model = build_model(len(class_names), pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    print(f"Loaded {MODEL_PATH.name}: version {ckpt['model_version']}, epoch {ckpt['epoch']}")

    # 1) Threshold tuning on VALIDATION
    val_probs, val_labels = predict_split(model, "val")
    threshold, sweep = tune_threshold(val_probs, val_labels, other_idx)
    val_best = next(r for r in sweep if r["threshold"] == threshold)
    print(f"Validation: tuned threshold = {threshold:.2f} "
          f"(macro-F1 {val_best['macro_f1']:.4f}, unknown rate {val_best['unknown_rate']:.1%})")

    # 2) One-time measurement on TEST
    test_probs, test_labels = predict_split(model, "test")
    raw = metrics(test_labels, test_probs.argmax(1), class_names)
    thr = metrics(test_labels, apply_threshold(test_probs, threshold, other_idx), class_names)
    print("\nTEST classification report (with threshold):")
    print(classification_report(test_labels, apply_threshold(test_probs, threshold, other_idx),
                                target_names=class_names, digits=4))

    # 3) Plots
    history = pd.read_csv(OUT_DIR / "history.csv")
    plot_curves(history, OUT_DIR / "training_curves.png")
    plot_confusion(raw["confusion_matrix"], thr["confusion_matrix"], class_names, threshold,
                   OUT_DIR / "confusion_matrix.png")

    # 4) Save results + threshold into the checkpoint
    report = {"model_version": ckpt["model_version"], "checkpoint_epoch": ckpt["epoch"],
              "class_names": class_names, "test_images": int(len(test_labels)),
              "confidence_threshold": threshold, "threshold_tuned_on": "validation",
              "test_argmax": raw, "test_with_threshold": thr}
    (OUT_DIR / "evaluation_report.json").write_text(json.dumps(report, indent=2))
    write_markdown(report, history, OUT_DIR / "evaluation_report.md")

    ckpt["confidence_threshold"] = threshold
    ckpt["test_accuracy"] = thr["accuracy"]
    torch.save(ckpt, MODEL_PATH)
    print(f"Saved threshold {threshold:.2f} into {MODEL_PATH}")
    print(f"Reports + plots in {OUT_DIR}")


def write_markdown(r: dict, history: pd.DataFrame, path: Path) -> None:
    def table(m):
        lines = ["| class | precision | recall | F1 | images |", "|---|---|---|---|---|"]
        for c, v in m["per_class"].items():
            lines.append(f"| {c} | {v['precision']:.4f} | {v['recall']:.4f} | "
                         f"{v['f1-score']:.4f} | {int(v['support'])} |")
        lines.append(f"| **macro avg** | {m['macro_precision']:.4f} | {m['macro_recall']:.4f} | "
                     f"{m['macro_f1']:.4f} | |")
        return "\n".join(lines)

    best = history.loc[history.val_acc.idxmax()]
    path.write_text(f"""# Evaluation report - model v{r['model_version']}

Model: MobileNetV3-Small (ImageNet pretrained), fine-tuned for {r['class_names']}.
Best checkpoint: epoch {int(best.epoch)} (validation accuracy {best.val_acc:.4f}).
Test set: {r['test_images']} untouched images (balanced).

## Test results with confidence threshold {r['confidence_threshold']:.2f}
(threshold tuned on the validation set; low-confidence answers become "other")

**Accuracy: {r['test_with_threshold']['accuracy']:.4f}**

{table(r['test_with_threshold'])}

## Test results without threshold (plain argmax)

**Accuracy: {r['test_argmax']['accuracy']:.4f}**

{table(r['test_argmax'])}

## Plots
![confusion matrix](confusion_matrix.png)
![training curves](training_curves.png)
""", encoding="utf-8")


if __name__ == "__main__":
    main()
