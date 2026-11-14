#!/usr/bin/env python3
"""
Reel vertical 9:16 : liste de vocabulaire savoyard sur les rushes du match.

Structure
  ACCROCHE  selfie réaction + question en gros (< 1 s pour accrocher)
  MOTS      un plan du stade par mot ; le mot savoyard apparaît d'abord
            (« devine »), la traduction arrive ~1 s plus tard
  FIN       selfie + « tu en connaissais combien ? » + appel au commentaire

Ajouts par rapport à un simple défilé de cartons :
  - effet devinette (mot puis traduction décalée) pour retenir le regard
  - compteur 3/8 et barre de progression : on sait où on en est, on reste
  - zoom lent (Ken Burns) + flash de coupe : les plans fixes au téléphone
    deviennent dynamiques
  - étalonnage commun (contraste, chaleur, vignettage) pour unifier les rushes
  - son : ambiance réelle du stade + « pop » à chaque mot, « ding » à la
    traduction, souffle aux coupes
  - textes dans la zone sûre Reels (ni sous le pseudo en haut, ni sous la
    légende en bas)

Usage : python3 reel.py RUSHES_DIR [vocab.json] [sortie.mp4]
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
SR = 48000
OVER = 1.10                          # marge pour le zoom lent
SW, SH = int(W * OVER) // 2 * 2, int(H * OVER) // 2 * 2

ROUGE = (200, 16, 46)                # rouge de Savoie
BLANC = (255, 255, 255)
NUIT = (18, 18, 24)

F_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
F_ITAL = "/usr/share/fonts/opentype/inter/Inter-SemiBoldItalic.otf"

HERE = os.path.dirname(os.path.abspath(__file__))

# Plans retenus dans les rushes du 7/11 : (fichier, début s, vitesse)
HOOK = ("125433", 0.0, 1.0)
OUTRO = ("132647", 4.6, 1.0)
BROLL = [
    ("125704", 0.2, 1.0),   # mêlée près des poteaux, applaudissements
    ("125950", 2.0, 1.0),   # plan large, phase de jeu
    ("130210", 0.2, 1.0),   # mêlée, poteaux
    ("125644", 0.5, 0.6),   # tribunes (120 i/s -> ralenti)
    ("125950", 12.0, 1.0),
    ("143416", 0.5, 1.0),
    ("135004", 4.0, 1.0),   # tribunes, projecteurs
    ("125950", 20.0, 1.0),
    ("143332", 8.0, 1.0),   # fin de match, drapeau sud-africain
    ("143456", 5.0, 1.0),
    ("135004", 14.0, 1.0),
    ("143456", 25.0, 1.0),
]

T_HOOK, T_WORD, T_OUTRO = 2.6, 3.0, 3.6
REVEAL = 1.0                        # délai avant la traduction


# ---------------------------------------------------------------- outils
def ease_out_back(x, s=1.9):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def font(path, size):
    return ImageFont.truetype(path, size)


def fit_font(path, text, max_w, start, mini=48):
    s = start
    while s > mini:
        f = font(path, s)
        if f.getbbox(text)[2] - f.getbbox(text)[0] <= max_w:
            return f
        s -= 4
    return font(path, mini)


def pill(text, f, fg, bg, padx=44, pady=26, radius=None, shadow=True):
    """Texte dans un cartouche arrondi, renvoyé en RGBA."""
    l, t, r, b = f.getbbox(text)
    tw, th = r - l, b - t
    w, h = tw + 2 * padx, th + 2 * pady
    m = 30
    img = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    rad = radius if radius is not None else h // 3
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            (m, m + 10, m + w, m + h + 10), rad, fill=(0, 0, 0, 120))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((m, m, m + w, m + h), rad, fill=bg)
    d.text((m + padx - l, m + pady - t), text, font=f, fill=fg)
    return img


def shadow_text(text, f, fill=BLANC, blur=10):
    l, t, r, b = f.getbbox(text)
    m = 40
    img = Image.new("RGBA", (r - l + 2 * m, b - t + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((m - l, m - t + 4), text, font=f, fill=(0, 0, 0, 200))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text((m - l, m - t), text, font=f, fill=fill)
    return img


def place(frame, layer, cx, cy, scale=1.0, alpha=1.0):
    """Colle `layer` centré en (cx, cy) avec échelle et opacité."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        layer = layer.resize((max(1, int(layer.width * scale)),
                              max(1, int(layer.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    frame.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


# ---------------------------------------------------------------- images
def read_clip(path, start, speed, dur):
    """Frames RGB (SW x SH) d'un extrait, rotation téléphone appliquée."""
    src_dur = dur * speed + 0.2
    vf = (f"setpts={1/speed:.4f}*PTS," if speed != 1 else "") + \
        f"scale={SW}:{SH}:force_original_aspect_ratio=increase,crop={SW}:{SH},fps={FPS}"
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", f"{src_dur:.3f}",
           "-i", path, "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    n = len(raw) // (SW * SH * 3)
    frames = np.frombuffer(raw, np.uint8)[: n * SW * SH * 3].reshape(n, SH, SW, 3)
    need = int(round(dur * FPS))
    if n < need:                      # rush trop court : on fige la dernière image
        frames = np.concatenate([frames, np.repeat(frames[-1:], need - n, 0)])
    return frames[:need]


def make_grade():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vign = 1 - 0.28 * np.clip(r - 0.55, 0, 1) ** 1.6
    # dégradé sombre derrière la zone de texte (bas-centre)
    g = np.clip((yy / H - 0.38) / 0.35, 0, 1) * (1 - np.clip((yy / H - 0.86) / 0.14, 0, 1) * 0.3)
    shade = 1 - 0.55 * g
    return (vign * shade)[..., None].astype(np.float32)


GRADE = None


def grade(rgb, text_zone=True):
    a = rgb.astype(np.float32) / 255
    a = np.clip((a - 0.5) * 1.12 + 0.5 + 0.01, 0, 1)                 # contraste
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
    a = np.clip(lum + (a - lum) * 1.18, 0, 1)                         # saturation
    a = a * np.array([1.03, 1.0, 0.95], np.float32)                   # chaleur
    if text_zone:
        a = a * GRADE
    else:
        a = a * (GRADE ** 0.35)
    return np.clip(a * 255, 0, 255).astype(np.uint8)


def kenburns(frame, p, zin=True):
    k = (1.0 + 0.08 * p) if zin else (1.08 - 0.08 * p)
    cw, ch = SW / (k * OVER), SH / (k * OVER)
    x0, y0 = (SW - cw) / 2, (SH - ch) / 2
    img = Image.fromarray(frame).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    return np.asarray(img)


# ---------------------------------------------------------------- sons
def read_audio(path, start, speed, dur):
    af = f"atempo={speed}" if speed != 1 else "anull"
    if speed < 0.5:
        af = "atempo=0.5"
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", f"{dur*speed+0.2:.3f}",
           "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = int(dur * SR)
    if len(a) < n:
        a = np.pad(a, (0, n - len(a)))
    return a[:n]


def sfx_pop(f0=520, dur=0.12):
    t = np.arange(int(SR * dur)) / SR
    f = f0 * (1 + 1.6 * np.exp(-t * 40))
    return 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30)


def sfx_ding():
    t = np.arange(int(SR * 0.6)) / SR
    s = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1318, .5), (1976, .25), (2637, .12)))
    return 0.35 * s * np.exp(-t * 7) * np.clip(t * 400, 0, 1)


