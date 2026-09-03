"""
MetaLex Deterministic Rule Engine — v2.0.0
SIH26034 Full Rulebook Implementation

AI extracts. Deterministic rules decide. Evidence explains.

Implements all 22 rules from the SIH26034 Legal Metrology Rulebook including:
  - Exemption engine (Rules 3, 26) — runs BEFORE any declaration check
  - Vague qualifier ban (Rule 12(6))
  - MRP wording + tax-inclusive validator (Rule 2(m), 6(1)(e))
  - Banned imperial unit check (Rule 13)
  - Standard pack size validator (Rule 5, Schedule II)
  - Pan masala micro-package override (Second Amendment Rules 2025)
  - External-DB checks flagged as UNABLE_TO_VERIFY (Rules 27-30, 18(2))
  - Medical device category routing
"""
import json
import re
from typing import Any
from pathlib import Path

RULES_DIR = Path(__file__).parent
RULES_FILE = RULES_DIR / "rules.json"

# OCR confidence threshold — below this we surface NEEDS_REVIEW instead of hard FAIL
CONFIDENCE_REVIEW_THRESHOLD = 0.60

# Severity scoring defaults (if not specified in rule JSON)
DEFAULT_SEVERITY_POINTS = {
    "critical": 10,
    "high": 7,
    "medium": 5,
    "low": 2,
}

# Risk level thresholds (0-100 score)
RISK_LEVELS = [
    (0, 20, "low", "Low Risk"),
    (21, 50, "medium", "Medium Risk"),
    (51, 80, "high", "High Risk"),
    (81, 100, "critical", "Critical Risk"),
]

# Commodity categories that short-circuit certain checks
FOOD_CATEGORIES = {"food", "food_article", "fssai", "edible"}
MEDICAL_DEVICE_CATEGORIES = {"medical_device", "medical device", "device"}
BIDI_CATEGORIES = {"bidi", "beedi"}
INCENSE_CATEGORIES = {"incense_stick", "incense stick", "agarbatti"}
LPG_ADMIN_CATEGORIES = {"lpg_admin_price", "lpg cylinder", "14.2kg lpg", "5kg lpg"}
SEED_CATEGORIES = {"seed", "seeds"}
PAN_MASALA_CATEGORIES = {"pan_masala", "pan masala", "gutkha", "gutka"}
RESTAURANT_CATEGORIES = {"restaurant", "hotel", "fast_food", "fast food"}
DRUG_PRICE_CTRL = {"drugs_price_control", "scheduled_formulation", "non_scheduled_formulation"}
AGRI_CATEGORIES = {"agricultural_produce", "agri_produce"}


