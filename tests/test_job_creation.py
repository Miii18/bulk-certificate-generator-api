from __future__ import annotations

import app.database as database
from app.models import Certificate, GenerationJob


def test_create_job_creates_job_and_certificate_records(test_client, valid_payload):
    response = test_client.post("/api/certificates/jobs", json=valid_payload)

    assert response.status_code == 202
    data = response.json()
    assert data["event_name"] == valid_payload["event_name"]
    assert data["organization"] == valid_payload["organization"]
    assert data["total_count"] == 2
    assert data["id"] is not None
    assert data["status"] in {"pending", "processing", "completed"}

    job_id = data["id"]
    db = database.SessionLocal()
    try:
        job = db.query(GenerationJob).filter_by(id=job_id).one()
        assert job.event_name == valid_payload["event_name"]
        assert job.organization == valid_payload["organization"]
        assert job.total_count == 2
        assert db.query(Certificate).filter_by(job_id=job_id).count() == 2
    finally:
        db.close()
