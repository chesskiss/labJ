# Faster-Whisper STT Docker Service

A lightweight, self-contained speech-to-text API powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — up to **4x faster** than OpenAI's Whisper with the same accuracy, using less memory.

## Quick Start

```bash
# 1. Build and run
docker compose up --build -d

# 2. Wait ~30s for model download on first run, then check:
curl http://localhost:8000/health

# 3. Transcribe an audio file
curl -X POST http://localhost:8000/transcribe \
  -F "file=@your_audio.wav"

# 4. View interactive API docs
open http://localhost:8000/docs
```

## Project Structure

```
├── Dockerfile           # CPU-optimized container
├── docker-compose.yml   # Easy orchestration with model caching
├── app.py               # FastAPI transcription service
├── requirements.txt     # Python dependencies
├── test_stt.sh          # Automated test script
└── README.md
```

## API Endpoints

### `GET /health`
Returns model status and config.

### `POST /transcribe`
Upload an audio file and get transcription back.

**Parameters (all optional except `file`):**

| Parameter        | Default | Description                                          |
|------------------|---------|------------------------------------------------------|
| `file`           | —       | Audio file (wav, mp3, m4a, flac, ogg, webm)          |
| `language`       | auto    | Language code (`en`, `he`, etc). Auto-detects if omitted |
| `beam_size`      | 5       | Beam size (1-10). Lower = faster, higher = more accurate |
| `word_timestamps`| false   | Include word-level timing                            |
| `vad_filter`     | true    | Filter silence with Silero VAD                       |
| `initial_prompt` | null    | Bias toward specific vocabulary/jargon               |

**Example response:**
```json
{
  "text": "Hello, this is a test recording for the lab journal.",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.42,
      "text": "Hello, this is a test recording for the lab journal."
    }
  ],
  "language": "en",
  "language_probability": 0.987,
  "duration_seconds": 3.42,
  "processing_time_seconds": 0.81
}
```

## Model Selection

Change the model in `docker-compose.yml` via the `WHISPER_MODEL` env var:

| Model             | Size   | RAM (approx) | Speed  | Accuracy  | Best for                   |
|-------------------|--------|-------------|--------|-----------|----------------------------|
| `tiny`            | 39M    | ~1 GB       | ★★★★★  | ★★        | Quick testing               |
| `base`            | 74M    | ~1 GB       | ★★★★   | ★★★       | **Default — good balance**  |
| `small`           | 244M   | ~2 GB       | ★★★    | ★★★★      | Better accuracy, still fast |
| `medium`          | 769M   | ~5 GB       | ★★     | ★★★★★     | High accuracy               |
| `large-v3`        | 1.5G   | ~10 GB      | ★      | ★★★★★+    | Best accuracy               |
| `large-v3-turbo`  | 809M   | ~6 GB       | ★★★    | ★★★★★     | **Best speed/accuracy**     |

**Recommendation:** Start with `base` to verify everything works, then upgrade to `small` or `large-v3-turbo` for your lab journal.

## Configuration

All config is via environment variables (set in `docker-compose.yml` or `docker run -e`):

```bash
WHISPER_MODEL=base            # Model size (see table above)
WHISPER_DEVICE=cpu            # cpu or cuda (GPU)
WHISPER_COMPUTE_TYPE=int8     # int8 (CPU), float16 (GPU), float32
WHISPER_WORKERS=4             # CPU threads
```

## Running

### With Docker Compose (recommended)
```bash
docker compose up --build -d        # Start
docker compose logs -f stt          # Watch logs
docker compose down                 # Stop
```

### With plain Docker
```bash
docker build -t faster-whisper-stt .

docker run -d \
  --name stt \
  -p 8000:8000 \
  -e WHISPER_MODEL=base \
  -e WHISPER_COMPUTE_TYPE=int8 \
  -v whisper-cache:/root/.cache/huggingface \
  faster-whisper-stt
```

### With GPU (NVIDIA)
```bash
# Requires: nvidia-container-toolkit installed on host
docker run -d \
  --name stt \
  --gpus all \
  -p 8000:8000 \
  -e WHISPER_MODEL=large-v3-turbo \
  -e WHISPER_DEVICE=cuda \
  -e WHISPER_COMPUTE_TYPE=float16 \
  -v whisper-cache:/root/.cache/huggingface \
  faster-whisper-stt
```

## Testing

### Automated test
```bash
chmod +x test_stt.sh
./test_stt.sh                       # Generates a test tone
./test_stt.sh my_recording.wav      # Test with your own file
```

### Record from microphone (requires `sox`)
```bash
# Install sox: brew install sox / apt install sox
rec -r 16000 -c 1 test.wav trim 0 5    # Record 5 seconds
./test_stt.sh test.wav
```

### curl examples
```bash
# Basic transcription
curl -X POST http://localhost:8000/transcribe \
  -F "file=@audio.wav"

# Force English + word timestamps
curl -X POST http://localhost:8000/transcribe \
  -F "file=@audio.wav" \
  -F "language=en" \
  -F "word_timestamps=true"

# Use initial_prompt for domain-specific jargon
curl -X POST http://localhost:8000/transcribe \
  -F "file=@audio.wav" \
  -F 'initial_prompt=Lab journal entry. Terms: FastAPI, SQLAlchemy, LangGraph, MCP, vector storage.'
```

### Python client example
```python
import requests

with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/transcribe",
        files={"file": ("audio.wav", f, "audio/wav")},
        data={
            "language": "en",
            "vad_filter": "true",
            "initial_prompt": "Lab journal. Terms: FastAPI, SQLAlchemy, uv.",
        },
    )

result = response.json()
print(result["text"])
```

## Tips for Better Accuracy

1. **Use `initial_prompt`** — feed it your common jargon and it'll recognize those terms much better
2. **Specify `language`** — auto-detection uses the first 30s; specifying it directly is faster and avoids misdetection
3. **Keep `vad_filter=true`** — filters out silence and background noise
4. **Upgrade the model** — `large-v3-turbo` is the sweet spot for quality vs speed
5. **16kHz mono** is the optimal input format, but faster-whisper handles resampling automatically

## Integration with Your Lab Journal

This service exposes a simple HTTP API that your FastAPI backend can call:

```python
# In your lab journal backend
import httpx

async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://stt:8000/transcribe",  # 'stt' = docker service name
            files={"file": (filename, audio_bytes, "audio/wav")},
            data={"language": "en", "vad_filter": "true"},
            timeout=60.0,
        )
        return response.json()["text"]
```
