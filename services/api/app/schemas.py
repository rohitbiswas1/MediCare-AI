from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict, field_validator


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Register(Credentials):
    name: str = Field(min_length=1, max_length=100)
    consent: Literal[True]


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    language: str
    role: str
    third_party_ai: bool
    mode: str


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    language: Literal["en", "hi", "bn"] = "en"


class ConsentUpdate(BaseModel):
    third_party_ai: bool


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    report_type: str
    status: str
    error: str | None
    safety_scan: str
    created_at: datetime
    expires_at: datetime


class Measurement(BaseModel):
    name: str
    value: float
    unit: str
    source_quote: str
    reference_low: float | None = None
    reference_high: float | None = None
    comparison: Literal[
        "above_reported_range", "below_reported_range", "within_reported_range", "no_reference"
    ]
    explanation: str


class InferenceMetadata(BaseModel):
    name: str
    version: str | None
    validation: Literal["informational-only", "unavailable"]


class UserSummary(BaseModel):
    report_count: int
    completed_count: int
    prescription_count: int


class AnalysisOut(BaseModel):
    report_type: str
    status: Literal["informational", "needs_review", "unavailable"]
    measurements: list[Measurement]
    summary: str
    limitations: list[str]
    quality: dict
    model: InferenceMetadata
    emergency_guidance: str
    disclaimer: str
    explanation_engine: str


class PrescriptionItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    strength: str = Field(default="", max_length=100)
    dosage_form: str = Field(default="", max_length=100)
    instructions: str = Field(default="", max_length=1000)


class PrescriptionConfirm(BaseModel):
    items: list[PrescriptionItemIn] = Field(min_length=1, max_length=30)
    confirmed: Literal[True]


class MedicineIn(BaseModel):
    generic_name: str = Field(min_length=1, max_length=200)
    brand_name: str = Field(default="", max_length=200)
    strength: str = Field(min_length=1, max_length=100)
    dosage_form: str = Field(min_length=1, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=200)
    prescription_required: bool
    source_url: HttpUrl
    source_name: str = Field(min_length=1, max_length=200)
    verified_at: datetime

    @field_validator("verified_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timezone required")
        from .models import now

        if value > now():
            raise ValueError("Verification cannot be in the future")
        return value


class InventoryIn(BaseModel):
    medicine_id: UUID
    status: Literal["verified_in_stock", "verified_out_of_stock"]
    source_reference: str = Field(min_length=3, max_length=500)
    expires_at: datetime


class DeleteAccount(BaseModel):
    confirmation: Literal["DELETE MY ACCOUNT"]
