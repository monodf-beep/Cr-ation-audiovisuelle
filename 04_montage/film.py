#!/usr/bin/env python3
"""
Monte le film : dix plans sur seize sont de la vraie video, et il y a du son.

Deux reproches ont fait cette version. Le film n'avait pas de son du tout,
et onze plans sur quinze etaient des images animees en pan-and-scan — ce
qui, meme avec de vrais mouvements de camera, se lit comme un diaporama
des qu'il y en a plusieurs de suite.

Ce qui a change :

  MATIERE  les plans qui trainaient sont devenus des clips. Il ne reste
           d'images que la ou le plan dure moins d'une seconde : a cette
           duree, une image ne se lit pas comme une image mais comme un
           flash.
  RYTHME   les plans sont plus courts et plus nombreux. Le milieu descend
           a une seconde, la fin a sept dixiemes. Seuls trois plans
           durent trois secondes : le maillot deploye, les crampons, le
           dos.
  SON      04_montage/son.py fabrique une piste calee sur ces coupes, avec
           une frappe sur chacune. C'est elle qui tient le rythme autant
           que le montage.
  RACCORD  les clips reviennent du modele avec leur propre contraste ; on
           les repasse dans leur registre, sinon la coupe se voit.

Usage : python3 04_montage/film.py
Sortie : 04_montage/champions-26.mp4  (1080x1920, 24 fps, avec son)
"""

import os
import subprocess
import numpy as np
from PIL import Image, ImageFilter
import imageio.v2 as imageio
import imageio_ffmpeg

SRC = "11_final"
CLIPS = "19_clips"
MUET = "04_montage/champions-26-muet.mp4"
SON = "04_montage/champions-26.wav"
OUT = "04_montage/champions-26.mp4"
W, H, FPS = 1080, 1920, 24

# kind    : "clip" (video) | "image" (pan-and-scan)
# duree   : secondes a l'ecran
# reglage : clip  -> (depart dans le clip 0-1, zoom de recadrage, dx, dy)
#           image -> (echelle depart, echelle fin, dx, dy)
# registre: "net" (le maillot) | "sale" (le lieu) | "nuit" (lieu de jour a corriger)
PLANS = [
    # --- l'objet : deux macros, lumiere dure ---
    ("clip",  "CLIP-R2",       2.5, (0.00, 1.00,  0.0,  0.0), "net"),
    # on remonte le cadre : le bas du clip garde le haut de FORZAFC coupe en
    # deux, et une demi-lettre se lit comme du texte casse
    ("clip",  "CLIP-ECUSSON",  2.5, (0.00, 1.45,  0.0, -0.75), "net"),

    # --- le lieu : un flash, puis les crampons ---
    ("image", "AMAT-02",       1.0, (1.00, 1.06,  0.0,  0.0), "nuit"),
    # le clip est deja tourne de nuit : pas de correction d'heure a lui appliquer
    ("clip",  "CLIP-CRAMPONS", 3.0, (0.00, 1.00,  0.0,  0.0), "sale"),

    # --- le maillot : le produit occupe le film ---
    ("clip",  "CLIP-FACE",     3.0, (0.00, 1.00,  0.0,  0.0), "net"),
    # on reste sur le debut de ces deux clips : plus loin, un pli du tissu
    # deforme le flocage et le mot devient illisible
    ("clip",  "CLIP-FORZA",    1.5, (0.00, 1.00,  0.0,  0.0), "net"),
    ("clip",  "CLIP-MANCHE",   1.5, (0.00, 1.00,  0.0,  0.0), "net"),
    ("clip",  "CLIP-FORCE",    1.2, (0.35, 1.00,  0.0,  0.0), "net"),
    ("clip",  "CLIP-FACE",     1.0, (0.70, 1.10,  0.0,  0.0), "net"),
    ("clip",  "CLIP-FLAG",     1.0, (0.30, 1.00,  0.0,  0.0), "sale"),

    # --- la montee ---
    ("clip",  "CLIP-ULTRAS",   2.0, (0.34, 1.00,  0.0,  0.0), "sale"),

    # --- le dos ---
    ("clip",  "CLIP-DOS",      3.0, (0.00, 1.00,  0.0,  0.0), "net"),
    ("image", "PLAN-11",       0.7, (1.06, 1.00,  0.0,  0.0), "net"),
    ("image", "PLATE-12",      0.7, (1.00, 1.00, -0.6,  0.0), "net"),
    ("image", "PLAN-13",       0.7, (1.03, 1.03,  0.0,  0.0), "net"),
    ("image", "PLAN-15",       1.8, (1.00, 1.04,  0.0,  0.0), "net"),
]

