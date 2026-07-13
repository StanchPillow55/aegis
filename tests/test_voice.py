import pytest
import os
from backend.providers.speech import transcribe_audio, synthesize_speech

def test_speech_mock(monkeypatch):
    monkeypatch.setenv("USE_MOCK_SPEECH", "true")
    
    text = transcribe_audio("dummy.wav")
    assert "good" in text
    
    success = synthesize_speech("Hello", "out.wav")
    assert success is True
    
    # Cleanup
    if os.path.exists("out.wav"):
        os.remove("out.wav")
