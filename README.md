# Bulk Certificate Generator API

A FastAPI application that accepts a certificate event and a list of recipients, creates a generation job, generates one PDF certificate per recipient, tracks status and progress, and exposes secure retrieval of completed PDF files.

## Project overview

This project is designed around a practical assignment workflow:

- submit a certificate batch job through a REST API
- validate the payload before processing
- create job and certificate records in the database
- generate one certificate PDF per recipient asynchronously
- track job-level and per-certificate status
- allow secure file download only for completed certificate files
- keep the production database on PostgreSQL while using an isolated SQLite test database for test execution

The service is intentionally compact and assignment-focused, with clear separation between API routes, business logic, database models, and schemas.

## Features

- Bulk certificate job creation for multiple recipients
- Input validation for event name, organization, event date, and recipient names/emails
- Asynchronous processing using FastAPI `BackgroundTasks`
- One PDF generated per certificate recipient
- Job-level progress tracking across total, success, and failure counts
- Per-certificate status tracking
- Secure PDF retrieval constrained to the generated output directory
- Failure isolation so one bad recipient does not stop the rest of the batch
- PostgreSQL-ready schema using native UUID handling in production
- SQLite-backed test isolation for reliable CI/local testing

## Tech stack

- Python 3.13
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Pydantic + Pydantic Settings
- ReportLab for PDF generation
- pytest for automated tests
- SQLite in-memory database for tests

## Project structure

```text
bulk-certificate-generator-api/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── init_db.py
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   ├── schemas.py
│   └── services.py
├── generated/
│   └── (generated PDF output files)
├── tests/
│   ├── conftest.py
│   ├── test_certificate_retrieval.py
│   ├── test_failure_isolation.py
│   ├── test_generation_and_status.py
│   ├── test_job_creation.py
│   ├── test_validation.py
├── .env
├── .gitignore
├── README.md
├── requirements.txt
└── .venv/
```

## Prerequisites

Before running this project, make sure the following are available:

- Python 3.11+
- PostgreSQL server installed and running
- A PostgreSQL user with permission to create databases and tables
- A working virtual environment
- pip to install Python dependencies

## Environment setup

Create a `.env` file at the project root.

This file contains environment variables used by the app at runtime. Keep it local to the project and do not commit secrets or real credentials.

Example:

```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/certificate_generator
```

Important notes:

- Replace `your_password` with your real local PostgreSQL password only on your machine.
- Do not commit `.env` to a public repository.
- Do not expose real passwords in documentation or examples.
- The database name used in this example is `certificate_generator`.

## PostgreSQL database setup

This project expects PostgreSQL to host the production database.

### Database name

The intended database name is:

```text
certificate_generator
```

### Create the database

Using PostgreSQL CLI:

```bash
createdb certificate_generator
```

Or with `psql`:

```bash
psql -U postgres -d postgres -c "CREATE DATABASE certificate_generator;"
```

### Initialize tables

From the project root, initialize the SQLAlchemy metadata:

```bash
python -m app.init_db
```

This creates the tables defined in the SQLAlchemy models for the production database.

> The project intentionally keeps PostgreSQL native UUID fields in production and does not replace PostgreSQL with SQLite for runtime use.

## Python virtual environment setup

Create a virtual environment in the project root:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Dependency installation

Install dependencies from the repository root:

```bash
pip install -r requirements.txt
```

If needed, upgrade pip first:

```bash
python -m pip install --upgrade pip
```

## How to start the FastAPI server

From the project root, run:

### macOS / Linux

```bash
uvicorn app.main:app --reload
```

### Windows

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API will usually be served at:

```text
http://127.0.0.1:8000
```

## Swagger documentation URL

Open the Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

You can also use the ReDoc UI at:

```text
http://127.0.0.1:8000/redoc
```

## How to run tests

Run the full test suite from the project root:

```bash
pytest -q
```

If using the project virtual environment:

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

This is the preferred validation command for the assignment.

## API endpoint documentation

### Health check

