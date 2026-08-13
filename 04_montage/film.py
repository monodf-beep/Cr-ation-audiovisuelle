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

import json
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio.v2 as imageio
import imageio_ffmpeg

SRC = "11_final"
CLIPS = "19_clips"
MUET = "04_montage/champions-26-muet.mp4"
SON = "04_montage/champions-26.wav"
OUT = "04_montage/champions-26.mp4"
W, H, FPS = 1080, 1920, 24

# kind    : "clip" (video) | "image" (pan-and-scan) | "amorce" (allumage synthetise)
# duree   : secondes a l'ecran
# reglage : clip   -> (depart dans le clip 0-1, zoom de recadrage, dx, dy)
#           image  -> (echelle depart, echelle fin, dx, dy)
#           amorce -> (echelle depart, echelle fin, dx, dy)
# registre: "net" (le maillot) | "sale" (le lieu) | "nuit" (lieu de jour a corriger)
PLANS = [
    # --- l'amorce : noir, un claquement, les lampes s'accrochent ---
    ("amorce", "MACRO-LAMPE",  1.7, (1.10, 1.00,  0.0,  0.0), "sale"),
    # un joueur seul, de dos, sous le mat qui vient de s'allumer. Ces deux
    # silhouettes-la sont les seules utilisables avant la fin : sur toutes
    # les autres on lit le dos, et le dos est le secret du film.
    ("image", "ETE-SILHOUETTE", 1.0, (1.00, 1.07,  0.0,  0.0), "nuit"),

    # --- l'objet : deux macros, lumiere dure ---
    # On entre tout a la fin du clip. Ailleurs l'epaule se deforme en
    # cherchant le raccord avec la photo de depart, et ca se voyait : c'est
    # la seule seconde et demie ou le mouvement est naturel.
    ("clip",  "CLIP-R2",       1.4, (0.95, 1.00,  0.0,  0.0), "net"),
    # on remonte le cadre : le bas du clip garde le haut de FORZAFC coupe en
    # deux, et une demi-lettre se lit comme du texte casse
    ("clip",  "CLIP-ECUSSON",  1.6, (0.10, 1.45,  0.0, -0.75), "net"),

    # --- le lieu ---
    # le clip est deja tourne de nuit : pas de correction d'heure a lui appliquer
    ("clip",  "CLIP-CRAMPONS", 1.8, (0.00, 1.00,  0.0,  0.0), "sale"),
    ("image", "MACRO-CRAIE",   0.5, (1.00, 1.10,  0.0,  0.0), "sale"),

    # --- le maillot : le produit occupe le film ---
    ("clip",  "CLIP-FACE",     2.0, (0.00, 1.00,  0.0,  0.0), "net"),
    ("clip",  "CLIP-MANCHE",   1.1, (0.00, 1.00,  0.0,  0.0), "net"),
    ("image", "MACRO-FILET",   0.5, (1.00, 1.08,  0.0,  0.0), "sale"),
    # le patch R2 ouvre le film ; le remontrer ici puis dans la rafale le
    # rendait banal, on revient sur l'ecusson a la place
    ("clip",  "CLIP-ECUSSON",  0.8, (0.62, 1.45,  0.0, -0.75), "net"),
    ("clip",  "CLIP-FACE",     0.8, (0.70, 1.12,  0.0,  0.0), "net"),
    ("clip",  "CLIP-FLAG",     0.8, (0.30, 1.00,  0.0,  0.0), "sale"),

    # --- le vrai lieu, une seconde avant la ferveur ---
    # Une vraie photo du club : la tribune, la piste, le banc de touche, de
    # nuit, projecteur allume. Elle passe par la meme passe que les clips du
    # lieu, sinon elle se poserait a cote du film au lieu d'y entrer.
    ("image", "TRIBUNE",       0.7, (1.00, 1.06,  0.0,  0.0), "reel"),

    # --- la montee : le noyau au drapeau, c'est le sommet du film ---
    ("clip",  "CLIP-ULTRAS",   2.4, (0.30, 1.00,  0.0,  0.0), "sale"),
    ("clip",  "CLIP-SAVOIE",   0.5, (0.50, 1.00,  0.0,  0.0), "sale"),

    # --- la rafale : quatre coupes en un peu plus d'une seconde ---
    # il y avait deux plans de chaussure a la suite ; un seul suffit
    ("clip",  "CLIP-CRAMPONS", 0.4, (0.80, 1.10,  0.0,  0.0), "sale"),
    ("clip",  "CLIP-FLAG",     0.4, (0.75, 1.10,  0.0,  0.0), "sale"),
    ("clip",  "CLIP-ULTRAS",   0.4, (0.88, 1.10,  0.0,  0.0), "sale"),
    ("clip",  "CLIP-MANCHE",   0.3, (0.85, 1.10,  0.0,  0.0), "net"),

    # --- l'intense : la revelation, puis la marque de plus en plus serree ---
    ("clip",  "CLIP-DOS",      2.4, (0.00, 1.00,  0.0,  0.0), "net"),
    ("image", "PLAN-11",       0.4, (1.06, 1.00,  0.0,  0.0), "net"),
    # on serre sur la croix seule : le bas de PLAN-14 porte un FC CLUSA
    # tronque dans l'image source, qu'aucun cadrage ne repare
    ("image", "PLAN-14",       0.3, (0.68, 0.68,  0.0, -0.55), "net"),
    ("image", "FIN-CROIX",     0.3, (1.00, 1.00,  0.0,  0.0), "net"),
    # FC CLUSA est tronque dans PLAN-13 et PLAN-15 des l'image source ;
    # 03_etalonnage/fin.py le redecoupe entier dans le haut du dos
    ("image", "FIN-CLUSA",     1.1, (1.00, 1.06,  0.0,  0.0), "net"),

    # --- l'apaisement : le film s'arrete sur le maillot porte, de dos ---
    # Apres la rafale et les quatre coupes courtes, tout retombe. Un seul
    # plan, long, sans coupe, ou il ne se passe plus rien : c'est ce qui
    # fait exister l'intensite qui precede.
    ("image", "DOS",           3.4, (1.00, 1.05,  0.0,  0.0), "nuit"),
]

