from app.database import init_db
import app.models  # noqa: F401


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully: generation_jobs and certificates tables created.")