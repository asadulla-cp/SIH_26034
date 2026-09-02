from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ExtractedField, Inspection, ReviewAction, Violation
from ..services.pipeline import run_pipeline, serialize_inspection
from ..services.preprocessor import ImageError
from ..services.rule_engine import load_rule_pack, overall_from, validate_fields
from ..services.extractor import FieldHit, FIELD_KEYS
from ..services.ocr import run_ocr
from ..services.extractor import extract_fields, looks_imported

router = APIRouter()


@router.post("/scan")
async def scan(
    db: Session = Depends(get_db),
    file: UploadFile | None = File(None),
    sample_id: str | None = Form(None),
    officer_name: str | None = Form("Demo officer"),
):
    try:
        data = await file.read() if file else None
        name = file.filename if file else "upload.jpg"
        if file and not data:
            raise HTTPException(400, "Empty upload.")
        insp = run_pipeline(db, file_bytes=data, filename=name or "upload.jpg", sample_id=sample_id, officer_name=officer_name)
        return serialize_inspection(insp)
    except ImageError as e:
        raise HTTPException(400, {"code": e.code, "message": e.message}) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, {"code": "scan_failed", "message": "Could not process this package image. Try a clearer photo or a demo sample."}) from None


@router.post("/extract")
async def extract_only(file: UploadFile = File(...)):
    try:
        from ..services.preprocessor import preprocess_upload

        data = await file.read()
        paths = preprocess_upload(data, file.filename or "upload.jpg")
        ocr = run_ocr(paths["processed_path"])
        hits = extract_fields(ocr.lines, paths["quality"])
        return {
            "pipeline_mode": ocr.engine,
            "ocr_available": ocr.available,
            "image_quality": paths["quality"],
            "lines": ocr.lines,
            "fields": {k: {"value": h.value, "confidence": h.confidence, "bbox": h.bbox} for k, h in hits.items()},
        }
    except ImageError as e:
        raise HTTPException(400, {"code": e.code, "message": e.message}) from None


@router.post("/validate")
async def validate_payload(payload: dict):
    hits = {}
    for k in FIELD_KEYS:
        raw = payload.get("fields", {}).get(k, {})
        if isinstance(raw, str):
            raw = {"value": raw}
        hits[k] = FieldHit(k, raw.get("value"), raw.get("confidence"), raw.get("bbox"))
    imported = bool(payload.get("imported"))
    quality = float(payload.get("image_quality") or 0.8)
    results = validate_fields(hits, imported, quality, ocr_available=True)
    status, score = overall_from(results, load_rule_pack())
    return {
        "overall_status": status,
        "compliance_score": score,
        "results": [r.__dict__ for r in results],
    }


@router.get("/inspections")
def list_inspections(q: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Inspection).order_by(Inspection.created_at.desc())
    rows = query.all()
    out = []
    for r in rows:
        if status and r.overall_status != status:
            continue
        if q:
            blob = f"{r.id} {r.product_name or ''} {r.demo_sample_id or ''}".lower()
            if q.lower() not in blob:
                continue
        out.append({
            "id": r.id,
            "created_at": r.created_at.isoformat() + "Z",
            "product_name": r.product_name,
            "overall_status": r.overall_status,
            "compliance_score": r.compliance_score,
            "violation_count": r.violation_count,
            "demo_sample_id": r.demo_sample_id,
            "pipeline_mode": r.pipeline_mode,
        })
    return out


@router.get("/inspections/{inspection_id}")
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.get(Inspection, inspection_id)
    if not insp:
        raise HTTPException(404, {"code": "not_found", "message": "Inspection not found."})
    return serialize_inspection(insp)


@router.post("/inspections/{inspection_id}/review")
def review_field(inspection_id: str, payload: dict, db: Session = Depends(get_db)):
    insp = db.get(Inspection, inspection_id)
    if not insp:
        raise HTTPException(404, {"code": "not_found", "message": "Inspection not found."})
    field_key = payload.get("field_key")
    action = payload.get("action")
    if action not in {"approve", "reject", "edit"}:
        raise HTTPException(400, {"code": "bad_action", "message": "Action must be approve, reject, or edit."})
    fld = next((f for f in insp.fields if f.field_key == field_key), None)
    if not fld:
        raise HTTPException(400, {"code": "bad_field", "message": "Unknown field."})
    original = fld.value
    corrected = payload.get("corrected_value") if action == "edit" else fld.value
    if action == "edit" and not (corrected or "").strip():
        raise HTTPException(400, {"code": "empty", "message": "Edited value cannot be empty."})
    fld.original_value = fld.original_value or original
    if action == "edit":
        fld.corrected_value = corrected
        fld.value = corrected
        fld.normalized_value = corrected.strip()
        fld.status = "PASS"
    elif action == "approve":
        fld.status = "PASS"
        fld.reviewer_action = "approve"
    elif action == "reject":
        fld.status = "FAIL"
        fld.reviewer_action = "reject"
    fld.reviewer_action = action
    fld.reviewed_at = datetime.utcnow()

    db.add(ReviewAction(
        inspection_id=insp.id,
        field_key=field_key,
        action=action,
        original_value=original,
        corrected_value=corrected if action == "edit" else original,
        reviewer=payload.get("reviewer") or insp.officer_name or "Demo officer",
        note=payload.get("note"),
    ))

    # Re-run rules on current field values (deterministic)
    hits = {}
    for f in insp.fields:
        hits[f.field_key] = FieldHit(f.field_key, f.value, f.confidence, None if f.bbox_x is None else {"x": f.bbox_x, "y": f.bbox_y, "w": f.bbox_w, "h": f.bbox_h})
    results = validate_fields(hits, insp.imported_flag, insp.image_quality, True)
    status, score = overall_from(results)
    insp.overall_status = status
    insp.compliance_score = score
    db.query(Violation).filter(Violation.inspection_id == insp.id).delete()
    vcount = 0
    for r in results:
        if r.status == "PASS":
            continue
        vcount += 1
        bbox = r.bbox or {}
        db.add(Violation(
            inspection_id=insp.id,
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
    # field statuses
    field_status = {}
    for r in results:
        field_status.setdefault(r.field, "PASS")
        if r.status == "FAIL":
            field_status[r.field] = "FAIL"
        elif r.status == "NEEDS_REVIEW" and field_status[r.field] != "FAIL":
            field_status[r.field] = "NEEDS_REVIEW"
    for f in insp.fields:
        if f.reviewer_action == "approve":
            f.status = "PASS"
        else:
            f.status = field_status.get(f.field_key, f.status)
    insp.violation_count = vcount
    db.commit()
    db.refresh(insp)
    return serialize_inspection(insp)
