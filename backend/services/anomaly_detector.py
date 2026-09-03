"""
MetaLex AI Anomaly Detection Service
Detects MRP tampering, sticker overlays, overwritten date fields, and physical label damage
using computer vision techniques (edge gradients, color histogram comparison, contour analysis).
"""
try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger("metalex.anomaly")


def detect_mrp_sticker(img: np.ndarray, mrp_bbox: Optional[List[int]]) -> Dict[str, Any]:
    """
    Detects if an MRP area has a sticker pasted over the original printed packaging.
    Stickers produce sharp boundary edges, slight elevation shadows, and color/texture discontinuity.
    """
    if img is None or mrp_bbox is None or len(mrp_bbox) < 4:
        return {"sticker_detected": False, "confidence": 0.0, "reason": "No MRP bbox available"}

    h, w = img.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in mrp_bbox]
    
    # Clip to image bounds
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    if (x2 - x1) < 10 or (y2 - y1) < 10:
        return {"sticker_detected": False, "confidence": 0.0, "reason": "Bbox too small for analysis"}

    # Pad region slightly to capture sticker edges
    pad_x = int((x2 - x1) * 0.25)
    pad_y = int((y2 - y1) * 0.35)
    rx1, ry1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
    rx2, ry2 = min(w, x2 + pad_x), min(h, y2 + pad_y)

    roi = img[ry1:ry2, rx1:rx2]
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi

    # 1. Edge analysis for rectangular sticker border
    blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 140)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    has_rectangular_contour = False
    max_rect_area = 0
    roi_area = (rx2 - rx1) * (ry2 - ry1)
    
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(cnt)
            if area > (roi_area * 0.15) and area < (roi_area * 0.95):
                has_rectangular_contour = True
                max_rect_area = max(max_rect_area, area)

    # 2. Color/brightness gradient difference between inner bbox and outer border
    inner_roi = img[y1:y2, x1:x2]
    inner_mean = np.mean(inner_roi, axis=(0, 1)) if inner_roi.size > 0 else np.array([0, 0, 0])
    
    # Outer margin samples
    margin_top = img[ry1:y1, rx1:rx2] if y1 > ry1 else None
    margin_bottom = img[y2:ry2, rx1:rx2] if ry2 > y2 else None
    
    outer_means = []
    if margin_top is not None and margin_top.size > 0:
        outer_means.append(np.mean(margin_top, axis=(0, 1)))
    if margin_bottom is not None and margin_bottom.size > 0:
        outer_means.append(np.mean(margin_bottom, axis=(0, 1)))

    color_diff_score = 0.0
    if outer_means:
        outer_mean = np.mean(outer_means, axis=0)
        color_diff = np.linalg.norm(inner_mean - outer_mean)
        # Normalize color difference (0 to 1)
        color_diff_score = min(1.0, color_diff / 80.0)

    # Calculate overall sticker confidence
    confidence = 0.0
    if has_rectangular_contour and color_diff_score > 0.4:
        confidence = round(0.70 + (color_diff_score * 0.25), 2)
    elif has_rectangular_contour:
        confidence = 0.65
    elif color_diff_score > 0.65:
        confidence = round(color_diff_score * 0.85, 2)
    else:
        confidence = round(max(0.1, color_diff_score * 0.3), 2)

    is_sticker = confidence >= 0.60

    return {
        "sticker_detected": is_sticker,
        "confidence": confidence,
        "color_discontinuity": round(color_diff_score, 2),
        "rectangular_boundary": has_rectangular_contour,
        "bbox": [x1, y1, x2, y2],
        "evidence_region": [rx1, ry1, rx2, ry2],
        "details": "Possible adhesive sticker overlay detected on MRP" if is_sticker else "No sticker overlay detected"
    }


