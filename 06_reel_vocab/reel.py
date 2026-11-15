#!/usr/bin/env python3
"""
Reel « Le rugby en savoyard », version teaser de match.

Deux étapes :
  1. PREP  — chaque plan devient un clip 1080x1920 30 i/s prêt à monter :
             plans pro (résumé TV) recadrés en 9:16, agrandis, puis passés
             dans le style animé choisi ; rushes du stade simplement
             redressés. Mis en cache dans DOSSIER_TRAVAIL/clips/.
  2. MONTAGE — ouverture à froid (action + commentateur), selfie accroche,
             mots en typographie géante qui claque, fin.

Usage :
  python3 reel.py montage.json            # prep (si besoin) + montage
Le fichier montage.json décrit la timeline (voir montage.json).
"""
import importlib.util
import json
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 48000
HERE = os.path.dirname(os.path.abspath(__file__))
ROUGE = (200, 16, 46)
BLEU = (0x0A, 0x36, 0xA8)   # bleu de l'étiquette de la miniature (et de « Le savoyard au CERN »)
BLANC = (255, 255, 255)
NUIT = (14, 14, 20)

# Typographie « R » : Bodoni (né à Saluzzo) pour les mots qui claquent,
# Semplicità (fonderie Nebiolo, Turin, 1930) pour le texte.
# Bodoni Moda : instance optique 11 pt (déliés plus épais, lisibles sur téléphone), OFL.
# Semplicità : numérisation Leonardo Di Lena, CC BY-ND 3.0 (à créditer, fichier non modifié).
# v12 : typo de la miniature. Mots en capitales condensées (Anton, OFL),
# étiquettes blanches en Semplicità Gras bleu ; bandeaux en bleu.
F_DISPLAY = os.path.join(HERE, "polices", "Anton.ttf")
F_ARTICLE = os.path.join(HERE, "polices", "Anton.ttf")
F_PASTILLE = os.path.join(HERE, "polices", "Semplicita-Bold.otf")
F_BOLD = os.path.join(HERE, "polices", "Semplicita-Medium.otf")
F_BLACK = os.path.join(HERE, "polices", "Semplicita-Bold.otf")
TRACK = -0.01   # interlettrage des mots (em)


# ================================================================ outils
def clamp01(x):
    return min(max(x, 0.0), 1.0)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=2.2):
    x = clamp01(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def font(path, size):
    return ImageFont.truetype(path, size)


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True).stdout


