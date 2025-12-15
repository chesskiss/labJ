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
## Setup instructions - Alpha users (Docker)

### Windows:

1. Unzip folder
2. Right-click → “Run with PowerShell” on run_all.ps1
!! If that doesn't work, enable double click -
- Open PowerShell
- run: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
- Type Y and press Enter


### MacOS

1. Unzip folder
2. Open Terminal
3. Run:
cd "<PATH_TO_THE_FOLDER>"
chmod +x run.command
4. Double click on run.command


### With Docker - current code breaks with mic
- Windows
1. Go to Windows PowerShell and run:
winget install -e --id Docker.DockerDesktop

2. Restart windows

3. Unzip folder. 

4. Copy the path to the file

5. Go to Windows PowerShell and run (Replace <PATH TO FOLDER> with the path u copied in step 4!):
cd <PATH TO FOLDER>
docker compose up --build

6. On your browser, go to:
http://localhost:5173


- Mac
1. Unzip folder

2. Copy the path to the file

3. Go to terminal and run (Replace <PATH TO FOLDER> with the path u copied in step 4!):
cd <PATH TO FOLDER>
brew install docker docker-compose colima
colima start
docker compose up --build

4. On your browser, go to:
http://localhost:5173



## Setup Instructions - Developers

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   cd ui && npm install #brew install node on MacOS if npm not found
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
   uvicorn agents.controller:app --reload --host 0.0.0.0 --port 8000 #backend
   cd ui && npm run dev # frontend (run from root)
   ``` 

### Prep to send:
zip -r lab_jarvis.zip labJ \
  -x 'labJ/.git/*' 'labJ/.DS_Store' 'labJ/**/.DS_Store' \
  -x 'labJ/.vlab/*' 'labJ/.venv/*' \
  -x 'labJ/**/__pycache__/*' 'labJ/.pytest_cache/*' 'labJ/.mypy_cache/*' 'labJ/.ruff_cache/*' \
  -x 'labJ/node_modules/*' 'labJ/ui/node_modules/*' \
  -x 'labJ/dist/*' 'labJ/ui/dist/*'



## Notes

- The code uses async/await for non-blocking operations
- Configuration can be loaded from environment variables or YAML files
- The project is designed to work on Windows first, then expand to Android/iOS
- All modules have placeholder implementations with clear TODOs

