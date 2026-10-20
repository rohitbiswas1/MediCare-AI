from datetime import timedelta, timezone
from uuid import UUID
from urllib.parse import quote
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from .auth import current_user, admin_user
from .config import settings
from .db import get_db
from .models import User, Medicine, Pharmacy, PharmacyInventory, MedicalReport, ModelVersion, AuditEvent, now
from .schemas import MedicineIn, InventoryIn

router = APIRouter()


def public_row(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def inventory_view(item):
    data = public_row(item)
    expiry = (
        item.expires_at.replace(tzinfo=timezone.utc) if item.expires_at.tzinfo is None else item.expires_at
    )
    if expiry <= now():
        data["status"] = "availability_not_confirmed"
    return data


@router.get("/medicines/search")
def medicines(
    q: str = Query("", max_length=100), user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if len(q.strip()) < 2:
        return []
    escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = db.scalars(
        select(Medicine)
        .where(
            or_(
                Medicine.generic_name.ilike(f"%{escaped}%", escape="\\"),
                Medicine.brand_name.ilike(f"%{escaped}%", escape="\\"),
            )
        )
        .limit(30)
    ).all()
    return [public_row(row) for row in rows]


@router.get("/medicines/{medicine_id}")
def medicine(medicine_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Medicine, medicine_id)
    if not row:
        raise HTTPException(404, "Medicine not found.")
    return public_row(row)


@router.post("/admin/medicines", status_code=201)
def import_medicine(body: MedicineIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    values = body.model_dump()
    values["source_url"] = str(body.source_url)
    row = Medicine(**values)
    db.add(row)
    db.add(AuditEvent(owner_id=user.id, action="catalog.record_imported"))
    db.commit()
    return public_row(row)


@router.get("/pharmacies/nearby")
def nearby(
    q: str = Query("", max_length=200),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    cfg = settings()
    if not q.strip() and (lat is None or lng is None):
        raise HTTPException(422, "Enter a city, PIN code, or address, or share your location.")
    if not cfg.google_maps_api_key:
        raise HTTPException(
            503, "Pharmacy discovery is not connected yet. No locations or stock have been assumed."
        )
    headers = {
        "X-Goog-Api-Key": cfg.google_maps_api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.regularOpeningHours,places.googleMapsUri",
    }
    if q.strip():
        endpoint = "places:searchText"
        payload = {
            "textQuery": "pharmacy in " + q.strip(),
            "includedType": "pharmacy",
            "regionCode": "IN",
            "pageSize": 15,
        }
    else:
        endpoint = "places:searchNearby"
        payload = {
            "includedTypes": ["pharmacy"],
            "maxResultCount": 15,
            "locationRestriction": {
                "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 5000.0}
            },
        }
    try:
        response = httpx.post(
            f"https://places.googleapis.com/v1/{endpoint}", headers=headers, json=payload, timeout=20
        )
        response.raise_for_status()
        places = response.json().get("places", [])
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Pharmacy discovery is temporarily unavailable.")
    rows = []
    for place in places:
        if not place.get("id"):
            continue
        row = db.scalar(select(Pharmacy).where(Pharmacy.place_id == place["id"]))
        if not row:
            row = Pharmacy(place_id=place["id"])
            db.add(row)
        row.name = place.get("displayName", {}).get("text", "Pharmacy")
        row.address = place.get("formattedAddress", "")
        row.latitude = place.get("location", {}).get("latitude")
        row.longitude = place.get("location", {}).get("longitude")
        row.phone = place.get("nationalPhoneNumber")
        row.hours = place.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        row.directions_url = (
            "https://www.google.com/maps/search/?api=1&query="
            + quote(row.name)
            + "&query_place_id="
            + quote(row.place_id)
        )
        row.verified_at = now()
        rows.append(row)
    db.commit()
    return [dict(public_row(row), stock_status="availability_not_confirmed") for row in rows]


@router.get("/pharmacies/{pharmacy_id}")
def pharmacy(pharmacy_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(Pharmacy, pharmacy_id)
    if not row:
        raise HTTPException(404, "Pharmacy not found.")
    return dict(public_row(row), stock_status="availability_not_confirmed")


@router.get("/pharmacies/{pharmacy_id}/inventory")
def inventory(pharmacy_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Pharmacy, pharmacy_id):
        raise HTTPException(404, "Pharmacy not found.")
    rows = db.scalars(select(PharmacyInventory).where(PharmacyInventory.pharmacy_id == pharmacy_id)).all()
    return {"items": [inventory_view(row) for row in rows], "default_status": "availability_not_confirmed"}


@router.put("/admin/pharmacies/{pharmacy_id}/inventory")
def update_inventory(
    pharmacy_id: UUID, body: InventoryIn, user: User = Depends(admin_user), db: Session = Depends(get_db)
):
    if body.expires_at.tzinfo is None or not now() < body.expires_at <= now() + timedelta(hours=24):
        raise HTTPException(422, "Inventory evidence must expire within 24 hours and include a timezone.")
    if not db.get(Pharmacy, pharmacy_id) or not db.get(Medicine, body.medicine_id):
        raise HTTPException(404, "Pharmacy or medicine not found.")
    row = db.scalar(
        select(PharmacyInventory).where(
            PharmacyInventory.pharmacy_id == pharmacy_id, PharmacyInventory.medicine_id == body.medicine_id
        )
    )
    if not row:
        row = PharmacyInventory(pharmacy_id=pharmacy_id, medicine_id=body.medicine_id)
        db.add(row)
    row.status, row.source_reference = body.status, body.source_reference
    row.verified_at, row.expires_at = now(), body.expires_at
    db.add(AuditEvent(owner_id=user.id, action="inventory.verified", resource_id=str(pharmacy_id)))
    db.commit()
    return inventory_view(row)


@router.get("/admin/metrics")
def metrics(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "reports": db.scalar(select(func.count()).select_from(MedicalReport)),
        "medicines": db.scalar(select(func.count()).select_from(Medicine)),
        "model_versions": db.scalar(select(func.count()).select_from(ModelVersion)),
        "mode": settings().app_mode,
    }


@router.get("/admin/model-versions")
def versions(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [public_row(row) for row in db.scalars(select(ModelVersion)).all()]