```http
GET /health
```

Returns a simple health response to confirm the service is running.

### Create certificate job

```http
POST /api/certificates/jobs
```

Creates a new bulk certificate job and returns a `202 Accepted` response immediately while processing continues in the background.

### Get job status

```http
GET /api/certificates/jobs/{job_id}
```

Returns the job metadata, counts, progress percentage, and the list of individual certificate records.

### Download a certificate

```http
GET /api/certificates/{certificate_id}
```

Returns the generated PDF for a successfully completed certificate.

## Example POST /api/certificates/jobs request

```json
{
  "event_name": "AI Leadership Summit",
  "organization": "Northwind Labs",
  "event_date": "2026-10-08",
  "recipients": [
    {"name": "Alice Johnson", "email": "alice@example.com"},
    {"name": "Bob Smith", "email": "bob@example.com"},
    {"name": "Carla Gomez", "email": "carla@example.com"}
  ]
}
```

## Example 202 response

```json
{
  "id": "5ea6b060-7459-4d6c-b160-8ea46715e0b4",
  "event_name": "AI Leadership Summit",
  "organization": "Northwind Labs",
  "event_date": "2026-10-08",
  "status": "pending",
  "total_count": 3,
  "success_count": 0,
  "failure_count": 0,
  "created_at": "2026-10-08T10:00:00Z",
  "completed_at": null
}
```

## Background processing

The API creates the job record and recipient certificate records immediately, then schedules processing through FastAPI `BackgroundTasks`.

This means the HTTP response returns quickly, while the actual PDF generation continues asynchronously in the background. The client can then poll the job status endpoint until the batch is finished.

This approach is useful for a short assignment or a small internal service, but it is not a durable queue system.

## Example GET job-status request

```http
GET /api/certificates/jobs/5ea6b060-7459-4d6c-b160-8ea46715e0b4
```

## Example completed job response

```json
{
  "id": "5ea6b060-7459-4d6c-b160-8ea46715e0b4",
  "event_name": "AI Leadership Summit",
  "organization": "Northwind Labs",
  "event_date": "2026-10-08",
  "status": "completed",
  "total_count": 3,
  "success_count": 3,
  "failure_count": 0,
  "progress": 100.0,
  "created_at": "2026-10-08T10:00:00Z",
  "completed_at": "2026-10-08T10:00:12Z",
  "certificates": [
    {
      "id": "0e1a8c7d-6b03-4e16-ba4f-70d9e6eaf5d1",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "completed",
      "file_path": "/absolute/path/to/generated/0e1a8c7d-6b03-4e16-ba4f-70d9e6eaf5d1.pdf",
      "error_message": null
    }
  ]
}
```

## How to retrieve an individual certificate

Once a certificate is complete, the client can call the certificate endpoint to download the generated PDF.

The route validates that the certificate is not still pending, not failed, and that the file path is still inside the configured generated directory. This keeps file downloads safe and constrained.

## Example certificate retrieval request

```http
GET /api/certificates/0e1a8c7d-6b03-4e16-ba4f-70d9e6eaf5d1
```

This returns the PDF file with a `Content-Type` of `application/pdf`.

## Failure isolation

Each recipient is processed independently within the job batch. A failure in one certificate does not abort subsequent certificates.

The logic works as follows:

- each recipient is processed in its own `try/except` block
- successful generation increments `success_count`
- failed generation increments `failure_count`
- the batch continues and attempts the remaining recipients
- the overall job final state is determined only after every recipient has been processed

This ensures a single failure does not stop the entire batch.

## Job status values

The job-level status values are:

- `pending` - the job was accepted but not yet processed
- `processing` - the batch is actively being generated
- `completed` - all recipients succeeded
- `completed_with_errors` - some recipients succeeded and some failed
- `failed` - all recipients failed

The certificate-level status values are:

- `pending`
- `processing`
- `completed`
- `failed`

## Progress calculation

The API calculates progress as:

```text
progress = ((success_count + failure_count) / total_count) * 100
```

