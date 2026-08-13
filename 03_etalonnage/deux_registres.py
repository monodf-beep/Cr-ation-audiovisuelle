#!/usr/bin/env python3
"""
Deux registres assumes : le lieu est sale, le maillot est net.

Le film melangeait deux qualites sans les separer franchement, si bien que
l'ecart se lisait comme une incoherence plutot que comme un parti pris. La
correction ne consiste pas a les rapprocher mais a les eloigner : le terrain
descend vers la photo de telephone poussee a bout, le maillot monte vers
l'image de campagne.

Ce que ca raconte : dans une soiree boueuse, mal eclairee et mal
photographiee, l'objet est la seule chose qui tienne debout et qui soit vue
nettement.

TERRAIN  bruit epais, voile de brume dans les faisceaux, frangeage violet,
         noirs laiteux, contraste ecrase
MAILLOT  net, contraste tenu, grain fin, lampes qui debordent a peine

Usage : python3 03_etalonnage/deux_registres.py
"""

import os
import numpy as np
from PIL import Image, ImageFilter

BASE = "11_final"

TERRAIN = ["AMAT-02", "GP-CRAMPONS", "FLAG-01", "ULTRAS-FIN"]
MAILLOT = ["HERO-PATCH", "HERO-FACE", "HERO-DOS", "PLAN-03", "PLAN-06",
           "PLAN-07", "PLAN-11", "PLAN-13", "PLAN-15", "PLATE-08", "PLATE-12"]


# --------------------------------------------------------------------------
# Le lieu
# --------------------------------------------------------------------------

def voile(img, a, seuil=0.66, rayon=38, force=0.13):
    """Voile de brume : la lumiere des projecteurs se diffuse dans tout le cadre.

    C'est ce qui manque le plus aux images propres. Un objectif bon marche
    plein de poussiere ne restitue pas un noir a cote d'une lampe : la
    lumiere bave partout et delave l'image entiere.
    """
    lum = a.mean(axis=2)
    hi = np.clip((lum - seuil) / max(1.0 - seuil, 1e-6), 0.0, 1.0)
    diffus = np.asarray(
        Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rayon)),
        dtype=np.float32) / 255.0
    teinte = np.array([1.00, 0.95, 0.82], dtype=np.float32)
    return np.clip(a + diffus[..., None] * teinte * force, 0.0, 1.0)


def frangeage(a, force=2.2):
    """Frangeage violet et vert autour des sources vives."""
    h, w = a.shape[:2]
    px = max(2, int(round(force * max(h, w) / 900)))
    lum = a.mean(axis=2)
    bord = np.clip(np.abs(np.gradient(lum, axis=1)) * 16.0, 0.0, 1.0)[..., None]
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], px, axis=1)
    out[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return np.clip(a * (1 - bord) + out * bord, 0.0, 1.0)


def bruit_capteur(a, rng, force=0.055):
    """Bruit epais, en taches, plus fort dans les ombres."""
    h, w = a.shape[:2]
    sombre = np.clip(1.3 - a.mean(axis=2) * 1.7, 0.0, 1.0)[..., None]
    petit = rng.normal(0, 1, (max(h // 26, 2), max(w // 26, 2), 3)).astype(np.float32)
    taches = np.asarray(
        Image.fromarray(((petit * 40 + 128).clip(0, 255)).astype(np.uint8)).resize(
            (w, h), Image.BICUBIC), dtype=np.float32)
    taches = (taches - 128.0) / 40.0
    taches = taches * 0.45 + taches.mean(axis=2, keepdims=True) * 0.55
    fin = rng.normal(0, 1, (h, w, 1)).astype(np.float32)
    return np.clip(a + (taches * 0.6 + fin * 0.4) * force * sombre, 0.0, 1.0)


def sale(path, rng):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img, dtype=np.float32) / 255.0
    a = voile(img, a)
    # Le sale n'est pas du delave : la reference est sombre et contrastee, et
    # ce sont le bruit, le frangeage et la bavure des lampes qui la salissent,
    # pas un brouillard uniforme. On tient donc les noirs.
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = np.clip(a * 0.55 + s * 0.45, 0.0, 1.0)
    a = a * 0.96 + 0.025
    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 1.7, 0, 1) ** 1.3
    sodium = np.array([1.00, 1.08, 0.82], dtype=np.float32)
    ambre = np.array([1.10, 0.98, 0.76], dtype=np.float32)
    a = np.clip(a * (sodium * (1 - haut) + ambre * haut), 0, 1)
    a = frangeage(a)
    a = bruit_capteur(a, rng)
    out = Image.fromarray((a * 255).astype(np.uint8))
    out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=110, threshold=1))
    w, h = out.size
    out = out.resize((int(w * 0.7), int(h * 0.7)), Image.BILINEAR).resize((w, h), Image.BICUBIC)
    return out


# --------------------------------------------------------------------------
# Le maillot
# --------------------------------------------------------------------------

def net(path, rng):
    """Le maillot garde sa nettete : on tient le contraste et on pose peu de grain."""
    img = Image.open(path).convert("RGB")
    a = np.asarray(img, dtype=np.float32) / 255.0
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = np.clip(a * 0.62 + s * 0.38, 0.0, 1.0)
    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 1.7, 0, 1) ** 1.4
    a = np.clip(a * (np.array([1.02, 1.03, 0.90], dtype=np.float32) * (1 - haut)
                     + np.array([1.07, 1.00, 0.86], dtype=np.float32) * haut), 0, 1)
    h, w = a.shape[:2]
    poids = (4.0 * a.mean(axis=2) * (1.0 - a.mean(axis=2)))[..., None]
    a = np.clip(a + rng.normal(0, 1, (h, w, 1)).astype(np.float32) * 0.014 * poids, 0, 1)
    out = Image.fromarray((a * 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2))


if __name__ == "__main__":
    rng = np.random.default_rng(1961)
    for nom in TERRAIN:
        p = os.path.join(BASE, nom + ".jpg")
        if not os.path.exists(p):
            print(f"{nom} : absent"); continue
        sale(p, rng).save(p, quality=88, subsampling=2)
        print(f"{nom:14s} terrain — sali")
    for nom in MAILLOT:
        p = os.path.join(BASE, nom + ".jpg")
        if not os.path.exists(p):
            print(f"{nom} : absent"); continue
        net(p, rng).save(p, quality=94, subsampling=0)
        print(f"{nom:14s} maillot — tenu net")
