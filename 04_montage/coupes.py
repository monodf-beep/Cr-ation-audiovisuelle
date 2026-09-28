#!/usr/bin/env python3
"""
Coupes franches : retire les silences d'une prise face camera.

ffmpeg repere les silences (silencedetect), on garde tout le reste avec une
petite marge avant et apres la parole, et chaque raccord recoit un fondu son
de 30 ms pour ne pas claquer. Le decoupage est ecrit a cote, en JSON, pour
pouvoir le relire ou le reprendre dans un logiciel de montage.

Une prise coupee au silence enchaine les coupes au meme cadre : c'est la que
l'on pose un zoom avant (--zoom) ou un plan de coupe, sinon l'image saute.

Usage :
  python3 04_montage/coupes.py prise.mp4 -o prise-coupee.mp4
  python3 04_montage/coupes.py prise.mp4 --liste          # affiche seulement ce qui serait coupe
Reglages :
  --seuil -35       niveau en dB sous lequel on parle de silence (plus bas = plus strict)
  --silence 0.45    duree minimale d'un silence a couper (s)
  --marge 0.08      parole gardee avant et apres chaque morceau (s)
  --zoom 1.08       une coupe sur deux est legerement recadree, pour masquer le saut
"""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outils_video import enregistrer_json, ffmpeg_bin, lancer, sonder  # noqa: E402


def silences(src, seuil, duree_min):
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", src, "-af",
                        f"silencedetect=noise={seuil}dB:d={duree_min}", "-f", "null", "-"],
                       capture_output=True, text=True)
    debuts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    fins = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(debuts, fins + [None] * (len(debuts) - len(fins))))


def morceaux(sil, duree, marge):
    garder, t = [], 0.0
    for d, f in sil:
        f = duree if f is None else f
        a, b = t, max(t, d + marge)
        if b - a > 0.12:
            garder.append((round(a, 3), round(min(b, duree), 3)))
        t = max(0.0, f - marge)
    if duree - t > 0.12:
        garder.append((round(t, 3), round(duree, 3)))
    return garder


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("-o", "--sortie")
    ap.add_argument("--seuil", type=float, default=-35)
    ap.add_argument("--silence", type=float, default=0.45)
    ap.add_argument("--marge", type=float, default=0.08)
    ap.add_argument("--zoom", type=float, default=1.0, help="1.08 : recadre une coupe sur deux de 8 %")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()

    info = sonder(a.source)
    if not info["son"]:
        raise SystemExit("pas de piste son : rien a detecter")
    garder = morceaux(silences(a.source, a.seuil, a.silence), info["duree"], a.marge)
    gagne = info["duree"] - sum(b - x for x, b in garder)
    print(f"{len(garder)} morceaux gardes, {gagne:.1f} s retirees sur {info['duree']:.1f} s")
    if a.liste or not a.sortie:
        for x, b in garder:
            print(f"  {x:8.2f} -> {b:8.2f}")
        return

    W, H = info["largeur"], info["hauteur"]
    fc, cat = [], ""
    for i, (x, b) in enumerate(garder):
        v = f"[0:v]trim={x}:{b},setpts=PTS-STARTPTS"
        if a.zoom > 1 and i % 2 == 1:
            zw, zh = int(W / a.zoom) // 2 * 2, int(H / a.zoom) // 2 * 2
            v += f",crop={zw}:{zh}:(iw-{zw})/2:(ih-{zh})*0.4,scale={W}:{H}"
        fc.append(v + f"[v{i}]")
        dur = b - x
        fc.append(f"[0:a]atrim={x}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,"
                  f"afade=t=out:st={max(0, dur - 0.03):.3f}:d=0.03[a{i}]")
        cat += f"[v{i}][a{i}]"
    fc.append(cat + f"concat=n={len(garder)}:v=1:a=1[v][a]")
    lancer([ffmpeg_bin(), "-y", "-hide_banner", "-i", a.source, "-filter_complex", ";".join(fc),
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", a.sortie])
    enregistrer_json(os.path.splitext(a.sortie)[0] + ".coupes.json",
                     {"source": a.source, "seuil_db": a.seuil, "silence_min": a.silence, "marge": a.marge,
                      "zoom": a.zoom, "gardes": [{"debut": x, "fin": b} for x, b in garder],
                      "secondes_retirees": round(gagne, 2)})
    print(f"-> {a.sortie}")


if __name__ == "__main__":
    main()
