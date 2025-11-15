# agents/controller.py

from datetime import datetime, timedelta, timezone

import asyncio
import numpy as np

from audio.mic_stream import MicrophoneStream
from stt.transcriber import Transcriber
from storage.sqlite_repository import SQLiteTranscriptRepository
from env_config import STT_WINDOW_SEC


async def main():
    mic = MicrophoneStream()
    transcriber = Transcriber()
    repo = SQLiteTranscriptRepository()

    # Start a new session
    session_id = repo.start_session(title="Lab voice session", metadata={})

    is_transcribing = True  # controlled by triggers
    window_delta = timedelta(seconds=STT_WINDOW_SEC)

    try:
        mic.start()
        async for audio_chunk in mic.stream_async():
            if audio_chunk is None or len(audio_chunk) == 0:
                continue

            try:
                audio_chunk = audio_chunk.flatten()
                text, action = transcriber.transcribe(audio_chunk, mic.sample_rate)
                now = datetime.now(timezone.utc)

                # Handle actions (triggers)
                if action is not None:
                    repo.save_action(
                        session_id=session_id,
                        time=now,
                        action_type=action,
                        raw_text=text if text else None,
                    )

                    if action == "pause_transcription":
                        is_transcribing = False
                        print("[Controller] ▶️ Paused transcription")
                    elif action == "resume_transcription":
                        is_transcribing = True
                        print("[Controller] ▶️ Resumed transcription")
                    elif action == "stop_listening":
                        print("[Controller] ⏹ Stop listening requested")
                        break

                # Save utterance only if we're in transcribing mode
                if is_transcribing and text and text.strip():
                    start_time = now - window_delta
                    repo.save_utterance(
                        session_id=session_id,
                        start_time=start_time,
                        end_time=now,
                        text=text,
                        source="stt",
                    )
                    print(f"📝 Transcribed: {text}")

            except Exception as e:
                print(f"❌ Error during transcription loop: {e}")

    finally:
        # End session gracefully
        repo.end_session(session_id=session_id)
        # You might also want: repo.close()
        print("[Controller] Session ended.")


if __name__ == "__main__":
    asyncio.run(main())
