"""
Microphone stream handler for real-time audio capture.

This module provides functionality to capture audio from the microphone
in real-time using sounddevice, with support for streaming and buffering.
"""
from env_config import CHUNK_SIZE, STT_SAMPLE_RATE

import asyncio
import logging
import queue
import numpy as np
from typing import AsyncIterator, Optional, Callable
import sounddevice as sd

logger = logging.getLogger(__name__)


class MicrophoneStream:
    """
    Handles real-time microphone input streaming.
    
    This class provides an async interface for capturing audio from the
    microphone and streaming it in chunks for processing.
    """
    
    def __init__(
        self,
        sample_rate: int = STT_SAMPLE_RATE,
        channels: int = 1,
        chunk_size: int = CHUNK_SIZE,
        device: Optional[int] = None,
        dtype: str = "float32",
        callback: Optional[Callable] = None
    ):
        """
        Initialize the microphone stream.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            chunk_size: Size of audio chunks in frames
            device: Audio device index (None for default)
            dtype: Data type for audio samples
            callback: Optional callback function for audio chunks
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device
        self.dtype = dtype
        self.callback = callback
        
        self.audio_queue: queue.Queue = queue.Queue()
        self.is_streaming = False
        self.stream: Optional[sd.InputStream] = None
        
        # TODO: Add audio buffer for VAD (Voice Activity Detection)
        # self.vad_buffer = []
        # self.vad_threshold = 0.01
    
    def _audio_callback(self, indata, frames, time, status):
        """
        Callback function called by sounddevice for each audio chunk.
        
        Args:
            indata: Input audio data
            frames: Number of frames
            time: Timestamp information
            status: Status flags
        """
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # Convert to the desired dtype
        audio_chunk = indata.copy()
        if self.dtype == "float32":
            audio_chunk = audio_chunk.astype(np.float32)
        elif self.dtype == "int16":
            audio_chunk = (audio_chunk * 32767).astype(np.int16)
        
        # Put audio chunk in queue
        self.audio_queue.put(audio_chunk.copy())
        
        # Call user callback if provided
        if self.callback:
            self.callback(audio_chunk, time, status)
    
    def start(self):
        """Start the audio stream."""
        if self.is_streaming:
            logger.warning("Stream is already running")
            return
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                callback=self._audio_callback
            )
            self.stream.start()
            self.is_streaming = True
            logger.info(f"Started audio stream: {self.sample_rate}Hz, {self.channels} channel(s)")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise
    
    def stop(self):
        """Stop the audio stream."""
        if not self.is_streaming:
            return
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        self.is_streaming = False
        logger.info("Stopped audio stream")
    
    async def stream_async(self) -> AsyncIterator[np.ndarray]:
        """
        Async generator that yields audio chunks from the microphone.
        
        Yields:
            Audio chunk as numpy array
        
        TODO: Implement proper async streaming with voice activity detection
        """
        if not self.is_streaming:
            self.start()
        
        try:
            while self.is_streaming:
                # Get audio chunk from queue (non-blocking)
                try:
                    audio_chunk = self.audio_queue.get_nowait()
                    yield audio_chunk
                except queue.Empty:
                    # No audio available, yield control
                    await asyncio.sleep(0.01)
                    
                # TODO: Add voice activity detection
                # if self._has_voice_activity(audio_chunk):
                #     yield audio_chunk
        except asyncio.CancelledError:
            logger.info("Audio streaming cancelled")
            raise
        finally:
            self.stop()
    
    def get_audio_chunk(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Get a single audio chunk from the stream (synchronous).
        
        Args:
            timeout: Maximum time to wait for audio chunk
        
        Returns:
            Audio chunk or None if timeout
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def list_devices(self):
        """
        List available audio input devices.
        
        TODO: Implement device listing with detailed information
        """
        # TODO: Print available audio devices with their capabilities
        devices = sd.query_devices()
        logger.info("Available audio devices:")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                logger.info(f"  [{i}] {device['name']} - {device['max_input_channels']} channels")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    # TODO: Add voice activity detection methods
    # def _has_voice_activity(self, audio_chunk: np.ndarray) -> bool:
    #     """Detect if audio chunk contains voice activity."""
    #     pass
    
    # TODO: Add audio level monitoring
    # def get_audio_level(self, audio_chunk: np.ndarray) -> float:
    #     """Get the RMS level of audio chunk."""
    #     pass

