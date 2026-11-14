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
BLANC = (255, 255, 255)
NUIT = (14, 14, 20)

F_DISPLAY = os.path.join(HERE, "polices", "Anton.ttf")
F_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
F_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"


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


def prep_clip(seg, cfg, style_obj, out):
    """Écrit un clip 1080x1920 30 i/s (vidéo seule) pour le segment."""
    if os.path.exists(out):
        return
    src = cfg["sources"][seg["src"]]
    speed = seg.get("vitesse", 1.0)
    dur = seg["dur"]
    sdur = dur * speed + 0.15
    if seg["src"] == "pro":
        # recadrage 9:16 avec panoramique linéaire cx_debut -> cx_fin
        sw, sh = src["w"], src["h"]
        cw = int(round(sh * 9 / 16)) // 2 * 2
        a, b = seg.get("cx_debut", sw / 2), seg.get("cx_fin", seg.get("cx_debut", sw / 2))
        x0 = f"min(max(({a}+({b}-{a})*t/{sdur:.3f})-{cw/2},0),{sw-cw})"
        vf = (f"crop={cw}:{sh}:'{x0}':0,"
              f"hqdn3d=3:3:4:4,scale={W}:{H}:flags=lanczos,")
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
    vf += (f"setpts={1/speed:.4f}*PTS," if speed != 1 else "") + f"fps={FPS}"
    raw = run(["ffmpeg", "-v", "error", "-ss", str(seg["start"]), "-t", f"{sdur:.3f}",
               "-i", src["path"], "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    n = len(raw) // (W * H * 3)
    frames = np.frombuffer(raw, np.uint8)[: n * W * H * 3].reshape(n, H, W, 3)
    need = int(round(dur * FPS))
    if n < need:
        frames = np.concatenate([frames, np.repeat(frames[-1:], need - n, 0)])
    frames = frames[:need]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                            "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", out],
                           stdin=subprocess.PIPE)
    if style_obj is not None and seg["src"] == "pro":
        style_obj.reset()
    for f in frames:
        if style_obj is not None and seg["src"] == "pro":
            f = style_obj(np.ascontiguousarray(f))
        enc.stdin.write(np.ascontiguousarray(f).tobytes())
    enc.stdin.close()
    enc.wait()


def read_frames(path, n):
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    k = len(raw) // (W * H * 3)
    fr = np.frombuffer(raw, np.uint8)[: k * W * H * 3].reshape(k, H, W, 3)
    if k < n:
        fr = np.concatenate([fr, np.repeat(fr[-1:], n - k, 0)])
    return fr[:n]


