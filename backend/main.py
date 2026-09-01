"""
MetaLex Backend — FastAPI Application v2
Main API server for the Legal Metrology compliance checking system.
Supports multi-image scanning (1-5 images per inspection).
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
from typing import Optional, List
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import get_db, init_db, SessionLocal
from backend.models.db_models import (
    Inspection, ExtractedField, Violation, ReviewAction, RuleRecord, User
)
from backend.auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_active_user, get_user_by_username, get_user_by_email
)
from backend.services.ocr_pipeline import (
    process_multiple_images,
    process_single_image,
    process_image,
    is_ocr_available,
    extract_fields,
    assess_image_quality,
    run_ocr,
    create_annotated_image,
    _empty_fields
)
from backend.services.demo_service import get_demo_products, get_demo_product
from backend.services.report_service import generate_report
from backend.services.commodity_detector import detect_commodity_category
from rules.rule_engine import get_rule_engine

# Gemini pipeline — optional, activated by GEMINI_API_KEY env var
_gemini_pipeline = None
if os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_API_KEY") != "your_gemini_api_key_here":
    try:
        from backend.services.gemini_pipeline import process_with_gemini
        _gemini_pipeline = process_with_gemini
        logging.getLogger("metalex").info("✅ Gemini 3.6 Flash pipeline activated.")
    except Exception as _ge:
        logging.getLogger("metalex").warning(f"Gemini pipeline failed to load: {_ge}")

# Logging
# Set to DEBUG for detailed inspection logs, INFO for production
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metalex")
if DEBUG_MODE:
    logger.info("🐛 DEBUG MODE ENABLED - Verbose logging active")

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
    logger.info("🚀 MetaLex v2 starting up...")
    init_db()
    get_rule_engine()
    logger.info("✅ Database & Rule Engine initialized")
    yield
    logger.info("MetaLex shutting down")


app = FastAPI(
    title="MetaLex API",
    description="Legal Metrology Compliance Checking System — Multi-Image Edition",
    version="2.0.0",
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
        "version": "2.0.0",
        "multi_image_support": True,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


# ────────────────────────────────── Auth ───────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = ""

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, _ and -.")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@app.post("/api/auth/register", response_model=TokenResponse, tags=["auth"])
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new officer account and return a JWT."""
    if get_user_by_username(db, req.username):
        raise HTTPException(status_code=400, detail="Username already taken.")
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        username=req.username,
        email=req.email,
        full_name=req.full_name or req.username,
        hashed_password=hash_password(req.password),
        role="officer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "email": user.email,
              "full_name": user.full_name, "role": user.role},
    )


@app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Log in with username + password, return a JWT."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # update last_login
    user.last_login = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "email": user.email,
              "full_name": user.full_name, "role": user.role},
    )


@app.get("/api/auth/me", tags=["auth"])
def me(current_user: User = Depends(get_current_active_user)):
    """Return the currently authenticated user's profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }


@app.get("/api/auth/my-inspections", tags=["auth"])
async def get_my_inspections(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get inspections performed by the currently logged-in user."""
    try:
        query = db.query(Inspection)\
            .filter(Inspection.user_id == current_user.id)\
            .order_by(Inspection.created_at.desc())

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
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                    "violation_count": len(i.violations),
                }
                for i in inspections
            ],
        }
    except Exception as e:
        logger.error(f"Get my inspections failed: {e}")
        raise HTTPException(500, "Failed to load user inspections")


