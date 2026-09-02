"""
MetaLex Rule Engine Unit Tests
Mandatory Suite: 15+ test cases verifying deterministic compliance logic.

Design principle: AI extracts. Deterministic rules decide. Evidence explains.
Low OCR confidence NEVER causes automatic legal non-compliance (must yield NEEDS_REVIEW).
"""
import pytest
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rules.rule_engine import RuleEngine, get_rule_engine


@pytest.fixture
def engine():
    return RuleEngine()


# ── Test 1: Fully Compliant Package ──
def test_fully_compliant_product(engine):
    fields = {
        "product_name": {"value": "Organic Basmati Rice", "confidence": 0.95, "bounding_box": [10, 10, 200, 50]},
        "net_quantity": {"value": "5 kg", "normalized_value": "5kg", "confidence": 0.92, "bounding_box": [10, 60, 100, 80]},
        "mrp": {"value": "₹450", "normalized_value": "₹450", "confidence": 0.90, "bounding_box": [10, 90, 120, 110]},
        "manufacturer": {"value": "Agro Pure Ltd, Delhi", "confidence": 0.88, "bounding_box": [10, 120, 300, 150]},
        "consumer_care": {"value": "customercare@agropure.com", "confidence": 0.85, "bounding_box": [10, 160, 250, 180]},
        "date": {"value": "08/2026", "normalized_value": "08/2026", "confidence": 0.91, "bounding_box": [10, 190, 120, 210]},
        "country_of_origin": {"value": "India", "confidence": 0.94, "bounding_box": [10, 220, 100, 240]},
    }
    result = engine.validate_all(fields)
    assert result["overall_status"] == "COMPLIANT"
    assert result["compliance_score"] == 100
    assert len(result["violations"]) == 0


# ── Test 2: Missing MRP Declaration ──
def test_missing_mrp_declaration(engine):
    fields = {
        "product_name": {"value": "Tea", "confidence": 0.95},
        "net_quantity": {"value": "250 g", "confidence": 0.92},
        "mrp": {"value": None, "confidence": 0.0},  # Missing!
        "manufacturer": {"value": "Tea Corp", "confidence": 0.88},
    }
    result = engine.validate_all(fields)
    assert result["overall_status"] == "NON_COMPLIANT"
    mrp_viol = [v for v in result["violations"] if v["field"] == "mrp" and v["rule_id"] == "LM-PC-003"]
    assert len(mrp_viol) == 1
    assert mrp_viol[0]["status"] == "FAIL"
    assert "not detected" in mrp_viol[0]["reason"].lower()


# ── Test 3: Missing Manufacturer Information ──
def test_missing_manufacturer(engine):
    fields = {
        "product_name": {"value": "Biscuits", "confidence": 0.90},
        "net_quantity": {"value": "100 g", "confidence": 0.90},
        "mrp": {"value": "₹30", "confidence": 0.90},
        "manufacturer": {"value": None, "confidence": 0.0},
    }
    result = engine.validate_all(fields)
    assert result["overall_status"] == "NON_COMPLIANT"
    mfg_viols = [v for v in result["violations"] if v["field"] == "manufacturer"]
    assert len(mfg_viols) > 0


# ── Test 4: Missing Consumer Care Details ──
def test_missing_consumer_care(engine):
    fields = {
        "product_name": {"value": "Detergent", "confidence": 0.90},
        "net_quantity": {"value": "1 kg", "confidence": 0.90},
        "mrp": {"value": "₹99", "confidence": 0.90},
        "manufacturer": {"value": "Clean Ltd", "confidence": 0.90},
        "consumer_care": {"value": None, "confidence": 0.0},
    }
    result = engine.validate_all(fields)
    assert result["overall_status"] == "NON_COMPLIANT"
    cc_viol = [v for v in result["violations"] if v["field"] == "consumer_care"]
    assert len(cc_viol) == 1


# ── Test 5: Low OCR Confidence Triggers NEEDS_REVIEW, Not Failure ──
def test_low_ocr_confidence_triggers_review(engine):
    fields = {
        "product_name": {"value": "Protein Bar", "confidence": 0.90},
        "net_quantity": {"value": "50g", "confidence": 0.90},
        "mrp": {"value": "₹I99", "confidence": 0.42},  # Low confidence OCR!
        "manufacturer": {"value": "Fit Foods", "confidence": 0.90},
        "consumer_care": {"value": "care@fit.com", "confidence": 0.90},
        "date": {"value": "05/2026", "confidence": 0.90},
    }
    result = engine.validate_all(fields)
    # Crucial SIH Principle: Low OCR confidence must NOT cause legal non-compliance!
    mrp_results = [r for r in result["results"] if r["field"] == "mrp" and r["rule_id"] == "LM-PC-003"]
    assert len(mrp_results) == 1
    assert mrp_results[0]["status"] == "NEEDS_REVIEW"
    assert "confidence is low" in mrp_results[0]["reason"].lower() or "low confidence" in mrp_results[0]["reason"].lower()


