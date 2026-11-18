"""
Step 1 of the dataset pipeline: download the raw datasets.

  * Oxford-IIIT Pets  -> cat and dog photos (with official species labels)
  * COCO 2017 val     -> everyday photos used for the "other" class
                         (+ its annotation file, so we can REMOVE photos
                          that contain cats or dogs)

Everything goes into training/raw/  (ignored by Git, ~2 GB).

Run from the project root:
    python training/download_data.py
"""

import zipfile
from pathlib import Path

from torchvision.datasets import OxfordIIITPet
from torchvision.datasets.utils import download_url

RAW_DIR = Path(__file__).parent / "raw"

COCO_IMAGES_URL = "http://images.cocodataset.org/zips/val2017.zip"
COCO_ANNOT_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"


def download_pets() -> None:
    """torchvision knows the official URL + checksum, so we let it download."""
    print("\n[1/2] Oxford-IIIT Pets")
    OxfordIIITPet(root=str(RAW_DIR), download=True)
    print("      ->", RAW_DIR / "oxford-iiit-pet")


def download_coco() -> None:
    print("\n[2/2] COCO 2017 validation images + annotations")
    coco_dir = RAW_DIR / "coco"
    coco_dir.mkdir(parents=True, exist_ok=True)

    # Images: 5,000 photos (~780 MB zip)
    images_dir = coco_dir / "val2017"
    if not images_dir.exists():
        download_url(COCO_IMAGES_URL, str(coco_dir))
        print("      extracting images ...")
        with zipfile.ZipFile(coco_dir / "val2017.zip") as zf:
            zf.extractall(coco_dir)
    else:
        print("      images already extracted, skipping")

    # Annotations (~240 MB zip). We only need ONE file from it.
    annot_file = coco_dir / "annotations" / "instances_val2017.json"
    if not annot_file.exists():
        download_url(COCO_ANNOT_URL, str(coco_dir))
        print("      extracting instances_val2017.json ...")
        with zipfile.ZipFile(coco_dir / "annotations_trainval2017.zip") as zf:
            zf.extract("annotations/instances_val2017.json", coco_dir)
    else:
        print("      annotations already extracted, skipping")

    print("      ->", coco_dir)


if __name__ == "__main__":
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    download_pets()
    download_coco()
    print("\nDone. Next: python training/preprocess.py")
