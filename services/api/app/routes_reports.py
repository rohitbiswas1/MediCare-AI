from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4
import hashlib
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Response
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .auth import current_user
from .config import settings
from .db import get_db, set_owner
from .models import (
    User,
    MedicalReport,
    ReportExtraction,
    AnalysisResult,
    Prescription,
    PrescriptionItem,
    ConsentRecord,
    ReportAccessLog,
    AuditEvent,
    now,
)
from .schemas import ReportOut, PrescriptionConfirm, AnalysisOut
from .storage import Storage, validate_file
from .jobs import process_report

router = APIRouter()
KINDS = {"document", "blood_test", "ecg", "xray", "heart_rate", "prescription"}


def owned_report(db, user, report_id, lock=False):
    query = select(MedicalReport).where(MedicalReport.id == report_id, MedicalReport.owner_id == user.id)
    if lock:
        query = query.with_for_update()
    report = db.scalar(query)
    if not report:
        raise HTTPException(404, "Report not found.")
    return report


def queue(db, report, user):
    report.status, report.error = "queued", None
    db.commit()
    try:
        process_report.delay(str(report.id), str(user.id))
    except Exception:
        set_owner(db, user.id)
        report.status = "failed"
        report.error = "Processing queue is unavailable. Your file is saved; please retry analysis."
        db.commit()
        raise HTTPException(503, report.error)
    return report


async def store_upload(file, consent, kind, user, db):
    if not consent:
        raise HTTPException(422, "Explicit consent is required to store and process your report.")
    if kind not in KINDS:
        raise HTTPException(422, "Unsupported report type.")
    data = await file.read(settings().max_upload_bytes + 1)
    name = Path((file.filename or "report").replace("\\", "/")).name[:180]
    mime, scan = validate_file(data, name)
    report_id = uuid4()
    key = f"{user.id}/{report_id}"
    Storage().put(key, data)
    report = MedicalReport(
        id=report_id,
        owner_id=user.id,
        filename=name,
        storage_key=key,
        content_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        report_type=kind,
        safety_scan=scan,
        expires_at=now() + timedelta(days=settings().retention_days),
    )
    try:
        db.add(report)
        db.add(ConsentRecord(owner_id=user.id, purpose="report_processing", granted=True))
        db.add(AuditEvent(owner_id=user.id, action="report.uploaded", resource_id=str(report.id)))
        db.commit()
    except Exception:
        db.rollback()
        Storage().delete(key)
        raise
    set_owner(db, user.id)
    return report


