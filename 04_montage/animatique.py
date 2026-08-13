#!/usr/bin/env python3
"""
Monte l'animatique du film a partir des plans fixes.

Les mouvements du decoupage sont tous des mouvements de camera sur une
surface : derive, travelling lateral, push-in, pull-back, tilt. Aucun ne
demande que la matiere bouge. Ils se font donc en pan-and-scan sur les
images haute definition, ce qui donne un resultat exact et ne coute rien.

Seuls quelques plans auraient besoin d'un vrai modele video : le tissu qui
flotte, un drapeau qui claque, les lampes qui s'amorcent. Ils sont montes
ici en mouvement simple, et pourront etre remplaces plan par plan sans
toucher au reste.

Usage : python3 04_montage/animatique.py
Sortie : 04_montage/champions-26.mp4  (1080x1920, 24 fps)
"""

import os
import numpy as np
from PIL import Image
import imageio.v2 as imageio

SRC = "11_final"
OUT = "04_montage/champions-26.mp4"
W, H, FPS = 1080, 1920, 24

# duree : secondes
# mouvement : (echelle depart, echelle fin, dx, dy) — dx/dy en fraction de la
#             marge disponible, donc independants de la taille de la source
PLANS = [
    ("GP-LIGNE",   2.0, (1.06, 1.06, -0.5,  0.5), "dérive latérale"),
    ("GP-PISTE",   2.0, (1.08, 1.08,  0.4, -0.5), "travelling bas"),
    ("VESTIAIRE",  3.0, (1.00, 1.07,  0.0,  0.0), "push-in très lent"),
    ("PLAN-01",    2.0, (1.06, 1.06, -0.5,  0.0), "dérive latérale"),

    ("GP-MARCHES", 2.0, (1.04, 1.04,  0.2,  0.2), "fixe"),
    ("GP-DRAPEAUX",2.0, (1.03, 1.05,  0.0,  0.0), "fixe, léger"),
    ("GP-CRAMPONS",2.0, (1.00, 1.10,  0.0,  0.0), "push-in sec"),
    ("PLAN-03",    2.0, (1.04, 1.04,  0.6, -0.3), "balayage"),
    ("GP-MANCHE",  2.0, (1.05, 1.05, -0.3,  0.0), "fixe, flou de bougé"),
    ("PLATE-08",   2.0, (1.00, 1.00, -1.0,  1.0), "travelling rapide"),
    ("PLAN-06",    1.0, (1.02, 1.02,  0.0, -0.8), "tilt descendant"),
    ("GP-NUQUES",  2.0, (1.04, 1.04,  0.2,  0.0), "fixe"),
    ("PLAN-07",    2.0, (1.00, 1.09,  0.0,  0.0), "push-in sec"),

    ("PLAN-02",    2.0, (1.00, 1.06,  0.0,  0.0), "push-in lent"),
    ("GP-DOS",     3.0, (1.00, 1.06,  0.0,  0.0), "arrêt sec puis push-in"),
    ("PLAN-11",    1.0, (1.10, 1.00,  0.0,  0.0), "pull-back"),
    ("PLATE-12",   1.0, (1.00, 1.00, -1.0,  0.0), "travelling latéral"),
    ("GP-BRAS",    2.0, (1.03, 1.05,  0.0,  0.0), "fixe"),
    ("GP-FAUCIGNY",1.0, (1.04, 1.04,  0.0,  0.0), "fixe"),
    ("PLAN-13",    1.0, (1.03, 1.03,  0.0,  0.0), "arrêt sec"),
    ("PLAN-14",    1.0, (1.00, 1.05,  0.0,  0.0), "push-in minimal"),
    ("PLAN-15",    1.5, (1.02, 1.02,  0.0,  0.0), "fondu au noir"),
]

# Le silence du montage : une seconde noire avant que le dos apparaisse.
# C'est l'effet principal du film, il doit exister dans l'animatique meme
# sans bande son.
NOIR_AVANT = "GP-DOS"
NOIR_DUREE = 0.6


def source(name):
    im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
    # on remplit le cadre 9:16 sans deformer
    r = max(W / im.width, H / im.height) * 1.15   # marge pour les mouvements
    im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    return im


def cadre(im, echelle, dx, dy):
    """Extrait un cadre 9:16 a l'echelle et a la position demandees."""
    cw, ch = int(W * echelle), int(H * echelle)
    cw, ch = min(cw, im.width), min(ch, im.height)
    mx, my = im.width - cw, im.height - ch
    x = int(mx / 2 + dx * mx / 2)
    y = int(my / 2 + dy * my / 2)
    x = max(0, min(mx, x)); y = max(0, min(my, y))
    return im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)


def lissage(t):
    """Amorce et sortie douces : une camera ne demarre jamais a pleine vitesse."""
    return t * t * (3 - 2 * t)


if __name__ == "__main__":
    os.makedirs("04_montage", exist_ok=True)
    writer = imageio.get_writer(OUT, fps=FPS, codec="libx264", quality=8,
                                macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    noir = np.zeros((H, W, 3), dtype=np.uint8)
    total = 0

    for name, duree, (s0, s1, dx, dy), note in PLANS:
        chemin = os.path.join(SRC, name + ".jpg")
        if not os.path.exists(chemin):
            print(f"{name} : absent, plan saute")
            continue

        if name == NOIR_AVANT:
            for _ in range(int(NOIR_DUREE * FPS)):
                writer.append_data(noir)
                total += 1

        im = source(name)
        n = int(duree * FPS)
        dernier = (name == PLANS[-1][0])
        for i in range(n):
            t = lissage(i / max(n - 1, 1))
            f = cadre(im, s0 + (s1 - s0) * t, dx * t, dy * t)
            a = np.asarray(f, dtype=np.float32)
            if dernier:                       # fondu au noir sur le dernier plan
                a *= max(0.0, 1.0 - max(0.0, (i / n - 0.45)) / 0.55)
            writer.append_data(a.astype(np.uint8))
            total += 1
        print(f"{name:14s} {duree:>4.1f}s  {note}")

    writer.close()
    print(f"\n{OUT}  {total/FPS:.1f}s  {total} images")
