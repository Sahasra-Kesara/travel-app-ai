from faster_whisper import WhisperModel
import tempfile
import os

# Force CPU + int8 to avoid CUDA dependency on Windows
model = WhisperModel("base", device="cpu", compute_type="int8")

def transcribe_audio(audio_file_path):
    """
    Convert speech audio to text
    """
    segments, info = model.transcribe(audio_file_path, beam_size=5)

    text = ""
    for segment in segments:
        text += segment.text + " "

    return text.strip()