# noir avant : le plan devant lequel on pose un noir, et sa duree
NOIRS = {"CLIP-DOS": 0.5}


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


def source(name, registre="net", rng=None):
    im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
    r = max(W / im.width, H / im.height) * 1.15   # marge pour les mouvements
    im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
    if registre in ("nuit", "reel"):
        a = np.asarray(im, dtype=np.float32) / 255.0
        # "reel" : une vraie photo du club, qu'on fait entrer dans le registre
        # du film au lieu de la poser telle quelle a cote. C'est la meme
        # passe que celle appliquee aux clips du lieu.
        if registre == "reel":
            a = raccord_sale(a, rng if rng is not None else np.random.default_rng(0))
        a = nuit(a)
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
    im = source(name, registre, rng)
    s0, s1, dx, dy = reglage
    n = int(duree * FPS)
    for i in range(n):
        t = lissage(i / max(n - 1, 1))
        yield np.asarray(cadre(im, s0 + (s1 - s0) * t, dx * t, dy * t))


# --------------------------------------------------------------------------
# L'amorce : les projecteurs s'accrochent
# --------------------------------------------------------------------------

# Une lampe a decharge ne s'allume pas, elle s'amorce : un eclair, un raté,
# un deuxieme eclair, puis une montee lente pendant qu'elle chauffe. C'est
# ce profil-la qu'on suit, et le son tape sur les deux eclairs.
AMORCE = [(0.00, 0.02), (0.10, 0.02), (0.115, 0.92), (0.155, 0.92),
          (0.20, 0.07), (0.27, 0.07), (0.285, 0.62), (0.33, 0.62),
          (0.39, 0.13), (0.47, 0.30), (0.70, 0.72), (1.00, 1.00)]


def frames_amorce(name, duree, reglage, registre, rng):
    im = source(name, registre, rng)
    s0, s1, dx, dy = reglage
    n = int(duree * FPS)
    base = np.asarray(cadre(im, s0, 0.0, 0.0), dtype=np.float32) / 255.0
    for i in range(n):
        u = i / max(n - 1, 1)
        k = float(np.interp(u, [p[0] for p in AMORCE], [p[1] for p in AMORCE]))
        k *= 1.0 + (0.05 if u > 0.4 else 0.0) * rng.normal()   # le filament tremble
        k = max(k, 0.0)
        t = lissage(u)
        a = np.asarray(cadre(im, s0 + (s1 - s0) * t, dx * t, dy * t),
                       dtype=np.float32) / 255.0
        # sous-exposition franche, puis la lampe deborde a mesure qu'elle monte
        a = a * (0.06 + 0.94 * k) ** 1.25
        hi = np.clip((a.mean(axis=2) - 0.55) / 0.45, 0.0, 1.0)
        bloom = np.asarray(
            Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(34)),
            dtype=np.float32) / 255.0
        a = a + bloom[..., None] * np.array([1.00, 0.92, 0.72], np.float32) * (0.55 * k)
        yield (np.clip(a, 0.0, 1.0) * 255).astype(np.uint8)
    del base


# --------------------------------------------------------------------------
# L'outro
# --------------------------------------------------------------------------

POLICE = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
OR = (199, 154, 75)
CREME = (237, 234, 227)
GRIS = (124, 130, 150)


def espace(d, texte, police, y, couleur, suivi, ancre_x=None):
    """Ecrit un texte centre avec un interlettrage, et rend sa largeur."""
    larg = [d.textlength(c, font=police) for c in texte]
    total = sum(larg) + suivi * (len(texte) - 1)
    x = (W - total) / 2 if ancre_x is None else ancre_x
    for c, l in zip(texte, larg):
        d.text((x, y), c, font=police, fill=couleur)
        x += l + suivi
    return total


