import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.rules.validators.base import ExtractedField
from backend.rules.validators.validators import (
    validate_presence, validate_format, validate_unit, validate_mrp, validate_date,
)
from backend.rules.rule_engine import get_rule_engine

engine = get_rule_engine()
RULES = {r["field"]: r for r in engine.get_rules()}


def ef(value=None, conf=0.9, normalized=None, bbox=None):
    return ExtractedField(
        field="x", value=value, normalized_value=normalized or value, confidence=conf,
        bounding_box=bbox or ({"x": 1, "y": 1, "w": 10, "h": 10} if value else None),
        source_text=value, extraction_method="test",
    )


# 1. Fully compliant MRP
def test_mrp_compliant():
    r = validate_mrp(RULES["mrp"], ef("₹199"))
    assert r.status == "PASS"


# 2. Missing MRP
def test_mrp_missing():
    r = validate_mrp(RULES["mrp"], ef(None, conf=0.0))
    assert r.status == "FAIL"


# 3. Malformed MRP (no currency symbol)
def test_mrp_malformed_no_currency():
    r = validate_mrp(RULES["mrp"], ef("199"))
    assert r.status == "FAIL"


# 4. MRP zero value
def test_mrp_zero_value():
    r = validate_mrp(RULES["mrp"], ef("₹0"))
    assert r.status == "FAIL"


# 5. Low OCR confidence MRP -> NEEDS_REVIEW, not auto-fail
def test_mrp_low_confidence_needs_review():
    r = validate_mrp(RULES["mrp"], ef("₹199", conf=0.35))
    assert r.status == "NEEDS_REVIEW"


# 6. Valid alternative currency format (Rs.)
def test_mrp_alternative_format_rs():
    r = validate_mrp(RULES["mrp"], ef("Rs. 299"))
    assert r.status == "PASS"


# 7. Net quantity valid unit
def test_quantity_valid_unit():
    r = validate_unit(RULES["net_quantity"], ef("1 kg"))
    assert r.status == "PASS"


# 8. Net quantity wrong/unsupported unit
def test_quantity_wrong_unit():
    r = validate_unit(RULES["net_quantity"], ef("500 units"))
    assert r.status == "FAIL"


# 9. Net quantity missing
def test_quantity_missing():
    r = validate_unit(RULES["net_quantity"], ef(None, conf=0.0))
    assert r.status == "FAIL"


# 10. Date valid MM/YYYY
def test_date_valid_mmYYYY():
    r = validate_date(RULES["mfg_date"], ef("03/2026"))
    assert r.status == "PASS"


# 11. Date valid Month YYYY format (alternative valid format)
def test_date_valid_month_name():
    r = validate_date(RULES["mfg_date"], ef("March 2026"))
    assert r.status == "PASS"


# 12. Date malformed
def test_date_malformed():
    r = validate_date(RULES["mfg_date"], ef("not-a-date"))
    assert r.status == "FAIL"


# 13. Presence: consumer care missing
def test_consumer_care_missing():
    r = validate_presence(RULES["consumer_care"], ef(None, conf=0.0))
    assert r.status == "FAIL"


# 14. Presence: consumer care present
def test_consumer_care_present():
    r = validate_presence(RULES["consumer_care"], ef("1800-123-4567"))
    assert r.status == "PASS"


# 15. Address format: too short / unstructured -> FAIL
def test_address_too_short():
    r = validate_format(RULES["address"], ef("XYZ"))
    assert r.status == "FAIL"


# 16. Address format: plausible full address -> PASS
def test_address_plausible():
    r = validate_format(RULES["address"], ef("Plot 12, Sector 5, Panipat, Haryana"))
    assert r.status == "PASS"


# 17. No OCR result at all (confidence 0, value None) across a field -> FAIL not crash
def test_no_ocr_result_manufacturer():
    r = validate_presence(RULES["manufacturer"], ef(None, conf=0.0))
    assert r.status == "FAIL"
    assert "not detected" in r.reason.lower()


# 18. Conflicting values handled via alternatives list (engine keeps top candidate, does not crash)
def test_field_with_alternatives_uses_best():
    field = ExtractedField(
        field="mrp", value="₹199", normalized_value="₹199", confidence=0.93,
        bounding_box={"x": 1, "y": 1, "w": 5, "h": 5}, source_text="₹199",
        extraction_method="test", alternatives=[{"value": "₹299", "confidence": 0.41}],
    )
    r = validate_mrp(RULES["mrp"], field)
    assert r.status == "PASS"
    assert r.detected_value == "₹199"


# 19. Incomplete image scenario: net quantity present but manufacturer missing (multi-field, partial)
def test_partial_incomplete_label():
    r_qty = validate_unit(RULES["net_quantity"], ef("200 g"))
    r_mfr = validate_presence(RULES["manufacturer"], ef(None, conf=0.0))
    assert r_qty.status == "PASS"
    assert r_mfr.status == "FAIL"


# 20. Multiple violations aggregate scoring sanity check
def test_rule_engine_score_and_status_multiple_violations():
    extracted = {
        "product_name": ef("Test Product"),
        "manufacturer": ef(None, conf=0.0),
        "address": ef(None, conf=0.0),
        "net_quantity": ef("500 units"),
        "mrp": ef("₹99"),
        "mfg_date": ef(None, conf=0.0),
        "consumer_care": ef(None, conf=0.0),
        "country_of_origin": ef(None, conf=0.0),
    }
    results = engine.validate_fields(extracted, is_imported=False)
    status = engine.overall_status(results)
    score = engine.compute_score(results)
    assert status == "NON_COMPLIANT"
    assert score < 100
