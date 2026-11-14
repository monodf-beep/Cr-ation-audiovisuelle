#!/usr/bin/env python3
"""
Focus ballon : le même plan (déjà redessiné, aplats + trait noir) passe très vite
par plusieurs traitements d'affiche, et le cadre se resserre d'un cran sur le
ballon à chaque changement.

Usage : ballon_styles.py clip_entree.mp4 clip_sortie.mp4 7,6,5,4,4,4
"""
import subprocess
import sys

import cv2
import numpy as np

W, H, FPS = 1080, 1920, 30
src, dst = sys.argv[1], sys.argv[2]
cadence = [int(x) for x in sys.argv[3].split(",")]
ROUGE, CREME, NUIT, AZUR, OR = (200, 16, 46), (242, 234, 216), (20, 16, 24), (24, 70, 160), (236, 184, 44)

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def trait(rgb):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    return cv2.GaussianBlur((g < 60).astype(np.float32), (0, 0), 1.2)[..., None]


def lum(rgb):
    return cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (0, 0), 2).astype(np.float32) / 255


def mix(a, b, k):
    return np.asarray(a, np.float32) * (1 - k) + np.asarray(b, np.float32) * k


def original(rgb):
    return rgb.astype(np.float32)


def duotone(rgb):           # affiche deux encres : rouge et crème, trait noir
    l = lum(rgb)[..., None]
    out = np.where(l > 0.55, np.float32(CREME), np.float32(ROUGE))
    return mix(out, NUIT, trait(rgb))


def bleu(rgb):              # deux encres : azur et crème, trait noir
    l = lum(rgb)[..., None]
    out = np.where(l > 0.55, np.float32(CREME), np.float32(AZUR))
    return mix(out, NUIT, trait(rgb))


def trame(rgb):             # trame d'imprimerie : points noirs sur or
    l = lum(rgb)
    p = 22
    yy, xx = np.mgrid[0:H, 0:W]
    a = np.deg2rad(30)
    u, v = xx * np.cos(a) + yy * np.sin(a), -xx * np.sin(a) + yy * np.cos(a)
    d = np.hypot((u % p) - p / 2, (v % p) - p / 2) / (p * 0.72)
    pts = np.clip(((1 - l) - d) * 6 + 0.5, 0, 1)[..., None]
    return mix(mix(np.full(rgb.shape, OR, np.float32), NUIT, pts), NUIT, trait(rgb))


def lino(rgb):              # linogravure : noir et crème
    l = lum(rgb)[..., None]
    out = np.where(l > 0.5, np.float32(CREME), np.float32(NUIT))
    return mix(out, NUIT, trait(rgb))


def nuit(rgb):              # négatif : trait or sur nuit, clairs en rouge
    l = lum(rgb)[..., None]
    out = np.where(l > 0.72, np.float32(ROUGE), np.float32(NUIT))
    return mix(out, OR, trait(rgb))


STYLES = [original, duotone, bleu, trame, lino, nuit]


def ballon(rgb, prev):
    """Centre du ballon : la bande bleue est le seul bleu de l'image."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 0] > 100) & (hsv[..., 0] < 125) & (hsv[..., 1] > 140) & (hsv[..., 2] > 90)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return prev
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return tuple(cen[k]) if prev is None else tuple(0.6 * np.array(prev) + 0.4 * cen[k])


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
c = None
fi = 0
for j, nfr in enumerate(cadence):
    k = 1.0 + 0.16 * j                      # un cran de zoom par changement
    for q in range(nfr):
        rgb = frames[min(fi, len(frames) - 1)]
        c = ballon(rgb, c) or (W / 2, H / 2)
        img = np.clip(STYLES[j % len(STYLES)](rgb), 0, 255).astype(np.uint8)
        kk = k + (0.10 if q == 0 else 0.04 if q == 1 else 0)   # petit coup à chaque changement
        w, h = W / kk, H / kk
        x0 = float(np.clip(c[0] - w / 2, 0, W - w)); y0 = float(np.clip(c[1] - h * 0.45, 0, H - h))
        M = np.float32([[kk, 0, -x0 * kk], [0, kk, -y0 * kk]])
        enc.stdin.write(cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4).tobytes())
        fi += 1
enc.stdin.close(); enc.wait()
print("=>", dst, fi, "images")