NOIR_AVANT = "CLIP-DOS"
NOIR_DUREE = 0.5


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
    """Ramene a la nuit les plans du lieu qui restaient clairs et verts.

    Le probleme n'est pas le style, c'est l'heure : a cote de macros
    cuivrees sous projecteur, une pelouse verte bien exposee lit comme un
    autre jour. On ne fabrique pas une fausse nuit — on retire le vert, on
    ferme d'un diaphragme, on laisse la lumiere ne tenir que le sujet.
    """
    vert = np.clip((a[..., 1] - (a[..., 0] + a[..., 2]) / 2) * 2.6, 0.0, 1.0)[..., None]
    a = a * (1.0 - vert * 0.42) + a * vert * 0.42 * np.array([1.16, 0.86, 0.50], np.float32)

    a = np.clip(a * 0.72, 0.0, 1.0)
    s = np.where(a < 0.5, 2.0 * a * a, 1.0 - 2.0 * (1.0 - a) ** 2)
    a = np.clip(a * 0.45 + s * 0.55, 0.0, 1.0)

    lum = a.mean(axis=2, keepdims=True)
    haut = np.clip(lum * 2.1, 0.0, 1.0) ** 1.5
    a = np.clip(a * (np.array([1.02, 0.94, 0.78], np.float32) * (1 - haut)
                     + np.array([1.12, 1.00, 0.80], np.float32) * haut), 0.0, 1.0)

    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return a * np.clip(1.0 - 0.42 * (d / 1.3) ** 2.0, 0.0, 1.0)[..., None]


def raccord(frame, registre, rng):
    a = frame.astype(np.float32) / 255.0
    if registre == "net":
        a = raccord_net(a, rng)
    else:
        a = raccord_sale(a, rng)
        if registre == "nuit":
            a = nuit(a)
    return (a * 255).astype(np.uint8)


# --------------------------------------------------------------------------
# Cadrage
# --------------------------------------------------------------------------

def couvre(im, zoom=1.0, dx=0.0, dy=0.0):
    """Remplit le cadre 9:16 sans deformer, avec un recadrage optionnel.

    Le zoom sert a sortir du cadre ce que le modele a laisse au bord : un
    mot coupe en deux au bas de l'image se lit comme du texte casse, alors
    qu'il suffit de le cadrer dehors.
    """
    r = max(W / im.width, H / im.height) * zoom
    im = im.resize((max(W, int(im.width * r)), max(H, int(im.height * r))), Image.LANCZOS)
    mx, my = im.width - W, im.height - H
    x = int(np.clip(mx / 2 + dx * mx / 2, 0, mx))
    y = int(np.clip(my / 2 + dy * my / 2, 0, my))
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

_cache = {}


def lire(name):
    if name not in _cache:
        r = imageio.get_reader(os.path.join(CLIPS, name + ".mp4"))
        _cache[name] = [f for f in r]
        r.close()
    return _cache[name]


def frames_clip(name, duree, reglage, registre, rng):
    """Prend une fenetre du clip, a sa vitesse reelle.

    On ne reechantillonne pas pour etaler le clip sur la duree du plan : un
    ralenti synthetique se voit tout de suite, et le mouvement de camera du
    modele est deja cale a la bonne vitesse. On coupe dedans, comme dans un
    rush.
    """
    depart, zoom, dx, dy = reglage
    brut = lire(name)
    n_src = len(brut)
    n_out = min(int(duree * FPS), n_src)
    d0 = int(depart * (n_src - n_out))
    for i in range(n_out):
        f = np.asarray(couvre(Image.fromarray(brut[d0 + i]).convert("RGB"), zoom, dx, dy))
        yield raccord(f, registre, rng)


def frames_image(name, duree, reglage, registre, rng):
    im = source(name, registre)
    s0, s1, dx, dy = reglage
    n = int(duree * FPS)
    for i in range(n):
        t = lissage(i / max(n - 1, 1))
        yield np.asarray(cadre(im, s0 + (s1 - s0) * t, dx * t, dy * t))


if __name__ == "__main__":
    os.makedirs("04_montage", exist_ok=True)
    rng = np.random.default_rng(1961)
    writer = imageio.get_writer(MUET, fps=FPS, codec="libx264", quality=9,
                                macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    noir = np.zeros((H, W, 3), dtype=np.uint8)
    total = 0

    for kind, name, duree, reglage, registre in PLANS:
        ext = ".mp4" if kind == "clip" else ".jpg"
        chemin = os.path.join(CLIPS if kind == "clip" else SRC, name + ext)
        if not os.path.exists(chemin):
            print(f"{name:14s} absent — plan saute")
            continue

        if name == NOIR_AVANT:
            for _ in range(int(NOIR_DUREE * FPS)):
                writer.append_data(noir)
                total += 1

        gen = (frames_clip if kind == "clip" else frames_image)(
            name, duree, reglage, registre, rng)
        n = int(duree * FPS)
        dernier = (name == PLANS[-1][1])
        for i, f in enumerate(gen):
            if dernier:                       # fondu au noir sur le dernier plan
                f = (f.astype(np.float32)
                     * max(0.0, 1.0 - max(0.0, (i / n - 0.40)) / 0.60)).astype(np.uint8)
            writer.append_data(f)
            total += 1
        print(f"{total/FPS - duree:>5.1f}s  {name:14s} {duree:>4.1f}s  {kind:5s} {registre}")

    writer.close()
    print(f"\nimage : {total/FPS:.1f}s  {total} images")

    if os.path.exists(SON):
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", MUET, "-i", SON,
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", OUT], check=True)
        print(f"{OUT}  image + son")
    else:
        print(f"{SON} absent — lancer d'abord 04_montage/son.py")
