#!/usr/bin/env python3
"""
Etalonnage des photos reelles du maillot vers le rendu "noir studio" du film.

Les plans macro de la publicite sont tires directement des photos du vrai
maillot, upscalees en 4K : aucune generation, donc aucune derive possible
sur les textes, l'ecusson ou le motif.
Ce script ne fait que recadrer et eclairer. Il ne redessine rien.

Chaine par plan :
  rotation -> recadrage normalise -> courbe en S -> lumiere rasante
  -> vignette -> saturation selective rouge/or -> nettete

Deux types de sortie :
  PLAN-XX  cadre 9:16 pret a monter (plans fixes ou push-in)
  PLATE-XX plaque large au format natif, pour les travellings lateraux
           realises en pan-and-scan au montage (pas de modele video)

Usage    : python3 03_etalonnage/grade.py
Entrees  : 04_sources/*.png
Sorties  : 05_plans/*.png
"""

import os
import numpy as np
from PIL import Image, ImageFilter

SRC = "04_sources"
OUT = "05_plans"
RATIO_916 = 9 / 16

SOURCES = {
    "dos_macro":  "dos_macro.png",      # Croix de Savoie + FC CLUSA + haut de CHAMPIONS
    "dos_plein":  "dos_plein.png",      # CHAMPIONS + 26
    "manche_g":   "manche_gauche.png",  # couronne + devise
    "manche_d":   "manche_droite.png",  # patch R2
    "face_macro": "face_macro.png",     # FORZAFC + TARIM + ecusson (photo tournee 90 deg)
}

# --------------------------------------------------------------------------
# Definition des plans
#
# rot   : rotation en degres (sens antihoraire) appliquee AVANT le recadrage
# crop  : (gauche, haut, droite, bas) en fraction de l'image, apres rotation
# light : (x, y) origine de la lumiere rasante, en fraction du cadre
# ev    : exposition globale, 1.0 = neutre
# kind  : "plan" -> cadre 9:16 ; "plate" -> plaque large pour travelling
# --------------------------------------------------------------------------
PLANS = [
    dict(id="03", kind="plan",  src="face_macro", rot=90,
         crop=(0.581, 0.00, 0.845, 1.00), light=(0.80, 0.35), ev=0.94,
         note="ecusson FC CLUSES 1961, lumiere rasante venant de la droite"),

    dict(id="05", kind="plate", src="face_macro", rot=90,
         crop=(0.150, 0.00, 0.430, 0.55), light=(0.20, 0.45), ev=1.00,
         note="sponsor TARIM, plaque pour travelling lateral"),

    dict(id="06", kind="plan",  src="manche_g",   rot=0,
         crop=(0.050, 0.08, 0.970, 0.84), light=(0.50, 0.04), ev=1.00,
         note="couronne + UNIS DANS TOUS NOS DEFIS, tilt descendant"),

    dict(id="07", kind="plan",  src="manche_d",   rot=0,
         crop=(0.080, 0.12, 0.970, 0.84), light=(0.22, 0.18), ev=1.00,
         note="R2 LAuRAFoot + FORCE ROUGE ET NOIR, push-in sec"),

    dict(id="08", kind="plate", src="face_macro", rot=90,
         crop=(0.180, 0.50, 0.850, 1.00), light=(0.10, 0.50), ev=1.02,
         note="FORZAFC, plaque pour travelling lateral rapide"),

    dict(id="11", kind="plan",  src="dos_plein",  rot=0,
         crop=(0.060, 0.09, 0.970, 0.83), light=(0.15, 0.32), ev=1.00,
         note="le 26, pull-back qui decouvre CHAMPIONS"),

    dict(id="12", kind="plate", src="dos_plein",  rot=0,
         crop=(0.060, 0.10, 0.980, 0.25), light=(0.08, 0.50), ev=1.00,
         note="CHAMPIONS, plaque pour travelling lateral"),

    dict(id="13", kind="plan",  src="dos_macro",  rot=0,
         crop=(0.200, 0.22, 0.870, 0.73), light=(0.22, 0.42), ev=1.00,
         note="FC CLUSA plein cadre, le reste dans l'ombre"),

    dict(id="14", kind="plan",  src="dos_macro",  rot=0,
         crop=(0.260, 0.09, 0.780, 0.52), light=(0.50, 0.16), ev=1.10,
         note="Croix de Savoie, point culminant lumineux du film"),

    dict(id="15", kind="plan",  src="dos_macro",  rot=0,
         crop=(0.130, 0.05, 0.900, 0.67), light=(0.50, 0.22), ev=1.03,
         note="plan de fin : Croix de Savoie + FC CLUSA ensemble"),
]


