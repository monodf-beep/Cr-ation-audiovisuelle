#!/usr/bin/env python3
"""
Outils communs aux scripts de mise en page du montage.

Pas de drawtext dans le ffmpeg livre avec imageio : tous les textes a l'ecran
sont dessines avec Pillow en PNG transparent, puis poses par ffmpeg (overlay).
"""

import json
import os
import re
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

POLICES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Formats de sortie : largeur, hauteur.
FORMATS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "16:9": (1920, 1080), "1:1": (1080, 1080)}


def ffmpeg_bin():
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def sonder(chemin):
    """Largeur, hauteur, images/s, duree, presence d'une piste son (lu dans la sortie de ffmpeg -i)."""
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", chemin], capture_output=True, text=True)
    err = r.stderr
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    fps = re.search(r"([\d.]+) fps", err)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    rot = re.search(r"rotation of (-?[\d.]+)", err) or re.search(r"rotate\s*:\s*(-?\d+)", err)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    if rot and abs(float(rot.group(1))) % 180 == 90:
        w, h = h, w
    return {
        "largeur": w, "hauteur": h,
        "fps": float(fps.group(1)) if fps else 25.0,
        "duree": int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else 0.0,
        "son": "Audio:" in err,
    }


def police(chemin=None, corps=64):
    for p in ([chemin] if chemin else []) + POLICES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, corps)
    return ImageFont.load_default()


def couleur(c):
    """'#DC5D45', 'DC5D45' ou 'blanc'/'noir' -> tuple RGB."""
    noms = {"blanc": "FFFFFF", "noir": "111111", "rouge": "DC5D45", "rose": "F6C1C9", "creme": "F7F1E8", "marine": "18365E"}
    c = noms.get(c, c).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def etiquette(texte, corps, fond="rose", encre="noir", police_chemin=None, marge=0.28, contour=0):
    """Une etiquette (texte dans un bloc de couleur), en PNG transparent. fond=None : texte seul."""
    f = police(police_chemin, corps)
    x0, y0, x1, y1 = f.getbbox(texte)
    pad = int(corps * marge)
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    im = Image.new("RGBA", (w + 2 * contour, h + 2 * contour), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fond:
        d.rectangle([contour, contour, contour + w - 1, contour + h - 1], fill=couleur(fond) + (255,))
    d.text((contour + pad - x0, contour + pad - y0), texte, font=f, fill=couleur(encre) + (255,),
           stroke_width=contour, stroke_fill=(0, 0, 0, 255) if contour else None)
    return im


def enregistrer_json(chemin, donnees):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)


def lancer(cmd):
    """Lance ffmpeg ; affiche la fin de l'erreur si ca echoue."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg a echoue :\n" + r.stderr[-2000:])
    return r
