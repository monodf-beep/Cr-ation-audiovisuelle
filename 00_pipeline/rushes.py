#!/usr/bin/env python3
"""Inventaire des rushes : lit les metadonnees des photos, videos et notes vocales d'un dossier,
les remet dans l'ordre de prise de vue et propose un squelette de plan chronologique.

    python3 00_pipeline/rushes.py DOSSIER [--sortie rushes] [--ecart 20] [--tz Europe/Paris]
                                          [--decalage "Canon EOS 250D=-00:04:30"]

Produit :
    rushes/inventaire.json   une ligne par fichier, avec la date retenue et d'ou elle vient
    rushes/plan-chrono.json  les rushes regroupes en moments, a valider avant tout montage

Sources de date, de la plus fiable a la moins fiable :
    exiftool > ffprobe / ffmpeg (videos) > EXIF via Pillow (photos) > nom du fichier > date du fichier
Aucune n'est obligatoire : le script prend la meilleure disponible.
"""

import argparse, json, os, re, shutil, subprocess, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PHOTO = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".dng", ".cr2", ".cr3", ".nef", ".arw"}
VIDEO = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".mts", ".3gp", ".webm"}
AUDIO = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".opus", ".amr", ".flac", ".caf"}

# Motifs de noms de fichiers courants. `utc` : l'horodatage du nom est en UTC (Pixel).
MOTIFS = [
    (re.compile(r"PXL_(\d{8})_(\d{6})"), "%Y%m%d%H%M%S", True),
    (re.compile(r"(?:IMG|VID|MVIMG|PANO)_(\d{8})_(\d{6})"), "%Y%m%d%H%M%S", False),
    (re.compile(r"(?:Screenshot|Capture)[_ -](\d{4}-\d{2}-\d{2})[_ -](\d{2}-\d{2}-\d{2})"), "%Y-%m-%d%H-%M-%S", False),
    (re.compile(r"(?<!\d)(\d{8})[_-](\d{6})(?!\d)"), "%Y%m%d%H%M%S", False),
    (re.compile(r"(?:IMG|VID|AUD|PTT)-(\d{8})-WA\d+"), "%Y%m%d", False),  # WhatsApp : la date seule
]


def lance(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired):
        return "", ""


def ffmpeg_bin():
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def lit_date(texte):
    """Date EXIF ou ISO -> datetime (avec fuseau si present)."""
    if not texte:
        return None
    t = str(texte).strip().replace("Z", "+00:00")
    t = re.sub(r"^(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", t)
    t = re.sub(r"(\.\d+)", "", t)
    if t.startswith("0000"):
        return None
    try:
        return datetime.fromisoformat(t.replace(" ", "T", 1))
    except ValueError:
        return None


def iso6709(texte):
    m = re.match(r"([+-]\d+\.\d+)([+-]\d+\.\d+)", texte or "")
    return [float(m.group(1)), float(m.group(2))] if m else None


# --- lecteurs --------------------------------------------------------------

def par_exiftool(chemins):
    if not shutil.which("exiftool"):
        return {}
    out, _ = lance(["exiftool", "-json", "-n", "-api", "QuickTimeUTC",
                    "-DateTimeOriginal", "-SubSecDateTimeOriginal", "-OffsetTimeOriginal",
                    "-CreateDate", "-CreationDate", "-MediaCreateDate",
                    "-GPSLatitude", "-GPSLongitude", "-Make", "-Model",
                    "-Duration", "-ImageWidth", "-ImageHeight", "-Rotation", "-Software"] + chemins)
    res = {}
    for d in json.loads(out or "[]"):
        date, champ = None, None
        for c in ("SubSecDateTimeOriginal", "DateTimeOriginal", "CreationDate", "CreateDate", "MediaCreateDate"):
            date = lit_date(d.get(c))
            if date:
                champ = c
                break
        if date and date.tzinfo is None and d.get("OffsetTimeOriginal"):
            date = lit_date(f"{date.isoformat()}{d['OffsetTimeOriginal']}") or date
        gps = [d["GPSLatitude"], d["GPSLongitude"]] if "GPSLatitude" in d and "GPSLongitude" in d else None
        res[d["SourceFile"]] = {
            "date": date, "source_date": f"exiftool:{champ}" if champ else None,
            "appareil": " ".join(x for x in (d.get("Make"), d.get("Model")) if x) or None,
            "gps": gps, "duree_s": d.get("Duration"), "logiciel": d.get("Software"),
            "largeur": d.get("ImageWidth"), "hauteur": d.get("ImageHeight"), "rotation": d.get("Rotation"),
        }
    return res


