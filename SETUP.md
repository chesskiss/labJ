# Lab Assistant AI - Setup Guide

## Project Structure

This project implements a voice-activated AI lab assistant with the following structure:

```
lab-assistant-ai/
├── main.py                 # Entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
│
├── audio/                 # Audio processing
│   ├── __init__.py
│   ├── mic_stream.py     # Microphone streaming
│   └── audio_utils.py    # Audio utilities
│
├── stt/                   # Speech-to-text
│   ├── __init__.py
│   ├── transcriber.py    # Transcription engine
│   └── models/           # Local STT models
│
├── nlp/                   # Natural language processing
│   ├── __init__.py
│   ├── parser.py         # Intent parsing
│   ├── agent.py          # Agent logic
│   └── memory.py         # Memory management
│
├── visualization/         # Visualization
│   ├── __init__.py
│   ├── chart_generator.py # Chart generation
│   └── table_builder.py  # Table building
│
├── ui/                    # User interface
│   ├── __init__.py
│   ├── streamlit_app.py  # Streamlit UI
│   └── display.py        # Display handler
│
├── data/                  # Data storage
│   ├── logs/             # Logs and transcripts
│   ├── charts/           # Generated charts
│   └── experiments/      # Experiment data
│
└── tests/                 # Tests
    ├── test_stt.py
    └── test_parser.py
```

## Setup Instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

3. **Install STT models (optional):**
   - For faster-whisper: Models are downloaded automatically on first use
   - For vosk: Download models from https://alphacephei.com/vosk/models and place in `stt/models/`

4. **Run the application:**
   ```bash
   python main.py
   ```

## Current Status

This is a placeholder implementation with:
- ✅ Complete project structure
- ✅ Configuration management
- ✅ Placeholder classes and functions
- ✅ TODO comments for implementation
- ⚠️ Core functionality needs to be implemented

## Next Steps

1. Implement audio capture in `audio/mic_stream.py`
2. Implement STT transcription in `stt/transcriber.py`
3. Implement intent parsing in `nlp/parser.py`
4. Implement LLM integration in `nlp/agent.py`
5. Implement chart generation in `visualization/chart_generator.py`
6. Implement table building in `visualization/table_builder.py`
7. Implement UI display in `ui/display.py`
8. Implement main processing loop in `main.py`

## Notes

- The code uses async/await for non-blocking operations
- Configuration can be loaded from environment variables or YAML files
- The project is designed to work on Windows first, then expand to Android/iOS
- All modules have placeholder implementations with clear TODOs

