"""Required background sync loop (S1 / PHC-SYNC-01).

Fail-soft daemon thread: never blocks FastAPI boot. When
``SyncConfig.background_enabled`` is true, ticks on ``interval_seconds``,
syncing enabled sources that support background with retry/backoff.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from backend.sync.registry import SourceId, SourceRegistry, SyncResult

logger = logging.getLogger("aegis.sync.background")


class BackgroundSyncLoop:
    """Interval-driven sync scheduler backed by ``SourceRegistry``."""

    def __init__(
        self,
        registry: SourceRegistry,
        *,
        time_fn: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.registry = registry
        self._time = time_fn or time.time
        self._sleep = sleep_fn or time.sleep
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self.running = False
        self.ticks = 0
        self.last_tick_at: float | None = None
        self.last_tick_results: list[dict[str, Any]] = []
        self.last_error: str | None = None
        self.started_at: float | None = None

    def start(self) -> None:
        """Start the daemon loop. Idempotent; never raises to callers."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._wake.clear()
            self.started_at = self._time()
            self.running = True
            self._thread = threading.Thread(
                target=self._run,
                name="aegis-background-sync",
                daemon=True,
            )
            try:
                self._thread.start()
            except Exception as exc:  # pragma: no cover — fail soft
                self.running = False
                self.last_error = str(exc)
                logger.warning("background sync failed to start: %s", exc)

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the loop to stop and join briefly."""
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        with self._lock:
            self.running = False
            self._thread = None

    def wake(self) -> None:
        """Interrupt the current sleep (e.g. after config change)."""
        self._wake.set()

    def status(self) -> dict[str, Any]:
        cfg = self.registry.get_config()
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "background_enabled": cfg.background_enabled,
            "interval_seconds": cfg.interval_seconds,
            "max_retries": cfg.max_retries,
            "retry_backoff_seconds": cfg.retry_backoff_seconds,
            "ticks": self.ticks,
            "last_tick_at": self.last_tick_at,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "last_tick_results": list(self.last_tick_results),
        }

    def eligible_sources(self) -> list[SourceId]:
        """Sources that should run on a background tick."""
        cfg = self.registry.get_config()
        out: list[SourceId] = []
        for status in self.registry.list_sources():
            if not status.supports_background:
                continue
            if not status.enabled:
                continue
            sid = status.source_id.value
            if cfg.sources and sid in cfg.sources and not cfg.sources[sid]:
                continue
            out.append(status.source_id)
        return out

    def tick(self, *, force: bool = False) -> list[SyncResult]:
        """Run one background cycle (also used by unit tests)."""
        cfg = self.registry.get_config()
        if not force and not cfg.background_enabled:
            return []

        results: list[SyncResult] = []
        try:
            for source_id in self.eligible_sources():
                results.append(
                    self.registry.sync_one_with_retries(
                        source_id,
                        max_retries=cfg.max_retries,
                        backoff_seconds=cfg.retry_backoff_seconds,
                    )
                )
            self.last_error = None
        except Exception as exc:  # fail soft — never kill the loop
            self.last_error = str(exc)
            logger.warning("background sync tick failed: %s", exc)

        self.ticks += 1
        self.last_tick_at = self._time()
        self.last_tick_results = [
            {
                "source_id": r.source_id.value,
                "success": r.success,
                "detail": r.detail,
                "error": r.error.model_dump() if r.error else None,
                "record_count": r.record_count,
            }
            for r in results
        ]
        return results

    def _run(self) -> None:
        # Initial delay: do not sync during boot; wait one interval (capped).
        while not self._stop.is_set():
            cfg = self.registry.get_config()
            interval = max(1, int(cfg.interval_seconds or 3600))
            # Wait interval, but wake early on config change / stop.
            self._wake.clear()
            self._wake.wait(timeout=interval)
            if self._stop.is_set():
                break
            if not self.registry.get_config().background_enabled:
                continue
            self.tick()

        self.running = False
