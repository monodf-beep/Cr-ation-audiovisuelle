#!/usr/bin/env python3
"""
Exporte la couleur de la passe pellicule en LUT 3D (.cube).

Un LUT ne porte que ce qui se calcule pixel par pixel. De filmlook.py, seule la
bascule ombres froides / hautes lumieres chaudes (split_tone) est dans ce cas.
Le grain, la halation et le vignettage dependent des pixels voisins : ils
restent des filtres, appliques apres le LUT (voir la commande ffmpeg plus bas).

Le meme fichier .cube sert partout : scripts ffmpeg du studio, et tout
logiciel de montage qui lit les LUT. Une video du mode « Je fais confiance » et
une video montee a la main partent ainsi de la meme couleur.

Usage :
    python3 03_etalonnage/lut.py                  # ecrit look-pellicule.cube (33 points)
    python3 03_etalonnage/lut.py --verifier IMG   # compare LUT et filmlook.split_tone

Application a une video (ordre de filmlook.py : couleur, vignettage, grain) :
    ffmpeg -i in.mp4 -vf "lut3d=03_etalonnage/look-pellicule.cube,\
vignette=angle=PI/6,noise=alls=10:allf=t+u" -c:a copy out.mp4
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filmlook import split_tone  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "look-pellicule.cube")


def grille(n):
    """Toutes les couleurs de la grille n×n×n, rouge variant le plus vite (ordre .cube)."""
    v = np.linspace(0.0, 1.0, n, dtype=np.float32)
    b, g, r = np.meshgrid(v, v, v, indexing="ij")
    return np.stack([r, g, b], axis=-1).reshape(-1, 3)


def ecrire(n, chemin):
    sortie = split_tone(grille(n)[None, ...])[0]
    with open(chemin, "w") as f:
        f.write("# Passe pellicule du studio video : ombres froides, hautes lumieres chaudes.\n")
        f.write("# Genere par 03_etalonnage/lut.py depuis filmlook.split_tone. Ne pas editer a la main.\n")
        f.write('TITLE "Studio video - pellicule"\n')
        f.write(f"LUT_3D_SIZE {n}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n")
        for r, g, b in sortie:
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print(f"-> {chemin} ({n}x{n}x{n} = {n ** 3} couleurs)")


def lire(chemin):
    n, lignes = None, []
    with open(chemin) as f:
        for l in f:
            l = l.strip()
            if l.startswith("LUT_3D_SIZE"):
                n = int(l.split()[1])
            elif l and (l[0].isdigit() or l[0] == "-"):
                lignes.append([float(x) for x in l.split()])
    return n, np.array(lignes, dtype=np.float32).reshape(n, n, n, 3)  # [b][g][r]


def appliquer(img, n, table):
    """Interpolation trilineaire, comme lut3d=interp=trilinear dans ffmpeg."""
    p = img * (n - 1)
    i0 = np.clip(np.floor(p).astype(int), 0, n - 2)
    f = p - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = 0
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                w = (fr if dr else 1 - fr) * (fg if dg else 1 - fg) * (fb if db else 1 - fb)
                out = out + w * table[b0 + db, g0 + dg, r0 + dr]
    return out


def verifier(chemin_lut, chemin_img):
    from PIL import Image
    a = np.asarray(Image.open(chemin_img).convert("RGB"), dtype=np.float32) / 255.0
    n, table = lire(chemin_lut)
    ecart = np.abs(appliquer(a, n, table) - split_tone(a)) * 255
    print(f"ecart LUT / filmlook : moyen {ecart.mean():.2f}, max {ecart.max():.2f} (sur 255)")
    return ecart.max()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taille", type=int, default=33)
    ap.add_argument("--verifier", metavar="IMAGE")
    a = ap.parse_args()
    if a.verifier:
        sys.exit(0 if verifier(SORTIE, a.verifier) < 3 else 1)
    ecrire(a.taille, SORTIE)
