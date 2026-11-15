#!/usr/bin/env bash
# Télécharge les dernières publications des comptes listés dans concurrents.txt.
# À lancer sur TON ordinateur, avec Firefox connecté à Instagram (compte secondaire conseillé).
#
#   ./telecharger.sh            # 30 dernières publications par compte, puis seulement les nouvelles
#   ./telecharger.sh 60         # 60 dernières au premier passage
#   NAVIGATEUR=chrome ./telecharger.sh
#
# Prérequis : pipx install "gallery-dl[video]"   (ou brew install gallery-dl) + ffmpeg
set -euo pipefail
cd "$(dirname "$0")"

N="${1:-30}"
NAVIGATEUR="${NAVIGATEUR:-firefox}"
ARCHIVE="donnees/.archive.sqlite3"
mkdir -p donnees

command -v gallery-dl >/dev/null || { echo "gallery-dl absent : pipx install 'gallery-dl[video]'"; exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg absent : brew install ffmpeg"; exit 1; }

grep -vE '^\s*(#|$)' concurrents.txt | while read -r compte _; do
  echo "== $compte"
  if [ -d "donnees/$compte" ]; then
    plage=(-A 5)                    # incrémental : s'arrête après 5 publications déjà connues
  else
    plage=(--post-range "1-$N")
  fi
  # Un compte à la fois, pauses gallery-dl par défaut + 2-5 s entre fichiers.
  # Au premier 429 / checkpoint : on arrête tout, on va valider le compte dans le navigateur.
  if ! gallery-dl \
      --cookies-from-browser "$NAVIGATEUR" \
      -o include=posts,reels \
      -o 'directory=["{username}"]' \
      -f '{post_date:%Y-%m-%d}_{post_shortcode}_{num:>02}.{extension}' \
      --write-metadata \
      --sleep 2-5 \
      --download-archive "$ARCHIVE" \
      "${plage[@]}" \
      -d donnees \
      "https://www.instagram.com/$compte/"; then
    echo "!! Erreur sur $compte. Si c'est un 429 ou un checkpoint : STOP, attendre 24 h."
    exit 1
  fi
  sleep $((20 + RANDOM % 40))       # pause entre deux comptes
done

echo "Terminé. Étape suivante : python3 traiter.py donnees/<compte> puis python3 indexer.py donnees/<compte>"
