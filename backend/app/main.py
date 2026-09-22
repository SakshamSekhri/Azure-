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
