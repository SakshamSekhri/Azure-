from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.core.database import engine, Base
from backend.app.models import *  # Ensure all models are registered
from backend.app.api.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: setup logging & create tables if needed
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    logger.info(f"[DATABASE] Connected to SQLite database at: {settings.DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    # Ensure new columns exist on existing SQLite databases
    try:
        from sqlalchemy import inspect as sqla_inspect, text
        inspector = sqla_inspect(engine)
        table_names = inspector.get_table_names()
        with engine.connect() as conn:
            if "assessments" in table_names:
                cols = {c["name"] for c in inspector.get_columns("assessments")}
                if "assessment_mode" not in cols:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN assessment_mode VARCHAR(50) DEFAULT 'full_assessment'"))
                if "topic" not in cols:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN topic VARCHAR(100)"))
                if "canonical_skill_id" not in cols:
                    conn.execute(text("ALTER TABLE assessments ADD COLUMN canonical_skill_id VARCHAR(100)"))
            if "assessment_attempts" in table_names:
                cols_att = {c["name"] for c in inspector.get_columns("assessment_attempts")}
                if "analysis_status" not in cols_att:
                    conn.execute(text("ALTER TABLE assessment_attempts ADD COLUMN analysis_status VARCHAR(50) DEFAULT 'pending'"))
            if "assessment_answers" in table_names:
                cols_ans = {c["name"] for c in inspector.get_columns("assessment_answers")}
                if "attempt_id" not in cols_ans:
                    conn.execute(text("ALTER TABLE assessment_answers ADD COLUMN attempt_id INTEGER"))
            if "student_profiles" in table_names and "users" in table_names:
                conn.execute(text("""
                    INSERT INTO student_profiles (user_id, name, target_role, experience_level, created_at, updated_at)
                    SELECT u.id, SUBSTR(u.email, 1, INSTR(u.email, '@') - 1), '', 'Entry Level', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM users u
                    LEFT JOIN student_profiles p ON u.id = p.user_id
                    WHERE p.id IS NULL
                """))
            conn.commit()
    except Exception as e:
        logger.warning(f"SQLite migration check warning: {e}")
    logger.info("Database tables verified/created.")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Credit-conscious, deterministic placement preparation platform with Azure AI Foundry & Azure AI Search.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS configuration for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.app.api.routes.assessment_start import router as assessment_start_router

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(assessment_start_router, prefix="/api/assessment", tags=["Assessment Agent"])


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/")
def root():
    return {
        "message": "Welcome to Placement Preparation Agent API",
        "docs_url": "/docs",
        "health_url": "/health"
    }
