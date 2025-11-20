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


ui/
  src/
    main.tsx          ← bootstraps React
    App.tsx           ← top-level app

    types.ts          ← shared data types (Session, Block, etc.)

    api/
      client.ts       ← low-level HTTP wrapper (GET/POST)
      sessions.ts     ← functions to call /sessions + /notebook
      commands.ts     ← function to call /commands

    components/
      layout/
        Layout.tsx        ← main 3-column layout (left, center, right)
        LeftSidebar.tsx   ← sessions + favorites + search
        RightPanel.tsx    ← filters, toggles, “Ask assistant” input

      notebook/
        NotebookView.tsx  ← renders all NotebookSession in a scroll
        SessionHeader.tsx ← title + divider for each session block
        TiptapEditor.tsx  ← editable content area (continuous document)

      console/
        CommandConsole.tsx ← bottom-right command input (text → /commands)

-----------------------------------------------------

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



# Debug
## Cache
logger.info("load_cache_from_db: %d sessions", len(sessions))
add_log_block(f"cache loaded: {len(sessions)} sessions")

## Endpoints hit
logger.info("GET /sessions")
add_log_block("GET /sessions")

logger.info("GET /notebook")
add_log_block("GET /notebook")

## Commands received
logger.info(f"POST /commands: {req.text!r}")
add_log_block(f"POST /commands: {req.text!r}")

add_log_block(f"NEW_SESSION created: {session_id} title={title}")
add_log_block(f"APPEND_NOTE to session_id={session_id}")


# Context prompt for gpt
Some context for the project - the goal is to create an AI lab journal + assistant that will be able to pull information from datasets, generate tables and graph, and even write in the journal via voice, hands-free, commands. 

To start, I want to only enable writing with voice - STT. 
Alls the componenets are ready, but the transcriber is still not fully connected to the tyopescript ui