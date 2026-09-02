from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import DEMO_DIR, SAMPLES_PATH


def load_samples() -> list[dict]:
    if not SAMPLES_PATH.exists():
        return []
    return json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))


def sample_by_id(sample_id: str) -> dict | None:
    for s in load_samples():
        if s["id"] == sample_id:
            return s
    return None


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


class OcrResult:
    def __init__(self, lines: list[dict], engine: str, available: bool):
        self.lines = lines
        self.engine = engine
        self.available = available

    def full_text(self) -> str:
        return "\n".join(x.get("text", "") for x in self.lines)


_ENGINE_CACHE = {"tried": False, "fn": None, "name": "none"}


def _try_live_ocr():
    if _ENGINE_CACHE["tried"]:
        return _ENGINE_CACHE["fn"], _ENGINE_CACHE["name"]
    _ENGINE_CACHE["tried"] = True
    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()

        def run(path: str):
            result, _ = engine(path)
            lines = []
            if not result:
                return lines
            for item in result:
                box, text, score = item[0], item[1], float(item[2])
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                from PIL import Image

                with Image.open(path) as im:
                    w, h = im.size
                lines.append({
                    "text": text,
                    "confidence": score,
                    "bbox": {
                        "x": min(xs) / w,
                        "y": min(ys) / h,
                        "w": (max(xs) - min(xs)) / w,
                        "h": (max(ys) - min(ys)) / h,
                    },
                })
            return lines

        _ENGINE_CACHE["fn"] = run
        _ENGINE_CACHE["name"] = "rapidocr"
        return run, "rapidocr"
    except Exception:
        pass
    try:
        import pytesseract
        from PIL import Image

        def run(path: str):
            im = Image.open(path)
            w, h = im.size
            data = pytesseract.image_to_data(im, output_type=pytesseract.Output.DICT)
            lines = []
            n = len(data["text"])
            for i in range(n):
                text = (data["text"][i] or "").strip()
                if not text:
                    continue
                conf = float(data["conf"][i])
                if conf < 0:
                    conf = 0
                lines.append({
                    "text": text,
                    "confidence": conf / 100.0,
                    "bbox": {
                        "x": data["left"][i] / w,
                        "y": data["top"][i] / h,
                        "w": data["width"][i] / w,
                        "h": data["height"][i] / h,
                    },
                })
            return lines

        _ENGINE_CACHE["fn"] = run
        _ENGINE_CACHE["name"] = "tesseract"
        return run, "tesseract"
    except Exception:
        pass
    return None, "none"


def run_ocr(image_path: str, sample: dict | None = None) -> OcrResult:
    if sample and sample.get("ocr_lines"):
        return OcrResult(sample["ocr_lines"], engine="demo_fixture", available=True)

    fn, name = _try_live_ocr()
    if fn:
        try:
            lines = fn(image_path)
            return OcrResult(lines, engine=name, available=True)
        except Exception:
            return OcrResult([], engine=f"{name}_failed", available=False)
    return OcrResult([], engine="unavailable", available=False)


def match_demo_by_hash(image_path: str) -> dict | None:
    try:
        digest = file_sha(Path(image_path))
    except Exception:
        return None
    for s in load_samples():
        p = DEMO_DIR.parent / s["image"] if not Path(s["image"]).is_absolute() else Path(s["image"])
        if not p.exists():
            p = DEMO_DIR / "images" / f"{s['id']}.png"
        if p.exists() and file_sha(p) == digest:
            return s
    return None
