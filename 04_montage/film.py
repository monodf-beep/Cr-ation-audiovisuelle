#!/usr/bin/env python3
"""
Monte le film a partir des plans fixes ET des clips generes.

Quatre plans sont maintenant de la vraie video : le maillot deploye qui
ondule, le dos qui respire, la goutte sur le patch, le drapeau qui claque.
Les onze autres restent des images, animees en pan-and-scan.

Le montage doit tenir le style, pas seulement les plans :

  RACCORD   les clips reviennent du modele avec leur propre contraste et
            leur propre balance. On les repasse dans le registre du film,
            sinon la coupe entre un clip et une image se voit.
  COUPE     franche partout. Aucun fondu enchaine : ce n'est pas un
            diaporama qui glisse d'une vue a l'autre, c'est un film qui
            coupe.
  RYTHME    long au debut et a la fin, court au milieu. La sequence des
            flocages tombe a une seconde par plan.
  SILENCE   0,6 s de noir avant le dos. C'est le seul effet du film.

Usage : python3 04_montage/film.py
Sortie : 04_montage/champions-26.mp4  (1080x1920, 24 fps)
"""

import os
import numpy as np
from PIL import Image, ImageFilter
import imageio.v2 as imageio

SRC = "11_final"
CLIPS = "19_clips"
OUT = "04_montage/champions-26.mp4"
W, H, FPS = 1080, 1920, 24

# type    : "image" -> pan-and-scan  |  "clip" -> video retimee
# duree   : secondes a l'ecran
# mouv    : (echelle depart, echelle fin, dx, dy) pour les images
# depart  : position de depart dans le clip, en fraction de sa duree
# registre: "net" (le maillot) ou "sale" (le lieu) ; "nuit" = "sale" + une
#           correction de nuit, pour les deux plans du lieu qui restaient
#           verts et clairs a cote du reste
PLANS = [
    # --- l'objet ---
    ("clip",  "CLIP-PATCH",  3.0, None,                        0.00, "net"),
    ("image", "PLAN-03",     2.0, (1.04, 1.04,  0.6, -0.3),    None, "net"),

    # --- le lieu ---
    ("image", "AMAT-02",     2.0, (1.00, 1.08,  0.0,  0.0),    None, "nuit"),
    ("image", "GP-CRAMPONS", 3.0, (1.00, 1.10,  0.0,  0.0),    None, "nuit"),

    # --- le maillot ---
    ("clip",  "CLIP-FACE",   3.0, None,                        0.00, "net"),
    ("image", "PLATE-08",    2.0, (1.00, 1.00, -1.0,  1.0),    None, "net"),
    ("image", "PLAN-06",     2.0, (1.02, 1.02,  0.0, -0.8),    None, "net"),
    ("image", "PLAN-07",     2.0, (1.00, 1.09,  0.0,  0.0),    None, "net"),
    ("image", "FLAG-01",     1.0, (1.04, 1.04,  0.0,  0.0),    None, "sale"),

    # --- la montee ---
    ("clip",  "CLIP-ULTRAS", 2.0, None,                        0.34, "sale"),

    # --- le dos ---
    ("clip",  "CLIP-DOS",    3.0, None,                        0.00, "net"),
    ("image", "PLAN-11",     1.0, (1.10, 1.00,  0.0,  0.0),    None, "net"),
    ("image", "PLATE-12",    1.0, (1.00, 1.00, -1.0,  0.0),    None, "net"),
    ("image", "PLAN-13",     1.0, (1.03, 1.03,  0.0,  0.0),    None, "net"),
    ("image", "PLAN-15",     1.5, (1.02, 1.02,  0.0,  0.0),    None, "net"),
]

NOIR_AVANT = "CLIP-DOS"
NOIR_DUREE = 0.6


# --------------------------------------------------------------------------
# Raccord : ramener les clips dans le registre du film
# --------------------------------------------------------------------------

SODIUM = np.array([1.02, 1.04, 0.89], dtype=np.float32)
AMBRE = np.array([1.07, 1.00, 0.86], dtype=np.float32)


def raccord_net(a, rng):
    """Le maillot : on rend aux clips le contraste et la dominante du film."""
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = np.clip(a * 0.74 + s * 0.26, 0.0, 1.0)
    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 1.7, 0.0, 1.0) ** 1.4
    a = np.clip(a * (SODIUM * (1.0 - haut) + AMBRE * haut), 0.0, 1.0)
    h, w = a.shape[:2]
    poids = (4.0 * a.mean(axis=2) * (1.0 - a.mean(axis=2)))[..., None]
    return np.clip(a + rng.normal(0, 1, (h, w, 1)).astype(np.float32) * 0.012 * poids, 0, 1)


def raccord_sale(a, rng):
    """Le lieu : bruit epais dans les ombres, bavure des lampes, noirs tenus."""
    lum = a.mean(axis=2)
    hi = np.clip((lum - 0.66) / 0.34, 0.0, 1.0)
    diffus = np.asarray(
        Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30)),
        dtype=np.float32) / 255.0
    a = np.clip(a + diffus[..., None] * np.array([1.00, 0.95, 0.82], np.float32) * 0.12, 0, 1)
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = np.clip(a * 0.60 + s * 0.40, 0.0, 1.0)
    a = a * 0.96 + 0.022
    l2 = a.mean(axis=2, keepdims=True)
    haut = np.clip(l2 * 1.7, 0, 1) ** 1.3
    a = np.clip(a * (np.array([1.00, 1.07, 0.83], np.float32) * (1 - haut)
                     + np.array([1.10, 0.99, 0.77], np.float32) * haut), 0, 1)
    h, w = a.shape[:2]
    sombre = np.clip(1.3 - a.mean(axis=2) * 1.7, 0.0, 1.0)[..., None]
    bruit = rng.normal(0, 1, (h, w, 1)).astype(np.float32)
    return np.clip(a + bruit * 0.045 * sombre, 0.0, 1.0)


