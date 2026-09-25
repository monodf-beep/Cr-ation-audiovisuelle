#!/bin/bash
# Telecharge les quatre cartes anciennes depuis Gallica (IIIF) et les passe en bichromie
# bleu Savoie sur blanc, dans assets/cartes/. Les .jpg sont hors depot (.gitignore).
# Sources et conditions de reutilisation : assets/cartes/SOURCES.md
#
# Usage : bash tools/prepare-cartes.sh
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Bichromie : noir -> #0a36af, blanc -> #ffffff.
TONE="format=rgb24,lutrgb=r='10+val*245/255':g='54+val*201/255':b='175+val*80/255'"
GRIS="format=gray"
# Canal rouge seul : les tampons rouges de bibliotheque disparaissent.
ROUGE="colorchannelmixer=rr=1:rg=0:rb=0:gr=1:gg=0:gb=0:br=1:bg=0:bb=0,format=gray"
CONTRASTE="curves=all='0/0 0.30/0.08 0.62/0.5 0.82/1 1/1'"

# nom | ark Gallica | recadrage (w:h:x:y sur l'image de 2400 px de large) | niveaux | courbe
cartes=(
  "sanson-1665|btv1b53042013w|2040:2240:180:290|$ROUGE|$CONTRASTE"
  "jaillot-1706|btv1b55013286s|2230:2080:105:65|$GRIS|curves=all='0/0 0.45/0.05 0.68/0.45 0.80/1 1/1'"
  "brunet-1728|btv1b530329939|2230:640:80:110|$GRIS|curves=all='0/0 0.30/0.10 0.62/0.55 0.80/1 1/1'"
  "bouffard-1841|btv1b53087648m|1660:2090:432:436|$ROUGE|$CONTRASTE"
)

mkdir -p assets/cartes
for c in "${cartes[@]}"; do
  IFS='|' read -r nom ark crop niveaux courbe <<< "$c"
  curl -sfL --retry 4 --retry-all-errors -o "$TMP/$nom.jpg" "https://gallica.bnf.fr/iiif/ark:/12148/$ark/f1/full/2400,/0/native.jpg"
  ffmpeg -loglevel error -y -i "$TMP/$nom.jpg" -vf "crop=$crop,$niveaux,$courbe,$TONE" -q:v 3 "assets/cartes/$nom.jpg"
  echo "assets/cartes/$nom.jpg"
done
