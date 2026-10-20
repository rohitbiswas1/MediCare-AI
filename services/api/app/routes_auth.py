from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .auth import (
    current_user,
    password_hasher,
    verify_password,
    local_token,
    session_cookie,
    supabase_request,
    user_view,
)
from .config import settings
from .db import get_db, set_owner
from .models import User, Profile, ConsentRecord, AuditEvent, MedicalReport
from .schemas import Register, Credentials, UserOut, ProfileUpdate, ConsentUpdate, DeleteAccount, UserSummary
from .storage import Storage

router = APIRouter()


@router.post("/auth/register", status_code=201)
def register(body: Register, response: Response, db: Session = Depends(get_db)):
    email = str(body.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Unable to register. Try signing in or use a different email.")
    if settings().auth_provider == "supabase":
        result = supabase_request(
            "signup",
            {
                "email": email,
                "password": body.password,
                "data": {"name": body.name, "consent_policy": "2026-01"},
            },
        )
        identity = result.get("user", {})
        if not identity.get("id"):
            raise HTTPException(400, "Check your email to complete registration.")
        user = User(id=UUID(identity["id"]), email=email, auth_provider="supabase")
    else:
        user = User(email=email, password_hash=password_hasher.hash(body.password))
    db.add(user)
    try:
        db.flush()
        set_owner(db, user.id)
        db.add(Profile(owner_id=user.id, name=body.name))
        db.add(ConsentRecord(owner_id=user.id, purpose="account_terms", granted=True))
        db.add(AuditEvent(owner_id=user.id, action="account.created"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Unable to register. Try signing in.")
    if settings().auth_provider == "supabase":
        if not result.get("access_token"):
            return {"requires_email_verification": True, "message": "Check your email before signing in."}
        session_cookie(response, result["access_token"], result.get("refresh_token"))
    else:
        session_cookie(response, local_token(user))
    set_owner(db, user.id)
    return user_view(db, user)


@router.post("/auth/login", response_model=UserOut)
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if settings().auth_provider == "supabase":
        result = supabase_request(
            "token?grant_type=password", {"email": str(body.email), "password": body.password}
        )
        identity = result["user"]
        if not user:
            user = User(id=UUID(identity["id"]), email=str(body.email).lower(), auth_provider="supabase")
            db.add(user)
            db.flush()
            set_owner(db, user.id)
            db.add(Profile(owner_id=user.id, name=identity.get("user_metadata", {}).get("name", "")))
        if str(user.id) != identity["id"]:
            raise HTTPException(401, "Account provider mismatch. Contact support.")
        session_cookie(response, result["access_token"], result.get("refresh_token"))
    else:
        if not user or not verify_password(user.password_hash, body.password):
            raise HTTPException(401, "Email or password is incorrect.")
        session_cookie(response, local_token(user))
    set_owner(db, user.id)
    db.add(AuditEvent(owner_id=user.id, action="auth.login"))
    db.commit()
    set_owner(db, user.id)
    return user_view(db, user)


@router.post("/auth/refresh")
def refresh(request: Request, response: Response):
    token = request.cookies.get("medicare_refresh")
    if settings().auth_provider != "supabase" or not token:
        raise HTTPException(401, "Please sign in again.")
    result = supabase_request("token?grant_type=refresh_token", {"refresh_token": token})
    session_cookie(response, result["access_token"], result.get("refresh_token"))
    return {"refreshed": True}


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if settings().auth_provider == "supabase":
        supabase_request("logout", token=request.cookies.get("medicare_session"))
    user.session_version += 1
    db.commit()
    for name in ["medicare_session", "medicare_csrf"]:
        response.delete_cookie(name, path="/")
    response.delete_cookie("medicare_refresh", path="/api/v1/auth")


@router.get("/users/me", response_model=UserOut)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_view(db, user)


@router.patch("/users/me", response_model=UserOut)
def update_profile(body: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    profile.name, profile.language = body.name, body.language
    db.commit()
    set_owner(db, user.id)
    return user_view(db, user)


@router.get("/users/me/consent")
def consent(user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    records = db.scalars(
        select(ConsentRecord)
        .where(ConsentRecord.owner_id == user.id)
        .order_by(ConsentRecord.created_at.desc())
    ).all()
    return {
        "third_party_ai": profile.third_party_ai,
        "training": False,
        "retention_days": settings().retention_days,
        "records": [
            {
                "purpose": r.purpose,
                "granted": r.granted,
                "created_at": r.created_at,
                "policy_version": r.policy_version,
            }
            for r in records
        ],
    }


@router.patch("/users/me/consent")
def update_consent(body: ConsentUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    profile.third_party_ai = body.third_party_ai
    db.add(ConsentRecord(owner_id=user.id, purpose="third_party_ai", granted=body.third_party_ai))
    db.add(
        AuditEvent(owner_id=user.id, action="consent.updated", detail={"third_party_ai": body.third_party_ai})
    )
    db.commit()
    return {"third_party_ai": body.third_party_ai}


@router.delete("/users/me", status_code=204)
def delete_account(
    body: DeleteAccount, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    reports = db.scalars(
        select(MedicalReport).where(MedicalReport.owner_id == user.id).with_for_update()
    ).all()
    for report in reports:
        Storage().delete(report.storage_key)
    # External deletion is done before the DB commit so failures remain retryable.
    if settings().auth_provider == "supabase":
        supabase_request(f"admin/users/{user.id}", method="DELETE", admin=True)
    db.delete(user)
    db.commit()
    for cookie in ["medicare_session", "medicare_csrf"]:
        response.delete_cookie(cookie, path="/")
    response.delete_cookie("medicare_refresh", path="/api/v1/auth")


@router.get("/users/me/summary", response_model=UserSummary)
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .models import Prescription

    return UserSummary(
        report_count=db.scalar(
            select(func.count()).select_from(MedicalReport).where(MedicalReport.owner_id == user.id)
        ),
        completed_count=db.scalar(
            select(func.count())
            .select_from(MedicalReport)
            .where(MedicalReport.owner_id == user.id, MedicalReport.status == "completed")
        ),
        prescription_count=db.scalar(
            select(func.count()).select_from(Prescription).where(Prescription.owner_id == user.id)
        ),
    )
