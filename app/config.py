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

    # Database
    database_url: str = "sqlite:///./data/geocass.db"

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


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)
