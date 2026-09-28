#!/usr/bin/env python3
"""
Texte derriere la personne : le mot passe derriere la tete, devant le decor.

Trois calques, du fond vers l'avant :
    1. la video d'origine
    2. le texte
    3. la personne, detouree image par image et reposee par-dessus

Le detourage vient de MediaPipe (modele « selfie segmenter », tourne sur le
processeur). Le masque est lisse dans le temps pour ne pas scintiller. Pour un
rendu plus fin sur des mouvements rapides, RobustVideoMatting (GPU) fait mieux.

Ce qui marche : un plan fixe ou presque, une personne nette sur un decor
distinct, un mot court et large (1 a 2 mots, lettres epaisses). Ce qui ne
marche pas : une personne qui bouge vite, des cheveux sur un fond de meme
couleur, un texte qui passe derriere et devant plusieurs fois.

Usage :
  python3 04_montage/texte_derriere.py prise.mp4 -o sortie.mp4 --texte DESIGN --debut 0.5 --fin 3
  python3 04_montage/texte_derriere.py prise.mp4 -o sortie.mp4 --plan textes.json
      textes.json : [{"texte": "DESIGN", "debut": 0.5, "fin": 3, "position": 0.35, "couleur": "blanc"}]
  python3 04_montage/texte_derriere.py prise.mp4 --apercu 1.5 -o apercu.png --texte DESIGN
      une seule image a 1,5 s, pour verifier avant de rendre toute la video
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outils_video import couleur, ffmpeg_bin, police, sonder  # noqa: E402

MODELE_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
              "selfie_segmenter/float16/latest/selfie_segmenter.tflite")
MODELE = os.path.expanduser("~/.cache/studio-video/selfie_segmenter.tflite")


def modele(chemin=None):
    chemin = chemin or MODELE
    if not os.path.exists(chemin):
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        print(f"telechargement du modele de detourage -> {chemin}", file=sys.stderr)
        urllib.request.urlretrieve(MODELE_URL, chemin)
    return chemin


class Detoureur:
    """Masque de la personne, image par image, lisse dans le temps."""

    def __init__(self, chemin_modele, lissage=0.55):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        opts = vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=chemin_modele),
            running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True)
        self.seg = vision.ImageSegmenter.create_from_options(opts)
        self.lissage = lissage
        self.prec = None

    def masque(self, rgb, t_ms):
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        m = self.seg.segment_for_video(img, int(t_ms)).confidence_masks[-1].numpy_view()
        m = np.squeeze(m).astype(np.float32)
        if self.prec is not None:
            m = self.lissage * self.prec + (1 - self.lissage) * m
        self.prec = m
        # Bord doux : on resserre le masque puis on l'adoucit d'un ou deux pixels.
        m = np.clip((m - 0.35) / 0.3, 0, 1)
        mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
        return np.asarray(mi, dtype=np.float32)[..., None] / 255.0

    def fermer(self):
        self.seg.close()


def calque_texte(W, H, item, police_chemin):
    """Le texte, aussi large que possible dans la largeur demandee, en RGBA."""
    texte = item["texte"]
    largeur = item.get("largeur", 0.9) * W
    corps = int(H * 0.4)
    f = police(police_chemin, corps)
    while corps > 20:
        f = police(police_chemin, corps)
        x0, y0, x1, y1 = f.getbbox(texte)
        if x1 - x0 <= largeur:
            break
        corps = int(corps * 0.92)
    x0, y0, x1, y1 = f.getbbox(texte)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = (W - (x1 - x0)) / 2 - x0
    y = item.get("position", 0.35) * H - (y1 - y0) / 2 - y0
    contour = item.get("contour", max(2, corps // 40))
    d.text((x, y), texte, font=f, fill=couleur(item.get("couleur", "blanc")) + (255,),
           stroke_width=contour, stroke_fill=couleur(item.get("couleur_contour", "noir")) + (90,))
    return np.asarray(im, dtype=np.float32) / 255.0


def opacite(item, t):
    """Fondu d'entree et de sortie de 0,25 s, et une legere montee a l'entree."""
    d, f = item["debut"], item["fin"]
    if t < d or t > f:
        return 0.0, 0
    a = min(1.0, (t - d) / 0.25, (f - t) / 0.25)
    montee = int((1 - min(1.0, (t - d) / 0.35)) * 40)
    return max(0.0, a), montee


def composer(rgb, m, calques, plan, t):
    out = rgb.astype(np.float32) / 255.0
    avec_texte = out.copy()
    for item, cal in zip(plan, calques):
        if item.get("devant"):
            continue  # pose apres la personne, plus bas
        a, montee = opacite(item, t)
        if a <= 0:
            continue
        c = np.roll(cal, montee, axis=0) if montee else cal
        al = c[..., 3:4] * a
        avec_texte = avec_texte * (1 - al) + c[..., :3] * al
    res = m * out + (1 - m) * avec_texte
    for item, cal in zip(plan, calques):
        if not item.get("devant"):
            continue
        a, montee = opacite(item, t)
        if a > 0:
            al = cal[..., 3:4] * a
            res = res * (1 - al) + cal[..., :3] * al
    return (np.clip(res, 0, 1) * 255).astype(np.uint8)


def lire_images(src, W, H):
    p = subprocess.Popen([ffmpeg_bin(), "-hide_banner", "-loglevel", "quiet", "-i", src,
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        try:
            yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
        except GeneratorExit:
            p.kill()
            raise
    p.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("-o", "--sortie", required=True)
    ap.add_argument("--texte")
    ap.add_argument("--debut", type=float, default=0.0)
    ap.add_argument("--fin", type=float, default=None)
    ap.add_argument("--position", type=float, default=0.35, help="hauteur du texte, 0 = haut, 1 = bas ; 0.35 = a hauteur de tete")
    ap.add_argument("--couleur", default="blanc")
    ap.add_argument("--plan", help="fichier JSON : liste de textes avec debut, fin, position, couleur, devant")
    ap.add_argument("--police")
    ap.add_argument("--modele", help="chemin du modele MediaPipe (telecharge sinon)")
    ap.add_argument("--apercu", type=float, help="ne rendre qu'une image, a ce temps (secondes)")
    a = ap.parse_args()

    info = sonder(a.source)
    W, H, fps = info["largeur"], info["hauteur"], info["fps"]
    if a.plan:
        plan = json.load(open(a.plan, encoding="utf-8"))
    elif a.texte:
        plan = [{"texte": a.texte, "debut": a.debut, "fin": a.fin if a.fin is not None else info["duree"],
                 "position": a.position, "couleur": a.couleur}]
    else:
        raise SystemExit("--texte ou --plan")
    calques = [calque_texte(W, H, it, a.police) for it in plan]
    det = Detoureur(modele(a.modele))

    if a.apercu is not None:
        # On deroule jusqu'a l'instant voulu pour que le lissage temporel soit le meme qu'au rendu.
        for i, rgb in enumerate(lire_images(a.source, W, H)):
            t = i / fps
            m = det.masque(rgb, t * 1000)
            if t >= a.apercu:
                Image.fromarray(composer(rgb, m, calques, plan, t)).save(a.sortie)
                Image.fromarray((m[..., 0] * 255).astype(np.uint8)).save(os.path.splitext(a.sortie)[0] + "-masque.png")
                print(f"-> {a.sortie} (+ masque) a {t:.2f} s")
                det.fermer()
                return
        raise SystemExit("temps au-dela de la fin de la video")

    tmp = a.sortie + ".sans-son.mp4"
    enc = subprocess.Popen([ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-",
                            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", tmp],
                           stdin=subprocess.PIPE)
    n = 0
    for i, rgb in enumerate(lire_images(a.source, W, H)):
        t = i / fps
        actif = any(opacite(it, t)[0] > 0 for it in plan)
        m = det.masque(rgb, t * 1000)  # toujours calcule : le lissage doit suivre toute la video
        enc.stdin.write((composer(rgb, m, calques, plan, t) if actif else rgb).tobytes())
        n += 1
    enc.stdin.close(); enc.wait()
    det.fermer()
    if info["son"]:
        subprocess.run([ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", "-i", tmp, "-i", a.source,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", a.sortie], check=True)
        os.remove(tmp)
    else:
        os.replace(tmp, a.sortie)
    print(f"-> {a.sortie} ({n} images, {len(plan)} texte(s))")


if __name__ == "__main__":
    main()
