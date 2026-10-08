from __future__ import annotations

import time


def test_generation_and_job_status_progress(test_client, valid_payload):
    response = test_client.post("/api/certificates/jobs", json=valid_payload)
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
    assert final_data["total_count"] == 2
    assert final_data["success_count"] == 2
    assert final_data["failure_count"] == 0
    assert final_data["status"] == "completed"
    assert final_data["progress"] == 100.0
    assert len(final_data["certificates"]) == 2

    for cert in final_data["certificates"]:
        assert cert["status"] == "completed"
        assert cert["file_path"] is not None


def test_missing_job_returns_404(test_client):
    response = test_client.get("/api/certificates/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
