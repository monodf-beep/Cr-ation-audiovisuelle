#!/usr/bin/env python3
"""
Miniature (couverture) du reel, dans le système visuel du repo Personal-branding :
palette (rosso mattone, giallo, blanc), logique IMPACT (gras, lettres serrées
-0,06 em, interligne 0,9), mot accentué en giallo, trait d'accent de la signature.

Usage : miniature.py image_fond.png sortie.png [x_ballon y_ballon]
(le ballon, s'il est donné, passe par-dessus le bandeau)
"""
import os
import sys

import cv2
import numpy as np

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOLD = os.path.join(HERE, "polices", "Semplicita-Bold.otf")
MEDIUM = os.path.join(HERE, "polices", "Semplicita-Medium.otf")
ROSSO, GIALLO, BLANC = (0x93, 0x1E, 0x1E), (0xFF, 0xCF, 0x26), (0xFF, 0xFF, 0xFF)
W, H = 1080, 1920
MARGE = 96


def largeur(texte, f, track):
    return f.getlength(texte) + track * f.size * (len(texte) - 1)


def ecrit(d, x, y, morceaux, f, track):
    """morceaux : [(texte, couleur)] sur une même ligne, lettres serrées."""
    for texte, coul in morceaux:
        for i, ch in enumerate(texte):
            d.text((x + f.getlength(texte[:i]) + track * f.size * i, y), ch, font=f, fill=coul)
        x += largeur(texte, f, track) + track * f.size
    return x


fond = Image.open(sys.argv[1]).convert("RGB").resize((W, H), Image.LANCZOS)
img = fond.copy()
d = ImageDraw.Draw(img)

# bloc rosso, bord oblique (le même angle que le bandeau des mots dans le reel)
haut_g, haut_d = 1150, 1222
d.polygon([(0, haut_g), (W, haut_d), (W, H), (0, H)], fill=ROSSO)

# trait d'accent (signature du brand kit) puis titre IMPACT
y = haut_d + 52
d.rectangle((MARGE, y, MARGE + int(0.32 * (W - 2 * MARGE)), y + 12), fill=GIALLO)
y += 50
lignes = [[("Le rugby", BLANC)], [("en ", BLANC), ("savoyard", GIALLO)]]
taille = 260
while True:
    f = ImageFont.truetype(BOLD, taille)
    if max(sum(largeur(t, f, -0.06) for t, _ in l) + 0.25 * taille for l in lignes) <= W - 2 * MARGE:
        break
    taille -= 4
asc, desc = f.getmetrics()
for l in lignes:
    ecrit(d, MARGE, y - f.getbbox("L")[1], l, f, -0.06)
    y += int(0.9 * taille)
# légende (logique LECTURE aérée)
fl = ImageFont.truetype(MEDIUM, 56)
ecrit(d, MARGE, y + 22, [("13 mots · lequel manque ?", BLANC)], fl, 0.03)
bas = y + 22 + fl.getbbox("q")[3]

# le ballon passe devant le bandeau : zone claire autour du point donné,
# trous bouchés, élargie pour garder son trait noir
if len(sys.argv) > 4:
    a = np.asarray(fond)
    clair = (a.min(axis=2) > 170).astype(np.uint8)
    # le ballon touche parfois d'autres zones claires (short) : on cherche
    # dans un carré de 420 px autour du point, et on coupe les ponts fins
    bx, by = int(sys.argv[3]), int(sys.argv[4])
    zone = np.zeros_like(clair)
    zone[max(0, by - 210):by + 210, max(0, bx - 210):bx + 210] = 1
    clair = cv2.morphologyEx(clair * zone, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab = cv2.connectedComponents(clair)
    k = lab[by, bx]
    if k == 0:
        sys.exit("le point donné n'est pas sur le ballon (zone claire)")
    m = (lab == k).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    m = np.zeros_like(m)
    cv2.drawContours(m, [max(cs, key=cv2.contourArea)], -1, 1, -1)
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    masque = Image.fromarray(m * 255).filter(ImageFilter.GaussianBlur(1.2))
    img.paste(fond, (0, 0), masque)
img.save(sys.argv[2])
print("=>", sys.argv[2], "titre", taille, "px, bas du texte", bas)
