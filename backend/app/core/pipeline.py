import cv2
import numpy as np
import datetime
from dataclasses import asdict
from .preprocessing import preprocess_pipeline
from .ocr_engine import run_ocr
from .field_extraction import extract_fields
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from backend.rules.rule_engine import get_rule_engine


class PipelineError(Exception):
    pass


def run_full_pipeline(image_bytes: bytes, is_imported: bool = False) -> dict:
    """
    UPLOAD -> PREPROCESS -> OCR -> EXTRACT -> VALIDATE -> RESULT
    Raises PipelineError with a safe, user-facing message on any failure.
    Never lets a raw exception/stack trace propagate to the API layer.
    """
    if not image_bytes or len(image_bytes) < 100:
        raise PipelineError("The uploaded file is empty or not a valid image.")

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise PipelineError("The uploaded file could not be read as an image. Please upload a JPG or PNG.")

    h, w = bgr.shape[:2]
    if h * w > 40_000_000:
        raise PipelineError("Image is too large to process. Please upload an image under ~40 megapixels.")
    if h < 20 or w < 20:
        raise PipelineError("Image is too small to process.")

    try:
        pre = preprocess_pipeline(bgr)
    except Exception:
        raise PipelineError("Image preprocessing failed. The file may be corrupted.")

    ocr_result = run_ocr(pre["processed_image"])

    quality = dict(pre["quality"])
    image_quality_warnings = list(quality["warnings"])

    if not ocr_result["available"]:
        image_quality_warnings.append("OCR engine unavailable — falling back to empty extraction (all fields will need manual entry/review).")
        words = []
    else:
        words = ocr_result["words"]
        if len(words) == 0:
            image_quality_warnings.append("No readable text detected on the package. Check image focus and framing.")

    extracted_fields = extract_fields(words)

    engine = get_rule_engine()
    validation_results = engine.validate_fields(extracted_fields, is_imported=is_imported)
    score = engine.compute_score(validation_results)
    overall_status = engine.overall_status(validation_results)

    return {
        "created_at": datetime.datetime.utcnow().isoformat(),
        "ruleset_version": engine.ruleset_version,
        "overall_status": overall_status,
        "compliance_score": score,
        "quality": quality,
        "image_quality_warnings": image_quality_warnings,
        "perspective_corrected": pre["perspective_corrected"],
        "ocr_available": ocr_result["available"],
        "word_count": len(words),
        "extracted_fields": {k: asdict(v) for k, v in extracted_fields.items()},
        "validation_results": [asdict(r) for r in validation_results],
        "display_image": pre["display_image"],  # kept in-memory only, not serialized directly
    }
