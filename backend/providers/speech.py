from typing import Any, Dict, Optional

class SpeechProvider:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def text_to_speech(self, text: str, **kwargs: Any) -> bytes:
        return b""

    def speech_to_text(self, audio_data: bytes, **kwargs: Any) -> str:
        return ""
