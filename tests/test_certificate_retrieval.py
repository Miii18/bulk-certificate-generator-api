from __future__ import annotations

import time

import app.database as database
from app.models import Certificate


def test_certificate_download_returns_pdf(test_client, valid_payload):
    response = test_client.post("/api/certificates/jobs", json=valid_payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    for _ in range(30):
        status_response = test_client.get(f"/api/certificates/jobs/{job_id}")
        data = status_response.json()
        if data["status"] == "completed":
            break
        time.sleep(0.5)

    db = database.SessionLocal()
    try:
        certificate = db.query(Certificate).filter_by(job_id=job_id).first()
        assert certificate is not None
        cert_id = certificate.id
    finally:
        db.close()

    download_response = test_client.get(f"/api/certificates/{cert_id}")
    assert download_response.status_code == 200
    assert "application/pdf" in download_response.headers.get("content-type", "")
    assert download_response.content.startswith(b"%PDF")


def test_missing_certificate_returns_404(test_client):
    response = test_client.get("/api/certificates/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_pending_and_failed_certificate_return_conflict(test_client, monkeypatch):
    payload = {
        "event_name": "Pending Test Workshop",
        "organization": "Pending Org",
        "event_date": "2026-10-08",
        "recipients": [{"name": "Alice Test", "email": "alice@example.com"}],
    }

    create_response = test_client.post("/api/certificates/jobs", json=payload)
    assert create_response.status_code == 202
    job_id = create_response.json()["id"]

    db = database.SessionLocal()
    try:
        cert = db.query(Certificate).filter_by(job_id=job_id).one()
        cert.status = "pending"
        cert.file_path = None
        db.commit()
        pending_id = cert.id

        cert.status = "failed"
        cert.file_path = None
        cert.error_message = "forced error"
        db.commit()
        failed_id = cert.id
    finally:
        db.close()

    pending_response = test_client.get(f"/api/certificates/{pending_id}")
    assert pending_response.status_code == 409

    failed_response = test_client.get(f"/api/certificates/{failed_id}")
    assert failed_response.status_code == 409