# ================================================================ 1. PREP
def load_style(name):
    if not name:
        return None
    p = os.path.join(HERE, "styles", name + ".py")
    if name == "celshade":
        p = os.path.join(HERE, "stylize.py")
    spec = importlib.util.spec_from_file_location("style_" + name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Style() if hasattr(mod, "Style") else mod.Stylizer()


def masks_for(cfg, seg):
    """Zones à nettoyer : celles de la source (habillage TV, écran géant…)
    + celles du plan. Rectangles {x,y,w,h[,t0,t1]} en pixels de la source
    (pro : 640x360 ; rushes : image redressée 1080x1920), temps en secondes
    de la SOURCE."""
    return cfg["sources"][seg["src"]].get("masques", []) + seg.get("masques", [])


def inpaint_frames(frames, masks, start, speed, scale=1.0):
    """Efface les zones (inpainting Telea) image par image."""
    import cv2
    if not masks:
        return frames
    out = []
    h, w = frames.shape[1:3]
    for k, f in enumerate(frames):
        t = start + k / FPS * speed
        m = np.zeros((h, w), np.uint8)
        for r in masks:
            if t < r.get("t0", -1e9) or t > r.get("t1", 1e9):
                continue
            x, y = int(r["x"]), int(r["y"])
            m[max(0, y):y + int(r["h"]), max(0, x):x + int(r["w"])] = 255
        if not m.any():
            out.append(f)
            continue
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
        if scale != 1.0:  # grandes images : on bouche en basse définition puis on recolle
            sw, sh = int(w * scale), int(h * scale)
            small = cv2.resize(f, (sw, sh), interpolation=cv2.INTER_AREA)
            ms = cv2.resize(m, (sw, sh), interpolation=cv2.INTER_NEAREST)
            fill = cv2.resize(cv2.inpaint(small, ms, 5, cv2.INPAINT_TELEA), (w, h),
                              interpolation=cv2.INTER_CUBIC)
            a = cv2.GaussianBlur(m, (0, 0), 3).astype(np.float32)[..., None] / 255
            out.append((f * (1 - a) + fill * a).astype(np.uint8))
        else:
            out.append(cv2.inpaint(f, m, 4, cv2.INPAINT_TELEA))
    return np.stack(out)


def prep_clip(seg, cfg, style_obj, out):
    """Écrit un clip 1080x1920 30 i/s (vidéo seule) pour le segment :
    lecture à la résolution de la source -> nettoyage des incrustations ->
    recadrage 9:16 (panoramique ou très gros plan) -> agrandissement -> style."""
    import cv2
    if os.path.exists(out):
        return
    src = cfg["sources"][seg["src"]]
    pro = seg["src"] == "pro"
    speed = seg.get("vitesse", 1.0)
    dur = seg["dur"]
    sdur = dur * speed + 0.15
    if pro:
        sw, sh = src["w"], src["h"]
        vf = "hqdn3d=3:3:4:4,"
    else:
        sw, sh = W, H
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
    vf += (f"setpts={1/speed:.4f}*PTS," if speed != 1 else "") + f"fps={FPS}"
    raw = run(["ffmpeg", "-v", "error", "-ss", str(seg["start"]), "-t", f"{sdur:.3f}",
               "-i", src["path"], "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    n = len(raw) // (sw * sh * 3)
    frames = np.frombuffer(raw, np.uint8)[: n * sw * sh * 3].reshape(n, sh, sw, 3)
    need = int(round(dur * FPS))
    if n < need:
        frames = np.concatenate([frames, np.repeat(frames[-1:], need - n, 0)])
    frames = frames[:need]
    frames = inpaint_frames(frames, masks_for(cfg, seg), seg["start"], speed,
                            scale=1.0 if pro else 0.5)

    def window(k):
        if "z" in seg:
            ch = int(round(sh * seg["z"])) // 2 * 2
            cw = int(round(ch * 9 / 16)) // 2 * 2
            cx, cy = seg["cx"], seg.get("cy", sh / 2)
        elif pro:
            ch = sh
            cw = int(round(sh * 9 / 16)) // 2 * 2
            a = seg.get("cx_debut", sw / 2)
            b = seg.get("cx_fin", a)
            cx = a + (b - a) * min(1.0, (k / FPS * speed) / sdur)
            cy = sh / 2
        else:
            return None
        x = int(min(max(cx - cw / 2, 0), sw - cw))
        y = int(min(max(cy - ch / 2, 0), sh - ch))
        return x, y, cw, ch

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                            "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", out],
                           stdin=subprocess.PIPE)
    styl = style_obj is not None and seg.get("styliser", pro)
    if styl:
        style_obj.reset()
    # focus ballon : le style change très vite (liste « styles_seq », une durée en
    # images par changement dans « cadence »), « reel » = image non stylisée
    seq = seg.get("styles_seq")
    sched = []
    if seq:
        for j, nfr in enumerate(seg["cadence"]):
            sched += [seq[j % len(seq)]] * nfr
        _styles = {}
    prev = None
    for k, f in enumerate(frames):
        win = window(k)
        if win is not None:
            x, y, cw, ch = win
            f = cv2.resize(np.ascontiguousarray(f[y:y + ch, x:x + cw]), (W, H),
                           interpolation=cv2.INTER_LANCZOS4)
        if seq:
            name = sched[min(k, len(sched) - 1)]
            if name != "reel":
                if name not in _styles:
                    _styles[name] = load_style(name)
                if name != prev:
                    _styles[name].reset()
                f = _styles[name](np.ascontiguousarray(f))
            prev = name
        elif styl:
            f = style_obj(np.ascontiguousarray(f))
        enc.stdin.write(np.ascontiguousarray(f).tobytes())
    enc.stdin.close()
    enc.wait()


def read_frames(path, n):
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    k = len(raw) // (W * H * 3)
    fr = np.frombuffer(raw, np.uint8)[: k * W * H * 3].reshape(k, H, W, 3)
    if n is None:
        return fr
    if k < n:
        fr = np.concatenate([fr, np.repeat(fr[-1:], n - k, 0)])
    return fr[:n]


def suite_images(s, nf, nclip):
    """Montage « sur le contact » : numéros des images du clip à montrer, une par
    image du plan. « entree » = première image jouée (on entre juste avant le
    choc), « sauter » = [a, b] images retirées, « gel » = [image, n] : l'image du
    contact est tenue n images de plus. Si le clip est trop court après un gel,
    la queue est étirée (1,5 fois au plus), puis la dernière image est tenue."""
    idx = list(range(min(s.get("entree", 0), nclip - 1), nclip))
    if s.get("sauter"):
        a, b = s["sauter"]
        idx = [k for k in idx if not a <= k <= b]
    gel = s.get("gel")
    if gel and gel[0] in idx:
        p = idx.index(gel[0])
        tete, queue = idx[:p + 1] + [gel[0]] * gel[1], idx[p + 1:]
        manque = nf - len(tete)
        if queue and manque > len(queue):
            f = min(1.5, manque / len(queue))
            queue = [queue[min(len(queue) - 1, int(j / f))] for j in range(int(round(len(queue) * f)))]
        idx = tete + queue
    idx += [idx[-1]] * max(0, nf - len(idx))
    return idx[:nf]


def read_audio(cfg, seg, piste):
    """Audio stéréo 48 kHz (n, 2) du segment. piste : 'plein' (avec commentateur),
    'foule' (stem sans voix), 'aucun'."""
    dur = seg.get("son_dur", seg["dur"])   # « son_dur » : une ambiance continue sous plusieurs plans
    n = int(dur * SR)
    if piste == "aucun":
        return np.zeros((n, 2), np.float32)
    src = cfg["sources"][seg["src"]]
    path = src["path"]
    # le son peut venir d'un autre instant que l'image (ex. ouverture : l'image de
    # l'échappée, le cri « Brilliant! » qui suit) et ne pas être ralenti
    start = seg.get("son_debut", seg["start"])
    if seg["src"] == "pro" and piste == "foule" and src.get("foule"):
        path = src["foule"]
        start = start - src.get("foule_offset", 0.0)
    speed = seg.get("son_vitesse", seg.get("vitesse", 1.0))
    af = f"atempo={max(0.5, speed)}" if speed != 1 else "anull"
    raw = run(["ffmpeg", "-v", "error", "-ss", f"{max(0, start):.3f}", "-t", f"{dur*speed+0.2:.3f}",
               "-i", path, "-af", af, "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"])
    a = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, 2) / 32768
    a = np.pad(a, ((0, max(0, n - len(a))), (0, 0)))[:n].copy()
    f = int(0.04 * SR)
    a[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(seg.get("son_fondu", 0.04) * SR)
    a[-f:] *= np.linspace(1, 0, f)[:, None]
    return a


# ================================================================ sons
# Règles (Clipwing real-sfx + earshot sound-design) :
#  - uniquement des enregistrements réels (dossier sons/, Openverse CC0/CC-BY),
#    aucun son synthétisé ; pas de son adapté -> le moment reste muet ;
#  - pas de whoosh sur chaque coupe (85 % des coupes pro sont muettes) :
#    seulement sur les vrais mouvements de caméra (2 max) ;
#  - une action répétée (le mot qui claque) puise dans un pool de prises,
#    jamais deux fois la même d'affilée, ±1,5 dB, ±0,4 demi-ton ;
#  - calage : impacts sur l'ARRIVÉE du son, whoosh sur son PIC,
#    montée qui FINIT 150 ms avant l'impact (un temps d'air) ;
#  - niveaux crête par rôle (dBFS) puis master -14 LUFS, -1 dBTP.
SONS = os.path.join(HERE, "sons")
#  - v7 : le mot claque avec un corps (impact_1, audible sur téléphone) + un
#    transitoire médium réel (« claque ») ; le dernier mot (« heros ») est le
#    sommet du film ; les sifflets passent sur la coupe, sous le niveau de la voix.
CRETE = {"impact": -8, "claque": -9, "heros": -3, "whoosh": -9, "montee": -12, "sifflet": -12,
         "clameur": -8, "foule": -14, "pop": -10, "musique": -3, "coup_de_pied": -5}
_CACHE = {}


def load_sound(name):
    """Charge sons/<name>.* en stéréo 48 kHz (n, 2), normalisé à 0 dBFS crête."""
    if name in _CACHE:
        return _CACHE[name]
    path = None
    if os.path.isdir(SONS):
        for f in sorted(os.listdir(SONS)):
            if os.path.splitext(f)[0] == name:
                path = os.path.join(SONS, f)
                break
    if path is None:
        _CACHE[name] = None
        return None
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"])
    a = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, 2) / 32768
    a = a / max(1e-6, np.abs(a).max())
    _CACHE[name] = a
    return a


