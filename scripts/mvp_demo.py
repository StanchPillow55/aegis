#!/usr/bin/env python3
"""MVP demo — offline heuristic path with canonical scores + WOD negotiation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from backend.local_llm import OllamaClient, extract_intake_with_meta
    from backend.providers.memory import LocalMemoryProvider
    from backend.health.evidence import build_evidence_bundle
    from backend.reasoner import compose_directive
    from backend.config import get_settings

    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url, timeout_s=0.5)
    sample = (
        "Slept 5 hours poorly. Shoulders and wrists sore 4/5. "
        "Ate toast only. Today's WOD is cleans and thrusters. Feeling exhausted."
    )
    intake, extractor = extract_intake_with_meta(sample, client=client)
    mem = LocalMemoryProvider(settings.resolved_memory_db())
    log_id = mem.store(intake, extractor=extractor)
    hits = mem.search("shoulders cleans", k=3, exclude_ids={log_id}, dedupe=True)
    bundle = build_evidence_bundle(
        intake=intake,
        log_id=log_id,
        history=[h.to_history_hit() for h in hits],
        extractor=extractor,
    )
    composed = compose_directive(intake, evidence_bundle=bundle)
    print("[mvp-demo] extractor:", extractor)
    print("[mvp-demo] scores:", {k: composed["scores"][k]["score"] for k in ("front_rack","sleep","diet","workout_preparation","overall")})
    print("[mvp-demo] wod:", composed["wod_decision"]["status"])
    print("[mvp-demo] directive:", composed["directive"])
    print("[mvp-demo] disclaimer_ok:", "diagnose" in composed["disclaimer"].lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
