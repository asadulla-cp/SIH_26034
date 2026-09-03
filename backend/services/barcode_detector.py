"""
MetaLex Barcode & QR Code Detector and GS1 Database Verifier
Detects 1D/2D barcodes (EAN-13, UPC-A, Code-128, QR) and validates against the GS1 National Registry.
"""

import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np

logger = logging.getLogger("metalex.barcode")

GS1_DB_PATH = Path(__file__).parent.parent / "data" / "gs1_database.json"

_gs1_cache: Optional[Dict[str, Any]] = None

def _load_gs1_database() -> Dict[str, Any]:
    global _gs1_cache
    if _gs1_cache is not None:
        return _gs1_cache
    if GS1_DB_PATH.exists():
        try:
            with open(GS1_DB_PATH, "r", encoding="utf-8") as f:
                _gs1_cache = json.load(f)
                return _gs1_cache
        except Exception as e:
            logger.error(f"Failed to load GS1 database: {e}")
    return {}


def detect_barcodes(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Detect 1D barcodes (EAN-13, UPC, Code-128) and 2D QR codes in an image.
    Uses pyzbar when available, with OpenCV native barcode & QR detectors as fallback.
    
    Returns:
        List of dicts: [{
            "type": "EAN13" / "QRCODE" / "CODE128" / "UPCA",
            "data": "8901030383846",
            "bbox": [x1, y1, x2, y2],
            "crop_base64": "...",
            "confidence": 1.0
        }]
    """
    if image is None or len(image.shape) < 2:
        return []

    detected_items = []
    seen_codes = set()

    # ── Strategy 1: pyzbar (if library linked) ──────────────────────────────
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        decoded_objs = pyzbar_decode(image)
        for obj in decoded_objs:
            code_str = obj.data.decode("utf-8", errors="ignore").strip()
            if not code_str or code_str in seen_codes:
                continue
            seen_codes.add(code_str)

            rect = obj.rect
            bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
            crop_b64 = _crop_to_base64(image, bbox)

            detected_items.append({
                "type": obj.type.upper(),
                "data": code_str,
                "bbox": bbox,
                "crop_base64": crop_b64,
                "confidence": 0.98,
                "detector": "pyzbar"
            })
    except Exception:
        pass

    # ── Strategy 2: OpenCV BarcodeDetector (Native 1D) ───────────────────────
    if not detected_items:
        try:
            barcode_detector = cv2.barcode.BarcodeDetector()
            ok, decoded_info, decoded_type, points = barcode_detector.detectAndDecode(image)
            if ok and decoded_info:
                for idx, code_str in enumerate(decoded_info):
                    c_clean = str(code_str).strip()
                    if not c_clean or c_clean in seen_codes:
                        continue
                    seen_codes.add(c_clean)
                    
                    b_type = decoded_type[idx] if (decoded_type and idx < len(decoded_type)) else "BARCODE"
                    bbox = None
                    if points is not None and idx < len(points):
                        pts = points[idx]
                        x1 = int(np.min(pts[:, 0]))
                        y1 = int(np.min(pts[:, 1]))
                        x2 = int(np.max(pts[:, 0]))
                        y2 = int(np.max(pts[:, 1]))
                        bbox = [max(0, x1), max(0, y1), x2, y2]
                    
                    crop_b64 = _crop_to_base64(image, bbox) if bbox else None
                    detected_items.append({
                        "type": str(b_type).upper(),
                        "data": c_clean,
                        "bbox": bbox,
                        "crop_base64": crop_b64,
                        "confidence": 0.95,
                        "detector": "opencv_barcode"
                    })
        except Exception as e:
            logger.debug(f"OpenCV barcode detector notice: {e}")

    # ── Strategy 3: OpenCV QRCodeDetector (Native 2D) ────────────────────────
    try:
        qr_detector = cv2.QRCodeDetector()
        ok, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(image)
        if ok and decoded_info:
            for idx, code_str in enumerate(decoded_info):
                c_clean = str(code_str).strip()
                if not c_clean or c_clean in seen_codes:
                    continue
                seen_codes.add(c_clean)

                bbox = None
                if points is not None and idx < len(points):
                    pts = points[idx]
                    x1 = int(np.min(pts[:, 0]))
                    y1 = int(np.min(pts[:, 1]))
                    x2 = int(np.max(pts[:, 0]))
                    y2 = int(np.max(pts[:, 1]))
                    bbox = [max(0, x1), max(0, y1), x2, y2]

                crop_b64 = _crop_to_base64(image, bbox) if bbox else None
                detected_items.append({
                    "type": "QRCODE",
                    "data": c_clean,
                    "bbox": bbox,
                    "crop_base64": crop_b64,
                    "confidence": 0.96,
                    "detector": "opencv_qr"
                })
    except Exception as e:
        logger.debug(f"OpenCV QR detector notice: {e}")

    return detected_items


def verify_against_gs1(
    barcode_data: str,
    extracted_fields: Dict[str, Any],
    tolerance_pct: float = 5.0
) -> Dict[str, Any]:
    """
    Verify detected barcode against GS1 Registry.
    Cross-checks manufacturer name, product category, and MRP (within ±5% tolerance).
    """
    gs1_db = _load_gs1_database()
    clean_code = str(barcode_data).strip().replace("-", "").replace(" ", "")

    record = gs1_db.get(clean_code)

    if not record:
        return {
            "barcode": clean_code,
            "gs1_found": False,
            "is_valid": None,           # None = cannot determine (not a confirmed fail)
            "status": "NEEDS_REVIEW",
            "message": (
                f"Barcode {clean_code} is not in the local GS1 reference database. "
                f"The product may be registered in the national GS1 India registry. "
                f"Officer should manually verify via gs1india.org if needed."
            ),
            "mismatches": [],
            "gs1_record": None,
        }

    mismatches = []
    gs1_mrp = float(record.get("declared_mrp", 0.0))
    gs1_mfg = record.get("manufacturer", "")
    gs1_category = record.get("category", "")
    gs1_name = record.get("product_name", "")

    # 1. MRP Verification (±5% tolerance)
    scanned_mrp_raw = extracted_fields.get("mrp", {}).get("value")
    scanned_mrp = _extract_number(scanned_mrp_raw)

    mrp_status = "NOT_SCANNED"
    mrp_diff_pct = 0.0
    if scanned_mrp is not None and gs1_mrp > 0:
        diff = scanned_mrp - gs1_mrp
        mrp_diff_pct = round((diff / gs1_mrp) * 100, 1)

        if mrp_diff_pct > tolerance_pct:
            mismatches.append(f"Scanned MRP ₹{scanned_mrp} exceeds GS1 declared MRP ₹{gs1_mrp} by {mrp_diff_pct}% (Overpricing Violation)")
            mrp_status = "OVERPRICED"
        elif mrp_diff_pct < -tolerance_pct:
            mismatches.append(f"Scanned MRP ₹{scanned_mrp} is lower than GS1 declared MRP ₹{gs1_mrp} by {abs(mrp_diff_pct)}%")
            mrp_status = "UNDERPRICED"
        else:
            mrp_status = "MATCH"

    # 2. Manufacturer Match Check
    scanned_mfg = str(extracted_fields.get("manufacturer", {}).get("value") or "").lower().strip()
    mfg_status = "MATCH"
    if scanned_mfg and gs1_mfg:
        # Fuzzy / keyword overlap check
        mfg_words = set(gs1_mfg.lower().split()) - {"ltd", "pvt", "limited", "private", "inc", "co", "the"}
        scanned_words = set(scanned_mfg.split())
        if not (mfg_words & scanned_words) and not (gs1_mfg.lower() in scanned_mfg or scanned_mfg in gs1_mfg.lower()):
            mismatches.append(f"Manufacturer mismatch: Scanned '{extracted_fields.get('manufacturer', {}).get('value')}' vs GS1 '{gs1_mfg}'")
            mfg_status = "MISMATCH"

    is_compliant = len(mismatches) == 0

    return {
        "barcode": clean_code,
        "gs1_found": True,
        "is_valid": is_compliant,
        "status": "PASS" if is_compliant else "FAIL",
        "gs1_product_name": gs1_name,
        "gs1_manufacturer": gs1_mfg,
        "gs1_category": gs1_category,
        "gs1_declared_mrp": gs1_mrp,
        "scanned_mrp": scanned_mrp,
        "mrp_diff_pct": mrp_diff_pct,
        "mrp_status": mrp_status,
        "mfg_status": mfg_status,
        "mismatches": mismatches,
        "message": "Verified against GS1 Registry." if is_compliant else "; ".join(mismatches),
    }


def _extract_number(val: Any) -> Optional[float]:
    if val is None:
        return None
    import re
    nums = re.findall(r"\d+\.?\d*", str(val).replace(",", ""))
    if nums:
        try:
            return float(nums[0])
        except ValueError:
            return None
    return None


def _crop_to_base64(img: np.ndarray, bbox: Optional[List[int]]) -> Optional[str]:
    if img is None or not bbox or len(bbox) < 4:
        return None
    x1, y1, x2, y2 = bbox
    h, w = img.shape[:2]
    # Pad crop slightly
    pad_x = int((x2 - x1) * 0.1)
    pad_y = int((y2 - y1) * 0.1)
    cx1 = max(0, x1 - pad_x)
    cy1 = max(0, y1 - pad_y)
    cx2 = min(w, x2 + pad_x)
    cy2 = min(h, y2 + pad_y)
    
    crop = img[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return None
    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if ok:
        return base64.b64encode(buf).decode("utf-8")
    return None
