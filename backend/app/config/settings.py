import os
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application Settings
    PROJECT_NAME: str = "Placement Preparation Agent"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = Field(
        default="placement-prep-agent-development-secret-key-32-bytes",
        description="JWT encryption secret key"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        insecure_defaults = [
            "placement-prep-agent-development-secret-key-32-bytes",
            "replace-with-a-very-secure-random-secret-key",
            "secret",
            "changeme"
        ]
        if env == "production":
            if not v or v in insecure_defaults or len(v) < 32:
                raise ValueError("In production, SECRET_KEY must be explicitly set to a cryptographically secure key of at least 32 characters.")
        elif not v:
            import secrets
            return secrets.token_urlsafe(32)
        return v

    # Database - Resolved to absolute path to prevent multi-database working directory bugs
    DATABASE_URL: str = Field(
        default=f"sqlite:///{(Path(__file__).resolve().parent.parent.parent.parent / 'placement_prep.db').resolve().as_posix()}",
        description="Database URL"
    )

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        if v.startswith("sqlite:///") and not v.startswith("sqlite:///:memory:"):
            raw_path = v[len("sqlite:///"):]
            path_obj = Path(raw_path)
            if not path_obj.is_absolute():
                base_dir = Path(__file__).resolve().parent.parent.parent.parent
                resolved = (base_dir / path_obj).resolve().as_posix()
                return f"sqlite:///{resolved}"
        return v

    # Microsoft Foundry Agent Configuration
    FOUNDRY_PROJECT_ENDPOINT: str = Field(default="", description="Azure AI Foundry Project Endpoint or Connection String")
    FOUNDRY_AGENT_NAME: str = Field(default="PlacementPreparationAgent", description="Foundry Agent Name")
    FOUNDRY_AGENT_VERSION: str = Field(default="4", description="Foundry Agent Version")
    FOUNDRY_MODEL_DEPLOYMENT: str = Field(default="gpt-5-mini", description="Foundry Model Deployment Name")

    # Azure AI Search (RAG)
    AZURE_AI_SEARCH_ENDPOINT: str = Field(default="", description="Azure AI Search Endpoint")
    AZURE_AI_SEARCH_KEY: str = Field(default="", description="Azure AI Search API Key")
    AZURE_AI_SEARCH_INDEX: str = Field(default="placement-prep-knowledge", description="Azure Search Index Name")

    # GitHub API
    GITHUB_TOKEN: str = Field(default="", description="GitHub Personal Access Token for higher rate limits")
    MAX_GITHUB_REPOS: int = 10
    MAX_README_CHARS: int = 2000

    # Credit Control & AI Gateway Policy
    AI_CACHE_ENABLED: bool = True
    AI_REQUEST_TIMEOUT_SECONDS: int = 120

    # Uploads
    UPLOAD_DIR: Path = Path("./uploads")


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