def carton():
    """Le carton de fin, dans la langue du maillot : de l'or sur du noir."""
    im = Image.new("RGB", (W, H), (10, 12, 19))
    d = ImageDraw.Draw(im)
    def ajuste(texte, corps, suivi, part):
        """Descend le corps jusqu'a ce que la ligne tienne dans la largeur.

        Une ligne de titre calee au pixel pres finit toujours par sortir du
        cadre des qu'on touche au texte ou a la police. On mesure.
        """
        while corps > 12:
            f = ImageFont.truetype(POLICE, corps)
            if sum(d.textlength(c, font=f) for c in texte) + suivi * (len(texte) - 1) <= W * part:
                return f
            corps -= 2
        return ImageFont.truetype(POLICE, 12)

    p_sur = ajuste("CHAMPIONS", 62, 30, 0.62)
    p_nom = ajuste("FC CLUSES", 208, -3, 0.84)
    p_an = ajuste("1961", 60, 20, 0.30)
    p_bas = ajuste("R2 · LAuRAFoot · 26", 50, 12, 0.70)

    y = H * 0.31
    espace(d, "CHAMPIONS", p_sur, y, OR, 30)
    y += 132
    largeur = espace(d, "FC CLUSES", p_nom, y, CREME, -3)
    y += 268
    d.line([(W - largeur) / 2, y, (W + largeur) / 2, y], fill=OR, width=4)
    y += 42
    espace(d, "1961", p_an, y, OR, 20)
    y += 168
    espace(d, "R2 · LAuRAFoot · 26", p_bas, y, GRIS, 12)
    return im


def frames_carton(name, duree, reglage, registre, rng):
    im = carton()
    s0, s1, dx, dy = reglage
    n = int(duree * FPS)
    marge = im.resize((int(W * 1.06), int(H * 1.06)), Image.LANCZOS)
    for i in range(n):
        u = i / max(n - 1, 1)
        f = np.asarray(cadre(marge, s0 + (s1 - s0) * lissage(u), 0.0, 0.0),
                       dtype=np.float32) / 255.0
        h, w = f.shape[:2]                              # le meme grain que le film
        poids = (4.0 * f.mean(axis=2) * (1.0 - f.mean(axis=2)))[..., None]
        f = np.clip(f + rng.normal(0, 1, (h, w, 1)).astype(np.float32) * 0.016 * poids
                    + rng.normal(0, 1, (h, w, 1)).astype(np.float32) * 0.004, 0, 1)
        f *= max(0.0, 1.0 - max(0.0, (u - 0.78)) / 0.22)   # fondu au noir a la fin
        yield (f * 255).astype(np.uint8)


GEN = {"clip": frames_clip, "image": frames_image,
       "amorce": frames_amorce, "carton": frames_carton}


if __name__ == "__main__":
    os.makedirs("04_montage", exist_ok=True)
    rng = np.random.default_rng(1961)
    writer = imageio.get_writer(MUET, fps=FPS, codec="libx264", quality=9,
                                macro_block_size=1, ffmpeg_params=["-pix_fmt", "yuv420p"])
    noir = np.zeros((H, W, 3), dtype=np.uint8)
    total = 0
    # Les coupes reelles, en secondes, ecrites pour que 04_montage/son.py se
    # cale dessus. Les durees demandees ne tombent pas toutes sur une image
    # entiere : si le son recalculait les memes sommes de son cote, il
    # deriverait d'une image ou deux sur les frappes.
    journal = {"fps": FPS, "coupes": [], "noirs": []}

    for kind, name, duree, reglage, registre in PLANS:
        if kind in ("clip", "image"):
            ext = ".mp4" if kind == "clip" else ".jpg"
            chemin = os.path.join(CLIPS if kind == "clip" else SRC, name + ext)
            if not os.path.exists(chemin):
                print(f"{name:14s} absent — plan saute")
                continue

        if name in NOIRS:
            journal["noirs"].append([total / FPS, NOIRS[name]])
            for _ in range(int(NOIRS[name] * FPS)):
                writer.append_data(noir)
                total += 1

        depart = total / FPS
        journal["coupes"].append([depart, name, kind])
        n = int(duree * FPS)
        dernier = (name == PLANS[-1][1])
        for i, f in enumerate(GEN[kind](name, duree, reglage, registre, rng)):
            if dernier:                   # le film s'eteint sur le dernier plan
                f = (f.astype(np.float32)
                     * max(0.0, 1.0 - max(0.0, (i / n - 0.55)) / 0.45)).astype(np.uint8)
            writer.append_data(f)
            total += 1
        print(f"{depart:>5.1f}s  {name:14s} {total/FPS - depart:>4.1f}s  {kind:6s} {registre}")

    writer.close()
    journal["fin"] = total / FPS
    with open("04_montage/coupes.json", "w") as fp:
        json.dump(journal, fp, indent=1)
    print(f"\nimage : {total/FPS:.2f}s  {total} images  {len(journal['coupes'])} plans")

    if os.path.exists(SON):
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", MUET, "-i", SON,
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", OUT], check=True)
        print(f"{OUT}  image + son")
    else:
        print(f"{SON} absent — lancer 04_montage/son.py puis relancer")
