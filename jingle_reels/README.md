# Générique CULTURA SABAUDA

Générique de 7 s pour l'émission, rendu en 9:16 (reels) et 16:9 (TV).
Tempo 128,6 : un temps = 14 images à 30 i/s. Chaque coupe tombe sur un temps.

| Images | Temps | Ce qui se passe |
|---|---|---|
| 0–27 | 0,0 s | une grille de « + » éclôt depuis le centre, pivote, le « + » central avale l'écran |
| 28–83 | 0,9 s | 8 cartes, une par demi-temps : HISTOIRE, LANGUE, CUISINE, MUSIQUE, PATRIMOINE, TRADITIONS, PAYSAGES, IDÉES |
| 84–97 | 2,8 s | accélération, un verbe par quart de temps : LIRE, VOIR, GOÛTER, ÉCOUTER |
| 98–107 | 3,3 s | montée : tunnel de « + » |
| 108–111 | 3,6 s | silence, noir |
| 112–209 | 3,7 s | DROP : le logo, puis le motif de clarine ré–la–ré |

La Savoie n'est jamais nommée. Elle est dans la croix devenue « + », les crêtes en zigzag,
les arcades, la meule, la clarine et le rouge et bleu du drapeau.

## Fichiers

- `generique.html` : toute l'animation, dessinée en canvas en fonction du numéro d'image (`dessiner(f)`)
- `rendu.js` : pilote Chromium image par image et assemble avec ffmpeg
- `son_generique.py` : bande son synthétisée (maquette), calée sur les mêmes numéros d'image

## Rendu

```
pip install numpy imageio-ffmpeg
mkdir -p jingle_reels/fonts
curl -L -o jingle_reels/fonts/Anton-Regular.ttf https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anton/Anton-Regular.ttf
curl -L -o jingle_reels/fonts/InstrumentSerif-Italic.ttf https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/instrumentserif/InstrumentSerif-Italic.ttf
python3 jingle_reels/son_generique.py
NODE_PATH=$(npm root -g) node jingle_reels/rendu.js 1080 1920 jingle_reels/out/generique_9x16.mp4 jingle_reels/out/generique.wav
NODE_PATH=$(npm root -g) node jingle_reels/rendu.js 1920 1080 jingle_reels/out/generique_16x9.mp4 jingle_reels/out/generique.wav
```

Avant diffusion TV : passer le test d'épilepsie photosensible (Harding/PSE). Les cartes
alternent déjà des fonds de luminance proche (rouge, bleu) sur l'accélération, mais le test fait foi.
