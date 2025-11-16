# env_config.py

"""
Global environment and path configuration for the project.
Use this file to define constants like workspace paths, cache directories,
and any shared global configuration that multiple modules depend on.
"""

from pathlib import Path

# Base project directory
ROOT = Path(__file__).resolve().parent

# stt and audio config
STT_SAMPLE_RATE = 16000
STT_MODEL_SIZE = "tiny"
STT_DURATION = 50 # seconds - Sleep time for the transcriber. Only for the blocking test in __main__
CHUNK_SIZE = 4096

# streaming STT tuning
STT_WINDOW_SEC = 3.0      # how much audio per Whisper call
STT_OVERLAP_SEC = 0.7     # how much context to keep between calls

# noise / text filters
STT_MIN_WINDOW_RMS = 0.005      # tune this; start small
STT_MIN_TEXT_CHARS = 5          # min length to accept as "real" text unless it's a command

# Data
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "journal.sqlite"

# # Workspace for storing audio, transcriptions, logs, etc.
# WORKDIR = ROOT / "workspace"
# WORKDIR.mkdir(parents=True, exist_ok=True)

# # Model cache or data directory (if needed later)
# MODEL_CACHE_DIR = WORKDIR / "models"
# MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
