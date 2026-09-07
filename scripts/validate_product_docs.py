#!/usr/bin/env python3
"""Lightweight consistency checks for canonical Aegis product docs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/PRODUCT_SPEC.md",
    "AGENT_HANDOFF.md",
    "README.md",
    "CLAUDE.md",
    "success_criteria.yaml",
]

REQUIRED_PHRASES = {
    "docs/PRODUCT_SPEC.md": [
        "daily training-decision copilot for functional longevity",
        "Front-rack",
        "Workout preparation",
        "local-first",
        "Fitbit",
        "FITINDEX",
        "Tailscale",
        "today wins",
    ],
    "AGENT_HANDOFF.md": [
        "PRODUCT_SPEC.md",
        "Known limitations",
        "Next implementation order",
        "Slice 0",
    ],
    "README.md": [
        "PRODUCT_SPEC.md",
        "success_criteria.yaml",
        "local-first",
    ],
    "CLAUDE.md": [
        "Front-rack",
        "success_criteria.yaml",
        "PRODUCT_SPEC.md",
    ],
}


def main() -> int:
    failed = False
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.is_file():
            print(f"ERROR: missing {rel}")
            failed = True
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in REQUIRED_PHRASES.get(rel, []):
            if phrase not in text:
                print(f"ERROR: {rel} missing required phrase: {phrase!r}")
                failed = True

    # MVP_SPEC must point at PRODUCT_SPEC to avoid duplicate canon
    mvp = ROOT / "docs" / "MVP_SPEC.md"
    if mvp.is_file():
        body = mvp.read_text(encoding="utf-8")
        if "PRODUCT_SPEC.md" not in body:
            print("ERROR: docs/MVP_SPEC.md must point to PRODUCT_SPEC.md")
            failed = True

    sc = (ROOT / "success_criteria.yaml").read_text(encoding="utf-8")
    for needle in ("MVP-SCORE-01", "PHC-FITBIT-01", "PHC-TOOLS-01", "PHC-GOALS-01"):
        if needle not in sc:
            print(f"ERROR: success_criteria.yaml missing {needle}")
            failed = True

    if failed:
        return 1
    print("Product docs consistency OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
