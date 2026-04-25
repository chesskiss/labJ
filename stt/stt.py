"""
Real-time STT client: mic capture -> VAD pause detection -> faster-whisper API -> text

Usage:
    # As a script (press Enter to stop recording):
    python stt.py

    # As a module with real-time callback:
    from stt import STTClient

    def on_transcription(text: str):
        print(f"Got: {text}")

    client = STTClient(on_transcription=on_transcription)
    client.start()
    # ... user speaks, callback fires after each pause ...
    client.stop()
"""

import io
import wave
import queue
import threading
from typing import TYPE_CHECKING, Any, Callable

import requests  # type: ignore[import-untyped]
import numpy as np

if TYPE_CHECKING:
    pass


class STTClient:
    """
    Captures audio from microphone and transcribes via faster-whisper API.
    Supports real-time transcription by detecting pauses in speech.
    """

    def __init__(
        self,
        on_transcription: Callable[[str], None] | None = None,
        api_url: str = "http://localhost:8000/transcribe",
        sample_rate: int = 16000,
        channels: int = 1,
        # VAD parameters
        silence_threshold: float = 0.01,  # RMS threshold for silence detection
        speech_min_duration: float = 0.3,  # Min speech duration to transcribe (seconds)
        silence_duration: float = 0.8,  # Silence duration to trigger transcription (seconds)
        chunk_duration: float = 0.1,  # Audio chunk size for processing (seconds)
        language: str | None = None,
    ):
        self.on_transcription = on_transcription
        self.api_url = api_url
        self.sample_rate = sample_rate
        self.channels = channels
        self.language = language

        # VAD config
        self.silence_threshold = silence_threshold
        self.speech_min_samples = int(speech_min_duration * sample_rate)
        self.silence_samples = int(silence_duration * sample_rate)
        self.chunk_samples = int(chunk_duration * sample_rate)

        # State
        self._stream: Any | None = None
        self._recording = False
        self._audio_queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._processor_thread: threading.Thread | None = None
        self._all_transcriptions: list[str] = []

    def start(self) -> None:
        """Start recording and real-time transcription."""
        if self._recording:
            return

        print(
            f"[STTClient] starting (api_url={self.api_url}, sample_rate={self.sample_rate}, "
            f"silence_threshold={self.silence_threshold})"
        )
        self._recording = True
        self._all_transcriptions = []
        self._audio_queue = queue.Queue()

        # Start processor thread
        self._processor_thread = threading.Thread(
            target=self._process_audio, daemon=True
        )
        self._processor_thread.start()

        # Start audio stream
        try:
            import sounddevice as sd
        except OSError as exc:
            raise RuntimeError(
                "Microphone capture requires PortAudio. Install the PortAudio runtime/library."
            ) from exc
        except ImportError as exc:
            raise RuntimeError(
                "Microphone capture requires the sounddevice package."
            ) from exc

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.int16,
            blocksize=self.chunk_samples,
            callback=self._audio_callback,
        )
        self._stream.start()

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info, status
    ) -> None:
        """Called by sounddevice for each audio chunk."""
        if self._recording:
            self._audio_queue.put(indata.copy())

    def _process_audio(self) -> None:
        """Background thread: accumulate audio, detect pauses, trigger transcription."""
        speech_buffer: list[np.ndarray] = []
        silence_count = 0
        is_speaking = False

        while self._recording or not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if chunk is None:
                break

            # Calculate RMS energy
            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0

            if rms > self.silence_threshold:
                # Speech detected
                is_speaking = True
                silence_count = 0
                speech_buffer.append(chunk)
            else:
                # Silence detected
                if is_speaking:
                    speech_buffer.append(chunk)  # Include trailing silence
                    silence_count += len(chunk)

                    # Check if pause is long enough to trigger transcription
                    if silence_count >= self.silence_samples:
                        audio = np.concatenate(speech_buffer, axis=0)

                        # Only transcribe if enough speech was captured
                        if len(audio) >= self.speech_min_samples:
                            self._send_for_transcription(audio)

                        # Reset for next utterance
                        speech_buffer = []
                        silence_count = 0
                        is_speaking = False

        # Process any remaining audio when stopping
        if speech_buffer:
            audio = np.concatenate(speech_buffer, axis=0)
            if len(audio) >= self.speech_min_samples:
                self._send_for_transcription(audio)

    def _send_for_transcription(self, audio: np.ndarray) -> None:
        """Send audio segment to API and handle the result."""
        wav_bytes = self._to_wav(audio)
        text = self._transcribe(wav_bytes)

        if text.strip():
            cleaned = text.strip()
            print(f"[STTClient] transcript: {cleaned}")
            self._all_transcriptions.append(cleaned)
            if self.on_transcription:
                self.on_transcription(cleaned)

    def stop(self) -> str:
        """Stop recording and return all transcribed text combined."""
        if not self._recording:
            return ""

        self._recording = False

        # Stop audio stream
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        # Signal processor thread to finish
        self._audio_queue.put(None)

        # Wait for processor to finish
        if self._processor_thread:
            self._processor_thread.join(timeout=30)
            self._processor_thread = None

        full_text = " ".join(self._all_transcriptions)
        print(
            f"[STTClient] stopped (segments={len(self._all_transcriptions)}, "
            f"chars={len(full_text)})"
        )
        return full_text

    def _to_wav(self, audio: np.ndarray) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()

    def _transcribe(self, wav_bytes: bytes) -> str:
        """Send audio to STT API and return transcribed text."""
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        params = {"vad_filter": "true"}
        if self.language:
            params["language"] = self.language

        try:
            resp = requests.post(self.api_url, files=files, params=params, timeout=120)
            resp.raise_for_status()
            return resp.json().get("text", "")
        except requests.RequestException as e:
            print(f"STT API error: {e}")
            return ""


def run_interactive(on_transcription: Callable[[str], None] | None = None) -> str:
    """
    Run interactive recording session until user presses Enter.

    Args:
        on_transcription: Optional callback called with each transcribed segment.
                         If None, segments are collected silently.

    Returns:
        Full transcription text (all segments joined).
    """
    client = STTClient(on_transcription=on_transcription)

    print("Recording... (press Enter to stop)")
    client.start()
    input()

    print("Stopping...")
    return client.stop()


if __name__ == "__main__":

    def print_segment(text: str):
        print(f">> {text}")

    run_interactive(on_transcription=print_segment)
