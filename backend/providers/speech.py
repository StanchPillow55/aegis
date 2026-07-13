import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Use environment variables to determine if we should load the large models
FASTER_WHISPER_MODEL = os.getenv("FASTER_WHISPER_MODEL", "tiny.en")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "en_US-lessac-medium.onnx")

def _is_mock():
    return os.getenv("USE_MOCK_SPEECH", "false").lower() == "true"

try:
    from faster_whisper import WhisperModel
    _whisper_model = None
except ImportError:
    # If not installed, force mock mode in the getter
    _whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None and not _is_mock():
        logger.info(f"Loading faster-whisper model: {FASTER_WHISPER_MODEL}")
        _whisper_model = WhisperModel(FASTER_WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper_model


def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file to text using faster-whisper."""
    if _is_mock():
        logger.info(f"Mock transcribing audio from {audio_path}")
        return "I slept pretty good, about 8 hours. My lower back is a little sore. I ate chicken and rice."

    try:
        model = _get_whisper_model()
        segments, info = model.transcribe(audio_path, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        return text.strip()
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return ""


def synthesize_speech(text: str, output_path: str) -> bool:
    """Synthesize text to speech using piper."""
    if _is_mock():
        logger.info(f"Mock synthesizing speech for: '{text}' to {output_path}")
        # Create a dummy file
        with open(output_path, "wb") as f:
            f.write(b"mock audio data")
        return True

    if not os.path.exists(PIPER_MODEL_PATH):
        logger.error(f"Piper model not found at {PIPER_MODEL_PATH}. Download it to synthesize speech.")
        return False

    try:
        # Assuming piper is installed as a binary accessible in PATH
        # echo 'text' | piper --model en_US-lessac-medium.onnx --output_file output.wav
        import subprocess
        process = subprocess.Popen(
            ["piper", "--model", PIPER_MODEL_PATH, "--output_file", output_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        _, stderr = process.communicate(input=text.encode('utf-8'))
        
        if process.returncode != 0:
            logger.error(f"Piper TTS failed: {stderr.decode('utf-8')}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        return False
