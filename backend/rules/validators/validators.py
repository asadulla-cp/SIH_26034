"""
Deterministic validators. Pure functions: (rule_dict, ExtractedField) -> ValidationResult.
No ML/LLM calls anywhere in this file.
"""
import re
from datetime import datetime
from .base import ExtractedField, ValidationResult, review_or


def _evidence_note(extracted: ExtractedField) -> str:
    if extracted.bounding_box:
        return "Evidence region located on supplied package image."
    if extracted.value:
        return "Evidence text detected but precise region unavailable."
    return "Not detected in supplied image."


def _base_result(rule: dict, extracted: ExtractedField, status: str, reason: str) -> ValidationResult:
    status_phrase = {
        "PASS": "detected and satisfies requirement",
        "FAIL": "missing or invalid",
        "NEEDS_REVIEW": "detected with low confidence and requires manual review",
    }[status]
    return ValidationResult(
        rule_id=rule["rule_id"],
        rule_version=rule["rule_version"],
        rule_status=rule.get("rule_status", "prototype"),
        title=rule["title"],
        field=rule["field"],
        severity=rule["severity"],
        status=status,
        detected_value=extracted.value,
        expected_requirement=rule["requirement"],
        reason=reason if reason else rule["explanation_template"].format(status_phrase=status_phrase),
        confidence=extracted.confidence,
        evidence_bounding_box=extracted.bounding_box,
        evidence_note=_evidence_note(extracted),
    )


def validate_presence(rule: dict, extracted: ExtractedField) -> ValidationResult:
    if not extracted.value:
        return _base_result(rule, extracted, "FAIL", "Required declaration was not detected anywhere on the package image.")
    status = review_or("PASS", extracted)
    reason = "" if status == "PASS" else f"Field detected but OCR confidence ({extracted.confidence:.0%}) is below the review threshold."
    return _base_result(rule, extracted, status, reason)


def validate_presence_conditional(rule: dict, extracted: ExtractedField) -> ValidationResult:
    # Same as presence, but caller may choose not to invoke this rule at all
    # when applicability condition (e.g. "is imported") is not met.
    return validate_presence(rule, extracted)


def validate_format(rule: dict, extracted: ExtractedField) -> ValidationResult:
    if not extracted.value:
        return _base_result(rule, extracted, "FAIL", "Required declaration was not detected anywhere on the package image.")
    # Address format check: require at least 2 comma/line separated components and length > 8
    val = extracted.normalized_value or extracted.value
    plausible = len(val) > 8 and (("," in val) or (" " in val and len(val.split()) >= 3))
    if not plausible:
        status = review_or("FAIL", extracted)
        reason = "Detected text is too short/unstructured to be a complete address." if status == "FAIL" else "Low OCR confidence; manual review needed to confirm address completeness."
        return _base_result(rule, extracted, status, reason)
    status = review_or("PASS", extracted)
    return _base_result(rule, extracted, status, "")


def validate_unit(rule: dict, extracted: ExtractedField) -> ValidationResult:
    if not extracted.value:
        return _base_result(rule, extracted, "FAIL", "Net quantity declaration was not detected on the package image.")
    allowed = [u.lower() for u in rule.get("allowed_units", [])]
    val = (extracted.normalized_value or extracted.value).lower()
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([a-z]+)", val)
    if not m:
        status = review_or("FAIL", extracted)
        reason = "Could not identify a numeric quantity with a unit." if status == "FAIL" else "Low OCR confidence; unable to confirm quantity/unit reliably."
        return _base_result(rule, extracted, status, reason)
    unit = m.group(2)
    if unit not in allowed:
        status = review_or("FAIL", extracted)
        reason = f"Unit '{unit}' is not among recognized standard units ({', '.join(allowed)})." if status == "FAIL" else "Low OCR confidence on unit; manual review needed."
        return _base_result(rule, extracted, status, reason)
    status = review_or("PASS", extracted)
    return _base_result(rule, extracted, status, "")


def validate_mrp(rule: dict, extracted: ExtractedField) -> ValidationResult:
    if not extracted.value:
        return _base_result(rule, extracted, "FAIL", "MRP declaration was not detected on the package image.")
    val = extracted.normalized_value or extracted.value
    m = re.search(r"(?:₹|rs\.?|inr)\s*([0-9]+(?:[.,][0-9]+)?)", val, re.IGNORECASE)
    if not m:
        status = review_or("FAIL", extracted)
        reason = "Detected text does not contain a currency-prefixed numeric MRP value." if status == "FAIL" else "Low OCR confidence; currency/number pattern unclear, needs manual check."
        return _base_result(rule, extracted, status, reason)
    try:
        amount = float(m.group(1).replace(",", ""))
    except ValueError:
        amount = 0
    if amount <= 0:
        status = review_or("FAIL", extracted)
        reason = "MRP numeric value must be greater than zero."
        return _base_result(rule, extracted, status, reason)
    status = review_or("PASS", extracted)
    return _base_result(rule, extracted, status, "")


def validate_date(rule: dict, extracted: ExtractedField) -> ValidationResult:
    if not extracted.value:
        return _base_result(rule, extracted, "FAIL", "Manufacturing/packing date was not detected on the package image.")
    val = extracted.normalized_value or extracted.value
    patterns = [
        r"\b(0?[1-9]|1[0-2])[/\-\.](\d{4})\b",           # MM/YYYY
        r"\b(\d{1,2})[/\-\.](0?[1-9]|1[0-2])[/\-\.](\d{2,4})\b",  # DD/MM/YYYY
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b",  # Mon YYYY
    ]
    matched = any(re.search(p, val, re.IGNORECASE) for p in patterns)
    if not matched:
        status = review_or("FAIL", extracted)
        reason = "Detected text does not match a recognizable date format (MM/YYYY, DD/MM/YYYY, or Month YYYY)." if status == "FAIL" else "Low OCR confidence; date format unclear."
        return _base_result(rule, extracted, status, reason)
    status = review_or("PASS", extracted)
    return _base_result(rule, extracted, status, "")


VALIDATOR_MAP = {
    "presence": validate_presence,
    "presence_conditional": validate_presence_conditional,
    "format": validate_format,
    "unit": validate_unit,
    "mrp": validate_mrp,
    "date": validate_date,
}
