# labJ/tests/test_trigger.py

import pytest
import numpy as np

from stt.trigger import TriggerEvaluator
from stt.transcriber import Transcriber


# ------------------ TriggerEvaluator tests ------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("please stop writing now", "pause_transcription"),
        ("can you resume writing", "resume_transcription"),
        ("stop listening to me please", "stop_listening"),
        ("this is just a sentence", None),
        ("STOP WRITING", "pause_transcription"),
        ("unmute transcription", "resume_transcription"),
        ("shutdown the system", "stop_listening"),
        # Extra phrases you now actually say:
        ("please stop transcribing", "pause_transcription"),
        ("can you start transcribing again", "resume_transcription"),
    ],
)
def test_trigger_evaluation(text, expected):
    evaluator = TriggerEvaluator()
    result = evaluator.evaluate(text)
    assert result == expected, f"Expected '{expected}', got '{result}' for: '{text}'"


# ------------------ Simple integration: stop_listening behavior ------------------


class FakeMicStream:
    """Tiny fake mic to simulate stop_listening behavior."""

    def __init__(self):
        self.streaming = True

    def stop(self):
        self.streaming = False

    def is_streaming(self):
        return self.streaming


def test_stop_listening_integration():
    mic = FakeMicStream()
    evaluator = TriggerEvaluator()

    text = "please stop listening right now"
    action = evaluator.evaluate(text)

    if action == "stop_listening":
        mic.stop()

    assert mic.is_streaming() is False


# ------------------ Transcriber tests ------------------


def test_transcriber_initialization():
    """Basic sanity: model loads and object is constructed."""
    transcriber = Transcriber(model_size="tiny")
    assert transcriber.model is not None


def test_transcriber_empty_audio():
    """Empty audio should produce (\"\", None)."""
    transcriber = Transcriber(model_size="tiny")
    text, action = transcriber.transcribe(audio_chunk=np.array([]), sample_rate=16000)
    assert text == ""
    assert action is None


# ------------------ Transcriber buffering + model integration ------------------


class DummySegment:
    """Minimal stand-in for faster_whisper segments."""

    def __init__(self, text: str):
        self.text = text


def dummy_transcribe_hello(audio, language="en"):
    """Fake backend that always returns 'hello world'."""
    return [DummySegment("hello world")], None


def dummy_transcribe_pause(audio, language="en"):
    """Fake backend that returns a phrase that should pause transcription."""
    return [DummySegment("please stop writing now")], None


def test_transcriber_buffering_aggregates_chunks(monkeypatch):
    """
    Transcriber should buffer multiple chunks internally and only
    emit text once enough samples have been collected.
    """
    t = Transcriber(model_size="tiny")

    # Make the window tiny so we don't need real audio
    t._window_samples = 4
    t._overlap_samples = 0
    t._buffer = np.array([], dtype=np.float32)

    # Stub out the underlying model so we don't call the real Whisper
    t.model = type("DummyModel", (), {"transcribe": staticmethod(dummy_transcribe_hello)})

    # First short chunk -> not enough samples yet, expect no text
    text, action = t.transcribe(np.ones(2, dtype=np.float32), 16000)
    assert text == ""
    assert action is None

    # Second chunk -> enough samples, dummy model is called
    text, action = t.transcribe(np.ones(2, dtype=np.float32), 16000)
    assert text == "hello world"
    assert action is None


def test_transcriber_trigger_integration(monkeypatch):
    """
    When the model outputs a phrase containing a stop-transcription trigger,
    Transcriber should return both the text and the appropriate action.
    """
    t = Transcriber(model_size="tiny")

    # Tiny window again to avoid big buffers in tests
    t._window_samples = 4
    t._overlap_samples = 0
    t._buffer = np.array([], dtype=np.float32)

    # Fake model that returns a 'stop writing' phrase
    t.model = type("DummyModel", (), {"transcribe": staticmethod(dummy_transcribe_pause)})

    # First chunk: buffer too small -> no text/action
    text, action = t.transcribe(np.ones(2, dtype=np.float32), 16000)
    assert text == ""
    assert action is None

    # Second chunk: enough samples -> phrase recognized and trigger fired
    text, action = t.transcribe(np.ones(2, dtype=np.float32), 16000)
    assert text == "please stop writing now"
    assert action == "pause_transcription"
