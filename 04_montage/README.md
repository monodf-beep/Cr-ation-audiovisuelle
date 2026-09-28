# Montage

| Script | Rôle |
|---|---|
| `film.py`, `son.py`, `animatique.py` | Le film FC Cluses (montage, piste son, animatique) |
| `disposition.py` | Écran divisé, bandes empilées avec étiquettes, visage en incrustation |
| `texte_derriere.py` | Texte derrière (ou devant) la personne, détourage MediaPipe |
| `coupes.py` | Coupes franches aux silences, zoom une coupe sur deux |
| `outils_video.py` | Fonctions communes (ffmpeg, étiquettes, formats) |

Quand utiliser quelle disposition : `.claude/skills/montage-mise-en-page/SKILL.md`.

Dépendances : Pillow, numpy, imageio-ffmpeg ; pour `texte_derriere.py`, `pip install mediapipe` (et `libegl1` sur un serveur Linux sans écran). Le modèle de détourage se télécharge seul au premier lancement dans `~/.cache/studio-video/`.

```
python3 04_montage/coupes.py prise.mp4 -o prise-coupee.mp4 --zoom 1.08
python3 04_montage/disposition.py pile prise.mp4 --etiquettes TOFU MOFU BOFU --sous "10 000 vues" "1 000 vues" "100 vues" --decalages 0 4 8 -o pile.mp4
python3 04_montage/disposition.py incrustation ecran.mp4 visage.mp4 --format 16:9 --coin bd -o incrustation.mp4
python3 04_montage/disposition.py divise avant.mp4 apres.mp4 --etiquettes Avant Après -o divise.mp4
python3 04_montage/texte_derriere.py prise.mp4 --texte DESIGN --debut 0.5 --fin 3 --apercu 1.5 -o apercu.png
python3 04_montage/texte_derriere.py prise.mp4 --texte DESIGN --debut 0.5 --fin 3 -o derriere.mp4
```
