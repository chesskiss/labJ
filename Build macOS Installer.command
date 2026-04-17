#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v node >/dev/null 2>&1; then
  echo "[LabJ] Node.js is not installed."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[LabJ] npm is not available."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "[LabJ] Python 3.10+ is required to bundle the desktop runtime."
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "[LabJ] Missing .env in repo root. Create .env before building installer."
  exit 1
fi

cd desktop
npm install
npm run dist:mac

echo "[LabJ] Done. Installer is in desktop/release/"
