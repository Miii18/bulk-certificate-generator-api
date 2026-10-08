from __future__ import annotations

import time

import app.database as database
import app.services as services
from app.models import Certificate


def test_all_success_job_finishes_completed_and_counts_total(test_client, valid_payload):
    payload = {
        **valid_payload,
        "recipients": [
            {"name": "Alice Test", "email": "alice@example.com"},
            {"name": "Bob Test", "email": "bob@example.com"},
            {"name": "Cara Test", "email": "cara@example.com"},
        ],
    }

    response = test_client.post("/api/certificates/jobs", json=payload)
    assert response.status_code == 202

    job_id = response.json()["id"]
    deadline = time.time() + 20
    final_data = None

    while time.time() < deadline:
        status_response = test_client.get(f"/api/certificates/jobs/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        if data["status"] in {"completed", "completed_with_errors", "failed"}:
            final_data = data
            break
        time.sleep(0.5)

    assert final_data is not None
    assert final_data["status"] == "completed"
    assert final_data["total_count"] == 3
    assert final_data["success_count"] == 3
    assert final_data["failure_count"] == 0
    assert final_data["progress"] == 100.0
    assert len(final_data["certificates"]) == 3
    assert {cert["status"] for cert in final_data["certificates"]} == {"completed"}


def test_all_failure_job_finishes_failed_and_keeps_processing_remaining_recipients(test_client, monkeypatch):
    payload = {
        "event_name": "Failure Lab",
        "organization": "Failure Org",
        "event_date": "2026-10-08",
        "recipients": [
            {"name": "Alice Test", "email": "alice@example.com"},
            {"name": "Bob Test", "email": "bob@example.com"},
            {"name": "Cara Test", "email": "cara@example.com"},
        ],
    }

    calls = []

    def fail_generation(job, certificate):
        calls.append(certificate.recipient_email)
        raise ValueError("forced generation failure")

    monkeypatch.setattr(services, "generate_certificate_pdf", fail_generation)

    response = test_client.post("/api/certificates/jobs", json=payload)
    assert response.status_code == 202

    job_id = response.json()["id"]
    deadline = time.time() + 20
    final_data = None

    while time.time() < deadline:
        status_response = test_client.get(f"/api/certificates/jobs/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        if data["status"] in {"completed", "completed_with_errors", "failed"}:
            final_data = data
            break
        time.sleep(0.5)

    assert final_data is not None
    assert final_data["status"] == "failed"
    assert final_data["total_count"] == 3
    assert final_data["success_count"] == 0
    assert final_data["failure_count"] == 3
    assert final_data["progress"] == 100.0
    assert sorted(calls) == [
        "alice@example.com",
        "bob@example.com",
        "cara@example.com",
    ]
    assert {cert["status"] for cert in final_data["certificates"]} == {"failed"}


def test_certificate_download_rejects_path_outside_generated_directory(test_client, tmp_path):
    payload = {
        "event_name": "Security Test Workshop",
        "organization": "Security Org",
        "event_date": "2026-10-08",
        "recipients": [{"name": "Mallory Test", "email": "mallory@example.com"}],
    }

    response = test_client.post("/api/certificates/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    db = database.SessionLocal()
    try:
        certificate = db.query(Certificate).filter_by(job_id=job_id).one()
        certificate.status = "completed"
        certificate.file_path = str(tmp_path / "outside" / "malicious.pdf")
        db.commit()
        certificate_id = certificate.id
    finally:
        db.close()

    download_response = test_client.get(f"/api/certificates/{certificate_id}")
    assert download_response.status_code == 403
    assert download_response.json()["detail"] == "Invalid certificate file path"
