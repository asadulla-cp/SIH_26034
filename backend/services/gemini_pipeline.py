"""
MetaLex — Gemini 2.5 Flash Extraction Pipeline
Uses Google Gemini 3.6 Flash multimodal capabilities with:
  - Native structured JSON schema output (no regex parsing needed)
  - System instruction for Legal Metrology officer persona
  - Cross-image reasoning across all uploaded angles
  - Confidence scoring per field
  - EasyOCR bounding-box overlay for UI evidence
"""
import os
import re
import json
import logging
from typing import Optional
try:
    import cv2
except ImportError:
    cv2 = None
import PIL.Image
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("metalex.gemini")

MODEL_ID = "gemini-3.6-flash"

SYSTEM_INSTRUCTION = """You are a certified Legal Metrology Inspector trained under the
Legal Metrology (Packaged Commodities) Rules, 2011 (India).

Your task is to carefully examine packaged commodity label images and extract ONLY the
mandatory declaration fields required by law. You must NOT hallucinate or guess values.

FIELD EXTRACTION RULES (follow strictly):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• product_name  → The main brand/product name printed most prominently. NOT a flavour variant or tagline.

• mrp           → The Maximum Retail Price. ONLY extract from text explicitly labelled
                  "MRP", "M.R.P.", or "Maximum Retail Price". Include the currency symbol
                  (₹ or Rs). NEVER extract nutritional numbers, batch codes, or barcodes as MRP.

• net_quantity  → Net weight, volume, or count. Look for "Net Wt", "Net Weight", "Vol",
                  "Contents", "Net Content". Include units (g, kg, ml, L, pcs).
                  NEVER extract per-serving nutritional sizes as net quantity.

• date_of_manufacture → Manufacturing or packaging date. Look for "MFD", "Mfd.", "Mfg Date",
                        "Manufactured On", "PKD", "Packed On". Return as text exactly as on label.

• use_by_date   → Expiry, best-before, or use-by date. Look for "Use By", "Expiry",
                  "Best Before", "BB", "EXP". Return as text exactly as on label.

• manufacturer  → Full name and address of the manufacturer, packer, or importer.
                  This is usually a multi-line text block. Include city, state, pin if visible.

• country_of_origin → Look for "Made in", "Country of Origin", "Product of", "Manufactured in".
                      Usually a single country name.

• customer_care → Consumer helpline. Look for "Consumer Care", "Customer Care",
                  "Helpline", "Toll Free", "Contact Us" with phone number or email.

CONFIDENCE SCORING:
  1.0  → Text is fully visible, unambiguous, clearly labelled
  0.7–0.9 → Text is readable but slightly unclear (minor blur/angle)
  0.4–0.6 → Text is partially visible or context-inferred
  0.1–0.3 → Barely readable, high uncertainty
  0.0  → Field not found in ANY of the images

MULTI-IMAGE INSTRUCTION:
If multiple images are provided, they are ALL photos of the SAME physical package from
different angles. A field found on ANY image is considered present. Prioritize the
reading with the highest clarity/confidence.
"""

EXTRACTION_PROMPT = """Examine all provided package images carefully.

Extract each mandatory declaration field and return a JSON object with this EXACT structure.
For fields not found on any image, set value to null and confidence to 0.0.
Do not guess or fabricate values. Return ONLY the JSON object, no explanation.

{
  "product_name":        {"value": "...", "confidence": 0.0},
  "mrp":                 {"value": "...", "confidence": 0.0},
  "net_quantity":        {"value": "...", "confidence": 0.0},
  "date_of_manufacture": {"value": "...", "confidence": 0.0},
  "use_by_date":         {"value": "...", "confidence": 0.0},
  "manufacturer":        {"value": "...", "confidence": 0.0},
  "country_of_origin":   {"value": "...", "confidence": 0.0},
  "customer_care":       {"value": "...", "confidence": 0.0}
}"""

