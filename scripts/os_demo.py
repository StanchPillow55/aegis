#!/usr/bin/env python3
"""Local demo loop for OS foundation mode.

Runs a single text update through intake -> memory -> directive.
If Ollama is missing, reports that cleanly and continues on heuristic fallback.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from backend.config import get_settings
    from backend.local_llm import OllamaClient, extract_intake
    from backend.providers.memory import LocalMemoryProvider
    from backend.providers.tracing import init_tracing, start_span
    from backend.reasoner import compose_directive

    settings = get_settings()
    init_tracing()
    client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_s=settings.ollama_timeout_s,
    )

    if client.available():
        print(f"[os-demo] Ollama available at {settings.ollama_base_url} model={settings.ollama_model}")
    else:
        print(
            "[os-demo] Ollama not running — using heuristic fallback. "
            f"To enable local LLM: install Ollama, `ollama pull {settings.ollama_model}`, "
            "then re-run `make os-demo`."
        )

    sample = (
        "Slept about 6 hours, sleep was rough. Quads sore 3/5. "
        "Had eggs and rice. Squats and rowing today. Feeling tired."
    )

    with start_span("os-demo.run"):
        intake = extract_intake(sample, client=client)
        mem = LocalMemoryProvider(settings.resolved_memory_db())
        log_id = mem.store(intake)
        hits = mem.search("fatigue quads squat", k=3)
        composed = compose_directive(
            intake,
            context_notes=[h.content for h in hits if h.log_id != log_id],
        )

    print("[os-demo] log_id:", log_id)
    print("[os-demo] overall:", composed["evidence"].get("overall"))
    print("[os-demo] wod:", composed.get("wod_decision", {}).get("status"))
    print("[os-demo] directive:", composed["directive"])
    print("[os-demo] intake:", json.dumps(intake.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
