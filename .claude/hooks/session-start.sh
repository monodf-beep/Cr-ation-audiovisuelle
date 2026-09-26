#!/bin/bash
# Outils de rendu vidéo pour les sessions Claude Code sur le web :
# FFmpeg (HyperFrames, 03_etalonnage, 04_montage) et Chrome headless (HyperFrames).
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0

if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get install -y -q ffmpeg >/dev/null 2>&1 \
    || { apt-get update -q >/dev/null 2>&1 && apt-get install -y -q ffmpeg >/dev/null 2>&1; }
fi
HYPERFRAMES_SKIP_SKILLS=1 npx -y hyperframes browser ensure >/dev/null 2>&1 || true
pip install -q yt-dlp imageio-ffmpeg faster-whisper pillow >/dev/null 2>&1 || true
