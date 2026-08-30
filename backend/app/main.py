import os
import sys
import json
import shutil
import traceback
import datetime
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.pipeline import run_full_pipeline, PipelineError
from backend.app.core.report_generator import generate_pdf_report
from backend.app.models.db import init_db, get_session, Inspection, ExtractedFieldRow, ViolationRow, ReviewActionRow, new_id
from backend.rules.rule_engine import get_rule_engine

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
UPLOADS_DIR = os.path.join(BASE_DIR, "storage", "uploads")
DEMO_IMAGES_DIR = os.path.join(BASE_DIR, "demo", "images")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="MetaLex API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static/demo", StaticFiles(directory=DEMO_IMAGES_DIR), name="demo")


@app.exception_handler(Exception)
async def safe_exception_handler(request, exc):
    # Never leak raw stack traces to the client.
    print("UNHANDLED ERROR:", traceback.format_exc())
    return JSONResponse(status_code=500, content={"error": "An unexpected server error occurred. Please try again."})


def _persist_inspection(result: dict, image_path: str, is_demo: bool, product_name_hint: str = None) -> str:
    session = get_session()
    try:
        insp_id = new_id("INSP")
        product_name = None
        pf = result["extracted_fields"].get("product_name")
        if pf and pf.get("value"):
            product_name = pf["value"]
        elif product_name_hint:
            product_name = product_name_hint

        insp = Inspection(
            id=insp_id,
            product_name=product_name,
            image_path=image_path,
            created_at=datetime.datetime.utcnow(),
            overall_status=result["overall_status"],
            compliance_score=result["compliance_score"],
            is_demo=is_demo,
            ruleset_version=result["ruleset_version"],
            quality_json=json.dumps(result["quality"]),
            perspective_corrected=result["perspective_corrected"],
        )
        session.add(insp)

        for fname, f in result["extracted_fields"].items():
            session.add(ExtractedFieldRow(
                inspection_id=insp_id, field=fname, value=f["value"],
                normalized_value=f["normalized_value"], confidence=f["confidence"],
                bounding_box_json=json.dumps(f["bounding_box"]) if f["bounding_box"] else None,
                source_text=f["source_text"], extraction_method=f["extraction_method"],
                alternatives_json=json.dumps(f["alternatives"]),
            ))

        for v in result["validation_results"]:
            session.add(ViolationRow(
                inspection_id=insp_id, rule_id=v["rule_id"], rule_version=v["rule_version"],
                rule_status=v["rule_status"], title=v["title"], field=v["field"], severity=v["severity"],
                status=v["status"], detected_value=v["detected_value"],
                expected_requirement=v["expected_requirement"], reason=v["reason"],
                confidence=v["confidence"],
                evidence_bounding_box_json=json.dumps(v["evidence_bounding_box"]) if v["evidence_bounding_box"] else None,
                evidence_note=v["evidence_note"],
            ))
        session.commit()
        return insp_id
    finally:
        session.close()


def _inspection_to_dict(insp: Inspection) -> dict:
    return {
        "id": insp.id,
        "product_name": insp.product_name,
        "image_url": f"/static/uploads/{os.path.basename(insp.image_path)}" if insp.image_path else None,
        "created_at": insp.created_at.isoformat(),
        "overall_status": insp.overall_status,
        "compliance_score": insp.compliance_score,
        "is_demo": insp.is_demo,
        "ruleset_version": insp.ruleset_version,
        "quality": json.loads(insp.quality_json) if insp.quality_json else {},
        "perspective_corrected": insp.perspective_corrected,
        "fields": [
            {
                "field": f.field, "value": f.value, "normalized_value": f.normalized_value,
                "confidence": f.confidence,
                "bounding_box": json.loads(f.bounding_box_json) if f.bounding_box_json else None,
                "source_text": f.source_text, "extraction_method": f.extraction_method,
                "alternatives": json.loads(f.alternatives_json) if f.alternatives_json else [],
            } for f in insp.fields
        ],
        "violations": [
            {
                "rule_id": v.rule_id, "rule_version": v.rule_version, "rule_status": v.rule_status,
                "title": v.title, "field": v.field, "severity": v.severity, "status": v.status,
                "detected_value": v.detected_value, "expected_requirement": v.expected_requirement,
                "reason": v.reason, "confidence": v.confidence,
                "evidence_bounding_box": json.loads(v.evidence_bounding_box_json) if v.evidence_bounding_box_json else None,
                "evidence_note": v.evidence_note,
            } for v in insp.violations
        ],
        "reviews": [
            {
                "field": r.field, "original_value": r.original_value, "corrected_value": r.corrected_value,
                "action": r.action, "reviewer": r.reviewer, "created_at": r.created_at.isoformat(),
            } for r in insp.reviews
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "online"}


@app.post("/api/scan")
async def scan(file: UploadFile = File(...), is_imported: bool = Query(False)):
    content_type = file.content_type or ""
    if not any(t in content_type for t in ["image/jpeg", "image/png", "image/jpg", "image/webp"]):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a JPG, PNG, or WEBP image.")

    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB).")

    try:
        result = run_full_pipeline(raw, is_imported=is_imported)
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))

    insp_id = new_id("INSP")
    ext = ".png"
    image_path = os.path.join(UPLOADS_DIR, f"{insp_id}{ext}")
    cv2.imwrite(image_path, result["display_image"])

    saved_id = _persist_inspection(result, image_path, is_demo=False)
    session = get_session()
    try:
        insp = session.query(Inspection).filter_by(id=saved_id).first()
        return _inspection_to_dict(insp)
    finally:
        session.close()


