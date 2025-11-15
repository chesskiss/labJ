lab-assistant-ai/
│
├── main.py                        # Entry point: orchestrates the agent flow
├── requirements.txt              # Python dependencies
├── config.py                     # Centralized settings (paths, model config)
│
├── audio/
│   ├── __init__.py
│   ├── mic_stream.py             # Captures live audio using sounddevice
│   └── audio_utils.py            # Optional filters, buffers
│
├── stt/
│   ├── __init__.py
│   ├── transcriber.py            # Wraps faster-whisper or vosk
│   └── models/                   # (Optional) Local model storage
│
├── nlp/
│   ├── __init__.py
│   ├── parser.py                 # Extracts intent: chart/table/notes
│   ├── agent.py                  # LLM or rule-based agent logic
│   └── memory.py                 # Stores/retrieves past sessions (FAISS/Chroma later)
│
├── visualization/
│   ├── __init__.py
│   ├── table_builder.py         # From parsed instructions to pandas DataFrame
│   ├── chart_generator.py       # Uses matplotlib/plotly or calls QuickChart
│
├── ui/
│   ├── __init__.py
│   ├── streamlit_app.py         # Optional UI layer for preview
│   └── display.py               # Show chart/table/image in window
│
├── data/
│   ├── logs/                     # Transcripts, notes, etc.
│   ├── charts/                   # Exported visualizations
│   └── experiments/             # Structured experiment data
│
└── tests/
    ├── test_stt.py
    ├── test_parser.py
    └── ...

High-level architecture / hierarchy scheme
+--------------------+
|  MicrophoneStream  |  (audio/mic_stream.py)
+---------+----------+
          |
          v
+--------------------+          +-------------------------+
|    Controller      |          |   TranscriptRepository  |
| (agents/controller)|--------->| (storage/sqlite_...py)  |
+----+-------+-------+          +-------------------------+
     |       |
     |       | text, action
     |       v
     |  +-----------------+
     |  |   Transcriber   |  (stt/transcriber.py)
     |  +--------+--------+
     |           |
     |           | text
     |           v
     |  +-----------------+
     |  | TriggerEvaluator|  (stt/trigger.py)
     |  +-----------------+
     |
     |  (state: is_transcribing, session_id)
     |
GUI <--------------------------------------------------> DB (journal.sqlite)
