from datetime import datetime, timezone
from uuid import uuid4, UUID
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
    Float,
    JSON,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Row:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class User(Row, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="user")
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")
    session_version: Mapped[int] = mapped_column(Integer, default=0)


class Profile(Row, Base):
    __tablename__ = "profiles"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    language: Mapped[str] = mapped_column(String(5), default="en")
    third_party_ai: Mapped[bool] = mapped_column(Boolean, default=False)


class ConsentRecord(Row, Base):
    __tablename__ = "consent_records"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(50))
    granted: Mapped[bool] = mapped_column(Boolean)
    policy_version: Mapped[str] = mapped_column(String(30), default="2026-01")


class MedicalReport(Row, Base):
    __tablename__ = "medical_reports"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(180))
    storage_key: Mapped[str] = mapped_column(String(250), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    report_type: Mapped[str] = mapped_column(String(30), default="document")
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    error: Mapped[str | None] = mapped_column(Text)
    safety_scan: Mapped[str] = mapped_column(String(40))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ReportExtraction(Row, Base):
    __tablename__ = "report_extractions"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("medical_reports.id", ondelete="CASCADE"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    measurements: Mapped[list] = mapped_column(JSON, default=list)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)
    engine: Mapped[str] = mapped_column(String(60))
    prescription_candidates: Mapped[list] = mapped_column(JSON, default=list)


class ModelVersion(Row, Base):
    __tablename__ = "model_versions"
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    modality: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="unavailable")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64))
    model_card: Mapped[str] = mapped_column(Text, default="No validated weights deployed.")
    __table_args__ = (UniqueConstraint("name", "version"),)


class AnalysisResult(Row, Base):
    __tablename__ = "ai_analysis_results"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("medical_reports.id", ondelete="CASCADE"), unique=True)
    model_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("model_versions.id"))
    result: Mapped[dict] = mapped_column(JSON)


class Prescription(Row, Base):
    __tablename__ = "prescriptions"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("medical_reports.id", ondelete="CASCADE"), unique=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PrescriptionItem(Row, Base):
    __tablename__ = "prescription_items"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    strength: Mapped[str] = mapped_column(String(100), default="")
    dosage_form: Mapped[str] = mapped_column(String(100), default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="user_confirmed")


class Medicine(Row, Base):
    __tablename__ = "medicines"
    generic_name: Mapped[str] = mapped_column(String(200), index=True)
    brand_name: Mapped[str] = mapped_column(String(200), index=True, default="")
    strength: Mapped[str] = mapped_column(String(100))
    dosage_form: Mapped[str] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    prescription_required: Mapped[bool] = mapped_column(Boolean)
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(200))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Pharmacy(Row, Base):
    __tablename__ = "pharmacies"
    place_id: Mapped[str] = mapped_column(String(250), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(100))
    hours: Mapped[list] = mapped_column(JSON, default=list)
    directions_url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), default="Google Maps")
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PharmacyInventory(Row, Base):
    __tablename__ = "pharmacy_inventory"
    pharmacy_id: Mapped[UUID] = mapped_column(ForeignKey("pharmacies.id", ondelete="CASCADE"), index=True)
    medicine_id: Mapped[UUID] = mapped_column(ForeignKey("medicines.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    source_reference: Mapped[str] = mapped_column(Text)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("pharmacy_id", "medicine_id"),)


class ReportAccessLog(Row, Base):
    __tablename__ = "report_access_logs"
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[UUID] = mapped_column(ForeignKey("medical_reports.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(40))


class AuditEvent(Row, Base):
    __tablename__ = "audit_events"
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
