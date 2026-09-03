"""
MetaLex Advanced OCR/Vision Pipeline v3
FIELD-AWARE SPATIAL REASONING MODEL

Key improvements:
1. Replaced generic regex with Field-Aware Spatial Extraction.
2. OCR Bounding Boxes are preserved and used for geometric reasoning.
3. Dedicated Detectors (MRP, Date, Qty) enforce layout rules (e.g., MRP value must be near MRP label).
4. Nutrition Table Masking prevents irrelevant numbers from contaminating candidate pools.
5. Multi-pass OCR remains, but heavily filters candidates based on legal context.
6. Validation explicitly rejects "0" for MRP and enforces sensible formatting.
"""
import re
try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np
from PIL import Image
from typing import Optional, List, Dict, Any, Tuple
import logging
import time
from backend.services.font_analyzer import (
    calculate_font_size_mm, get_min_font_size, analyze_font_compliance
)
from backend.services.barcode_detector import (
    detect_barcodes, verify_against_gs1
)
from backend.services.anomaly_detector import run_full_anomaly_detection
from backend.services.image_forensics import analyze_image_authenticity

logger = logging.getLogger("metalex.ocr")

# Multi-language EasyOCR reader cache
_ocr_readers: Dict[tuple, Any] = {}
_ocr_available = False

SUPPORTED_LANGUAGES = ["en", "hi", "ta", "bn", "mr", "gu"]


def _get_ocr_reader(languages: Optional[List[str]] = None):
    global _ocr_readers, _ocr_available
    if not languages:
        langs_tuple = ("en",)
    else:
        valid_langs = [l.strip().lower() for l in languages if l.strip().lower() in SUPPORTED_LANGUAGES]
        if not valid_langs:
            valid_langs = ["en"]
        if "en" not in valid_langs:
            valid_langs.append("en")
        langs_tuple = tuple(sorted(list(set(valid_langs))))

    if langs_tuple in _ocr_readers:
        return _ocr_readers[langs_tuple]

    try:
        import ssl
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        import easyocr
        # Use the same model dir as the startup pre-warmer so models aren't re-downloaded
        from pathlib import Path as _Path
        _model_dir = str(_Path(__file__).parent.parent.parent / ".easyocr_models")
        import os as _os
        _os.makedirs(_model_dir, exist_ok=True)
        reader = easyocr.Reader(list(langs_tuple), gpu=False, verbose=False, model_storage_directory=_model_dir)
        _ocr_readers[langs_tuple] = reader
        _ocr_available = True
        logger.info(f"EasyOCR initialized successfully for languages: {langs_tuple}")
        return reader
    except Exception as e:
        logger.warning(f"EasyOCR initialization warning for {langs_tuple}: {e}. Fallback pipeline active.")
        # Fallback to English if multi-lang fails
        if langs_tuple != ("en",):
            return _get_ocr_reader(["en"])
        _ocr_available = False
        return None


def detect_text_languages(ocr_results: list) -> dict:
    """
    Detects Indian languages from Unicode scripts in the extracted OCR text.
    """
    scripts = {
        "devanagari": 0,  # Hindi, Marathi
        "tamil": 0,       # Tamil
        "bengali": 0,     # Bengali
        "gujarati": 0,    # Gujarati
        "latin": 0,       # English
        "digits": 0
    }

    all_text = " ".join([r.get("text", "") for r in ocr_results])

    for char in all_text:
        cp = ord(char)
        if 0x0900 <= cp <= 0x097F:
            scripts["devanagari"] += 1
        elif 0x0B80 <= cp <= 0x0BFF:
            scripts["tamil"] += 1
        elif 0x0980 <= cp <= 0x09FF:
            scripts["bengali"] += 1
        elif 0x0A80 <= cp <= 0x0AFF:
            scripts["gujarati"] += 1
        elif (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            scripts["latin"] += 1
        elif 0x0030 <= cp <= 0x0039:
            scripts["digits"] += 1

    detected = []
    if scripts["latin"] >= 5:
        detected.append("en")
    if scripts["devanagari"] >= 3:
        detected.append("hi")
    if scripts["tamil"] >= 3:
        detected.append("ta")
    if scripts["bengali"] >= 3:
        detected.append("bn")
    if scripts["gujarati"] >= 3:
        detected.append("gu")

    if not detected:
        detected = ["en"]

    has_english = "en" in detected
    has_hindi = "hi" in detected
    is_dual_language = has_english and has_hindi

    return {
        "detected_languages": detected,
        "has_english": has_english,
        "has_hindi": has_hindi,
        "is_dual_language": is_dual_language,
        "primary_language": "en" if scripts["latin"] >= scripts["devanagari"] else "hi",
        "script_counts": scripts
    }


def is_ocr_available() -> bool:
    global _ocr_available
    _get_ocr_reader()
    return _ocr_available

# ──────────────────────────── Quality Assessment ──────────────────────────────
def assess_image_quality(img: np.ndarray) -> dict:
    """Assess image quality for Legal Metrology OCR suitability."""
    issues = []
    scores = {}
    h, w = img.shape[:2]

    resolution = h * w
    if resolution < 120 * 120:
        issues.append("Extremely low resolution — text unreadable")
        scores["resolution"] = 0.2
    elif resolution < 400 * 400:
        issues.append("Low resolution — minor text may be missed")
        scores["resolution"] = 0.6
    else:
        scores["resolution"] = 1.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 25:
        issues.append("Image is blurry — please hold camera steady")
        scores["sharpness"] = 0.3
    elif laplacian_var < 90:
        issues.append("Slightly blurry — consider retaking")
        scores["sharpness"] = 0.7
    else:
        scores["sharpness"] = 1.0

    contrast = gray.std()
    if contrast < 22:
        issues.append("Low contrast between packaging text and background")
        scores["contrast"] = 0.4
    else:
        scores["contrast"] = 1.0

    brightness = gray.mean()
    if brightness < 35:
        issues.append("Image is too dark — improve lighting")
        scores["brightness"] = 0.4
    elif brightness > 230:
        issues.append("Image has glare or overexposure")
        scores["brightness"] = 0.5
    else:
        scores["brightness"] = 1.0

    overall = sum(scores.values()) / len(scores) if scores else 0.5

    return {
        "overall_score": round(overall, 2),
        "scores": scores,
        "issues": issues,
        "resolution": f"{w}x{h}",
        "is_suitable": overall >= 0.4,
        "quality_label": "Good" if overall >= 0.75 else ("Fair" if overall >= 0.5 else "Poor"),
    }

# ──────────────────────────── Multi-Pass Preprocessing ────────────────────────
def preprocess_for_ocr(img: np.ndarray) -> List[np.ndarray]:
    """Produce multi-pass preprocessed variants."""
    h, w = img.shape[:2]
    variants = []

    scaled = img.copy()
    if max(h, w) < 900:
        factor = 900 / max(h, w)
        scaled = cv2.resize(scaled, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    elif max(h, w) > 3000:
        factor = 3000 / max(h, w)
        scaled = cv2.resize(scaled, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)

    # 1. Base CLAHE
    try:
        denoised = cv2.fastNlMeansDenoisingColored(scaled, None, 8, 8, 7, 21)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)
        variants.append(enhanced)
    except Exception:
        variants.append(scaled)

    # 2. High-contrast Grayscale (Adaptive Threshold for stamped text)
    try:
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        clahe2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray_clahe = clahe2.apply(gray)
        thresh = cv2.adaptiveThreshold(gray_clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 15, 8)
        variants.append(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR))
    except Exception:
        pass

    # 3. Sharpened
    try:
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharp = cv2.filter2D(scaled, -1, kernel)
        variants.append(sharp)
    except Exception:
        pass

    return variants if variants else [img]

