from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overall_status: Mapped[str] = mapped_column(String(32))
    compliance_score: Mapped[int] = mapped_column(Integer)
    violation_count: Mapped[int] = mapped_column(Integer, default=0)
    image_path: Mapped[str] = mapped_column(String(500))
    processed_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_sample_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pipeline_mode: Mapped[str] = mapped_column(String(40))
    ocr_available: Mapped[bool] = mapped_column(default=False)
    image_quality: Mapped[float] = mapped_column(Float, default=0.0)
    officer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_ocr_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_flag: Mapped[bool] = mapped_column(default=False)

    fields: Mapped[list["ExtractedField"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    violations: Mapped[list["Violation"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    reviews: Mapped[list["ReviewAction"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    field_key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="fields")


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    field_key: Mapped[str] = mapped_column(String(64))
    rule_id: Mapped[str] = mapped_column(String(32))
    rule_version: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(16))
    detected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    has_bbox: Mapped[bool] = mapped_column(default=False)
    bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_h: Mapped[float | None] = mapped_column(Float, nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="violations")


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    field_key: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="reviews")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    pdf_path: Mapped[str] = mapped_column(String(500))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inspection: Mapped[Inspection] = relationship(back_populates="reports")


class RuleRecord(Base):
    __tablename__ = "rules"

    rule_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    field: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    requirement: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))
    validation_type: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(24))
    legal_reference: Mapped[str] = mapped_column(Text)
    demo_simplified: Mapped[bool] = mapped_column(default=True)
