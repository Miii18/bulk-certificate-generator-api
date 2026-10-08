from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {
            "event_name": "Test AI Workshop",
            "organization": "Test Organization",
            "event_date": "2026-10-08",
            "recipients": [{"name": "Test User", "email": "not-an-email"}],
        },
        {
            "event_name": "Test AI Workshop",
            "organization": "Test Organization",
            "event_date": "2026-10-08",
            "recipients": [{"name": "   ", "email": "test@example.com"}],
        },
        {
            "event_name": "Test AI Workshop",
            "organization": "Test Organization",
            "event_date": "2026-10-08",
            "recipients": [],
        },
    ],
)
def test_invalid_payloads_are_rejected(test_client, payload):
    response = test_client.post("/api/certificates/jobs", json=payload)
    assert response.status_code == 422


def test_valid_payload_succeeds(test_client, valid_payload):
    response = test_client.post("/api/certificates/jobs", json=valid_payload)
    assert response.status_code == 202
