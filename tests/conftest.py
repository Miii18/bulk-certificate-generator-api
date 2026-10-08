from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
import app.services as services
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def test_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    original_session_local = database.SessionLocal
    original_services_session_local = services.SessionLocal
    original_generated_dir = services.GENERATED_DIR

    database.SessionLocal = TestingSessionLocal
    services.SessionLocal = TestingSessionLocal
    monkeypatch.setattr(services, "GENERATED_DIR", tmp_path / "generated")

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        database.SessionLocal = original_session_local
        services.SessionLocal = original_services_session_local
        services.GENERATED_DIR = original_generated_dir
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def valid_payload() -> dict:
    return {
        "event_name": "Test AI Workshop",
        "organization": "Test Organization",
        "event_date": "2026-10-08",
        "recipients": [
            {"name": "Alice Test", "email": "alice@example.com"},
            {"name": "Bob Test", "email": "bob@example.com"},
        ],
    }