FIELD_LABELS = {
    "product_name": "Product Name",
    "mrp": "MRP",
    "net_quantity": "Net Quantity",
    "date_of_manufacture": "Date of Manufacture",
    "use_by_date": "Use By / Best Before",
    "manufacturer": "Manufacturer/Packer",
    "country_of_origin": "Country of Origin",
    "customer_care": "Customer Care",
}

ALL_FIELDS = list(FIELD_LABELS.keys())


# ─────────────────────── Helpers ────────────────────────────────────────────

def _get_api_key():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not set. Add it to your .env file: GEMINI_API_KEY=<your_key>"
        )
    return api_key


def _load_pil_image(path: str) -> PIL.Image.Image:
    """Load and resize image for Gemini (max 2048px longest side, RGB)."""
    img = PIL.Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    max_dim = 2048
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, PIL.Image.LANCZOS)
    return img


def _safe_extract_json(text: str) -> dict:
    """Robustly parse JSON from Gemini response (handles markdown code fences)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        logger.error(f"Could not parse Gemini JSON response: {text[:300]}")
        return {}


def _find_bbox_in_ocr(value: str, ocr_results: list) -> Optional[list]:
    """Find bounding box of an extracted value string within OCR results."""
    if not value or not ocr_results:
        return None
    val_lower = str(value).lower()
    val_words = set(val_lower.split())
    for item in ocr_results:
        ocr_text = item.get("text", "").lower()
        if val_lower in ocr_text:
            return item.get("bbox_rect")
        ocr_words = set(ocr_text.split())
        shared = val_words & ocr_words
        if val_words and len(shared) / len(val_words) >= 0.6:
            return item.get("bbox_rect")
    return None


def _assess_image_quality(file_path: str) -> dict:
    """Quick image quality estimate using blur/brightness heuristics."""
    try:
        img = cv2.imread(file_path)
        if img is None:
            return {"overall_score": 0.5, "quality_label": "Unknown", "issues": ["Could not read image"]}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = gray.mean()
        issues = []
        score = 1.0
        if blur_score < 100:
            issues.append("Image is blurry")
            score -= 0.3
        if brightness < 50:
            issues.append("Image is too dark")
            score -= 0.2
        elif brightness > 220:
            issues.append("Image is overexposed")
            score -= 0.1
        score = max(0.0, min(1.0, score))
        if score >= 0.8:
            label = "Good"
        elif score >= 0.5:
            label = "Fair"
        else:
            label = "Poor"
        return {"overall_score": round(score, 2), "quality_label": label, "issues": issues}
    except Exception as e:
        return {"overall_score": 0.7, "quality_label": "Unknown", "issues": [str(e)]}


# ─────────────────────── Main Pipeline ──────────────────────────────────────

# ─────────────────────── Main Pipeline ──────────────────────────────────────

def process_with_gemini(file_paths: list[str]) -> dict:
    """
    Run Gemini 2.5 Flash extraction on one or more package images via REST API.
    Returns a field dict in the same schema as ocr_pipeline.process_multiple_images().
    """
    import base64
    import requests

    api_key = _get_api_key()
    url = f"https://generativelanguage.googleapis.com/v1alpha/models/{MODEL_ID}:generateContent?key={api_key}"

    # ── Load and encode all images ───────────────────────────────────────────
    quality_scores = []
    image_parts = []
    for fp in file_paths:
        try:
            pil_img = _load_pil_image(fp)
            import io
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=90)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            image_parts.append({
                "inline_data": {"mime_type": "image/jpeg", "data": b64}
            })
            quality_scores.append(_assess_image_quality(fp))
        except Exception as e:
            logger.warning(f"Could not load image {fp}: {e}")
            quality_scores.append({"overall_score": 0.0, "quality_label": "Failed", "issues": [str(e)]})

    if not image_parts:
        raise ValueError("No valid package images could be loaded for Gemini processing.")

    image_note = ""
    if len(image_parts) > 1:
        image_note = (
            f"\n\nNOTE: You are viewing {len(image_parts)} photos of the SAME physical package "
            f"from different angles/sides. Inspect ALL images before concluding a field is absent."
        )

    # ── Build request payload ────────────────────────────────────────────────
    parts = image_parts + [{"text": EXTRACTION_PROMPT + image_note}]

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.05,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        },
    }

    # ── Call Gemini REST API ─────────────────────────────────────────────────
    logger.info(f"Calling {MODEL_ID} REST API with {len(image_parts)} image(s)...")
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as api_err:
        logger.error(f"Gemini API error: {api_err}")
        raise RuntimeError(f"Gemini extraction failed: {api_err}") from api_err

    logger.info(f"Gemini response (first 600 chars): {raw_text[:600]}")
    extracted = _safe_extract_json(raw_text)

    # ── Get EasyOCR results for bounding-box UI overlay ─────────────────────
    ocr_results = []
    try:
        from backend.services.ocr_pipeline import run_ocr
        img0 = cv2.imread(file_paths[0])
        if img0 is not None:
            ocr_results = run_ocr(img0)
    except Exception as e:
        logger.warning(f"OCR bbox extraction skipped: {e}")

    # ── Remap Gemini field names → rule engine field names ───────────────────
    FIELD_REMAP = {
        "date_of_manufacture": "date",
        "use_by_date": "date",          # merge into single date field (take whichever found)
        "customer_care": "consumer_care",
    }

    remapped_fields = {}
    for field_key in ALL_FIELDS:
        raw = extracted.get(field_key) or {}
        val = raw.get("value") if isinstance(raw, dict) else None
        conf = float(raw.get("confidence", 0.0)) if isinstance(raw, dict) else 0.0
        conf = max(0.0, min(1.0, conf))

        if val is not None and str(val).strip().lower() in ("", "null", "none", "n/a", "not found", "not visible"):
            val = None

        bbox = _find_bbox_in_ocr(val, ocr_results) if val else None

        target_key = FIELD_REMAP.get(field_key, field_key)

        candidate = {
            "value": val,
            "confidence": conf,
            "score": conf,
            "reason": f"Gemini {MODEL_ID} multimodal extraction",
            "bbox": bbox,
            "source_image_number": 1,
        } if val else None

        entry = {
            "value": val,
            "normalized_value": val,
            "confidence": conf,
            "extraction_method": f"gemini_{MODEL_ID.replace('-', '_')}" if val else "not_detected",
            "bounding_box": bbox,
            "source_text": val or "",
            "candidates": [candidate] if candidate else [],
            "all_image_candidates": [candidate] if candidate else [],
            "conflict_detected": False,
            "source_image_index": 0,
            "source_image_number": 1,
        }

        # For remapped keys, only overwrite if this has a better value
        if target_key in remapped_fields:
            existing = remapped_fields[target_key]
            if val and (not existing.get("value") or conf > existing.get("confidence", 0)):
                remapped_fields[target_key] = entry
        else:
            remapped_fields[target_key] = entry

    fused_fields = remapped_fields

    # ── Per-image summaries ──────────────────────────────────────────────────
    detected_fields = [k for k, v in fused_fields.items() if v.get("value")]
    per_image_results = []
    for i, fp in enumerate(file_paths):
        q = quality_scores[i] if i < len(quality_scores) else {"overall_score": 0.9, "quality_label": "Good", "issues": []}
        per_image_results.append({
            "image_index": i,
            "image_number": i + 1,
            "success": True,
            "fields_found": detected_fields,
            "quality": q,
            "annotated_image": None,
        })

    avg_quality = sum(q["overall_score"] for q in quality_scores) / len(quality_scores) if quality_scores else 0.9
    quality_issues = []
    for q in quality_scores:
        quality_issues.extend(q.get("issues", []))

    overall_quality = {
        "overall_score": round(avg_quality, 2),
        "quality_label": "Good" if avg_quality >= 0.75 else ("Fair" if avg_quality >= 0.5 else "Poor"),
        "issues": list(set(quality_issues)),
    }

    logger.info(f"Gemini extraction complete. Fields detected: {detected_fields}")

    return {
        "fields": fused_fields,
        "per_image_results": per_image_results,
        "has_conflicts": False,
        "conflict_fields": [],
        "quality": overall_quality,
        "ocr_engine": f"gemini_{MODEL_ID}",
    }
