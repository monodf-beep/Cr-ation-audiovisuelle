#!/usr/bin/env python3
"""
Fabrique les gros plans du film a partir des images deja validees.

Aucune generation. Le probleme de coherence venait des plans larges, qui
portent tout le stade et doivent donc s'accorder entre eux sur la geometrie,
la saison, l'effectif et la lumiere. Un gros plan ne porte presque rien : il
n'a rien dans le cadre pour contredire le plan d'a cote.

Plutot que de refabriquer une serie neuve, qui se serait a nouveau eloignee
de ce qui etait acquis, on entre dans les images validees : on recadre au
plus pres, on creuse la profondeur de champ que le telephone n'avait pas, et
on ramene la lumiere sur le sujet.

Dans l'ordre :
  recadrage normalise -> flou croissant hors zone de nettete
  -> chute de lumiere vers les bords -> accent lumineux sur le sujet

Usage : python3 03_etalonnage/gros_plan.py
Entree : 11_final/  (images deja etalonnees)
Sortie : 17_gros_plans/
"""

import os
import numpy as np
from PIL import Image, ImageFilter

SRC = "11_final"
OUT = "17_gros_plans"

# crop  : (gauche, haut, droite, bas) en fraction de l'image source
# focus : (x, y, rayon) de la zone nette, en fraction du cadre recadre
# flou  : rayon maximal du flou aux bords, en pixels
# accent: (x, y, force) du renfort lumineux
PLANS = [
    # --- le lieu, tire des photographies reelles du club ---
    dict(id="GP-LIGNE", src="REEL-01", crop=(0.10, 0.58, 0.72, 0.90),
         focus=(0.45, 0.45, 0.30), flou=13, accent=(0.45, 0.40, 0.07),
         note="la ligne blanche et les bandes de tonte"),
    dict(id="GP-PISTE", src="REEL-05", crop=(0.02, 0.62, 0.60, 0.94),
         focus=(0.40, 0.50, 0.28), flou=14, accent=(0.35, 0.45, 0.06),
         note="la piste et le bord de terrain"),

    # --- le public, sans geographie ---
    dict(id="GP-DRAPEAUX", src="ULTRAS", crop=(0.32, 0.30, 0.86, 0.62),
         focus=(0.50, 0.45, 0.30), flou=15, accent=(0.50, 0.40, 0.08),
         note="deux drapeaux au-dessus du noyau"),
    dict(id="GP-NUQUES", src="TRIBUNE-PLEINE", crop=(0.06, 0.60, 0.72, 0.98),
         focus=(0.42, 0.42, 0.28), flou=16, accent=(0.42, 0.38, 0.06),
         note="des nuques et des epaules dans les gradins"),
    dict(id="GP-MARCHES", src="ARRIVEE", crop=(0.10, 0.62, 0.78, 0.98),
         focus=(0.45, 0.45, 0.30), flou=15, accent=(0.45, 0.40, 0.06),
         note="des jambes qui montent les marches"),
    dict(id="GP-BRAS", src="ULTRAS-FIN", crop=(0.30, 0.40, 0.88, 0.76),
         focus=(0.50, 0.45, 0.30), flou=15, accent=(0.50, 0.38, 0.08),
         note="des bras leves et un drapeau"),

    # --- le drapeau du Faucigny ---
    dict(id="GP-FAUCIGNY", src="FLAG-02", crop=(0.14, 0.16, 0.90, 0.60),
         focus=(0.50, 0.45, 0.32), flou=14, accent=(0.50, 0.40, 0.07),
         note="le drapeau brandi, tissu plein cadre"),

    # --- le maillot porte ---
    dict(id="GP-MANCHE", src="MATCH-ETE", crop=(0.42, 0.02, 0.98, 0.34),
         focus=(0.55, 0.45, 0.30), flou=13, accent=(0.55, 0.40, 0.07),
         note="la manche trempee et le patch R2"),
    dict(id="GP-DOS", src="DOS-ETE", crop=(0.14, 0.26, 0.92, 0.72),
         focus=(0.50, 0.48, 0.34), flou=12, accent=(0.50, 0.42, 0.06),
         note="le dos porte, CHAMPIONS et le 26"),

    # --- les crampons ---
    dict(id="GP-CRAMPONS", src="AMAT-05", crop=(0.02, 0.36, 0.78, 0.88),
         focus=(0.42, 0.45, 0.30), flou=13, accent=(0.42, 0.40, 0.06),
         note="les crampons dans l'herbe seche"),
]


