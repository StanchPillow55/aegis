"""Safety language guardrails — suppress unsupported prescriptive tone.

Ported from legacy-aegis/src/backend/safety/guardrails.py and adapted to
string metric names (no MetricType enum dependency).
"""

from __future__ import annotations

import re

REWRITES = [
    (r"(?i)\byou should\s+(\w[\w\s]*?)(?=[.,;!?]|$)", r"\1 may be worth considering"),
    (r"(?i)\byou need to\s+(\w[\w\s]*?)(?=[.,;!?]|$)", r"\1 may be worth considering"),
    (r"(?i)\btoo high\b", "above your recent baseline"),
    (r"(?i)\btoo low\b", "below your recent baseline"),
    (r"(?i)\bconcerning\b", "notable compared to your baseline"),
    (r"(?i)\bdangerous\b", "outside the typical range"),
]


def apply_guardrails(llm_response: str, active_goal_metrics: list[str] | None = None) -> str:
    """Rewrite prescriptive phrases unless the sentence names an active goal metric."""
    active_goal_metrics = active_goal_metrics or []
    sentences = re.split(r"(?<=[.!?])\s+", llm_response or "")
    result: list[str] = []
    for sentence in sentences:
        if not sentence:
            continue
        skip = False
        lower = sentence.lower()
        for metric in active_goal_metrics:
            metric_str = str(metric).replace("_", " ").lower()
            if metric_str in lower or str(metric).lower() in lower:
                skip = True
                break
        if skip:
            result.append(sentence)
        else:
            rewritten = sentence
            for pattern, replacement in REWRITES:
                rewritten = re.sub(pattern, replacement, rewritten)
            result.append(rewritten)
    return " ".join(result).strip()