def par_ffmpeg(chemin):
    """Videos : ffprobe si present, sinon on lit l'en-tete que ffmpeg -i ecrit sur stderr."""
    tags, duree, larg, haut, rot = {}, None, None, None, None
    if shutil.which("ffprobe"):
        out, _ = lance(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", chemin])
        d = json.loads(out or "{}")
        tags = {k.lower(): v for k, v in (d.get("format", {}).get("tags") or {}).items()}
        duree = float(d["format"]["duration"]) if d.get("format", {}).get("duration") else None
        for s in d.get("streams", []):
            if s.get("codec_type") == "video":
                larg, haut = s.get("width"), s.get("height")
                rot = (s.get("tags") or {}).get("rotate")
                for sd in s.get("side_data_list", []):
                    rot = sd.get("rotation", rot)
                break
    elif ffmpeg_bin():
        _, err = lance([ffmpeg_bin(), "-hide_banner", "-i", chemin])
        for m in re.finditer(r"^\s{4}([\w.:-]+)\s*:\s(.+)$", err, re.M):
            tags.setdefault(m.group(1).lower(), m.group(2).strip())
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
        if m:
            duree = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        m = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", err)
        if m:
            larg, haut = int(m.group(1)), int(m.group(2))
        m = re.search(r"rotation of (-?[\d.]+) degrees", err)
        rot = float(m.group(1)) if m else None
    else:
        return {}
    # L'heure Apple porte le fuseau local ; creation_time est en UTC.
    date, champ = None, None
    for c in ("com.apple.quicktime.creationdate", "creation_time", "date"):
        date = lit_date(tags.get(c))
        if date:
            champ = c
            break
    appareil = " ".join(x for x in (tags.get("com.apple.quicktime.make"), tags.get("com.apple.quicktime.model")) if x)
    appareil = appareil or tags.get("com.android.manufacturer")
    gps = iso6709(tags.get("com.apple.quicktime.location.iso6709") or tags.get("location"))
    return {"date": date, "source_date": f"video:{champ}" if champ else None, "appareil": appareil or None,
            "gps": gps, "duree_s": duree, "largeur": larg, "hauteur": haut, "rotation": rot}


def par_pillow(chemin):
    try:
        from PIL import Image
    except ImportError:
        return {}
    try:
        with Image.open(chemin) as im:
            exif = im.getexif()
            larg, haut = im.size
            sub = exif.get_ifd(0x8769)
            gps_ifd = exif.get_ifd(0x8825)
    except Exception:
        return {}
    date = lit_date(sub.get(36867) or exif.get(306))
    if date and sub.get(36881):
        date = lit_date(f"{date.isoformat()}{sub[36881]}") or date
    gps = None
    if gps_ifd.get(2) and gps_ifd.get(4):
        dms = lambda v: float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat, lon = dms(gps_ifd[2]), dms(gps_ifd[4])
        gps = [lat if gps_ifd.get(1, "N") == "N" else -lat, lon if gps_ifd.get(3, "E") == "E" else -lon]
    appareil = " ".join(str(x).strip("\x00 ") for x in (exif.get(271), exif.get(272)) if x) or None
    return {"date": date, "source_date": "exif" if date else None, "appareil": appareil, "gps": gps,
            "largeur": larg, "hauteur": haut, "logiciel": exif.get(305)}


def par_nom(nom):
    for motif, fmt, utc in MOTIFS:
        m = motif.search(nom)
        if m:
            try:
                d = datetime.strptime("".join(m.groups()), fmt)
            except ValueError:
                continue
            if utc:
                d = d.replace(tzinfo=timezone.utc)
            return d, ("nom:date-seule" if fmt == "%Y%m%d" else "nom")
    return None, None


# --- assemblage -----------------------------------------------------------

def fiabilite(source, date):
    if not source or source.startswith("fichier"):
        return "basse"
    if source == "nom:date-seule":
        return "basse"
    if source == "nom":
        return "moyenne"
    return "haute" if date and date.tzinfo else "moyenne"


def transcription(chemin):
    """Texte d'une note vocale, s'il a ete produit par notes.py (fichier voisin .txt)."""
    for t in (chemin + ".txt", os.path.splitext(chemin)[0] + ".txt"):
        if os.path.exists(t):
            with open(t, encoding="utf-8") as f:
                return f.read().strip()
    return None


def decalages(liste):
    """'Canon EOS 250D=-00:04:30' -> {'Canon EOS 250D': timedelta(-270 s)}"""
    res = {}
    for d in liste or []:
        appareil, _, val = d.rpartition("=")
        signe = -1 if val.startswith("-") else 1
        h, m, s = (int(x) for x in val.lstrip("+-").split(":"))
        res[appareil.strip()] = signe * timedelta(hours=h, minutes=m, seconds=s)
    return res


def inventaire(dossier, tz, decal):
    chemins = []
    for racine, _, fichiers in os.walk(dossier):
        for f in sorted(fichiers):
            ext = os.path.splitext(f)[1].lower()
            if ext in PHOTO | VIDEO | AUDIO and not f.startswith("."):
                chemins.append(os.path.join(racine, f))
    exif = par_exiftool(chemins)
    rushes = []
    for c in chemins:
        ext = os.path.splitext(c)[1].lower()
        nature = "video" if ext in VIDEO else "audio" if ext in AUDIO else "photo"
        info = exif.get(c) or {}
        if not info.get("date"):
            info = {**(par_pillow(c) if nature == "photo" else par_ffmpeg(c)), **{k: v for k, v in info.items() if v}}
        if not info.get("date"):
            d, src = par_nom(os.path.basename(c))
            if d:
                info["date"], info["source_date"] = d, src
        if not info.get("date"):
            info["date"] = datetime.fromtimestamp(os.path.getmtime(c))
            info["source_date"] = "fichier:mtime"
        date = info["date"]
        # Tout est ramene a l'heure locale du tournage.
        date = date.astimezone(tz) if date.tzinfo else date.replace(tzinfo=tz)
        corr = next((v for k, v in decal.items() if k.lower() in (info.get("appareil") or "").lower()), None)
        if corr:
            date += corr
        rushes.append({
            "fichier": os.path.relpath(c, dossier),
            "nature": nature,
            "date": date.isoformat(timespec="seconds"),
            "source_date": info["source_date"] + (" +decalage" if corr else ""),
            "fiabilite": fiabilite(info["source_date"], info["date"]),
            "appareil": info.get("appareil"),
            "gps": [round(x, 5) for x in info["gps"]] if info.get("gps") else None,
            "duree_s": round(float(info["duree_s"]), 2) if info.get("duree_s") else None,
            "format": f"{info['largeur']}x{info['hauteur']}" if info.get("largeur") else None,
            "rotation": info.get("rotation"),
            "taille_octets": os.path.getsize(c),
            "transcription": transcription(c) if nature == "audio" else None,
            "_t": date,
        })
    rushes.sort(key=lambda r: (r["_t"], r["fichier"]))
    return rushes


def avertissements(rushes):
    av = []
    basses = [r["fichier"] for r in rushes if r["fiabilite"] == "basse"]
    if basses:
        av.append(f"{len(basses)} rush(es) sans heure de prise de vue fiable, laisses hors chronologie "
                  "(voir a_placer) : " + ", ".join(basses[:8]) + (" ..." if len(basses) > 8 else ""))
    wa = [r["fichier"] for r in rushes if "-WA" in r["fichier"]]
    muettes = [r["fichier"] for r in rushes if r["nature"] == "audio" and not r["transcription"]]
    if muettes:
        av.append(f"{len(muettes)} note(s) vocale(s) pas encore transcrite(s) : lancer 00_pipeline/notes.py.")
    if wa:
        av.append(f"{len(wa)} fichier(s) passes par WhatsApp : metadonnees effacees, demander les originaux.")
    appareils = sorted({r["appareil"] for r in rushes if r["appareil"]})
    if len(appareils) > 1:
        av.append("Plusieurs appareils (" + ", ".join(appareils) + ") : verifier que leurs horloges concordent "
                  "(filmer une meme horloge avec chacun, puis --decalage).")
    vus = {}
    for r in rushes:
        cle = (r["date"], r["taille_octets"])
        if cle in vus:
            av.append(f"Doublon probable : {r['fichier']} = {vus[cle]}")
        vus[cle] = r["fichier"]
    return av


def moments(rushes, ecart_min):
    groupes = []
    for r in rushes:
        if not groupes or r["_t"] - groupes[-1][-1]["_t"] > timedelta(minutes=ecart_min):
            groupes.append([])
        groupes[-1].append(r)
    return [{
        "id": f"M{i}",
        "debut": g[0]["date"], "fin": g[-1]["date"],
        "titre": "", "description": "",
        "rushes": [r["fichier"] for r in g],
        "duree_videos_s": round(sum(r["duree_s"] or 0 for r in g if r["nature"] == "video"), 1),
        "notes_vocales": [{"fichier": r["fichier"], "heure": r["date"][11:16], "transcription": r["transcription"]}
                          for r in g if r["nature"] == "audio"],
    } for i, g in enumerate(groupes, 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--sortie", default="rushes")
    ap.add_argument("--ecart", type=float, default=20, help="minutes sans prise de vue qui ouvrent un nouveau moment")
    ap.add_argument("--tz", default="Europe/Paris")
    ap.add_argument("--decalage", action="append", help='"Appareil=+HH:MM:SS" : corrige une horloge en avance ou en retard')
    a = ap.parse_args()

    rushes = inventaire(a.dossier, ZoneInfo(a.tz), decalages(a.decalage))
    if not rushes:
        sys.exit(f"Aucune photo ni video dans {a.dossier}")
    av = avertissements(rushes)
    plan = {
        "ordre": "chronologique",
        "note": "Proposition tiree des metadonnees. A valider (ou a reordonner) avant tout montage.",
        "titre": "", "accroche": "", "angle": "",
        "moments": moments([r for r in rushes if r["fiabilite"] != "basse"], a.ecart),
        "a_placer": [{"fichier": r["fichier"], "indice": r["date"], "source_date": r["source_date"]}
                     for r in rushes if r["fiabilite"] == "basse"],
        "avertissements": av,
    }
    os.makedirs(a.sortie, exist_ok=True)
    for r in rushes:
        r.pop("_t")
    with open(os.path.join(a.sortie, "inventaire.json"), "w") as f:
        json.dump(rushes, f, ensure_ascii=False, indent=2)
    with open(os.path.join(a.sortie, "plan-chrono.json"), "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    for m in plan["moments"]:
        print(f"\n{m['id']}  {m['debut'][:16].replace('T', ' ')} -> {m['fin'][11:16]}  ({len(m['rushes'])} rushes)")
        for fic in m["rushes"]:
            r = next(x for x in rushes if x["fichier"] == fic)
            duree = f"{r['duree_s']:.1f}s" if r["duree_s"] else ""
            print(f"   {r['date'][11:19]}  {r['nature']:5} {duree:>7}  [{r['fiabilite']:7}] {fic}")
            if r["transcription"]:
                print(f"      « {r['transcription'][:110]}{'…' if len(r['transcription']) > 110 else ''} »")
    for r in plan["a_placer"]:
        print(f"\n?  a placer : {r['fichier']}  (indice : {r['indice'][:10]}, {r['source_date']})")
    for x in av:
        print(f"\n! {x}")
    print(f"\n-> {a.sortie}/inventaire.json, {a.sortie}/plan-chrono.json")


if __name__ == "__main__":
    main()
