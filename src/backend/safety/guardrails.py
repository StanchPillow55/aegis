import re
from typing import List
from src.backend.models.health_metrics import MetricType

REWRITES = [
    (r"(?i)\byou should\s+(\w[\w\s]*?)(?=[.,;!?]|$)", r"\1 may be worth considering"),
    (r"(?i)\byou need to\s+(\w[\w\s]*?)(?=[.,;!?]|$)", r"\1 may be worth considering"),
    (r"(?i)\btoo high\b", "above your recent baseline"),
    (r"(?i)\btoo low\b", "below your recent baseline"),
    (r"(?i)\bconcerning\b", "notable compared to your baseline"),
    (r"(?i)\bdangerous\b", "outside the typical range"),
]

def apply_guardrails(llm_response: str, active_goal_metrics: List[MetricType] = None) -> str:
    """
    Scans LLM output for prescriptive language patterns.
    If no goal is set for a specific context, strip normative framing.
    """
    if active_goal_metrics is None:
        active_goal_metrics = []
        
    sentences = re.split(r'(?<=[.!?])\s+', llm_response)
    
    result = []
    for sentence in sentences:
        if not sentence:
            continue
            
        skip = False
        for metric in active_goal_metrics:
            # Replace underscores with spaces for metric value to match English text, e.g. "heart rate"
            metric_str = metric.value.replace("_", " ").lower()
            if metric_str in sentence.lower() or metric.value.lower() in sentence.lower():
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