@app.get("/api/demo/list")
def demo_list():
    items = []
    if os.path.isdir(DEMO_IMAGES_DIR):
        for fname in sorted(os.listdir(DEMO_IMAGES_DIR)):
            items.append({"filename": fname, "url": f"/static/demo/{fname}"})
    return {"demo_images": items}


@app.post("/api/demo/scan/{filename}")
def demo_scan(filename: str):
    path = os.path.join(DEMO_IMAGES_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Demo image not found.")
    with open(path, "rb") as f:
        raw = f.read()
    try:
        result = run_full_pipeline(raw, is_imported=("country" in filename.lower()))
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))

    insp_id = new_id("INSP")
    image_path = os.path.join(UPLOADS_DIR, f"{insp_id}.png")
    cv2.imwrite(image_path, result["display_image"])
    saved_id = _persist_inspection(result, image_path, is_demo=True, product_name_hint=filename)
    session = get_session()
    try:
        insp = session.query(Inspection).filter_by(id=saved_id).first()
        return _inspection_to_dict(insp)
    finally:
        session.close()


@app.get("/api/inspections")
def list_inspections(
    q: str = Query(None), result: str = Query(None), min_violations: int = Query(None)
):
    session = get_session()
    try:
        query = session.query(Inspection).order_by(Inspection.created_at.desc())
        if result:
            query = query.filter(Inspection.overall_status == result)
        rows = query.all()
        out = []
        for insp in rows:
            if q and (not insp.product_name or q.lower() not in insp.product_name.lower()):
                continue
            viol_count = sum(1 for v in insp.violations if v.status in ("FAIL", "NEEDS_REVIEW"))
            if min_violations is not None and viol_count < min_violations:
                continue
            out.append({
                "id": insp.id, "product_name": insp.product_name or "Unknown",
                "created_at": insp.created_at.isoformat(), "overall_status": insp.overall_status,
                "compliance_score": insp.compliance_score, "violation_count": viol_count,
                "is_demo": insp.is_demo,
            })
        return {"inspections": out}
    finally:
        session.close()


@app.get("/api/inspections/{insp_id}")
def get_inspection(insp_id: str):
    session = get_session()
    try:
        insp = session.query(Inspection).filter_by(id=insp_id).first()
        if not insp:
            raise HTTPException(status_code=404, detail="Inspection not found.")
        return _inspection_to_dict(insp)
    finally:
        session.close()


@app.post("/api/inspections/{insp_id}/review")
def submit_review(insp_id: str, field: str, action: str, corrected_value: str = None):
    if action not in ("APPROVE", "REJECT", "EDIT"):
        raise HTTPException(status_code=400, detail="Invalid review action.")
    session = get_session()
    try:
        insp = session.query(Inspection).filter_by(id=insp_id).first()
        if not insp:
            raise HTTPException(status_code=404, detail="Inspection not found.")
        original = next((f.value for f in insp.fields if f.field == field), None)
        session.add(ReviewActionRow(
            inspection_id=insp_id, field=field, original_value=original,
            corrected_value=corrected_value, action=action,
        ))
        if action == "EDIT" and corrected_value is not None:
            for f in insp.fields:
                if f.field == field:
                    f.value = corrected_value
        session.commit()
        return {"status": "recorded"}
    finally:
        session.close()


@app.get("/api/rules")
def get_rules():
    engine = get_rule_engine()
    return {"ruleset_version": engine.ruleset_version, "note": engine.note, "rules": engine.get_rules()}


@app.get("/api/reports/{insp_id}")
def get_report(insp_id: str):
    session = get_session()
    try:
        insp = session.query(Inspection).filter_by(id=insp_id).first()
        if not insp:
            raise HTTPException(status_code=404, detail="Inspection not found.")
        d = _inspection_to_dict(insp)
        try:
            pdf_path = generate_pdf_report(
                {"id": insp.id, "product_name": insp.product_name, "created_at": insp.created_at,
                 "ruleset_version": insp.ruleset_version, "overall_status": insp.overall_status,
                 "compliance_score": insp.compliance_score, "is_demo": insp.is_demo},
                d["fields"], d["violations"], image_path=insp.image_path,
            )
        except Exception:
            raise HTTPException(status_code=500, detail="Report generation failed. Please try again.")
        return FileResponse(pdf_path, filename=f"MetaLex_Report_{insp.id}.pdf", media_type="application/pdf")
    finally:
        session.close()


@app.get("/api/dashboard/summary")
def dashboard_summary():
    session = get_session()
    try:
        rows = session.query(Inspection).all()
        total = len(rows)
        compliant = sum(1 for r in rows if r.overall_status == "COMPLIANT")
        non_compliant = sum(1 for r in rows if r.overall_status == "NON_COMPLIANT")
        needs_review = sum(1 for r in rows if r.overall_status == "NEEDS_REVIEW")

        violation_counts = {}
        for r in rows:
            for v in r.violations:
                if v.status == "FAIL":
                    violation_counts[v.title] = violation_counts.get(v.title, 0) + 1
        common = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        recent = sorted(rows, key=lambda r: r.created_at, reverse=True)[:5]
        return {
            "total_inspections": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "needs_review": needs_review,
            "common_violations": [{"title": t, "count": c} for t, c in common],
            "recent": [
                {"id": r.id, "product_name": r.product_name or "Unknown", "created_at": r.created_at.isoformat(),
                 "overall_status": r.overall_status, "compliance_score": r.compliance_score, "is_demo": r.is_demo}
                for r in recent
            ],
            "any_demo_data": any(r.is_demo for r in rows),
        }
    finally:
        session.close()
