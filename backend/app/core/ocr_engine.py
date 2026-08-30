"""
OCR engine wrapper. Uses pytesseract (Tesseract) for real OCR with word-level
bounding boxes and confidences. If tesseract is unavailable at runtime for any
reason, falls back to a deterministic "OCR unavailable" state rather than crashing,
so the rest of the pipeline (rule engine, UI, demo mode) keeps working.
"""
from typing import List, Dict
import numpy as np

try:
    import pytesseract
    from pytesseract import Output
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


def run_ocr(bgr_image: np.ndarray) -> Dict:
    """
    Returns {"available": bool, "words": [ {text, confidence(0-1), box:{x,y,w,h}} ]}
    """
    if not TESSERACT_AVAILABLE:
        return {"available": False, "words": [], "error": "OCR engine not available in this environment."}

    try:
        data = pytesseract.image_to_data(bgr_image, output_type=Output.DICT, config="--psm 11")
    except Exception as e:
        return {"available": False, "words": [], "error": f"OCR execution failed: {type(e).__name__}"}

    words = []
    n = len(data.get("text", []))
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        if conf < 0:
            continue  # tesseract uses -1 for non-text regions
        words.append({
            "text": text,
            "confidence": round(conf / 100.0, 3),
            "box": {
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "w": int(data["width"][i]),
                "h": int(data["height"][i]),
            },
        })
    return {"available": True, "words": words}
