"""
Deterministic Rule Engine.

AI/OCR extracts. THIS FILE decides compliance. No LLM call exists anywhere
in this module, by design, so that legal decisions are always reproducible,
auditable, and independent of model drift.
"""
import json
import os
from typing import Dict, List
from .validators.base import ExtractedField, ValidationResult
from .validators.validators import VALIDATOR_MAP

RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")


class RuleEngine:
    def __init__(self, rules_path: str = RULES_PATH):
        with open(rules_path, "r") as f:
            data = json.load(f)
        self.ruleset_version = data["ruleset_version"]
        self.note = data["note"]
        self.rules = data["rules"]
        self.rules_by_field = {r["field"]: r for r in self.rules}

    def get_rules(self) -> List[dict]:
        return self.rules

    def validate_fields(self, extracted_fields: Dict[str, ExtractedField], is_imported: bool = False) -> List[ValidationResult]:
        """
        extracted_fields: mapping field_name -> ExtractedField
        Returns one ValidationResult per applicable rule, deterministic and ordered by rules.json order.
        """
        results = []
        for rule in self.rules:
            field_name = rule["field"]

            if rule["applicability"] == "imported_commodities" and not is_imported:
                continue  # rule not applicable -> skip, not a failure

            extracted = extracted_fields.get(field_name) or ExtractedField(
                field=field_name, value=None, normalized_value=None,
                confidence=0.0, bounding_box=None, source_text=None,
                extraction_method="not_found",
            )
            validator_fn = VALIDATOR_MAP.get(rule["validation_type"])
            if validator_fn is None:
                continue
            result = validator_fn(rule, extracted)
            results.append(result)
        return results

    @staticmethod
    def compute_score(results: List[ValidationResult]) -> int:
        """
        Weighted deterministic scoring:
        PASS = full weight, NEEDS_REVIEW = half weight, FAIL = zero weight.
        Severity weights: high=3, medium=2, low=1.
        """
        weight_map = {"high": 3, "medium": 2, "low": 1}
        total = 0
        earned = 0.0
        for r in results:
            w = weight_map.get(r.severity, 1)
            total += w
            if r.status == "PASS":
                earned += w
            elif r.status == "NEEDS_REVIEW":
                earned += w * 0.5
        if total == 0:
            return 100
        return round((earned / total) * 100)

    @staticmethod
    def overall_status(results: List[ValidationResult]) -> str:
        if any(r.status == "FAIL" and r.severity == "high" for r in results):
            return "NON_COMPLIANT"
        if any(r.status == "FAIL" for r in results):
            return "NON_COMPLIANT"
        if any(r.status == "NEEDS_REVIEW" for r in results):
            return "NEEDS_REVIEW"
        return "COMPLIANT"


_engine_instance = None


def get_rule_engine() -> RuleEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RuleEngine()
    return _engine_instance
