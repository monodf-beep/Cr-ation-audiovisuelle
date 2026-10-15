#!/usr/bin/env bash
# Traitement de la voix off montée -> assets/voix-off.wav. Chaîne reprise de 10_cern/tools/voix-finale.sh
# (04_montage/BONNES-PRATIQUES.md, « Voix ») : voix proche et naturelle, aucun effet voyant.
#   accélération (montage.json, atempo garde la hauteur) -> passe-haut 80 Hz -> réduction de bruit légère
#   -> -2 dB à 250 Hz -> +2,5 dB à 3,5 kHz -> +1 dB à 10 kHz -> de-esser léger -> compression douce 2:1 -> -16 LUFS (v4 : traitement allégé, plus naturel).
# Le niveau final se règle au mixage (tools/bande-son.py).
# Usage (dans 15_decidia/) : bash tools/voix-finale.sh
set -euo pipefail
cd "$(dirname "$0")/.."
VITESSE=$(python3 -c 'import json; print(json.load(open("montage.json"))["vitesse"])')
CHAINE="atempo=$VITESSE,highpass=f=80,afftdn=nr=4:nf=-45,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1.0:g=2.5,equalizer=f=10000:t=h:w=0.7:g=1,deesser=i=0.2,acompressor=threshold=-22dB:ratio=2:attack=12:release=180:makeup=1.5,loudnorm=I=-16:TP=-1.5:LRA=9"
ffmpeg -v error -y -i voix-off/voix-montee.wav -af "$CHAINE" -ar 48000 -ac 2 assets/voix-off.wav
ffmpeg -hide_banner -i assets/voix-off.wav -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1
