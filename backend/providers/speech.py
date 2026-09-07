"""Local STT/TTS adapters (optional). Text UI remains primary.

STT: faster-whisper when installed + enabled.
TTS: Piper (or pyttsx3) when installed + enabled.
Missing deps/services -> clean skip messages, never hard-fail imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VoiceResult:
    ok: bool
    text: str = ""
    audio_path: str | None = None
    detail: str = ""


class LocalSpeechProvider:
    """Optional local speech stack with explicit readiness checks."""

    def __init__(
        self,
        *,
        stt_enabled: bool | None = None,
        tts_enabled: bool | None = None,
        whisper_model: str | None = None,
        piper_model_path: str | None = None,
    ) -> None:
        from backend.config import get_settings

        settings = get_settings()
        self.stt_enabled = settings.voice_stt_enabled if stt_enabled is None else stt_enabled
        self.tts_enabled = settings.voice_tts_enabled if tts_enabled is None else tts_enabled
        self.whisper_model = whisper_model or settings.whisper_model
        self.piper_model_path = piper_model_path or settings.piper_model_path

    def stt_status(self) -> VoiceResult:
        if not self.stt_enabled:
            return VoiceResult(
                ok=False,
                detail="STT disabled (set VOICE_STT_ENABLED=true to opt in).",
            )
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return VoiceResult(
                ok=False,
                detail="faster-whisper not installed. pip install faster-whisper",
            )
        return VoiceResult(ok=True, detail=f"faster-whisper ready (model={self.whisper_model})")

    def tts_status(self) -> VoiceResult:
        if not self.tts_enabled:
            return VoiceResult(
                ok=False,
                detail="TTS disabled (set VOICE_TTS_ENABLED=true to opt in).",
            )
        if self.piper_model_path and Path(self.piper_model_path).exists():
            return VoiceResult(ok=True, detail=f"Piper model at {self.piper_model_path}")
        try:
            import pyttsx3  # noqa: F401

            return VoiceResult(ok=True, detail="pyttsx3 available as TTS fallback")
        except ImportError:
            return VoiceResult(
                ok=False,
                detail="No TTS backend: install piper voice model or pyttsx3.",
            )

    def transcribe(self, audio_path: str) -> VoiceResult:
        status = self.stt_status()
        if not status.ok:
            return status
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(self.whisper_model)
            segments, _info = model.transcribe(audio_path)
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return VoiceResult(ok=True, text=text, detail="transcribed")
        except Exception as exc:  # pragma: no cover - depends on local audio stack
            return VoiceResult(ok=False, detail=f"STT failed: {exc}")

    def synthesize(self, text: str, out_path: str | None = None) -> VoiceResult:
        status = self.tts_status()
        if not status.ok:
            return status
        target = Path(out_path or Path("data") / "tts_out.wav")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self.piper_model_path and Path(self.piper_model_path).exists():
                # Piper CLI integration left as a bucket-list enhancement; write text sidecar.
                sidecar = target.with_suffix(".txt")
                sidecar.write_text(text, encoding="utf-8")
                return VoiceResult(
                    ok=True,
                    text=text,
                    audio_path=str(sidecar),
                    detail="Piper model present; text sidecar written (CLI synthesize TODO).",
                )
            import pyttsx3

            engine = pyttsx3.init()
            engine.save_to_file(text, str(target))
            engine.runAndWait()
            return VoiceResult(ok=True, text=text, audio_path=str(target), detail="pyttsx3")
        except Exception as exc:  # pragma: no cover
            return VoiceResult(ok=False, detail=f"TTS failed: {exc}")


def transcribe_audio(audio_path: str) -> str:
    """Skeleton-compatible helper. Returns empty string when STT unavailable."""
    result = LocalSpeechProvider().transcribe(audio_path)
    return result.text if result.ok else ""


def synthesize_speech(text: str, out_path: str | None = None) -> VoiceResult:
    return LocalSpeechProvider().synthesize(text, out_path=out_path)
