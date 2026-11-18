"""
Upload validation and storage.

Checks, in order:
  1. size <= MAX_UPLOAD_MB (read at most limit+1 bytes, so huge uploads are cut off)
  2. the bytes really are a JPEG / PNG / WEBP (we look at the file content, not the name)
  3. the image is not corrupted and not absurdly large in pixels ("decompression bomb")
Then the image is re-saved as JPEG. Re-encoding strips hidden metadata such as GPS location.
"""

import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000  # 40 megapixels


async def read_and_validate(file: UploadFile, max_bytes: int) -> Image.Image:
    data = await file.read(max_bytes + 1)
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
    if len(data) > max_bytes:
        raise HTTPException(
            413,  # "Content Too Large"
            f"File is too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
        )
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            if fmt not in ALLOWED_FORMATS:
                raise HTTPException(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    "Unsupported image type. Please upload a JPEG, PNG or WEBP image.",
                )
            if probe.width * probe.height > MAX_PIXELS:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image dimensions are too large.")
            probe.verify()  # structural check
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image)  # fix phone photo rotation
        image = image.convert("RGB")  # fully decodes -> catches truncated files
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "The file is not a valid image or is corrupted."
        )
    return image


def save_image(image: Image.Image, upload_dir: Path, user_id: uuid.UUID) -> str:
    """Save under uploads/<user_id>/<random>.jpg and return the path RELATIVE to upload_dir."""
    folder = upload_dir / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"  # random name: never trust the user's file name
    image.save(folder / name, "JPEG", quality=90)
    return f"{user_id}/{name}"
