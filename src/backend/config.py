"""Application settings loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama (local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = "llava"

    # Claude (optional cloud fallback)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"

    # Storage
    sqlite_db_path: str = "./data/aegis.db"
    chroma_persist_dir: str = "./data/chroma"

    # Fitbit (optional)
    fitbit_client_id: str | None = None
    fitbit_client_secret: str | None = None

    # Google
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