def detect_label_damage(img: np.ndarray) -> Dict[str, Any]:
    """
    Assesses physical label condition: water damage, fading, tears, and overall readability.
    """
    if img is None:
        return {"damage_detected": False, "readability_pct": 100.0, "condition": "Good"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # 1. Local Contrast analysis (Fading detection)
    std_dev = np.std(gray)
    contrast_score = min(100.0, (std_dev / 64.0) * 100.0)

    # 2. Color variance / water stain blotch detection
    stain_score = 0.0
    if len(img.shape) == 3:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        sat_std = np.std(sat)
        if sat_std > 50:
            stain_score = min(1.0, (sat_std - 50) / 40.0)

    # 3. Blurriness / wear
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_score = min(100.0, (laplacian_var / 300.0) * 100.0)

    # Readability percentage estimation
    readability_pct = round(max(10.0, min(100.0, (contrast_score * 0.45) + (blur_score * 0.55))), 1)

    issues = []
    condition = "Good"

    if readability_pct < 50.0:
        issues.append("Severe text fading and low contrast")
        condition = "Severely Faded / Worn"
    elif readability_pct < 70.0:
        issues.append("Moderate label wear / faded declarations")
        condition = "Moderately Faded"

    if stain_score > 0.5:
        issues.append("Possible moisture stains or color bleeding detected")
        if condition == "Good":
            condition = "Moisture Damaged"

    damage_detected = len(issues) > 0

    return {
        "damage_detected": damage_detected,
        "readability_pct": readability_pct,
        "condition": condition,
        "issues": issues,
        "contrast_level": round(contrast_score, 1),
        "sharpness_level": round(blur_score, 1)
    }


def analyze_font_consistency(img: np.ndarray, bboxes_by_field: Dict[str, List[int]]) -> Dict[str, Any]:
    """
    Compares text properties (average stroke thickness, stroke intensity) across fields
    to detect if dates or prices were overwritten with different ink/printer.
    """
    if img is None or not bboxes_by_field:
        return {"consistent": True, "anomalous_fields": [], "confidence": 0.0}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape[:2]

    field_intensities = {}
    
    for field, bbox in bboxes_by_field.items():
        if not bbox or len(bbox) < 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        crop = gray[y1:y2, x1:x2]
        if crop.size < 50:
            continue
            
        # Text ink intensity (darkest 20% of pixels)
        sorted_pixels = np.sort(crop.ravel())
        dark_pixels = sorted_pixels[:max(1, int(len(sorted_pixels) * 0.2))]
        field_intensities[field] = np.mean(dark_pixels)

    anomalous = []
    if len(field_intensities) >= 2:
        values = list(field_intensities.values())
        median_val = np.median(values)
        for field, val in field_intensities.items():
            # If ink intensity differs by more than 45 grayscale levels from median
            if abs(val - median_val) > 45:
                anomalous.append({
                    "field": field,
                    "difference": round(abs(val - median_val), 1),
                    "reason": "Ink darkness/font stroke significantly differs from surrounding declarations"
                })

    return {
        "consistent": len(anomalous) == 0,
        "anomalous_fields": anomalous,
        "confidence": 0.78 if anomalous else 0.90
    }


def run_full_anomaly_detection(img: np.ndarray, fields_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Orchestrates all anomaly and physical package integrity checks.
    """
    if img is None:
        return {
            "has_anomaly": False,
            "overall_status": "NORMAL",
            "tampering_risk": "LOW",
            "findings": []
        }

    # Extract bboxes
    mrp_bbox = None
    bboxes_dict = {}
    for f in fields_data:
        fname = f.get("field_name")
        bbox = f.get("bounding_box")
        if bbox:
            bboxes_dict[fname] = bbox
            if fname == "mrp":
                mrp_bbox = bbox

    # Run checks
    sticker_res = detect_mrp_sticker(img, mrp_bbox)
    damage_res = detect_label_damage(img)
    font_res = analyze_font_consistency(img, bboxes_dict)

    findings = []
    has_tampering = False

    if sticker_res.get("sticker_detected"):
        has_tampering = True
        findings.append({
            "type": "MRP_STICKER_OVERLAY",
            "severity": "CRITICAL",
            "confidence": sticker_res["confidence"],
            "title": "Possible MRP Sticker Tampering",
            "details": "Adhesive sticker boundary and color discontinuity detected over original MRP declaration.",
            "bbox": sticker_res.get("bbox")
        })

    if not font_res.get("consistent"):
        for af in font_res.get("anomalous_fields", []):
            findings.append({
                "type": "FONT_INCONSISTENCY",
                "severity": "HIGH",
                "confidence": font_res["confidence"],
                "title": f"Ink/Font Inconsistency in {af['field'].upper()}",
                "details": af["reason"]
            })

    if damage_res.get("damage_detected"):
        findings.append({
            "type": "PACKAGE_DAMAGE",
            "severity": "MEDIUM" if damage_res["readability_pct"] < 60 else "LOW",
            "confidence": 0.85,
            "title": f"Package Condition: {damage_res['condition']}",
            "details": f"Overall declaration readability: {damage_res['readability_pct']}%. " + "; ".join(damage_res.get("issues", []))
        })

    tampering_risk = "CRITICAL" if sticker_res.get("sticker_detected") else ("HIGH" if len(findings) > 1 else ("MEDIUM" if len(findings) == 1 else "LOW"))

    return {
        "has_anomaly": len(findings) > 0,
        "tampering_detected": has_tampering,
        "tampering_risk": tampering_risk,
        "findings": findings,
        "sticker_analysis": sticker_res,
        "damage_analysis": damage_res,
        "font_analysis": font_res
    }
