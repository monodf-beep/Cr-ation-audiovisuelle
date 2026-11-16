#!/usr/bin/env python3
"""Convertit un dataset du scraper Instagram d'Apify (apify/instagram-scraper)
au format de la chaîne de veille (le même que gallery-dl), puis télécharge les médias.

Pour chaque publication, dans donnees/<compte>/ :
  AAAA-MM-JJ_<shortcode>_NN.<ext>        le média (image, ou vidéo pour les reels)
  AAAA-MM-JJ_<shortcode>_NN.<ext>.json   métadonnées lues par indexer.py
  stats/<shortcode>.info.json            commentaires, vues, durée (comme stats.sh)

Ensuite : python traiter.py donnees/<compte> ; python indexer.py donnees/<compte>

Usage : python apify_import.py dataset.json [--sans-medias]
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent / "donnees"


def ext_de(url: str, defaut: str) -> str:
    m = re.search(r"\.(jpg|jpeg|png|webp|heic|mp4)(?:\?|$)", url or "", re.I)
    return (m.group(1).lower() if m else defaut).replace("jpeg", "jpg")


def telecharger(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
        time.sleep(0.3)
        return True
    except Exception as e:  # média expiré ou refusé : on garde les métadonnées
        print(f"   média non récupéré ({dest.name}) : {e}")
        return False


def medias(p: dict) -> list[tuple[str, str]]:
    """Liste (url, extension) dans l'ordre des slides."""
    t = p.get("type")
    if t == "Sidecar" and p.get("childPosts"):
        out = []
        for c in p["childPosts"]:
            if c.get("type") == "Video" and c.get("videoUrl"):
                out.append((c["videoUrl"], "mp4"))
            elif c.get("displayUrl"):
                out.append((c["displayUrl"], ext_de(c["displayUrl"], "jpg")))
        return out
    if t == "Sidecar" and p.get("images"):
        return [(u, ext_de(u, "jpg")) for u in p["images"]]
    if t == "Video" and p.get("videoUrl"):
        return [(p["videoUrl"], "mp4")]
    if p.get("displayUrl"):
        return [(p["displayUrl"], ext_de(p["displayUrl"], "jpg"))]
    return []


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    avec_medias = "--sans-medias" not in sys.argv
    par_compte: dict[str, int] = {}
    for p in items:
        if p.get("error") or not p.get("shortCode"):
            print("   ignoré :", p.get("error") or p.get("url"))
            continue
        # le compte visé (inputUrl), pas l'auteur : une collaboration apparaît dans la grille du compte visé
        m = re.search(r"instagram\.com/([^/?#]+)", p.get("inputUrl") or "")
        compte = m.group(1) if m else (p.get("ownerUsername") or "inconnu")
        sc = p["shortCode"]
        date = (p.get("timestamp") or "")[:10] or "0000-00-00"
        d = RACINE / compte
        (d / "stats").mkdir(parents=True, exist_ok=True)
        ms = medias(p) or [("", "jpg")]
        sidecar = p.get("type") == "Sidecar"
        meta = {
            "post_shortcode": sc,
            "likes": p.get("likesCount") if (p.get("likesCount") or 0) >= 0 else None,
            "description": p.get("caption") or "",
            "tags": p.get("hashtags") or [],
            "count": len(ms),
            "type": "reel" if (p.get("type") == "Video" and not sidecar) else "post",
            "pinned": bool(p.get("isPinned")),
            "location_name": p.get("locationName") or "",
            "coauthors": [{"username": c.get("username")} for c in (p.get("coauthorProducers") or [])],
            "source": "apify",
            "url": p.get("url"),
        }
        for i, (url, ext) in enumerate(ms, 1):
            nom = f"{date}_{sc}_{i:02d}.{ext}"
            (d / f"{nom}.json").write_text(json.dumps({**meta, "num": i}, ensure_ascii=False), encoding="utf-8")
            if avec_medias and url:
                telecharger(url, d / nom)
        stats = {
            "comment_count": p.get("commentsCount") if (p.get("commentsCount") or 0) >= 0 else None,
            "view_count": p.get("videoPlayCount") or p.get("videoViewCount"),
            "like_count": p.get("likesCount") if (p.get("likesCount") or 0) >= 0 else None,
            "duration": p.get("videoDuration"),
        }
        (d / "stats" / f"{sc}.info.json").write_text(json.dumps(stats), encoding="utf-8")
        par_compte[compte] = par_compte.get(compte, 0) + 1
    for c, n in sorted(par_compte.items()):
        print(f"{c} : {n} publications")


if __name__ == "__main__":
    main()
