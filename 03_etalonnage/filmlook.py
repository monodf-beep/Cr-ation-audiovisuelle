#!/usr/bin/env python3
"""
Passe pellicule commune a tous les plans du film.

Le film melange deux matieres : des photographies du vrai maillot et des
images de terrain fabriquees. Sans traitement commun, la couture se verrait
a chaque coupe. Cette passe est le liant : meme grain, meme halation, meme
etalonnage de base sur les vingt-deux plans, quelle que soit leur origine.

Dans l'ordre :
  split-toning (ombres froides / hautes lumieres chaudes)
  -> halation rouge-orangee autour des sources vives
  -> grain 35 mm module par la luminance
  -> leger vignettage optique

Usage : python3 03_etalonnage/filmlook.py
Entrees : 05_plans/*.png (maillot)  +  06_terrain/*.png (terrain)
Sortie  : 07_film/*.png
"""

import os
import glob
import numpy as np
from PIL import Image, ImageFilter

OUT = "07_film"
SOURCES = ["05_plans", "06_terrain"]

# Le grain est la signature la plus visible du rendu. Il est volontairement
# plus fort sur les plans de terrain, qui sortent d'un modele et ont donc une
# proprete numerique a casser, que sur les photos de maillot qui portent deja
# le bruit du capteur du telephone.
GRAIN = {"05_plans": 0.030, "06_terrain": 0.042}

SHADOW_TINT = np.array([0.94, 1.01, 1.06], dtype=np.float32)   # bleu-vert
HIGHLIGHT_TINT = np.array([1.05, 1.00, 0.92], dtype=np.float32)  # ambre sodium


def split_tone(a):
    """Ombres froides, hautes lumieres chaudes : la bascule de base du film."""
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
    w = np.clip(lum * 1.35, 0.0, 1.0) ** 1.4
    return np.clip(a * (SHADOW_TINT * (1.0 - w) + HIGHLIGHT_TINT * w), 0.0, 1.0)


def halation(a, threshold=0.62, radius=26, strength=0.30):
    """Debord rouge-orange autour des sources vives.

    C'est la marque la plus reconnaissable du rendu argentique : les
    projecteurs, les gouttes en contre-jour et les bords dores du flocage
    bavent legerement dans le rouge.
    """
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    hi = np.clip((lum - threshold) / max(1.0 - threshold, 1e-6), 0.0, 1.0)
    hi_img = Image.fromarray((hi * 255).astype(np.uint8))
    bloom = np.asarray(
        hi_img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32
    ) / 255.0
    tint = np.array([1.00, 0.42, 0.20], dtype=np.float32)     # rouge-orange
    glow = bloom[..., None] * tint * strength
    return np.clip(a + glow * (1.0 - a), 0.0, 1.0)            # ajout type screen


def grain(a, amount, rng):
    """Grain 35 mm : present dans les demi-teintes, discret dans les noirs.

    Un grain uniforme trahit tout de suite le filtre numerique. Sur pellicule
    la densite du grain suit l'exposition, d'ou la modulation par la luminance.
    """
    h, w = a.shape[:2]
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    weight = (4.0 * lum * (1.0 - lum))[..., None]             # maximum a 0.5
    mono = rng.normal(0.0, 1.0, (h, w, 1)).astype(np.float32)
    chroma = rng.normal(0.0, 1.0, (h, w, 3)).astype(np.float32)
    noise = mono * 0.80 + chroma * 0.20                       # grain peu colore
    return np.clip(a + noise * amount * weight, 0.0, 1.0)


def optical_vignette(a, strength=0.20):
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return a * np.clip(1.0 - strength * (d / 1.5) ** 2.2, 0.0, 1.0)[..., None]


def process(path, amount, rng):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    a = split_tone(a)
    a = halation(a)
    a = optical_vignette(a)
    a = grain(a, amount, rng)
    return Image.fromarray((a * 255).astype(np.uint8))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    # Graine fixe : deux executions donnent le meme grain, indispensable pour
    # pouvoir retoucher un seul plan sans que sa texture bouge par rapport aux
    # autres.
    rng = np.random.default_rng(2026)
    for src in SOURCES:
        for path in sorted(glob.glob(os.path.join(src, "*.png"))):
            name = os.path.basename(path)
            if name.startswith("_"):
                continue
            out = process(path, GRAIN[src], rng)
            out.save(os.path.join(OUT, name))
            print(f"{name:20s} {out.size[0]}x{out.size[1]}  grain {GRAIN[src]}")
