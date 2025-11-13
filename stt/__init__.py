"""
Speech-to-text (STT) module for transcribing audio to text.

Includes:
- FasterWhisper-based local transcription
- Extensible base class for other engines (e.g., Vosk, API)
"""

from .transcriber import Transcriber

__all__ = ["Transcriber"] #TODO add - ["VoskTranscriber", "StreamTranscriber"]
