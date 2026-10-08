from __future__ import annotations

import time

import app.services as services


def test_one_failure_does_not_stop_other_recipients(test_client, monkeypatch):
    real_generate = services.generate_certificate_pdf

    def fake_generate(job, certificate):
        if certificate.recipient_email == "bob@example.com":
            raise ValueError("forced certificate failure")
        return real_generate(job, certificate)

    monkeypatch.setattr(services, "generate_certificate_pdf", fake_generate)

    payload = {
        "event_name": "Failure Test Workshop",
        "organization": "Failure Org",
        "event_date": "2026-10-08",
        "recipients": [
            {"name": "Alice Test", "email": "alice@example.com"},
            {"name": "Bob Test", "email": "bob@example.com"},
        ],
    }

    response = test_client.post("/api/certificates/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    deadline = time.time() + 20
    final_data = None
    while time.time() < deadline:
        status_response = test_client.get(f"/api/certificates/jobs/{job_id}")
        data = status_response.json()
        if data["status"] in {"completed", "completed_with_errors", "failed"}:
            final_data = data
            break
        time.sleep(0.5)

    assert final_data is not None
    assert final_data["status"] == "completed_with_errors"
    assert final_data["total_count"] == 2
    assert final_data["success_count"] == 1
    assert final_data["failure_count"] == 1
    assert final_data["progress"] == 100.0

    certificate_statuses = {entry["recipient_email"]: entry["status"] for entry in final_data["certificates"]}
    assert certificate_statuses["alice@example.com"] == "completed"
    assert certificate_statuses["bob@example.com"] == "failed"

    failing_certificate = next(entry for entry in final_data["certificates"] if entry["recipient_email"] == "bob@example.com")
    assert failing_certificate["error_message"]
