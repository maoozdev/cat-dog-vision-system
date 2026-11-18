"""
Step 2 of the dataset pipeline: clean, de-duplicate, balance and split.

Input : training/raw/            (created by download_data.py)
Output: training/dataset/
          train/{cat,dog,other}/*.jpg   70 %
          val/{cat,dog,other}/*.jpg     15 %
          test/{cat,dog,other}/*.jpg    15 %
          manifest.csv                  one row per image (for auditing)
        training/outputs/dataset_samples.png   preview grid

What this script does, in order:
  1. Collect labelled image paths from both datasets.
  2. Remove corrupted / unreadable / tiny images.
  3. Remove duplicates (perceptual hash) BEFORE splitting -> no leakage.
  4. Balance classes (same number of images per class).
  5. Shuffle with a fixed seed and split 70/15/15 per class (stratified).
  6. Resize (shorter side = 256 px) and save as RGB JPEG.

Run from the project root:
    python training/preprocess.py
"""

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to file, no window needed
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageOps

TRAINING_DIR = Path(__file__).parent
CLASSES = ["cat", "dog", "other"]
SPLITS = {"train": 0.70, "val": 0.15, "test": 0.15}
MIN_SIDE = 64  # images smaller than this are useless for training


# ---------------------------------------------------------------- collecting
def collect_pets(raw: Path) -> list[dict]:
    """Oxford-IIIT Pets: annotations/list.txt has a SPECIES column (1=cat, 2=dog)."""
    root = raw / "oxford-iiit-pet"
    items = []
    for line in (root / "annotations" / "list.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        name, _class_id, species, _breed = line.split()
        items.append(
            {
                "path": root / "images" / f"{name}.jpg",
                "label": "cat" if species == "1" else "dog",
                "source": "pets",
            }
        )
    return items


def collect_coco_other(raw: Path) -> list[dict]:
    """COCO val2017 photos that contain NO cat and NO dog."""
    root = raw / "coco"
    data = json.loads((root / "annotations" / "instances_val2017.json").read_text())

    # Look the ids up by name instead of hard-coding them.
    pet_ids = {c["id"] for c in data["categories"] if c["name"] in ("cat", "dog")}
    images_with_pets = {a["image_id"] for a in data["annotations"] if a["category_id"] in pet_ids}

    items = []
    for img in data["images"]:
        if img["id"] in images_with_pets:
            continue
        items.append(
            {"path": root / "val2017" / img["file_name"], "label": "other", "source": "coco"}
        )
    print(f"  COCO: {len(data['images'])} images, {len(images_with_pets)} contain cat/dog -> excluded")
    return items


# ------------------------------------------------------------ image helpers
def load_rgb(path: Path) -> Image.Image | None:
    """Return a clean RGB image, or None if the file is corrupted / not an image."""
    try:
        with Image.open(path) as im:
            im.verify()  # checks file integrity without decoding pixels
        with Image.open(path) as im:  # verify() closes the file, so reopen
            im = ImageOps.exif_transpose(im)  # respect phone rotation metadata
            return im.convert("RGB")  # also fully decodes -> catches truncated files
    except Exception:
        return None


def dhash(img: Image.Image, size: int = 8) -> int:
    """Difference hash: identical/near-identical pictures get the same 64-bit number."""
    small = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    px = small.tobytes()  # one byte (0-255 brightness) per pixel
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (left > right)
    return bits


def resize_shorter_side(img: Image.Image, target: int) -> Image.Image:
    w, h = img.size
    scale = target / min(w, h)
    if scale >= 1:  # never upscale
        return img
    return img.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)


