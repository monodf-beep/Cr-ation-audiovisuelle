#!/usr/bin/env python3
"""
Jingle des reels : la croix de Savoie bordee de bleu.

Deux pieces, rendues ici en 1080x1920 a 30 i/s :

  OUTRO  2,4 s, la signature complete, avec le son.
         0,00  le drapeau arrive en tournant comme une piece lancee
         0,42  NOTE 1 : il se plante, onde de choc, l'image tremble
         0,80  NOTE 2 : le bras horizontal de la croix jaillit d'un bord
               a l'autre de l'ecran
         1,05  le bras se detache et descend, le drapeau remonte
         1,10  le nom sort du bras, lettre par lettre
         1,60  NOTE 3 : coup sec, tout se fige
         2,40  fin

  STING  1,2 s, sans fond (ProRes 4444 avec alpha), a poser sur la
         premiere image d'un reel : le petit drapeau tourne, se plante
         dans le coin, reste, puis s'en va.

Le drapeau est celui du chateau dans les images Higgsfield de la parade
aux flambeaux : champ rouge, croix blanche, bordure bleue.

Rien n'est genere par IA ici : les formes et le nom sont dessines, donc
identiques a chaque rendu. Le son est synthetise (cloche inharmonique,
sub, souffles) ; c'est une maquette, a remplacer si on veut un vrai
logo sonore.

Usage : python3 jingle_reels/jingle.py
Sorties : jingle_reels/out/
"""

import math
import os
import subprocess
import urllib.request
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# Reglages
# --------------------------------------------------------------------------

NOM = "FRANCK MONOD"

W, H = 1080, 1920
FPS = 30
SOUS = 6            # sous-images par image, pour le flou de mouvement
OBTURATEUR = 0.5    # 180 degres
SR = 48000

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, "out")
POLICE = os.path.join(ICI, "fonts", "Anton-Regular.ttf")
POLICE_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anton/Anton-Regular.ttf"
FOND_APERCU = os.path.join(ICI, "apercu_fond.png")   # optionnel, pour le sting

ROUGE = (190, 22, 44)
BLANC = (246, 242, 234)
BLEU = (32, 64, 160)
NUIT = (9, 16, 38)

# Temps forts (secondes)
T_IMPACT = 0.42
T_BRAS = 0.80
T_DETACHE = 1.05
T_NOM = 1.10
T_FIGE = 1.60
DUREE = 2.40


# --------------------------------------------------------------------------
# Courbes
# --------------------------------------------------------------------------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def expo_out(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def cubic_in_out(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def back_out(p, s=2.2):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def ressort(t, t0, amp, raideur=9.0, freq=26.0):
    """Rebond amorti apres t0, qui part de amp et revient a 0."""
    if t < t0:
        return amp
    d = t - t0
    return amp * math.exp(-raideur * d) * math.cos(freq * d)


def lerp(a, b, p):
    return a + (b - a) * p


# --------------------------------------------------------------------------
# Le drapeau
# --------------------------------------------------------------------------

def drapeau(taille):
    """Drapeau carre, bordure bleue, champ rouge, croix blanche."""
    im = Image.new("RGBA", (taille, taille), BLEU + (255,))
    d = ImageDraw.Draw(im)
    b = round(taille * 0.085)
    d.rectangle([b, b, taille - b - 1, taille - b - 1], fill=ROUGE)
    inner = taille - 2 * b
    bras = round(inner * 0.2)
    c0 = (taille - bras) // 2
    d.rectangle([c0, b, c0 + bras - 1, taille - b - 1], fill=BLANC)
    d.rectangle([b, c0, taille - b - 1, c0 + bras - 1], fill=BLANC)
    return im, bras


def coeffs_perspective(dst, src):
    a, v = [], []
    for (x, y), (X, Y) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -X * x, -X * y]); v.append(X)
        a.append([0, 0, 0, x, y, 1, -Y * x, -Y * y]); v.append(Y)
    return np.linalg.solve(np.array(a, float), np.array(v, float))


