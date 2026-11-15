#!/usr/bin/env bash
# Prépare le paquet à déposer sur Google Drive pour la session cloud :
# seulement les fichiers légers (index, résumés, transcriptions, planches), jamais les vidéos.
#   ./exporter.sh   →  veille-AAAA-MM-JJ.zip dans ce dossier
set -euo pipefail
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
DATE=$(date +%F)
OUT="export_veille"
rm -rf "$OUT" && mkdir -p "$OUT"
for d in donnees/*/; do
  c=$(basename "$d"); mkdir -p "$OUT/$c"
  cp -f "$d"index.csv "$d"resume.md "$OUT/$c/" 2>/dev/null || true
  [ -d "$d"transcriptions ] && cp -r "$d"transcriptions "$OUT/$c/"
  [ -d "$d"planches ] && cp -r "$d"planches "$OUT/$c/"
done
"$PY" -m zipfile -c "veille-$DATE.zip" "$OUT"
rm -rf "$OUT"
echo "Paquet prêt : $(pwd)/veille-$DATE.zip  → dépose-le dans Google Drive, dossier « veille-instagram »."
