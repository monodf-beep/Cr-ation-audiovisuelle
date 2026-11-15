#!/usr/bin/env bash
# Complète les compteurs que gallery-dl ne donne pas (commentaires, vues) via yt-dlp,
# sans retélécharger les médias. Optionnel : l'indexeur fonctionne sans.
#
#   ./stats.sh donnees/<compte>
# Prérequis : brew install yt-dlp   (ou pipx install yt-dlp)
set -euo pipefail
cd "$(dirname "$0")"
D="${1:?usage: ./stats.sh donnees/<compte>}"
NAVIGATEUR="${NAVIGATEUR:-firefox}"
mkdir -p "$D/stats"

ls "$D" | sed -nE 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}_(.+)_[0-9]+\..*$/\1/p' | sort -u | while read -r sc; do
  [ -f "$D/stats/$sc.info.json" ] && continue
  yt-dlp --cookies-from-browser "$NAVIGATEUR" --skip-download --write-info-json \
    --no-warnings -q -o "$D/stats/$sc.%(ext)s" "https://www.instagram.com/p/$sc/" \
    || { echo "!! $sc : échec (arrêt par prudence)"; exit 1; }
  sleep $((4 + RANDOM % 6))
done
