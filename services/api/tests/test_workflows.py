import io
from datetime import timedelta
from uuid import uuid4
import pymupdf
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.db import SessionLocal
from app.config import settings
from app.models import MedicalReport, ReportExtraction, AnalysisResult, User, PharmacyInventory, now
from app.processing import extract_measurements, classify, analyze, controlled_gemini
from app.schemas import AnalysisOut
from app.storage import Storage
from app.routes_catalog import inventory_view
from conftest import register


def pdf(text="Heart rate: 105 bpm Reference: 60-100"):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((30, 60), text)
    return doc.tobytes()


def upload(client, kind="heart_rate", text="Heart rate: 105 bpm Reference: 60-100"):
    response = client.post(
        "/reports/upload",
        files={"file": ("synthetic.pdf", pdf(text), "application/pdf")},
        data={"consent": "true", "report_type": kind},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_auth_requires_consent_and_strong_password(client):
    result = client.post(
        "/auth/register",
        json={"email": "test@example.com", "name": "Tester", "password": "short", "consent": False},
    )
    assert result.status_code == 422
    assert client.get("/users/me").status_code == 401


def test_session_cookie_and_logout_revocation(signed):
    token = signed.cookies["medicare_session"]
    assert signed.get("/users/me").status_code == 200
    response = signed.post("/auth/logout")
    assert response.status_code == 204
    signed.cookies.set("medicare_session", token)
    assert signed.get("/users/me").status_code == 401


def test_login_error_does_not_expose_identity(client):
    register(client)
    client.post("/auth/logout")
    result = client.post("/auth/login", json={"email": "one@example.com", "password": "Wrong-password-123"})
    assert result.status_code == 401
    result = client.post(
        "/auth/login", json={"email": "one@example.com", "password": "A-long-test-password-123"}
    )
    assert result.status_code == 200
    assert "password_hash" not in result.text


def test_csrf_and_origin_checks(signed):
    assert (
        signed.patch("/users/me", headers={"X-CSRF-Token": "wrong"}, json={"name": "Changed"}).status_code
        == 403
    )
    assert (
        signed.patch(
            "/users/me", headers={"Origin": "https://evil.example"}, json={"name": "Changed"}
        ).status_code
        == 403
    )


def test_upload_processing_real_pdf(signed):
    rid = upload(signed)
    assert signed.get(f"/reports/{rid}").json()["status"] == "completed"
    result = signed.get(f"/reports/{rid}/analysis")
    assert result.status_code == 200
    validated = AnalysisOut.model_validate(result.json())
    assert signed.get("/users/me/summary").json()["report_count"] == 1
    assert validated.measurements[0].value == 105
    assert validated.measurements[0].source_quote == "Heart rate: 105 bpm Reference: 60-100"
    assert validated.measurements[0].comparison == "above_reported_range"
    assert signed.get(f"/reports/{rid}/download").content.startswith(b"%PDF")


def test_encrypted_storage(signed):
    rid = upload(signed)
    with SessionLocal() as db:
        row = db.get(MedicalReport, __import__("uuid").UUID(rid))
        encrypted = Storage()._path(row.storage_key).read_bytes()
        assert b"%PDF" not in encrypted and b"Heart rate" not in encrypted
        assert Storage().get(row.storage_key).startswith(b"%PDF")


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", ""),
        ("GET", "/analysis"),
        ("GET", "/extraction"),
        ("GET", "/download"),
        ("GET", "/signed-url"),
        ("POST", "/analyze"),
        ("DELETE", ""),
    ],
)
def test_owner_isolation(signed, method, path):
    rid = upload(signed)
    with TestClient(app) as other:
        register(other, "two@example.com")
        assert other.request(method, f"/reports/{rid}{path}").status_code == 404
        assert other.get("/reports").json() == []


def test_upload_content_and_consent(signed):
    for name, payload, consent in [
        ("malicious.pdf", b"<script>alert(1)</script>", "true"),
        ("report.pdf", pdf(), "false"),
        ("report.exe", pdf(), "true"),
    ]:
        response = signed.post("/reports/upload", files={"file": (name, payload)}, data={"consent": consent})
        assert response.status_code == 422
    response = signed.post("/reports/upload", files={"file": ("empty.pdf", b"")}, data={"consent": "true"})
    assert response.status_code == 413


