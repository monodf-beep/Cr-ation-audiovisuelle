#!/usr/bin/env python3
"""Prépare les vidéos téléchargées pour l'analyse par les agents.

Pour chaque .mp4 de donnees/<compte>/ :
  - transcriptions/<nom>.txt   texte parlé (faster-whisper, langue auto-détectée)
  - planches/<nom>.jpg         planche 4x3 des changements de plan + image d'accroche

Pour chaque publication à plusieurs images (carrousel) :
  - planches/<shortcode>.jpg   toutes les slides côte à côte

Idempotent : ce qui existe déjà n'est pas refait.

Usage : python3 traiter.py donnees/<compte> [--modele small]
Prérequis : ffmpeg, pip install faster-whisper pillow
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def planche_video(video: Path, sortie: Path) -> None:
    """12 images réparties sur toute la durée (la 1re ≈ l'accroche) + rythme de montage."""
    if sortie.exists():
        return
    d = duree(video)
    if d <= 0:
        print(f"   illisible, ignorée : {video.name}")
        return
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(video),
         "-vf", f"fps=12/{d:.3f},scale=270:-2,tile=4x3:padding=4:color=white",
         "-frames:v", "1", str(sortie)],
        check=False,
    )
    # Nombre de coupes franches : c'est le rythme de montage du reel.
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video), "-an",
         "-vf", "select='gt(scene,0.3)',metadata=print", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    coupes = r.stderr.count("lavfi.scene_score")
    sortie.with_suffix(".json").write_text(json.dumps({
        "duree_s": round(d, 1),
        "coupes": coupes,
        "secondes_par_plan": round(d / (coupes + 1), 1),
    }))


def duree(video: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def transcrire(video: Path, sortie: Path, modele) -> None:
    if sortie.exists():
        return
    segments, info = modele.transcribe(str(video), vad_filter=True)
    lignes = [f"[{s.start:05.1f}s] {s.text.strip()}" for s in segments]
    entete = f"# langue={info.language} duree={duree(video):.1f}s\n"
    sortie.write_text(entete + "\n".join(lignes) + "\n", encoding="utf-8")


def planche_carrousel(images: list[Path], sortie: Path) -> None:
    from PIL import Image

    if sortie.exists() or len(images) < 2:
        return
    vignettes = []
    for p in sorted(images):
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        im.thumbnail((360, 450))
        vignettes.append(im)
    if not vignettes:
        return
    colonnes = min(5, len(vignettes))
    lignes = -(-len(vignettes) // colonnes)
    w, h = 360, 450
    feuille = Image.new("RGB", (colonnes * (w + 4), lignes * (h + 4)), "white")
    for i, im in enumerate(vignettes):
        feuille.paste(im, ((i % colonnes) * (w + 4), (i // colonnes) * (h + 4)))
    feuille.save(sortie, quality=85)


def cle_publication(p: Path) -> str:
    """Regroupe les slides d'un carrousel : on retire le suffixe _1, _2…"""
    return re.sub(r"_\d+$", "", p.stem)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", type=Path)
    ap.add_argument("--modele", default="small",
                    help="tiny/base/small/medium/large-v3 (small = bon compromis CPU)")
    ap.add_argument("--sans-transcription", action="store_true")
    a = ap.parse_args()

    d: Path = a.dossier
    if not d.is_dir():
        sys.exit(f"Dossier introuvable : {d}")
    (d / "planches").mkdir(exist_ok=True)
    (d / "transcriptions").mkdir(exist_ok=True)

    medias = [p for p in d.rglob("*") if p.parent.name not in ("planches", "transcriptions")]
    videos = sorted(p for p in medias if p.suffix.lower() == ".mp4")
    images = [p for p in medias if p.suffix.lower() in IMAGES]

    modele = None
    if videos and not a.sans_transcription:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            sys.exit("pip install faster-whisper  (ou relancer avec --sans-transcription)")
        modele = WhisperModel(a.modele, device="auto", compute_type="int8")

    for i, v in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {v.name}")
        planche_video(v, d / "planches" / f"{v.stem}.jpg")
        if modele:
            transcrire(v, d / "transcriptions" / f"{v.stem}.txt", modele)

    groupes = defaultdict(list)
    for p in images:
        groupes[cle_publication(p)].append(p)
    for cle, imgs in groupes.items():
        planche_carrousel(imgs, d / "planches" / f"{cle}.jpg")

    print(f"OK : {len(videos)} vidéos, {sum(len(g) > 1 for g in groupes.values())} carrousels.")


if __name__ == "__main__":
    main()
