# ── Faster-Whisper STT Service ────────────────────────────────────────────────
# CPU-optimized build. For GPU, swap base image to nvidia/cuda and use float16.

FROM python:3.11-slim

# Prevent interactive prompts and set locale
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install minimal system deps (PyAV handles audio decoding, no ffmpeg needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# ── Configuration defaults ───────────────────────────────────────────────────
# Override these with docker run -e or docker-compose environment
ENV WHISPER_MODEL=base \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    WHISPER_WORKERS=2

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
