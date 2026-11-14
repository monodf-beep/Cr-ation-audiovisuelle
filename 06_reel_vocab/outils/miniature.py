#!/usr/bin/env python3
"""
Miniature (couverture) du reel, alignée sur les slides « HOOK PHOTO » du
carrousel Instagram publié (Template Master Carousel, brand kit franck monod) :

- la photo occupe le haut et se fond en dégradé dans le rosso mattone ;
- titre en Semplicità Gras, blanc, aligné à gauche, en phrase (pas en capitales),
  lettres serrées (-60) et interligne 0,9 ; le jaune ne sert qu'au chiffre ;
- « fm » en bas à droite ;
- tout le texte tient dans la zone 4:5 que la grille du profil affiche.

Usage : miniature.py image_fond.png sortie.png [x_ballon y_ballon]
(le ballon, s'il est donné, reste net par-dessus le dégradé)
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOLD = os.path.join(HERE, "polices", "Semplicita-Bold.otf")
MEDIUM = os.path.join(HERE, "polices", "Semplicita-Medium.otf")
ROSSO, GIALLO, BLANC, NOIR = (0x93, 0x1E, 0x1E), (0xFF, 0xCF, 0x26), (0xFF, 0xFF, 0xFF), (0x1A, 0x1A, 0x1A)
W, H = 1080, 1920
K = W / 1200                      # le brand kit est défini sur un canvas de 1200 px
Y45 = (H - W * 5 // 4) // 2       # haut de la zone 4:5 (grille du profil) : 285
MARGE = round(64 * K)
DECALAGE = 110                    # la photo descend : la tête reste dans la zone 4:5

TITRE = [[("13", GIALLO), (" mots de rugby", BLANC)], [("en savoyard.", BLANC)]]
TAILLE_TITRE = round(110 * K)
GRAISSE = 1                       # le Gras Canva (CAST) est plus noir que la version Di Lena


def largeur(texte, f, track):
    return f.getlength(texte) + track * f.size * max(0, len(texte) - 1)


def ecrit(d, x, y, morceaux, f, track):
    """morceaux : [(texte, couleur)] sur une même ligne, interlettrage en em."""
    for texte, coul in morceaux:
        for i, ch in enumerate(texte):
            d.text((x + f.getlength(texte[:i]) + track * f.size * i, y), ch, font=f, fill=coul,
                   stroke_width=GRAISSE if f.size > 80 else 0, stroke_fill=coul)
        x += largeur(texte, f, track) + track * f.size


src = Image.open(sys.argv[1]).convert("RGB").resize((W, H), Image.LANCZOS)
# photo descendue de DECALAGE px ; la bande libérée en haut est noire et la photo
# y entre en fondu (hors de la zone 4:5, sous l'en-tête des Reels)
fond = Image.new("RGB", (W, H), NOIR)
fond.paste(src, (0, DECALAGE))
h0, h1 = DECALAGE, DECALAGE + 170
u = np.clip((np.arange(H) - h0) / (h1 - h0), 0, 1)[:, None, None]
fond = Image.fromarray((np.asarray(fond, np.float32) * u + np.array(NOIR, np.float32) * (1 - u)).astype(np.uint8))

# fondu de la photo dans le rosso (comme les slides d'accroche du carrousel)
d0, d1 = 1080, 1340
t = np.clip((np.arange(H) - d0) / (d1 - d0), 0, 1)
t = t * t * (3 - 2 * t)
a = np.asarray(fond, np.float32)
a = a * (1 - t)[:, None, None] + np.array(ROSSO, np.float32) * t[:, None, None]
img = Image.fromarray(a.astype(np.uint8))

# le ballon reste net devant le dégradé
if len(sys.argv) > 4:
    p = np.asarray(fond)
    clair = (p.min(axis=2) > 170).astype(np.uint8)
    bx, by = int(sys.argv[3]), int(sys.argv[4]) + DECALAGE
    zone = np.zeros_like(clair)
    zone[max(0, by - 210):by + 210, max(0, bx - 210):bx + 210] = 1
    clair = cv2.morphologyEx(clair * zone, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab = cv2.connectedComponents(clair)
    k = lab[by, bx]
    if k == 0:
        sys.exit("le point donné n'est pas sur le ballon (zone claire)")
    m = np.zeros_like(clair)
    cs, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(m, [max(cs, key=cv2.contourArea)], -1, 1, -1)
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    img.paste(fond, (0, 0), Image.fromarray(m * 255).filter(ImageFilter.GaussianBlur(1.2)))

d = ImageDraw.Draw(img)
# titre calé en bas de la zone 4:5, comme sur la slide 1 du carrousel
f = ImageFont.truetype(BOLD, TAILLE_TITRE)
pas = round(0.9 * TAILLE_TITRE)
bas_titre = Y45 + round(1340 * K)
cap = f.getbbox("H")
y = bas_titre - (len(TITRE) - 1) * pas - cap[3]
for ligne in TITRE:
    ecrit(d, MARGE, y, ligne, f, -0.035)   # -60 Canva ; ici le « t » Di Lena touche ses voisins en dessous de -0,035
    y += pas
# « fm » en bas à droite (brand kit : ~1066, 1365 sur 1200x1500)
ffm = ImageFont.truetype(MEDIUM, round(64 * K))
x_fm = round(1066 * K) - ffm.getlength("fm") / 2
d.text((x_fm, Y45 + round(1365 * K) - ffm.getbbox("fm")[3] + 6), "fm", font=ffm, fill=BLANC)
img.save(sys.argv[2])
print("=>", sys.argv[2], f"titre {TAILLE_TITRE} px, bas du titre {bas_titre}, zone 4:5 {Y45}-{H - Y45}")
