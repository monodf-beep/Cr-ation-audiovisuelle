#!/usr/bin/env bash
# Fabrique les medias du montage qui ne sont pas dans le depot (depot public : pas de videos ni de musique).
# A lancer dans 10_cern/, ici ou sur le VPS :  bash tools/preparer-medias.sh
#   assets/face-voix.mp4        image de la prise filmee, montee comme la voix (tools/face-voix.py)
#   assets/article-nosalpes.jpg capture de l'article de Nos Alpes (haut de page, 1080 px de large)
#   assets/musique.mp3          musique de fond : basse sous la voix, remonte sur le carton final
#   assets/effets.mp3           habillage sonore (tools/habillage-sonore.py)
set -euo pipefail
cd "$(dirname "$0")/.."

PRISE=${PRISE:-voix-off/cern-reperes-2026-09-26_17h32m13.webm}
ARTICLE=https://nosalpes.eu/fr/2026/05/15/grand-geneve-un-projet-culturel-transfrontalier-dici-2027/
# Musique : « Curiosity » de Diego Nava (Mixkit, licence libre, sans attribution), validee par Franck
# (04_montage/bibliotheque.json). Changer l'adresse pour une autre piste.
MUSIQUE=${MUSIQUE:-https://assets.mixkit.co/music/480/480.mp3}
DUREE=88.5      # duree du montage (index.html)
FIN_VOIX=78.0   # la voix s'arrete : la musique remonte

# Videos du montage : une image cle par seconde, sinon le rendu se fige en cherchant une image (avertissement
# « sparse keyframes » de HyperFrames). Reencodees une fois, sur place.
for v in assets/affiche-animee.mp4 assets/exterieur.mp4 assets/interieur-lent.mp4 assets/interieur.mp4; do
  [ -f "$v" ] || continue
  ecart=$(ffprobe -v error -select_streams v -skip_frame nokey -show_entries frame=pts_time -of csv=p=0 "$v" \
    | awk 'NR>1 && $1-p>m {m=$1-p} {p=$1} END {print (m>1.1)}')
  if [ "$ecart" = 1 ]; then
    echo "images cles : $v"
    ffmpeg -v error -y -i "$v" -c:v libx264 -crf 18 -preset medium -r 30 -g 30 -keyint_min 30 -pix_fmt yuv420p -movflags +faststart -an "$v.tmp.mp4" && mv "$v.tmp.mp4" "$v"
  fi
done

if [ ! -f assets/face-voix.mp4 ] || [ "${FORCER:-}" = 1 ]; then
  [ -f voix-off/voix-montee.json ] || python3 tools/couper-voix.py "${PRISE%.*}.wav" voix-off/voix-montee.wav voix-off/voix-montee.json
  python3 tools/face-voix.py "$PRISE" voix-off/voix-montee.json assets/face-voix.mp4
fi

if [ ! -f assets/article-nosalpes.jpg ] || [ "${FORCER:-}" = 1 ]; then
  tmp=$(mktemp -d)
  # Capture pleine page a 540 px de large (x2), comme sur un telephone, puis le haut de l'article.
  npx --yes playwright@1.56.1 screenshot --full-page --viewport-size=540,960 --device="Pixel 7" --wait-for-timeout=2000 "$ARTICLE" "$tmp/page.png" \
    || { npx --yes playwright@1.56.1 install chromium && npx --yes playwright@1.56.1 screenshot --full-page --device="Pixel 7" --wait-for-timeout=2000 "$ARTICLE" "$tmp/page.png"; }
  ffmpeg -v error -y -i "$tmp/page.png" -vf "scale=1080:-1,crop=1080:4000:0:0" -q:v 3 assets/article-nosalpes.jpg
  rm -rf "$tmp"
fi

if [ ! -f assets/musique.mp3 ] || [ "${FORCER:-}" = 1 ]; then
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/source.mp3" "$MUSIQUE"
  # Environ -32 LUFS sous la voix (-16), puis -24 sur le carton final ; fondus d'entree et de sortie.
  ffmpeg -v error -y -i "$tmp/source.mp3" -af "loudnorm=I=-20:TP=-2,volume='if(lt(t,$FIN_VOIX),0.2,0.2+min((t-$FIN_VOIX)/1.5,1)*0.42)':eval=frame,afade=t=in:d=1.5,afade=t=out:st=$(awk "BEGIN{print $DUREE-2.5}"):d=2.5,atrim=0:$DUREE" \
    -ar 48000 -b:a 192k assets/musique.mp3
  rm -rf "$tmp"
fi
python3 tools/habillage-sonore.py
ls -la assets/face-voix.mp4 assets/effets.mp3 assets/article-nosalpes.jpg assets/musique.mp3
