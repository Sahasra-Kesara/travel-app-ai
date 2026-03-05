from faster_whisper import WhisperModel
import tempfile
import os

# Load model (small = fast, base = better accuracy)
model = WhisperModel("base", compute_type="int8")

def transcribe_audio(audio_file_path):
    """
    Convert speech audio to text
    """
    segments, info = model.transcribe(audio_file_path)

    text = ""
    for segment in segments:
        text += segment.text + " "

    return text.strip()