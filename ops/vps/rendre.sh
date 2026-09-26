#!/usr/bin/env bash
# Rendu d'un montage sur le VPS, en arriere-plan : il continue meme si le terminal se ferme ou si la
# connexion saute. Met le depot a jour, fabrique les medias hors depot, rend, lance les metriques.
#
#   sudo bash /srv/studio/depot/ops/vps/rendre.sh 10_cern
#
# Suivre :  tail -f /srv/studio/depot/10_cern/renders/rendu.log      (Ctrl+C arrete seulement l'affichage)
# Etat   :  systemctl status studio-rendu
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Lancer avec sudo."; exit 1; }
source /etc/studio/studio.env
PROJET=${1:-$PROJET}
[ -d "$DEPOT/$PROJET" ] || { echo "Projet introuvable : $DEPOT/$PROJET"; exit 1; }
if systemctl is-active --quiet studio-rendu; then echo "Un rendu tourne deja : tail -f $DEPOT/$PROJET/renders/rendu.log"; exit 1; fi
systemctl reset-failed studio-rendu 2>/dev/null || true
mkdir -p "$DEPOT/$PROJET/renders" && chown studio:studio "$DEPOT/$PROJET/renders"
JOURNAL="$DEPOT/$PROJET/renders/rendu.log"
# Nom du fichier rendu : 2e argument, sinon cern-reportage.mp4 pour 10_cern, <projet>.mp4 pour les autres.
SORTIE=${2:-$([ "$PROJET" = 10_cern ] && echo cern-reportage.mp4 || echo "$PROJET.mp4")}

systemd-run --unit=studio-rendu --description="Rendu $PROJET" --property=KillMode=control-group \
  /bin/bash -c "
    exec >'$JOURNAL' 2>&1
    echo \"== \$(date '+%d/%m %H:%M') rendu de $PROJET\"
    systemctl stop studio-hf
    trap 'systemctl start studio-hf' EXIT
    cd '$DEPOT' && sudo -u studio git fetch -q origin '$BRANCHE' && sudo -u studio git reset -q --hard 'origin/$BRANCHE'
    cd '$DEPOT/$PROJET'
    echo '== medias'; sudo -u studio -H bash tools/preparer-medias.sh || { echo 'MEDIAS EN ECHEC'; exit 1; }
    echo '== rendu'; sudo -u studio -H npx --yes $HF render -o renders/$SORTIE . || { echo 'RENDU EN ECHEC'; exit 1; }
    echo '== metriques'; cd '$DEPOT' && sudo -u studio -H python3 04_montage/metriques.py '$PROJET' || true
    echo \"== termine \$(date '+%H:%M') : $PROJET/renders/$SORTIE (copie dans Drive sous 3 minutes)\"
  "
echo "Rendu lance en arriere-plan. Vous pouvez fermer le terminal."
echo "Suivre : tail -f $JOURNAL"
