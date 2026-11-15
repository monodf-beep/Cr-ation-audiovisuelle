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

Version médaillon : --fond image.png --rond cx,cy,r [--rond-source R]
  le visage est découpé dans un rond (rayon R px autour de --visage dans la source),
  posé à (cx, cy) avec un rayon r et un liseré blanc. La photo n'est pas agrandie
  quand r <= R : elle reste nette.

Version composée : --fond image.png [--fond-echelle k --fond-decalage dx,dy]
  le selfie est détouré (segmentation selfie, modeles/selfie_multiclass_256x256.tflite)
  et posé net, sans fondu, devant l'illustration.
"""
import argparse
import os

import numpy as np

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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
ap.add_argument("--fond")
ap.add_argument("--fond-echelle", type=float, default=1.0)
ap.add_argument("--fond-decalage", default="0,0")
ap.add_argument("--etiquette", default="262,1000", help="centre de l'étiquette")
ap.add_argument("--largeur", type=int, default=390, help="largeur du texte de l'étiquette")
ap.add_argument("--rond", help="cx,cy,r : médaillon du visage")
ap.add_argument("--rond-source", type=int, default=320)
ap.add_argument("--rond-coin", choices=["hd", "hg", "bd", "bg"],
                help="accroche le médaillon à un coin de l'étiquette (cx,cy de --rond ignorés)")
ap.add_argument("--rond-debord", default="0.18,0.18",
                help="débord du rond vers l'extérieur du coin, en fraction du rayon (x,y)")
ap.add_argument("--liseré", type=int, default=14)
ap.add_argument("--effacer", action="append", default=[],
                help="x0,y0,x1,y1 (px source) : zone à retirer du détourage (un voisin collé)")
arg = ap.parse_args()


def detoure(rgb):
    """Masque de la personne au premier plan (0-255), sans les voisins."""
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    modele = os.path.join(HERE, "modeles", "selfie_multiclass_256x256.tflite")
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=mpt.BaseOptions(model_asset_path=modele), output_confidence_masks=True))
    fondc = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))).confidence_masks[0].numpy_view()
    doux = np.clip(1 - (fondc[..., 0] if fondc.ndim == 3 else fondc), 0, 1)
    m = (doux > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    m = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    # bord doux du modèle (cheveux), limité à la personne principale
    zone = cv2.dilate(m, np.ones((11, 11), np.uint8)).astype(np.float32)
    a = np.clip((doux - 0.25) / 0.5, 0, 1) * zone
    a = np.maximum(a, cv2.erode(m, np.ones((5, 5), np.uint8)).astype(np.float32))
    return (cv2.GaussianBlur(a, (0, 0), 0.7) * 255).astype(np.uint8)

# --- photo : mise à l'échelle et cadrée pour poser le visage sur la cible
src = Image.open(arg.image).convert("RGB")
vx, vy = (float(v) for v in arg.visage.split(","))
if arg.miroir:
    src = src.transpose(Image.FLIP_LEFT_RIGHT)
    vx = src.width - vx
# selfie sous un ciel couvert : un peu de contraste et de couleur, sans plus
src = ImageEnhance.Color(ImageEnhance.Contrast(src).enhance(1.10)).enhance(1.15)
tx, ty = (float(v) for v in arg.cible.split(","))
def fond_illustre():
    f = Image.open(arg.fond).convert("RGB")
    kf = max(arg.fond_echelle, W / f.width, H / f.height)
    f = f.resize((round(f.width * kf), round(f.height * kf)), Image.LANCZOS)
    dx, dy = (int(v) for v in arg.fond_decalage.split(","))
    im = Image.new("RGB", (W, H))
    im.paste(f, (min(0, max(W - f.width, dx)), min(0, max(H - f.height, dy))))
    return im


def medaillon(r):
    """Visage dans un rond (liseré blanc), en RGBA de côté 2(r+e)."""
    R = arg.rond_source
    # cadrage serré : les yeux à ~42 % du haut, le haut des cheveux peut être coupé ;
    # la vraie tribune reste derrière (un fond uni ne marchait pas)
    boite = (int(vx - R), int(vy - R * 0.85), int(vx + R), int(vy + R * 1.15))
    vignette = src.crop(boite).resize((2 * r, 2 * r), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 60, 2))
    e = arg.liseré
    rond = Image.new("L", (8 * r, 8 * r), 0)
    ImageDraw.Draw(rond).ellipse((0, 0, 8 * r - 1, 8 * r - 1), fill=255)
    rond = rond.resize((2 * r, 2 * r), Image.LANCZOS)
    anneau = Image.new("L", (8 * (r + e), 8 * (r + e)), 0)
    ImageDraw.Draw(anneau).ellipse((0, 0, 8 * (r + e) - 1, 8 * (r + e) - 1), fill=255)
    anneau = anneau.resize((2 * (r + e), 2 * (r + e)), Image.LANCZOS)
    m = Image.new("RGBA", anneau.size, (0, 0, 0, 0))
    m.paste(Image.new("RGBA", anneau.size, BLANC + (255,)), (0, 0), anneau)
    m.paste(vignette, (e, e), rond)
    return m


MED = None
if arg.rond:
    img = fond_illustre()
    rcx, rcy, rr = (int(v) for v in arg.rond.split(","))
    MED = medaillon(rr)
    if not arg.rond_coin:
        img.paste(MED, (rcx - MED.width // 2, rcy - MED.height // 2), MED)
elif arg.fond:
    # illustration en fond, selfie détouré posé devant, net
    m = detoure(np.asarray(src))
    for z in arg.effacer:
        x0, y0, x1, y1 = (int(v) for v in z.split(","))
        m[y0:y1, x0:x1] = 0
    masque = Image.fromarray(m)
    f = Image.open(arg.fond).convert("RGB")
    kf = max(arg.fond_echelle, W / f.width, H / f.height)
    f = f.resize((round(f.width * kf), round(f.height * kf)), Image.LANCZOS)
    dx, dy = (int(v) for v in arg.fond_decalage.split(","))
    img = Image.new("RGB", (W, H))
    img.paste(f, (min(0, max(W - f.width, dx)), min(0, max(H - f.height, dy))))
    s = arg.echelle
    src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    masque = masque.resize(src.size, Image.LANCZOS)
    ox, oy = int(tx - vx * s), int(ty - vy * s)
    img.paste(src, (ox, oy), masque)
else:
    s = max(arg.echelle, W / src.width, H / src.height)
    src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    ox = int(min(0, max(W - src.width, tx - vx * s)))
    oy = int(min(0, max(H - src.height, ty - vy * s)))
    img = Image.new("RGB", (W, H))
    img.paste(src, (ox, oy))

# --- étiquette : lignes centrées, la dernière plus grande
lignes = arg.lignes.split("|")
largeur_utile = arg.largeur
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

# marge autour de l'étiquette : de quoi y accrocher le médaillon à un coin
M = MED.width // 2 if (MED is not None and arg.rond_coin) else 0
fx, fy = (float(v) for v in arg.rond_debord.split(","))
G = int(M * (1 + max(fx, fy))) + 4      # le rond déborde du coin : la marge doit le contenir
calque = Image.new("RGBA", (max(bw, pw) + 40 + 2 * G, bh + ph - recouvre + 40 + 2 * G), (0, 0, 0, 0))
d = ImageDraw.Draw(calque)
bx = (calque.width - bw) // 2
haut = 20 + G
d.rectangle((bx, haut, bx + bw, haut + bh), fill=BLEU)
y = haut + pad_y
for l, f, x0, y0, lw, lh in blocs:
    d.text((bx + (bw - lw) / 2 - x0, y - y0), l, font=f, fill=BLANC)
    y += lh + inter
pxx = (calque.width - pw) // 2
pyy = haut + bh - recouvre
d.rounded_rectangle((pxx, pyy, pxx + pw, pyy + ph), radius=ph // 2, fill=BLANC)
d.text((pxx + 34 - px0, pyy + 18 - py0), arg.lieu, font=fp, fill=BLEU)
if M:
    # le centre du rond sur le coin, légèrement débordant vers l'extérieur
    kx = bx + bw if arg.rond_coin[1] == "d" else bx
    ky = haut if arg.rond_coin[0] == "h" else haut + bh
    dx = fx * M * (1 if arg.rond_coin[1] == "d" else -1)
    dy = fy * M * (-1 if arg.rond_coin[0] == "h" else 1)
    calque.alpha_composite(MED, (int(kx + dx - M), int(ky + dy - M)))
calque = calque.rotate(arg.angle, expand=True, resample=Image.BICUBIC)

# position : à gauche du visage, centrée dans la zone 3:4 comme sur la miniature du CERN
cx, cy = (int(v) for v in arg.etiquette.split(","))
img.paste(calque, (int(cx - calque.width / 2), int(cy - calque.height / 2)), calque)
img.save(arg.sortie)
print("=>", arg.sortie, "étiquette", bw, "x", bh)
