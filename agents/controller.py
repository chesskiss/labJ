from audio.mic_stream import MicrophoneStream
from stt.transcriber import Transcriber

import numpy as np
import asyncio


async def main():
    mic = MicrophoneStream()
    transcriber = Transcriber()

    # State: are we currently writing/transcribing user text?
    is_transcribing = True

    mic.start()
    async for audio_chunk in mic.stream_async():
        if audio_chunk is None or len(audio_chunk) == 0:
            continue

        # Optional debug
        # print(f"[DEBUG] Mean volume: {np.abs(audio_chunk).mean():.5f}")

        try:
            audio_chunk = audio_chunk.flatten()
            text, action = transcriber.transcribe(audio_chunk, mic.sample_rate)

            # --- Handle trigger actions first ---
            if action == "pause_transcription":
                is_transcribing = False
                print("[Controller] ▶️ Paused transcription (still listening for commands)")
            elif action == "resume_transcription":
                is_transcribing = True
                print("[Controller] ▶️ Resumed transcription")
            elif action == "stop_listening":
                print("[Controller] ⏹ Stop listening requested, shutting down")
                break

            # --- Only emit/save text if we are in 'transcribing' mode ---
            if is_transcribing and text.strip():
                print(f"📝 Transcribed: {text}")

        except Exception as e:
            print(f"❌ Error during transcription: {e}")


if __name__ == "__main__":
    asyncio.run(main())
