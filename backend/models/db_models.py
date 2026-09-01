"""
MetaLex Database Models
All tables for inspections, extracted fields, violations, reviews, and reports.
Designed for SQLite (hackathon), easily migrated to PostgreSQL.
"""
import uuid
import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean, JSON,
    ForeignKey, Enum as SqlEnum
)
from sqlalchemy.orm import relationship
from backend.database import Base


def gen_uuid():
    return str(uuid.uuid4())


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(String, primary_key=True, default=gen_uuid)
    inspection_id = Column(String, unique=True, nullable=False)  # e.g. MLX-20260830-001
    product_name = Column(String, default="Unknown Product")
    image_path = Column(String, nullable=True)
    annotated_image_path = Column(String, nullable=True)
    overall_status = Column(String, default="PENDING")  # COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW / PENDING
    compliance_score = Column(Float, default=0.0)
    total_fields = Column(Integer, default=0)
    passed_fields = Column(Integer, default=0)
    failed_fields = Column(Integer, default=0)
    review_fields = Column(Integer, default=0)
    is_demo = Column(Boolean, default=False)
    image_quality_score = Column(Float, nullable=True)
    image_quality_issues = Column(JSON, nullable=True)
    ocr_engine = Column(String, default="easyocr")
    processing_time_ms = Column(Integer, nullable=True)
    commodity_category = Column(String, nullable=True)  # Auto-detected category (tea, coffee, soap, etc.)
    commodity_confidence = Column(Float, nullable=True)  # Detection confidence 0.0-1.0
    commodity_detection_meta = Column(JSON, nullable=True)  # Full detection result metadata
    
    # Severity & Risk Scoring
    severity_score = Column(Float, default=0.0)  # 0-100 risk score
    risk_level = Column(String, default="low")    # low / medium / high / critical
    
    # GPS Tagging (PWA)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Barcode / GS1 data
    barcode_data = Column(JSON, nullable=True)
    
    # Anomaly Detection & Forensics
    anomaly_data = Column(JSON, nullable=True)
    
    # Multi-language detection metadata
    detected_languages = Column(JSON, nullable=True)
    
    # User tracking - links inspection to officer who performed it
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Nullable for backward compatibility
    
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    # Relationships
    performed_by = relationship("User", back_populates="inspections")
    extracted_fields = relationship("ExtractedField", back_populates="inspection", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="inspection", cascade="all, delete-orphan")
    review_actions = relationship("ReviewAction", back_populates="inspection", cascade="all, delete-orphan")
    legal_notices = relationship("LegalNotice", back_populates="inspection", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(String, primary_key=True, default=gen_uuid)
    inspection_id = Column(String, ForeignKey("inspections.id"), nullable=False)
    field_name = Column(String, nullable=False)  # e.g. "mrp", "net_quantity"
    field_label = Column(String, nullable=False)  # e.g. "MRP", "Net Quantity"
    detected_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    status = Column(String, default="PENDING")  # PASS / FAIL / NEEDS_REVIEW / NOT_DETECTED
    bounding_box = Column(JSON, nullable=True)  # [x1, y1, x2, y2]
    font_size_mm = Column(Float, nullable=True)  # Measured font height in mm
    min_font_size_mm = Column(Float, nullable=True)  # Minimum legal required font height in mm
    source_text = Column(Text, nullable=True)
    extraction_method = Column(String, default="ocr_regex")
    candidates = Column(JSON, nullable=True)  # Alternative candidates with confidence
    created_at = Column(DateTime, default=now_utc)

    inspection = relationship("Inspection", back_populates="extracted_fields")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(String, primary_key=True, default=gen_uuid)
    inspection_id = Column(String, ForeignKey("inspections.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    field = Column(String, nullable=False)
    severity = Column(String, default="high")  # high / medium / low / critical
    severity_points = Column(Integer, default=5)  # 2, 5, 7, 10
    title = Column(String, nullable=False)
    detected_value = Column(Text, nullable=True)
    expected_requirement = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    evidence_type = Column(String, default="image")  # image / bounding_box / not_detected
    bounding_box = Column(JSON, nullable=True)
    rule_version = Column(String, default="1.0.0")
    is_prototype_rule = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    inspection = relationship("Inspection", back_populates="violations")


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(String, primary_key=True, default=gen_uuid)
    inspection_id = Column(String, ForeignKey("inspections.id"), nullable=False)
    field_name = Column(String, nullable=False)
    action = Column(String, nullable=False)  # APPROVE / REJECT / EDIT
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    inspection = relationship("Inspection", back_populates="review_actions")


class RuleRecord(Base):
    """Persisted copy of rules for audit trail."""
    __tablename__ = "rule_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    rule_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    field = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    requirement = Column(Text, nullable=True)
    severity = Column(String, default="high")
    validation_type = Column(String, nullable=False)
    rule_version = Column(String, default="1.0.0")
    is_prototype = Column(Boolean, default=True)
    source_reference = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_utc)


class User(Base):
    """User account for MetaLex enforcement officers."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="officer")        # officer / admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)
    last_login = Column(DateTime, nullable=True)
    
    # Relationship: all inspections performed by this user
    inspections = relationship("Inspection", back_populates="performed_by")


class LegalNotice(Base):
    """Auto-generated Legal Notice issued under Legal Metrology Act, 2009."""
    __tablename__ = "legal_notices"

    id = Column(String, primary_key=True, default=gen_uuid)
    notice_id = Column(String, unique=True, nullable=False)  # e.g. NOTICE-MLX-20260901-001
    inspection_id = Column(String, ForeignKey("inspections.id"), nullable=False)
    manufacturer_name = Column(String, nullable=True)
    manufacturer_email = Column(String, nullable=True)
    total_penalty = Column(Integer, default=0)
    violations_summary = Column(JSON, nullable=True)
    status = Column(String, default="GENERATED")  # GENERATED / SENT / RESPONDED / PENDING
    pdf_path = Column(String, nullable=True)
    response_deadline = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_utc)

    # Relationship
    inspection = relationship("Inspection", back_populates="legal_notices")