# ── Test 6: Non-Standard Unit Declaration ──
def test_non_standard_unit_declaration(engine):
    fields = {
        "net_quantity": {"value": "500 widgets", "normalized_value": "500 widgets", "confidence": 0.85},
    }
    res = engine.validate_field("net_quantity", fields["net_quantity"])
    unit_res = [r for r in res if r["rule_id"] == "LM-PC-011"]
    assert len(unit_res) == 1
    assert unit_res[0]["status"] == "NEEDS_REVIEW"
    assert "metric" in unit_res[0]["reason"].lower()


# ── Test 7: Standard Metric Units Pass ──
@pytest.mark.parametrize("unit_val", ["500 g", "1 kg", "200 ml", "2 L", "50 pieces", "10 nos"])
def test_valid_metric_units(engine, unit_val):
    field_data = {"value": unit_val, "normalized_value": unit_val, "confidence": 0.95}
    res = engine.validate_field("net_quantity", field_data)
    unit_res = [r for r in res if r["rule_id"] == "LM-PC-011"]
    assert len(unit_res) == 1
    assert unit_res[0]["status"] == "PASS"


# ── Test 8: Valid Alternative MRP Formats ──
@pytest.mark.parametrize("mrp_val", ["₹ 199", "Rs. 250", "MRP: ₹99.50", "M.R.P. Rs 499 (Incl. of all taxes)"])
def test_valid_mrp_formats(engine, mrp_val):
    field_data = {"value": mrp_val, "normalized_value": mrp_val, "confidence": 0.90}
    res = engine.validate_field("mrp", field_data)
    presence_rule = [r for r in res if r["rule_id"] == "LM-PC-003"]
    assert len(presence_rule) == 1
    assert presence_rule[0]["status"] == "PASS"


# ── Test 9: Zero or Negative Numeric Value ──
def test_zero_numeric_value(engine):
    field_data = {"value": "0 g", "normalized_value": "0g", "confidence": 0.90}
    res = engine.validate_field("net_quantity", field_data)
    num_rule = [r for r in res if r["rule_id"] == "LM-PC-009"]
    assert len(num_rule) == 1
    assert num_rule[0]["status"] == "FAIL"


# ── Test 10: Date Format Verification ──
@pytest.mark.parametrize("date_val", ["08/2026", "Aug 2026", "15/08/2026", "2026-08-15"])
def test_valid_date_formats(engine, date_val):
    field_data = {"value": date_val, "normalized_value": date_val, "confidence": 0.92}
    res = engine.validate_field("date", field_data)
    assert len(res) > 0
    assert res[0]["status"] == "PASS"


# ── Test 11: Empty / No OCR Result ──
def test_empty_ocr_result(engine):
    empty_fields = {}
    result = engine.validate_all(empty_fields)
    assert result["overall_status"] == "NON_COMPLIANT"
    assert result["compliance_score"] == 0
    assert result["failed"] > 0


# ── Test 12: Multiple Violations Accumulation ──
def test_multiple_violations_calculation(engine):
    # Package missing MRP, Manufacturer, and Consumer Care
    fields = {
        "product_name": {"value": "Mineral Water", "confidence": 0.95},
        "net_quantity": {"value": "1 L", "confidence": 0.95},
        "mrp": {"value": None, "confidence": 0.0},
        "manufacturer": {"value": None, "confidence": 0.0},
        "consumer_care": {"value": None, "confidence": 0.0},
    }
    result = engine.validate_all(fields)
    assert result["overall_status"] == "NON_COMPLIANT"
    assert len(result["violations"]) >= 3
    assert result["compliance_score"] <= 60


# ── Test 13: Country of Origin Conditional Rule ──
def test_country_of_origin_detection(engine):
    # When present
    res_present = engine.validate_field("country_of_origin", {"value": "India", "confidence": 0.95})
    assert res_present[0]["status"] == "PASS"

    # When missing (conditional rule shouldn't hard-fail if not known imported)
    res_missing = engine.validate_field("country_of_origin", {"value": None, "confidence": 0.0})
    assert res_missing[0]["status"] == "PASS"


# ── Test 14: Evidence and Source Text Integrity ──
def test_evidence_bounding_box_retention(engine):
    field_data = {
        "value": "₹199",
        "confidence": 0.90,
        "bounding_box": [50, 50, 150, 80],
        "source_text": "MRP ₹199"
    }
    res = engine.validate_field("mrp", field_data)
    assert res[0]["bounding_box"] == [50, 50, 150, 80]
    assert res[0]["evidence_type"] == "bounding_box"


# ── Test 15: Versioned Metadata Preservation ──
def test_versioned_rule_metadata(engine):
    all_rules = engine.get_all_rules()
    for r in all_rules:
        assert "rule_id" in r
        assert "rule_version" in r
        assert "source_reference" in r
        assert "severity" in r
