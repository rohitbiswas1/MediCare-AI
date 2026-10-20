import logging
from uuid import UUID
from celery import Celery
from sqlalchemy import select, delete
from .config import settings
from .db import SessionLocal, set_owner
from .models import Medicine, MedicalReport, ReportExtraction, AnalysisResult, Profile, AuditEvent, User, now
from .storage import Storage
from .processing import extract, analyze, prescription_candidates

celery = Celery("medicare", broker=settings().redis_url, backend=settings().redis_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=180,
    task_time_limit=210,
    broker_connection_retry_on_startup=True,
    beat_schedule={"delete-expired-reports": {"task": "app.jobs.purge_expired", "schedule": 3600}},
)
logger = logging.getLogger(__name__)


@celery.task(name="app.jobs.process_report")
def process_report(report_id: str, owner_id: str):
    # Queue carries opaque IDs only. DB lock serializes analysis and deletion.
    with SessionLocal() as db:
        set_owner(db, owner_id)
        report = db.scalar(
            select(MedicalReport)
            .where(MedicalReport.id == UUID(report_id), MedicalReport.owner_id == UUID(owner_id))
            .with_for_update()
        )
        if not report or report.status == "completed":
            return
        try:
            report.status = "processing"
            db.flush()
            text, quality, engine = extract(Storage().get(report.storage_key), report.content_type)
            profile = db.scalar(select(Profile).where(Profile.owner_id == report.owner_id))
            result = analyze(text, quality, report.report_type, bool(profile and profile.third_party_ai))
            db.execute(delete(ReportExtraction).where(ReportExtraction.report_id == report.id))
            db.execute(delete(AnalysisResult).where(AnalysisResult.report_id == report.id))
            db.add(
                ReportExtraction(
                    owner_id=report.owner_id,
                    report_id=report.id,
                    text=text,
                    measurements=result["measurements"],
                    quality=quality,
                    engine=engine,
                    prescription_candidates=prescription_candidates(text, db.scalars(select(Medicine)).all())
                    if report.report_type == "prescription"
                    else [],
                )
            )
            db.add(AnalysisResult(owner_id=report.owner_id, report_id=report.id, result=result))
            report.report_type = result["report_type"]
            report.status = "completed"
            report.error = None
            db.add(AuditEvent(owner_id=report.owner_id, action="report.analyzed", resource_id=str(report.id)))
            db.commit()
        except Exception as exc:
            db.rollback()
            set_owner(db, owner_id)
            report = db.get(MedicalReport, UUID(report_id))
            if report:
                report.status = "failed"
                report.error = "Processing could not finish. Try a clearer supported file or contact support."
                db.commit()
            # Do not log document text, storage key, provider responses, or patient identifiers.
            logger.warning("Document processing failed (%s)", type(exc).__name__)


@celery.task(name="app.jobs.purge_expired")
def purge_expired():
    # A dedicated retention service DB role must be allowed to enumerate expired rows in production.
    owners = [None]
    if settings().app_mode == "demo":
        # Render's ordinary role honors forced RLS. Process each owner's expired
        # documents in a separate transaction instead of granting a bypass role.
        with SessionLocal() as db:
            owners = db.scalars(select(User.id)).all()
    count = 0
    for owner in owners:
        with SessionLocal() as db:
            query = select(MedicalReport).where(MedicalReport.expires_at < now())
            if owner is not None:
                set_owner(db, owner)
                query = query.where(MedicalReport.owner_id == owner)
            reports = db.scalars(query.with_for_update()).all()
            for report in reports:
                Storage().delete(report.storage_key)
                db.delete(report)
            db.commit()
            count += len(reports)
    return count
