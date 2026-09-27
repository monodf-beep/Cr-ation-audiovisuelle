#!/usr/bin/env bash
# Rendu demande depuis la page « Rendus » du studio (/enregistrement/rendu/), sans terminal.
# La page depose <projet>/renders/demande-rendu.json ; synchro.sh (toutes les 3 minutes, utilisateur studio)
# appelle ce script, qui fabrique les medias, rend, lance les metriques et ecrit l'etat pour la page.
# Usage : bash ops/vps/rendu-auto.sh <projet>
set -uo pipefail
DEPOT=${DEPOT:-/srv/studio/depot}
HF=${HF:-hyperframes@0.8.75}
PROJET=$1
DOSSIER="$DEPOT/$PROJET/renders"
ETAT="$DOSSIER/etat-rendu.json"
JOURNAL="$DOSSIER/rendu.log"
SORTIE=$([ "$PROJET" = 10_cern ] && echo cern-reportage.mp4 || echo "$PROJET.mp4")
maintenant() { date '+%Y-%m-%dT%H:%M:%S%z'; }
etat() { printf '{"etat":"%s","debut":"%s","fin":"%s","fichier":"%s","message":"%s"}\n' "$1" "$DEBUT" "${2:-}" "$SORTIE" "${3:-}" > "$ETAT"; }

mkdir -p "$DOSSIER"
rm -f "$DOSSIER/demande-rendu.json"
DEBUT=$(maintenant)
etat "en cours"
{
  echo "== $(date '+%d/%m %H:%M') rendu de $PROJET (demande depuis le studio)"
  cd "$DEPOT/$PROJET" || exit 1
  if [ -f tools/preparer-medias.sh ]; then
    echo "== medias"; bash tools/preparer-medias.sh || { echo "MEDIAS EN ECHEC"; exit 2; }
  fi
  echo "== rendu"; npx --yes "$HF" render -o "renders/$SORTIE" . || { echo "RENDU EN ECHEC"; exit 3; }
  echo "== metriques"; (cd "$DEPOT" && python3 04_montage/metriques.py "$PROJET") || true
  echo "== termine $(date '+%H:%M')"
} > "$JOURNAL" 2>&1
code=$?
case $code in
  0) etat "termine" "$(maintenant)" ;;
  2) etat "echec" "$(maintenant)" "preparation des medias" ;;
  *) etat "echec" "$(maintenant)" "rendu" ;;
esac
exit 0
