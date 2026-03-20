# STT Module (Faster-Whisper)


## Quick Start (Docker Compose)

Run from `stt/`:

```bash
colima start
docker compose up --build -d

# For orchestrator
curl -X POST http://localhost:8000/mic/start \
  -H "Content-Type: application/json" \
  -d '{"language":"en","stt_api_url":"http://localhost:8001","silence_duration":0.8,"silence_threshold":0.01}'
```

Stop:

```bash
#Mic:
url -X POST http://localhost:8000/mic/stop 

# Container
docker compose down
```



This module has two pieces:
- `app.py`: HTTP STT service (`/health`, `/transcribe`) for audio file/chunk transcription.
- `stt.py`: live microphone client (`STTClient`) that captures audio in real time and sends chunks to `/transcribe`.


## Port Mapping

`docker-compose.yml` maps host `8001` to container `8000` (`8001:8000`).

Use from host:
- `http://localhost:8001/health`
- `http://localhost:8001/transcribe`

## API Transcription (File/Chunk)

```bash
# Basic
curl -X POST "http://localhost:8001/transcribe" \
  -F "file=@audio.wav"

# With params
curl -X POST "http://localhost:8001/transcribe?language=en&word_timestamps=true&vad_filter=true" \
  -F "file=@audio.wav"
```

`POST /transcribe` parameters:
- `file` (required)
- `language` (optional)
- `beam_size` (optional)
- `word_timestamps` (optional)
- `vad_filter` (optional)
- `initial_prompt` (optional)

## Live Mic Transcription (`stt.py`)

`stt.py` is the live path. It is not a websocket endpoint; it is a local mic client that:
1. captures audio from microphone,
2. detects pauses (VAD-like threshold logic),
3. sends each speech segment to `/transcribe`,
4. emits transcripts via callback.

### Run live demo

From repo root:

```bash
uv run python -m stt.test-module
```

### Use client directly

```python
from stt.stt import STTClient


def on_text(text: str) -> None:
    print(f"segment: {text}")


client = STTClient(
    on_transcription=on_text,
    api_url="http://localhost:8001/transcribe",
    language="en",
)

client.start()
input("Recording... press Enter to stop\n")
full_text = client.stop()
print(full_text)
```

## Troubleshooting

```bash
# Container/service state
docker compose ps
docker compose logs -f stt

# Reachability
curl http://localhost:8001/health
open http://localhost:8001/docs
```

If live mic capture fails, verify local audio permissions/device access for Python (`sounddevice`) on your OS.

## Colima Memory Cleanup

If Docker/Colima memory is exhausted and you want to fully reset VM state:

```bash
# Stop services first
docker compose down

# Stop Colima VM
colima stop

# Delete Colima VM (frees memory/disk, removes cached images/volumes in that VM)
colima delete
```

Then re-create:

```bash
colima start
docker compose up --build -d
```