def pool(prefix):
    if not os.path.isdir(SONS):
        return []
    return sorted({os.path.splitext(f)[0] for f in os.listdir(SONS)
                   if f.startswith(prefix) and not f.endswith(".md")})


def envelope(a, win=0.01):
    if a.ndim == 2:
        a = a.mean(1)
    n = max(1, int(win * SR))
    e = np.sqrt(np.convolve(a ** 2, np.ones(n) / n, mode="same"))
    return e


def anchor_offset(a, mode):
    """Position (s) dans le son du point à caler sur l'image."""
    e = envelope(a)
    pk = int(np.argmax(e))
    if mode == "peak":
        return pk / SR
    if mode == "end":
        above = np.nonzero(e > e.max() * 10 ** (-40 / 20))[0]
        return (above[-1] if len(above) else len(a)) / SR
    # arrivée : premier instant à moins de 6 dB du maximum
    idx = np.nonzero(e >= e.max() * 10 ** (-6 / 20))[0]
    return (idx[0] if len(idx) else pk) / SR


def pitch(a, st):
    if abs(st) < 1e-3:
        return a
    r = 2 ** (st / 12)
    x = np.arange(0, len(a) - 1, r)
    return np.stack([np.interp(x, np.arange(len(a)), a[:, c]) for c in range(a.shape[1])], 1).astype(np.float32)


# effets secs et centrés (règle earshot) ; whoosh, montée, clameur, musique restent larges
MONO_ROLES = ("impact", "claque", "heros", "sifflet", "coup_de_pied", "pop")


class SfxTrack:
    """Piste d'effets construite à partir d'une liste de repères."""

    def __init__(self, n):
        self.buf = np.zeros((n, 2), np.float32)
        self.libre = np.zeros((n, 2), np.float32)   # sons jamais atténués (explosion finale)
        self.cues = []
        self._last = {}

    def add(self, t, role, name=None, anchor="arrive", gain_db=0.0, st=0.0, max_dur=None, label="",
            fondu=0.03, coupe_avant=False, libre=False):
        """fondu : fondu de sortie quand max_dur coupe le son ; coupe_avant : le son
        démarre sur son arrivée (rien ne joue avant le repère) ; libre : hors atténuation."""
        if name is None:  # pool : on tourne, jamais deux fois la même prise
            p = pool(role)
            if not p:
                self.cues.append((t, role, None, label))
                return
            k = (self._last.get(role, -1) + 1) % len(p)
            self._last[role] = k
            name = p[k]
        a = load_sound(name)
        if a is None:
            self.cues.append((t, role, None, label))
            return
        if role in MONO_ROLES:
            a = np.repeat(a.mean(1, keepdims=True), 2, 1)
        a = pitch(a, st)
        if coupe_avant:
            i = max(0, int((anchor_offset(a, anchor) - 0.03) * SR))
            a = a[i:].copy()
            f = min(len(a), int(0.03 * SR))
            a[:f] *= np.linspace(0, 1, f)[:, None]
        if max_dur:
            n = int(max_dur * SR)
            if len(a) > n:
                a = a[:n].copy()
                f = int(fondu * SR)
                a[-f:] *= np.linspace(1, 0, f)[:, None]
        off = anchor_offset(a, anchor)
        g = 10 ** ((CRETE.get(role, -10) + gain_db) / 20)
        mix_at(self.libre if libre else self.buf, a * g, t - off)
        self.cues.append((round(t, 3), role, name, label))


def mix_at(buf, s, t, g=1.0):
    i = int(t * SR)
    if i < 0:
        s, i = s[-i:], 0
    j = min(len(buf), i + len(s))
    if i < len(buf):
        buf[i:j] += g * s[: j - i]