def poser_drapeau(calque, img, cx, cy, echelle, theta, focale=1600.0):
    """Pose le drapeau tourne de theta autour de l'axe vertical."""
    c = math.cos(theta)
    if abs(c) < 0.03 or echelle <= 0.01:
        return
    s = math.sin(theta)
    n = img.size[0]
    demi = n / 2
    pts = []
    for x, y in ((-demi, -demi), (demi, -demi), (demi, demi), (-demi, demi)):
        xr, zr = x * c, x * s
        k = focale / (focale + zr * echelle)
        pts.append((cx + xr * echelle * k, cy + y * echelle * k))
    x0 = int(math.floor(min(p[0] for p in pts))) - 2
    y0 = int(math.floor(min(p[1] for p in pts))) - 2
    x1 = int(math.ceil(max(p[0] for p in pts))) + 2
    y1 = int(math.ceil(max(p[1] for p in pts))) + 2
    local = [(px - x0, py - y0) for px, py in pts]
    src = [(0, 0), (n, 0), (n, n), (0, n)]
    co = coeffs_perspective(local, src)
    morceau = img.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(co),
                            Image.BICUBIC)
    # ombre de rotation : plus sombre quand il est vu de biais
    lum = 0.5 + 0.5 * abs(c)
    if lum < 0.999:
        a = np.asarray(morceau).astype(np.float32)
        a[..., :3] *= lum
        morceau = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    calque.alpha_composite(morceau, (x0, y0)) if x0 >= 0 and y0 >= 0 else \
        calque.paste(morceau, (x0, y0), morceau)


# --------------------------------------------------------------------------
# Fond, grain
# --------------------------------------------------------------------------

