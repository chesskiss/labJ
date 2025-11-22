#!/usr/bin/env python3
"""
One-shot launcher for backend + frontend via Docker Compose.
Works on macOS/Windows/Linux (Docker Desktop or Docker Engine + Compose plugin required).

Usage:
    python run_docker.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def find_compose_command() -> list[str]:
    """
    Return the docker compose command to use.
    Prefers `docker compose` (v2 plugin), falls back to `docker-compose` (v1).
    """
    candidates = [
        ["docker", "compose"],
        ["docker-compose"],
    ]
    for cmd in candidates:
        try:
            subprocess.run(cmd + ["version"], capture_output=True, check=True)
            return cmd
        except Exception:
            continue
    return []


def main() -> int:
    cmd = find_compose_command()
    if not cmd:
        print("❌ Docker Compose not found. Install Docker Desktop or the Compose plugin and retry.", file=sys.stderr)
        return 1

    print(f"▶️  Using compose command: {' '.join(cmd)}")
    print("▶️  Building and starting services (frontend + backend)...")

    try:
        subprocess.run(cmd + ["up", "--build"], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ docker compose failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        print("❌ docker compose command not found. Ensure Docker is installed and in PATH.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