# ================================================================ typographie
def text_layer(text, f, fill=BLANC, stroke=0, stroke_fill=NUIT, shadow=True):
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    m = 60
    img = Image.new("RGBA", (r - l + 2 * m, b - t + 2 * m), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((m - l + 6, m - t + 12), text, font=f, fill=(0, 0, 0, 170),
                                stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(16)))
    ImageDraw.Draw(img).text((m - l, m - t), text, font=f, fill=fill,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def fit(path, text, max_w, start, mini=60):
    s = start
    while s > mini:
        f = font(path, s)
        l, _, r, _ = f.getbbox(text)
        if r - l <= max_w:
            return f
        s -= 6
    return font(path, mini)


def split_article(sv):
    """« La mècllâye » -> ('La', 'mècllâye') ; « L'arbitro » -> ("L'", 'arbitro').
    Bas de casse : l'italique Bodoni y est plus grand et plus élégant."""
    s = sv.strip()
    if s[:2].lower() == "l'" or s[:2].lower() == "l’":
        return "L'", s[2:].lower()
    parts = s.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() in ("lo", "la", "los", "les", "le", "lé", "lés"):
        return parts[0].capitalize(), parts[1].lower()
    return "", s.lower()


def lettre_layer(ch, f, top, bot, m=60):
    """Une lettre avec ombre, dans une boîte verticale commune (top, bot du mot)."""
    l, _, r, _ = f.getbbox(ch)
    img = Image.new("RGBA", (r - l + 2 * m, bot - top + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((m - l + 6, m - top + 12), ch, font=f, fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(16)))
    ImageDraw.Draw(img).text((m - l, m - top), ch, font=f, fill=BLANC)
    return img


class WordCard:
    """Mot géant façon teaser : lettres qui tombent une à une, bandeau rouge
    oblique, traduction qui glisse dessous."""

    def __init__(self, sv, fr, idx, n, impact=0.5, largeur=960):
        art, noun = split_article(sv)
        art, noun = art.upper(), noun.upper()      # capitales condensées (miniature)
        self.IMPACT = impact   # la dernière lettre tombe sur l'image du contact
        self.f = fit(F_DISPLAY, noun, largeur, 330)
        tr = TRACK * self.f.size
        self.letters = []
        # toutes les lettres partagent la même boîte verticale (celle du mot entier) :
        # les capitales accentuées (Â, È, Ç) gardent la ligne de base commune
        _, self.l_top, _, self.l_bot = self.f.getbbox(noun)
        for k, ch in enumerate(noun):  # positions avec crénage (longueur des préfixes)
            x = self.f.getlength(noun[:k]) + tr * k
            adv = self.f.getlength(noun[:k + 1]) + tr * (k + 1) - x
            lay = lettre_layer(ch, self.f, self.l_top, self.l_bot) if ch != " " else None
            self.letters.append((lay, x, adv))
        self.noun_w = self.f.getlength(noun) + tr * (len(noun) - 1)
        asc, desc = self.f.getmetrics()
        self.noun_h = asc
        self.art = text_layer(art, font(F_ARTICLE, int(min(130, self.f.size * 0.5))), shadow=True) if art else None
        self.fr = text_layer(fr, font(F_PASTILLE, 70), fill=BLEU, shadow=False)
        self.cnt = text_layer(f"{idx+1:02d}", font(F_BLACK, 70), shadow=True)
        self.cnt_tot = text_layer(f"/{n:02d}", font(F_BOLD, 40), fill=(255, 255, 255, 200), shadow=True)
        self.n_letters = sum(1 for l in self.letters if l[0] is not None)

    STAGGER, LAND = 0.045, 0.14
    IMPACT = 0.5   # par défaut ; « impact » du plan sinon (les MOTS restent sur les
                   # temps de la musique, ce sont les coupes qui se décalent)

    def _timing(self):
        n = max(1, self.n_letters - 1)
        st = min(self.STAGGER, (self.IMPACT - self.LAND - 0.03) / n)
        return self.IMPACT - self.LAND - st * n, st

    def impact_time(self, t0=None):
        return self.IMPACT

    def debut(self):
        """Instant où l'habillage arrive : juste avant les lettres, pour laisser
        l'action nue jusqu'au contact."""
        return max(0.0, self._timing()[0] - 0.12)

    def cy_min(self):
        h_art = (self.art.height - 120) if self.art is not None else 0
        return 420 + h_art + 16 + (self.l_bot - self.l_top) / 2

    def draw(self, fr, t, dur, cy=900):
        # l'article ne doit pas monter dans le compteur (y 250-330) : la carte descend
        # juste assez (les capitales condensées sont plus hautes que l'ancien bas de casse)
        cy = max(cy, self.cy_min())
        t0, stag = self._timing()
        tb = self.debut()
        # bandeau rouge oblique qui balaie
        bp = ease_out((t - tb) / 0.2)
        if bp > 0:
            band_h = int(self.noun_h * 0.62)
            band = Image.new("RGBA", (W + 400, band_h), BLEU + (255,))
            band = band.rotate(-6, expand=True, resample=Image.BICUBIC)
            wv = int(band.width * bp)
            if wv > 0:
                band = band.crop((0, 0, wv, band.height))
                fr.alpha_composite(band, (-200, int(cy - band.height / 2 + self.noun_h * 0.06)))
        # article au-dessus, à gauche
        x_start = (W - self.noun_w) / 2
        if self.art is not None:
            ap = ease_out((t - tb - 0.02) / 0.18)
            if ap > 0:
                lay = self.art
                haut_caps = cy - (self.l_bot - self.l_top) / 2
                fr.alpha_composite(_alpha(lay, ap), (int(x_start - 30 + (1 - ap) * -80),
                                                     int(haut_caps - 16 - lay.height + 60)))
        # lettres
        k = 0
        for lay, x, adv in self.letters:
            if lay is None:
                continue
            ts = t0 + stag * k
            k += 1
            p = (t - ts) / self.LAND
            if p <= 0:
                continue
            sc = 1 + 1.6 * (1 - ease_out_back(p, 1.4)) if p < 1 else 1.0
            sc = max(sc, 0.85)
            al = ease_out(p * 2)
            breathe = 1 + 0.025 * clamp01((t - self.impact_time()) / max(0.1, dur))
            sc *= breathe
            lw, lh = lay.width * sc, lay.height * sc
            cx = (x_start + x + adv / 2 - W / 2) * breathe + W / 2
            l2 = lay.resize((max(1, int(lw)), max(1, int(lh))), Image.BICUBIC) if abs(sc - 1) > 1e-3 else lay
            if p < 1:
                l2 = l2.filter(ImageFilter.GaussianBlur((1 - p) * 6))
            fr.alpha_composite(_alpha(l2, al), (int(cx - l2.width / 2), int(cy - l2.height / 2)))
        # traduction : bandeau blanc qui glisse depuis la droite
        rp = ease_out((t - (self.impact_time() + 0.18)) / 0.25)
        if rp > 0:
            pad = 28
            box = Image.new("RGBA", (self.fr.width - 120 + 2 * pad, self.fr.height - 120 + 2 * pad),
                            (255, 255, 255, 245))
            box.alpha_composite(self.fr, (pad - 60, pad - 60))
            xx = int((W - box.width) / 2 + (1 - rp) * 500)
            fr.alpha_composite(_alpha(box, rp), (xx, int(cy + (self.l_bot - self.l_top) / 2 + 56)))
        # compteur
        fr.alpha_composite(self.cnt, (70, 250))
        fr.alpha_composite(self.cnt_tot, (70 + self.cnt.width - 110, 250 + 30))


def _alpha(layer, a):
    if a >= 0.999:
        return layer
    l2 = layer.copy()
    l2.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    return l2


# ================================================================ étalonnage
def grade(img, kind):
    a = img.astype(np.float32) / 255
    if kind == "rush":
        a = np.clip((a - 0.5) * 1.1 + 0.5, 0, 1)
        lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
        a = np.clip(lum + (a - lum) * 1.15, 0, 1) * np.array([1.03, 1, 0.95], np.float32)
    return a


_VIGN = None


_BANDS = {}


def finish(a, darken_center=0.0, cy=950):
    global _VIGN
    if _VIGN is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIGN = (1 - 0.3 * np.clip(r - 0.5, 0, 1) ** 1.5)[..., None]
    a = a * _VIGN
    if darken_center:
        if cy not in _BANDS:
            yy = np.arange(H, dtype=np.float32)[:, None, None]
            _BANDS[cy] = np.exp(-((yy - (cy + 50)) / 420) ** 2)
        a = a * (1 - darken_center * _BANDS[cy])
    return np.clip(a * 255, 0, 255).astype(np.uint8)


def zoom(img, k, dx=0, dy=0):
    """Agrandit de k ; (dx, dy) décale l'image (la fenêtre reste dans le cadre)."""
    if abs(k - 1) < 1e-3 and dx == 0 and dy == 0:
        return img
    cw, ch = W / k, H / k
    x0 = min(max((W - cw) / 2 - dx, 0), W - cw)
    y0 = min(max((H - ch) / 2 - dy, 0), H - ch)
    return np.asarray(Image.fromarray(img).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)))