# ──────────────────────────── OCR Execution ───────────────────────────────────
def run_ocr(img: np.ndarray, languages: Optional[List[str]] = None) -> list:
    """Run multi-pass OCR on image with bounding box tracking and duplicate removal."""
    reader = _get_ocr_reader(languages)
    if reader is None:
        return []

    variants = preprocess_for_ocr(img)
    collected_results = []
    seen_texts: set = set()

    for var in variants:
        try:
            raw_results = reader.readtext(var, paragraph=False, width_ths=0.7)
            for (bbox, text, conf) in raw_results:
                clean_text = text.strip()
                if len(clean_text) < 2:
                    continue

                pts = np.array(bbox)
                vh, vw = var.shape[:2]
                oh, ow = img.shape[:2]
                scale_x = ow / vw
                scale_y = oh / vh

                x_min = int(pts[:, 0].min() * scale_x)
                y_min = int(pts[:, 1].min() * scale_y)
                x_max = int(pts[:, 0].max() * scale_x)
                y_max = int(pts[:, 1].max() * scale_y)

                key = (clean_text.lower(), round(x_min / 50), round(y_min / 50))
                if key not in seen_texts:
                    seen_texts.add(key)
                    collected_results.append({
                        "text": clean_text,
                        "confidence": round(float(conf), 3),
                        "bbox": [[int(p[0] * scale_x), int(p[1] * scale_y)] for p in bbox],
                        "bbox_rect": [max(0, x_min), max(0, y_min), min(ow, x_max), min(oh, y_max)],
                        "center_x": (x_min + x_max) / 2,
                        "center_y": (y_min + y_max) / 2,
                        "width": max(1, x_max - x_min),
                        "height": max(1, y_max - y_min),
                    })
        except Exception as e:
            logger.warning(f"OCR pass error: {e}")

    return collected_results

# ──────────────────────────── Character Repair ────────────────────────────────
def repair_ocr_digits(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"(?<=[₹Rs\d\.\/])[Il|](?=\d)", "1", cleaned)
    cleaned = re.sub(r"(?<=\d)[Il|](?=[₹Rs\d\.\/])", "1", cleaned)
    cleaned = re.sub(r"(?<=[₹Rs\d\.\/])[Oo](?=\d)", "0", cleaned)
    cleaned = re.sub(r"(?<=\d)[Oo](?=[₹Rs\d\.\/])", "0", cleaned)
    return cleaned

# ──────────────────────────── SPATIAL REASONING & MASKS ──────────────────────
def _get_distance(b1: list, b2: list) -> float:
    # b is [x1, y1, x2, y2]
    c1x = (b1[0] + b1[2]) / 2
    c1y = (b1[1] + b1[3]) / 2
    c2x = (b2[0] + b2[2]) / 2
    c2y = (b2[1] + b2[3]) / 2
    return ((c1x - c2x) ** 2 + (c1y - c2y) ** 2) ** 0.5

def _is_below_or_right(anchor: list, target: list, max_dist_multiplier: float = 4.0) -> bool:
    """Check if target box is reasonably below or to the right of anchor box."""
    anchor_h = max(1, anchor[3] - anchor[1])

    # Same-row check: if target vertically overlaps the anchor, it's on the same line.
    # In this case use a much wider horizontal tolerance (20x anchor height) so that
    # values placed far to the right of their label (e.g. "MRP: ... ₹199") are found.
    anchor_mid_y = (anchor[1] + anchor[3]) / 2
    target_mid_y = (target[1] + target[3]) / 2
    same_row = abs(anchor_mid_y - target_mid_y) < anchor_h * 1.5
    if same_row and target[0] > anchor[0]:
        # Same row, target is to the right — always allow up to 20× anchor height wide
        horiz_dist = target[0] - anchor[2]  # gap between label right edge and value left edge
        return horiz_dist < anchor_h * 20

    # Otherwise use the original distance cap
    dist = _get_distance(anchor, target)
    if dist > anchor_h * max_dist_multiplier:
        return False
    # Check if mostly below or right
    if target[1] > anchor[1] - (anchor_h / 2) or target[0] > anchor[0] + (anchor[2]-anchor[0])*0.8:
        return True
    return False

