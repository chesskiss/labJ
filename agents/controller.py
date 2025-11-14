from audio.mic_stream import MicrophoneStream
from stt.transcriber import Transcriber

import numpy as np
import asyncio

async def main():
    mic = MicrophoneStream()
    transcriber = Transcriber()

    mic.start()
    async for audio_chunk in mic.stream_async():
        if audio_chunk is None or len(audio_chunk) == 0:
            continue

        # ✅ Add these lines
        print(f"[DEBUG] Audio chunk shape: {audio_chunk.shape}")
        print(f"[DEBUG] Mean volume: {np.abs(audio_chunk).mean():.5f}")

        try:
            audio_chunk = audio_chunk.flatten()
            text, action = transcriber.transcribe(audio_chunk, mic.sample_rate)

            if text.strip():
                print(f"📝 Transcribed: {text}")

        except Exception as e:
            print(f"❌ Error during transcription: {e}")


if __name__ == "__main__":
    asyncio.run(run())
