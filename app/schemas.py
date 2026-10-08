from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CertificateRecipientInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be empty or whitespace only.")
        return value.strip()


class CertificateJobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_name: str = Field(..., min_length=1)
    organization: str = Field(..., min_length=1)
    event_date: date
    recipients: list[CertificateRecipientInput] = Field(..., min_length=1)


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_name: str
    recipient_email: str
    status: str
    file_path: str | None = None
    error_message: str | None = None


class CertificateStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipient_name: str
    recipient_email: str
    status: str
    file_path: str | None = None
    error_message: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_name: str
    organization: str
    event_date: date
    status: str
    total_count: int | None = None
    success_count: int | None = None
    failure_count: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_name: str
    organization: str
    event_date: date
    status: str
    total_count: int
    success_count: int
    failure_count: int
    progress: float = 0.0
    created_at: datetime | None = None
    completed_at: datetime | None = None
    certificates: list[CertificateStatusResponse] = Field(default_factory=list)
