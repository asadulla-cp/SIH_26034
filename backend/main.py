"""
MetaLex Backend — FastAPI Application
Main API server for the Legal Metrology compliance checking system.
"""
import os
import sys
import uuid
import time
import shutil
import base64
import logging
import datetime
import traceback
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import get_db, init_db, SessionLocal
from backend.models.db_models import (
    Inspection, ExtractedField, Violation, ReviewAction, RuleRecord
)
from backend.services.ocr_pipeline import (
    process_image, is_ocr_available, extract_fields, assess_image_quality,
    run_ocr, preprocess_image, create_annotated_image, _empty_fields
)
from backend.services.demo_service import get_demo_products, get_demo_product
from backend.services.report_service import generate_report
from rules.rule_engine import get_rule_engine

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metalex")

# Directories
UPLOAD_DIR = PROJECT_ROOT / "uploads"
ANNOTATED_DIR = PROJECT_ROOT / "annotated"
REPORTS_DIR = PROJECT_ROOT / "reports"
UPLOAD_DIR.mkdir(exist_ok=True)
ANNOTATED_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Max upload size: 20MB
MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".gif"}


def generate_inspection_id():
    now = datetime.datetime.now()
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"MLX-{now.strftime('%Y%m%d')}-{short_uuid}"


FIELD_LABELS = {
    "product_name": "Product Name",
    "net_quantity": "Net Quantity",
    "mrp": "MRP",
    "manufacturer": "Manufacturer/Packer",
    "date": "Mfg/Pkg Date",
    "consumer_care": "Consumer Care",
    "country_of_origin": "Country of Origin",
    "address": "Address",
    "common_name": "Common/Generic Name",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown."""
    logger.info("🚀 MetaLex starting up...")
    init_db()
    # Pre-load rule engine (instant)
    get_rule_engine()
    logger.info("✅ Database & Rule Engine initialized")
    yield
    logger.info("MetaLex shutting down")


app = FastAPI(
    title="MetaLex API",
    description="Legal Metrology Compliance Checking System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────── Health ─────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "ocr_available": is_ocr_available(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


# ────────────────────────────────── Scan ──────────────────────────────────────
@app.post("/api/scan")
async def scan_product(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Full scan pipeline:
    1. Validate & save uploaded image
    2. Run OCR + field extraction
    3. Apply rule engine
    4. Store results
    5. Return compliance assessment
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(400, "No filename provided")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

        # Read file content
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(400, f"File too large. Max: {MAX_UPLOAD_SIZE // (1024*1024)}MB")

        if len(content) < 100:
            raise HTTPException(400, "File appears to be empty or corrupted")

        # Save upload
        inspection_id = generate_inspection_id()
        filename = f"{inspection_id}{ext}"
        image_path = str(UPLOAD_DIR / filename)

        with open(image_path, "wb") as f:
            f.write(content)

        # Process image
        start_time = time.time()

        if is_ocr_available():
            result = process_image(image_path)
        else:
            # Fallback: still try to load and assess the image
            try:
                img = cv2.imread(image_path)
                if img is None:
                    pil_img = Image.open(image_path).convert("RGB")
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                quality = assess_image_quality(img)
                result = {
                    "success": True,
                    "quality": quality,
                    "ocr_results": [],
                    "fields": _empty_fields(),
                    "annotated_image": img,
                    "original_image": img,
                    "processing_time_ms": 0,
                    "ocr_engine": "fallback_demo",
                }
            except Exception:
                result = {
                    "success": False,
                    "error": "Cannot process image and OCR is not available",
                    "quality": {"overall_score": 0, "issues": ["Image processing failed"]},
                    "ocr_results": [],
                    "fields": _empty_fields(),
                    "processing_time_ms": 0,
                }

        if not result["success"]:
            raise HTTPException(422, result.get("error", "Image processing failed"))

        processing_time = int((time.time() - start_time) * 1000)
        fields = result["fields"]

        # Save annotated image
        annotated_path = None
        if "annotated_image" in result and result["annotated_image"] is not None:
            annotated_filename = f"{inspection_id}_annotated.jpg"
            annotated_path = str(ANNOTATED_DIR / annotated_filename)
            cv2.imwrite(annotated_path, result["annotated_image"])

        # Run rule engine
        engine = get_rule_engine()
        validation = engine.validate_all(fields)

        # Determine product name
        product_name = "Unknown Product"
        pn = fields.get("product_name", {})
        if pn.get("value"):
            product_name = pn["value"]

        # Save to database
        inspection = Inspection(
            inspection_id=inspection_id,
            product_name=product_name,
            image_path=image_path,
            annotated_image_path=annotated_path,
            overall_status=validation["overall_status"],
            compliance_score=validation["compliance_score"],
            total_fields=validation["total_checks"],
            passed_fields=validation["passed"],
            failed_fields=validation["failed"],
            review_fields=validation["needs_review"],
            is_demo=False,
            image_quality_score=result["quality"]["overall_score"],
            image_quality_issues=result["quality"]["issues"],
            ocr_engine=result.get("ocr_engine", "easyocr"),
            processing_time_ms=processing_time,
        )
        db.add(inspection)
        db.flush()

        # Save extracted fields
        extracted_list = []
        for field_name, field_data in fields.items():
            ef = ExtractedField(
                inspection_id=inspection.id,
                field_name=field_name,
                field_label=FIELD_LABELS.get(field_name, field_name),
                detected_value=field_data.get("value"),
                normalized_value=field_data.get("normalized_value"),
                confidence=field_data.get("confidence", 0),
                status="PENDING",
                bounding_box=field_data.get("bounding_box"),
                source_text=field_data.get("source_text", ""),
                extraction_method=field_data.get("extraction_method", "ocr"),
                candidates=field_data.get("candidates"),
            )
            db.add(ef)
            extracted_list.append(ef)

        # Update field statuses from validation
        for vr in validation["results"]:
            for ef in extracted_list:
                if ef.field_name == vr["field"]:
                    # Use the most severe status
                    if ef.status == "PENDING" or vr["status"] == "FAIL" or (vr["status"] == "NEEDS_REVIEW" and ef.status != "FAIL"):
                        ef.status = vr["status"]

        # Save violations
        violation_list = []
        for v in validation["violations"] + validation["reviews"]:
            if v["status"] == "PASS":
                continue
            viol = Violation(
                inspection_id=inspection.id,
                rule_id=v["rule_id"],
                field=v["field"],
                severity=v["severity"],
                title=v["rule_title"],
                detected_value=v.get("detected_value"),
                expected_requirement=v.get("expected_requirement"),
                reason=v.get("reason", ""),
                confidence=v.get("confidence"),
                evidence_type=v.get("evidence_type", "image"),
                bounding_box=v.get("bounding_box"),
                rule_version=v.get("rule_version", "1.0.0"),
                is_prototype_rule=v.get("is_prototype_rule", True),
            )
            db.add(viol)
            violation_list.append(viol)

        db.commit()

        # Build response
        response = _build_inspection_response(
            inspection, extracted_list, violation_list,
            validation, result, annotated_path
        )
        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, "An error occurred while processing the image. Please try again.")


# ────────────────────────────────── Demo Scan ─────────────────────────────────
@app.post("/api/scan/demo/{product_id}")
async def scan_demo_product(product_id: str, db: Session = Depends(get_db)):
    """Process a demo product with pre-defined data."""
    try:
        demo = get_demo_product(product_id)
        if not demo:
            raise HTTPException(404, f"Demo product '{product_id}' not found")

        inspection_id = generate_inspection_id()
        fields = demo["fields"]

        # Run rule engine on demo fields
        engine = get_rule_engine()
        validation = engine.validate_all(fields)

        product_name = demo["name"]

        # Save to database
        inspection = Inspection(
            inspection_id=inspection_id,
            product_name=product_name,
            image_path=None,
            annotated_image_path=None,
            overall_status=validation["overall_status"],
            compliance_score=validation["compliance_score"],
            total_fields=validation["total_checks"],
            passed_fields=validation["passed"],
            failed_fields=validation["failed"],
            review_fields=validation["needs_review"],
            is_demo=True,
            image_quality_score=0.9,
            image_quality_issues=[],
            ocr_engine="demo",
            processing_time_ms=150,
        )
        db.add(inspection)
        db.flush()

        extracted_list = []
        for field_name, field_data in fields.items():
            ef = ExtractedField(
                inspection_id=inspection.id,
                field_name=field_name,
                field_label=FIELD_LABELS.get(field_name, field_name),
                detected_value=field_data.get("value"),
                normalized_value=field_data.get("normalized_value"),
                confidence=field_data.get("confidence", 0),
                status="PENDING",
                bounding_box=field_data.get("bounding_box"),
                source_text=field_data.get("source_text", ""),
                extraction_method=field_data.get("extraction_method", "demo"),
                candidates=field_data.get("candidates"),
            )
            db.add(ef)
            extracted_list.append(ef)

        # Update field statuses
        for vr in validation["results"]:
            for ef in extracted_list:
                if ef.field_name == vr["field"]:
                    if ef.status == "PENDING" or vr["status"] == "FAIL" or (vr["status"] == "NEEDS_REVIEW" and ef.status != "FAIL"):
                        ef.status = vr["status"]

        violation_list = []
        for v in validation["violations"] + validation["reviews"]:
            if v["status"] == "PASS":
                continue
            viol = Violation(
                inspection_id=inspection.id,
                rule_id=v["rule_id"],
                field=v["field"],
                severity=v["severity"],
                title=v["rule_title"],
                detected_value=v.get("detected_value"),
                expected_requirement=v.get("expected_requirement"),
                reason=v.get("reason", ""),
                confidence=v.get("confidence"),
                evidence_type=v.get("evidence_type", "image"),
                bounding_box=v.get("bounding_box"),
                rule_version=v.get("rule_version", "1.0.0"),
                is_prototype_rule=v.get("is_prototype_rule", True),
            )
            db.add(viol)
            violation_list.append(viol)

        db.commit()

        response = _build_inspection_response(
            inspection, extracted_list, violation_list,
            validation, None, None
        )
        response["is_demo"] = True
        response["demo_description"] = demo["description"]
        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demo scan failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, "Demo scan failed. Please try again.")


# ────────────────────────────────── Demo Products List ────────────────────────
@app.get("/api/demo/products")
async def list_demo_products():
    products = get_demo_products()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "is_compliant": p["is_compliant"],
        }
        for p in products
    ]


# ────────────────────────────────── Inspections ───────────────────────────────
@app.delete("/api/inspections")
async def clear_all_inspections(db: Session = Depends(get_db)):
    """Clear all inspection history and associated records."""
    try:
        db.query(ReviewAction).delete()
        db.query(Violation).delete()
        db.query(ExtractedField).delete()
        count = db.query(Inspection).delete()
        db.commit()
        return {"status": "ok", "message": f"Deleted {count} inspections and associated records."}
    except Exception as e:
        logger.error(f"Failed to clear inspections: {e}")
        db.rollback()
        raise HTTPException(500, "Failed to clear inspection history")


@app.get("/api/inspections")
async def list_inspections(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List inspections with optional filtering."""
    try:
        query = db.query(Inspection).order_by(Inspection.created_at.desc())

        if status:
            query = query.filter(Inspection.overall_status == status.upper())
        if search:
            query = query.filter(
                Inspection.product_name.ilike(f"%{search}%") |
                Inspection.inspection_id.ilike(f"%{search}%")
            )

        total = query.count()
        inspections = query.offset(offset).limit(limit).all()

        return {
            "total": total,
            "inspections": [
                {
                    "id": i.id,
                    "inspection_id": i.inspection_id,
                    "product_name": i.product_name,
                    "overall_status": i.overall_status,
                    "compliance_score": i.compliance_score,
                    "total_fields": i.total_fields,
                    "passed_fields": i.passed_fields,
                    "failed_fields": i.failed_fields,
                    "review_fields": i.review_fields,
                    "is_demo": i.is_demo,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                    "violation_count": len(i.violations),
                }
                for i in inspections
            ],
        }
    except Exception as e:
        logger.error(f"List inspections failed: {e}")
        raise HTTPException(500, "Failed to load inspections")


@app.get("/api/inspections/{inspection_id}")
async def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    """Get detailed inspection by ID (supports both internal ID and inspection_id)."""
    try:
        inspection = db.query(Inspection).filter(
            (Inspection.id == inspection_id) | (Inspection.inspection_id == inspection_id)
        ).first()

        if not inspection:
            raise HTTPException(404, "Inspection not found")

        fields = db.query(ExtractedField).filter(
            ExtractedField.inspection_id == inspection.id
        ).all()

        violations = db.query(Violation).filter(
            Violation.inspection_id == inspection.id
        ).all()

        reviews = db.query(ReviewAction).filter(
            ReviewAction.inspection_id == inspection.id
        ).all()

        return {
            "id": inspection.id,
            "inspection_id": inspection.inspection_id,
            "product_name": inspection.product_name,
            "overall_status": inspection.overall_status,
            "compliance_score": inspection.compliance_score,
            "total_fields": inspection.total_fields,
            "passed_fields": inspection.passed_fields,
            "failed_fields": inspection.failed_fields,
            "review_fields": inspection.review_fields,
            "is_demo": inspection.is_demo,
            "image_quality_score": inspection.image_quality_score,
            "image_quality_issues": inspection.image_quality_issues,
            "ocr_engine": inspection.ocr_engine,
            "processing_time_ms": inspection.processing_time_ms,
            "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
            "has_image": bool(inspection.image_path),
            "has_annotated_image": bool(inspection.annotated_image_path),
            "fields": [
                {
                    "id": f.id,
                    "field_name": f.field_name,
                    "field_label": f.field_label,
                    "detected_value": f.detected_value,
                    "normalized_value": f.normalized_value,
                    "confidence": f.confidence,
                    "status": f.status,
                    "bounding_box": f.bounding_box,
                    "source_text": f.source_text,
                    "extraction_method": f.extraction_method,
                    "candidates": f.candidates,
                }
                for f in fields
            ],
            "violations": [
                {
                    "id": v.id,
                    "rule_id": v.rule_id,
                    "field": v.field,
                    "severity": v.severity,
                    "title": v.title,
                    "detected_value": v.detected_value,
                    "expected_requirement": v.expected_requirement,
                    "reason": v.reason,
                    "confidence": v.confidence,
                    "evidence_type": v.evidence_type,
                    "bounding_box": v.bounding_box,
                    "rule_version": v.rule_version,
                    "is_prototype_rule": v.is_prototype_rule,
                }
                for v in violations
            ],
            "reviews": [
                {
                    "id": r.id,
                    "field_name": r.field_name,
                    "action": r.action,
                    "original_value": r.original_value,
                    "corrected_value": r.corrected_value,
                    "reviewer_notes": r.reviewer_notes,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reviews
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get inspection failed: {e}")
        raise HTTPException(500, "Failed to load inspection")


# ────────────────────────────────── Images ────────────────────────────────────
@app.get("/api/inspections/{inspection_id}/image")
async def get_inspection_image(inspection_id: str, db: Session = Depends(get_db)):
    """Get the original uploaded image."""
    inspection = db.query(Inspection).filter(
        (Inspection.id == inspection_id) | (Inspection.inspection_id == inspection_id)
    ).first()
    if not inspection or not inspection.image_path:
        raise HTTPException(404, "Image not found")
    if not os.path.exists(inspection.image_path):
        raise HTTPException(404, "Image file not found on disk")
    return FileResponse(inspection.image_path)


@app.get("/api/inspections/{inspection_id}/annotated")
async def get_annotated_image(inspection_id: str, db: Session = Depends(get_db)):
    """Get the annotated image with bounding boxes."""
    inspection = db.query(Inspection).filter(
        (Inspection.id == inspection_id) | (Inspection.inspection_id == inspection_id)
    ).first()
    if not inspection or not inspection.annotated_image_path:
        raise HTTPException(404, "Annotated image not found")
    if not os.path.exists(inspection.annotated_image_path):
        raise HTTPException(404, "Annotated image file not found on disk")
    return FileResponse(inspection.annotated_image_path)


# ────────────────────────────────── Review Actions ────────────────────────────
@app.post("/api/inspections/{inspection_id}/review")
async def submit_review(inspection_id: str, review_data: dict, db: Session = Depends(get_db)):
    """Submit a review action for a field."""
    try:
        inspection = db.query(Inspection).filter(
            (Inspection.id == inspection_id) | (Inspection.inspection_id == inspection_id)
        ).first()
        if not inspection:
            raise HTTPException(404, "Inspection not found")

        action = ReviewAction(
            inspection_id=inspection.id,
            field_name=review_data.get("field_name", ""),
            action=review_data.get("action", "EDIT"),
            original_value=review_data.get("original_value"),
            corrected_value=review_data.get("corrected_value"),
            reviewer_notes=review_data.get("notes"),
        )
        db.add(action)

        # Update extracted field if edited
        if review_data.get("corrected_value") and review_data.get("field_name"):
            ef = db.query(ExtractedField).filter(
                ExtractedField.inspection_id == inspection.id,
                ExtractedField.field_name == review_data["field_name"],
            ).first()
            if ef:
                ef.detected_value = review_data["corrected_value"]
                ef.normalized_value = review_data["corrected_value"]
                if review_data.get("action") == "APPROVE":
                    ef.status = "PASS"
                elif review_data.get("action") == "REJECT":
                    ef.status = "FAIL"

        db.commit()
        return {"status": "ok", "message": "Review submitted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Review submission failed: {e}")
        raise HTTPException(500, "Failed to submit review")


# ────────────────────────────────── Rules ─────────────────────────────────────
@app.get("/api/rules")
async def list_rules():
    """Get all compliance rules."""
    engine = get_rule_engine()
    return {
        "rule_set_version": engine.rule_set_version,
        "rule_set_name": engine.rule_set_name,
        "disclaimer": engine.disclaimer,
        "rules": engine.get_all_rules(),
    }


# ────────────────────────────────── Reports ───────────────────────────────────
@app.get("/api/reports/{inspection_id}")
async def generate_inspection_report(inspection_id: str, db: Session = Depends(get_db)):
    """Generate and return a PDF report for an inspection."""
    try:
        inspection = db.query(Inspection).filter(
            (Inspection.id == inspection_id) | (Inspection.inspection_id == inspection_id)
        ).first()
        if not inspection:
            raise HTTPException(404, "Inspection not found")

        fields = db.query(ExtractedField).filter(
            ExtractedField.inspection_id == inspection.id
        ).all()

        violations = db.query(Violation).filter(
            Violation.inspection_id == inspection.id
        ).all()

        engine = get_rule_engine()

        report_data = {
            "inspection_id": inspection.inspection_id,
            "product_name": inspection.product_name,
            "created_at": inspection.created_at.isoformat() if inspection.created_at else "",
            "overall_status": inspection.overall_status,
            "compliance_score": inspection.compliance_score,
            "is_demo": inspection.is_demo,
            "rule_set_version": engine.rule_set_version,
            "disclaimer": engine.disclaimer,
            "fields": [
                {
                    "field_name": f.field_name,
                    "field_label": f.field_label,
                    "value": f.detected_value,
                    "confidence": f.confidence,
                    "status": f.status,
                }
                for f in fields
            ],
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "title": v.title,
                    "field": v.field,
                    "severity": v.severity,
                    "detected_value": v.detected_value,
                    "expected_requirement": v.expected_requirement,
                    "reason": v.reason,
                    "is_prototype_rule": v.is_prototype_rule,
                }
                for v in violations
            ],
        }

        report_path = str(REPORTS_DIR / f"{inspection.inspection_id}_report.pdf")
        pdf_bytes = generate_report(report_data, report_path)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{inspection.inspection_id}_report.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, "Failed to generate report")


# ────────────────────────────────── Dashboard Stats ───────────────────────────
@app.get("/api/dashboard/stats")
async def dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    try:
        total = db.query(Inspection).count()
        compliant = db.query(Inspection).filter(Inspection.overall_status == "COMPLIANT").count()
        non_compliant = db.query(Inspection).filter(Inspection.overall_status == "NON_COMPLIANT").count()
        needs_review = db.query(Inspection).filter(Inspection.overall_status == "NEEDS_REVIEW").count()

        # Recent inspections
        recent = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(10).all()

        # Common violations
        all_violations = db.query(Violation).all()
        violation_counts: dict[str, int] = {}
        for v in all_violations:
            key = v.field
            violation_counts[key] = violation_counts.get(key, 0) + 1

        common_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Recent high-severity violations
        high_violations = db.query(Violation).filter(
            Violation.severity == "high"
        ).order_by(Violation.created_at.desc()).limit(5).all()

        return {
            "total_inspections": total,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "needs_review": needs_review,
            "recent_inspections": [
                {
                    "id": i.id,
                    "inspection_id": i.inspection_id,
                    "product_name": i.product_name,
                    "overall_status": i.overall_status,
                    "compliance_score": i.compliance_score,
                    "is_demo": i.is_demo,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                    "violation_count": len(i.violations),
                }
                for i in recent
            ],
            "common_violations": [
                {"field": FIELD_LABELS.get(f, f), "count": c}
                for f, c in common_violations
            ],
            "high_severity_violations": [
                {
                    "id": v.id,
                    "rule_id": v.rule_id,
                    "field": v.field,
                    "title": v.title,
                    "severity": v.severity,
                    "inspection_id": v.inspection_id,
                }
                for v in high_violations
            ],
        }
    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        return {
            "total_inspections": 0,
            "compliant": 0,
            "non_compliant": 0,
            "needs_review": 0,
            "recent_inspections": [],
            "common_violations": [],
            "high_severity_violations": [],
        }


# ────────────────────────────────── Helper ────────────────────────────────────
def _build_inspection_response(
    inspection, extracted_list, violation_list, validation, result, annotated_path
):
    """Build the API response for a completed inspection."""
    return {
        "id": inspection.id,
        "inspection_id": inspection.inspection_id,
        "product_name": inspection.product_name,
        "overall_status": validation["overall_status"],
        "compliance_score": validation["compliance_score"],
        "total_checks": validation["total_checks"],
        "passed": validation["passed"],
        "failed": validation["failed"],
        "needs_review": validation["needs_review"],
        "is_demo": inspection.is_demo,
        "image_quality": result["quality"] if result else None,
        "processing_time_ms": inspection.processing_time_ms,
        "ocr_engine": inspection.ocr_engine,
        "has_image": bool(inspection.image_path),
        "has_annotated_image": bool(annotated_path),
        "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
        "rule_set_version": validation.get("rule_set_version"),
        "disclaimer": validation.get("disclaimer"),
        "fields": [
            {
                "field_name": ef.field_name,
                "field_label": ef.field_label,
                "detected_value": ef.detected_value,
                "normalized_value": ef.normalized_value,
                "confidence": ef.confidence,
                "status": ef.status,
                "bounding_box": ef.bounding_box,
                "source_text": ef.source_text,
                "extraction_method": ef.extraction_method,
                "candidates": ef.candidates,
            }
            for ef in extracted_list
        ],
        "violations": [
            {
                "rule_id": v.rule_id,
                "field": v.field,
                "severity": v.severity,
                "title": v.title,
                "detected_value": v.detected_value,
                "expected_requirement": v.expected_requirement,
                "reason": v.reason,
                "confidence": v.confidence,
                "evidence_type": v.evidence_type,
                "bounding_box": v.bounding_box,
                "rule_version": v.rule_version,
                "is_prototype_rule": v.is_prototype_rule,
            }
            for v in violation_list
        ],
        "validation_results": validation["results"],
    }


# ─────────────────────────── Serve Frontend (Production) ──────────────────────
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
