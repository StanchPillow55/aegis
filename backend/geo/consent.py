"""Local geolocation consent preference (never sent to cloud LLM)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class GeoConsentStore:
    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            from backend.config import get_settings

            path = Path(get_settings().data_dir) / "geo_consent.json"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, Any]:
        data = self._read()
        return {
            "enabled": bool(data.get("enabled", False)),
            "default": "off",
            "revocable": True,
            "cloud_llm": False,
            "coords_stored": False,
            "updated_at": data.get("updated_at"),
            "detail": (
                "Geolocation is opt-in and disabled by default. "
                "Coordinates are not persisted server-side and are never sent to a cloud LLM."
            ),
        }

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        payload = {
            "enabled": bool(enabled),
            "updated_at": time.time(),
            # Explicitly do not store lat/lon
        }
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        return self.status()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"enabled": False}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"enabled": False}