# ────────────────────────────────── Multi-Image Scan ──────────────────────────
@app.post("/api/scan")
async def scan_product(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(lambda: None)  # Optional: user if logged in
):
    """
    Multi-image Legal Metrology Scan (1 to 5 package angle photos).
    Pass 1 to 5 images using the 'files' field (multipart form).
    Fuses declarations across Front, Back, Bottom/MRP panel, and side views.
    Detects conflicts (e.g., ₹199 vs ₹299) and flags them as NEEDS REVIEW.
    """
    try:
        # Normalize files list
        upload_list: List[UploadFile] = list(files) if files else []

        if not upload_list:
            raise HTTPException(400, "No image files provided. Please upload 1 to 5 package images.")

        if len(upload_list) > 5:
            upload_list = upload_list[:5]  # Max 5 package pictures

        inspection_id = generate_inspection_id()
        saved_image_paths: List[str] = []
        saved_annotated_paths: List[str] = []

        # ── Validate and save all uploaded images ────────────────────────────
        for idx, up_file in enumerate(upload_list):
            fname = up_file.filename or f"image_{idx}.jpg"
            ext = Path(fname).suffix.lower() or ".jpg"
            if ext not in ALLOWED_EXTENSIONS:
                ext = ".jpg"

            content = await up_file.read()
            if len(content) < 100:
                logger.warning(f"Skipping empty/invalid upload: {fname}")
                continue
            if len(content) > MAX_UPLOAD_SIZE:
                raise HTTPException(400, f"File {fname} exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit.")

            img_filename = f"{inspection_id}_{idx}{ext}"
            img_path = str(UPLOAD_DIR / img_filename)
            with open(img_path, "wb") as f:
                f.write(content)
            saved_image_paths.append(img_path)

        if not saved_image_paths:
            raise HTTPException(400, "No valid package images could be processed.")

        # ── Run multi-image extraction (Gemini if available, else EasyOCR) ────
        start_time = time.time()
        if _gemini_pipeline:
            logger.info("Using Gemini 2.5 Flash for field extraction.")
            multi_result = _gemini_pipeline(saved_image_paths)
        else:
            logger.info("Using EasyOCR pipeline (set GEMINI_API_KEY to enable Gemini).")
            multi_result = process_multiple_images(saved_image_paths)

        # ── Save annotated image for each angle ──────────────────────────────
        for idx, p_res in enumerate(multi_result.get("per_image_results", [])):
            ann_img = p_res.get("annotated_image")
            if ann_img is not None:
                ann_name = f"{inspection_id}_{idx}_annotated.jpg"
                ann_path = str(ANNOTATED_DIR / ann_name)
                cv2.imwrite(ann_path, ann_img)
                saved_annotated_paths.append(ann_path)

        processing_time = int((time.time() - start_time) * 1000)
        fused_fields = multi_result.get("fields", {})

        # ── Apply conflict-awareness: if field has conflict, mark as needs_review ─
        # The rule engine receives the fused fields — conflict fields will be NEEDS_REVIEW
        fields_for_engine = {}
        for fname, fdata in fused_fields.items():
            entry = dict(fdata)
            # If conflict detected, degrade confidence so rule engine sees uncertainty
            if fdata.get("conflict_detected") and fdata.get("value"):
                entry["confidence"] = min(entry.get("confidence", 0), 0.45)
                entry["extraction_method"] = "conflict_detected"
            fields_for_engine[fname] = entry

        # ── Run Deterministic Legal Rule Engine on merged declarations ─────────
        engine = get_rule_engine()
        validation = engine.validate_all(fields_for_engine)

        # ── Determine product name ─────────────────────────────────────────────
        product_name = "Unknown Product"
        pn = fused_fields.get("product_name", {})
        if pn.get("value"):
            product_name = pn["value"]

        # ── Auto-detect commodity category ──────────────────────────────────────
        # Combine all OCR text for better detection
        all_ocr_text = " ".join([
            str(fdata.get("source_text", "")) for fdata in fused_fields.values()
        ])
        commodity_result = detect_commodity_category(
            ocr_text=all_ocr_text,
            product_name=product_name,
            extra_hint=""
        )
        logger.info(f"Commodity detection: {commodity_result.get('category')} "
                   f"(confidence: {commodity_result.get('confidence')})")

        # ── Save inspection to DB ──────────────────────────────────────────────
        primary_image = saved_image_paths[0] if saved_image_paths else None
        primary_annotated = saved_annotated_paths[0] if saved_annotated_paths else None

        inspection = Inspection(
            inspection_id=inspection_id,
            product_name=product_name,
            image_path=primary_image,
            annotated_image_path=primary_annotated,
            overall_status=validation["overall_status"],
            compliance_score=validation["compliance_score"],
            total_fields=validation["total_checks"],
            passed_fields=validation["passed"],
            failed_fields=validation["failed"],
            review_fields=validation["needs_review"],
            is_demo=False,
            image_quality_score=multi_result.get("quality", {}).get("overall_score", 0.9),
            image_quality_issues=multi_result.get("quality", {}).get("issues", []),
            ocr_engine=multi_result.get("ocr_engine", "easyocr_multipass_v2"),
            processing_time_ms=processing_time,
            commodity_category=commodity_result.get("category"),
            commodity_confidence=commodity_result.get("confidence"),
            commodity_detection_meta=commodity_result,
            user_id=current_user.id if current_user else None,  # Track user if logged in
        )
        db.add(inspection)
        db.flush()

        # ── Save extracted fields ──────────────────────────────────────────────
        extracted_list = []
        for field_name, field_data in fused_fields.items():
            # Include conflict info in candidates
            candidates = field_data.get("candidates", [])
            if field_data.get("all_image_candidates"):
                candidates = field_data["all_image_candidates"]

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
                candidates=candidates,
            )
            db.add(ef)
            extracted_list.append(ef)

        # ── Update field statuses from rule engine validation ──────────────────
        for vr in validation["results"]:
            for ef in extracted_list:
                if ef.field_name == vr["field"]:
                    if (ef.status == "PENDING" or
                            vr["status"] == "FAIL" or
                            (vr["status"] == "NEEDS_REVIEW" and ef.status != "FAIL")):
                        ef.status = vr["status"]

        # Conflict fields that aren't already FAIL → NEEDS_REVIEW
        for field_name, fdata in fused_fields.items():
            if fdata.get("conflict_detected"):
                for ef in extracted_list:
                    if ef.field_name == field_name and ef.status not in ("FAIL",):
                        ef.status = "NEEDS_REVIEW"

        # ── Save violations ────────────────────────────────────────────────────
        violation_list = []
        all_issues = validation.get("violations", []) + validation.get("reviews", [])
        for v in all_issues:
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

        # ── Build per-image metadata for UI ───────────────────────────────────
        per_image_meta = []
        for p_res in multi_result.get("per_image_results", []):
            # Support both Gemini pipeline (fields_found=[...]) and EasyOCR (fields={...})
            raw_fields_found = p_res.get("fields_found")
            if isinstance(raw_fields_found, list):
                fields_found_list = raw_fields_found
            elif isinstance(p_res.get("fields"), dict):
                fields_found_list = [
                    fname for fname, fd in p_res["fields"].items()
                    if fd.get("value")
                ]
            else:
                fields_found_list = []

            per_image_meta.append({
                "image_index": p_res.get("image_index", 0),
                "image_number": p_res.get("image_number", 1),
                "success": p_res.get("success", True),
                "error": p_res.get("error"),
                "quality": p_res.get("quality", {}),
                "ocr_text_count": p_res.get("ocr_text_count", 0),
                "fields_found": fields_found_list,
            })

        # ── Build response ────────────────────────────────────────────────────
        # Rebuild fields with conflict info for the response
        fields_response = []
        for ef in extracted_list:
            fdata = fused_fields.get(ef.field_name, {})
            field_entry = {
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
                # Multi-image specific
                "conflict_detected": fdata.get("conflict_detected", False),
                "source_image_index": fdata.get("source_image_index"),
                "source_image_number": fdata.get("source_image_number"),
                "all_image_candidates": fdata.get("all_image_candidates", []),
            }
            fields_response.append(field_entry)

        response = {
            "id": inspection.id,
            "inspection_id": inspection.inspection_id,
            "product_name": inspection.product_name,
            "overall_status": validation["overall_status"],
            "compliance_score": validation["compliance_score"],
            "total_checks": validation["total_checks"],
            "passed": validation["passed"],
            "failed": validation["failed"],
            "needs_review": validation["needs_review"],
            "is_demo": False,
            # Multi-image metadata — safe fallbacks for both Gemini and EasyOCR pipelines
            "total_images": multi_result.get("total_images", len(saved_image_paths)),
            "successful_images": multi_result.get("successful_images", len(saved_image_paths)),
            "per_image_results": per_image_meta,
            "has_conflicts": multi_result.get("has_conflicts", False),
            "conflict_fields": multi_result.get("conflict_fields", []),
            # Quality
            "image_quality": multi_result.get("quality", {"overall_score": 0.9, "quality_label": "Good", "issues": []}),
            "processing_time_ms": processing_time,
            "ocr_engine": multi_result.get("ocr_engine", "easyocr_multipass_v2"),
            "has_image": bool(primary_image),
            "has_annotated_image": bool(primary_annotated),
            "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
            "rule_set_version": validation.get("rule_set_version"),
            "disclaimer": validation.get("disclaimer"),
            "fields": fields_response,
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

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"An error occurred while processing the image: {str(e)}")


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

        # ── Auto-detect commodity category for demo ─────────────────────────────
        all_ocr_text = " ".join([
            str(fdata.get("source_text", "")) for fdata in fields.values()
        ])
        commodity_result = detect_commodity_category(
            ocr_text=all_ocr_text,
            product_name=product_name,
            extra_hint=""
        )

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
            commodity_category=commodity_result.get("category"),
            commodity_confidence=commodity_result.get("confidence"),
            commodity_detection_meta=commodity_result,
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

        for vr in validation["results"]:
            for ef in extracted_list:
                if ef.field_name == vr["field"]:
                    if (ef.status == "PENDING" or
                            vr["status"] == "FAIL" or
                            (vr["status"] == "NEEDS_REVIEW" and ef.status != "FAIL")):
                        ef.status = vr["status"]

        violation_list = []
        for v in validation.get("violations", []) + validation.get("reviews", []):
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
            inspection, extracted_list, violation_list, validation, None, None
        )
        response["is_demo"] = True
        response["demo_description"] = demo["description"]
        response["total_images"] = 1
        response["successful_images"] = 1
        response["per_image_results"] = []
        response["has_conflicts"] = False
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

        recent = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(10).all()

        all_violations = db.query(Violation).all()
        violation_counts: dict = {}
        for v in all_violations:
            key = v.field
            violation_counts[key] = violation_counts.get(key, 0) + 1

        common_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]

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
                "conflict_detected": False,
                "source_image_index": None,
                "source_image_number": None,
                "all_image_candidates": [],
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
