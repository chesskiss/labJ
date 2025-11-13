from audio.mic_stream import MicStream
from stt.transcriber import Transcriber

mic = MicStream()
transcriber = Transcriber()

while mic.is_active:
    audio = mic.record_once()
    text, action = transcriber.transcribe(audio)

    if action == "stop_listening":
        mic.stop()
