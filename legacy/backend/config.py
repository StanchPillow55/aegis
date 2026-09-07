"""Application settings.

Loads configuration from the environment / `.env` file via pydantic-settings.
Required secret keys have no defaults, so a missing or empty value fails loud at
load time (`ValidationError`) rather than surfacing as a confusing runtime error
on the first external call.

Settings are loaded lazily through `get_settings()` so that importing the app
(e.g. for the `/health` liveness probe or unit tests) does not require a fully
populated `.env`.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration.

    Field names map case-insensitively to environment variables, so
    `anthropic_api_key` is populated from `ANTHROPIC_API_KEY`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Required secrets: missing/empty -> fail loud at load time ---
    anthropic_api_key: str = Field(..., min_length=1)
    gemini_api_key: str = Field(..., min_length=1)
    redis_url: str = Field(..., min_length=1)
    sentry_dsn: str = Field(..., min_length=1)
    deepgram_api_key: str = Field(..., min_length=1)
    browserbase_api_key: str = Field(..., min_length=1)

    # --- Model selection (optional; has a sane default) ---
    # Extraction runs at temperature=0, so the model MUST accept sampling
    # params. claude-opus-4-8 / 4.7 / fable-5 reject `temperature` with a 400,
    # so the default is a Sonnet-tier model (also the project's cost-discipline
    # tier). Override with ANTHROPIC_MODEL.
    anthropic_model: str = "claude-sonnet-4-5"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, validating required keys on first access."""
    return Settings()
