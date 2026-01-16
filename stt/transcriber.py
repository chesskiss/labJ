# stt/transcriber.py

"""Buffered Whisper transcriber using Groq API.

- Keeps `main` and controller API unchanged: `text, action = transcriber.transcribe(chunk, sr)`.
- Handles short streaming chunks by buffering internally and only calling Whisper
  when enough audio has accumulated.
- Uses Groq's Whisper Large v3 Turbo API for transcription.
"""

from typing import Tuple, Optional
import os
import tempfile

import numpy as np
import soundfile as sf

# from faster_whisper import WhisperModel  # Replaced with Groq API
from groq import Groq

from stt.trigger import TriggerEvaluator
from config import (
    STT_SAMPLE_RATE,
    STT_MODEL_SIZE,
    STT_WINDOW_SEC,
    STT_OVERLAP_SEC,
    STT_MIN_WINDOW_RMS,
    STT_MIN_TEXT_CHARS,
    STT_DURATION,
)


class Transcriber:
    """Streaming transcriber with internal buffering using Groq API.

    Public API:
        transcribe(audio_chunk: np.ndarray, sample_rate: int) -> tuple[str, Optional[str]]
    """

    def __init__(self, model_size: Optional[str] = "small", compute_type: str = "int8"):
        self.sample_rate: int = STT_SAMPLE_RATE
        # model_size and compute_type kept for API compatibility but not used with Groq
        self.model_size: str = model_size or STT_MODEL_SIZE

        # Internal rolling buffer
        self._buffer: np.ndarray = np.array([], dtype=np.float32)

        # Window / overlap configuration (in seconds -> samples)
        self._window_sec: float = float(STT_WINDOW_SEC)
        self._overlap_sec: float = float(STT_OVERLAP_SEC)

        self._window_samples: int = int(self._window_sec * self.sample_rate)
        self._overlap_samples: int = int(self._overlap_sec * self.sample_rate)

        self._min_window_rms: float = float(STT_MIN_WINDOW_RMS)
        self._min_text_chars: int = int(STT_MIN_TEXT_CHARS)

        print(
            f"[Transcriber] Init: Using Groq Whisper Large v3 Turbo API, "
            f"window={self._window_sec}s, overlap={self._overlap_sec}s"
        )

        try:
            # Initialize Groq client instead of local WhisperModel
            self.groq_client = Groq(api_key=os.getenv("LLM_API_KEY"))
            self.trigger = TriggerEvaluator()
        except Exception as e:  # pragma: no cover - fail fast on model issues
            raise RuntimeError(f"Failed to initialize Groq client: {e}")

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def transcribe(
        self, audio_chunk: np.ndarray, sample_rate: Optional[int] = None
    ) -> Tuple[str, Optional[str]]:
        """Process a streaming chunk.

        - Appends `audio_chunk` to an internal rolling buffer.
        - Only calls Whisper when the buffer length exceeds the configured window.
        - Returns ("", None) until a window is ready or if nothing meaningful was recognized.
        - When text is recognized, also returns an optional trigger `action`.
        """

        if audio_chunk is None:
            return "", None

        # Normalize to 1D float32 numpy array
        audio_chunk = np.asarray(audio_chunk, dtype=np.float32)
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.flatten()

        if audio_chunk.size == 0:
            return "", None

        # Note: we deliberately ignore `sample_rate` argument and trust STT_SAMPLE_RATE
        # for consistency throughout the system.

        # Append to internal buffer
        self._buffer = np.concatenate([self._buffer, audio_chunk])

        # If we don't yet have enough audio, do not call Whisper
        if self._buffer.size < self._window_samples:
            return "", None

        # Use the last `window` samples as the current context window
        window = self._buffer[-self._window_samples :]

        window_rms = float(np.sqrt(np.mean(window**2))) if window.size > 0 else 0.0

        if window_rms < self._min_window_rms:
            # Too quiet, treat as silence / background noise
            # Do NOT reset buffer; keep accumulating
            # so we can still capture real speech when it comes.
            # Optional: print debug
            # print(f"[Transcriber] Skipping window, low RMS: {window_rms:.6f}")
            return "", None

        try:
            # Save window audio to temporary WAV file for Groq API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_path = temp_audio.name
                sf.write(temp_path, window, self.sample_rate)

            # Call Groq Whisper API
            with open(temp_path, "rb") as audio_file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language="en",
                    response_format="text",
                )

            # Clean up temp file
            os.unlink(temp_path)

            # Extract text result
            result = transcription.strip() if isinstance(transcription, str) else ""

            print(f"[Transcriber] STT window result: {result!r}")

            if not result:
                # Do not reset buffer; let it accumulate more audio
                return "", None

            if len(
                result
            ) < self._min_text_chars and not self.trigger.contains_any_keyword(result):
                # This is likely random "you / uh / hm" from noise.
                # Let it pass through only if it's actually a command phrase.
                # Optional debug:
                # print(f"[Transcriber] Ignoring short non-command text: {result!r}")
                return "", None

            # Trigger / command-control evaluation
            action = self.trigger.evaluate(result)
            if action:
                print(f"[Transcriber] Trigger action: {action}")

            # Keep only the overlap for the next call
            if self._overlap_samples > 0:
                self._buffer = self._buffer[-self._overlap_samples :]
            else:
                self._buffer = np.array([], dtype=np.float32)

            return result, action

        except Exception as e:
            print(f"[Transcriber] Error during Groq API transcription: {e}")
            return "", None


if __name__ == "__main__":
    """Simple blocking mic test for debugging.

    Uses the same buffering logic but records one long clip instead of streaming.
    """
    import sounddevice as sd

    sample_rate = STT_SAMPLE_RATE
    duration = STT_DURATION

    try:
        print(f"[__main__] Recording {duration}s at {sample_rate}Hz...")
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        transcriber = Transcriber()
        text, action = transcriber.transcribe(audio, sample_rate)

        print(f"[__main__] Text: {text}")
        print(f"[__main__] Action: {action}")

    except Exception as e:
        print(f"[__main__] Error during mic test: {e}")