def sfx_whoosh(dur=0.32):
    n = int(SR * dur)
    rng = np.random.default_rng(1)
    x = rng.standard_normal(n)
    # bruit filtré par une moyenne glissante dont la largeur varie : souffle
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    k = 24
    y = np.convolve(x, np.ones(k) / k, mode="same")
    return 0.5 * y * env


def mix_at(buf, s, t):
    i = int(t * SR)
    j = min(len(buf), i + len(s))
    if i < len(buf):
        buf[i:j] += s[: j - i]


# ---------------------------------------------------------------- rendu
def main():
    global GRADE
    rush = sys.argv[1] if len(sys.argv) > 1 else "rushes"
    cfg_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "vocab.json")
    out = sys.argv[3] if len(sys.argv) > 3 else "reel_vocab.mp4"
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    mots = cfg["mots"]
    N = len(mots)
    GRADE = make_grade()

    # --- calques texte précalculés
    f_tag = font(F_BOLD, 40)
    tag = pill(f"LE {cfg['theme']} EN SAVOYARD", f_tag, BLANC, ROUGE + (255,), padx=30, pady=18)
    hook_l1 = shadow_text(cfg["hook"][0], font(F_BLACK, 92))
    hook_l2 = pill(cfg["hook"][1], font(F_BLACK, 170), BLANC, ROUGE + (255,), padx=50, pady=30)
    hook_l3 = shadow_text(cfg["hook"][2], font(F_BLACK, 92))
    out_l1 = shadow_text(cfg["outro"][0], font(F_BLACK, 88))
    out_l2 = pill(cfg["outro"][1], font(F_BLACK, 150), BLANC, ROUGE + (255,), padx=50, pady=30)
    out_cta = pill(cfg["cta"], font(F_BOLD, 56), NUIT, (255, 255, 255, 240), padx=40, pady=24)
    out_sig = shadow_text(cfg["signature"], font(F_BOLD, 44))

    cards = []
    for i, m in enumerate(mots):
        sv = pill(m["sv"], fit_font(F_BLACK, m["sv"], 820, 140), BLANC, ROUGE + (255,),
                  padx=54, pady=34)
        pr = shadow_text(m.get("pron", ""), font(F_ITAL, 54)) if m.get("pron") else None
        fr = pill(m["fr"], fit_font(F_BOLD, m["fr"], 760, 84), NUIT, (255, 255, 255, 245),
                  padx=44, pady=26)
        lab = shadow_text("en français", font(F_BOLD, 34), fill=(255, 255, 255, 220), blur=6)
        cnt = shadow_text(f"{i+1} / {N}", font(F_BLACK, 52))
        cards.append((sv, pr, fr, lab, cnt))

    # --- plan de montage
    segs = [("hook", HOOK, T_HOOK, None)]
    for i in range(N):
        segs.append(("mot", tuple(mots[i]["plan"]) if "plan" in mots[i] else BROLL[i % len(BROLL)], T_WORD, i))
    segs.append(("outro", OUTRO, T_OUTRO, None))
    total = sum(s[2] for s in segs)

    audio = np.zeros(int((total + 1) * SR), np.float32)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "_video.mp4"],
        stdin=subprocess.PIPE)

    t0 = 0.0
    for si, (kind, (name, start, speed), dur, idx) in enumerate(segs):
        path = os.path.join(rush, name + ".mp4")
        frames = read_clip(path, start, speed, dur)
        a = read_audio(path, start, speed, dur)
        fade = int(0.06 * SR)
        a[:fade] *= np.linspace(0, 1, fade)
        a[-fade:] *= np.linspace(1, 0, fade)
        i0 = int(t0 * SR)
        audio[i0:i0 + len(a)] += 0.55 * a
        if si > 0:
            mix_at(audio, sfx_whoosh(), max(0, t0 - 0.16))
        if kind == "mot":
            mix_at(audio, sfx_pop(), t0 + 0.12)
            mix_at(audio, sfx_ding(), t0 + REVEAL)
        if kind == "hook":
            mix_at(audio, sfx_pop(420), 0.5)
        if kind == "outro":
            mix_at(audio, sfx_pop(), t0 + 0.4)
            mix_at(audio, sfx_ding(), t0 + 1.1)

        nf = len(frames)
        for fi in range(nf):
            t = fi / FPS
            p = fi / max(1, nf - 1)
            img = kenburns(frames[fi], p, zin=(si % 2 == 0))
            img = grade(img, text_zone=(kind == "mot"))
            # flash de coupe
            if si > 0 and fi < 4:
                fl = (1 - fi / 4) * 0.45
                img = np.clip(img.astype(np.float32) * (1 - fl) + 255 * fl, 0, 255).astype(np.uint8)
            fr = Image.fromarray(img).convert("RGBA")

            if kind == "hook":
                place(fr, hook_l1, W / 2, 620, 1, ease_out(t / 0.2))
                place(fr, hook_l2, W / 2, 790, ease_out_back((t - 0.12) / 0.35), ease_out((t - 0.12) / 0.15))
                place(fr, hook_l3, W / 2, 965, 1, ease_out((t - 0.45) / 0.25))
            elif kind == "mot":
                sv, pr, frl, lab, cnt = cards[idx]
                place(fr, tag, W / 2, 330, 1, 1)
                place(fr, cnt, W / 2, 430, 1, 1)
                place(fr, sv, W / 2, 1000, ease_out_back((t - 0.08) / 0.38), ease_out((t - 0.08) / 0.12))
                if pr is not None:
                    place(fr, pr, W / 2, 1150, 1, ease_out((t - 0.4) / 0.3))
                rp = (t - REVEAL) / 0.35
                place(fr, lab, W / 2, 1265 + 20 * (1 - ease_out(rp)), 1, ease_out(rp))
                place(fr, frl, W / 2, 1360 + 60 * (1 - ease_out(rp)), 1, ease_out(rp))
                # barre de progression
                d = ImageDraw.Draw(fr)
                bw, gap, y = 760, 10, 1560
                sw = (bw - gap * (N - 1)) / N
                for k in range(N):
                    x = (W - bw) / 2 + k * (sw + gap)
                    d.rounded_rectangle((x, y, x + sw, y + 12), 6, fill=(255, 255, 255, 90))
                    fill = 1.0 if k < idx else (min(1, t / dur) if k == idx else 0)
                    if fill > 0:
                        d.rounded_rectangle((x, y, x + max(12, sw * fill), y + 12), 6, fill=ROUGE + (255,))
            else:
                place(fr, out_l1, W / 2, 640, 1, ease_out(t / 0.25))
                place(fr, out_l2, W / 2, 810, ease_out_back((t - 0.4) / 0.35), ease_out((t - 0.4) / 0.15))
                place(fr, out_cta, W / 2, 1020, 1, ease_out((t - 1.1) / 0.3))
                place(fr, out_sig, W / 2, 1500, 1, ease_out((t - 1.5) / 0.4))
            # fondu au noir final
            if kind == "outro" and t > dur - 0.35:
                k = (t - (dur - 0.35)) / 0.35
                arr = np.asarray(fr.convert("RGB"), np.float32) * (1 - k)
                fr = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
            enc.stdin.write(fr.convert("RGB").tobytes())
        t0 += dur
        print(f"  segment {si+1}/{len(segs)} ({kind}) ok", flush=True)

    enc.stdin.close()
    enc.wait()

    audio = audio[: int(total * SR)]
    audio /= max(1e-6, np.abs(audio).max()) / 0.89
    with wave.open("_audio.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "_video.mp4", "-i", "_audio.wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove("_video.mp4")
    os.remove("_audio.wav")
    print(f"=> {out}  ({total:.1f} s)")


if __name__ == "__main__":
    main()
