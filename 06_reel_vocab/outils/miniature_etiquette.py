#!/usr/bin/env python3
"""
Miniature de reel « étiquette », sur le modèle de « Le savoyard au CERN »
(reel publié, 5 225 vues) :

- selfie plein cadre, visage à droite, le lieu visible à gauche ;
- étiquette bleue inclinée, texte blanc en capitales condensées, centré,
  le dernier mot plus grand ;
- pastille blanche dessous, lieu en bleu (« Ville · Précision ») ;
- pas de dégradé, pas de logo : le visage et l'étiquette suffisent.

Usage :
  miniature_etiquette.py selfie.png sortie.png --visage X,Y [--miroir]
      [--lignes "LE SAVOYARD|AU|RUGBY"] [--lieu "Turin · Allianz Stadium"]
  --visage : point entre les yeux, en px de l'image source
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONDENSEE = os.path.join(HERE, "polices", "Anton.ttf")
PASTILLE = os.path.join(HERE, "polices", "Semplicita-Bold.otf")
BLEU = (0x0A, 0x36, 0xA8)        # bleu de l'étiquette « Le savoyard au CERN » (relevé)
BLANC = (0xFF, 0xFF, 0xFF)
W, H = 1080, 1920
Y34 = (H - W * 4 // 3) // 2      # haut de la zone 3:4 affichée dans la grille du profil : 240

ap = argparse.ArgumentParser()
ap.add_argument("image")
ap.add_argument("sortie")
ap.add_argument("--visage", required=True)
ap.add_argument("--miroir", action="store_true")
ap.add_argument("--cible", default="800,860", help="où placer le point entre les yeux")
ap.add_argument("--echelle", type=float, default=1.66)
ap.add_argument("--lignes", default="LE SAVOYARD|AU|RUGBY")
ap.add_argument("--lieu", default="Turin · Allianz Stadium")
ap.add_argument("--angle", type=float, default=7.0)
arg = ap.parse_args()

# --- photo : mise à l'échelle et cadrée pour poser le visage sur la cible
src = Image.open(arg.image).convert("RGB")
vx, vy = (float(v) for v in arg.visage.split(","))
if arg.miroir:
    src = src.transpose(Image.FLIP_LEFT_RIGHT)
    vx = src.width - vx
s = max(arg.echelle, W / src.width, H / src.height)
src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
tx, ty = (float(v) for v in arg.cible.split(","))
ox = int(min(0, max(W - src.width, tx - vx * s)))
oy = int(min(0, max(H - src.height, ty - vy * s)))
img = Image.new("RGB", (W, H))
img.paste(src, (ox, oy))
# selfie sous un ciel couvert : un peu de contraste et de couleur, sans plus
img = ImageEnhance.Contrast(img).enhance(1.10)
img = ImageEnhance.Color(img).enhance(1.15)

# --- étiquette : lignes centrées, la dernière plus grande
lignes = arg.lignes.split("|")
largeur_utile = 390
tailles = []
for i, l in enumerate(lignes):
    t = 230 if i == len(lignes) - 1 else 104
    while ImageFont.truetype(CONDENSEE, t).getlength(l) > largeur_utile:
        t -= 2
    tailles.append(t)
# les lignes courtes (« AU ») gardent la taille des lignes de tête
tailles = [min(t, tailles[0]) if i < len(lignes) - 1 else t for i, t in enumerate(tailles)]
pad_x, pad_y, inter = 34, 34, 14
blocs = []
for l, t in zip(lignes, tailles):
    f = ImageFont.truetype(CONDENSEE, t)
    x0, y0, x1, y1 = f.getbbox(l)
    blocs.append((l, f, x0, y0, x1 - x0, y1 - y0))
bw = largeur_utile + 2 * pad_x
bh = sum(b[5] for b in blocs) + inter * (len(blocs) - 1) + 2 * pad_y

# pastille du lieu
fp = ImageFont.truetype(PASTILLE, 40)
px0, py0, px1, py1 = fp.getbbox(arg.lieu)
pw, ph = (px1 - px0) + 2 * 34, (py1 - py0) + 2 * 18
recouvre = 16                                        # la pastille mord sur le bas de l'étiquette

calque = Image.new("RGBA", (max(bw, pw) + 40, bh + ph - recouvre + 40), (0, 0, 0, 0))
d = ImageDraw.Draw(calque)
bx = (calque.width - bw) // 2
d.rectangle((bx, 20, bx + bw, 20 + bh), fill=BLEU)
y = 20 + pad_y
for l, f, x0, y0, lw, lh in blocs:
    d.text((bx + (bw - lw) / 2 - x0, y - y0), l, font=f, fill=BLANC)
    y += lh + inter
pxx = (calque.width - pw) // 2
pyy = 20 + bh - recouvre
d.rounded_rectangle((pxx, pyy, pxx + pw, pyy + ph), radius=ph // 2, fill=BLANC)
d.text((pxx + 34 - px0, pyy + 18 - py0), arg.lieu, font=fp, fill=BLEU)
calque = calque.rotate(arg.angle, expand=True, resample=Image.BICUBIC)

# position : à gauche du visage, centrée dans la zone 3:4 comme sur la miniature du CERN
cx, cy = 262, Y34 + 760
img.paste(calque, (int(cx - calque.width / 2), int(cy - calque.height / 2)), calque)
img.save(arg.sortie)
print("=>", arg.sortie, "échelle", round(s, 2), "décalage", ox, oy, "étiquette", bw, "x", bh)