def test_active_pdf_rejected(signed):
    doc = pymupdf.open(stream=pdf(), filetype="pdf")
    doc.embfile_add("payload.txt", b"not allowed")
    response = signed.post(
        "/reports/upload", files={"file": ("active.pdf", doc.tobytes())}, data={"consent": "true"}
    )
    assert response.status_code == 422


def test_image_extension_spoof_rejected(signed):
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(buf, format="PNG")
    result = signed.post(
        "/reports/upload", files={"file": ("wrong.jpg", buf.getvalue())}, data={"consent": "true"}
    )
    assert result.status_code == 422


def test_delete_cascades_and_removes_blob(signed):
    rid = upload(signed)
    with SessionLocal() as db:
        row = db.get(MedicalReport, __import__("uuid").UUID(rid))
        path = Storage()._path(row.storage_key)
    assert signed.delete(f"/reports/{rid}").status_code == 204
    assert not path.exists()
    assert signed.get(f"/reports/{rid}/analysis").status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReportExtraction)) == 0
        assert db.scalar(select(func.count()).select_from(AnalysisResult)) == 0


def test_prescription_human_confirmation(signed):
    result = signed.post(
        "/prescriptions/upload",
        files={"file": ("rx.pdf", pdf("Unreadable handwritten prescription"))},
        data={"consent": "true"},
    )
    assert result.status_code == 201
    pid = result.json()["id"]
    row = signed.get(f"/prescriptions/{pid}").json()
    assert row["items"] == [] and row["confirmed_at"] is None
    body = {
        "items": [{"name": "Synthetic medicine", "strength": "as written", "instructions": "as written"}],
        "confirmed": False,
    }
    assert signed.patch(f"/prescriptions/{pid}/confirm", json=body).status_code == 422
    body["confirmed"] = True
    assert signed.patch(f"/prescriptions/{pid}/confirm", json=body).status_code == 200
    assert signed.get(f"/prescriptions/{pid}").json()["items"][0]["name"] == "Synthetic medicine"
    with TestClient(app) as other:
        register(other, "rx-other@example.com")
        assert other.get(f"/prescriptions/{pid}").status_code == 404
        assert other.patch(f"/prescriptions/{pid}/confirm", json=body).status_code == 404


def test_no_invented_measurements_or_diagnosis():
    assert extract_measurements("Unreadable. Glucose: ??") == []
    assert extract_measurements("Heart rate: 105") == []  # Missing unit must not be guessed.
    result = analyze("", {"needs_review": True}, "xray")
    assert result["status"] == "unavailable"
    assert result["measurements"] == []
    assert result["model"]["validation"] == "unavailable"
    assert classify("Haemoglobin: 12 g/dL", "document") == "blood_test"


@pytest.mark.parametrize("kind", ["ecg", "xray"])
def test_specialized_models_fail_closed(signed, kind):
    rid = upload(signed, kind)
    result = signed.get(f"/reports/{rid}/analysis").json()
    assert result["status"] == "unavailable"
    assert not any("confidence" in k for k in result)


def test_catalog_starts_without_invented_records(signed):
    assert signed.get("/medicines/search?q=paracetamol").json() == []
    assert signed.get("/medicines/" + str(uuid4())).status_code == 404
    assert signed.get("/pharmacies/nearby?q=Kolkata").status_code == 503
    assert signed.get("/pharmacies/nearby?lat=500&lng=4").status_code == 422


def test_pharmacy_discovery_does_not_imply_stock(signed, monkeypatch):
    from app import routes_catalog

    monkeypatch.setattr(settings(), "google_maps_api_key", "test-only")
    import httpx

    def response(*args, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://places.googleapis.com"),
            json={
                "places": [
                    {
                        "id": "synthetic-place",
                        "displayName": {"text": "Synthetic Pharmacy"},
                        "formattedAddress": "Synthetic location",
                        "location": {"latitude": 22.5, "longitude": 88.3},
                    }
                ]
            },
        )

    monkeypatch.setattr(routes_catalog.httpx, "post", response)
    result = signed.get("/pharmacies/nearby?q=Kolkata")
    assert result.status_code == 200
    row = result.json()[0]
    assert row["stock_status"] == "availability_not_confirmed"
    assert signed.get(f"/pharmacies/{row['id']}/inventory").json()["items"] == []


