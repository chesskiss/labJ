from stt.transcriber import Transcriber
from stt.config import STT_SAMPLE_RATE
import sounddevice as sd

def record_and_transcribe():
    duration = 5
    audio = sd.rec(int(duration * STT_SAMPLE_RATE), samplerate=STT_SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    transcriber = Transcriber()
    print(transcriber.transcribe(audio.flatten(), STT_SAMPLE_RATE))

if __name__ == "__main__":
    record_and_transcribe()
