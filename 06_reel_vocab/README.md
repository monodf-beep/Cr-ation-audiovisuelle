# Reel vocabulaire savoyard (9:16)

Rushes : match de rugby du 7/11/2026 (dossier Drive, 10 fichiers `VID_20261107_*.mp4`,
renommés par leur heure : `125433.mp4`, etc.).

- `vocab.json` : thème, accroche, conclusion et **liste des mots** (`sv`, `pron`, `fr`).
- `reel.py` : montage complet, de l'image au son. `python3 reel.py DOSSIER_RUSHES vocab.json sortie.mp4`

Le nombre de mots est libre : chaque mot dure 3 s, chaque mot peut choisir son plan (`"plan": [rush, début, vitesse]`).