def _detect_nutrition_tables(ocr_results: list) -> list:
    """Identify bounding boxes of nutrition tables to suppress false numbers."""
    nutrition_keywords = [r"energy", r"protein", r"carbohydrate", r"sugar", r"fat", r"sodium", r"cholesterol"]
    nutrition_boxes = []
    for item in ocr_results:
        text = item["text"].lower()
        if any(re.search(kw, text) for kw in nutrition_keywords):
            nutrition_boxes.append(item["bbox_rect"])
    
    # Expand boxes to create exclusion zones
    zones = []
    for b in nutrition_boxes:
        h = max(1, b[3] - b[1])
        w = max(1, b[2] - b[0])
        zones.append([max(0, b[0] - w), max(0, b[1] - h), b[2] + w, b[3] + h*3])
    return zones

def _is_in_zones(bbox: list, zones: list) -> bool:
    for z in zones:
        # Check intersection
        if (bbox[0] < z[2] and bbox[2] > z[0] and
            bbox[1] < z[3] and bbox[3] > z[1]):
            return True
    return False

def _merge_adjacent_blocks(ocr_results: list, x_thresh=1.5, y_thresh=2.0) -> list:
    """Merge lines of text that form a coherent block (e.g. addresses)."""
    if not ocr_results:
        return []
    
    blocks = []
    used = set()
    
    # Sort top to bottom
    sorted_items = sorted(ocr_results, key=lambda x: x["center_y"])
    
    for i, item in enumerate(sorted_items):
        if i in used:
            continue
        
        current_block = [item]
        used.add(i)
        
        base_h = item["height"]
        
        # Look ahead for adjacent lines
        for j, other in enumerate(sorted_items):
            if j in used: continue
            
            # Check if other is directly below or adjacent
            dx = abs(item["center_x"] - other["center_x"])
            dy = other["center_y"] - current_block[-1]["center_y"]
            
            if dx < (base_h * x_thresh) * 5 and 0 < dy < (base_h * y_thresh):
                current_block.append(other)
                used.add(j)
                
        # Merge block
        texts = [b["text"] for b in current_block]
        bboxes = [b["bbox_rect"] for b in current_block]
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[2] for b in bboxes)
        y2 = max(b[3] for b in bboxes)
        
        blocks.append({
            "text": " ".join(texts),
            "confidence": sum(b["confidence"] for b in current_block) / len(current_block),
            "bbox_rect": [x1, y1, x2, y2],
            "original_items": current_block
        })
        
    return blocks

# ──────────────────────────── FIELD DETECTORS ──────────────────────────────
class BaseDetector:
    def __init__(self, name: str):
        self.name = name

    def detect(self, ocr_results: list, nutrition_zones: list, merged_blocks: list, all_text: str) -> list:
        return []

class MRPDetector(BaseDetector):
    def __init__(self):
        super().__init__("mrp")
        self.label_patterns = [r"m\.?\s*r\.?\s*p\.?", r"maximum\s*retail\s*price"]
        self.val_patterns = [
            r"(?:₹|rs[\.\:\-\s]*|inr[\.\:\-\s]*)\s*([0-9IlOo,\.]+)",
            r"^([0-9IlOo,\.]+)$",
            # Leading number on a line that has extra text like "(Inclusive of all taxes)"
            r"^([0-9IlOo,\.]{2,})\s*[\(\s]",
        ]

    def detect(self, ocr_results, nutrition_zones, merged_blocks, all_text) -> list:
        candidates = []
        labels = []
        # Find MRP labels
        for item in ocr_results:
            text = item["text"].lower()
            if any(re.search(p, text) for p in self.label_patterns):
                labels.append(item)
                
        for label in labels:
            label_box = label["bbox_rect"]
            
            # Look for values near this label
            for item in ocr_results:
                if item == label:
                    # Check if value is inside the label text itself (e.g. "MRP Rs. 199")
                    repaired = repair_ocr_digits(item["text"])
                    m = re.search(r"(?:mrp|price).*?(?:₹|rs[\.\:\-\s]*)\s*([0-9IlOo,\.]+)", repaired, re.IGNORECASE)
                    if m:
                        val = m.group(1).strip()
                        if self._is_valid_mrp(val):
                            candidates.append({
                                "text": f"₹{val}",
                                "confidence": item["confidence"],
                                "score": item["confidence"] + 1.0, # High score for direct match
                                "bbox": item["bbox_rect"],
                                "source_text": item["text"],
                                "reason": "Extracted directly from MRP label line"
                            })
                    continue

                if _is_in_zones(item["bbox_rect"], nutrition_zones):
                    continue

                if _is_below_or_right(label_box, item["bbox_rect"], max_dist_multiplier=5.0):
                    repaired = repair_ocr_digits(item["text"])
                    for vp in self.val_patterns:
                        m = re.search(vp, repaired, re.IGNORECASE)
                        if m:
                            val = m.group(1).strip()
                            if self._is_valid_mrp(val):
                                dist = _get_distance(label_box, item["bbox_rect"])
                                dist_penalty = min(0.5, dist / 1000.0)
                                score = item["confidence"] + 0.8 - dist_penalty
                                candidates.append({
                                    "text": f"₹{val}",
                                    "confidence": item["confidence"],
                                    "score": score,
                                    "bbox": item["bbox_rect"],
                                    "source_text": item["text"],
                                    "reason": f"Spatially near MRP label (dist: {int(dist)})"
                                })
        return candidates

    def _is_valid_mrp(self, val: str) -> bool:
        # Strip commas
        v = val.replace(",", "")
        try:
            f = float(v)
            if f <= 0: return False # Ignore 0
            if f > 100000: return False # Ignore absurdly high numbers (e.g. barcodes)
            return True
        except ValueError:
            return False

