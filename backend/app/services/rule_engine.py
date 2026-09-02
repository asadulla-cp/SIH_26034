from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from ..config import RULES_PATH
from .extractor import STANDARD_UNITS, FieldHit, MONTHS

MONTH_RE = re.compile(rf"(?:{MONTHS})\s+\d{{4}}|\d{{1,2}}[/-]\d{{4}}|\b(20\d{{2}}|19\d{{2}})\b", re.I)
PHONE_RE = re.compile(r"(1800[\s-]?\d{3}[\s-]?\d{3,4}|\+91[\s-]?\d{10}|\b\d{10}\b)")
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
MRP_AMT_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
AMBIGUOUS_MRP_RE = re.compile(r"[IlO][\d]{2,}|[\d][IlO][\d]")


@dataclass
class RuleResult:
    rule_id: str
    field: str
    version: str
    severity: str
    status: str  # PASS | FAIL | NEEDS_REVIEW
    detected: str | None
    expected: str
    reason: str
    confidence: float | None
    bbox: dict | None
    demo_simplified: bool
    legal_reference: str
    validation_type: str


def load_rule_pack() -> dict:
    return json.loads(Path(RULES_PATH).read_text(encoding="utf-8"))


def _conf_status(pack: dict, confidence: float | None, image_quality: float, missing: bool) -> str | None:
    policy = pack["status_policy"]
    if image_quality < policy["poor_image_quality_threshold"] and (missing or (confidence is not None and confidence < policy["review_confidence_threshold"])):
        return "NEEDS_REVIEW"
    if confidence is not None and confidence < policy["low_confidence_threshold"]:
        return "NEEDS_REVIEW"
    if confidence is not None and confidence < policy["review_confidence_threshold"] and not missing:
        return "NEEDS_REVIEW"
    return None


def _present(value: str | None) -> bool:
    return bool(value and str(value).strip() and str(value).strip().lower() not in {"none", "null", "n/a"})


def validate_fields(hits: dict[str, FieldHit], imported: bool, image_quality: float, ocr_available: bool) -> list[RuleResult]:
    pack = load_rule_pack()
    results: list[RuleResult] = []
    for rule in pack["rules"]:
        hit = hits.get(rule["field"], FieldHit(rule["field"], None, None, None))
        results.append(_run_rule(pack, rule, hit, hits, imported, image_quality, ocr_available))
    return results


