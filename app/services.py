from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.database import SessionLocal
from app.models import Certificate, GenerationJob

GENERATED_DIR = Path(__file__).resolve().parents[1] / "generated"


def ensure_generated_dir() -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    return GENERATED_DIR


def generate_certificate_pdf(job: GenerationJob, certificate: Certificate) -> Path:
    output_dir = ensure_generated_dir()
    pdf_path = output_dir / f"{certificate.id}.pdf"

    pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    pdf.setTitle("Certificate of Participation")
    pdf.setFillColor(colors.HexColor("#1F2A44"))
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawCentredString(width / 2, height - 72, "Certificate of Participation")

    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 110, "This certificate is proudly presented to")

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 160, certificate.recipient_name)

    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 210, "for successfully participating in")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 250, job.event_name)

    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, height - 290, "organized by")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 330, job.organization)

    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 370, job.event_date.isoformat())

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, 115, f"Certificate ID: {certificate.id}")

    pdf.save()
    return pdf_path


def process_generation_job(job_id: UUID) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, str(job_id))
        if job is None:
            return

        job.status = "processing"
        job.success_count = 0
        job.failure_count = 0
        job.completed_at = None
        db.commit()

        for certificate in job.certificates:
            certificate.status = "processing"
            certificate.error_message = None
            certificate.file_path = None
            db.add(certificate)
            db.commit()

            try:
                file_path = generate_certificate_pdf(job, certificate)
                certificate.file_path = str(file_path)
                certificate.status = "completed"
                certificate.error_message = None
                job.success_count = (job.success_count or 0) + 1
            except Exception as exc:  # noqa: BLE001
                certificate.status = "failed"
                certificate.file_path = None
                certificate.error_message = str(exc)
                job.failure_count = (job.failure_count or 0) + 1

            db.add(certificate)
            db.commit()

        if job.failure_count == 0:
            job.status = "completed"
        elif job.success_count == 0:
            job.status = "failed"
        else:
            job.status = "completed_with_errors"

        job.completed_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
    finally:
        db.close()
