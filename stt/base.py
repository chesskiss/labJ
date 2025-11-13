# stt/base.py
from abc import ABC, abstractmethod

class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_chunk, sample_rate):
        pass
