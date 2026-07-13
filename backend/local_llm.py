"""Local LLM path using Ollama.

This module provides a local, self-hosted LLM path that does not rely on any
paid API (such as Anthropic). It is designed to work well on standard
developer hardware.

Default Local Model (M2 / 16 GB):
    We recommend using `llama3` (or `mistral:instruct`) as the default local model
    for an M2 with 16 GB of unified memory. These 7B-8B parameter models fit well
    into RAM while leaving headroom for the OS and IDE.

Stretch Alternatives:
    If you have an M2 Max/Ultra with 32 GB+ of memory, you can experiment with
    larger models like `mixtral` (8x7B MoE) or `llama3:70b-instruct-q4_0` for
    better reasoning and extraction quality, although generation will be slower.
"""

import json
from typing import Any, Dict


class OllamaClient:
    """Skeleton for an Ollama client to run local models."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize the client."""
        self.base_url = base_url

    def generate(self, prompt: str, model: str = "llama3") -> str:
        """Generate text from a prompt using the specified local model.
        
        Args:
            prompt: The input prompt.
            model: The Ollama model tag to use.
            
        Returns:
            The generated string response.
        """
        # TODO: Implement actual HTTP call to Ollama generate endpoint
        raise NotImplementedError("Ollama generation not yet implemented")


def fallback_extractor(text: str) -> Dict[str, Any]:
    """Deterministic extractor fallback logic.

    Used when the local LLM fails to return properly formatted JSON or
    when bypassing the LLM entirely for testing purposes.

    Args:
        text: The raw text that should contain extracted fields.

    Returns:
        A dictionary with default or extracted fallback fields.
    """
    # Simple deterministic fallback: try to parse as JSON, else return a default structure.
    try:
        # Check if text is raw JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback dictionary structure
        return {
            "status": "fallback",
            "original_text": text.strip()[:100],  # keep a snippet
            "extracted": False,
        }
