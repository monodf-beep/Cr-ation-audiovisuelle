"""Coupe et cadre les rushes des plans (tools/plans.py) en 1080x1920, sans son, dans assets/plans/.
Usage (dans 12_terra-madre/) : python3 tools/preparer-medias.py <dossier des rushes>"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from plans import MEDIAS

R = sys.argv[1]
os.makedirs("assets/plans", exist_ok=True)
GRADE = "eq=contrast=1.04:saturation=1.08,colorbalance=rs=0.02:bs=-0.02"
for cle, (rush, off, effet, d) in MEDIAS.items():
    src = os.path.join(R, rush)
    nom = f"assets/plans/{cle}"
    if rush.endswith(".jpg"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf",
                        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{GRADE}", "-q:v", "3", nom + ".jpg"], check=True)
        continue
    if effet == "clocher":
        # Le clocher, en haut a droite de la prise (cadre 720x1280) : agrandi en plein ecran.
        vf = f"crop=260:462:450:150,scale=1080:1920:flags=lanczos,{GRADE},unsharp=5:5:0.6"
    elif effet == "flou":
        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{GRADE},gblur=sigma=26,eq=brightness=-0.06"
    else:
        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{GRADE}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(off), "-t", f"{d:.2f}", "-i", src, "-an", "-vf", vf + ",fps=30",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-g", "10", nom + ".mp4"], check=True)
    print(nom, rush)
