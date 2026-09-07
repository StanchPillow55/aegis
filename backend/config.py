"""Application settings — local-first / open-source mode.

Cloud provider keys are optional leftovers from the hackathon track. The
runtime defaults to Ollama + SQLite + OpenTelemetry and never requires paid APIs.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    """Typed application configuration (env / `.env`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime mode ---
    aegis_mode: str = "open-source-foundation"
    data_dir: Path = Field(default=DEFAULT_DATA_DIR)

    # --- Local LLM (Ollama) ---
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_s: float = 8.0

    # --- Local memory ---
    memory_db_path: Path | None = None  # default: {data_dir}/aegis_memory.sqlite3

    # --- Voice (optional; text UI is primary) ---
    voice_stt_enabled: bool = False
    voice_tts_enabled: bool = False
    whisper_model: str = "base"
    piper_model_path: str = ""

    # --- Observability (local OpenTelemetry; no Sentry required) ---
    otel_service_name: str = "aegis"
    otel_exporter: str = "console"  # console | none
    otel_endpoint: str = ""

    # --- Optional legacy cloud keys (unused in local-only mode) ---
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    redis_url: str = ""
    sentry_dsn: str = ""
    deepgram_api_key: str = ""
    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    def resolved_memory_db(self) -> Path:
        if self.memory_db_path is not None:
            return Path(self.memory_db_path)
        return Path(self.data_dir) / "aegis_memory.sqlite3"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings. Safe to call without a populated `.env`."""
    settings = Settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    return settings