class DateDetector(BaseDetector):
    def __init__(self):
        super().__init__("date")
        self.label_patterns = [r"mfg", r"mfd", r"pkd", r"pkg", r"packed", r"manufactured", r"expiry", r"exp", r"use\s*by", r"best\s*before"]
        self.val_patterns = [
            r"(\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b)",
            r"(\b\d{1,2}[/\-\.]\d{2,4}\b)",
            r"(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s/\-\.]+\d{2,4}\b)"
        ]

    def detect(self, ocr_results, nutrition_zones, merged_blocks, all_text) -> list:
        candidates = []
        labels = []
        for item in ocr_results:
            text = item["text"].lower()
            if any(re.search(p, text) for p in self.label_patterns):
                labels.append(item)

        for label in labels:
            label_box = label["bbox_rect"]
            for item in ocr_results:
                if item == label:
                    # In-line match
                    for vp in self.val_patterns:
                        m = re.search(vp, item["text"], re.IGNORECASE)
                        if m:
                            candidates.append({
                                "text": m.group(1).strip(),
                                "confidence": item["confidence"],
                                "score": item["confidence"] + 1.0,
                                "bbox": item["bbox_rect"],
                                "source_text": item["text"],
                                "reason": "Extracted directly from Date label line"
                            })
                    continue

                if _is_in_zones(item["bbox_rect"], nutrition_zones): continue

                if _is_below_or_right(label_box, item["bbox_rect"], max_dist_multiplier=5.0):
                    for vp in self.val_patterns:
                        m = re.search(vp, item["text"], re.IGNORECASE)
                        if m:
                            dist = _get_distance(label_box, item["bbox_rect"])
                            dist_penalty = min(0.5, dist / 1000.0)
                            candidates.append({
                                "text": m.group(1).strip(),
                                "confidence": item["confidence"],
                                "score": item["confidence"] + 0.8 - dist_penalty,
                                "bbox": item["bbox_rect"],
                                "source_text": item["text"],
                                "reason": f"Spatially near Date label (dist: {int(dist)})"
                            })
        return candidates

class QuantityDetector(BaseDetector):
    def __init__(self):
        super().__init__("net_quantity")
        self.label_patterns = [r"net\s*(?:wt|weight|qty|quantity|vol|volume)"]
        self.val_patterns = [r"(\b[\d\.]+\s*(?:g|gm|kg|ml|l|ltr|pcs|units)\b)"]
        self.serving_patterns = [r"serving"]

    def detect(self, ocr_results, nutrition_zones, merged_blocks, all_text) -> list:
        candidates = []
        labels = []
        for item in ocr_results:
            text = item["text"].lower()
            if any(re.search(p, text) for p in self.serving_patterns):
                # Ignore serving size blocks
                continue
            if any(re.search(p, text) for p in self.label_patterns):
                labels.append(item)

        for label in labels:
            label_box = label["bbox_rect"]
            for item in ocr_results:
                if item == label:
                    m = re.search(r"net[^\d]+([\d\.]+\s*(?:g|gm|kg|ml|l|ltr|pcs|units))", item["text"], re.IGNORECASE)
                    if m:
                        candidates.append({
                            "text": m.group(1).strip(),
                            "confidence": item["confidence"],
                            "score": item["confidence"] + 1.0,
                            "bbox": item["bbox_rect"],
                            "source_text": item["text"],
                            "reason": "Direct in-line match"
                        })
                    continue

                if _is_below_or_right(label_box, item["bbox_rect"], max_dist_multiplier=4.0):
                    m = re.search(r"(\b[\d\.]+\s*(?:g|gm|kg|ml|l|ltr|pcs|units)\b)", item["text"], re.IGNORECASE)
                    if m:
                        dist = _get_distance(label_box, item["bbox_rect"])
                        candidates.append({
                            "text": m.group(1).strip(),
                            "confidence": item["confidence"],
                            "score": item["confidence"] + 0.8 - min(0.5, dist/1000.0),
                            "bbox": item["bbox_rect"],
                            "source_text": item["text"],
                            "reason": "Spatially near Net Qty label"
                        })
        return candidates