# ================================================================ 2. MONTAGE
def main():
    mpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "montage.json")
    cfg = json.load(open(mpath, encoding="utf-8"))
    work = cfg["travail"]
    os.makedirs(os.path.join(work, "clips"), exist_ok=True)
    style_obj = load_style(cfg.get("style"))
    segs = cfg["timeline"]
    mots = [s for s in segs if s["type"] == "mot"]
    N = len(mots)
    audio_seul = "--audio" in sys.argv   # mix son seul (+ couches séparées), sans calcul d'image
    # --apercu=12.3,13.0 : n'écrit que ces images (travail/apercu/), pour vérifier un cadrage
    apercu = None
    for arg in sys.argv:
        if arg.startswith("--apercu="):
            apercu = {int(round(float(x) * FPS)) for x in arg.split("=")[1].split(",")}
            os.makedirs(os.path.join(work, "apercu"), exist_ok=True)
    for s in segs:   # durées calées sur l'image : l'image et le son ne dérivent pas
        s["dur"] = round(s["dur"] * FPS) / FPS

    # --- PREP
    for i, s in enumerate([] if audio_seul else segs):
        if s.get("clip"):            # plan déjà prêt (redessiné ailleurs), 1080x1920 30 i/s
            s["_clip"] = s["clip"]
            continue
        styl = s.get("styliser", s["src"] == "pro")
        extra = f"_{s['cx']}_{s.get('cy','')}_{s['z']}" if "z" in s else ""
        import hashlib
        mk = masks_for(cfg, s)
        extra += f"_{s.get('cx_debut','')}_{s.get('cx_fin','')}_v2"
        if s.get("styles_seq"):
            extra += "_seq" + hashlib.md5(json.dumps([s["styles_seq"], s["cadence"]]).encode()).hexdigest()[:6]
        if mk:
            extra += "_m" + hashlib.md5(json.dumps(mk, sort_keys=True).encode()).hexdigest()[:8]
        tag = f"{i:02d}_{s['src']}_{s['start']}_{s['dur']}_{s.get('vitesse',1)}{extra}_{cfg.get('style') if styl else 'brut'}"
        s["_clip"] = os.path.join(work, "clips", tag.replace(".", "-") + ".mp4")
        prep_clip(s, cfg, style_obj, s["_clip"])
        print(f"prep {i+1}/{len(segs)}", flush=True)

    total = sum(s["dur"] for s in segs)
    audio = np.zeros((int((total + 1) * SR), 2), np.float32)
    kick_t = hero_t = None
    enc = None if (audio_seul or apercu is not None) else subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
         os.path.join(work, "_v.mp4")], stdin=subprocess.PIPE)
    sfx = SfxTrack(len(audio))
    music_start, music_end = None, None
    mus_fen = []
    t0 = 0.0
    wi = 0
    for si, s in enumerate(segs):
        nf = 0 if audio_seul else int(round(s["dur"] * FPS))
        if apercu is not None and not any(round(t0 * FPS) <= x < round(t0 * FPS) + nf for x in apercu):
            nf = 0
        frames = read_frames(s["_clip"], None) if nf else None
        ordre = suite_images(s, nf, len(frames)) if nf else []
        kind = s["type"]
        a = read_audio(cfg, s, s.get("son", "foule" if s.get("src") == "pro" else "plein"))
        # ambiance nivelée plan par plan : la foule ne doit pas sauter de 20 dB entre
        # un plan TV (stem sans voix) et un rush téléphone. L'ouverture garde son
        # niveau d'origine (cri du commentateur).
        cibles = cfg.get("ambiance_cible_db", {"defaut": -30, "leone": -33, "fin": -31, "accroche": -30})
        if kind != "froid" and np.abs(a).max() > 1e-4:
            rms = np.sqrt((a ** 2).mean())
            g_amb = np.clip(cibles.get(kind, cibles["defaut"]) - 20 * np.log10(rms + 1e-9), -18, 12)
            mix_at(audio, a, t0, 10 ** (g_amb / 20))
        else:
            mix_at(audio, a, t0, s.get("gain", 0.6))
        card = None
        rng = np.random.default_rng(si)
        if kind == "mot":
            card = WordCard(s["sv"], s["fr"], wi, N, s.get("impact", 0.5), s.get("largeur", 960))
            wi += 1
            ti = t0 + card.impact_time()
            last = wi == N
            if last:  # moment héroïque : (montée -> temps d'air ->) impact + clameur.
                # C'est le sommet du film : deux impacts superposés à niveau fixe, la
                # clameur démarre SUR l'impact (rien dans le silence qui précède),
                # et rien de tout cela ne baisse sous la voix.
                if not any(x["type"] == "leone" for x in segs):
                    sfx.add(ti - 0.15, "montee", anchor="end", label="montée transformation")
                hero_t = ti
                sfx.add(ti, "heros", name="impact_1", label=s["sv"], libre=True)
                sfx.add(ti, "heros", name="impact_3", gain_db=-1.0, label=s["sv"] + " (grave)", libre=True)
                # la clameur retombe avant la question finale (elle ne doit pas la couvrir)
                sfx.add(ti + 0.01, "clameur", name="clameur_2", gain_db=-3.0, coupe_avant=True, libre=True, max_dur=2.4,
                        fondu=1.0, label="clameur")
                sfx.add(ti + 0.01, "clameur", name="clameur_1", gain_db=-4.0, coupe_avant=True, libre=True, max_dur=3.2,
                        fondu=1.6, label="clameur (longue)")
            else:
                # corps (impact_1, le seul qui passe sur un haut-parleur de téléphone)
                # + transitoire médium, deux prises en alternance ; queue courte pour
                # laisser la place à la voix qui suit
                sfx.add(ti, "impact", name="impact_1", gain_db=float(rng.uniform(-1.5, 1.5)),
                        st=float(rng.uniform(-0.8, 0.8)), max_dur=0.45, fondu=0.15, label=s["sv"])
                sfx.add(ti, "claque", name=("pop_4", "tic_lettre")[wi % 2], gain_db=float(rng.uniform(-1, 1)),
                        st=float(rng.uniform(-0.5, 0.5)), label=s["sv"] + " (claque)")
            if s.get("sifflet"):   # sur la coupe, court : il annonce le plan sans couvrir le mot
                sfx.add(t0 + 0.05, "sifflet", anchor="arrive", max_dur=0.42, fondu=0.06, label="sifflet")
            # sons de contact réels : [{"son", "role", "db", "dt", "max"}], calés sur le contact
            for c in s.get("contact", []):
                sfx.add(ti + c.get("dt", 0.0), c.get("role", "claque"), name=c["son"], gain_db=c.get("db", 0.0),
                        max_dur=c.get("max"), fondu=0.08, label="contact " + s["sv"])
        if kind == "accroche":  # seul « RUGBY » claque ; la musique entre dessus
            sfx.add(t0 + 0.35 + 0.16, "impact", name="impact_1", gain_db=3.0, label="RUGBY")
            music_start = t0 + 0.35 + 0.16
            if s.get("promesse"):
                sfx.add(t0 + s.get("promesse_t", 1.25) + 0.1, "claque", name="pop_4", label="promesse")
        if kind == "leone":
            # finale à la Leone : la musique s'arrête net sur la mesure, l'ambiance
            # retombe, la montée court sur les plans qui raccourcissent et s'arrête
            # 0,12 s avant le contact du pied (temps d'air), puis le « toc » du ballon
            if music_end is None:
                music_end = t0
            if s.get("role") == "frappe":
                sfx.add(t0 + s["dur"] - 0.12, "montee", anchor="end", label="montée Leone")
                kick_t = t0 + s["dur"]
                sfx.add(t0 + s["dur"] - 0.01, "coup_de_pied", name="coup_de_pied", anchor="arrive", label="frappe")
                # le coup de pied seul n'est que du grave : deux transitoires pour le téléphone
                sfx.add(t0 + s["dur"] - 0.01, "claque", name="tic_lettre", gain_db=-2.0, label="frappe (claque)")
                sfx.add(t0 + s["dur"] - 0.01, "claque", name="pop_4", label="frappe (claque)")
        if kind == "ballon":
            # pas de mitraillette : prises différentes en rotation, rythme qui
            # accélère puis ralentit (celui de la cadence), hauteur qui monte,
            # volume qui varie de ±2 dB
            tt = t0
            nch = len(s["cadence"])
            for j, nfr in enumerate(s["cadence"]):
                sfx.add(tt, "pop", anchor="arrive", st=-2 + 6 * j / max(1, nch - 1),
                        gain_db=float(rng.uniform(-2, 2)), max_dur=0.18, label=f"ballon {j}")
                tt += nfr / FPS
        if kind == "froid" and s.get("whoosh", True):  # coup de zoom final = mouvement de caméra -> whoosh
            sfx.add(t0 + s["dur"] - 0.25, "whoosh", anchor="peak", max_dur=0.9, label="zoom ouverture")
        if kind == "froid" and s.get("impact") is not None:
            # relance en plein milieu (v8) : un essai plein écran, sans carte ; l'impact
            # tombe sur le plongeon, la foule réelle explose juste après
            sfx.add(t0 + s["impact"], "impact", name="impact_1", gain_db=2.0, label="essai (relance)")
            sfx.add(t0 + s["impact"] + 0.02, "clameur", name="clameur_1", gain_db=-7.0, max_dur=1.6, fondu=0.7,
                    label="clameur relance")
        if s.get("musique_db") is not None:   # la musique s'efface sous un commentateur
            mus_fen.append((t0, t0 + s["dur"], s["musique_db"]))
        if kind == "fin":
            music_end = t0 if music_end is None else music_end
            sfx.add(t0 + 0.4 + 0.18, "impact", name="impact_1", gain_db=-5.0, max_dur=0.45, fondu=0.15, label="COMBIEN")
        impact = (card.impact_time() if card else
                  0.51 if kind == "accroche" else s.get("impact") if kind == "froid" else None)

        # --- caméra du plan (v7)
        #  « cadre » {k, x, y} : recadrage fixe centré sur un point du clip ;
        #  « punch » {k, x, y} : coup de zoom sur l'image du contact, vers ce point,
        #     tenu pendant le gel puis relâché en 8 images ;
        #  « crans » [[image, dk], ...] : crans de zoom secs (ouverture à froid) ;
        #  « pousse » : zoom lent sur la durée du plan (0,06 par défaut).
        cad, pun = s.get("cadre"), s.get("punch")
        foyer = ((cad or pun or {}).get("x", W / 2), (cad or pun or {}).get("y", H / 2))
        if s.get("foyer"):
            foyer = tuple(s["foyer"])
        pk = pun["k"] if pun else (0.05 if kind != "mot" else 0.08)
        gel_s = s["gel"][1] / FPS if (s.get("gel") and impact is not None) else 0.0
        heros = kind == "mot" and wi == N
        cy = s.get("cy", 900)
        if card is not None:
            cy = max(cy, card.cy_min())   # assombrissement et carte au même endroit
        for fi in range(nf):
            if apercu is not None and round(t0 * FPS) + fi not in apercu:
                continue
            t = fi / FPS
            p = fi / max(1, nf - 1)
            img = frames[ordre[fi]]
            k = (cad["k"] if cad else 1.0) * (1.0 + s.get("pousse", 0.06) * p)
            for f0, dk in s.get("crans", []):
                k += dk * clamp01((fi - f0 + 1) / 2)
            dx = dy = 0
            if impact is not None and t >= impact:
                e = clamp01(1 - (t - impact) / 0.25)                 # secousse : dès le contact
                ez = clamp01(1 - (t - impact - gel_s) / 0.27)        # zoom : tenu pendant le gel
                amp = 24 if kind == "mot" else 18
                dx = amp * e * np.sin(t * 90)
                dy = amp * 0.75 * e * np.cos(t * 77)
                k += pk * ez
            if kind == "froid" and t > s["dur"] - 0.6:
                k += s.get("zoom_final", 0.25) * ease_out((t - (s["dur"] - 0.6)) / 0.6)
            # fenêtre : centrée sur le point (cadre) ou zoom VERS le point (punch, crans)
            if cad:
                dx += W / 2 - foyer[0]
                dy += H / 2 - foyer[1]
            else:
                dx -= (foyer[0] - W / 2) * (1 - 1 / k)
                dy -= (foyer[1] - H / 2) * (1 - 1 / k)
            img = zoom(img, k, dx, dy)
            a_ = grade(img, "pro" if (s.get("src") == "pro" or s.get("clip")) else "rush")
            # un seul flash, sur l'image du contact (plus de flash de coupe : il diluait l'impact)
            fl = 0
            if impact is not None:
                n_fl, f_fl = (3, 0.6) if heros else (2, 0.35)
                kf = int(round((t - impact) * FPS))
                if 0 <= kf < n_fl:
                    fl = f_fl * (1 - kf / n_fl)
            if fl:
                a_ = a_ * (1 - fl) + fl
            # l'image reste nue jusqu'à l'arrivée du mot, puis s'assombrit derrière la carte
            sombre = 0.45 * clamp01((t - card.debut()) / 0.15) if kind == "mot" else \
                0 if kind in ("froid", "leone", "ballon") else 0.25
            out = Image.fromarray(finish(a_, sombre, cy)).convert("RGBA")

            if kind == "mot":
                card.draw(out, t, s["dur"], cy)
                # barre de progression haute
                d = ImageDraw.Draw(out)
                bw, y = W - 140, 210
                d.rectangle((70, y, 70 + bw, y + 8), fill=(255, 255, 255, 70))
                pr = (card_idx_prog := (wi - 1 + clamp01(t / s["dur"])) / N)
                d.rectangle((70, y, 70 + int(bw * pr), y + 8), fill=BLEU + (255,))
            elif kind == "accroche":
                lines = s.get("texte", ["ET SI ON PARLAIT", "RUGBY", "EN SAVOYARD ?"])
                ys = (640, 860, 1080)
                for li, (txt, yy) in enumerate(zip(lines, ys)):
                    ts = (0.05, 0.35, 0.75)[li]
                    pp = (t - ts) / 0.16
                    if pp <= 0:
                        continue
                    f = fit(F_DISPLAY, txt, 960, 300 if li == 1 else 120)
                    lay = text_layer(txt, f, fill=BLANC)
                    if li == 1:
                        box = Image.new("RGBA", (lay.width - 40, lay.height - 70), BLEU + (255,))
                        box = box.rotate(-4, expand=True)
                        bb = Image.new("RGBA", (max(lay.width, box.width), max(lay.height, box.height)), (0, 0, 0, 0))
                        bb.alpha_composite(box, ((bb.width - box.width) // 2, (bb.height - box.height) // 2))
                        bb.alpha_composite(lay, ((bb.width - lay.width) // 2, (bb.height - lay.height) // 2))
                        lay = bb
                    sc = 1 + 1.2 * (1 - ease_out_back(pp, 1.3)) if pp < 1 else 1
                    l2 = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BICUBIC) if sc != 1 else lay
                    out.alpha_composite(_alpha(l2, ease_out(pp * 2)), (int(W / 2 - l2.width / 2), int(yy - l2.height / 2)))
                # promesse écrite : une étiquette blanche qui claque après la question
                if s.get("promesse"):
                    pp = (t - s.get("promesse_t", 1.25)) / 0.16
                    if pp > 0:
                        lay = text_layer(s["promesse"], font(F_PASTILLE, 60), fill=BLEU, shadow=False)
                        box = Image.new("RGBA", (lay.width - 120 + 64, lay.height - 120 + 48), (255, 255, 255, 250))
                        box.alpha_composite(lay, (32 - 60, 24 - 60))
                        box = box.rotate(-4, expand=True, resample=Image.BICUBIC)
                        sc = 1 + 0.8 * (1 - ease_out_back(pp, 1.3)) if pp < 1 else 1
                        b2 = box.resize((int(box.width * sc), int(box.height * sc)), Image.BICUBIC) if sc != 1 else box
                        out.alpha_composite(_alpha(b2, ease_out(pp * 2)), (int(W / 2 - b2.width / 2), int(1290 - b2.height / 2)))
            elif kind == "fin":
                lines = s.get("texte", ["TU EN CONNAISSAIS", "COMBIEN ?"])
                for li, txt in enumerate(lines):
                    ts = 0.15 + 0.35 * li
                    pp = (t - ts) / 0.18
                    if pp <= 0:
                        continue
                    f = fit(F_DISPLAY, txt, 960, 260 if li == 1 else 115)
                    lay = text_layer(txt, f)
                    sc = 1 + 1.0 * (1 - ease_out_back(pp, 1.3)) if pp < 1 else 1
                    l2 = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BICUBIC) if sc != 1 else lay
                    out.alpha_composite(_alpha(l2, ease_out(pp * 2)), (int(W / 2 - l2.width / 2), int((640, 830)[li] - l2.height / 2)))
                cta = s.get("cta")
                cp = ease_out((t - 1.1) / 0.3) if cta else 0
                if cp > 0:
                    lay = text_layer(cta, font(F_BOLD, 58), fill=NUIT, shadow=False)
                    box = Image.new("RGBA", (lay.width - 120 + 60, lay.height - 120 + 44), (255, 255, 255, 245))
                    box.alpha_composite(lay, (30 - 60, 22 - 60))
                    out.alpha_composite(_alpha(box, cp), (int(W / 2 - box.width / 2), 1010))
                sig = s.get("signature")
                if sig:
                    sp = ease_out((t - 1.5) / 0.4)
                    if sp > 0:
                        lay = text_layer(sig, font(F_BOLD, 44))
                        out.alpha_composite(_alpha(lay, sp), (int(W / 2 - lay.width / 2), 1480))
                if t > s["dur"] - 0.3:
                    kk = (t - (s["dur"] - 0.3)) / 0.3
                    arr = np.asarray(out.convert("RGB"), np.float32) * (1 - kk)
                    out = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
            elif kind == "froid" and s.get("texte"):
                pass
            if apercu is not None:
                out.convert("RGB").save(os.path.join(work, "apercu", f"t_{t0 + t:06.2f}.jpg"), quality=88)
            else:
                enc.stdin.write(out.convert("RGB").tobytes())
        t0 += s["dur"]
        print(f"montage {si+1}/{len(segs)} ({kind})", flush=True)
    if enc is not None:
        enc.stdin.close()
        enc.wait()
    if apercu is not None:
        print("=> " + os.path.join(work, "apercu"))
        return
    # la musique peut courir sous les premiers plans du final et s'arrêter net
    # sur une barre de mesure (« musique.fin_s », temps dans le reel)
    if cfg.get("musique", {}).get("fin_s"):
        music_end = cfg["musique"]["fin_s"]

    # --- musique : entre sur « RUGBY », s'arrête net sur la fin (un temps de
    # quasi-silence avant le dernier carton), niveau réglé dans montage.json
    music = load_sound("musique")
    mus = np.zeros_like(audio)
    if music is not None and music_start is not None:
        m0 = cfg.get("musique", {}).get("debut_s", 0.0)  # point du morceau calé sur RUGBY (un temps fort)
        end = music_end if music_end is not None else total
        n = int((end - music_start) * SR)
        piece = music[int(m0 * SR): int(m0 * SR) + n].copy()
        f = int(0.12 * SR)
        if len(piece) > f:
            piece[-f:] *= np.linspace(1, 0, f)[:, None]
        mix_at(mus, piece, music_start, 10 ** (cfg.get("musique", {}).get("gain_db", -12) / 20))

    for a0, a1, db in mus_fen:
        g = np.ones(len(mus), np.float32)
        g[int(a0 * SR):int(a1 * SR)] = 10 ** (db / 20)
        r = int(0.1 * SR)
        mus *= np.convolve(g, np.ones(r) / r, mode="same")[:, None]

    # --- voix off éventuelle (fichier + repères [t_reel, t_fichier, durée]) :
    # la musique et l'ambiance baissent dessous, les effets aussi (≈ -9 dB)
    voice = np.zeros_like(audio)
    duck = np.ones(len(audio), np.float32)
    vo = cfg.get("voix")
    if vo and os.path.exists(vo["fichier"]):
        raw = run(["ffmpeg", "-v", "error", "-i", vo["fichier"], "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
        v = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        v = v / max(1e-6, np.abs(v).max())
        for tr, tf, d, *g_rep in vo["reperes"]:   # 4e valeur facultative : gain de la réplique (dB)
            piece = v[int(tf * SR): int((tf + d) * SR)].copy()
            # nivelage réplique par réplique (±4 dB max) vers -17 dBFS RMS sur la partie parlée,
            # puis petits fondus pour ne jamais entendre une coupe
            e = envelope(piece, 0.02)
            act = piece[e > e.max() * 0.25]
            if len(act):
                rms = np.sqrt((act ** 2).mean())
                piece *= 10 ** (np.clip(-17 - 20 * np.log10(rms + 1e-9), -4, 4) / 20)
            fi, fo = int(0.012 * SR), int(0.045 * SR)
            piece[:fi] *= np.linspace(0, 1, fi)
            piece[-fo:] *= np.linspace(1, 0, fo)
            mix_at(voice, np.repeat(piece[:, None], 2, 1), tr,
                   10 ** ((vo.get("gain_db", -2) + (g_rep[0] if g_rep else 0)) / 20))
            i, j = int(tr * SR), int((tr + d) * SR)
            duck[max(0, i - 4800): j + 4800] = 0.0
        duck[j:] = 0.0   # après la dernière réplique, rien ne remonte pendant le fondu final
        k = int(0.12 * SR)  # lissage des remontées (pas d'effet de pompage)
        duck = np.convolve(duck, np.ones(k) / k, mode="same")
    # « stop-down » à la Leone : tout retombe presque au silence entre le contact
    # du pied et l'impact du dernier mot, puis tout explose
    if kick_t is not None and hero_t is not None and hero_t - kick_t > 0.15:
        a0, a1 = int((kick_t + 0.06) * SR), int((hero_t - 0.02) * SR)
        r = int(0.03 * SR)
        g = np.ones(len(audio), np.float32)
        g[a0:a1] = 10 ** (-20 / 20)
        g = np.convolve(g, np.ones(r) / r, mode="same")
        audio *= g[:, None]
        mus *= g[:, None]
        # les effets aussi (queue de la montée…), une fois le coup de pied éteint
        g2 = np.ones(len(audio), np.float32)
        g2[int((kick_t + 0.35) * SR):a1] = 10 ** (-20 / 20)
        sfx.buf *= np.convolve(g2, np.ones(r) / r, mode="same")[:, None]
    # profondeur d'atténuation sous la voix, couche par couche : la musique baisse
    # peu (le tapis reste stable), la foule un peu plus, les effets à peine
    prof = cfg.get("ducking_db", {"musique": -5, "ambiance": -7, "effets": -3})
    w = 1 - duck[:, None]   # 1 sous la voix, 0 ailleurs
    gk = lambda db: 1 + w * (10 ** (db / 20) - 1)
    couches = {"ambiance": audio * gk(prof["ambiance"]), "musique": mus * gk(prof["musique"]),
               "effets": sfx.buf * gk(prof["effets"]) + sfx.libre, "voix": voice}
    audio = sum(couches.values())
    f = int(0.8 * SR)  # extinction finale (pas de son coupé net)
    end = int(total * SR)
    audio[end - f:end] *= np.linspace(1, 0, f)[:, None] ** 1.5
    audio = audio[: int(total * SR)]
    norm = max(1e-6, np.abs(audio).max()) / 0.9
    audio /= norm
    # couches séparées (même gain que le master) pour le plan des niveaux
    os.makedirs(os.path.join(work, "couches"), exist_ok=True)
    for nom, c in couches.items():
        with wave.open(os.path.join(work, "couches", nom + ".wav"), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(np.ascontiguousarray(np.clip(c[: int(total * SR)] / norm, -1, 1) * 32767).astype(np.int16).tobytes())
    with open(os.path.join(work, "repere_sons.txt"), "w", encoding="utf-8") as fh:
        for c in sfx.cues:
            fh.write(f"{c[0]:7.3f}  {c[1]:8s} {c[2] or 'MUET (aucun son)'}  {c[3]}\n")
    wpath = os.path.join(work, "_a.wav")
    with wave.open(wpath, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.ascontiguousarray(audio * 32767).astype(np.int16).tobytes())
    # -14 LUFS par un gain FIXE + limiteur (le loudnorm en une passe remontait
    # l'ouverture de 9 dB puis glissait : les rapports du mix bougeaient)
    mes = subprocess.run(["ffmpeg", "-hide_banner", "-i", wpath, "-af", "loudnorm=I=-14:TP=-1:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = float(json.loads(mes[mes.rindex("{"):])["input_i"])
    norm_af = f"volume={-14 - lufs:.2f}dB,alimiter=limit=0.85:level=false:attack=2:release=60"
    print(f"mix : {lufs:.1f} LUFS -> gain {-14 - lufs:+.1f} dB")
    out = cfg["sortie"]
    if audio_seul:
        out = os.path.splitext(out)[0] + "_son.m4a"
        run(["ffmpeg", "-v", "error", "-y", "-i", wpath, "-c:a", "aac", "-b:a", "192k",
             "-af", norm_af, out])
        print(f"=> {out} ({total:.1f} s, son seul)")
        return
    run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(work, "_v.mp4"), "-i", wpath,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", norm_af,
         "-shortest", "-movflags", "+faststart", out])
    print(f"=> {out} ({total:.1f} s)")


if __name__ == "__main__":
    main()
