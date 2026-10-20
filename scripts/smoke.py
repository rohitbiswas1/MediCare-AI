"""Exercise the actual HTTP API, PostgreSQL, Redis/Celery, encryption, and Tesseract.
Synthetic data only. Removes created accounts and files on completion.
Run: services/api/.venv/bin/python scripts/smoke.py
"""

import io
import os
import time
import uuid

import httpx
import pymupdf
from PIL import Image, ImageDraw, ImageFont

BASE = os.environ.get("MEDICARE_API_BASE", "http://127.0.0.1:8000")


def mutate(client, method, path, **kwargs):
    headers = {"X-CSRF-Token": client.cookies.get("medicare_csrf", "")}
    return client.request(method, path, headers=headers, **kwargs)


def main():
    a, b = httpx.Client(base_url=BASE, timeout=30), httpx.Client(base_url=BASE, timeout=30)
    accounts = []
    try:
        assert a.get("/health").json()["status"] == "ok"
        for client in [a, b]:
            result = client.post(
                "/auth/register",
                json={
                    "email": f"smoke-{uuid.uuid4().hex}@example.com",
                    "password": "Synthetic-test-only-123!",
                    "name": "Synthetic Test",
                    "consent": True,
                },
            )
            assert result.status_code == 201, result.text
            accounts.append(client)
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text((40, 60), "SYNTHETIC TEST REPORT - NOT A PATIENT")
        page.insert_text((40, 90), "Heart rate: 105 bpm Reference: 60-100")
        page.insert_text((40, 115), "Haemoglobin: 13.5 g/dL Reference: 12-16")
        upload = mutate(
            a,
            "POST",
            "/reports/upload",
            files={"file": ("synthetic.pdf", pdf.tobytes(), "application/pdf")},
            data={"consent": "true", "report_type": "heart_rate"},
        )
        assert upload.status_code == 201, upload.text
        report_id = upload.json()["id"]
        assert b.get(f"/reports/{report_id}").status_code == 404
        assert mutate(b, "DELETE", f"/reports/{report_id}").status_code == 404
        assert a.post(f"/reports/{report_id}/analyze").status_code == 403
        for _ in range(60):
            report = a.get(f"/reports/{report_id}").json()
            if report["status"] in {"completed", "failed"}:
                break
            time.sleep(0.5)
        assert report["status"] == "completed", report
        analysis = a.get(f"/reports/{report_id}/analysis").json()
        assert [m["value"] for m in analysis["measurements"]] == [105, 13.5], analysis
        assert analysis["measurements"][0]["comparison"] == "above_reported_range"
        assert a.get(f"/reports/{report_id}/download").content.startswith(b"%PDF")
        print(
            "PASS: registration, sessions, PostgreSQL, queue, PDF extraction, evidence comparisons, ownership, CSRF, authorized download"
        )
        image = Image.new("RGB", (1500, 650), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
        draw.text((50, 60), "SYNTHETIC OCR TEST - NOT A PATIENT", fill="black", font=font)
        draw.text((50, 180), "Heart rate: 88 bpm", fill="black", font=font)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        result = mutate(
            a,
            "POST",
            "/reports/upload",
            files={"file": ("synthetic.png", buffer.getvalue(), "image/png")},
            data={"consent": "true", "report_type": "heart_rate"},
        )
        assert result.status_code == 201, result.text
        image_id = result.json()["id"]
        for _ in range(60):
            report = a.get(f"/reports/{image_id}").json()
            if report["status"] in {"completed", "failed"}:
                break
            time.sleep(0.5)
        assert report["status"] == "completed", report
        result = a.get(f"/reports/{image_id}/analysis").json()
        assert result["measurements"][0]["value"] == 88, result
        print("PASS: actual Tesseract image OCR and extraction")
        for rid in [report_id, image_id]:
            assert mutate(a, "DELETE", f"/reports/{rid}").status_code == 204
            assert a.get(f"/reports/{rid}").status_code == 404
        print("PASS: report deletion")
    finally:
        for client in accounts:
            result = mutate(client, "DELETE", "/users/me", json={"confirmation": "DELETE MY ACCOUNT"})
            assert result.status_code == 204, result.text
            assert client.get("/users/me").status_code == 401
        a.close()
        b.close()
    print("PASS: account deletion and test cleanup")


if __name__ == "__main__":
    main()
