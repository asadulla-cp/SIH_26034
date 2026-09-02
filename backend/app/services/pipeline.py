from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import DEMO_DIR, ROOT
from ..models import ExtractedField, Inspection, Violation
from .extractor import extract_fields, looks_imported
from .ocr import match_demo_by_hash, run_ocr, sample_by_id
from .preprocessor import ImageError, copy_demo_image, preprocess_upload
from .rule_engine import load_rule_pack, overall_from, validate_fields


def new_inspection_id() -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d")
    return f"INSP-{stamp}-{random.randint(1000, 9999)}"


def serialize_inspection(insp: Inspection) -> dict:
    fields = []
    for f in insp.fields:
        fields.append({
            "field_key": f.field_key,
            "value": f.value,
            "normalized_value": f.normalized_value,
            "confidence": f.confidence,
            "status": f.status,
            "bbox": None if f.bbox_x is None else {"x": f.bbox_x, "y": f.bbox_y, "w": f.bbox_w, "h": f.bbox_h},
            "original_value": f.original_value,
            "corrected_value": f.corrected_value,
            "reviewer_action": f.reviewer_action,
            "reviewed_at": f.reviewed_at.isoformat() if f.reviewed_at else None,
        })
    violations = []
    for v in insp.violations:
        violations.append({
            "field": v.field_key,
            "rule_id": v.rule_id,
            "rule_version": v.rule_version,
            "severity": v.severity,
            "detected_value": v.detected_value,
            "expected": v.expected,
            "reason": v.reason,
            "confidence": v.confidence,
            "status": v.status,
            "evidence": (
                {"bbox": {"x": v.bbox_x, "y": v.bbox_y, "w": v.bbox_w, "h": v.bbox_h}}
                if v.has_bbox
                else {"note": "Not detected in supplied image."}
            ),
        })
    return {
        "id": insp.id,
        "created_at": insp.created_at.isoformat() + "Z",
        "product_name": insp.product_name,
        "overall_status": insp.overall_status,
        "compliance_score": insp.compliance_score,
        "violation_count": insp.violation_count,
        "image_url": f"/api/files/inspections/{insp.id}/image",
        "demo_sample_id": insp.demo_sample_id,
        "pipeline_mode": insp.pipeline_mode,
        "ocr_available": insp.ocr_available,
        "image_quality": insp.image_quality,
        "officer_name": insp.officer_name,
        "notes": insp.notes,
        "imported_flag": insp.imported_flag,
        "ocr_lines": json.loads(insp.raw_ocr_json or "[]"),
        "fields": fields,
        "violations": violations,
        "disclaimer": "Rule outcomes use a versioned prototype mapping of LM(PC) Rules, 2011 — not official gazette text.",
    }


def run_pipeline(
    db: Session,
    *,
    file_bytes: bytes | None = None,
    filename: str = "upload.jpg",
    sample_id: str | None = None,
    officer_name: str | None = None,
) -> Inspection:
    sample = sample_by_id(sample_id) if sample_id else None
    if sample:
        src = ROOT / sample["image"]
        if not src.exists():
            src = DEMO_DIR / "images" / f"{sample['id']}.png"
        paths = copy_demo_image(src, sample["id"])
        # prefer fixture quality
        if sample.get("image_quality"):
            paths["quality"] = sample["image_quality"]
    elif file_bytes is not None:
        paths = preprocess_upload(file_bytes, filename)
        sample = match_demo_by_hash(paths["original_path"])
    else:
        raise ImageError("no_image", "No image or demo sample provided.")

    ocr = run_ocr(paths["processed_path"], sample)
    quality = paths["quality"]
    hits = extract_fields(ocr.lines, quality)
    imported = bool(sample.get("imported")) if sample else looks_imported(ocr.lines, hits)
    if sample and sample.get("ambiguous"):
        if hits.get("mrp"):
            hits["mrp"].value = sample["fields"].get("mrp") or hits["mrp"].value
            hits["mrp"].confidence = min(hits["mrp"].confidence or 0.41, 0.42)

    results = validate_fields(hits, imported, quality, ocr.available or bool(sample))
    status, score = overall_from(results)

    product = hits.get("product_name").value if hits.get("product_name") else None
    iid = new_inspection_id()
    while db.get(Inspection, iid):
        iid = new_inspection_id()

    insp = Inspection(
        id=iid,
        product_name=product,
        overall_status=status,
        compliance_score=score,
        violation_count=sum(1 for r in results if r.status in {"FAIL", "NEEDS_REVIEW"} and r.status != "PASS"),
        image_path=paths["original_path"],
        processed_image_path=paths["processed_path"],
        demo_sample_id=sample["id"] if sample else None,
        pipeline_mode="demo_fixture" if sample else ("live_ocr" if ocr.available else "fallback_no_ocr"),
        ocr_available=ocr.available or bool(sample),
        image_quality=quality,
        officer_name=officer_name,
        raw_ocr_json=json.dumps(ocr.lines),
        imported_flag=imported,
        notes=sample.get("notes") if sample else None,
    )
    db.add(insp)

    field_status = {}
    for r in results:
        field_status.setdefault(r.field, "PASS")
        if r.status == "FAIL":
            field_status[r.field] = "FAIL"
        elif r.status == "NEEDS_REVIEW" and field_status[r.field] != "FAIL":
            field_status[r.field] = "NEEDS_REVIEW"

    for key, hit in hits.items():
        bbox = hit.bbox or {}
        db.add(ExtractedField(
            inspection_id=iid,
            field_key=key,
            value=hit.value,
            normalized_value=(hit.value or "").strip() or None,
            confidence=hit.confidence,
            status=field_status.get(key, "PASS"),
            bbox_x=bbox.get("x"),
            bbox_y=bbox.get("y"),
            bbox_w=bbox.get("w"),
            bbox_h=bbox.get("h"),
            original_value=hit.value,
        ))

    vcount = 0
    for r in results:
        if r.status == "PASS":
            continue
        vcount += 1
        bbox = r.bbox or {}
        db.add(Violation(
            inspection_id=iid,
            field_key=r.field,
            rule_id=r.rule_id,
            rule_version=r.version,
            severity=r.severity,
            detected_value=r.detected,
            expected=r.expected,
            reason=r.reason,
            confidence=r.confidence,
            status=r.status,
            has_bbox=bool(r.bbox),
            bbox_x=bbox.get("x"),
            bbox_y=bbox.get("y"),
            bbox_w=bbox.get("w"),
            bbox_h=bbox.get("h"),
        ))
    insp.violation_count = vcount
    db.commit()
    db.refresh(insp)
    return insp
