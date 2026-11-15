#!/usr/bin/env python3
"""Transforme un dossier de compte téléchargé en tableau exploitable par l'agent « veilleur ».

Lit les métadonnées gallery-dl (*.json à côté des médias), et si présents les compteurs
yt-dlp (stats/*.info.json), les transcriptions et planches produites par traiter.py.

Sorties dans donnees/<compte>/ :
  index.csv   une ligne par publication, triée par score décroissant
  resume.md   chiffres clés du compte + top 10 / flop 5

score = interactions / médiane des interactions du compte
        (interactions = likes + 3 x commentaires ; on compare un compte à lui-même)

Usage : python3 indexer.py donnees/<compte>
"""
import csv
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

NOM = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)_(\d+)\.[^.]+\.json$")


def charger(d: Path) -> list[dict]:
    pubs: dict[str, dict] = {}
    for meta in sorted(d.glob("*.json")):
        m = NOM.match(meta.name)
        if not m:
            continue
        date, sc, _ = m.groups()
        try:
            j = json.loads(meta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        media = meta.name[: -len(".json")]
        p = pubs.setdefault(sc, {
            "shortcode": sc,
            "date": date,
            "type": j.get("type") or "post",
            "slides": j.get("count") or 1,
            "likes": j.get("likes") or 0,
            "commentaires": "",
            "vues": "",
            "duree_s": "",
            "epingle": bool(j.get("pinned")),
            "lieu": j.get("location_name") or "",
            "coauteurs": ",".join(c.get("username") or "" for c in j.get("coauthors") or []),
            "hashtags": " ".join("#" + t for t in j.get("tags") or []),
            "legende": (j.get("description") or "").strip(),
            "videos": 0,
            "medias": [],
        })
        p["medias"].append(media)
        if media.endswith(".mp4"):
            p["videos"] += 1

    for sc, p in pubs.items():
        if p["type"] == "post" and p["slides"] > 1:
            p["format"] = "carrousel"
        elif p["videos"]:
            p["format"] = "reel"
        else:
            p["format"] = "photo"

        stats = d / "stats" / f"{sc}.info.json"
        if stats.exists():
            try:
                s = json.loads(stats.read_text(encoding="utf-8"))
                p["commentaires"] = s.get("comment_count") or ""
                p["vues"] = s.get("view_count") or ""
                if s.get("duration"):
                    p["duree_s"] = round(s["duration"], 1)
                if s.get("like_count"):
                    p["likes"] = s["like_count"]
            except (json.JSONDecodeError, OSError):
                pass

        tr = sorted((d / "transcriptions").glob(f"*_{sc}_*.txt"))
        p["transcription"] = tr[0].name if tr else ""
        if tr and not p["duree_s"]:
            m = re.search(r"duree=([\d.]+)s", tr[0].read_text(encoding="utf-8")[:200])
            p["duree_s"] = float(m.group(1)) if m else ""
        pl = sorted((d / "planches").glob(f"{p['date']}_{sc}*.jpg"))
        p["planche"] = pl[0].name if pl else ""
        p["secondes_par_plan"] = ""
        rythme = sorted((d / "planches").glob(f"{p['date']}_{sc}*.json"))
        if rythme:
            r = json.loads(rythme[0].read_text())
            p["secondes_par_plan"] = r.get("secondes_par_plan", "")
            p["duree_s"] = p["duree_s"] or r.get("duree_s", "")
        p["url"] = f"https://www.instagram.com/{'reel' if p['format'] == 'reel' else 'p'}/{sc}/"
        p["mots_legende"] = len(p["legende"].split())
        p["accroche"] = p["legende"].split("\n")[0][:140]

    return list(pubs.values())


def scorer(pubs: list[dict]) -> None:
    def inter(p):
        c = p["commentaires"] if isinstance(p["commentaires"], int) else 0
        return p["likes"] + 3 * c

    valeurs = [inter(p) for p in pubs if not p["epingle"]] or [inter(p) for p in pubs]
    med = statistics.median(valeurs) if valeurs else 0
    for p in pubs:
        p["interactions"] = inter(p)
        p["score"] = round(inter(p) / med, 2) if med else 0


def resume(pubs: list[dict], compte: str) -> str:
    dates = sorted(datetime.fromisoformat(p["date"]) for p in pubs)
    semaines = max(1, (dates[-1] - dates[0]).days / 7) if len(dates) > 1 else 1
    formats = Counter(p["format"] for p in pubs)
    tri = sorted(pubs, key=lambda p: p["score"], reverse=True)

    def moyenne_score(fmt):
        s = [p["score"] for p in pubs if p["format"] == fmt]
        return f"{statistics.mean(s):.2f}" if s else "-"

    tags = Counter(t for p in pubs for t in p["hashtags"].split())
    lignes = [
        f"# @{compte}",
        "",
        f"- {len(pubs)} publications du {dates[0]:%d/%m/%Y} au {dates[-1]:%d/%m/%Y}"
        f" — {len(pubs) / semaines:.1f} par semaine",
        "- Formats : " + ", ".join(
            f"{f} {n} (score moyen {moyenne_score(f)})" for f, n in formats.most_common()),
        f"- Légende médiane : {statistics.median(p['mots_legende'] for p in pubs):.0f} mots",
        "- Hashtags fréquents : " + (" ".join(t for t, _ in tags.most_common(10)) or "aucun"),
    ]
    if len(pubs) < 20:
        lignes.append(f"- ⚠ Seulement {len(pubs)} publications : conclusions fragiles.")
    if not any(p["commentaires"] != "" for p in pubs):
        lignes.append("- Commentaires et vues absents (lancer ./stats.sh pour les ajouter).")

    def bloc(titre, sel):
        out = ["", f"## {titre}", "", "| score | date | format | likes | com. | accroche |", "|---|---|---|---|---|---|"]
        for p in sel:
            acc = p["accroche"].replace("|", "/") or "(sans légende)"
            out.append(f"| {p['score']} | [{p['date']}]({p['url']}) | {p['format']} | {p['likes']} "
                       f"| {p['commentaires']} | {acc} |")
        return out

    lignes += bloc("Top 10", tri[:10])
    lignes += bloc("Flop 5", tri[-5:][::-1] if len(tri) > 10 else [])
    return "\n".join(lignes) + "\n"


COLONNES = ["score", "date", "format", "slides", "duree_s", "secondes_par_plan", "likes", "commentaires", "vues",
            "interactions", "epingle", "accroche", "mots_legende", "hashtags", "lieu",
            "coauteurs", "url", "shortcode", "transcription", "planche", "legende"]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    d = Path(sys.argv[1])
    pubs = charger(d)
    if not pubs:
        sys.exit(f"Aucune métadonnée gallery-dl trouvée dans {d}")
    scorer(pubs)
    pubs.sort(key=lambda p: p["score"], reverse=True)
    with open(d / "index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES, extrasaction="ignore")
        w.writeheader()
        w.writerows(pubs)
    (d / "resume.md").write_text(resume(pubs, d.name), encoding="utf-8")
    print(f"{len(pubs)} publications indexées → {d / 'index.csv'}, {d / 'resume.md'}")


if __name__ == "__main__":
    main()
