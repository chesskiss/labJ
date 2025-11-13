# env_config.py

"""
Global environment and path configuration for the project.
Use this file to define constants like workspace paths, cache directories,
and any shared global configuration that multiple modules depend on.
"""

from pathlib import Path

# Base project directory
ROOT = Path(__file__).resolve().parent

# # Workspace for storing audio, transcriptions, logs, etc.
# WORKDIR = ROOT / "workspace"
# WORKDIR.mkdir(parents=True, exist_ok=True)

# # Model cache or data directory (if needed later)
# MODEL_CACHE_DIR = WORKDIR / "models"
# MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
