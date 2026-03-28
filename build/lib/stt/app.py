"""
Faster-Whisper STT API Service
A simple FastAPI wrapper around faster-whisper for speech-to-text transcription.
"""

import os
import time
import tempfile
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration via environment variables ──────────────────────────────────
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large-v3
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu or cuda
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, float16, float32
NUM_WORKERS = int(os.getenv("WHISPER_WORKERS", "2"))

model: WhisperModel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model on startup, release on shutdown."""
    global model
    logger.info(
        f"Loading model '{MODEL_SIZE}' on {DEVICE} with compute_type={COMPUTE_TYPE}..."
    )
    start = time.time()
    model = WhisperModel(
        MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        cpu_threads=NUM_WORKERS,
    )
    logger.info(f"Model loaded in {time.time() - start:.1f}s")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Faster-Whisper STT API",
    description="Speech-to-text transcription powered by faster-whisper",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "model": MODEL_SIZE, "device": DEVICE}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(
        ..., description="Audio file (wav, mp3, m4a, flac, ogg, webm)"
    ),
    language: str = Query(
        default=None,
        description="Language code (e.g. 'en', 'he'). Auto-detect if omitted.",
    ),
    beam_size: int = Query(
        default=5, ge=1, le=10, description="Beam size for decoding"
    ),
    word_timestamps: bool = Query(
        default=False, description="Include word-level timestamps"
    ),
    vad_filter: bool = Query(
        default=True, description="Filter out non-speech segments using Silero VAD"
    ),
    initial_prompt: str = Query(
        default=None,
        description="Optional prompt to condition the model (helps with jargon)",
    ),
):
    """
    Transcribe an uploaded audio file.

    Supports: wav, mp3, m4a, flac, ogg, webm and most ffmpeg-compatible formats.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    # Save uploaded file to a temp location
    suffix = os.path.splitext(file.filename or "audio.wav")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        start = time.time()

        segments, info = model.transcribe(
            tmp_path,
            beam_size=beam_size,
            language=language,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            initial_prompt=initial_prompt,
        )

        # Consume the generator and build response
        results = []
        full_text_parts = []

        for segment in segments:
            seg_data = {
                "id": segment.id,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
            }

            if word_timestamps and segment.words:
                seg_data["words"] = [
                    {
                        "word": w.word.strip(),
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 3),
                    }
                    for w in segment.words
                ]

            results.append(seg_data)
            full_text_parts.append(segment.text.strip())

        elapsed = time.time() - start

        return JSONResponse(
            {
                "text": " ".join(full_text_parts),
                "segments": results,
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
                "duration_seconds": round(info.duration, 2),
                "processing_time_seconds": round(elapsed, 2),
            }
        )

    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
