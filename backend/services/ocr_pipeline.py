"""
MetaLex OCR/Vision Pipeline
IMAGE → PREPROCESS → OCR → EXTRACT → CLASSIFY → VALIDATE

This module handles:
1. Image quality assessment
2. Image preprocessing (perspective, contrast, noise)
3. OCR with bounding boxes and confidence
4. Text normalization
5. Field classification using regex + keyword matching
6. Confidence scoring
"""
import re
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional
import logging
import io

logger = logging.getLogger("metalex.ocr")

# Try to import EasyOCR
_easyocr_reader = None
_ocr_available = False

def _get_ocr_reader():
    global _easyocr_reader, _ocr_available
    if _easyocr_reader is not None:
        return _easyocr_reader
    try:
        import ssl
        import urllib.request
        # Allow downloading models on macOS without pre-installed root certificates
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context

        import easyocr
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        _ocr_available = True
        logger.info("EasyOCR initialized successfully")
        return _easyocr_reader
    except Exception as e:
        logger.warning(f"EasyOCR unavailable: {e}. Demo mode will be used.")
        _ocr_available = False
        return None


def is_ocr_available() -> bool:
    global _ocr_available
    _get_ocr_reader()
    return _ocr_available


# ──────────────────────────── Image Quality Assessment ────────────────────────
def assess_image_quality(img: np.ndarray) -> dict:
    """Assess image quality for OCR suitability."""
    issues = []
    scores = {}

    h, w = img.shape[:2]

    # Resolution check
    resolution = h * w
    if resolution < 100 * 100:
        issues.append("Extremely low resolution — OCR results may be unreliable")
        scores["resolution"] = 0.2
    elif resolution < 300 * 300:
        issues.append("Low resolution — OCR accuracy may be reduced")
        scores["resolution"] = 0.5
    elif resolution < 640 * 480:
        scores["resolution"] = 0.7
    else:
        scores["resolution"] = 1.0

    # Blur detection (Laplacian variance)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 20:
        issues.append("Image appears very blurry — text may be unreadable")
        scores["sharpness"] = 0.2
    elif laplacian_var < 80:
        issues.append("Image appears somewhat blurry")
        scores["sharpness"] = 0.5
    elif laplacian_var < 200:
        scores["sharpness"] = 0.7
    else:
        scores["sharpness"] = 1.0

    # Contrast check
    if len(img.shape) == 3:
        gray_for_contrast = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray_for_contrast = gray
    contrast = gray_for_contrast.std()
    if contrast < 20:
        issues.append("Very low contrast — text may blend with background")
        scores["contrast"] = 0.3
    elif contrast < 40:
        issues.append("Low contrast detected")
        scores["contrast"] = 0.6
    else:
        scores["contrast"] = 1.0

    # Brightness check
    brightness = gray_for_contrast.mean()
    if brightness < 40:
        issues.append("Image is very dark")
        scores["brightness"] = 0.4
    elif brightness > 220:
        issues.append("Image is overexposed")
        scores["brightness"] = 0.4
    else:
        scores["brightness"] = 1.0

    # Overall quality score
    overall = sum(scores.values()) / len(scores) if scores else 0.5

    return {
        "overall_score": round(overall, 2),
        "scores": scores,
        "issues": issues,
        "resolution": f"{w}x{h}",
        "is_suitable": overall >= 0.5,
    }