class ManufacturerDetector(BaseDetector):
    def __init__(self):
        super().__init__("manufacturer")
        self.kws = [r"manufactured\s*(?:by|&)?", r"marketed\s*by", r"packed\s*by"]

    def detect(self, ocr_results, nutrition_zones, merged_blocks, all_text) -> list:
        candidates = []

        # First pass: find label tokens
        labels = []
        for item in ocr_results:
            text = item["text"].lower()
            if any(re.search(p, text) for p in self.kws):
                labels.append(item)

        for label in labels:
            label_box = label["bbox_rect"]

            # Check if the value is inline in the label itself
            clean = re.sub(r"(?i)^(.*?)(?:manufactured\s*(?:by|&)?|marketed\s*by|packed\s*by)\s*[:\-]*\s*", "", label["text"]).strip()
            if len(clean) > 3 and not clean.lower().startswith("add"):
                candidates.append({
                    "text": clean,
                    "confidence": label["confidence"],
                    "score": label["confidence"] + 1.0,
                    "bbox": label_box,
                    "source_text": label["text"],
                    "reason": "Inline manufacturer name"
                })
                continue

            # Spatial lookup: find value token to the right or below the label
            for item in ocr_results:
                if item is label:
                    continue
                if _is_in_zones(item["bbox_rect"], nutrition_zones):
                    continue
                if _is_below_or_right(label_box, item["bbox_rect"], max_dist_multiplier=5.0):
                    t = item["text"].strip()
                    if not t or len(t) < 3:
                        continue
                    # Skip label-like tokens or partial manufacturer keyword matches
                    if t.lower().startswith("address") or t.endswith(":"):
                        continue
                    if any(re.search(p, t.lower()) for p in self.kws):
                        continue
                    # Skip tokens that look like fragments of the label word itself
                    if re.match(r"(?i)^manufact|^marketed|^packed", t):
                        continue
                    # Skip things that look like phone numbers, dates, or PIN codes
                    if re.match(r"^[\d\-\+\(\)]{6,}$", t):
                        continue
                    dist = _get_distance(label_box, item["bbox_rect"])
                    candidates.append({
                        "text": t,
                        "confidence": item["confidence"],
                        "score": item["confidence"] + 0.8 - min(0.4, dist / 300),
                        "bbox": item["bbox_rect"],
                        "source_text": item["text"],
                        "reason": f"Spatially near Manufacturer label"
                    })

        return candidates

class GenericDetector(BaseDetector):
    def __init__(self, name: str, kws: list, regexes: list = None, regex_only: bool = False):
        super().__init__(name)
        self.kws = kws
        self.regexes = regexes or []
        self.regex_only = regex_only  # if True, spatial fallback only uses regex matches (no plain value)

    def detect(self, ocr_results, nutrition_zones, merged_blocks, all_text) -> list:
        candidates = []
        labels_found = []
        for item in ocr_results:
            text = item["text"].lower()
            score = 0.0
            if any(re.search(p, text) for p in self.kws):
                score += 0.5
                labels_found.append(item)

            for rx in self.regexes:
                m = re.search(rx, item["text"], re.IGNORECASE)
                if m:
                    val = m.group(1).strip() if m.groups() else m.group(0).strip()
                    candidates.append({
                        "text": val,
                        "confidence": item["confidence"],
                        "score": item["confidence"] + score + 0.5,
                        "bbox": item["bbox_rect"],
                        "source_text": item["text"],
                        "reason": f"Regex match + Keyword"
                    })
            if score > 0 and not self.regexes:
                t = item["text"].strip()
                # Don't return the label token itself as the value (e.g. "Common Name:")
                if t.endswith(":") or t.endswith("?") or not t:
                    pass
                else:
                    candidates.append({
                        "text": t,
                        "confidence": item["confidence"],
                        "score": item["confidence"] + score,
                        "bbox": item["bbox_rect"],
                        "source_text": item["text"],
                        "reason": "Keyword match"
                    })

        # Spatial lookup: if we found a label, look for value tokens nearby
        for label in labels_found:
            label_box = label["bbox_rect"]
            for item in ocr_results:
                if item is label:
                    continue
                if _is_in_zones(item["bbox_rect"], nutrition_zones):
                    continue
                if _is_below_or_right(label_box, item["bbox_rect"], max_dist_multiplier=5.0):
                    # Skip items that look like another label (contain a colon at end, or match kws)
                    t = item["text"].strip()
                    if not t or t.endswith(":") or any(re.search(p, t.lower()) for p in self.kws):
                        continue
                    # For fields with regexes, prefer regex match; but also accept plain nearby value
                    if self.regexes:
                        matched = False
                        for rx in self.regexes:
                            m = re.search(rx, item["text"], re.IGNORECASE)
                            if m:
                                val = m.group(1).strip() if m.groups() else m.group(0).strip()
                                dist = _get_distance(label_box, item["bbox_rect"])
                                candidates.append({
                                    "text": val,
                                    "confidence": item["confidence"],
                                    "score": item["confidence"] + 0.7 - min(0.3, dist / 500),
                                    "bbox": item["bbox_rect"],
                                    "source_text": item["text"],
                                    "reason": "Spatial regex match near label"
                                })
                                matched = True
                        if not matched and not self.regex_only:
                            # Accept plain text value found spatially near a label
                            # (e.g. "India" after "CountryofOrigin:" label)
                            dist = _get_distance(label_box, item["bbox_rect"])
                            candidates.append({
                                "text": t,
                                "confidence": item["confidence"],
                                "score": item["confidence"] + 0.5 - min(0.3, dist / 500),
                                "bbox": item["bbox_rect"],
                                "source_text": item["text"],
                                "reason": "Spatial proximity to label (plain value)"
                            })
                    else:
                        dist = _get_distance(label_box, item["bbox_rect"])
                        candidates.append({
                            "text": t,
                            "confidence": item["confidence"],
                            "score": item["confidence"] + 0.6 - min(0.3, dist / 500),
                            "bbox": item["bbox_rect"],
                            "source_text": item["text"],
                            "reason": "Spatial proximity to label"
                        })

        return candidates

DETECTORS = [
    MRPDetector(),
    DateDetector(),
    QuantityDetector(),
    ManufacturerDetector(),
    GenericDetector("consumer_care", [r"consumer", r"care", r"feedback"], [r"([\w\.-]+@[\w\.-]+\.\w+)", r"(1800[-\s]?\d{3}[-\s]?\d{3,4}|\b\d{10}\b)"]),
    GenericDetector("country_of_origin", [r"country\s*of\s*origin", r"made\s*in", r"product\s*of"], [r"(?:made\s*in|product\s*of)\s*([a-zA-Z\s]+)"]),
    GenericDetector("address", [r"address", r"regd\.?\s*off", r"pin\s*code"], [r"(\b\d{6}\b)"], regex_only=True),
    GenericDetector("common_name", [r"common\s*name", r"generic\s*name"]),
]

