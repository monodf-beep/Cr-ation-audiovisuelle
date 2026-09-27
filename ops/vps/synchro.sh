#!/usr/bin/env bash
# Synchronisation du VPS, lancee toutes les 3 minutes par studio-synchro.timer.
#  1. GitHub -> VPS : le code des montages (avance rapide seulement, jamais d'ecrasement).
#  2. Drive -> VPS : les medias (videos, images, sons, polices), copies a la meme place que dans le depot.
#  3. VPS -> Drive : les rendus (renders/), les prises de voix off (voix-off/), la bibliotheque de montage.
# Rien n'est jamais supprime d'un cote ou de l'autre : les copies ne font qu'ajouter ou mettre a jour.
set -uo pipefail
# Reglages du studio : seulement nos 5 variables, lues sans executer le fichier (d'autres outils du VPS y
# ajoutent leurs propres lignes, parfois non valides pour bash).
while IFS='=' read -r cle valeur; do
  case "$cle" in DEPOT|PROJET|DRIVE|BRANCHE|HF) export "$cle=$valeur" ;; esac
done < /etc/studio/studio.env

cd "$DEPOT" || exit 1
# Le VPS est une copie de GitHub : les modifications se font dans le depot (par Claude), pas sur le VPS.
# Le Studio HyperFrames reecrit index.html quand il l'ouvre (reperes techniques) : ces reecritures sont
# ecartees a chaque mise a jour, sinon git refuserait de recuperer la nouvelle version.
if git fetch -q origin "$BRANCHE" && [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$BRANCHE")" ]; then
  git reset -q --hard "origin/$BRANCHE" || echo "git : mise a jour impossible, a regarder"
fi

# Google Drive accepte deux dossiers du meme nom cote a cote (glisser un dossier deja present en cree
# un second) : on les fusionne avant chaque copie, sans rien supprimer d'autre.
# (rclone fusionne toujours les dossiers en double ; le mode « skip » laisse les fichiers en double tels quels.)
rclone dedupe --dedupe-mode skip "$DRIVE" -q || echo "rclone : fusion des dossiers en double en erreur"

MEDIAS='*.{mp4,mov,m4v,webm,wav,mp3,m4a,aac,flac,ogg,jpg,jpeg,png,webp,gif,svg,woff,woff2,otf,ttf}'
# Regles de filtre dans l'ordre (rclone refuse de melanger --include et --exclude).
rclone copy "$DRIVE" "$DEPOT" --update --filter '- node_modules/**' --filter '- .git/**' --filter "+ $MEDIAS" --filter '- *' \
  --drive-skip-gdocs --fast-list -q || echo "rclone : Drive -> VPS en erreur"

# Bibliotheque de montage : sons candidats telecharges a la source (une fois), choix et ajouts copies dans Drive.
python3 "$DEPOT/bibliotheque/installer-sons.py" || echo "bibliotheque : installation des sons en erreur"
for sous in donnees fichiers/televerses; do
  [ -d "$DEPOT/bibliotheque/$sous" ] && rclone copy "$DEPOT/bibliotheque/$sous" "$DRIVE/bibliotheque/$sous" --update -q || true
done

# Prises filmees : version eclaircie et verticale, a cote de la prise brute.
DEPOT="$DEPOT" "$DEPOT/ops/vps/traiter-prises.sh" || echo "traitement des prises en erreur"

for projet in "$DEPOT"/*/; do
  p=$(basename "$projet")
  for sous in renders voix-off; do
    [ -d "$projet/$sous" ] && rclone copy "$projet/$sous" "$DRIVE/$p/$sous" --update -q || true
  done
done
