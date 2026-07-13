"""Tests for the local LLM path using only fallback/mock logic."""

import pytest
from backend.local_llm import OllamaClient, fallback_extractor


def test_ollama_client_generate_not_implemented():
    """Test that the Ollama client skeleton raises NotImplementedError."""
    client = OllamaClient()
    with pytest.raises(NotImplementedError):
        client.generate("Hello, world!")


def test_fallback_extractor_valid_json():
    """Test the deterministic extractor with valid JSON."""
    text = '{"name": "test", "value": 123}'
    result = fallback_extractor(text)
    assert result == {"name": "test", "value": 123}


def test_fallback_extractor_invalid_text():
    """Test the deterministic extractor fallback logic on plain text."""
    text = "This is not JSON text. It is just a plain string."
    result = fallback_extractor(text)
    assert result["status"] == "fallback"
    assert result["extracted"] is False
    assert "This is not JSON" in result["original_text"]