def extract_fields(ocr_results: list, img_shape: tuple) -> dict:
    if not ocr_results:
        return _empty_fields()

    all_text = " ".join([r["text"] for r in ocr_results])
    nutrition_zones = _detect_nutrition_tables(ocr_results)
    merged_blocks = _merge_adjacent_blocks(ocr_results)
    
    fields = {}
    
    for det in DETECTORS:
        cands = det.detect(ocr_results, nutrition_zones, merged_blocks, all_text)
        if cands:
            cands.sort(key=lambda c: c["score"], reverse=True)
            best = cands[0]
            fields[det.name] = {
                "value": best["text"],
                "normalized_value": _normalize_field_value(det.name, best["text"]),
                "confidence": min(1.0, round(best["confidence"], 3)),
                "bounding_box": best["bbox"],
                "source_text": best["source_text"],
                "extraction_method": "spatial_aware_detector",
                "candidates": [{"value": c["text"], "confidence": c["confidence"], "score": round(c["score"], 3), "reason": c.get("reason", "")} for c in cands[:5]],
            }
        else:
            fields[det.name] = {
                "value": None,
                "normalized_value": None,
                "confidence": 0.0,
                "bounding_box": None,
                "source_text": "",
                "extraction_method": "not_detected",
                "candidates": [],
            }

    # Product Name Fallback
    if not fields.get("product_name", {}).get("value"):
        pn = _detect_prominent_product_name(ocr_results, fields, img_shape)
        if pn:
            fields["product_name"] = pn
        else:
            fields["product_name"] = _empty_fields()["product_name"]

    # Calculate Font Height in mm for all detected declarations
    for fname, fdata in fields.items():
        if fdata.get("bounding_box") and fdata.get("value"):
            fdata["font_size_mm"] = calculate_font_size_mm(fdata["bounding_box"], img_shape)
            fdata["min_font_size_mm"] = get_min_font_size(fname)
        else:
            fdata["font_size_mm"] = None
            fdata["min_font_size_mm"] = get_min_font_size(fname)

    return fields

def _detect_prominent_product_name(ocr_results: list, existing: dict, img_shape: tuple) -> Optional[dict]:
    if not ocr_results: return None
    used = set()
    for f in existing.values():
        if f.get("value"): used.add(str(f["value"]).lower())
    
    h, w = img_shape[:2] if len(img_shape) >= 2 else (1000, 1000)
    best = None
    max_score = 0
    
    for item in ocr_results:
        t = item["text"].strip()
        if len(t) < 3 or t.lower() in used or re.match(r"^[\d₹\.\,\-\/\:]+$", t):
            continue
            
        bbox = item["bbox_rect"]
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        y_pos = bbox[1] / h
        score = (area / (h * w + 1)) * 4.0 + (1.0 - y_pos) * 2.0
        
        if score > max_score:
            max_score = score
            best = {
                "value": t,
                "normalized_value": t.title(),
                "confidence": round(item["confidence"], 3),
                "bounding_box": bbox,
                "font_size_mm": calculate_font_size_mm(bbox, img_shape),
                "min_font_size_mm": get_min_font_size("product_name"),
                "source_text": t,
                "extraction_method": "spatial_headline_heuristic",
                "candidates": [{"value": t, "confidence": item["confidence"], "score": round(score, 3), "reason": "Largest/topmost text block"}],
            }
    return best

def _normalize_field_value(field_name: str, value: str) -> str:
    if not value: return ""
    val = value.strip()
    if field_name == "mrp":
        repaired = repair_ocr_digits(val)
        nums = re.findall(r"[\d\.]+", repaired)
        if nums:
            try:
                # Parse as float to strip leading zeros (e.g. "0199" → 199.0)
                price = float(nums[0])
                if price > 0:
                    formatted = f"{int(price)}" if price == int(price) else f"{price:.2f}"
                    return f"₹{formatted}"
            except ValueError:
                pass
            return f"₹{nums[0]}"
        return val
    elif field_name == "product_name": return val.title()
    elif field_name == "country_of_origin": return re.sub(r"(?:country\s*of\s*origin|made\s*in|product\s*of|[:\.\-])", "", val, flags=re.I).strip().title()
    return val

def _normalize_for_comparison(field_name: str, value: str) -> str:
    if not value: return ""
    val = value.strip().lower()
    if field_name == "mrp":
        repaired = repair_ocr_digits(val)
        nums = re.findall(r"[\d\.]+", repaired)
        return nums[0] if nums else val
    elif field_name == "net_quantity":
        val = re.sub(r"\s+", "", val)
        val = re.sub(r"gms?|gram?s?", "g", val)
        return val
    return re.sub(r"[^\w\s]", "", val).strip()

def _empty_fields() -> dict:
    names = ["product_name", "net_quantity", "mrp", "manufacturer", "date", "consumer_care", "country_of_origin", "address", "common_name"]
    return {
        k: {
            "value": None,
            "normalized_value": None,
            "confidence": 0.0,
            "bounding_box": None,
            "font_size_mm": None,
            "min_font_size_mm": get_min_font_size(k),
            "source_text": "",
            "extraction_method": "not_detected",
            "candidates": []
        }
        for k in names
    }

