#!/usr/bin/env bash
# Traitement de la voix off montee -> assets/voix-off.mp3 (docs : 04_montage/BONNES-PRATIQUES.md, « Voix »).
# Style reportage sobre, voix proche et naturelle, pas d'effet voyant :
#   passe-haut 80 Hz (souffle, pied de micro) -> reduction de bruit legere -> -2 dB a 250 Hz (boue)
#   -> +2,5 dB a 3,5 kHz (presence, intelligibilite sur telephone) -> +1 dB a 10 kHz (air)
#   -> de-esser -> compression douce 3:1 -> -16 LUFS, crete -1,5 dB (norme des reseaux sociaux).
# Usage (dans 10_cern/) : bash tools/voix-finale.sh [voix-off/voix-montee.wav]
set -euo pipefail
cd "$(dirname "$0")/.."
SOURCE=${1:-voix-off/voix-montee.wav}
CHAINE="highpass=f=80,afftdn=nr=8:nf=-45,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1.0:g=2.5,equalizer=f=10000:t=h:w=0.7:g=1,deesser=i=0.35,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=9"
ffmpeg -v error -y -i "$SOURCE" -af "$CHAINE" -ar 48000 -b:a 192k assets/voix-off.mp3
ffmpeg -hide_banner -i assets/voix-off.mp3 -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
