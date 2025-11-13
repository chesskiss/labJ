# stt/transcriber.py
import sys
from pathlib import Path
import site
root = Path(__file__).resolve().parent
site.addsitedir(str(root))

from faster_whisper import WhisperModel
import numpy as np
import sounddevice as sd
from config import STT_SAMPLE_RATE, STT_MODEL_SIZE, STT_DURATION
from trigger import TriggerEvaluator


class Transcriber:
    def __init__(self, model_size="base", compute_type="int8"):
        try:
            self.model = WhisperModel(model_size, compute_type=compute_type)
            self.trigger = TriggerEvaluator()
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model '{model_size}': {e}")

    def transcribe(self, audio_chunk, sample_rate=16000):
        if audio_chunk is None or len(audio_chunk) == 0:
            raise ValueError("Empty or invalid audio chunk received for transcription.")

        try:
            segments, _ = self.model.transcribe(audio_chunk, language="en")
            result = " ".join([seg.text for seg in segments])
            print(f"[DEBUG] Recognized speech: '{result}'")
            trigger_action = self.trigger.evaluate(result)
            if trigger_action:
                print(f"[DEBUG] Trigger action detected: {trigger_action}")
                mic_stream.stop()
            return result, trigger_action
        except Exception as e:
            raise RuntimeError(f"Error during transcription: {e}")


if __name__ == "__main__":
    sample_rate = STT_SAMPLE_RATE
    duration = STT_DURATION

    try:
        print("🎙️ Recording... Speak now!")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()

        transcriber = Transcriber(model_size="tiny")
        audio = audio.flatten()
        text, action = transcriber.transcribe(audio, sample_rate)
        print("📝 Transcribed:", text)
        print("⚙️ Trigger Action:", action)

    except Exception as e:
        print(f"❌ Error: {e}")


#TODO: test recording in noisy environments, e.g. dunkin donuts, labs. Recognition was terrible.
#TODO: failsafe if noise sabotages input