from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "data/neeka.db")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    environment: str = os.getenv("ENVIRONMENT", "development")
    cors_origins: tuple[str, ...] = tuple(
        item.strip() for item in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
        ).split(",") if item.strip()
    )
    artifact_max_size: int = int(os.getenv("ARTIFACT_MAX_SIZE", str(50 * 1024 * 1024)))