def read_audio(cfg, seg, piste):
    """Audio mono 48 kHz du segment. piste : 'plein' (avec commentateur),
    'foule' (stem sans voix), 'aucun'."""
    n = int(seg["dur"] * SR)
    if piste == "aucun":
        return np.zeros(n, np.float32)
    src = cfg["sources"][seg["src"]]
    path = src["path"]
    start = seg["start"]
    if seg["src"] == "pro" and piste == "foule" and src.get("foule"):
        path = src["foule"]
        start = seg["start"] - src.get("foule_offset", 0.0)
    speed = seg.get("vitesse", 1.0)
    af = f"atempo={max(0.5, speed)}" if speed != 1 else "anull"
    raw = run(["ffmpeg", "-v", "error", "-ss", f"{max(0, start):.3f}", "-t", f"{seg['dur']*speed+0.2:.3f}",
               "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    a = np.pad(a, (0, max(0, n - len(a))))[:n]
    f = int(0.04 * SR)
    a[:f] *= np.linspace(0, 1, f)
    a[-f:] *= np.linspace(1, 0, f)
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
CRETE = {"impact": -4, "whoosh": -9, "montee": -12, "sifflet": -8, "clameur": -8,
         "pop": -14, "musique": -3}
_CACHE = {}


def load_sound(name):
    """Charge sons/<name>.* en mono 48 kHz, normalisé à 0 dBFS crête."""
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
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    a = a / max(1e-6, np.abs(a).max())
    _CACHE[name] = a
    return a


def pool(prefix):
    if not os.path.isdir(SONS):
        return []
    return sorted({os.path.splitext(f)[0] for f in os.listdir(SONS)
                   if f.startswith(prefix) and not f.endswith(".md")})


def envelope(a, win=0.01):
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
    return np.interp(x, np.arange(len(a)), a).astype(np.float32)


class SfxTrack:
    """Piste d'effets construite à partir d'une liste de repères."""

    def __init__(self, n):
        self.buf = np.zeros(n, np.float32)
        self.cues = []
        self._last = {}

    def add(self, t, role, name=None, anchor="arrive", gain_db=0.0, st=0.0, max_dur=None, label=""):
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
        a = pitch(a, st)
        if max_dur:
            n = int(max_dur * SR)
            if len(a) > n:
                a = a[:n].copy()
                f = int(0.03 * SR)
                a[-f:] *= np.linspace(1, 0, f)
        off = anchor_offset(a, anchor)
        g = 10 ** ((CRETE.get(role, -10) + gain_db) / 20)
        mix_at(self.buf, a * g, t - off)
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
    """« La mècllâye » -> ('LA', 'MÈCLLÂYE') ; « L'arbitro » -> ("L'", 'ARBITRO')."""
    s = sv.strip()
    if s[:2].lower() == "l'" or s[:2].lower() == "l’":
        return "L'", s[2:].upper()
    parts = s.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() in ("lo", "la", "los", "les", "le", "lé", "lés"):
        return parts[0].upper(), parts[1].upper()
    return "", s.upper()


class WordCard:
    """Mot géant façon teaser : lettres qui tombent une à une, bandeau rouge
    oblique, traduction qui glisse dessous."""

    def __init__(self, sv, fr, idx, n):
        art, noun = split_article(sv)
        self.f = fit(F_DISPLAY, noun, 980, 330)
        self.letters = []
        x = 0
        for ch in noun:
            lay = text_layer(ch, self.f, stroke=0, shadow=True) if ch != " " else None
            adv = self.f.getlength(ch)
            self.letters.append((lay, x, adv))
            x += adv
        self.noun_w = x
        asc, desc = self.f.getmetrics()
        self.noun_h = asc
        self.art = text_layer(art, font(F_DISPLAY, 120), shadow=True) if art else None
        self.fr = text_layer(fr, font(F_BOLD, 64), fill=NUIT, shadow=False)
        self.cnt = text_layer(f"{idx+1:02d}", font(F_DISPLAY, 70), shadow=True)
        self.cnt_tot = text_layer(f"/{n:02d}", font(F_DISPLAY, 40), fill=(255, 255, 255, 200), shadow=True)
        self.n_letters = sum(1 for l in self.letters if l[0] is not None)

    STAGGER, LAND = 0.045, 0.14

    def impact_time(self, t0=0.10):
        return t0 + self.STAGGER * max(0, self.n_letters - 1) + self.LAND

    def draw(self, fr, t, dur, cy=900):
        t0 = 0.10
        # bandeau rouge oblique qui balaie
        bp = ease_out((t - 0.0) / 0.22)
        if bp > 0:
            band_h = int(self.noun_h * 0.62)
            band = Image.new("RGBA", (W + 400, band_h), ROUGE + (255,))
            band = band.rotate(-6, expand=True, resample=Image.BICUBIC)
            wv = int(band.width * bp)
            if wv > 0:
                band = band.crop((0, 0, wv, band.height))
                fr.alpha_composite(band, (-200, int(cy - band.height / 2 + self.noun_h * 0.06)))
        # article au-dessus, à gauche
        x_start = (W - self.noun_w) / 2
        if self.art is not None:
            ap = ease_out((t - 0.02) / 0.18)
            if ap > 0:
                lay = self.art
                fr.alpha_composite(_alpha(lay, ap), (int(x_start - 30 + (1 - ap) * -80),
                                                     int(cy - self.noun_h / 2 - lay.height + 70)))
        # lettres
        k = 0
        for lay, x, adv in self.letters:
            if lay is None:
                continue
            ts = t0 + self.STAGGER * k
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
            box = Image.new("RGBA", (self.fr.width - 60 + 2 * pad, self.fr.height - 60 + 2 * pad),
                            (255, 255, 255, 245))
            box.alpha_composite(self.fr, (pad - 60, pad - 60))
            xx = int((W - box.width) / 2 + (1 - rp) * 500)
            fr.alpha_composite(_alpha(box, rp), (xx, int(cy + self.noun_h / 2 + 70)))
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


def finish(a, darken_center=0.0):
    global _VIGN
    if _VIGN is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _VIGN = (1 - 0.3 * np.clip(r - 0.5, 0, 1) ** 1.5)[..., None]
        band = np.exp(-((yy - 950) / 420) ** 2)[..., None]
        globals()["_BAND"] = band
    a = a * _VIGN
    if darken_center:
        a = a * (1 - darken_center * globals()["_BAND"])
    return np.clip(a * 255, 0, 255).astype(np.uint8)


def zoom(img, k, dx=0, dy=0):
    if abs(k - 1) < 1e-3 and dx == 0 and dy == 0:
        return img
    cw, ch = W / k, H / k
    x0, y0 = (W - cw) / 2 - dx, (H - ch) / 2 - dy
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

    # --- PREP
    for i, s in enumerate(segs):
        tag = f"{i:02d}_{s['src']}_{s['start']}_{s['dur']}_{s.get('vitesse',1)}_{cfg.get('style') if s['src']=='pro' else 'brut'}"
        s["_clip"] = os.path.join(work, "clips", tag.replace(".", "-") + ".mp4")
        prep_clip(s, cfg, style_obj, s["_clip"])
        print(f"prep {i+1}/{len(segs)}", flush=True)

    total = sum(s["dur"] for s in segs)
    audio = np.zeros(int((total + 1) * SR), np.float32)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                           os.path.join(work, "_v.mp4")], stdin=subprocess.PIPE)
    sfx = SfxTrack(len(audio))
    music_start, music_end = None, None
    t0 = 0.0
    wi = 0
    for si, s in enumerate(segs):
        nf = int(round(s["dur"] * FPS))
        frames = read_frames(s["_clip"], nf)
        kind = s["type"]
        a = read_audio(cfg, s, s.get("son", "foule" if s["src"] == "pro" else "plein"))
        mix_at(audio, a, t0, s.get("gain", 0.6))
        card = None
        rng = np.random.default_rng(si)
        if kind == "mot":
            card = WordCard(s["sv"], s["fr"], wi, N)
            wi += 1
            ti = t0 + card.impact_time()
            last = wi == N
            if last:  # moment héroïque : montée -> temps d'air -> impact + clameur
                sfx.add(ti - 0.15, "montee", anchor="end", label="montée transformation")
                sfx.add(ti + 0.01, "clameur", anchor="arrive", label="clameur")
            sfx.add(ti, "impact", anchor="arrive", gain_db=float(rng.uniform(-1.5, 1.5)),
                    st=float(rng.uniform(-0.4, 0.4)), label=s["sv"])
            if s.get("sifflet"):
                sfx.add(ti + 0.05, "sifflet", anchor="arrive", max_dur=0.7, label="sifflet")
        if kind == "accroche":  # seul « RUGBY » claque ; la musique entre dessus
            sfx.add(t0 + 0.35 + 0.16, "impact", anchor="arrive", gain_db=1.0, label="RUGBY")
            music_start = t0 + 0.35 + 0.16
        if kind == "froid":  # coup de zoom final = mouvement de caméra -> whoosh
            sfx.add(t0 + s["dur"] - 0.25, "whoosh", anchor="peak", max_dur=0.9, label="zoom ouverture")
        if kind == "fin":
            music_end = t0
            sfx.add(t0 + 0.4 + 0.18, "impact", anchor="arrive", gain_db=-5.0, label="COMBIEN")
        impact = (card.impact_time() if card else
                  0.51 if kind == "accroche" else None)

        for fi in range(nf):
            t = fi / FPS
            p = fi / max(1, nf - 1)
            img = frames[fi]
            # caméra : zoom lent + secousse à l'impact + coup de zoom final à froid
            k = 1.0 + 0.06 * p
            dx = dy = 0
            if impact is not None and 0 <= t - impact < 0.25:
                e = 1 - (t - impact) / 0.25
                dx = 18 * e * np.sin(t * 90)
                dy = 14 * e * np.cos(t * 77)
                k += 0.05 * e
            if kind == "froid" and t > s["dur"] - 0.6:
                k += 0.25 * ease_out((t - (s["dur"] - 0.6)) / 0.6)
            img = zoom(img, k, dx, dy)
            a_ = grade(img, "pro" if s["src"] == "pro" else "rush")
            # flash d'impact / de coupe
            fl = 0
            if si > 0 and fi < 3:
                fl = 0.5 * (1 - fi / 3)
            if impact is not None and 0 <= t - impact < 0.1:
                fl = max(fl, 0.55 * (1 - (t - impact) / 0.1))
            if fl:
                a_ = a_ * (1 - fl) + fl
            out = Image.fromarray(finish(a_, 0.45 if kind == "mot" else 0.25 if kind != "froid" else 0)).convert("RGBA")

            if kind == "mot":
                card.draw(out, t, s["dur"])
                # barre de progression haute
                d = ImageDraw.Draw(out)
                bw, y = W - 140, 210
                d.rectangle((70, y, 70 + bw, y + 8), fill=(255, 255, 255, 70))
                pr = (card_idx_prog := (wi - 1 + clamp01(t / s["dur"])) / N)
                d.rectangle((70, y, 70 + int(bw * pr), y + 8), fill=ROUGE + (255,))
            elif kind == "accroche":
                lines = s.get("texte", ["ET SI ON PARLAIT", "RUGBY", "EN SAVOYARD ?"])
                ys = (640, 860, 1080)
                for li, (txt, yy) in enumerate(zip(lines, ys)):
                    ts = (0.05, 0.35, 0.75)[li]
                    pp = (t - ts) / 0.16
                    if pp <= 0:
                        continue
                    f = fit(F_DISPLAY, txt, 960, 260 if li == 1 else 120)
                    lay = text_layer(txt, f, fill=BLANC)
                    if li == 1:
                        box = Image.new("RGBA", (lay.width - 40, lay.height - 70), ROUGE + (255,))
                        box = box.rotate(-4, expand=True)
                        bb = Image.new("RGBA", (max(lay.width, box.width), max(lay.height, box.height)), (0, 0, 0, 0))
                        bb.alpha_composite(box, ((bb.width - box.width) // 2, (bb.height - box.height) // 2))
                        bb.alpha_composite(lay, ((bb.width - lay.width) // 2, (bb.height - lay.height) // 2))
                        lay = bb
                    sc = 1 + 1.2 * (1 - ease_out_back(pp, 1.3)) if pp < 1 else 1
                    l2 = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BICUBIC) if sc != 1 else lay
                    out.alpha_composite(_alpha(l2, ease_out(pp * 2)), (int(W / 2 - l2.width / 2), int(yy - l2.height / 2)))
            elif kind == "fin":
                lines = s.get("texte", ["TU EN CONNAISSAIS", "COMBIEN ?"])
                for li, txt in enumerate(lines):
                    ts = 0.15 + 0.35 * li
                    pp = (t - ts) / 0.18
                    if pp <= 0:
                        continue
                    f = fit(F_DISPLAY, txt, 960, 230 if li == 1 else 110)
                    lay = text_layer(txt, f)
                    sc = 1 + 1.0 * (1 - ease_out_back(pp, 1.3)) if pp < 1 else 1
                    l2 = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BICUBIC) if sc != 1 else lay
                    out.alpha_composite(_alpha(l2, ease_out(pp * 2)), (int(W / 2 - l2.width / 2), int((640, 830)[li] - l2.height / 2)))
                cta = s.get("cta", "Dis-le en commentaire")
                cp = ease_out((t - 1.1) / 0.3)
                if cp > 0:
                    lay = text_layer(cta, font(F_BOLD, 58), fill=NUIT, shadow=False)
                    box = Image.new("RGBA", (lay.width - 60 + 60, lay.height - 60 + 44), (255, 255, 255, 245))
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
            enc.stdin.write(out.convert("RGB").tobytes())
        t0 += s["dur"]
        print(f"montage {si+1}/{len(segs)} ({kind})", flush=True)
    enc.stdin.close()
    enc.wait()

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
            piece[-f:] *= np.linspace(1, 0, f)
        mix_at(mus, piece, music_start, 10 ** (cfg.get("musique", {}).get("gain_db", -12) / 20))

    # --- voix off éventuelle (fichier + repères [t_reel, t_fichier, durée]) :
    # la musique et l'ambiance baissent dessous, les effets aussi (≈ -9 dB)
    voice = np.zeros_like(audio)
    duck = np.ones_like(audio)
    vo = cfg.get("voix")
    if vo and os.path.exists(vo["fichier"]):
        raw = run(["ffmpeg", "-v", "error", "-i", vo["fichier"], "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"])
        v = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        v = v / max(1e-6, np.abs(v).max())
        for tr, tf, d in vo["reperes"]:
            piece = v[int(tf * SR): int((tf + d) * SR)]
            mix_at(voice, piece, tr, 10 ** (vo.get("gain_db", -2) / 20))
            i, j = int(tr * SR), int((tr + d) * SR)
            duck[max(0, i - 4800): j + 4800] = 10 ** (-9 / 20)
        k = int(0.08 * SR)  # lissage des remontées
        duck = np.convolve(duck, np.ones(k) / k, mode="same")
    audio = audio * duck + mus * duck + sfx.buf * duck + voice
    audio = audio[: int(total * SR)]
    audio /= max(1e-6, np.abs(audio).max()) / 0.9
    with open(os.path.join(work, "repere_sons.txt"), "w", encoding="utf-8") as fh:
        for c in sfx.cues:
            fh.write(f"{c[0]:7.3f}  {c[1]:8s} {c[2] or 'MUET (aucun son)'}  {c[3]}\n")
    wpath = os.path.join(work, "_a.wav")
    with wave.open(wpath, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    out = cfg["sortie"]
    run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(work, "_v.mp4"), "-i", wpath,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1",
         "-shortest", "-movflags", "+faststart", out])
    print(f"=> {out} ({total:.1f} s)")


if __name__ == "__main__":
    main()
