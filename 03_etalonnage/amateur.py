#!/usr/bin/env python3
"""
Passe "telephone de CM" : casser la perfection qui trahit l'image fabriquee.

Le probleme n'est pas le manque de grain, c'est l'absence de defauts. Une
image generee est parfaitement exposee, parfaitement nette la ou il faut et
parfaitement floue ailleurs, sans aucune faute optique. Aucun appareil bon
marche ne produit ca, surtout de nuit sous des projecteurs.

Cette passe remplace la passe pellicule. Elle simule la chaine reelle d'une
photo de club : petit capteur pousse en sensibilite, traitement interne
agressif, puis deux passages de compression avant d'arriver sur un fil.

Dans l'ordre :
  derive de balance des blancs (sodium vert-orange)
  -> noirs laiteux remontes par l'auto-exposition
  -> hautes lumieres cramees a plat
  -> aberration chromatique sur les bords contrastes
  -> bruit de capteur : chroma en taches basse frequence + luminance fine
  -> lissage de reduction de bruit dans les ombres
  -> accentuation interne avec halos
  -> banding
  -> double compression JPEG

Usage : python3 03_etalonnage/amateur.py [dossier_entree] [dossier_sortie]
Defaut : 05_plans + 06_terrain  ->  08_amateur
"""

import io
import os
import sys
import glob
import numpy as np
from PIL import Image, ImageFilter

SOURCES = ["05_plans", "06_terrain"]
OUT = "08_amateur"

# Intensite par origine. Les plans de terrain sortent d'un modele et sont les
# plus lisses : ils encaissent le traitement le plus dur. Les photos de
# maillot portent deja le bruit d'un vrai telephone, on n'en rajoute qu'un peu.
PRESET = {
    "05_plans":  dict(iso=0.30, lift=0.040, clip=0.95, ca=0.6, jpeg=(70, 82), sharp=60),
    "06_terrain": dict(iso=0.62, lift=0.070, clip=0.91, ca=1.1, jpeg=(56, 76), sharp=95),
    # Les photos du stade sont prises de jour, bien exposees et bien cadrees :
    # ce sont les plus propres du lot, donc celles qui encaissent le traitement
    # le plus dur avant de ressembler au reste du film.
    "09_reel/plans": dict(iso=0.85, lift=0.095, clip=0.88, ca=1.5, jpeg=(44, 68), sharp=130),
}


def white_balance_drift(a, rng):
    """Les projecteurs au sodium mettent la balance des blancs en echec.

    On tire une derive differente par plan : sur un vrai fil de club, deux
    photos de la meme soiree n'ont jamais la meme dominante.
    """
    green = 1.0 + rng.uniform(0.010, 0.045)
    warm = 1.0 + rng.uniform(0.015, 0.055)
    cool = 1.0 - rng.uniform(0.020, 0.070)
    return np.clip(a * np.array([warm, green, cool], dtype=np.float32), 0.0, 1.0)


def lift_blacks(a, amount):
    """Noirs laiteux : l'auto-exposition remonte les ombres et tue le contraste."""
    return a * (1.0 - amount) + amount


def clip_highlights(a, ceiling):
    """Hautes lumieres cramees a plat, sans roll-off. Le capteur sature, point."""
    return np.clip(a / ceiling, 0.0, 1.0)


def chromatic_aberration(a, strength):
    """Frangeage violet et vert sur les bords contrastes.

    Obtenu en decalant les canaux rouge et bleu de quelques pixels vers
    l'exterieur du cadre, comme le fait une optique bon marche.
    """
    h, w = a.shape[:2]
    px = max(1, int(round(strength * max(h, w) / 900)))
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], px, axis=1)
    out[..., 2] = np.roll(a[..., 2], -px, axis=1)
    edge = np.abs(np.gradient(a.mean(axis=2), axis=1))
    mask = np.clip(edge * 14.0, 0.0, 1.0)[..., None]
    return np.clip(a * (1.0 - mask) + out * mask, 0.0, 1.0)


