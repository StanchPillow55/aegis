from backend.providers.speech import LocalSpeechProvider, transcribe_audio


def test_speech_adapters_scaffold():
    provider = LocalSpeechProvider(stt_enabled=False, tts_enabled=False)
    stt = provider.stt_status()
    tts = provider.tts_status()
    assert stt.ok is False
    assert "disabled" in stt.detail.lower()
    assert tts.ok is False
    assert "disabled" in tts.detail.lower()
    # Missing file / disabled path returns empty transcript, does not raise.
    assert transcribe_audio("/tmp/does-not-exist.wav") == ""


def test_speech_enabled_without_deps_reports_cleanly():
    provider = LocalSpeechProvider(stt_enabled=True, tts_enabled=True, piper_model_path="")
    stt = provider.stt_status()
    tts = provider.tts_status()
    # Without faster-whisper / pyttsx3 / piper model, readiness is false but structured.
    assert isinstance(stt.ok, bool)
    assert isinstance(tts.ok, bool)
    assert stt.detail
    assert tts.detail
