# stt/transcriber.py

"""Buffered Whisper transcriber.

- Keeps `main` and controller API unchanged: `text, action = transcriber.transcribe(chunk, sr)`.
- Handles short streaming chunks by buffering internally and only calling Whisper
  when enough audio has accumulated.
"""

from typing import Tuple, Optional

import numpy as np
from faster_whisper import WhisperModel

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
    """Streaming transcriber with internal buffering.

    Public API:
        transcribe(audio_chunk: np.ndarray, sample_rate: int) -> tuple[str, Optional[str]]
    """
    #TODO check if GPU available on windows, android, macos, ios, and choose int8_float16, float16, etc. Heavy whisper: large-v3
    def __init__(self, model_size: Optional[str] = "small", compute_type: str = "int8"):
        self.sample_rate: int = STT_SAMPLE_RATE
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
            f"[Transcriber] Init: model={self.model_size}, compute_type={compute_type}, "
            f"window={self._window_sec}s, overlap={self._overlap_sec}s"
        )

        try:
            self.model = WhisperModel(self.model_size, compute_type=compute_type)
            self.trigger = TriggerEvaluator()
        except Exception as e:  # pragma: no cover - fail fast on model issues
            raise RuntimeError(f"Failed to load Whisper model '{self.model_size}': {e}")

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

        window_rms = float(np.sqrt(np.mean(window ** 2))) if window.size > 0 else 0.0
        
        if window_rms < self._min_window_rms:
            # Too quiet, treat as silence / background noise
            # Do NOT reset buffer; keep accumulating
            # so we can still capture real speech when it comes.
            # Optional: print debug
            # print(f"[Transcriber] Skipping window, low RMS: {window_rms:.6f}")
            return "", None

        try:
            segments, _ = self.model.transcribe(
                window, 
                language="en",  # avoid language detection
                beam_size=1,           # 1 = fastest, higher = better but slower
                best_of=1,
                vad_filter=True,       # skip silence
                word_timestamps=False, # cheaper
            )
            texts = [seg.text.strip() for seg in segments if seg.text.strip()]
            result = " ".join(texts).strip()

            print(f"[Transcriber] STT window result: {result!r}")

            if not result:
                # Do not reset buffer; let it accumulate more audio
                return "", None
            
            if len(result) < self._min_text_chars and not self.trigger.contains_any_keyword(result):
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
            print(f"[Transcriber] Error during Whisper transcription: {e}")
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
