#!/usr/bin/env bash
# ── test_stt.sh ──────────────────────────────────────────────────────────────
# Quick test for the faster-whisper STT API.
#
# Usage:
#   ./test_stt.sh                      # generates a test wav and transcribes it
#   ./test_stt.sh /path/to/audio.wav   # transcribes your own file

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
AUDIO_FILE="${1:-}"

echo "═══════════════════════════════════════════════════════"
echo "  Faster-Whisper STT API Tester"
echo "═══════════════════════════════════════════════════════"

# ── 1. Health check ──────────────────────────────────────────────────────────
echo ""
echo "▸ Checking API health..."
HEALTH=$(curl -s "${API_URL}/health")
echo "  ${HEALTH}"

# ── 2. Prepare audio file ────────────────────────────────────────────────────
if [ -z "$AUDIO_FILE" ]; then
    echo ""
    echo "▸ No audio file provided. Generating a test WAV with Python..."

    python3 -c "
import struct, wave, math

# Generate a simple 1-second sine wave (440 Hz) as a test tone
# This won't produce meaningful text - it's just to verify the API works.
# For a real test, record your voice or use an actual audio file.
sample_rate = 16000
duration = 2
frequency = 440
samples = []
for i in range(sample_rate * duration):
    t = i / sample_rate
    sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
    samples.append(struct.pack('<h', sample))

with wave.open('/tmp/test_tone.wav', 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    f.writeframes(b''.join(samples))
print('  Generated /tmp/test_tone.wav (2s sine wave)')
"
    AUDIO_FILE="/tmp/test_tone.wav"
    echo ""
    echo "  ⚠  Note: A sine wave won't produce real text."
    echo "     For a real test, run:  ./test_stt.sh /path/to/your/recording.wav"
fi

# ── 3. Transcribe ────────────────────────────────────────────────────────────
echo ""
echo "▸ Sending '${AUDIO_FILE}' to ${API_URL}/transcribe ..."
echo ""

RESPONSE=$(curl -s -X POST "${API_URL}/transcribe" \
    -F "file=@${AUDIO_FILE}" \
    -F "vad_filter=true" \
    -F "beam_size=5")

echo "── Response ──────────────────────────────────────────"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo "─────────────────────────────────────────────────────"

# ── 4. Quick summary ─────────────────────────────────────────────────────────
TEXT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('text',''))" 2>/dev/null || true)
PROC_TIME=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('processing_time_seconds','?'))" 2>/dev/null || true)
LANG=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('language','?'))" 2>/dev/null || true)

echo ""
echo "▸ Summary:"
echo "  Language detected: ${LANG}"
echo "  Processing time:   ${PROC_TIME}s"
echo "  Transcription:     \"${TEXT}\""
echo ""

# ── 5. Example: test with word timestamps ────────────────────────────────────
echo "▸ Bonus: testing with word_timestamps=true ..."
curl -s -X POST "${API_URL}/transcribe" \
    -F "file=@${AUDIO_FILE}" \
    -F "word_timestamps=true" \
    -F "vad_filter=true" | python3 -m json.tool 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✓ Done! API is working."
echo ""
echo "  Quick test with your own voice:"
echo "    # Record 5 seconds from mic (requires sox/arecord):"
echo "    rec -r 16000 -c 1 my_voice.wav trim 0 5"
echo "    ./test_stt.sh my_voice.wav"
echo "═══════════════════════════════════════════════════════"
