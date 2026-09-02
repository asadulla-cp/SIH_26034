import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

from .config import MAX_IMAGE_PX, MAX_UPLOAD_MB, UPLOAD_DIR


class ImageError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def assess_quality(img: Image.Image) -> float:
    gray = ImageOps.grayscale(img.resize((320, 320)))
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    std = stat.stddev[0]
    brightness = 1.0 - abs(mean - 128) / 128
    contrast = min(std / 60.0, 1.0)
    return round(max(0.05, min(1.0, 0.45 * brightness + 0.55 * contrast)), 3)


def preprocess_upload(data: bytes, filename: str) -> dict:
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ImageError("image_too_large", f"Image exceeds {MAX_UPLOAD_MB} MB limit.")
    try:
        from io import BytesIO

        img = Image.open(BytesIO(data))
        img.load()
    except Exception:
        raise ImageError("invalid_image", "The file is not a readable image (PNG/JPEG/WebP).") from None

    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_IMAGE_PX:
        img.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX))
    quality = assess_quality(img)

    processed = ImageOps.autocontrast(img, cutoff=1)
    processed = ImageEnhance.Sharpness(processed).enhance(1.15)
    if quality < 0.45:
        processed = processed.filter(ImageFilter.UnsharpMask(radius=1.5, percent=140, threshold=3))

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem[:40] or "pack"
    orig_path = UPLOAD_DIR / f"{stem}_orig.jpg"
    proc_path = UPLOAD_DIR / f"{stem}_proc.jpg"
    # unique names
    i = 0
    while orig_path.exists():
        i += 1
        orig_path = UPLOAD_DIR / f"{stem}_{i}_orig.jpg"
        proc_path = UPLOAD_DIR / f"{stem}_{i}_proc.jpg"
    img.save(orig_path, "JPEG", quality=90)
    processed.save(proc_path, "JPEG", quality=92)
    return {
        "original_path": str(orig_path),
        "processed_path": str(proc_path),
        "width": img.size[0],
        "height": img.size[1],
        "quality": quality,
    }


def copy_demo_image(src: Path, sample_id: str) -> dict:
    img = Image.open(src).convert("RGB")
    quality = assess_quality(img)
    dest = UPLOAD_DIR / f"{sample_id}_orig.jpg"
    proc = UPLOAD_DIR / f"{sample_id}_proc.jpg"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=92)
    ImageOps.autocontrast(img).save(proc, "JPEG", quality=92)
    return {
        "original_path": str(dest),
        "processed_path": str(proc),
        "width": img.size[0],
        "height": img.size[1],
        "quality": quality,
    }
