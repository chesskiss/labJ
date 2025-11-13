import pytest
import numpy as np
from stt.trigger import TriggerEvaluator
from stt.transcriber import Transcriber

# ------------------ Trigger Evaluator Tests ------------------

@pytest.mark.parametrize("text,expected", [
    ("please stop writing now", "pause_transcription"),
    ("can you resume writing", "resume_transcription"),
    ("stop listening to me please", "stop_listening"),
    ("this is just a sentence", None),
    ("STOP WRITING", "pause_transcription"),
    ("unmute transcription", "resume_transcription"),
    ("shutdown the system", "stop_listening"),
])
def test_trigger_evaluation(text, expected):
    evaluator = TriggerEvaluator()
    result = evaluator.evaluate(text)
    assert result == expected, f"Expected '{expected}', got '{result}' for: '{text}'"


# ------------------ Integration: Stop Listening Behavior ------------------

class FakeMicStream:
    def __init__(self):
        self.streaming = True

    def stop(self):
        self.streaming = False

    def is_streaming(self):
        return self.streaming


@pytest.mark.asyncio
async def test_stop_listening_stops_mic():
    mic = FakeMicStream()
    evaluator = TriggerEvaluator()
    transcript = "Testing... stop listening now"
    action = evaluator.evaluate(transcript)

    if action == "stop_listening":
        mic.stop()

    assert mic.is_streaming() is False


# ------------------ Transcriber Tests ------------------

def test_transcriber_initialization():
    transcriber = Transcriber(model_size="tiny")
    assert transcriber.model is not None

def test_transcriber_empty_audio():
    transcriber = Transcriber(model_size="tiny")
    text = transcriber.transcribe(audio_chunk=np.array([]), sample_rate=16000)
    assert text == ""
