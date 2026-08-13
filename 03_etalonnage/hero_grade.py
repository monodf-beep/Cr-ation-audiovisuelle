#!/usr/bin/env python3
"""
Etalonnage des plans heros vers le registre du film.

Les plans heros sortent nets, riches et bien eclaires : c'est ce qu'on
voulait, et c'est ce que la passe amateur aurait detruit. Le style recherche
n'est pas de la basse qualite, c'est une lumiere dure et une dominante
sodium sur une image qui reste nette.

Cette passe ne degrade donc rien. Elle bascule la couleur, creuse le
contraste, fait baver les lampes et pose un grain fin. Le sujet reste net
de bout en bout.

Usage : python3 03_etalonnage/hero_grade.py <entree> <sortie>
"""

import os
import sys
import glob
import numpy as np
from PIL import Image, ImageFilter

SODIUM = np.array([1.02, 1.05, 0.86], dtype=np.float32)
AMBRE = np.array([1.08, 1.00, 0.84], dtype=np.float32)


def contraste(a, force=0.30):
    """Courbe en S : noirs plus denses, hautes lumieres tenues."""
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    return np.clip(a * (1 - force) + s * force, 0.0, 1.0)


def bascule(a):
    """Sodium dans les demi-teintes, ambre dans les hautes lumieres."""
    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 1.7, 0.0, 1.0) ** 1.4
    return np.clip(a * (SODIUM * (1.0 - haut) + AMBRE * haut), 0.0, 1.0)


def bavure(img, a, seuil=0.74, rayon=26, force=0.22):
    """Les projecteurs debordent au lieu de s'ecreter proprement."""
    lum = a.mean(axis=2)
    hi = np.clip((lum - seuil) / max(1.0 - seuil, 1e-6), 0.0, 1.0)
    bloom = np.asarray(
        Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rayon)),
        dtype=np.float32) / 255.0
    teinte = np.array([1.00, 0.88, 0.66], dtype=np.float32)
    return np.clip(a + bloom[..., None] * teinte * force, 0.0, 1.0)


def vignette(a, force=0.30):
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return a * np.clip(1.0 - force * (d / 1.35) ** 2.2, 0.0, 1.0)[..., None]


def grain(a, amount, rng):
    """Grain fin, pose sur l'image nette. Il texture, il ne brouille pas."""
    h, w = a.shape[:2]
    lum = a.mean(axis=2)
    poids = (4.0 * lum * (1.0 - lum))[..., None]
    bruit = rng.normal(0.0, 1.0, (h, w, 1)).astype(np.float32)
    return np.clip(a + bruit * amount * poids, 0.0, 1.0)


def process(path, rng):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img, dtype=np.float32) / 255.0
    a = contraste(a)
    a = bascule(a)
    a = bavure(img, a)
    a = vignette(a)
    a = grain(a, 0.022, rng)
    out = Image.fromarray((a * 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(radius=2, percent=40, threshold=3))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "18_hero"
    out = sys.argv[2] if len(sys.argv) > 2 else "11_final"
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(26)
    for path in sorted(glob.glob(os.path.join(src, "*.png"))):
        name = os.path.basename(path).replace(".png", ".jpg")
        res = process(path, rng)
        res.save(os.path.join(out, name), quality=93, subsampling=0)
        print(f"{name:20s} {res.size[0]}x{res.size[1]}")
