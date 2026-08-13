#!/usr/bin/env python3
"""
Fabrique les deux derniers plans du film : la Croix de Savoie et FC CLUSA.

Le film devait finir sur ces deux-la, et ils sortaient coupes. La cause
n'etait pas le cadrage du montage : sur PLAN-13, PLAN-14 et PLAN-15, le
mot est deja tronque dans l'image source, aux deux bords. Aucun recadrage
ne le repare.

Le mot entier existe ailleurs : en haut du dos de HERO-DOS, sous la nuque,
la croix et FC CLUSA sont complets et nets. On decoupe donc la fin
la-dedans, ce qui a en plus l'avantage de la raccorder au plan du dos qui
la precede — c'est le meme vetement, au meme endroit.

Usage : python3 03_etalonnage/fin.py
Sortie : 11_final/FIN-CLUSA.jpg   la croix, le mot, le haut de CHAMPIONS
         11_final/FIN-CROIX.jpg   la croix seule, pour un flash
"""

import numpy as np
from PIL import Image, ImageFilter

SRC = "11_final/HERO-DOS.jpg"

# (sortie, gauche, haut, largeur — en fraction de l'image ; la hauteur suit
#  du 9:16, ancree sous le haut demande)
PLANS = [
    ("11_final/FIN-CLUSA.jpg", 0.29, 0.005, 0.42, "la croix, FC CLUSA, le haut de CHAMPIONS"),
    ("11_final/FIN-CROIX.jpg", 0.355, 0.020, 0.29, "la croix seule"),
]


def decoupe(im, gauche, haut, largeur):
    w, h = im.size
    cw = int(largeur * w)
    ch = int(round(cw * 16 / 9))
    x = int(gauche * w)
    y = int(haut * h)
    if y + ch > h:                      # on remonte plutot que de deformer
        y = max(0, h - ch)
    return im.crop((x, y, x + cw, y + ch))


def lumiere(a):
    """On ramene l'oeil sur le mot : les bords tombent, l'or reste tenu."""
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.42) / (h / 2)) ** 2)
    a = a * np.clip(1.0 - 0.34 * (d / 1.15) ** 2.0, 0.0, 1.0)[..., None]
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    return np.clip(a * 0.70 + s * 0.30, 0.0, 1.0)


if __name__ == "__main__":
    im = Image.open(SRC).convert("RGB")
    for sortie, g, ht, lg, note in PLANS:
        c = decoupe(im, g, ht, lg)
        a = lumiere(np.asarray(c, dtype=np.float32) / 255.0)
        out = Image.fromarray((a * 255).astype(np.uint8))
        out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=45, threshold=3))
        out.save(sortie, quality=94, subsampling=0)
        print(f"{sortie:26s} {out.size[0]}x{out.size[1]}  {note}")
