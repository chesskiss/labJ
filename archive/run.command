#!/usr/bin/env bash
# run_all.command
# - Checks/installs Python3 and Node (via Homebrew if available)
# - Activates/creates venv, installs Python deps (PortAudio/libsndfile via brew)
# - Starts backend (uvicorn) + frontend (npm dev)
# - Opens browser at http://localhost:5173

set -euo pipefail

cd "$(dirname "$0")"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  # Kill background jobs if still running
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "=== Checking python3 ==="
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found."
  if command -v brew >/dev/null 2>&1; then
    echo "Installing python via Homebrew..."
    brew install python
  else
    echo "ERROR: Homebrew is not installed. Please install Homebrew from https://brew.sh and rerun this script."
    exit 1
  fi
else
  echo "python3 is installed."
fi

echo "=== Checking Node.js ==="
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js not found."
  if command -v brew >/dev/null 2>&1; then
    echo "Installing Node.js via Homebrew..."
    brew install node
  else
    echo "ERROR: Homebrew is not installed. Please install Homebrew from https://brew.sh and rerun this script."
    exit 1
  fi
else
  echo "Node.js is installed."
fi

echo "=== Checking audio libs (portaudio, libsndfile) ==="
if command -v brew >/dev/null 2>&1; then
  brew list portaudio >/dev/null 2>&1 || brew install portaudio
  brew list libsndfile >/dev/null 2>&1 || brew install libsndfile
else
  echo "WARNING: Homebrew not found, required audio libs may be missing (portaudio, libsndfile). Install brew from https://brew.sh if STT fails."
fi

echo "=== Ensuring virtualenv exists ==="
if [ ! -d ".vlab" ]; then
  echo "Creating virtualenv..."
  python3 -m venv .vlab
fi

echo "Activating virtualenv..."
# shellcheck disable=SC1091
source .vlab/bin/activate

echo "Installing Python requirements..."
python -m pip install -r requirements.txt

echo "=== Starting backend (uvicorn) ==="
# run in background
python -m uvicorn agents.controller:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "=== Starting frontend (npm dev) ==="
cd ui
# Skip npm install if node_modules already exists
if [ ! -d "node_modules" ]; then
  npm install
else
  echo "node_modules present, skipping npm install (delete node_modules to force reinstall)."
fi
npm run dev &
FRONTEND_PID=$!

echo "Opening browser at http://localhost:5173 ..."
open "http://localhost:5173"

wait
