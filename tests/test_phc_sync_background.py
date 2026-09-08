"""S1 / PHC-SYNC-01 — background sync loop, retries, chat/voice triggers."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.chat import ChatService, ChatTurnRequest, is_sync_trigger
from backend.main import app
from backend.sync import BackgroundSyncLoop, SourceId, SourceRegistry, SyncConfig, SyncResult
from backend.sync.registry import SyncError
from backend.tools import HealthQueryTools


client = TestClient(app)


def test_is_sync_trigger_phrases():
    assert is_sync_trigger("sync now")
    assert is_sync_trigger("please run a sync")
    assert is_sync_trigger("refresh sources")
    assert not is_sync_trigger("what is my sync status")
    assert not is_sync_trigger("are sources stale")


def test_sync_one_with_retries_skips_disabled(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "r1.sqlite3")
    reg.set_enabled(SourceId.FIXTURE, False)
    result = reg.sync_one_with_retries(SourceId.FIXTURE, max_retries=3, backoff_seconds=0)
    assert result.success is False
    assert result.error and result.error.code == "disabled"


def test_sync_one_with_retries_backoff_on_transient(tmp_path: Path, monkeypatch):
    reg = SourceRegistry(tmp_path / "r2.sqlite3")
    sleeps: list[float] = []

    attempts = {"n": 0}

    def flaky(registry, source_id):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return SyncResult(
                source_id=source_id,
                success=False,
                detail="transient",
                error=SyncError(code="sync_failed", message="boom", at=time.time()),
            )
        return SyncResult(source_id=source_id, success=True, record_count=1, detail="ok")

    reg.register_handler(SourceId.FIXTURE, flaky)
    result = reg.sync_one_with_retries(
        SourceId.FIXTURE,
        max_retries=3,
        backoff_seconds=0.01,
        sleep_fn=lambda s: sleeps.append(s),
    )
    assert result.success is True
    assert attempts["n"] == 3
    assert sleeps == [0.01, 0.02]


def test_background_tick_respects_enabled_and_skips_disabled(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "bg.sqlite3")
    reg.set_config(
        SyncConfig(
            background_enabled=True,
            interval_seconds=5,
            sources={"fixture": True},
            max_retries=1,
            retry_backoff_seconds=0,
        )
    )
    # Disable fixture — should be skipped even though supports_background
    reg.set_enabled(SourceId.FIXTURE, False)
    loop = BackgroundSyncLoop(reg)
    results = loop.tick()
    assert results == []

    reg.set_enabled(SourceId.FIXTURE, True)
    results = loop.tick()
    assert any(r.source_id == SourceId.FIXTURE and r.success for r in results)
    assert loop.ticks == 2
    assert loop.last_tick_at is not None


def test_background_tick_noop_when_disabled(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "bg2.sqlite3")
    reg.set_config(SyncConfig(background_enabled=False, interval_seconds=5))
    loop = BackgroundSyncLoop(reg)
    assert loop.tick() == []
    # force still runs
    forced = loop.tick(force=True)
    assert any(r.success for r in forced)


def test_background_loop_start_stop_no_boot_hang(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "bg3.sqlite3")
    reg.set_config(SyncConfig(background_enabled=True, interval_seconds=3600))
    loop = BackgroundSyncLoop(reg)
    t0 = time.time()
    loop.start()
    assert time.time() - t0 < 1.0  # must not block
    assert loop.status()["running"] is True
    loop.stop(timeout=1.0)
    assert loop.status()["running"] is False


def test_api_background_tick_and_config(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._sync = SourceRegistry(tmp_path / "api_bg.sqlite3")
    main_mod._background = BackgroundSyncLoop(main_mod._sync)

    put = client.put(
        "/api/sync/config",
        json={
            "background_enabled": True,
            "interval_seconds": 30,
            "sources": {"fixture": True},
            "max_retries": 2,
            "retry_backoff_seconds": 0.01,
        },
    )
    assert put.status_code == 200
    assert put.json()["background_enabled"] is True

    tick = client.post("/api/sync/background/tick?force=true")
    assert tick.status_code == 200
    body = tick.json()
    assert body["results"]
    assert body["status"]["ticks"] >= 1

    status = client.get("/api/sync/background")
    assert status.status_code == 200
    assert "background_enabled" in status.json()

    health = client.get("/health")
    assert health.status_code == 200
    assert "background_sync" in health.json()


def test_chat_sync_now_triggers_sync(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "chat_sync.sqlite3")
    tools = HealthQueryTools(sync=reg)
    chat = ChatService(tools=tools)
    resp = chat.turn(ChatTurnRequest(message="sync now"))
    tools_used = [t["tool"] for t in resp.tool_results]
    assert "trigger_sync" in tools_used
    assert "source_freshness" in tools_used
    assert "On-demand sync via chat" in resp.reply


def test_voice_channel_sync_via_chat(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "voice_sync.sqlite3")
    tools = HealthQueryTools(sync=reg)
    chat = ChatService(tools=tools)
    resp = chat.turn(
        ChatTurnRequest(
            message="please run a sync",
            screen_context={"input": "voice", "panel": "today"},
        )
    )
    sync_tool = next(t for t in resp.tool_results if t["tool"] == "trigger_sync")
    assert sync_tool["result"]["channel"] == "voice"


def test_per_source_config_sources_false_skips(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "skip.sqlite3")
    reg.set_config(
        SyncConfig(
            background_enabled=True,
            interval_seconds=10,
            sources={"fixture": False},
            max_retries=1,
        )
    )
    loop = BackgroundSyncLoop(reg)
    assert SourceId.FIXTURE not in loop.eligible_sources()
    assert loop.tick() == []
