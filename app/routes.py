from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from starlette.responses import FileResponse
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.models import Certificate, GenerationJob
from app.schemas import (
    CertificateJobCreate,
    CertificateStatusResponse,
    JobResponse,
    JobStatusResponse,
)

router = APIRouter(prefix="/api/certificates")


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
def create_certificate_job(
    payload: CertificateJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = GenerationJob(
        event_name=payload.event_name,
        organization=payload.organization,
        event_date=payload.event_date,
        status="pending",
        total_count=len(payload.recipients),
        success_count=0,
        failure_count=0,
    )

    db.add(job)
    db.flush()

    for recipient in payload.recipients:
        db.add(
            Certificate(
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=recipient.email,
                status="pending",
            )
        )

    db.commit()
    db.refresh(job)

    background_tasks.add_task(services.process_generation_job, job.id)

    return JobResponse(
        id=job.id,
        event_name=job.event_name,
        organization=job.organization,
        event_date=job.event_date,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failure_count=job.failure_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: UUID, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, str(job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    total_count = job.total_count or 0
    if total_count > 0:
        progress = round(((job.success_count or 0) + (job.failure_count or 0)) / total_count * 100, 2)
    else:
        progress = 0.0

    certificates = [
        CertificateStatusResponse(
            id=certificate.id,
            recipient_name=certificate.recipient_name,
            recipient_email=certificate.recipient_email,
            status=certificate.status,
            file_path=certificate.file_path,
            error_message=certificate.error_message,
        )
        for certificate in job.certificates
    ]

    return JobStatusResponse(
        id=job.id,
        event_name=job.event_name,
        organization=job.organization,
        event_date=job.event_date,
        status=job.status,
        total_count=total_count,
        success_count=job.success_count or 0,
        failure_count=job.failure_count or 0,
        progress=progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
        certificates=certificates,
    )


@router.get("/{certificate_id}")
def get_certificate_file(certificate_id: UUID, db: Session = Depends(get_db)):
    certificate = db.get(Certificate, str(certificate_id))
    if certificate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if certificate.status in {"pending", "processing"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Certificate is not ready yet")

    if certificate.status == "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Certificate generation failed")

    if not certificate.file_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Certificate file is not available")

    file_path = Path(certificate.file_path).resolve()
    generated_dir = services.GENERATED_DIR.resolve()
    try:
        file_path.relative_to(generated_dir)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid certificate file path") from exc

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate file not found")

    return FileResponse(str(file_path), media_type="application/pdf", filename=f"{certificate.id}.pdf")