# --------------------------------------------------------------- main steps
def clean_and_dedupe(items: list[dict]) -> list[dict]:
    seen: dict[int, dict] = {}
    stats = Counter()
    kept = []
    for i, item in enumerate(items, 1):
        if i % 2000 == 0:
            print(f"  checked {i}/{len(items)}")
        img = load_rgb(item["path"])
        if img is None:
            stats["corrupted"] += 1
            continue
        if min(img.size) < MIN_SIDE:
            stats["too_small"] += 1
            continue
        h = dhash(img)
        if h in seen:
            stats["duplicate"] += 1
            if seen[h]["label"] != item["label"]:
                stats["duplicate_conflicting_label"] += 1
            continue
        seen[h] = item
        kept.append(item)
    print(f"  removed: {dict(stats) or 'nothing'}")
    return kept


def balance_and_split(items: list[dict], per_class: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for label in CLASSES:
        group = [it for it in items if it["label"] == label]
        rng.shuffle(group)
        group = group[:per_class]
        n = len(group)
        n_train = round(n * SPLITS["train"])
        n_val = round(n * SPLITS["val"])
        for j, it in enumerate(group):
            split = "train" if j < n_train else "val" if j < n_train + n_val else "test"
            out.append({**it, "split": split})
    return out


def write_dataset(items: list[dict], out_dir: Path, size: int) -> None:
    # Start fresh so old files from a previous run can't leak into a split.
    for split in SPLITS:
        shutil.rmtree(out_dir / split, ignore_errors=True)
        for label in CLASSES:
            (out_dir / split / label).mkdir(parents=True)

    for i, it in enumerate(items, 1):
        if i % 2000 == 0:
            print(f"  saved {i}/{len(items)}")
        img = resize_shorter_side(load_rgb(it["path"]), size)
        dest = out_dir / it["split"] / it["label"] / f"{it['source']}_{it['path'].stem}.jpg"
        img.save(dest, "JPEG", quality=95)
        it["file"] = dest.relative_to(out_dir).as_posix()


def save_preview(items: list[dict], out_dir: Path, path: Path, seed: int) -> None:
    rng = random.Random(seed)
    fig, axes = plt.subplots(len(CLASSES), 6, figsize=(12, 6.5))
    for r, label in enumerate(CLASSES):
        picks = rng.sample([it for it in items if it["label"] == label], 6)
        for c, it in enumerate(picks):
            ax = axes[r][c]
            ax.imshow(Image.open(out_dir / it["file"]))
            ax.set_title(label, fontsize=9)
            ax.axis("off")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=80)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, default=TRAINING_DIR / "raw")
    p.add_argument("--out", type=Path, default=TRAINING_DIR / "dataset")
    p.add_argument("--size", type=int, default=256, help="shorter side in pixels")
    p.add_argument("--per-class", type=int, default=0, help="0 = size of the smallest class")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    print("1) Collecting image lists")
    items = collect_pets(args.raw) + collect_coco_other(args.raw)
    print(f"  found: {dict(Counter(it['label'] for it in items))}")

    print("2-3) Removing corrupted images and duplicates")
    items = clean_and_dedupe(items)
    counts = Counter(it["label"] for it in items)
    print(f"  clean: {dict(counts)}")

    per_class = args.per_class or min(counts.values())
    print(f"4-5) Balancing to {per_class} per class and splitting 70/15/15 (seed={args.seed})")
    items = balance_and_split(items, per_class, args.seed)

    print(f"6) Resizing (shorter side {args.size}px) and saving to {args.out}")
    write_dataset(items, args.out, args.size)

    df = pd.DataFrame(
        [{"file": it["file"], "label": it["label"], "split": it["split"],
          "source": it["source"], "original": it["path"].name} for it in items]
    )
    df.to_csv(args.out / "manifest.csv", index=False)
    save_preview(items, args.out, TRAINING_DIR / "outputs" / "dataset_samples.png", args.seed)

    print("\nFinal dataset (images per split and class):")
    print(pd.crosstab(df["split"], df["label"], margins=True).loc[["train", "val", "test", "All"]])
    print(f"\nManifest: {args.out / 'manifest.csv'}")
    print(f"Preview : {TRAINING_DIR / 'outputs' / 'dataset_samples.png'}")


if __name__ == "__main__":
    main()