def _run_rule(pack, rule, hit: FieldHit, hits: dict[str, FieldHit], imported: bool, image_quality: float, ocr_available: bool) -> RuleResult:
    vtype = rule["validation_type"]
    detected = hit.value
    conf = hit.confidence
    bbox = hit.bbox
    expected = rule["requirement"]
    missing = not _present(detected)

    def make(status, reason):
        gate = _conf_status(pack, conf, image_quality, missing)
        if status == "FAIL" and gate == "NEEDS_REVIEW":
            status = "NEEDS_REVIEW"
            reason = "OCR/image uncertainty — not auto-failed as legal non-compliance. " + reason
        if not ocr_available and missing:
            status = "NEEDS_REVIEW"
            reason = "OCR engine unavailable for this image; officer review required. " + reason
        return RuleResult(
            rule_id=rule["rule_id"],
            field=rule["field"],
            version=rule["version"],
            severity=rule["severity"],
            status=status,
            detected=detected,
            expected=expected,
            reason=reason,
            confidence=conf,
            bbox=bbox,
            demo_simplified=bool(rule.get("demo_simplified")),
            legal_reference=rule.get("legal_reference", ""),
            validation_type=vtype,
        )

    if vtype == "required_present":
        if missing:
            return make("FAIL", "Required declaration not detected in the supplied image.")
        return make("PASS", "Declaration detected.")

    if vtype == "address_quality":
        if missing:
            return make("FAIL", "Address not detected.")
        if len(detected.strip()) < 18 or not re.search(r"\d", detected):
            return make("FAIL", "Address appears incomplete (prototype check: too short or missing a number/PIN).")
        return make("PASS", "Address declaration detected.")

    if vtype == "net_quantity_with_unit":
        if missing:
            return make("FAIL", "Net quantity not detected.")
        if not re.search(r"\d", detected):
            return make("FAIL", "Net quantity has no numeric value.")
        unit_hit = hits.get("unit")
        unit = (unit_hit.value if unit_hit else None) or _unit(detected)
        if not unit:
            return make("FAIL", "Net quantity does not include a unit.")
        return make("PASS", "Net quantity with unit detected.")

    if vtype == "mrp_format":
        if missing:
            return make("FAIL", "Required MRP declaration not detected.")
        if AMBIGUOUS_MRP_RE.search(detected.replace(" ", "")) or "i99" in detected.lower():
            return make("NEEDS_REVIEW", "MRP characters are ambiguous (e.g. I vs 1). Human review required.")
        if not (re.search(r"(₹|rs\.?|inr|mrp)", detected, re.I) and re.search(r"\d", detected)):
            return make("FAIL", "MRP does not clearly show currency/rupees and a numeric value (prototype format check).")
        return make("PASS", "MRP declaration detected.")

    if vtype == "date_parseable":
        if missing:
            return make("FAIL", "Month/year of manufacture, packing or import not detected.")
        if not MONTH_RE.search(detected):
            return make("FAIL", "Date text was found but could not be parsed as month-year (prototype parser).")
        return make("PASS", "Date of manufacture/packing/import detected.")

    if vtype == "consumer_care_contact":
        if missing:
            return make("FAIL", "Consumer care details not detected.")
        if not (PHONE_RE.search(detected) or EMAIL_RE.search(detected)):
            return make("FAIL", "Consumer care text lacks a telephone number or email (prototype check).")
        return make("PASS", "Consumer care contact detected.")

    if vtype == "origin_if_imported":
        if not imported:
            return make("PASS", "Package not treated as imported; country-of-origin rule not triggered.")
        if missing:
            return make("FAIL", "Imported package without detected country of origin.")
        return make("PASS", "Country of origin detected for imported package.")

    if vtype == "standard_unit":
        unit_hit = hits.get("unit")
        unit = (unit_hit.value if unit_hit else None) or _unit(detected or "")
        nq = hits.get("net_quantity")
        if nq and not _present(nq.value) and not unit:
            return make("FAIL", "No unit could be associated with net quantity.")
        if unit and unit.lower() not in STANDARD_UNITS:
            return make("FAIL", f"Unit '{unit}' is not in the prototype standard-unit list.")
        if not unit:
            # if qty has unit inside
            unit = _unit((nq.value if nq else "") or "")
            if unit and unit.lower() in STANDARD_UNITS:
                return make("PASS", "Standard unit inferred from net quantity.")
            return make("FAIL", "Standard unit not detected.")
        return make("PASS", "Standard unit detected.")

    if vtype == "no_conflicting_mrp":
        mrp = hits.get("mrp")
        vals = (mrp.raw_matches if mrp else []) or []
        nums = []
        for v in vals:
            try:
                nums.append(float(v.replace(",", "")))
            except Exception:
                pass
        uniq = {round(n, 2) for n in nums}
        if len(uniq) > 1:
            return make("NEEDS_REVIEW", f"Multiple distinct MRP amounts detected: {sorted(uniq)}.")
        return make("PASS", "No conflicting MRP amounts detected.")

    return make("NEEDS_REVIEW", f"Unknown validation_type '{vtype}'.")


def _unit(s: str) -> str | None:
    m = re.search(r"(\d[\d.,]*)\s*([a-zA-Z]+)", s or "")
    return m.group(2).lower() if m else None


def overall_from(results: list[RuleResult], pack: dict | None = None) -> tuple[str, int]:
    pack = pack or load_rule_pack()
    score = pack["scoring"]["start"]
    has_fail = False
    has_review = False
    seen_fail_fields = set()
    for r in results:
        if r.status == "FAIL":
            has_fail = True
            if (r.field, r.severity) in seen_fail_fields:
                continue
            seen_fail_fields.add((r.field, r.severity))
            if r.severity == "high":
                score -= pack["scoring"]["deduct_high"]
            elif r.severity == "medium":
                score -= pack["scoring"]["deduct_medium"]
            else:
                score -= pack["scoring"]["deduct_low"]
        elif r.status == "NEEDS_REVIEW":
            has_review = True
    score = max(0, min(100, score))
    if has_fail:
        status = "NON_COMPLIANT"
    elif has_review:
        status = "NEEDS_REVIEW"
    else:
        status = "COMPLIANT"
    return status, score
