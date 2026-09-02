"""
SQLite by default (zero-friction demo). Schema is written in vanilla SQLAlchemy
so migrating to PostgreSQL later only requires changing DATABASE_URL.
"""
import os
import json
import uuid
import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "metalex.db")
DATABASE_URL = os.environ.get("METALEX_DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(String, primary_key=True, default=lambda: new_id("INSP"))
    product_name = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    overall_status = Column(String, nullable=False)  # COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW
    compliance_score = Column(Integer, nullable=False)
    is_demo = Column(Boolean, default=False)
    ruleset_version = Column(String, nullable=False)
    quality_json = Column(Text, nullable=True)  # image quality metadata
    perspective_corrected = Column(Boolean, default=False)

    fields = relationship("ExtractedFieldRow", back_populates="inspection", cascade="all, delete-orphan")
    violations = relationship("ViolationRow", back_populates="inspection", cascade="all, delete-orphan")
    reviews = relationship("ReviewActionRow", back_populates="inspection", cascade="all, delete-orphan")


class ExtractedFieldRow(Base):
    __tablename__ = "extracted_fields"
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, ForeignKey("inspections.id"))
    field = Column(String)
    value = Column(String, nullable=True)
    normalized_value = Column(String, nullable=True)
    confidence = Column(Float)
    bounding_box_json = Column(Text, nullable=True)
    source_text = Column(String, nullable=True)
    extraction_method = Column(String, nullable=True)
    alternatives_json = Column(Text, nullable=True)

    inspection = relationship("Inspection", back_populates="fields")


class ViolationRow(Base):
    __tablename__ = "violations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, ForeignKey("inspections.id"))
    rule_id = Column(String)
    rule_version = Column(String)
    rule_status = Column(String)
    title = Column(String)
    field = Column(String)
    severity = Column(String)
    status = Column(String)  # FAIL / NEEDS_REVIEW  (PASS rows also stored for full audit)
    detected_value = Column(String, nullable=True)
    expected_requirement = Column(Text)
    reason = Column(Text)
    confidence = Column(Float)
    evidence_bounding_box_json = Column(Text, nullable=True)
    evidence_note = Column(Text, nullable=True)

    inspection = relationship("Inspection", back_populates="violations")


class ReviewActionRow(Base):
    __tablename__ = "review_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, ForeignKey("inspections.id"))
    field = Column(String)
    original_value = Column(String, nullable=True)
    corrected_value = Column(String, nullable=True)
    action = Column(String)  # APPROVE / REJECT / EDIT
    reviewer = Column(String, default="demo_officer")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    inspection = relationship("Inspection", back_populates="reviews")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
