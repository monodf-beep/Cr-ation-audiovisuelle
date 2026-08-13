#!/usr/bin/env python3
"""
Conversion jour gris -> fin de journee, pour les photographies du club.

Le film raconte une soiree : la lumiere doit tomber du premier plan au
dernier. Les photographies du stade sont en revanche prises par un gris
d'octobre, en plein jour. Sans traitement elles ouvrent le film sur une
lumiere qui contredit tout ce qui suit.

Cette passe ne cherche pas la nuit, qui serait invraisemblable a partir
d'une source aussi plate. Elle vise l'heure juste avant : le soleil est
tombe derriere la montagne, le ciel garde sa lumiere, le sol est deja dans
l'ombre. C'est le seul point ou une photo de jour et un plan de projecteurs
peuvent se rejoindre.

Dans l'ordre :
  assombrissement progressif du bas vers le haut (le sol tombe avant le ciel)
  -> rechauffement du ciel bas, refroidissement des ombres
  -> baisse generale d'exposition et de contraste local
  -> halo chaud ajoute autour des projecteurs eventuels

Usage : python3 03_etalonnage/crepuscule.py <entree> <sortie>
"""

import os
import sys
import glob
import numpy as np
from PIL import Image, ImageFilter

# Le sol tombe dans l'ombre bien avant le ciel : c'est ce degrade vertical,
# et non une simple baisse d'exposition, qui fait lire la fin de journee.
SOL = 0.42        # facteur d'exposition en bas de cadre
CIEL = 0.86       # facteur d'exposition en haut de cadre
CHAUD_CIEL = np.array([1.10, 1.01, 0.88], dtype=np.float32)
FROID_OMBRE = np.array([0.92, 0.97, 1.12], dtype=np.float32)


def chute_de_lumiere(a):
    h, w = a.shape[:2]
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    # courbe : le bas plonge vite, le haut resiste
    facteur = SOL + (CIEL - SOL) * (1.0 - y) ** 1.6
    return np.clip(a * facteur, 0.0, 1.0)


def bascule_chromatique(a):
    """Ciel chaud en haut, ombres froides en bas."""
    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 1.6, 0.0, 1.0) ** 1.3
    return np.clip(a * (CHAUD_CIEL * haut + FROID_OMBRE * (1.0 - haut)), 0.0, 1.0)


def halo_projecteurs(img, seuil=0.80, rayon=30, force=0.45):
    """Les lampes deja allumees prennent un halo chaud, comme au crepuscule."""
    a = np.asarray(img, dtype=np.float32) / 255.0
    lum = a.mean(axis=2)
    hi = np.clip((lum - seuil) / max(1.0 - seuil, 1e-6), 0.0, 1.0)
    bloom = np.asarray(
        Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rayon)),
        dtype=np.float32,
    ) / 255.0
    teinte = np.array([1.00, 0.82, 0.52], dtype=np.float32)
    glow = bloom[..., None] * teinte * force
    return Image.fromarray((np.clip(a + glow * (1.0 - a), 0, 1) * 255).astype(np.uint8))


def process(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    a = chute_de_lumiere(a)
    a = bascule_chromatique(a)
    # contraste local ecrase : au crepuscule les volumes s'aplatissent
    a = np.clip(a * 0.94 + a.mean() * 0.06, 0.0, 1.0)
    return halo_projecteurs(Image.fromarray((a * 255).astype(np.uint8)))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "09_reel/plans"
    out = sys.argv[2] if len(sys.argv) > 2 else "09_reel/crepuscule"
    os.makedirs(out, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(src, "*.png"))):
        name = os.path.basename(path)
        res = process(path)
        res.save(os.path.join(out, name))
        print(f"{name:20s} {res.size[0]}x{res.size[1]}")
