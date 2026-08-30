"""
Image preprocessing & quality assessment.
Steps: quality check -> grayscale -> denoise -> contrast (CLAHE) -> adaptive threshold candidate -> resize/upscale.
Perspective correction: attempts largest-quadrilateral detection; falls back to no-op if not confidently found
(never fabricates a warp that could distort real evidence).
"""
import cv2
import numpy as np
from typing import Dict, Tuple


def assess_quality(gray: np.ndarray) -> Dict:
    """Returns quality warnings using classic CV heuristics (no ML model)."""
    warnings = []
    h, w = gray.shape[:2]

    # Blur detection via variance of Laplacian
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = lap_var < 60
    if is_blurry:
        warnings.append("Image appears blurry (low edge sharpness). OCR accuracy may be reduced.")

    # Resolution check
    if max(h, w) < 500:
        warnings.append("Image resolution is low. Consider a closer, higher-resolution capture.")

    # Brightness check
    mean_brightness = float(np.mean(gray))
    if mean_brightness < 50:
        warnings.append("Image is very dark; declarations may not be readable.")
    elif mean_brightness > 220:
        warnings.append("Image appears overexposed/washed out.")

    return {
        "sharpness_score": round(float(lap_var), 2),
        "resolution": f"{w}x{h}",
        "mean_brightness": round(mean_brightness, 1),
        "warnings": warnings,
        "is_blurry": bool(is_blurry),
    }


def try_perspective_correction(bgr: np.ndarray) -> Tuple[np.ndarray, bool]:
    """
    Attempts to find the package's bounding quadrilateral and warp it flat.
    Returns (possibly_corrected_image, was_corrected).
    Conservative: only applies correction if a confident 4-point contour
    covering a large fraction of the image is found, to avoid destroying evidence.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return bgr, False

    img_area = bgr.shape[0] * bgr.shape[1]
    best_quad = None
    best_area = 0
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > best_area and area > 0.35 * img_area:
                best_area = area
                best_quad = approx

    if best_quad is None:
        return bgr, False

    pts = best_quad.reshape(4, 2).astype("float32")
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))
    if maxWidth < 50 or maxHeight < 50:
        return bgr, False

    dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(bgr, M, (maxWidth, maxHeight))
    return warped, True


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def preprocess_pipeline(bgr: np.ndarray) -> Dict:
    """
    Full pipeline: quality -> perspective correction -> resize/upscale -> contrast -> denoise.
    Returns dict with the final processed BGR image plus metadata for the report/UI.
    """
    gray0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    quality = assess_quality(gray0)

    corrected, was_corrected = try_perspective_correction(bgr)

    h, w = corrected.shape[:2]
    scale = 1.0
    if max(h, w) < 1200:
        scale = 1200 / max(h, w)
        corrected = cv2.resize(corrected, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    final_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    return {
        "processed_image": final_bgr,
        "display_image": corrected,  # color image (for overlay display), same coordinate space as OCR
        "quality": quality,
        "perspective_corrected": was_corrected,
        "upscale_factor": round(scale, 2),
    }
