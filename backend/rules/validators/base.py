"""
Base types for the deterministic validator layer.

Design principle enforced here: validators NEVER call any AI/LLM model.
They operate only on already-extracted structured field data
(value, normalized_value, confidence, bounding_box, source_text).
"""
from dataclasses import dataclass, field
from typing import Optional, Any, Dict


REVIEW_CONFIDENCE_THRESHOLD = 0.60  # configurable; below this -> NEEDS_REVIEW, never auto-FAIL


@dataclass
class ExtractedField:
    field: str
    value: Optional[str]
    normalized_value: Optional[str]
    confidence: float  # 0.0 - 1.0 ; 0.0 means "not detected at all"
    bounding_box: Optional[Dict[str, float]]  # {x, y, w, h} in image pixel coords, or None
    source_text: Optional[str]
    extraction_method: str  # e.g. "regex+keyword", "spatial", "not_found"
    alternatives: list = field(default_factory=list)  # other candidate (value, confidence) tuples


@dataclass
class ValidationResult:
    rule_id: str
    rule_version: str
    rule_status: str  # "official" | "prototype"
    title: str
    field: str
    severity: str
    status: str  # "PASS" | "FAIL" | "NEEDS_REVIEW"
    detected_value: Optional[str]
    expected_requirement: str
    reason: str
    confidence: float
    evidence_bounding_box: Optional[Dict[str, float]]
    evidence_note: str


def review_or(status_if_confident: str, extracted: ExtractedField) -> str:
    """Never auto-fail purely because OCR confidence is low."""
    if extracted.value is not None and 0 < extracted.confidence < REVIEW_CONFIDENCE_THRESHOLD:
        return "NEEDS_REVIEW"
    return status_if_confident