def fond():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array(NUIT, np.float32)
    lueur = np.exp(-(((xx - W / 2) / 620) ** 2 + ((yy - 900) / 760) ** 2))
    img = base + lueur[..., None] * np.array([18, 30, 70], np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    vign = 1 - 0.55 * np.clip(r - 0.35, 0, 1) ** 1.6
    return img * vign[..., None]


def grain(img, rng, force=7.0):
    n = rng.normal(0, force, (H // 2, W // 2)).astype(np.float32)
    n = n.repeat(2, 0).repeat(2, 1)
    return img + n[..., None]


# --------------------------------------------------------------------------
# Le nom dans le bras
# --------------------------------------------------------------------------

class Nom:
    def __init__(self, texte, police, taille):
        self.f = ImageFont.truetype(police, taille)
        self.texte = texte
        self.largeur = self.f.getlength(texte)
        self.pos = [self.f.getlength(texte[:i]) for i in range(len(texte))]
        box = self.f.getbbox(texte)
        self.haut = box[3] - box[1]
        self.dy = box[1]

    def dessiner(self, largeur_bande, hauteur_bande, t):
        cal = Image.new("RGBA", (largeur_bande, hauteur_bande), BLANC + (255,))
        d = ImageDraw.Draw(cal)
        x0 = (largeur_bande - self.largeur) / 2
        ybase = (hauteur_bande - self.haut) / 2 - self.dy
        lettres = [i for i, ch in enumerate(self.texte) if ch != " "]
        for rang, i in enumerate(lettres):
            debut = T_NOM + rang * 0.022
            p = prog(t, debut, debut + 0.26)
            if p <= 0:
                continue
            off = (1 - back_out(p, 1.6)) * hauteur_bande * 0.95
            d.text((x0 + self.pos[i], ybase + off), self.texte[i],
                   font=self.f, fill=NUIT)
        return cal


# --------------------------------------------------------------------------
# Outro
# --------------------------------------------------------------------------

TAILLE_DRAPEAU = 560
CY0 = 860          # centre du drapeau a l'impact
CY_FIN = 610       # centre du drapeau a la fin
EC_FIN = 0.6
BANDE_Y_FIN = 1130
BANDE_H_FIN = 250


def etat_drapeau(t):
    """Centre y, echelle, angle du drapeau a l'instant t."""
    p = prog(t, 0, T_IMPACT)
    e = expo_out(p)
    theta = (1 - e) * (-3 * math.pi)
    y = lerp(CY0 + 520, CY0, e)
    if t < T_IMPACT:
        ech = lerp(0.12, 1.12, e)
    else:
        ech = 1.0 + ressort(t, T_IMPACT, 0.12)
    pd = expo_out(prog(t, T_DETACHE, T_DETACHE + 0.45))
    y = lerp(y, CY_FIN, pd)
    ech = lerp(ech, EC_FIN, pd)
    return y, ech, theta


def onde(calque, t, cx, cy, t0, r0, r1, couleur, epais=16):
    p = prog(t, t0, t0 + 0.38)
    if p <= 0 or p >= 1:
        return
    e = expo_out(p)
    r = lerp(r0, r1, e)
    a = int(220 * (1 - p) ** 1.5)
    w = max(2, int(epais * (1 - p)))
    d = ImageDraw.Draw(calque)
    d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=int(r * 0.08),
                        outline=couleur + (a,), width=w)


def sous_image_outro(t, img_drap, bras_px, nom, bg):
    cal = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cy, ech, theta = etat_drapeau(t)
    cx = W / 2
    demi = TAILLE_DRAPEAU / 2 * ech

    # onde de choc a l'impact, et plus petite au fige
    onde(cal, t, cx, CY0, T_IMPACT, demi * 1.02, demi * 2.3, BLANC)
    onde(cal, t, cx, CY_FIN, T_FIGE, TAILLE_DRAPEAU / 2 * EC_FIN * 1.05,
         TAILLE_DRAPEAU / 2 * EC_FIN * 1.8, (120, 150, 255), 10)

    poser_drapeau(cal, img_drap, cx, cy, ech, theta)

    # le bras qui jaillit puis se detache
    if t >= T_BRAS:
        pe = expo_out(prog(t, T_BRAS, T_BRAS + 0.24))
        inner = TAILLE_DRAPEAU * (1 - 2 * 0.085)
        hw = lerp(inner / 2 * ech, W / 2 + 40, pe)
        pd = expo_out(prog(t, T_DETACHE, T_DETACHE + 0.45))
        by = lerp(cy, BANDE_Y_FIN, pd)
        bh = lerp(bras_px * ech, BANDE_H_FIN, pd)
        # coup de poing au fige
        punch = 1 + max(0.0, ressort(t, T_FIGE, 0.07, 14, 30)) if t >= T_FIGE else 1
        bh *= punch
        x0, x1 = int(round(cx - hw)), int(round(cx + hw))
        y0 = int(round(by - bh / 2))
        hb = max(1, int(round(bh)))
        lb = max(1, x1 - x0)
        if t >= T_NOM:
            base = nom.dessiner(W, BANDE_H_FIN, t)
            if punch != 1:
                nw = int(W * punch)
                base = base.resize((nw, int(BANDE_H_FIN * punch)), Image.BICUBIC)
                base = base.crop(((nw - W) // 2, 0, (nw - W) // 2 + W, base.size[1]))
            # la bande peut encore grandir : on recadre au centre, sans ecraser
            if base.size[1] > hb:
                h0 = (base.size[1] - hb) // 2
                base = base.crop((0, h0, W, h0 + hb))
            elif base.size[1] < hb:
                base = base.resize((W, hb), Image.BICUBIC)
            morceau = base.crop((max(0, x0), 0, max(0, x0) + min(lb, W), hb))
            cal.alpha_composite(morceau, (max(0, x0), max(0, y0)))
        else:
            ImageDraw.Draw(cal).rectangle([x0, y0, x1, y0 + hb - 1], fill=BLANC)

    a = np.asarray(cal).astype(np.float32) / 255.0
    return bg * (1 - a[..., 3:]) + a[..., :3] * 255 * a[..., 3:]


def secousse(t):
    dx = dy = 0.0
    for t0, amp in ((T_IMPACT, 22.0), (T_FIGE, 12.0)):
        if t >= t0:
            d = t - t0
            k = amp * math.exp(-d / 0.055)
            dx += k * math.sin(d * 95)
            dy += k * math.cos(d * 71)
    return int(round(dx)), int(round(dy))


def aberration(img, t):
    """Decalage rouge/bleu bref sur les deux chocs."""
    f = 0.0
    for t0 in (T_IMPACT, T_FIGE):
        if t >= t0:
            f += math.exp(-(t - t0) / 0.07)
    s = int(round(8 * f))
    if s:
        img[..., 0] = np.roll(img[..., 0], s, axis=1)
        img[..., 2] = np.roll(img[..., 2], -s, axis=1)
    return img


def rendre_outro(ffmpeg, wav):
    img_drap, bras = drapeau(TAILLE_DRAPEAU)
    nom = Nom(NOM, POLICE, 150)
    bg = fond()
    rng = np.random.default_rng(7)
    n = round(DUREE * FPS)
    sortie = os.path.join(OUT, "outro.mp4")
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-i", wav,
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
         sortie], stdin=subprocess.PIPE)
    planches = {}
    for i in range(n):
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(SOUS):
            t = (i + k / SOUS * OBTURATEUR) / FPS
            acc += sous_image_outro(t, img_drap, bras, nom, bg)
        img = acc / SOUS
        t = i / FPS
        dx, dy = secousse(t)
        if dx or dy:
            img = np.roll(img, (dy, dx), axis=(0, 1))
        img = aberration(img, t)
        img = grain(img, rng)
        img8 = img.clip(0, 255).astype(np.uint8)
        proc.stdin.write(img8.tobytes())
        for tt in (0.20, T_IMPACT + 0.03, 0.92, 1.25, T_FIGE + 0.2):
            if abs(t - tt) < 0.5 / FPS:
                planches[tt] = Image.fromarray(img8)
    proc.stdin.close()
    proc.wait()
    return sortie, planches


# --------------------------------------------------------------------------
# Sting
# --------------------------------------------------------------------------

STING_DUREE = 1.2
STING_TAILLE = 150
STING_X, STING_Y = 150, 300    # coin haut gauche, dans la zone sure


def sous_image_sting(t, img):
    cal = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = prog(t, 0, 0.30)
    e = expo_out(p)
    theta = (1 - e) * (-2 * math.pi)
    ech = lerp(0.1, 1.15, e) if t < 0.30 else 1 + ressort(t, 0.30, 0.15, 11, 30)
    sortie = prog(t, 1.00, 1.18)
    if sortie > 0:
        ech *= 1 - cubic_in_out(sortie)
        theta += cubic_in_out(sortie) * math.pi
    onde(cal, t, STING_X, STING_Y, 0.30, STING_TAILLE * 0.55, STING_TAILLE * 1.3,
         BLANC, 8)
    poser_drapeau(cal, img, STING_X, STING_Y, ech, theta)
    a = np.asarray(cal).astype(np.float32)
    a[..., :3] *= a[..., 3:] / 255.0      # premultiplie, pour moyenner juste
    return a


def rendre_sting(ffmpeg):
    img, _ = drapeau(STING_TAILLE)
    n = round(STING_DUREE * FPS)
    mov = os.path.join(OUT, "sting_alpha.mov")
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
         "-pix_fmt", "yuva444p10le", mov], stdin=subprocess.PIPE)
    images = []
    for i in range(n):
        acc = np.zeros((H, W, 4), np.float32)
        for k in range(SOUS):
            acc += sous_image_sting((i + k / SOUS * OBTURATEUR) / FPS, img)
        # moyenne en alpha premultiplie, puis on repasse en alpha droit
        pm = (acc / SOUS).clip(0, 255)
        droit = pm.copy()
        al = pm[..., 3:]
        droit[..., :3] = np.where(al > 0, pm[..., :3] * 255.0 / np.maximum(al, 1e-3), 0)
        proc.stdin.write(droit.clip(0, 255).astype(np.uint8).tobytes())
        images.append(pm)
    proc.stdin.close()
    proc.wait()

    # apercu : le sting pose sur une image de reel
    if os.path.exists(FOND_APERCU):
        f = Image.open(FOND_APERCU).convert("RGB").resize((W, H))
        base = np.asarray(f).astype(np.float32)
    else:
        base = fond()
    apercu = os.path.join(OUT, "sting_apercu.mp4")
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-i", os.path.join(OUT, "sting.wav"),
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "256k", "-shortest", apercu], stdin=subprocess.PIPE)
    for a in images + [images[-1]] * 15:
        al = a[..., 3:] / 255.0
        img_ = base * (1 - al) + a[..., :3]
        proc.stdin.write(img_.clip(0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    return mov, apercu


# --------------------------------------------------------------------------
# Son (maquette synthetisee)
# --------------------------------------------------------------------------

def passe_bas(x, fc):
    """Filtre passe-bas a un pole, frequence de coupure variable (tableau)."""
    y = np.zeros_like(x)
    a = 1 - np.exp(-2 * np.pi * np.asarray(fc) / SR)
    a = np.broadcast_to(a, x.shape)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def cloche(f, duree, rng):
    """Clarine : partiels inharmoniques qui s'eteignent a des vitesses differentes."""
    t = np.arange(int(duree * SR)) / SR
    s = np.zeros_like(t)
    for rapport, amp, dec in ((1.0, 1.0, 1.4), (2.76, 0.55, 3.2), (5.40, 0.32, 6.0),
                              (8.93, 0.18, 9.5), (0.5, 0.25, 2.0)):
        ph = rng.uniform(0, 2 * np.pi)
        s += amp * np.sin(2 * np.pi * f * rapport * t + ph) * np.exp(-dec * t)
    attaque = np.minimum(1, t / 0.002)
    clic = rng.normal(0, 1, len(t)) * np.exp(-t / 0.004) * 0.6
    return (s * attaque + clic) / 2.2


def sub(duree, f0=120, f1=42):
    t = np.arange(int(duree * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.22) * np.minimum(1, t / 0.003)


def souffle(duree, rng, fc0=300, fc1=6000, montee=True):
    n = int(duree * SR)
    t = np.linspace(0, 1, n)
    env = t ** 2.2 if montee else (1 - t) ** 2
    fc = fc0 + (fc1 - fc0) * (t if montee else 1 - t) ** 2
    bruit = rng.normal(0, 1, n)
    return passe_bas(bruit, fc) * env * 1.6


def poser(piste, son, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    j = min(len(piste), i + len(son))
    if j <= i:
        return
    g = np.array([math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)])
    piste[i:j] += son[: j - i, None] * g[None, :] * gain * math.sqrt(2)


def ecrire_wav(chemin, st):
    st = st / max(1e-6, np.abs(st).max()) * 0.89
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())


# Motif : re, la, re a l'octave
NOTES = (587.33, 880.0, 1174.66)


def son_outro(chemin):
    rng = np.random.default_rng(3)
    st = np.zeros((int(DUREE * SR), 2))
    poser(st, souffle(T_IMPACT, rng), 0.0, 0.35)
    poser(st, cloche(NOTES[0], 1.8, rng), T_IMPACT, 0.9, -0.15)
    poser(st, sub(0.8), T_IMPACT, 1.0)
    poser(st, souffle(0.22, rng, 800, 9000), T_BRAS - 0.2, 0.3, -0.6)
    poser(st, souffle(0.35, rng, 9000, 400, montee=False), T_BRAS, 0.3, 0.6)
    poser(st, cloche(NOTES[1], 1.4, rng), T_BRAS, 0.75, 0.2)
    poser(st, souffle(T_FIGE - T_NOM, rng, 500, 5000), T_NOM, 0.18)
    poser(st, cloche(NOTES[2], DUREE - T_FIGE, rng), T_FIGE, 1.0)
    poser(st, cloche(NOTES[0], DUREE - T_FIGE, rng), T_FIGE, 0.45)
    poser(st, sub(0.8, 140, 40), T_FIGE, 1.1)
    # queue coupee proprement sur les 60 dernieres ms
    n = int(0.06 * SR)
    st[-n:] *= np.linspace(1, 0, n)[:, None]
    ecrire_wav(chemin, st)


def son_sting(chemin):
    rng = np.random.default_rng(5)
    st = np.zeros((int(1.7 * SR), 2))
    poser(st, souffle(0.30, rng, 600, 8000), 0.0, 0.25, -0.4)
    poser(st, cloche(NOTES[0], 1.3, rng), 0.30, 0.9, -0.3)
    poser(st, sub(0.6, 110, 45), 0.30, 0.6)
    ecrire_wav(chemin, st)


# --------------------------------------------------------------------------

def planche(images, chemin):
    cles = sorted(images)
    tw, th = 360, 640
    p = Image.new("RGB", (tw * len(cles) + 10 * (len(cles) + 1), th + 20), (20, 20, 20))
    for k, c in enumerate(cles):
        p.paste(images[c].resize((tw, th), Image.LANCZOS), (10 + k * (tw + 10), 10))
    p.save(chemin, quality=92)


def main():
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(POLICE):
        os.makedirs(os.path.dirname(POLICE), exist_ok=True)
        urllib.request.urlretrieve(POLICE_URL, POLICE)

    wav = os.path.join(OUT, "outro.wav")
    son_outro(wav)
    son_sting(os.path.join(OUT, "sting.wav"))
    outro, images = rendre_outro(ffmpeg, wav)
    planche(images, os.path.join(OUT, "outro_planche.jpg"))
    mov, apercu = rendre_sting(ffmpeg)
    for f in (outro, mov, apercu):
        print(f)


if __name__ == "__main__":
    main()