def curve(a):
    """Courbe en S douce : ecrase les noirs vers le fond studio sans bruler l'or.

    Une courbe trop dure delavait le bronze des flocages vers un creme pale et
    poussait le rouge sublime vers le magenta. On garde un contraste tenu mais
    on protege les hautes lumieres.
    """
    a = np.clip(a, 0.0, 1.0)
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = a * 0.42 + s * 0.58          # melange lineaire / S : contraste tempere
    return np.clip(a ** 1.24, 0.0, 1.0)


def warm_gold(a):
    """Ramene les flocages vers l'or bronze mat plutot que vers le creme."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    # masque des zones dorees : chaudes, claires, et pas rouge pur
    gold = np.clip((g - b) * 3.0, 0, 1) * np.clip((r - b) * 2.4, 0, 1) * np.clip(lum * 1.6, 0, 1)
    gold = gold[..., None]
    tint = np.array([1.00, 0.905, 0.66], dtype=np.float32)   # #C79A4B normalise
    return np.clip(a * (1.0 - 0.34 * gold) + a * tint * (0.34 * gold), 0.0, 1.0)


def raking_light(h, w, origin, strength=0.62):
    """Degrade directionnel : simule une source rasante hors champ."""
    oy, ox = origin[1] * h, origin[0] * w
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - ox) / w) ** 2 + ((yy - oy) / h) ** 2)
    d /= max(d.max(), 1e-6)
    return (1.0 - strength * d ** 1.30)[..., None]


def vignette(h, w, strength=0.50):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return np.clip(1.0 - strength * (d / 1.45) ** 2.4, 0.0, 1.0)[..., None]


def boost_red_gold(a):
    """Redonne un peu de corps au rouge, sans le pousser vers le magenta.

    Le gain est volontairement faible : le rouge sublime du maillot est deja
    tres sature a la prise de vue, un boost fort le fait virer rose.
    """
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    warm = np.clip((a[..., 0] - a[..., 2]) * 2.0, 0.0, 1.0)[..., None]
    out = a + (a - lum[..., None]) * (0.16 * warm)
    # le rouge du maillot est orange-rouge, pas rose : on retient le bleu
    out[..., 2] = np.minimum(out[..., 2], a[..., 2] * (1.0 - 0.28 * warm[..., 0]))
    return np.clip(out, 0.0, 1.0)


def crop_to_916(img):
    """Recadre au centre vers le 9:16 exact, sans jamais ajouter de bord noir."""
    w, h = img.size
    if w / h > RATIO_916:
        nw = int(round(h * RATIO_916))
        off = (w - nw) // 2
        return img.crop((off, 0, off + nw, h))
    nh = int(round(w / RATIO_916))
    off = (h - nh) // 2
    return img.crop((0, off, w, off + nh))


def build(plan):
    img = Image.open(os.path.join(SRC, SOURCES[plan["src"]])).convert("RGB")
    if plan["rot"]:
        img = img.rotate(plan["rot"], expand=True, resample=Image.BICUBIC)

    w, h = img.size
    l, t, r, b = plan["crop"]
    img = img.crop((int(l * w), int(t * h), int(r * w), int(b * h)))

    if plan["kind"] == "plan":
        img = crop_to_916(img)

    a = np.asarray(img, dtype=np.float32) / 255.0
    a = np.clip(curve(a) * plan["ev"], 0.0, 1.0)
    a *= raking_light(*a.shape[:2], plan["light"])
    a *= vignette(*a.shape[:2])
    a = boost_red_gold(a)
    a = warm_gold(a)

    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for plan in PLANS:
        path = os.path.join(SRC, SOURCES[plan["src"]])
        if not os.path.exists(path):
            print(f"PLAN-{plan['id']} : source absente ({path}), ignore")
            continue
        prefix = "PLAN" if plan["kind"] == "plan" else "PLATE"
        dest = os.path.join(OUT, f"{prefix}-{plan['id']}.png")
        out = build(plan)
        out.save(dest)
        print(f"{prefix}-{plan['id']}  {out.size[0]}x{out.size[1]}  {plan['note']}")
