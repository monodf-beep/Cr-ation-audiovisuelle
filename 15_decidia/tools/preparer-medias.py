"""Prépare les médias du montage (hors dépôt) à partir de rushes/ : plans vidéo coupés au format 1080 x 1920,
30 images/s, sans son ; son direct des plans parlés à part ; photos au format du cadre ; logo Savoy IA détouré.
Usage (dans 15_decidia/) : python3 tools/preparer-medias.py
Les points d'entrée et de sortie sont ceux du montage (index.html, tools/monter.py)."""
import json, os, subprocess
import numpy as np
from PIL import Image

R = "rushes/"
os.makedirs("assets", exist_ok=True)

# Image corrigée, pas détournée (04_montage/BONNES-PRATIQUES.md) : un peu de lumière et de chaleur, rien de plus.
GRADE = "eq=brightness=0.02:contrast=1.04:saturation=1.08,colorbalance=rm=0.02:bm=-0.02"

# nom : (rush, entrée, sortie, miroir, son direct)
# Les selfies du stand sont filmés en miroir (l'enseigne « Traiteur La Rioule » se lit à l'envers) : on les retourne.
PLANS = {
    "hook":        ("VID_20261015_114308.mp4", 0.00, 1.95, False, False),   # accueil exposants Décidia
    "duo":         ("VID_20261015_103245.mp4", 4.55, 6.85, False, True),    # Franck et Rony saluent (coupé avant « Nous sommes… »)
    "allee":       ("VID_20261015_114135.mp4", 2.00, 5.15, False, False),   # allée du hall A
    "frenchtech":  ("VID_20261015_112126.mp4", 0.00, 2.60, False, False),   # stand de la French Tech
    "affiche":     ("VID_20261015_110711.mp4", 0.30, 2.80, False, False),   # programme des conférences
    "entreprises": ("VID_20261015_114135.mp4", 0.00, 1.95, False, False),   # stand « Offres entreprises »
    "cabine":      ("VID_20261015_114118.mp4", 0.00, 3.20, False, False),   # stand du Téléphérique du Salève
    "stand":       ("VID_20261015_104526.mp4", 20.00, 22.70, True, False),  # le stand du traiteur, sans visage
    "rioule-1":    ("VID_20261015_104526.mp4", 3.05, 5.45, True, True),     # « tu sais ce que ça veut dire, la rioule ? »
    "rioule-2":    ("VID_20261015_104526.mp4", 8.50, 10.30, True, True),    # « c'est faire la fête, la bambouche »
    "rioule-3":    ("VID_20261015_104526.mp4", 11.95, 12.75, True, True),   # « exactement, bravo »
    "bientot":     ("VID_20261015_145936.mp4", 144.70, 146.90, False, True),# « … à bientôt ! », la main levée
}

def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)

durees = {}
for nom, (rush, a, b, miroir, son) in PLANS.items():
    vf = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30"
    if miroir: vf += ",hflip"
    vf += "," + GRADE
    # Images clés toutes les 10 images : la recherche d'image au rendu reste exacte et rapide.
    ff("-ss", f"{a}", "-t", f"{b - a}", "-i", R + rush, "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium",
       "-crf", "17", "-g", "10", "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"assets/{nom}.mp4")
    if son:
        ff("-ss", f"{a}", "-t", f"{b - a}", "-i", R + rush, "-vn", "-ac", "2", "-ar", "48000", f"assets/{nom}.wav")
    durees[nom] = round(b - a, 3)
    print(f"plan   assets/{nom}.mp4  {b - a:.2f} s" + ("  + son direct" if son else ""))

# Photos du public et de la scène, recadrées au format 9:16 du cadre (1440 x 1920, marge pour la poussée lente).
for i in (5, 6, 7, 8, 9):
    im = Image.open(f"{R}IMG-20261015-WA000{i}.jpg").convert("RGB")
    im = im.resize((1440, 1920), Image.LANCZOS)
    im.save(f"assets/photo-{i}.jpg", quality=92)
    print(f"photo  assets/photo-{i}.jpg")

# Logo Savoy IA : la sphère et le nom, détourés du fond sombre de l'image officielle (savoy-ia.fr).
src = np.asarray(Image.open("assets/logos/savoy-ia.png").convert("RGB")).astype(np.float32)
crop = src[300:900, 240:840]
m = crop.max(axis=2)
alpha = np.clip((m - 60) / 50, 0, 1)
fond = np.array([27, 27, 27], np.float32)
rgb = np.where(alpha[..., None] > 0, (crop - fond * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 1e-3), 0)
out = np.dstack([np.clip(rgb, 0, 255), alpha * 255]).astype(np.uint8)
Image.fromarray(out, "RGBA").save("assets/logos/savoy-ia-detoure.png")
print("logo   assets/logos/savoy-ia-detoure.png")

json.dump(durees, open("assets/durees.json", "w"), indent=1)
