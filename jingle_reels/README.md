# Jingle des reels — la croix de Savoie

`jingle.py` fabrique deux pièces en 1080×1920, 30 i/s :

| Fichier | Durée | Usage |
|---|---|---|
| `out/outro.mp4` | 2,4 s | signature de fin, avec le son |
| `out/sting_alpha.mov` | 1,2 s | petit drapeau sans fond (ProRes 4444) à poser sur la 1ʳᵉ image d'un reel |
| `out/sting_apercu.mp4` | — | le sting posé sur une image, pour juger |

Le drapeau est celui des images Higgsfield de la parade (champ rouge, croix blanche, bordure bleue).
Tout est dessiné, rien n'est généré : le nom et la croix restent exacts à chaque rendu.
Le son est une maquette synthétisée (trois notes de clarine ré–la–ré, sub, souffles).

Réglages en tête du script : `NOM`, couleurs, temps forts (`T_IMPACT`, `T_BRAS`, `T_FIGE`…).

```
pip install pillow numpy imageio-ffmpeg
python3 jingle_reels/jingle.py
```

La police Anton (OFL) est téléchargée au premier lancement. `apercu_fond.png` (hors dépôt) sert de fond à l'aperçu du sting.