def test_inventory_expiration_is_not_in_stock():
    row = PharmacyInventory(
        id=uuid4(),
        pharmacy_id=uuid4(),
        medicine_id=uuid4(),
        status="verified_in_stock",
        source_reference="test-only",
        verified_at=now() - timedelta(hours=2),
        expires_at=now() - timedelta(hours=1),
    )
    assert inventory_view(row)["status"] == "availability_not_confirmed"


def test_admin_access_control(signed):
    assert signed.get("/admin/metrics").status_code == 403
    assert signed.get("/admin/model-versions").status_code == 403
    assert signed.post("/admin/medicines", json={}).status_code == 403


def test_privacy_and_account_erasure(signed):
    upload(signed)
    assert signed.get("/users/me/consent").json()["third_party_ai"] is False
    assert signed.patch("/users/me/consent", json={"third_party_ai": True}).status_code == 200
    assert signed.patch("/users/me/consent", json={"third_party_ai": False}).status_code == 200
    assert signed.request("DELETE", "/users/me", json={"confirmation": "wrong"}).status_code == 422
    result = signed.request("DELETE", "/users/me", json={"confirmation": "DELETE MY ACCOUNT"})
    assert result.status_code == 204
    assert signed.get("/users/me").status_code == 401
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(MedicalReport)) == 0


def test_gemini_cannot_introduce_findings(monkeypatch):
    from app import processing
    import httpx

    monkeypatch.setattr(settings(), "gemini_api_key", "test-only")
    monkeypatch.setattr(
        processing.httpx,
        "post",
        lambda *a, **k: httpx.Response(
            200,
            request=httpx.Request("POST", "https://example.test"),
            json={"candidates": [{"content": {"parts": [{"text": '[{"diagnosis":"invented"}]'}]}}]},
        ),
    )
    assert controlled_gemini(extract_measurements("Heart rate: 80 bpm")) == "deterministic-evidence-templates"


def test_prescription_fields_are_literal_and_unknown_names_not_guessed():
    from types import SimpleNamespace
    from app.processing import prescription_candidates

    catalog = [SimpleNamespace(generic_name="SyntheticMed", brand_name="")]
    result = prescription_candidates("SyntheticMed 10 mg tablet with food\nUnreadable ???", catalog)
    assert result == [
        {
            "name": "SyntheticMed",
            "strength": "10 mg",
            "dosage_form": "tablet",
            "instructions": "with food",
            "source_quote": "SyntheticMed 10 mg tablet with food",
            "verification": "unconfirmed",
        }
    ]
    assert prescription_candidates("UnknownDrug 50 mg tablet", catalog) == []
    assert prescription_candidates("SyntheticMed ??? tablet", catalog)[0]["strength"] == ""


def test_validation_errors_do_not_echo_password(client):
    result = client.post(
        "/auth/register", json={"email": "invalid", "password": "secret", "name": "A", "consent": True}
    )
    assert result.status_code == 422
    assert "secret" not in result.text


def test_supabase_delete_uses_bucket_prefix_api(monkeypatch):
    from app import storage
    import httpx

    cfg = settings()
    monkeypatch.setattr(cfg, "storage_provider", "supabase")
    monkeypatch.setattr(cfg, "supabase_url", "https://project.example.com")
    monkeypatch.setattr(cfg, "supabase_service_role_key", "test-only")
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return httpx.Response(200, json=[], request=httpx.Request(method, url))

    monkeypatch.setattr(storage.httpx, "request", request)
    Storage().delete("owner/report")
    assert calls[0][0] == "DELETE"
    assert calls[0][1].endswith("/storage/v1/object/medical-reports")
    assert calls[0][2]["json"] == {"prefixes": ["owner/report"]}


def test_public_storage_bucket_is_rejected(monkeypatch):
    from app import storage
    import httpx

    monkeypatch.setattr(
        storage.httpx,
        "get",
        lambda *a, **k: httpx.Response(
            200, json={"public": True}, request=httpx.Request("GET", "https://example.com")
        ),
    )
    with pytest.raises(RuntimeError, match="private"):
        storage.verify_private_bucket()
