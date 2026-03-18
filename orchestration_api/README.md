# Orchestration API

Thin backend integration layer that wires:

`text/audio -> parser -> validator -> executor -> optional NoteCapture DB write`

`/process_text` and `/process_audio` use an LLM parser first when configured, then
fallback to deterministic parsing if the LLM key is missing or the call fails.

## Run

```bash
uv run uvicorn orchestration_api.app:app --reload --host 0.0.0.0 --port 8000
```

Optional LLM env:

```bash
# Optional overrides
export LLM_MODEL=llama-3.3-70b-versatile
export LLM_BASE_URL=https://api.groq.com/openai/v1
```

## Endpoints

- `GET /health`
- `POST /process_text`
- `POST /process_audio`
- `GET /runtime_state`
- `POST /mic/start`
- `POST /mic/stop`
- `GET /mic/status`
- `GET /mic/events`

## `process_text` Examples

### 1) Note capture (persists through journal tool)

```bash
curl -X POST http://localhost:8000/process_text \
  -H "Content-Type: application/json" \
  -d '{"text":"sample 4 became cloudy after heating"}'
```

Expected high-level result:
- `parsed.kind = note_capture`
- `validation.is_valid = true`
- `execution.status = succeeded`
- `execution.final_output.entry_id` present

### 2) Action plan flow

```bash
curl -X POST http://localhost:8000/process_text \
  -H "Content-Type: application/json" \
  -d '{"text":"take result from calculator 1, add 2, convert liters to mL, write to journal"}'
```

Expected high-level result:
- `parsed.kind = action_plan`
- `validation.is_executable = true`
- `execution.status` depends on runtime state (can be `succeeded` or `failed`)

## STT Integration

`POST /process_audio` forwards audio to STT (`STT_API_URL`, default `http://localhost:8001/transcribe`), then runs the same pipeline on returned transcript text.

Example:

```bash
curl -X POST "http://localhost:8000/process_audio?language=en&vad_filter=true" \
  -F "file=@stt/test.wav"
```

## Continuous Mic Flow

Start a mic session where pause-delimited STT transcripts are continuously sent through:
`parse -> validate -> execute`.

```bash
curl -X POST http://localhost:8000/mic/start \
  -H "Content-Type: application/json" \
  -d '{"language":"en","stt_api_url":"http://localhost:8001","silence_duration":0.8,"silence_threshold":0.01}'
```

Check state:

```bash
curl http://localhost:8000/mic/status
curl http://localhost:8000/mic/events
```

Stop:

```bash
curl -X POST http://localhost:8000/mic/stop
```
