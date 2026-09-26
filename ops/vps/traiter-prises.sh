#!/usr/bin/env bash
# Traitement automatique des prises de voix off filmees (appele par synchro.sh, sur le VPS).
# Pour chaque prise video de <projet>/voix-off/ pas encore traitee, ecrit dans <projet>/voix-off/traitees/ :
#   <prise>-lumiere.mp4 : image eclaircie et rechauffee (la webcam donne une image sombre et bleutee),
#                         bruit reduit, recadree au centre en vertical 1080 x 1920, 30 images/s,
#                         son au niveau des reseaux sociaux (-16 LUFS).
# La prise brute n'est jamais modifiee. Les fichiers traites partent dans Drive avec le reste de voix-off/.
set -uo pipefail
DEPOT=${DEPOT:-/srv/studio/depot}

IMAGE="hqdn3d=3:3:4:4,eq=gamma=1.35:contrast=1.06:saturation=1.08:brightness=0.02,colortemperature=temperature=5200,crop=trunc(ih*9/16/2)*2:ih,scale=1080:1920:flags=lanczos,unsharp=5:5:0.6,fps=30"

for prise in "$DEPOT"/*/voix-off/*.webm "$DEPOT"/*/voix-off/*.mp4; do
  [ -f "$prise" ] || continue
  dossier=$(dirname "$prise")/traitees
  sortie="$dossier/$(basename "${prise%.*}")-lumiere.mp4"
  [ -f "$sortie" ] && continue
  # Seulement les prises filmees, et pas une prise encore en cours d'envoi (modifiee il y a moins d'une minute).
  ffprobe -v error -select_streams v -show_entries stream=codec_type -of csv=p=0 "$prise" | grep -q video || continue
  [ $(( $(date +%s) - $(stat -c %Y "$prise") )) -lt 60 ] && continue
  mkdir -p "$dossier"
  echo "traitement : $prise"
  nice -n 10 ffmpeg -v error -y -i "$prise" -vf "$IMAGE" -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
    -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$sortie.tmp.mp4" && mv "$sortie.tmp.mp4" "$sortie" || { rm -f "$sortie.tmp.mp4"; echo "echec : $prise"; }
done
