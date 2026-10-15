#!/usr/bin/env bash
# Récupère tout ce qui reste hors du dépôt public : rushes du salon, logos partenaires, sons de la bibliothèque.
#
#   bash tools/recuperer.sh <lien ou identifiant du dossier Drive « Decidia »>
#
# Le dossier Drive est partagé par lien : son identifiant ne doit pas apparaître dans ce dépôt public,
# d'où l'argument. Les fichiers sont listés depuis la page publique du dossier, puis téléchargés un par un.
#
# Police Semplicità Pro : licence commerciale, à déposer à la main dans assets/fonts/
# (SemplicitaPro.woff, -Medium, -Semibold, -Bold ; copie dans le studio, page « Maquette Studio vidéo »).
set -euo pipefail
cd "$(dirname "$0")/.."

DOSSIER=${1:?usage : bash tools/recuperer.sh <dossier Drive>}
DOSSIER=$(echo "$DOSSIER" | sed -E 's#.*/folders/([A-Za-z0-9_-]+).*#\1#')
mkdir -p rushes sons assets/logos

# 1. Rushes : la page du dossier contient, pour chaque fichier, son identifiant suivi de son nom.
curl -sS -L -m 60 "https://drive.google.com/drive/folders/$DOSSIER" -o rushes/.dossier.html
python3 - "$DOSSIER" <<'EOF' > rushes/.liste.tsv
import re, sys
h = open("rushes/.dossier.html", encoding="utf-8", errors="replace").read()
for a, b in (("\\x22", '"'), ("\\x5b", "["), ("\\x5d", "]"), ("\\u200b", ""), ("\\/", "/")):
    h = h.replace(a, b)
vus = set()
for m in re.finditer(r'\["([\w-]{25,45})",\["' + re.escape(sys.argv[1]) + r'"\],"([^"]+\.(?:aac|m4a|mp3|wav|jpg|jpeg|png|mp4|mov))"', h):
    fid, nom = m.groups()
    nom = nom.replace("\\", "")
    if nom not in vus:
        vus.add(nom); print(f"{fid}\t{nom}")
EOF
while IFS=$'\t' read -r fid nom; do
  cible="rushes/${nom//[ ,]/_}"
  [ -s "$cible" ] || curl -sS -L -m 900 -o "$cible" "https://drive.usercontent.google.com/download?id=$fid&export=download&confirm=t"
  echo "rush  $cible"
done < rushes/.liste.tsv

# 2. Logos partenaires, depuis leurs sites officiels.
curl -sS -m 30 -o assets/logos/french-tech-alpes.svg https://www.ftalps.com/content/uploads/2023/02/LOGO_French-tech_ALPES-small.svg
curl -sS -m 30 -o assets/logos/savoy-ia.png https://savoy-ia.fr/lovable-uploads/2fed94c6-b2a3-4e51-8a98-9ec8531896f6.png

# GSAP en local : le rendu ne dépend ni du réseau ni du proxy.
curl -sS -m 30 -o assets/gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js

# 3. Sons : sources Mixkit de la bibliothèque (04_montage/bibliotheque.json, branche HyperFrames).
#    Les quatre premiers et la musique sont validés par Franck ; whoosh, pop et clic sont proposés pour ce montage.
while read -r nom url; do
  [ -s "sons/$nom" ] || curl -sS -L -m 120 -o "sons/$nom" "$url"
  echo "son   sons/$nom"
done <<'EOF'
declencheur-photo-1.wav https://assets.mixkit.co/active_storage/sfx/1133/1133.wav
page-papier-2.wav https://assets.mixkit.co/active_storage/sfx/1530/1530.wav
riser-doux-1.wav https://assets.mixkit.co/active_storage/sfx/790/790.wav
ambiance-foule-2.wav https://assets.mixkit.co/active_storage/sfx/364/364.wav
musique-curiosity.mp3 https://assets.mixkit.co/music/480/480.mp3
whoosh-doux-1.wav https://assets.mixkit.co/active_storage/sfx/1489/1489.wav
whoosh-doux-3.wav https://assets.mixkit.co/active_storage/sfx/1468/1468.wav
pop-doux-3.wav https://assets.mixkit.co/active_storage/sfx/3005/3005.wav
clic-interface-1.wav https://assets.mixkit.co/active_storage/sfx/2568/2568.wav
EOF