This produces a percentage based on how many certificates have already been processed in the current job.

If `total_count` is zero, progress is reported as `0.0`.

## Database design / relationship explanation

The schema has two main tables:

### `generation_jobs`

Represents the overall job submitted by the client.

Fields include:

- `id` - UUID primary key
- `event_name`
- `organization`
- `event_date`
- `status`
- `total_count`
- `success_count`
- `failure_count`
- `created_at`
- `completed_at`

### `certificates`

Represents a single certificate for one recipient within a job.

Fields include:

- `id` - UUID primary key
- `job_id` - foreign key to `generation_jobs.id`
- `recipient_name`
- `recipient_email`
- `status`
- `file_path`
- `error_message`
- `created_at`

A job can have many certificates, and each certificate belongs to exactly one job.

The relationship is expressed as a one-to-many association and uses cascading deletes for integrity.

## Architecture/design decisions

This project intentionally keeps the codebase extremely readable and assignment-oriented:

- `app/routes.py` handles HTTP concerns and validation flow
- `app/services.py` performs the certificate generation logic and job finalization
- `app/models.py` defines the database schema and relationships
- `app/schemas.py` defines request and response validation models
- `app/database.py` centralizes database configuration and session management

This separation keeps the API simple while making responsibilities easy to explain in an interview and easy to extend in a real codebase.

## Why `BackgroundTasks` was selected for this assignment

`BackgroundTasks` was chosen because it meets the assignment requirements without introducing an additional queuing framework or external infrastructure.

Benefits for this project:

- fast job-acceptance response
- straightforward API design
- no external Redis/RabbitMQ dependency required
- easy to test with the current FastAPI test setup

Tradeoff:

- it is not a durable production queue
- it runs in-process and is not intended for a multi-instance, fault-tolerant platform deployment

## Production limitations / tradeoffs

This implementation is appropriate for the assignment and for small local or internal workloads, but it has important production limitations:

- `BackgroundTasks` is not a durable production queue.
- generated local PDF files are stored on disk and are not ideal for distributed or horizontally scaled production deployments.
- production systems would typically use durable job orchestration, object storage such as Azure Blob Storage, and migration tooling for schema management.
- there is no managed retry queue, dead-letter handling, or multi-worker orchestration in this assignment implementation.

The app is intentionally simple and fast to reason about, but it is not a full production-grade distributed certificate processing system.

## Testing strategy

The project uses pytest to validate real application behavior.

The test fixture configures an in-memory SQLite database and overrides the application dependency injection so that tests remain isolated from the real PostgreSQL database.

This allows the suite to verify:

- payload validation
- job creation
- generation processing
- progress calculation
- success and failure status transitions
- certificate file download behavior
- failure isolation
- safe path validation

## Security considerations

The API includes important safeguards:

- input validation for recipient names and emails
- safe database usage via SQLAlchemy models
- file retrieval restricted to the generated directory
- path traversal prevention using resolved path checks
- no hardcoded credentials in source code
- environment variables stored in `.env` rather than embedded in code

The generated directory is strictly validated before any file is returned, so a certificate whose `file_path` points outside the allowed directory is rejected.

## Interview / design notes

This project is a good example of a focused service built around clear responsibilities:

- API layer for request handling
- service layer for processing logic
- DB layer for persistence and relationships
- secure file route for retrieval
- isolated tests for behavioral confidence

If asked during an interview, a strong explanation would include:

- why asynchronous processing was necessary for batch work
- how a single failed recipient is isolated from the rest of the batch
- why the app validates file paths before returning PDF downloads
- why PostgreSQL remains the production database while tests use SQLite
- how progress is calculated and used to drive monitoring

## Summary

This project demonstrates a compact but complete bulk certificate generation workflow with:

- REST API submission
- asynchronous processing
- per-recipient generation
- status tracking
- safe file retrieval
- real behavior tests
- PostgreSQL-compatible production design

It is a practical backend implementation suitable for a technical assignment and a strong interview discussion topic.