@router.post("/reports/upload", response_model=ReportOut, status_code=201)
async def upload(
    file: UploadFile = File(...),
    consent: bool = Form(...),
    report_type: str = Form("document"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    report = await store_upload(file, consent, report_type, user, db)
    return queue(db, report, user)


@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = 50, offset: int = 0
):
    return db.scalars(
        select(MedicalReport)
        .where(MedicalReport.owner_id == user.id)
        .order_by(MedicalReport.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .offset(max(0, offset))
    ).all()


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = owned_report(db, user, report_id)
    db.add(ReportAccessLog(owner_id=user.id, report_id=report.id, action="view"))
    db.commit()
    return report


@router.post("/reports/{report_id}/analyze", response_model=ReportOut)
def run_analysis(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = owned_report(db, user, report_id, lock=True)
    if report.status in {"queued", "processing"}:
        return report
    return queue(db, report, user)


@router.get("/reports/{report_id}/analysis", response_model=AnalysisOut)
def get_analysis(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = owned_report(db, user, report_id)
    analysis = db.scalar(
        select(AnalysisResult).where(
            AnalysisResult.report_id == report.id, AnalysisResult.owner_id == user.id
        )
    )
    if not analysis:
        raise HTTPException(409, "Analysis is not ready yet.")
    return analysis.result


@router.get("/reports/{report_id}/extraction")
def get_extraction(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_report(db, user, report_id)
    value = db.scalar(
        select(ReportExtraction).where(
            ReportExtraction.report_id == report_id, ReportExtraction.owner_id == user.id
        )
    )
    if not value:
        raise HTTPException(409, "Extraction is not ready yet.")
    return {
        "text": value.text,
        "quality": value.quality,
        "engine": value.engine,
        "measurements": value.measurements,
    }


@router.get("/reports/{report_id}/download")
def download(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = owned_report(db, user, report_id)
    data = Storage().get(report.storage_key)
    db.add(ReportAccessLog(owner_id=user.id, report_id=report.id, action="download"))
    db.commit()
    return Response(
        data,
        media_type=report.content_type,
        headers={
            "Content-Disposition": 'attachment; filename="medical-report'
            + Path(report.filename).suffix
            + '"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/reports/{report_id}/signed-url")
def signed_url(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = owned_report(db, user, report_id)
    url = Storage().signed_url(report.storage_key)
    if not url:
        return {"url": f"/api/v1/reports/{report_id}/download", "expires_in": None, "requires_session": True}
    return {"url": url, "expires_in": 60, "requires_session": False}


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = owned_report(db, user, report_id, lock=True)
    Storage().delete(report.storage_key)
    db.add(AuditEvent(owner_id=user.id, action="report.deleted", resource_id=str(report.id)))
    db.delete(report)
    db.commit()


@router.post("/prescriptions/upload", status_code=201)
async def upload_prescription(
    file: UploadFile = File(...),
    consent: bool = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if Path(file.filename or "").suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(422, "Prescriptions must be PDF, JPG, or PNG.")
    report = await store_upload(file, consent, "prescription", user, db)
    prescription = Prescription(owner_id=user.id, report_id=report.id)
    db.add(prescription)
    db.commit()
    set_owner(db, user.id)
    queue(db, report, user)
    return {"id": prescription.id, "report_id": report.id, "status": report.status}


@router.get("/prescriptions")
def list_prescriptions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Prescription)
        .where(Prescription.owner_id == user.id)
        .order_by(Prescription.created_at.desc())
        .limit(100)
    ).all()
    return [
        {"id": p.id, "report_id": p.report_id, "confirmed_at": p.confirmed_at, "created_at": p.created_at}
        for p in rows
    ]


@router.get("/prescriptions/{prescription_id}")
def prescription_detail(
    prescription_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    prescription = db.scalar(
        select(Prescription).where(Prescription.id == prescription_id, Prescription.owner_id == user.id)
    )
    if not prescription:
        raise HTTPException(404, "Prescription not found.")
    report = owned_report(db, user, prescription.report_id)
    extraction = db.scalar(
        select(ReportExtraction).where(
            ReportExtraction.report_id == report.id, ReportExtraction.owner_id == user.id
        )
    )
    items = db.scalars(
        select(PrescriptionItem).where(
            PrescriptionItem.prescription_id == prescription.id, PrescriptionItem.owner_id == user.id
        )
    ).all()
    return {
        "id": prescription.id,
        "report_id": report.id,
        "status": report.status,
        "error": report.error,
        "confirmed_at": prescription.confirmed_at,
        "candidates": extraction.prescription_candidates if extraction else [],
        "extracted_text": extraction.text if extraction else "",
        "items": [
            {
                "name": i.name,
                "strength": i.strength,
                "dosage_form": i.dosage_form,
                "instructions": i.instructions,
            }
            for i in items
        ],
        "notice": "OCR is an unverified transcription. Confirm medicine names, strengths, and instructions with your clinician or pharmacist. No substitutions are suggested.",
    }


@router.patch("/prescriptions/{prescription_id}/confirm")
def confirm_prescription(
    prescription_id: UUID,
    body: PrescriptionConfirm,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    prescription = db.scalar(
        select(Prescription)
        .where(Prescription.id == prescription_id, Prescription.owner_id == user.id)
        .with_for_update()
    )
    if not prescription:
        raise HTTPException(404, "Prescription not found.")
    report = owned_report(db, user, prescription.report_id)
    if report.status != "completed":
        raise HTTPException(409, "Wait for extraction to complete before confirming.")
    db.execute(
        delete(PrescriptionItem).where(
            PrescriptionItem.prescription_id == prescription.id, PrescriptionItem.owner_id == user.id
        )
    )
    for item in body.items:
        db.add(PrescriptionItem(owner_id=user.id, prescription_id=prescription.id, **item.model_dump()))
    prescription.confirmed_at = now()
    db.add(AuditEvent(owner_id=user.id, action="prescription.confirmed", resource_id=str(prescription.id)))
    db.commit()
    return {"confirmed": True, "id": prescription.id}