def nuit(a):
    """Ramene a la nuit les deux plans du lieu qui restaient clairs et verts.

    Le probleme n'est pas le style, c'est l'heure : a cote de macros
    cuivrees sous projecteur, une pelouse verte bien exposee lit comme un
    autre jour. On ne fabrique pas une fausse nuit — on retire le vert,
    on ferme d'un diaphragme, on laisse la lumiere ne tenir que le sujet.
    """
    # le vert de l'herbe de jour, ramene vers la pelouse sous sodium
    vert = np.clip((a[..., 1] - (a[..., 0] + a[..., 2]) / 2) * 2.6, 0.0, 1.0)[..., None]
    a = a * (1.0 - vert * 0.42) + a * vert * 0.42 * np.array([1.16, 0.86, 0.50], np.float32)

    a = np.clip(a * 0.72, 0.0, 1.0)                       # un diaphragme de moins
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = np.clip(a * 0.45 + s * 0.55, 0.0, 1.0)            # les ombres se ferment

    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 2.1, 0.0, 1.0) ** 1.5            # seules les lampes restent
    a = np.clip(a * (np.array([1.02, 0.94, 0.78], np.float32) * (1 - haut)
                     + np.array([1.12, 1.00, 0.80], np.float32) * haut), 0.0, 1.0)

    h, w = a.shape[:2]                                    # la nuit tombe vers les bords
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return a * np.clip(1.0 - 0.42 * (d / 1.3) ** 2.0, 0.0, 1.0)[..., None]


def raccord(frame, registre, rng):
    a = frame.astype(np.float32) / 255.0
    a = raccord_net(a, rng) if registre == "net" else raccord_sale(a, rng)
    return (a * 255).astype(np.uint8)


# --------------------------------------------------------------------------
# Cadrage
# --------------------------------------------------------------------------

def couvre(im):
    """Remplit le cadre 9:16 sans deformer, en recadrant au centre."""
    r = max(W / im.width, H / im.height)
    im = im.resize((max(W, int(im.width * r)), max(H, int(im.height * r))), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def source(name, registre="net"):
    im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
    r = max(W / im.width, H / im.height) * 1.15   # marge pour les mouvements
    im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    if registre == "nuit":
        a = nuit(np.asarray(im, dtype=np.float32) / 255.0)
        im = Image.fromarray((a * 255).astype(np.uint8))
    return im


def cadre(im, echelle, dx, dy):
    cw, ch = int(W * echelle), int(H * echelle)
    cw, ch = min(cw, im.width), min(ch, im.height)
    mx, my = im.width - cw, im.height - ch
    x = max(0, min(mx, int(mx / 2 + dx * mx / 2)))
    y = max(0, min(my, int(my / 2 + dy * my / 2)))
    return im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS)


def lissage(t):
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------

def frames_clip(name, duree, depart, registre, rng):
    """Prend une fenetre du clip, a sa vitesse reelle.

    Le clip fait cinq secondes, le plan en fait deux ou trois. On ne le
    reechantillonne pas pour l'etaler sur la duree du plan : un ralenti
    synthetique se voit tout de suite, et le mouvement de camera du modele
    est deja cale a la bonne vitesse. On coupe donc dedans, comme on
    couperait dans un rush.
    """
    path = os.path.join(CLIPS, name + ".mp4")
    reader = imageio.get_reader(path)
    brut = [f for f in reader]
    reader.close()
    n_src = len(brut)
    n_out = min(int(duree * FPS), n_src)
    d0 = int(depart * (n_src - n_out))
    for i in range(n_out):
        f = np.asarray(couvre(Image.fromarray(brut[d0 + i]).convert("RGB")))
        yield raccord(f, registre, rng)


def frames_image(name, duree, mouv, registre, rng):
    im = source(name, registre)
    s0, s1, dx, dy = mouv
    n = int(duree * FPS)
    for i in range(n):
        t = lissage(i / max(n - 1, 1))
        yield np.asarray(cadre(im, s0 + (s1 - s0) * t, dx * t, dy * t))


if __name__ == "__main__":
    os.makedirs("04_montage", exist_ok=True)
    rng = np.random.default_rng(1961)
    writer = imageio.get_writer(OUT, fps=FPS, codec="libx264", quality=9,
                                macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    noir = np.zeros((H, W, 3), dtype=np.uint8)
    total = 0

    for kind, name, duree, mouv, depart, registre in PLANS:
        chemin = os.path.join(CLIPS if kind == "clip" else SRC,
                              name + (".mp4" if kind == "clip" else ".jpg"))
        if not os.path.exists(chemin):
            print(f"{name:14s} absent — plan saute")
            continue

        if name == NOIR_AVANT:
            for _ in range(int(NOIR_DUREE * FPS)):
                writer.append_data(noir)
                total += 1

        gen = (frames_clip(name, duree, depart, registre, rng) if kind == "clip"
               else frames_image(name, duree, mouv, registre, rng))
        n = int(duree * FPS)
        dernier = (name == PLANS[-1][1])
        for i, f in enumerate(gen):
            if dernier:                       # fondu au noir sur le dernier plan
                f = (f.astype(np.float32)
                     * max(0.0, 1.0 - max(0.0, (i / n - 0.45)) / 0.55)).astype(np.uint8)
            writer.append_data(f)
            total += 1
        print(f"{name:14s} {duree:>4.1f}s  {kind:5s} {registre}")

    writer.close()
    print(f"\n{OUT}  {total/FPS:.1f}s  {total} images")
