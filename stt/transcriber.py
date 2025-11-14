# stt/transcriber.py
from env_config import STT_SAMPLE_RATE
import numpy as np
import sounddevice as sd
from stt.trigger import TriggerEvaluator
from faster_whisper import WhisperModel



class Transcriber:
    def __init__(self, model_size="base", compute_type="int8"):
        try:
            self.model = WhisperModel(model_size, compute_type=compute_type)
            self.trigger = TriggerEvaluator()
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model '{model_size}': {e}")

    def transcribe(self, audio_chunk, sample_rate=STT_SAMPLE_RATE):
        if audio_chunk is None or len(audio_chunk) == 0:
            return "", None

        try:
            segments, _ = self.model.transcribe(audio_chunk, language="en")
            result = " ".join([seg.text for seg in segments]).strip()

            if result:
                trigger_action = self.trigger.evaluate(result)
                return result, trigger_action
            return "", None

        except Exception as e:
            raise RuntimeError(f"Error during transcription: {e}")

