#!/usr/bin/env python3
"""Démonte un reel en données de montage, puis supprime la vidéo.

    python3 analyse_reel.py URL [URL ...] [--out DOSSIER] [--seuil 0.3]

Pour chaque URL, produit dans DOSSIER/<id>/ :
  analyse.json   métadonnées, transcription horodatée, plans (coupes), rythme
  planche.jpg    une vignette par plan + une toutes les --pas secondes,
                 pour lire textes à l'écran, cadrages, zooms et B-roll

La vidéo et l'audio sont téléchargés dans un dossier temporaire supprimé
à la fin de chaque reel, même en cas d'erreur. Rien d'autre ne reste
sur le disque que analyse.json et planche.jpg.
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from PIL import Image, ImageDraw

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
_whisper = None


def telecharger(url, dossier, cookies=None):
    opts = {"outtmpl": str(dossier / "v.%(ext)s"), "quiet": True,
            "no_warnings": True, "noprogress": True,
            "format": "best[ext=mp4]/best"}
    if cookies:
        opts["cookiefile"] = str(cookies)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    video = next(dossier.glob("v.*"))
    meta = {k: info.get(k) for k in (
        "id", "uploader", "uploader_id", "channel", "title", "description",
        "timestamp", "duration", "view_count", "like_count", "comment_count")}
    meta["url"] = url
    return video, meta


def duree(video):
    err = subprocess.run([FFMPEG, "-i", str(video)], capture_output=True,
                         text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def coupes(video, seuil):
    """Instants des changements de plan (détection de scène ffmpeg)."""
    err = subprocess.run(
        [FFMPEG, "-i", str(video), "-an", "-vf",
         f"select='gt(scene,{seuil})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", err)]


def transcrire(video, dossier):
    global _whisper
    wav = dossier / "a.wav"
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", str(video),
                    "-ac", "1", "-ar", "16000", str(wav)], check=True)
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel("small", device="cpu", compute_type="int8")
    segs, info = _whisper.transcribe(str(wav), word_timestamps=True)
    lignes, mots = [], 0
    for s in segs:
        lignes.append({"debut": round(s.start, 2), "fin": round(s.end, 2),
                       "texte": s.text.strip()})
        mots += len(s.words or [])
    return lignes, mots, info.language


def instants(plans, total, pas):
    """Milieu de chaque plan + un instant tous les `pas` secondes.

    Un face caméra sans coupe reste un seul plan : l'échantillonnage régulier
    attrape quand même les textes incrustés, zooms et inserts qui changent.
    """
    ts = {round((p["debut"] + p["fin"]) / 2, 1): i + 1
          for i, p in enumerate(plans)}
    t = pas / 2
    while t < total:
        num = next(i + 1 for i, p in enumerate(plans) if t < p["fin"])
        ts.setdefault(round(t, 1), num)
        t += pas
    return sorted(ts.items())


def planche(video, ts, sortie):
    """Vignettes horodatées et numérotées par plan, en grille."""
    vignettes = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (t, num) in enumerate(ts):
            img = Path(tmp) / f"{i}.jpg"
            subprocess.run([FFMPEG, "-loglevel", "error", "-ss", f"{t:.2f}",
                            "-i", str(video), "-frames:v", "1",
                            "-vf", "scale=240:-2", str(img)], check=True)
            if img.exists():
                vignettes.append((t, num, Image.open(img).copy()))
    if not vignettes:
        return
    w, h = vignettes[0][2].size
    cols = min(8, len(vignettes))
    rows = -(-len(vignettes) // cols)
    grille = Image.new("RGB", (cols * w, rows * (h + 22)), "white")
    d = ImageDraw.Draw(grille)
    for k, (t, num, im) in enumerate(vignettes):
        x, y = (k % cols) * w, (k // cols) * (h + 22)
        grille.paste(im, (x, y + 22))
        d.text((x + 4, y + 4), f"{t:.1f}s  plan {num}", fill="black")
    grille.save(sortie, quality=80)


def analyser(url, out, seuil, pas, cookies):
    with tempfile.TemporaryDirectory(prefix="reel_") as tmp:
        tmp = Path(tmp)
        video, meta = telecharger(url, tmp, cookies)
        total = duree(video)
        bornes = [0.0] + coupes(video, seuil) + [round(total, 2)]
        plans = [{"debut": a, "fin": b, "duree": round(b - a, 2)}
                 for a, b in zip(bornes, bornes[1:]) if b - a > 0.05]
        lignes, mots, langue = transcrire(video, tmp)
        for p in plans:
            p["texte"] = " ".join(
                l["texte"] for l in lignes
                if l["debut"] < p["fin"] and l["fin"] > p["debut"])
        dossier = out / (meta["id"] or "reel")
        dossier.mkdir(parents=True, exist_ok=True)
        planche(video, instants(plans, total, pas), dossier / "planche.jpg")
        durees = [p["duree"] for p in plans]
        analyse = {
            "meta": meta,
            "langue": langue,
            "duree": round(total, 2),
            "rythme": {
                "nb_plans": len(plans),
                "plan_moyen_s": round(statistics.mean(durees), 2),
                "plan_median_s": round(statistics.median(durees), 2),
                "premiere_coupe_s": plans[0]["fin"],
                "mots_par_s": round(mots / total, 2) if total else None,
            },
            "plans": plans,
            "transcription": lignes,
        }
        (dossier / "analyse.json").write_text(
            json.dumps(analyse, ensure_ascii=False, indent=2))
    # Le dossier temporaire (vidéo + audio) est supprimé ici.
    return dossier


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--out", default="reels_analyses", type=Path)
    ap.add_argument("--seuil", default=0.3, type=float,
                    help="sensibilité de détection des coupes (0.2-0.4)")
    ap.add_argument("--pas", default=2.0, type=float,
                    help="une vignette toutes les N secondes en plus des coupes")
    ap.add_argument("--cookies", type=Path,
                    help="cookies.txt (format Netscape) si Instagram bloque")
    a = ap.parse_args()
    echecs = 0
    for url in a.urls:
        try:
            print(f"ok  {analyser(url, a.out, a.seuil, a.pas, a.cookies)}")
        except Exception as e:  # un reel bloqué ne doit pas arrêter le lot
            echecs += 1
            print(f"ERR {url} : {e}", file=sys.stderr)
    sys.exit(1 if echecs == len(a.urls) else 0)


if __name__ == "__main__":
    main()