def create_annotated_image(img: np.ndarray, ocr_results: list, fields: dict, violations=None, barcodes=None) -> np.ndarray:
    annotated = img.copy()
    violation_fields = {v.get("field") for v in (violations or [])}

    # 1. Faint grey bounding boxes for all OCR tokens
    for item in ocr_results:
        b = item["bbox_rect"]
        cv2.rectangle(annotated, (b[0], b[1]), (b[2], b[3]), (220, 220, 220), 1)

    # 2. Highlight Barcodes & QR Codes with Cyan/Gold borders
    if barcodes:
        for bc in barcodes:
            bbox = bc.get("bbox")
            if bbox and len(bbox) >= 4:
                cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 180, 0), 3)
                bclabel = f"BARCODE: {bc.get('type', 'CODE')} ({bc.get('data', '')})"
                (tw, th), _ = cv2.getTextSize(bclabel, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                y = max(bbox[1] - 4, th + 4)
                cv2.rectangle(annotated, (bbox[0], y - th - 3), (bbox[0] + tw + 6, y + 2), (255, 180, 0), -1)
                cv2.putText(annotated, bclabel, (bbox[0] + 3, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    # 3. Highlight Legal Declarations with Font Size & Compliance Indicators
    for field_name, fdata in fields.items():
        bbox = fdata.get("bounding_box")
        if not bbox or len(bbox) < 4:
            continue

        is_viol = field_name in violation_fields
        conf = fdata.get("confidence", 0)
        font_sz = fdata.get("font_size_mm")
        min_sz = fdata.get("min_font_size_mm", 1.0)
        
        is_undersized = font_sz is not None and font_sz < min_sz

        # Color coding:
        # Undersized font -> Orange (0, 140, 255)
        # General Violation -> Red (40, 40, 235)
        # Compliant high confidence -> Green (40, 200, 40)
        # Needs review / medium confidence -> Amber (0, 180, 255)
        if is_undersized:
            color = (0, 120, 255)  # Orange for font violation
            label = f"{field_name.replace('_', ' ').title()} ({font_sz}mm < {min_sz}mm ❌)"
        elif is_viol:
            color = (40, 40, 235)  # Red
            label = f"{field_name.replace('_', ' ').title()} (Violation)"
        elif conf >= 0.6:
            color = (40, 200, 40)  # Green
            font_str = f" [{font_sz}mm]" if font_sz else ""
            label = f"{field_name.replace('_', ' ').title()} ({conf:.0%}){font_str}"
        else:
            color = (0, 180, 255)  # Amber
            label = f"{field_name.replace('_', ' ').title()} ({conf:.0%})"

        cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 3)

        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        y = max(bbox[1] - 4, th + 4)
        cv2.rectangle(annotated, (bbox[0], y - th - 3), (bbox[0] + tw + 6, y + 2), color, -1)
        cv2.putText(annotated, label, (bbox[0] + 3, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    return annotated

def process_single_image(image_path: str, languages: Optional[List[str]] = None) -> dict:
    img = None
    try:
        img = cv2.imread(image_path)
        if img is None:
            pil_img = Image.open(image_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        return {
            "success": False, "error": str(e), "ocr_results": [],
            "fields": _empty_fields(),
            "barcodes": [],
            "font_analysis": {},
            "languages": {"detected_languages": ["en"], "has_english": True, "has_hindi": False, "is_dual_language": False},
            "anomaly_detection": {"has_anomaly": False, "tampering_detected": False, "findings": []},
            "forensics": {"verdict": "UNKNOWN", "authenticity_score": 0.0, "findings": []},
            "quality": {"overall_score": 0, "issues": ["Failed to read image"], "is_suitable": False, "quality_label": "Poor"},
        }
    quality = assess_image_quality(img)
    ocr_results = run_ocr(img, languages=languages)
    fields = extract_fields(ocr_results, img.shape)
    barcodes = detect_barcodes(img)
    font_analysis = analyze_font_compliance(fields, img.shape)
    
    # Phase 2: Multi-language detection & script analysis
    lang_info = detect_text_languages(ocr_results)
    
    # Phase 2: Anomaly detection (MRP sticker, package damage, font inconsistency)
    fields_list = [{"field_name": k, "bounding_box": v.get("bounding_box"), "value": v.get("value")} for k, v in fields.items()]
    anomaly_res = run_full_anomaly_detection(img, fields_list)
    
    # Phase 2: Image forensics (ELA and digital tampering checks)
    forensics_res = analyze_image_authenticity(img, file_path=image_path)
    
    annotated = create_annotated_image(img, ocr_results, fields, barcodes=barcodes)
    return {
        "success": True, 
        "quality": quality, 
        "ocr_results": ocr_results,
        "fields": fields, 
        "barcodes": barcodes,
        "font_analysis": font_analysis,
        "languages": lang_info,
        "anomaly_detection": anomaly_res,
        "forensics": forensics_res,
        "annotated_image": annotated, 
        "original_image": img, 
        "ocr_text_count": len(ocr_results),
    }

def process_image(image_path: str, languages: Optional[List[str]] = None) -> dict:
    return process_single_image(image_path, languages=languages)

def _fuse_field_candidates(field_name: str, per_image_candidates: list) -> dict:
    valid = [c for c in per_image_candidates if c.get("value")]
    if not valid:
        base = _empty_fields()[field_name]
        base.update({"conflict_detected": False, "all_image_candidates": [], "source_image_index": None, "source_image_number": None})
        return base

    normalized_groups: Dict[str, list] = {}
    for c in valid:
        norm = _normalize_for_comparison(field_name, c["value"])
        if norm not in normalized_groups: normalized_groups[norm] = []
        normalized_groups[norm].append(c)

    conflict_detected = len(normalized_groups) > 1
    best = max(valid, key=lambda c: c.get("confidence", 0))

    all_candidates = []
    for c in valid:
        all_candidates.append({
            "value": c["value"],
            "normalized_value": _normalize_field_value(field_name, c["value"]),
            "confidence": round(c.get("confidence", 0), 3),
            "source_image_index": c.get("image_index", 0),
            "source_image_number": c.get("image_number", 1),
            "bounding_box": c.get("bounding_box"),
            "source_text": c.get("source_text", ""),
            "reason": c.get("candidates", [{}])[0].get("reason", "") if c.get("candidates") else ""
        })
    all_candidates.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "value": best["value"],
        "normalized_value": _normalize_field_value(field_name, best["value"]),
        "confidence": round(best.get("confidence", 0), 3),
        "bounding_box": best.get("bounding_box"),
        "font_size_mm": best.get("font_size_mm"),
        "min_font_size_mm": best.get("min_font_size_mm") or get_min_font_size(field_name),
        "source_text": best.get("source_text", ""),
        "extraction_method": best.get("extraction_method", "ocr_regex_spatial"),
        "candidates": [{"value": c["value"], "confidence": c["confidence"], "score": c["confidence"], "reason": c.get("reason", "")} for c in all_candidates[:5]],
        "conflict_detected": conflict_detected,
        "all_image_candidates": all_candidates,
        "source_image_index": best.get("image_index", 0),
        "source_image_number": best.get("image_number", 1),
        "needs_review_due_to_conflict": conflict_detected,
    }

def process_multiple_images(image_paths: List[str], languages: Optional[List[str]] = None) -> dict:
    start = time.time()
    per_image_results = []
    overall_quality_scores = []
    all_quality_issues = []
    all_barcodes = []
    all_anomalies = []
    detected_languages_all = set()

    for idx, path in enumerate(image_paths):
        image_number = idx + 1
        logger.info(f"Processing image {image_number}/{len(image_paths)}: {path}")
        res = process_single_image(path, languages=languages)
        res["image_index"] = idx
        res["image_number"] = image_number
        res["image_path"] = path
        per_image_results.append(res)
        if res.get("success"):
            overall_quality_scores.append(res["quality"]["overall_score"])
            all_quality_issues.extend(res["quality"].get("issues", []))
            for bc in res.get("barcodes", []):
                bc_item = dict(bc)
                bc_item["source_image_index"] = idx
                bc_item["source_image_number"] = image_number
                all_barcodes.append(bc_item)
            
            if res.get("languages", {}).get("detected_languages"):
                detected_languages_all.update(res["languages"]["detected_languages"])
            
            if res.get("anomaly_detection", {}).get("findings"):
                for finding in res["anomaly_detection"]["findings"]:
                    f_item = dict(finding)
                    f_item["image_number"] = image_number
                    all_anomalies.append(f_item)

    per_field_candidates: Dict[str, list] = {k: [] for k in _empty_fields().keys()}
    for res in per_image_results:
        if not res.get("success"): continue
        for field_name, fdata in res.get("fields", {}).items():
            if fdata.get("value"):
                candidate = dict(fdata)
                candidate["image_index"] = res["image_index"]
                candidate["image_number"] = res["image_number"]
                per_field_candidates[field_name].append(candidate)

    fused_fields = {}
    for field_name in per_field_candidates:
        fused_fields[field_name] = _fuse_field_candidates(field_name, per_field_candidates[field_name])

    if not fused_fields.get("product_name", {}).get("value"):
        for res in sorted(per_image_results, key=lambda r: r.get("quality", {}).get("overall_score", 0), reverse=True):
            if res.get("success") and res.get("ocr_results"):
                pn = _detect_prominent_product_name(res["ocr_results"], fused_fields, res["original_image"].shape if res.get("original_image") is not None else (1000, 1000))
                if pn:
                    pn["source_image_index"] = res["image_index"]
                    pn["source_image_number"] = res["image_number"]
                    pn["conflict_detected"] = False
                    pn["all_image_candidates"] = [{"value": pn["value"], "confidence": pn["confidence"], "source_image_index": res["image_index"], "source_image_number": res["image_number"]}]
                    fused_fields["product_name"] = pn
                    break

    elapsed_ms = int((time.time() - start) * 1000)
    avg_quality = sum(overall_quality_scores) / len(overall_quality_scores) if overall_quality_scores else 0.8
    successful_images = sum(1 for r in per_image_results if r.get("success"))

    has_tampering = any(a.get("type") == "MRP_STICKER_OVERLAY" for a in all_anomalies)

    return {
        "success": True,
        "total_images": len(image_paths),
        "successful_images": successful_images,
        "fields": fused_fields,
        "barcodes": all_barcodes,
        "languages": {
            "detected_languages": list(detected_languages_all) if detected_languages_all else ["en"],
            "has_english": "en" in detected_languages_all or not detected_languages_all,
            "has_hindi": "hi" in detected_languages_all,
            "is_dual_language": "en" in detected_languages_all and "hi" in detected_languages_all
        },
        "anomaly_detection": {
            "has_anomaly": len(all_anomalies) > 0,
            "tampering_detected": has_tampering,
            "tampering_risk": "CRITICAL" if has_tampering else ("HIGH" if len(all_anomalies) > 1 else ("MEDIUM" if len(all_anomalies) == 1 else "LOW")),
            "findings": all_anomalies
        },
        "forensics": per_image_results[0].get("forensics", {}) if per_image_results else {},
        "quality": {
            "overall_score": round(avg_quality, 2),
            "issues": list(set(all_quality_issues)),
            "is_suitable": avg_quality >= 0.4,
            "quality_label": "Good" if avg_quality >= 0.75 else ("Fair" if avg_quality >= 0.5 else "Poor"),
        },
        "per_image_results": per_image_results,
        "has_conflicts": any(fdata.get("conflict_detected") for fdata in fused_fields.values()),
        "conflict_fields": [fname for fname, fdata in fused_fields.items() if fdata.get("conflict_detected")],
        "ocr_engine": "easyocr_multipass_spatial_v3",
    }