# ──────────────────────────── Image Preprocessing ─────────────────────────────
def preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better OCR:
    1. Resize if too small
    2. Denoise
    3. Contrast enhancement (CLAHE)
    4. Optional perspective correction
    """
    h, w = img.shape[:2]

    # Upscale small images
    if max(h, w) < 800:
        scale = 800 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Limit oversized images
    if max(h, w) > 4000:
        scale = 4000 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # Denoise
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    # CLAHE contrast enhancement
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(l_channel)
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return img


# ──────────────────────────── OCR Execution ───────────────────────────────────
def run_ocr(img: np.ndarray) -> list[dict]:
    """
    Run OCR on image. Returns list of detected text regions with bounding boxes.

    Each result: {
        "text": str,
        "confidence": float (0-1),
        "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
        "bbox_rect": [x_min, y_min, x_max, y_max],
    }
    """
    reader = _get_ocr_reader()
    if reader is None:
        return []

    try:
        results = reader.readtext(img)
        parsed = []
        for (bbox, text, conf) in results:
            # Convert polygon to rectangle
            pts = np.array(bbox)
            x_min, y_min = pts.min(axis=0).astype(int).tolist()
            x_max, y_max = pts.max(axis=0).astype(int).tolist()

            parsed.append({
                "text": text.strip(),
                "confidence": round(float(conf), 3),
                "bbox": [[int(p[0]), int(p[1])] for p in bbox],
                "bbox_rect": [x_min, y_min, x_max, y_max],
            })
        return parsed
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return []


# ──────────────────────────── Field Extraction ────────────────────────────────

# Keyword patterns for field classification
FIELD_PATTERNS = {
    "product_name": {
        "keywords": [],  # Product name is identified by elimination / position
        "priority": 0,
    },
    "net_quantity": {
        "keywords": [
            r"net\s*(?:wt|weight|qty|quantity|content|contents|vol|volume)",
            r"(?:net|nett)\s*:?\s*\d",
            r"\d+\s*(?:g|gm|gram|grams|kg|kilogram|ml|millilitre|l|litre|liter|litres|cm|m|mm|pieces|pcs)\b",
        ],
        "extract_pattern": r"(?:net\s*(?:wt|weight|qty|quantity|content|contents|vol|volume)\s*:?\s*)?([\d]+\.?\d*\s*(?:g|gm|gram|grams|kg|kilogram|kilograms|ml|millilitre|milliliter|l|litre|liter|litres|liters|cm|centimetre|centimeter|m|metre|meter|mm|pieces|pcs|nos|units|pairs|sheets|rolls))",
        "priority": 2,
    },
    "mrp": {
        "keywords": [
            r"(?:m\.?\s*r\.?\s*p\.?|mrp|maximum\s*retail\s*price|retail\s*price|price)",
            r"(?:₹|rs\.?|inr)\s*:?\s*[\d]",
        ],
        "extract_pattern": r"(?:m\.?\s*r\.?\s*p\.?\s*:?\s*)?(?:₹|rs\.?|inr\.?)\s*:?\s*([\d,]+\.?\d*)",
        "priority": 3,
    },
    "manufacturer": {
        "keywords": [
            r"(?:mfg|mfd|manufactured|marketed|packed|packaged|distributed|imported)\s*(?:by|&|and)?",
            r"(?:manufacturer|packer|importer|marketer)\s*:?",
        ],
        "priority": 1,
    },
    "date": {
        "keywords": [
            r"(?:mfg|mfd|manufactured|manufacturing|packed|packing|pkg|best\s*before|exp|expiry|use\s*by|import)\s*(?:date|dt|d)?",
            r"(?:date\s*of\s*(?:mfg|manufacture|manufacturing|packing|import))",
        ],
        "extract_pattern": r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}[/\-\.]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{2,4})",
        "priority": 2,
    },
    "consumer_care": {
        "keywords": [
            r"(?:consumer|customer)\s*(?:care|complaint|grievance|helpline|service|support)",
            r"(?:toll\s*free|helpline|contact\s*us|for\s*complaints)",
            r"(?:care@|support@|info@|complaints?@)",
        ],
        "priority": 2,
    },
    "country_of_origin": {
        "keywords": [
            r"(?:country\s*of\s*origin|made\s*in|product\s*of|origin\s*:?)",
        ],
        "extract_pattern": r"(?:country\s*of\s*origin|made\s*in|product\s*of)\s*:?\s*(.+?)(?:\.|$|\n)",
        "priority": 2,
    },
    "address": {
        "keywords": [
            r"(?:address|addr|regd\.?\s*off|registered\s*office|plot|sector|street|road|lane|nagar|colony|district|state|pin\s*code?|pincode|\d{6})",
        ],
        "priority": 1,
    },
    "common_name": {
        "keywords": [
            r"(?:common\s*name|generic\s*name|also\s*known\s*as)",
        ],
        "priority": 0,
    },
}


def extract_fields(ocr_results: list[dict], img_shape: tuple) -> dict[str, dict]:
    """
    Extract and classify fields from OCR results using regex + keyword matching + spatial relationships.

    Returns: {field_name: {value, normalized_value, confidence, bounding_box, source_text, extraction_method, candidates}}
    """
    if not ocr_results:
        return _empty_fields()

    # Combine all OCR text for full-text searching
    all_text = " ".join([r["text"] for r in ocr_results])
    all_text_lower = all_text.lower()

    # Initialize fields
    fields = {}

    # ── Extract each field ──
    for field_name, pattern_info in FIELD_PATTERNS.items():
        candidates = []

        for ocr_item in ocr_results:
            text = ocr_item["text"]
            text_lower = text.lower()
            conf = ocr_item["confidence"]
            bbox = ocr_item["bbox_rect"]

            score = 0.0

            # Check keyword match
            for kw in pattern_info.get("keywords", []):
                if re.search(kw, text_lower):
                    score += 0.5
                    break

            # Check extract patterns
            extract_pat = pattern_info.get("extract_pattern")
            if extract_pat:
                match = re.search(extract_pat, text_lower)
                if match:
                    score += 0.3

            if score > 0:
                candidates.append({
                    "text": text,
                    "confidence": conf,
                    "score": score + conf * 0.5,
                    "bbox": bbox,
                    "source_text": text,
                })

        # For fields with extract patterns, also try full text
        extract_pat = pattern_info.get("extract_pattern")
        if extract_pat:
            for m in re.finditer(extract_pat, all_text_lower):
                extracted_val = m.group(1) if m.groups() else m.group(0)
                # Find the OCR box that contains this text
                matching_box = _find_bbox_for_text(extracted_val, ocr_results)
                candidates.append({
                    "text": extracted_val.strip(),
                    "confidence": matching_box["confidence"] if matching_box else 0.7,
                    "score": 0.9,
                    "bbox": matching_box["bbox_rect"] if matching_box else None,
                    "source_text": m.group(0),
                })

        if candidates:
            # Rank by score
            candidates.sort(key=lambda c: c["score"], reverse=True)
            best = candidates[0]

            # Clean/normalize value
            normalized = _normalize_field_value(field_name, best["text"])

            fields[field_name] = {
                "value": best["text"],
                "normalized_value": normalized,
                "confidence": round(best["confidence"], 3),
                "bounding_box": best["bbox"],
                "source_text": best["source_text"],
                "extraction_method": "ocr_regex_keyword",
                "candidates": [
                    {"value": c["text"], "confidence": c["confidence"], "score": round(c["score"], 3)}
                    for c in candidates[:5]
                ],
            }
        else:
            fields[field_name] = {
                "value": None,
                "normalized_value": None,
                "confidence": 0.0,
                "bounding_box": None,
                "source_text": "",
                "extraction_method": "not_detected",
                "candidates": [],
            }

    # ── Product Name Heuristic ──
    # If product name not found by keywords, use the largest/most prominent text
    if not fields.get("product_name", {}).get("value"):
        product_candidate = _detect_product_name(ocr_results, fields, img_shape)
        if product_candidate:
            fields["product_name"] = product_candidate

    return fields


def _empty_fields() -> dict[str, dict]:
    """Return empty field dict when no OCR results."""
    empty = {}
    for field_name in FIELD_PATTERNS:
        empty[field_name] = {
            "value": None,
            "normalized_value": None,
            "confidence": 0.0,
            "bounding_box": None,
            "source_text": "",
            "extraction_method": "not_detected",
            "candidates": [],
        }
    return empty


def _find_bbox_for_text(text: str, ocr_results: list[dict]) -> Optional[dict]:
    """Find the OCR result that best matches the given text."""
    text_lower = text.lower().strip()
    for item in ocr_results:
        if text_lower in item["text"].lower():
            return item
    return None


def _detect_product_name(ocr_results: list[dict], existing_fields: dict, img_shape: tuple) -> Optional[dict]:
    """
    Detect product name using spatial heuristics:
    - Usually the largest text
    - Usually at the top/center of the image
    - Not already classified as another field
    """
    if not ocr_results:
        return None

    # Get texts already used for other fields
    used_texts = set()
    for field_data in existing_fields.values():
        if field_data.get("value"):
            used_texts.add(field_data["value"].lower())

    h, w = img_shape[:2] if len(img_shape) >= 2 else (1000, 1000)

    best_candidate = None
    best_score = 0

    for item in ocr_results:
        text = item["text"].strip()
        if len(text) < 2 or text.lower() in used_texts:
            continue

        # Skip items that look like numbers, dates, or prices
        if re.match(r"^[\d₹\.\,\-\/]+$", text):
            continue

        bbox = item["bbox_rect"]
        # Score based on: size, position (top of image = higher), text length
        text_height = bbox[3] - bbox[1]
        text_width = bbox[2] - bbox[0]
        area = text_height * text_width
        y_position = bbox[1] / h  # 0 = top, 1 = bottom

        score = (area / (h * w + 1)) * 3 + (1 - y_position) * 2 + min(len(text) / 30, 1)

        if score > best_score:
            best_score = score
            best_candidate = {
                "value": text,
                "normalized_value": text.title(),
                "confidence": round(item["confidence"], 3),
                "bounding_box": bbox,
                "source_text": text,
                "extraction_method": "spatial_heuristic",
                "candidates": [{"value": text, "confidence": item["confidence"], "score": round(score, 3)}],
            }

    return best_candidate


def _normalize_field_value(field_name: str, value: str) -> str:
    """Normalize field values for validation."""
    if not value:
        return ""

    value = value.strip()

    if field_name == "mrp":
        # Extract numeric part
        nums = re.findall(r"[\d,]+\.?\d*", value)
        if nums:
            return "₹" + nums[0].replace(",", "")
        return value

    elif field_name == "net_quantity":
        return value.strip()

    elif field_name == "date":
        return value.strip()

    elif field_name == "product_name":
        return value.title()

    return value


# ──────────────────────────── Annotated Image Generation ──────────────────────
def create_annotated_image(
    img: np.ndarray,
    ocr_results: list[dict],
    fields: dict[str, dict],
    violations: list[dict] | None = None,
) -> np.ndarray:
    """
    Create annotated image with:
    - OCR bounding boxes (blue)
    - Detected field labels (green)
    - Violation highlights (red)
    """
    annotated = img.copy()

    # Draw OCR boxes (light blue, thin)
    for item in ocr_results:
        bbox = item["bbox_rect"]
        cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 180, 0), 1)

    # Draw field boxes (green with labels)
    field_labels = {
        "product_name": "Product Name",
        "net_quantity": "Net Qty",
        "mrp": "MRP",
        "manufacturer": "Manufacturer",
        "date": "Date",
        "consumer_care": "Consumer Care",
        "country_of_origin": "Country of Origin",
        "address": "Address",
        "common_name": "Common Name",
    }

    violation_fields = set()
    if violations:
        for v in violations:
            violation_fields.add(v.get("field", ""))

    for field_name, field_data in fields.items():
        bbox = field_data.get("bounding_box")
        if not bbox or len(bbox) < 4:
            continue

        label = field_labels.get(field_name, field_name)
        is_violation = field_name in violation_fields

        if is_violation:
            color = (0, 0, 255)  # Red
            thickness = 3
        elif field_data.get("confidence", 0) < 0.6:
            color = (0, 165, 255)  # Orange
            thickness = 2
        else:
            color = (0, 200, 0)  # Green
            thickness = 2

        cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness)

        # Draw label background
        label_text = f"{label} ({field_data.get('confidence', 0):.0%})"
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y = max(bbox[1] - 5, th + 5)
        cv2.rectangle(annotated, (bbox[0], label_y - th - 4), (bbox[0] + tw + 4, label_y + 2), color, -1)
        cv2.putText(annotated, label_text, (bbox[0] + 2, label_y - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    return annotated


# ──────────────────────────── Full Pipeline ───────────────────────────────────
def process_image(image_path: str) -> dict:
    """
    Full OCR pipeline:
    1. Load image
    2. Quality assessment
    3. Preprocess
    4. OCR
    5. Field extraction
    6. Return structured results
    """
    import time
    start = time.time()

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        # Try with PIL for more format support
        try:
            pil_img = Image.open(image_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            return {
                "success": False,
                "error": f"Cannot load image: {str(e)}",
                "quality": {"overall_score": 0, "issues": ["Image could not be loaded"]},
                "ocr_results": [],
                "fields": _empty_fields(),
                "processing_time_ms": 0,
            }

    # Quality assessment
    quality = assess_image_quality(img)

    # Preprocess
    preprocessed = preprocess_image(img)

    # OCR
    ocr_results = run_ocr(preprocessed)

    # Field extraction
    fields = extract_fields(ocr_results, img.shape)

    # Generate annotated image
    annotated = create_annotated_image(img, ocr_results, fields)

    elapsed = int((time.time() - start) * 1000)

    return {
        "success": True,
        "quality": quality,
        "ocr_results": ocr_results,
        "fields": fields,
        "annotated_image": annotated,
        "original_image": img,
        "processing_time_ms": elapsed,
        "ocr_engine": "easyocr",
    }