def masque_flou(h, w, focus):
    """Distance a la zone nette, normalisee : 0 au centre du sujet, 1 aux bords."""
    fx, fy, r = focus
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w) - fx) ** 2 + ((yy / h) - fy) ** 2)
    return np.clip((d - r) / max(1.0 - r, 1e-6), 0.0, 1.0) ** 1.25


def profondeur(img, focus, rayon):
    """Creuse la profondeur de champ que le petit capteur n'avait pas.

    On empile quelques versions de plus en plus floues et on interpole selon
    la distance au sujet : un flou unique applique en masque laisse une
    frontiere visible, alors qu'un degrade en couches se lit comme une vraie
    bascule optique.
    """
    a = np.asarray(img, dtype=np.float32) / 255.0
    h, w = a.shape[:2]
    m = masque_flou(h, w, focus)[..., None]

    couches = [a]
    for k in (0.35, 0.7, 1.0):
        b = np.asarray(img.filter(ImageFilter.GaussianBlur(rayon * k)),
                       dtype=np.float32) / 255.0
        couches.append(b)

    n = len(couches) - 1
    pos = m[..., 0] * n
    bas = np.clip(np.floor(pos), 0, n - 1).astype(np.int32)
    frac = (pos - bas)[..., None]
    out = np.zeros_like(a)
    for i in range(n):
        sel = (bas == i)[..., None]
        out += sel * (couches[i] * (1 - frac) + couches[i + 1] * frac)
    return out


def lumiere(a, accent):
    """Ramene l'image au registre des plans deja valides.

    Ce registre n'est pas seulement sombre : il tient a la difference entre
    un sujet tenu par la lumiere et un pourtour qui tombe vite. La chute est
    donc forte et le plancher bas, la dominante sodium vert-orange, et les
    hautes lumieres bavent au lieu de s'ecreter proprement.
    """
    h, w = a.shape[:2]
    ax, ay, force = accent
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w) - ax) ** 2 + ((yy / h) - ay) ** 2)

    chute = np.clip(1.0 - 0.46 * (d / 0.80) ** 2.0, 0.44, 1.0)[..., None]
    a = a * chute

    # dominante sodium : vert dans les demi-teintes, ambre dans les hautes
    lum = a.mean(axis=2, keepdims=True)
    sodium = np.array([1.01, 1.04, 0.88], dtype=np.float32)
    ambre = np.array([1.06, 1.00, 0.87], dtype=np.float32)
    haut = np.clip(lum * 1.8, 0.0, 1.0) ** 1.4
    a = a * (sodium * (1.0 - haut) + ambre * haut)

    halo = np.clip(1.0 - d / 0.55, 0.0, 1.0)[..., None] ** 2
    a = a + halo * np.array([1.00, 0.93, 0.76], dtype=np.float32) * force

    # bavure des hautes lumieres : les lampes debordent au lieu de s'ecreter
    hi = np.clip((a.mean(axis=2) - 0.72) / 0.28, 0.0, 1.0)
    bloom = np.asarray(
        Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(24)),
        dtype=np.float32) / 255.0
    a = a + bloom[..., None] * np.array([1.00, 0.86, 0.62], dtype=np.float32) * 0.14

    return np.clip(a, 0.0, 1.0)


def build(plan):
    img = Image.open(os.path.join(SRC, plan["src"] + ".jpg")).convert("RGB")
    w, h = img.size
    l, t, r, b = plan["crop"]
    img = img.crop((int(l * w), int(t * h), int(r * w), int(b * h)))

    # cadre 9:16 au centre du recadrage
    w, h = img.size
    if w / h > 9 / 16:
        nw = int(round(h * 9 / 16))
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(round(w * 16 / 9))
        off = max(0, (h - nh) // 2)
        img = img.crop((0, off, w, min(h, off + nh)))

    a = profondeur(img, plan["focus"], plan["flou"])
    a = lumiere(a, plan["accent"])
    out = Image.fromarray((a * 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(radius=2, percent=45, threshold=3))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for plan in PLANS:
        src = os.path.join(SRC, plan["src"] + ".jpg")
        if not os.path.exists(src):
            print(f"{plan['id']} : source absente ({plan['src']})")
            continue
        res = build(plan)
        res.save(os.path.join(OUT, plan["id"] + ".jpg"), quality=90, subsampling=2)
        print(f"{plan['id']:14s} {res.size[0]}x{res.size[1]}  <- {plan['src']:16s} {plan['note']}")