def sensor_noise(a, iso, rng):
    """Bruit de capteur, pas grain argentique.

    Deux composantes : un bruit de chrominance basse frequence, genere en
    petit puis agrandi, qui donne les taches de couleur baveuses ; et un
    bruit de luminance fin. Les deux sont plus forts dans les ombres, la ou
    le capteur manque de signal, exactement l'inverse du grain argentique.
    """
    h, w = a.shape[:2]
    lum = a.mean(axis=2)
    dark = np.clip(1.25 - lum * 1.6, 0.0, 1.0)[..., None]

    small = rng.normal(0.0, 1.0, (max(h // 32, 2), max(w // 32, 2), 3)).astype(np.float32)
    blotch = np.asarray(
        Image.fromarray(((small * 40 + 128).clip(0, 255)).astype(np.uint8)).resize(
            (w, h), Image.BICUBIC
        ),
        dtype=np.float32,
    )
    blotch = (blotch - 128.0) / 40.0

    # La chrominance du bruit est en partie desaturee : un capteur bruite ne
    # produit pas des confettis colores, il produit des taches ternes que la
    # reduction de bruit ecrase ensuite en aplats.
    blotch = blotch * 0.45 + blotch.mean(axis=2, keepdims=True) * 0.55

    fine = rng.normal(0.0, 1.0, (h, w, 1)).astype(np.float32)
    noisy = a + (blotch * 0.026 + fine * 0.020) * iso * dark
    return np.clip(noisy, 0.0, 1.0)


def denoise_smear(img, strength=4):
    """Le lissage interne de l'appareil : les ombres deviennent pateuses."""
    a = np.asarray(img, dtype=np.float32) / 255.0
    dark = np.clip(1.15 - a.mean(axis=2) * 1.7, 0.0, 1.0)[..., None]
    blurred = np.asarray(
        img.filter(ImageFilter.GaussianBlur(strength)), dtype=np.float32
    ) / 255.0
    return Image.fromarray(
        ((a * (1.0 - dark * 0.72) + blurred * (dark * 0.72)) * 255).astype(np.uint8)
    )


def banding(a, levels=48):
    """Aplats postérisés dans les degrades : ciel de nuit, halos de projecteur."""
    return np.round(a * levels) / levels


def recompress(img, q1, q2):
    """Deux passages JPEG : l'appareil, puis la messagerie ou le reseau."""
    for q in (q1, q2):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, subsampling=2)
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
    return img


def social_resize(img):
    """Redimensionnement de la chaine sociale : on descend, on remonte."""
    w, h = img.size
    small = img.resize((int(w * 0.62), int(h * 0.62)), Image.BILINEAR)
    return small.resize((w, h), Image.BICUBIC)


def handheld_frame(img, rng):
    """Horizon penche et recadrage decentre : personne ne vise droit a main levee."""
    angle = rng.uniform(-3.2, 3.2)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    w, h = img.size
    m = 0.055
    dx = rng.uniform(-0.5, 0.5) * m * w
    dy = rng.uniform(-0.5, 0.5) * m * h
    box = (
        int(m * w + dx), int(m * h + dy),
        int(w - m * w + dx), int(h - m * h + dy),
    )
    return img.crop(box).resize((w, h), Image.BICUBIC)


def process(path, preset, rng):
    img = Image.open(path).convert("RGB")
    img = handheld_frame(img, rng)

    a = np.asarray(img, dtype=np.float32) / 255.0
    a = white_balance_drift(a, rng)
    a = clip_highlights(a, preset["clip"])
    a = lift_blacks(a, preset["lift"])
    a = chromatic_aberration(a, preset["ca"])
    a = sensor_noise(a, preset["iso"], rng)
    a = banding(a)

    img = Image.fromarray((a * 255).astype(np.uint8))
    img = denoise_smear(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=preset["sharp"], threshold=1))
    img = social_resize(img)
    return recompress(img, *preset["jpeg"])


if __name__ == "__main__":
    srcs = [sys.argv[1]] if len(sys.argv) > 1 else SOURCES
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(1961)
    for src in srcs:
        preset = PRESET.get(src, PRESET["06_terrain"])
        for path in sorted(glob.glob(os.path.join(src, "*.png"))):
            name = os.path.basename(path)
            if name.startswith("_"):
                continue
            res = process(path, preset, rng)
            dest = os.path.join(out, name.replace(".png", ".jpg"))
            res.save(dest, quality=88, subsampling=2)
            print(f"{name:20s} {res.size[0]}x{res.size[1]}")