class RuleEngine:
    """Deterministic compliance rule engine — SIH26034 v2.0.0."""

    def __init__(self, rules_path: str | None = None):
        path = Path(rules_path) if rules_path else RULES_FILE
        with open(path, "r") as f:
            data = json.load(f)

        self.rule_set_version = data.get("rule_set_version", "2.0.0")
        self.rule_set_name = data.get("rule_set_name", "Unknown")
        self.disclaimer = data.get("disclaimer", "")
        self.categories = data.get("categories", {})
        self.exemption_categories = data.get("exemption_categories", {})
        self.standard_pack_sizes: dict[str, list] = data.get("standard_pack_sizes", {})
        self.banned_qualifiers: list[str] = data.get("banned_quantity_qualifiers", [])
        self.valid_metric_units: dict[str, list] = data.get("valid_metric_units", {})
        self.banned_units: list[str] = data.get("banned_units", [])
        self.mrp_wording_patterns: list[str] = data.get("mrp_required_wording_patterns", [])
        self.mrp_tax_patterns: list[str] = data.get("mrp_tax_inclusive_patterns", [])
        self.rules: list[dict] = data.get("rules", [])

        # Build lookup indexes
        self._rules_by_field: dict[str, list[dict]] = {}
        self._rules_by_id: dict[str, dict] = {}
        for rule in self.rules:
            field = rule["field"]
            self._rules_by_field.setdefault(field, []).append(rule)
            self._rules_by_id[rule["rule_id"]] = rule

        # Flat valid-unit list
        self._all_valid_units = [
            u.lower()
            for units in self.valid_metric_units.values()
            for u in units
        ]
        self._all_banned_units = [u.lower() for u in self.banned_units]

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def get_all_rules(self) -> list[dict]:
        return self.rules

    def get_rule(self, rule_id: str) -> dict | None:
        return self._rules_by_id.get(rule_id)

    def get_rules_for_field(self, field: str) -> list[dict]:
        return self._rules_by_field.get(field, [])

    def validate_all(self, extracted_fields: dict[str, dict], context: dict | None = None) -> dict:
        """
        Validate all extracted fields against all rules.

        Args:
            extracted_fields: dict keyed by field_name with {value, normalized_value, confidence, bounding_box}
            context: optional dict with {commodity_category, is_imported, net_quantity_grams, package_type}

        Returns:
            Full validation result dict.
        """
        ctx = context or {}
        commodity = (ctx.get("commodity_category") or "").lower().strip()
        is_imported = ctx.get("is_imported", False)
        net_qty_grams = ctx.get("net_quantity_grams", None)  # numeric grams/ml for exemption checks

        # Step 1 — Exemption engine: determine what Chapter II even applies to
        exemptions = self._compute_exemptions(commodity, net_qty_grams, ctx)

        all_results: list[dict] = []
        violations: list[dict] = []
        reviews: list[dict] = []
        passes: list[dict] = []

        for rule in self.rules:
            field_name = rule["field"]
            extracted = extracted_fields.get(field_name, {
                "value": None,
                "normalized_value": None,
                "confidence": 0.0,
                "bounding_box": None,
                "source_text": "",
            })
            result = self._apply_rule(rule, extracted, exemptions, commodity, is_imported, net_qty_grams)
            all_results.append(result)

            status = result["status"]
            if status == "FAIL":
                violations.append(result)
            elif status == "NEEDS_REVIEW":
                reviews.append(result)
            elif status == "PASS":
                passes.append(result)
            # EXEMPT and UNABLE_TO_VERIFY don't count toward score

        # Score: only PASS/FAIL/NEEDS_REVIEW rules that are NOT exempt/external
        scored = [r for r in all_results if r["status"] in ("PASS", "FAIL", "NEEDS_REVIEW")]
        total_scored = len(scored)
        passed_scored = sum(1 for r in scored if r["status"] == "PASS")
        score = round((passed_scored / total_scored) * 100) if total_scored > 0 else 0

        # Overall status
        if violations:
            overall = "NON_COMPLIANT"
        elif reviews:
            overall = "NEEDS_REVIEW"
        else:
            overall = "COMPLIANT"

        # ── Severity scoring ──────────────────────────────────────────────
        # Calculate max possible severity points across ALL rules (not just scored)
        max_severity_points = sum(
            r.get("severity_points", DEFAULT_SEVERITY_POINTS.get(r.get("severity", "medium"), 5))
            for r in self.rules
        )
        # Calculate actual violation severity points
        violation_severity_points = 0
        severity_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in violations:
            pts = v.get("severity_points", DEFAULT_SEVERITY_POINTS.get(v.get("severity", "medium"), 5))
            violation_severity_points += pts
            level = v.get("severity_level", v.get("severity", "medium"))
            if level in severity_breakdown:
                severity_breakdown[level] += 1

        severity_score = round((violation_severity_points / max_severity_points) * 100) if max_severity_points > 0 else 0
        severity_score = min(100, severity_score)

        risk_level = "low"
        risk_label = "Low Risk"
        for low, high, level, label in RISK_LEVELS:
            if low <= severity_score <= high:
                risk_level = level
                risk_label = label
                break

        # Sort violations by severity points (descending)
        violations.sort(key=lambda v: v.get("severity_points", 0), reverse=True)

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
            "exemptions_applied": list(exemptions),
            "rule_set_version": self.rule_set_version,
            "rule_set_name": self.rule_set_name,
            "disclaimer": self.disclaimer,
            # Severity scoring
            "severity_score": severity_score,
            "risk_level": risk_level,
            "risk_label": risk_label,
            "severity_breakdown": severity_breakdown,
            "violation_severity_points": violation_severity_points,
            "max_severity_points": max_severity_points,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Exemption Engine
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_exemptions(self, commodity: str, net_qty_grams: float | None, ctx: dict) -> set[str]:
        """
        Determine which exemptions apply to this package.
        Must run BEFORE any declaration checks.
        """
        exemptions: set[str] = set()

        # Commodity-category exemptions
        if commodity in FOOD_CATEGORIES:
            exemptions.add("food")
        if commodity in BIDI_CATEGORIES:
            exemptions.add("bidi")
        if commodity in INCENSE_CATEGORIES:
            exemptions.add("incense_stick")
        if commodity in LPG_ADMIN_CATEGORIES:
            exemptions.add("lpg_admin_price")
        if commodity in SEED_CATEGORIES:
            exemptions.add("seed")
        if commodity in MEDICAL_DEVICE_CATEGORIES:
            exemptions.add("medical_device")
        if commodity in RESTAURANT_CATEGORIES:
            exemptions.add("restaurant_hotel")
        if commodity in DRUG_PRICE_CTRL:
            exemptions.add("drugs_price_control")

        # Agricultural >50 kg
        if commodity in AGRI_CATEGORIES and net_qty_grams and net_qty_grams > 50000:
            exemptions.add("agri_above_50kg")

        # Micro-package ≤10 g/ml — but NOT pan masala
        if net_qty_grams is not None and net_qty_grams <= 10:
            if commodity not in PAN_MASALA_CATEGORIES:
                exemptions.add("micro_package_under_10g")

        # Large packages >25 kg (25,000 g) outside Chapter II
        # Cement/fertiliser bags up to 50 kg still covered
        if net_qty_grams and net_qty_grams > 25000:
            cat = commodity
            if cat not in {"cement", "fertiliser", "fertilizer"}:
                exemptions.add("above_25kg")
        
        # Third Schedule "when packed" qualifier allowed for soaps/lotions/creams
        if commodity in {"soap", "lotion", "cream"}:
            exemptions.add("third_schedule_when_packed")

        return exemptions

    # ──────────────────────────────────────────────────────────────────────────
    # Rule Dispatcher
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_rule(
        self,
        rule: dict,
        extracted: dict,
        exemptions: set[str],
        commodity: str,
        is_imported: bool,
        net_qty_grams: float | None,
    ) -> dict:
        """Apply a single rule to an extracted field, respecting exemptions."""
        vtype = rule.get("validation_type", "presence")
        value = extracted.get("value")
        normalized = extracted.get("normalized_value") or value
        confidence = float(extracted.get("confidence") or 0.0)
        bbox = extracted.get("bounding_box")

        result = {
            "rule_id": rule["rule_id"],
            "rule_title": rule["title"],
            "field": rule["field"],
            "severity": rule["severity"],
            "severity_level": rule.get("severity_level", rule.get("severity", "medium")),
            "severity_points": rule.get("severity_points", DEFAULT_SEVERITY_POINTS.get(rule.get("severity", "medium"), 5)),
            "rule_version": rule["rule_version"],
            "is_prototype_rule": rule.get("is_prototype", True),
            "source_reference": rule.get("source_reference", ""),
            "legal_basis": rule.get("legal_basis", ""),
            "penalty_section": rule.get("penalty_section", ""),
            "penalty_amount": rule.get("penalty_amount", ""),
            "amendment_notes": rule.get("amendment_notes"),
            "detected_value": value,
            "confidence": confidence,
            "bounding_box": bbox,
            "expected_requirement": rule["requirement"],
            "status": "PASS",
            "reason": "",
            "evidence_type": "bounding_box" if bbox else ("not_detected" if not value else "image"),
        }

        # ── Check if this rule's exemptions apply ──────────────────────────
        rule_exemptions = rule.get("exemptions", [])
        for ex in rule_exemptions:
            if ex in exemptions:
                result["status"] = "EXEMPT"
                result["reason"] = f"Exempt: {self.exemption_categories.get(ex, ex)}"
                return self._add_explanation(result, rule)

        # ── Full Chapter II exemption (micro-package or above-25kg) ────────
        if "micro_package_under_10g" in exemptions and vtype != "exemption_check":
            result["status"] = "EXEMPT"
            result["reason"] = "Package ≤10 g/ml — fully exempt from Rule 6 declarations (Rule 26(a)). Not pan masala."
            return self._add_explanation(result, rule)

        if "above_25kg" in exemptions and rule.get("applicability") != "wholesale_packages":
            result["status"] = "EXEMPT"
            result["reason"] = "Package >25 kg/25 L — outside Chapter II scope (Rule 3)."
            return self._add_explanation(result, rule)

        # ── Dispatch to validator ──────────────────────────────────────────
        dispatch = {
            "presence": self._validate_presence,
            "presence_and_format": self._validate_presence_and_format,
            "numeric_value": self._validate_numeric,
            "unit_check": self._validate_unit,
            "conditional_presence": lambda r, v, n, c, ru: self._validate_conditional(r, v, n, c, ru, is_imported),
            "vague_word_check": self._validate_vague_words,
            "mrp_format": self._validate_mrp_format,
            "mrp_tax_wording": self._validate_mrp_tax_wording,
            "standard_pack_check": lambda r, v, n, c, ru: self._validate_standard_pack(r, v, n, c, ru, commodity, net_qty_grams),
            "exemption_check": lambda r, v, n, c, ru: self._validate_exemption_info(r, v, n, c, ru, exemptions, commodity, net_qty_grams),
            "tamper_check": self._validate_tamper,
            "font_size_check": self._validate_font_size,
            "font_size_measurement": lambda r, v, n, c, ru: self._validate_font_size_measurement(r, v, n, c, ru, extracted),
            "pdp_placement_check": self._validate_pdp_placement,
            "external_db_check": self._validate_external_db,
            "barcode_gs1_check": lambda r, v, n, c, ru: self._validate_barcode_gs1(r, v, n, c, ru, extracted),
            "dual_language_check": lambda r, v, n, c, ru: self._validate_dual_language(r, v, n, c, ru, extracted),
            "anomaly_tampering_check": lambda r, v, n, c, ru: self._validate_anomaly_tampering(r, v, n, c, ru, extracted),
        }

        validator = dispatch.get(vtype, self._validate_presence)
        validator(result, value, normalized, confidence, rule)

        return self._add_explanation(result, rule)

    # ──────────────────────────────────────────────────────────────────────────
    # Individual Validators
    # ──────────────────────────────────────────────────────────────────────────

    def _validate_presence(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-001, 002, 006, 019 — simple presence check."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Field detected with low OCR confidence ({confidence:.0%}). Manual verification required."
            else:
                result["status"] = "FAIL"
                result["reason"] = "Required declaration not detected in the supplied image."
                result["evidence_type"] = "not_detected"
        elif 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Field detected as '{value}' but OCR confidence is low ({confidence:.0%}). Manual verification required."
        else:
            result["status"] = "PASS"
            result["reason"] = f"Declaration detected: '{value}'"

    def _validate_presence_and_format(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-003, 005 — presence + regex format check."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Field detected with low OCR confidence ({confidence:.0%}). Manual verification required."
            else:
                result["status"] = "FAIL"
                result["reason"] = "Required declaration not detected in the supplied image."
                result["evidence_type"] = "not_detected"
            return

        if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Field detected as '{value}' but OCR confidence is low ({confidence:.0%}). Manual verification required."
            return

        patterns = rule.get("format_patterns", [])
        if patterns:
            text = str(normalized or value).strip()
            matched = any(re.search(p, text, re.IGNORECASE) for p in patterns)
            if not matched:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"Value '{value}' detected but does not match expected format. Manual verification recommended."
            else:
                result["status"] = "PASS"
                result["reason"] = f"Declaration detected and format validated: '{value}'"
        else:
            result["status"] = "PASS"
            result["reason"] = f"Declaration detected: '{value}'"

    def _validate_numeric(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-008, 009 — positive numeric value check."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            result["status"] = "FAIL"
            result["reason"] = "Numeric check failed — declaration is missing."
            result["evidence_type"] = "not_detected"
            return

        nums = re.findall(r"\d+\.?\d*", str(normalized or value))
        if not nums:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"No numeric value extractable from '{value}'. Manual verification needed."
            return

        num = float(nums[0])
        min_val = rule.get("min_value", None)
        if min_val is not None and num <= min_val:
            result["status"] = "FAIL"
            result["reason"] = f"Numeric value {num} is not greater than {min_val}. A non-zero value is required."
        else:
            result["status"] = "PASS"
            result["reason"] = f"Valid positive numeric value detected: {num}"

    def _validate_unit(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-010 — metric unit validity; flag banned imperial/count units."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            result["status"] = "FAIL"
            result["reason"] = "Unit check failed — net quantity declaration is missing."
            result["evidence_type"] = "not_detected"
            return

        text = str(normalized or value).lower()
        # Extract the unit token (letters only)
        unit_tokens = re.findall(r"[a-zA-Z/²³]+", text)

        # Check for banned units first
        for tok in unit_tokens:
            if tok in self._all_banned_units:
                result["status"] = "FAIL"
                result["reason"] = (
                    f"Banned unit detected: '{tok}'. Only SI/metric units are permitted under Rule 13. "
                    f"Imperial units (lb, oz, gallon, yard, inch, dozen, etc.) are explicitly prohibited."
                )
                return

        # Check if at least one valid metric unit is present
        found_valid = any(tok in self._all_valid_units for tok in unit_tokens)
        if found_valid:
            found_tok = next(tok for tok in unit_tokens if tok in self._all_valid_units)
            result["status"] = "PASS"
            result["reason"] = f"Valid metric unit detected: '{found_tok}'"
        elif unit_tokens:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Unit token '{unit_tokens[0]}' not in standard metric unit list. Manual verification needed."
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Could not identify a unit in '{value}'. Manual verification needed."

    def _validate_vague_words(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-011 — Rule 12(6) vague qualifier ban."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            # If quantity is missing, that's caught by LM-PC-003 — just pass here
            result["status"] = "PASS"
            result["reason"] = "No quantity text to check for vague qualifiers."
            return

        text = str(normalized or value).lower()
        banned = rule.get("banned_qualifiers", self.banned_qualifiers)
        found = [q for q in banned if re.search(r'\b' + re.escape(q) + r'\b', text)]

        if found:
            result["status"] = "FAIL"
            result["reason"] = (
                f"Vague/misleading qualifier(s) detected: {found}. "
                f"Rule 12(6) prohibits these words adjacent to the net quantity declaration."
            )
        else:
            result["status"] = "PASS"
            result["reason"] = "No banned vague qualifiers detected in quantity declaration."

    def _validate_mrp_format(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-004 — MRP presence + wording format check."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
                result["status"] = "NEEDS_REVIEW"
                result["reason"] = f"MRP detected with low confidence ({confidence:.0%}). Manual verification required."
            else:
                result["status"] = "FAIL"
                result["reason"] = "MRP declaration not detected. Required on all pre-packaged commodities (Rule 6(1)(e))."
                result["evidence_type"] = "not_detected"
            return

        if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"MRP detected as '{value}' but OCR confidence is low ({confidence:.0%}). Manual verification required."
            return

        text = str(normalized or value).strip()

        # Check for MRP wording
        has_mrp_wording = any(
            re.search(p, text, re.IGNORECASE) for p in self.mrp_wording_patterns
        )
        # Check for numeric value
        has_numeric = bool(re.search(r"\d+", text))

        if not has_mrp_wording:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                f"MRP text '{value}' detected but prescribed wording ('Maximum Retail Price Rs/₹…' or 'MRP Rs/₹…') "
                f"not confirmed. Manual verification recommended."
            )
        elif not has_numeric:
            result["status"] = "FAIL"
            result["reason"] = f"MRP wording found but no numeric price value detected in '{value}'."
        else:
            result["status"] = "PASS"
            result["reason"] = f"MRP declaration detected with valid wording and numeric value: '{value}'"

    def _validate_mrp_tax_wording(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-014 — 'inclusive of all taxes' clause check."""
        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a", "null"):
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = "MRP declaration not detected — tax-inclusive clause cannot be verified."
            return

        if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"MRP detected with low confidence ({confidence:.0%}) — tax-inclusive clause unverifiable."
            return

        text = str(normalized or value).strip()
        has_tax_clause = any(re.search(p, text, re.IGNORECASE) for p in self.mrp_tax_patterns)

        if has_tax_clause:
            result["status"] = "PASS"
            result["reason"] = f"MRP 'inclusive of all taxes' wording confirmed in: '{value}'"
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                f"MRP detected as '{value}' but 'inclusive of all taxes' clause not confirmed. "
                f"Rule 2(m) requires this wording. Manual verification recommended."
            )

    def _validate_standard_pack(
        self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict,
        commodity: str, net_qty_grams: float | None
    ):
        """LM-PC-012 — Schedule II standard pack size conformity."""
        schedule_ii_commodities = rule.get("schedule_ii_commodities", [])
        if commodity not in schedule_ii_commodities:
            result["status"] = "PASS"
            result["reason"] = f"Commodity '{commodity}' is not a Second-Schedule commodity — standard pack size check not applicable."
            return

        if not value or str(value).strip().lower() in ("", "none", "missing", "not detected", "n/a"):
            result["status"] = "FAIL"
            result["reason"] = "Standard pack size cannot be verified — net quantity is missing."
            result["evidence_type"] = "not_detected"
            return

        # Extract numeric value
        nums = re.findall(r"\d+\.?\d*", str(normalized or value))
        if not nums:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Cannot extract numeric value from '{value}' to check against Schedule II pack sizes."
            return

        qty = float(nums[0])
        permitted = self.standard_pack_sizes.get(commodity, [])
        if not permitted:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"No Schedule II pack size list found for '{commodity}'. Manual verification required."
            return

        if qty in permitted:
            result["status"] = "PASS"
            result["reason"] = f"Declared quantity {qty} is in the Schedule II permitted list for '{commodity}': {permitted}"
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                f"Declared quantity {qty} is NOT in the Schedule II standard pack sizes for '{commodity}': {permitted}. "
                f"Note: the 'non-standard size declaration' proviso was reportedly withdrawn w.e.f. 01.07.2012 — "
                f"verify current status before escalating to FAIL."
            )

    def _validate_exemption_info(
        self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict,
        exemptions: set[str], commodity: str, net_qty_grams: float | None
    ):
        """LM-PC-013 — micro-package exemption + pan masala override info."""
        is_pan_masala = commodity in PAN_MASALA_CATEGORIES

        if net_qty_grams is not None and net_qty_grams <= 10 and is_pan_masala:
            result["status"] = "FAIL"
            result["reason"] = (
                f"Pan masala with net quantity ≤10 g ({net_qty_grams} g) detected. "
                f"The micro-package exemption (Rule 26(a)) does NOT apply to pan masala "
                f"per Second Amendment Rules 2025 (effective 01.02.2026). Full declarations required."
            )
        elif net_qty_grams is not None and net_qty_grams <= 10:
            result["status"] = "EXEMPT"
            result["reason"] = (
                f"Package net quantity ≤10 g/ml ({net_qty_grams} g/ml) — fully exempt from Rule 6 "
                f"declarations under Rule 26(a). Not pan masala."
            )
        elif net_qty_grams is not None and 10 < net_qty_grams <= 20:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                f"Package in the 10–20 g/ml band ({net_qty_grams} g/ml). "
                f"MRP and net quantity declarations are still required even though full exemption does not apply."
            )
        else:
            result["status"] = "PASS"
            result["reason"] = "Package is above 20 g/ml threshold — micro-package exemption does not apply. Full declarations required."

    def _validate_tamper(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-015 — MRP sticker/tamper check (CV-level, always NEEDS_REVIEW)."""
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = (
            "MRP anti-tampering check requires computer vision analysis. "
            "Automatic detection of sticker overprints and obliterations is not fully reliable from a single image. "
            "Manual inspection recommended to verify original MRP is visible and unaltered (Rules 6(3)–(4), 18(5)–(6))."
        )

    def _validate_font_size(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-016 — numeral height check (CV-level, NEEDS_REVIEW without calibration)."""
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = (
            "Numeral height compliance (Rule 7) requires calibrated computer vision measurement. "
            "Accurate measurement depends on image resolution and a known reference dimension in the frame. "
            "Manual measurement recommended if the package fails a rough visual check."
        )

    def _validate_pdp_placement(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-017 — PDP placement check (CV-level, NEEDS_REVIEW)."""
        result["status"] = "NEEDS_REVIEW"
        result["reason"] = (
            "Principal Display Panel (PDP) placement check (Rule 8) requires image segmentation "
            "to identify the PDP region and verify all declarations appear on it with required clear-space margins. "
            "Manual verification recommended."
        )

    def _validate_legibility(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-018 — legibility + contrast + language check."""
        if 0 < confidence < CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                f"Low OCR confidence ({confidence:.0%}) suggests declarations may not be sufficiently legible "
                f"or contrasting with the background (Rule 9). Manual verification required."
            )
        elif value and confidence >= CONFIDENCE_REVIEW_THRESHOLD:
            result["status"] = "PASS"
            result["reason"] = (
                f"OCR extracted text with confidence {confidence:.0%} — declarations appear legible. "
                f"Language (Hindi/English) and contrast require visual spot-check for full Rule 9 compliance."
            )
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                "Cannot assess legibility, contrast, or language compliance without a readable image. "
                "Manual verification required."
            )

    def _validate_conditional(
        self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict, is_imported: bool
    ):
        """LM-PC-007, 020 — conditional presence (imported only)."""
        # If rule is for imported commodities and package is not imported, pass
        if rule.get("applicability") == "imported_commodities" and not is_imported:
            result["status"] = "PASS"
            result["reason"] = "Domestic package — this declaration is only required for imported commodities."
            return

        self._validate_presence(result, value, normalized, confidence, rule)

    def _validate_external_db(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict):
        """LM-PC-021, 022 — external-DB checks; always UNABLE_TO_VERIFY."""
        result["status"] = "NEEDS_REVIEW"
        automation_note = rule.get("automation_note", "External database required for verification.")
        result["reason"] = (
            f"Unable to Verify — Human Review Required. {automation_note}"
        )

    def _validate_font_size_measurement(
        self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict, extracted: dict
    ):
        """LM-PC-FS-001, 002, 003 — font size compliance measurement."""
        font_size = extracted.get("font_size_mm")
        min_required = rule.get("min_height_mm", 1.0)
        field_name = rule["field"]

        if not value:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Declaration for {field_name} not detected — font size could not be measured."
            return

        if font_size is None:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = f"Bounding box measurement unavailable for {field_name}. Manual physical measurement recommended."
            return

        if font_size < min_required:
            result["status"] = "FAIL"
            result["reason"] = (
                f"Measured font height {font_size} mm is below the legal minimum of {min_required} mm "
                f"for {field_name.replace('_', ' ').title()} (Rule 7)."
            )
        else:
            result["status"] = "PASS"
            result["reason"] = f"Font height {font_size} mm meets/exceeds the legal requirement of {min_required} mm."

    def _validate_barcode_gs1(
        self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict, extracted: dict
    ):
        """LM-PC-BC-001 — Barcode & GS1 registry cross-check."""
        bc_info = extracted.get("barcode_info") or {}
        if not bc_info or not bc_info.get("detected"):
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = "No barcode/QR code detected on the visible package surface. Please scan barcode side if present."
            return

        barcode_number = bc_info.get("barcode", "Unknown")
        if not bc_info.get("gs1_found"):
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = (
                f"Barcode {barcode_number} is not in the local GS1 reference database. "
                f"This does not mean the product is unregistered — the national GS1 India "
                f"registry may have a record. Officer may verify at gs1india.org."
            )
            return

        mismatches = bc_info.get("mismatches", [])
        if mismatches:
            result["status"] = "FAIL"
            result["reason"] = f"GS1 database mismatch for barcode {barcode_number}: " + "; ".join(mismatches)
        else:
            product_name = bc_info.get("gs1_product_name", "Verified Product")
            mfg = bc_info.get("gs1_manufacturer", "Registered Manufacturer")
            result["status"] = "PASS"
            result["reason"] = f"Barcode {barcode_number} verified against GS1 database ({product_name} by {mfg})."

    def _validate_dual_language(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict, extracted: dict):
        """LM-PC-LANG-001 — Rule 9 language verification (English / Hindi / Regional)."""
        lang_data = extracted.get("languages") or {}
        detected = lang_data.get("detected_languages", ["en"])
        has_english = lang_data.get("has_english", True)
        has_hindi = lang_data.get("has_hindi", False)
        is_dual = lang_data.get("is_dual_language", False)

        result["detected_value"] = ", ".join([l.upper() for l in detected])

        if has_english and has_hindi:
            result["status"] = "PASS"
            result["reason"] = "Dual-language declarations verified in both English and Hindi (Devanagari script) per Rule 9(1)."
        elif has_english:
            result["status"] = "PASS"
            result["reason"] = "Mandatory declarations legible in English per Rule 9(1). Hindi translations recommended for national distribution."
        elif has_hindi:
            result["status"] = "PASS"
            result["reason"] = "Mandatory declarations legible in Hindi (Devanagari script) per Rule 9(1)."
        else:
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = "No standard English or Hindi text recognized with high confidence. Regional script detected."

    def _validate_anomaly_tampering(self, result: dict, value: Any, normalized: Any, confidence: float, rule: dict, extracted: dict):
        """LM-PC-ANOM-001 — Anti-tampering and MRP integrity check."""
        anomaly_data = extracted.get("anomaly_detection") or {}
        has_anomaly = anomaly_data.get("has_anomaly", False)
        tampering = anomaly_data.get("tampering_detected", False)
        findings = anomaly_data.get("findings", [])

        if tampering:
            result["status"] = "FAIL"
            finding_details = "; ".join([f"{f['title']}: {f['details']}" for f in findings if f.get("severity") in ("CRITICAL", "HIGH")])
            result["reason"] = f"Packaging tampering anomaly detected: {finding_details} (Section 18(2) violation)."
        elif has_anomaly and any(f.get("type") == "PACKAGE_DAMAGE" for f in findings):
            result["status"] = "NEEDS_REVIEW"
            result["reason"] = "Physical label wear / moisture damage detected. Officer manual inspection recommended."
        else:
            result["status"] = "PASS"
            result["reason"] = "Packaging authenticity verified. No adhesive sticker overlays, tampering, or ink anomalies detected."

    # ──────────────────────────────────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────────────────────────────────

    def _add_explanation(self, result: dict, rule: dict) -> dict:
        tmpl = rule.get("explanation_template", "{field} {status}. {detail}")
        status_map = {
            "PASS": "was found and is compliant",
            "FAIL": "was not found or is non-compliant",
            "NEEDS_REVIEW": "requires manual officer review",
            "EXEMPT": "is exempt for this package type",
        }
        status_word = status_map.get(result["status"], result["status"])
        result["explanation"] = tmpl.format(
            status=status_word,
            detail=result["reason"] or "No issues detected.",
            field=rule["field"],
        )
        return result


# ──────────────────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────────────────
_engine: RuleEngine | None = None


def get_rule_engine() -> RuleEngine:
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine
