# stt/transcriber.py

from faster_whisper import WhisperModel
import numpy as np
import sounddevice as sd
from config import STT_SAMPLE_RATE, STT_MODEL_SIZE, STT_DURATION


class Transcriber:
    def __init__(self, model_size="base", compute_type="int8"):
        self.model = WhisperModel(model_size, compute_type=compute_type)

    def transcribe(self, audio_chunk, sample_rate=16000):
        if audio_chunk is None or len(audio_chunk) == 0:
            return ""

        try:
            segments, _ = self.model.transcribe(audio_chunk, language="en")
            result = " ".join([seg.text for seg in segments])
            return result
        except Exception:
            return ""


if __name__ == "__main__":
    sample_rate = STT_SAMPLE_RATE
    duration = STT_DURATION

    try:
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()

        transcriber = Transcriber(model_size="tiny")
        audio = audio.flatten()
        text = transcriber.transcribe(audio, sample_rate)
        print(text)

    except Exception as e:
        pass