"""
MetaLex Deterministic Rule Engine
AI extracts. Deterministic rules decide. Evidence explains.

This engine loads versioned rules from JSON and applies deterministic validation
to extracted fields. It NEVER uses LLM/AI to make legal compliance decisions.
"""
import json
import os
import re
from typing import Any
from pathlib import Path

RULES_DIR = Path(__file__).parent
RULES_FILE = RULES_DIR / "rules.json"

# Confidence threshold below which we mark NEEDS_REVIEW instead of FAIL
CONFIDENCE_REVIEW_THRESHOLD = 0.60


class RuleEngine:
    """Deterministic compliance rule engine."""

    def __init__(self, rules_path: str | None = None):
        path = Path(rules_path) if rules_path else RULES_FILE
        with open(path, "r") as f:
            data = json.load(f)
        self.rule_set_version = data.get("rule_set_version", "1.0.0")
        self.rule_set_name = data.get("rule_set_name", "Unknown")
        self.disclaimer = data.get("disclaimer", "")
        self.rules: list[dict] = data.get("rules", [])
        self._rules_by_field: dict[str, list[dict]] = {}
        self._rules_by_id: dict[str, dict] = {}
        for rule in self.rules:
            field = rule["field"]
            self._rules_by_field.setdefault(field, []).append(rule)
            self._rules_by_id[rule["rule_id"]] = rule

    def get_all_rules(self) -> list[dict]:
        return self.rules

    def get_rule(self, rule_id: str) -> dict | None:
        return self._rules_by_id.get(rule_id)

    def get_rules_for_field(self, field: str) -> list[dict]:
        return self._rules_by_field.get(field, [])

    def validate_field(self, field_name: str, extracted: dict) -> list[dict]:
        """
        Validate a single extracted field against all applicable rules.
        """
        rules_for_field = self.get_rules_for_field(field_name)
        results = []
        for rule in rules_for_field:
            result = self._apply_rule(rule, extracted)
            results.append(result)
        return results

    def validate_all(self, extracted_fields: dict[str, dict]) -> dict:
        """
        Validate all extracted fields against all rules.
        """
        all_results = []
        violations = []
        reviews = []
        passes = []

        # Check every rule
        for rule in self.rules:
            field_name = rule["field"]
            extracted = extracted_fields.get(field_name, {
                "value": None,
                "normalized_value": None,
                "confidence": 0.0,
                "bounding_box": None,
                "source_text": "",
            })
            result = self._apply_rule(rule, extracted)
            all_results.append(result)

            if result["status"] == "FAIL":
                violations.append(result)
            elif result["status"] == "NEEDS_REVIEW":
                reviews.append(result)
            elif result["status"] == "PASS":
                passes.append(result)

        # Calculate compliance score
        # Core mandatory checks count towards score
        scored_results = [r for r in all_results if r["status"] in ("PASS", "FAIL", "NEEDS_REVIEW")]
        if not extracted_fields or all(not (v.get("value") if isinstance(v, dict) else v) for v in extracted_fields.values()):
            score = 0
        else:
            total_checks = len(scored_results)
            passed_checks = len(passes)
            score = round((passed_checks / total_checks) * 100) if total_checks > 0 else 0

        # Determine overall status
        if len(violations) > 0:
            overall = "NON_COMPLIANT"
        elif len(reviews) > 0:
            overall = "NEEDS_REVIEW"
        else:
            overall = "COMPLIANT"

        return {
            "overall_status": overall,
            "compliance_score": score,
            "total_checks": len(all_results),
            "passed": len(passes),
            "failed": len(violations),
            "needs_review": len(reviews),
            "results": all_results,
            "violations": violations,
            "reviews": reviews,
            "passes": passes,
            "rule_set_version": self.rule_set_version,
            "rule_set_name": self.rule_set_name,
            "disclaimer": self.disclaimer,
        }

    def _apply_rule(self, rule: dict, extracted: dict) -> dict:
        """Apply a single rule to an extracted field."""
        validation_type = rule.get("validation_type", "presence")
        value = extracted.get("value")
        normalized = extracted.get("normalized_value") or value
        confidence = extracted.get("confidence", 0.0)
        bbox = extracted.get("bounding_box")

        # Base result
        result = {
            "rule_id": rule["rule_id"],
            "rule_title": rule["title"],
            "field": rule["field"],
            "severity": rule["severity"],
            "rule_version": rule["rule_version"],
            "is_prototype_rule": rule.get("is_prototype", True),
            "source_reference": rule.get("source_reference", ""),
            "detected_value": value,
            "confidence": confidence,
            "bounding_box": bbox,
            "expected_requirement": rule["requirement"],
            "status": "PASS",
            "reason": "",
            "evidence_type": "bounding_box" if bbox else ("not_detected" if not value else "image"),
        }

        # Dispatch to validator
        if validation_type == "presence":
            self._validate_presence(result, value, confidence, rule)
        elif validation_type == "presence_and_format":
            self._validate_presence_and_format(result, value, normalized, confidence, rule)
        elif validation_type == "numeric_value":
            self._validate_numeric(result, value, normalized, confidence, rule)
        elif validation_type == "unit_check":
            self._validate_unit(result, value, normalized, confidence, rule)
        elif validation_type == "conditional_presence":
            self._validate_conditional(result, value, confidence, rule, extracted)
        else:
            self._validate_presence(result, value, confidence, rule)

        # Generate explanation
        tmpl = rule.get("explanation_template", "{field} {status}. {detail}")
        status_word = "was found" if result["status"] == "PASS" else (
            "requires review" if result["status"] == "NEEDS_REVIEW" else "was not found or is non-compliant"
        )
        result["explanation"] = tmpl.format(
            status=status_word,
            detail=result["reason"] or "No issues detected.",
            field=rule["field"],
        )

        return result

    def _validate_presence(self, result: dict, value: Any, confidence: float, rule: dict):
        """Check if a required field is present."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a"):
            if confidence > 0 and confidence < CONFIDENCE_REVIEW_THRESHOLD:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Field detected with low confidence ({confidence:.0%}). Manual verification required."
            else:
                result["status"] = "FAIL"
                result["reason"] = f"Required declaration not detected in the supplied image."
                result["evidence_type"] = "not_detected"
        elif confidence > 0 and confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Field detected as '{value}' but OCR confidence is low ({confidence:.0%}). Manual verification required."
        else:
            result["status"] = "PASS"
            result["reason"] = f"Declaration detected: '{value}'"

    def _validate_presence_and_format(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """Check presence and format pattern."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a"):
            if confidence > 0 and confidence < CONFIDENCE_REVIEW_THRESHOLD:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Field detected with low confidence ({confidence:.0%}). Manual verification required."
            else:
                result["status"] = "FAIL"
                result["reason"] = f"Required declaration not detected in the supplied image."
                result["evidence_type"] = "not_detected"
            return

        if confidence > 0 and confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Field detected as '{value}' but OCR confidence is low ({confidence:.0%}). Manual verification required."
            return

        patterns = rule.get("format_patterns", [])
        if patterns:
            check_text = (normalized or value).strip()
            matched = any(re.search(p, check_text, re.IGNORECASE) for p in patterns)
            if not matched:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Declaration '{value}' detected but format may not match expected pattern. Manual verification recommended."
            else:
                result["status"] = "PASS"
                result["reason"] = f"Declaration detected and format validated: '{value}'"
        else:
            result["status"] = "PASS"
            result["reason"] = f"Declaration detected: '{value}'"

    def _validate_numeric(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """Validate numeric value."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a"):
            result["status"] = "FAIL"
            result["reason"] = "Numeric check failed because required declaration is missing."
            result["evidence_type"] = "not_detected"
            return

        check_val = normalized or value
        numbers = re.findall(r"[\d]+\.?\d*", str(check_val))
        if not numbers:
            if confidence > 0 and confidence < CONFIDENCE_REVIEW_THRESHOLD:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Could not extract numeric value from '{value}' with low confidence ({confidence:.0%})."
            else:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"No numeric value found in declaration '{value}'. Manual verification recommended."
            return

        num = float(numbers[0])
        min_val = rule.get("min_value", None)
        if min_val is not None and num <= min_val:
            result["status"] = "FAIL"
            result["reason"] = f"Numeric value {num} is not greater than {min_val}."
        else:
            result["status"] = "PASS"
            result["reason"] = f"Valid numeric value detected: {num}"

    def _validate_unit(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """Validate units."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a"):
            result["status"] = "FAIL"
            result["reason"] = "Unit check failed because required declaration is missing."
            result["evidence_type"] = "not_detected"
            return

        valid_units = rule.get("valid_units", [])
        if not valid_units:
            result["status"] = "PASS"
            result["reason"] = "No unit constraints specified."
            return

        check_val = (normalized or value).lower()
        unit_match = re.search(r"[a-zA-Z]+", check_val)
        if unit_match:
            unit = unit_match.group().lower()
            if unit in [u.lower() for u in valid_units]:
                result["status"] = "PASS"
                result["reason"] = f"Valid unit '{unit}' detected."
            else:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Unit '{unit}' may not be a standard metric unit. Manual verification recommended."
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Could not identify unit in '{value}'. Manual verification recommended."

    def _validate_conditional(self, result: dict, value: Any, confidence: float, rule: dict, extracted: dict):
        """Conditional validation."""
        if value and str(value).strip().lower() not in ("", "none", "missing", "not detected", "n/a"):
            result["status"] = "PASS"
            result["reason"] = f"Declaration detected: '{value}'"
        else:
            result["status"] = "PASS"
            result["reason"] = f"Declaration optional or conditionally applicable."


# Singleton instance
_engine: RuleEngine | None = None


def get_rule_engine() -> RuleEngine:
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine
