#!/usr/bin/env bash
# Synchronisation du VPS, lancee toutes les 3 minutes par studio-synchro.timer.
#  1. GitHub -> VPS : le code des montages (avance rapide seulement, jamais d'ecrasement).
#  2. Drive -> VPS : les medias (videos, images, sons, polices), copies a la meme place que dans le depot.
#  3. VPS -> Drive : les rendus (renders/) et les prises de voix off (voix-off/).
# Rien n'est jamais supprime d'un cote ou de l'autre : les copies ne font qu'ajouter ou mettre a jour.
set -uo pipefail
source /etc/studio/studio.env

cd "$DEPOT" || exit 1
# Le VPS est une copie de GitHub : les modifications se font dans le depot (par Claude), pas sur le VPS.
# Le Studio HyperFrames reecrit index.html quand il l'ouvre (reperes techniques) : ces reecritures sont
# ecartees a chaque mise a jour, sinon git refuserait de recuperer la nouvelle version.
if git fetch -q origin "$BRANCHE" && [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$BRANCHE")" ]; then
  git reset -q --hard "origin/$BRANCHE" || echo "git : mise a jour impossible, a regarder"
fi

# Google Drive accepte deux dossiers du meme nom cote a cote (glisser un dossier deja present en cree
# un second) : on les fusionne avant chaque copie, sans rien supprimer d'autre.
rclone dedupe --dedupe-mode merge "$DRIVE" -q || echo "rclone : fusion des dossiers en double en erreur"

MEDIAS='*.{mp4,mov,m4v,webm,wav,mp3,m4a,aac,flac,ogg,jpg,jpeg,png,webp,gif,svg,woff,woff2,otf,ttf}'
rclone copy "$DRIVE" "$DEPOT" --update --include "$MEDIAS" --exclude 'node_modules/**' --exclude '.git/**' \
  --drive-skip-gdocs --fast-list -q || echo "rclone : Drive -> VPS en erreur"

# Prises filmees : version eclaircie et verticale, a cote de la prise brute.
DEPOT="$DEPOT" "$DEPOT/ops/vps/traiter-prises.sh" || echo "traitement des prises en erreur"

for projet in "$DEPOT"/*/; do
  p=$(basename "$projet")
  for sous in renders voix-off; do
    [ -d "$projet/$sous" ] && rclone copy "$projet/$sous" "$DRIVE/$p/$sous" --update -q || true
  done
done
