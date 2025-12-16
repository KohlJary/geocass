"""
GeoCass Server Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App settings
    app_name: str = "GeoCass"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # Database path (relative or absolute)
    data_dir: str = "./data"

    # Security
    secret_key: str = "change-me-in-production"
    api_key_prefix: str = "gc_"

    # Limits
    max_homepage_size_kb: int = 1024  # 1MB max HTML
    max_sync_per_minute: int = 5
    max_sync_per_day: int = 100

    # Public URL
    public_url: str = "https://geocass.hearthweave.org"

    class Config:
        env_file = ".env"
        env_prefix = "GEOCASS_"
        extra = "ignore"  # Ignore unknown env vars for backwards compatibility

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway sets PORT without prefix - check for it
        if "PORT" in os.environ:
            self.port = int(os.environ["PORT"])


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Paths
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "app" / "templates"


def get_data_dir() -> Path:
    """Get the data directory path, creating it if needed."""
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    if not data_dir.is_absolute():
        data_dir = BASE_DIR / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# For backwards compatibility
DATA_DIR = get_data_dir()
