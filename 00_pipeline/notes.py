#!/usr/bin/env python3
"""Transcrit les notes vocales d'un dossier de rushes, sur l'ordinateur, sans rien envoyer en ligne.

    pip install faster-whisper
    python3 00_pipeline/notes.py DOSSIER [--modele small] [--langue fr] [--refaire]
                                        [--mots "Terra Madre, Slow Food, piémontais, tomme"]

Pour chaque note (m4a, mp3, wav, opus...), ecrit a cote :
    <note>.txt   le texte, lu par l'atelier et par rushes.py
    <note>.json  le texte par segments horodates, pour retrouver une phrase dans l'audio
Puis un carnet de bord, DOSSIER/carnet-de-bord.md : toutes les notes dans l'ordre ou elles ont ete dites.

Une note deja transcrite n'est pas refaite (sauf --refaire), et un .txt corrige a la main est conserve.
"""

import argparse, json, os, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rushes import AUDIO, inventaire  # noqa: E402


def transcrire(modele, chemin, langue, mots):
    # Les noms propres du lieu, donnes d'avance, sont bien mieux reconnus.
    amorce = f"Vocabulaire : {mots}." if mots else None
    segments, info = modele.transcribe(chemin, language=langue, vad_filter=True, beam_size=5, initial_prompt=amorce)
    segs = [{"debut": round(s.start, 1), "fin": round(s.end, 1), "texte": s.text.strip()} for s in segments]
    return " ".join(s["texte"] for s in segs).strip(), segs, info.language


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier")
    ap.add_argument("--modele", default="small", help="tiny, base, small, medium, large-v3 (plus gros = plus juste, plus lent)")
    ap.add_argument("--langue", default=None, help="fr, it... ; laisser vide pour la detection automatique")
    ap.add_argument("--refaire", action="store_true", help="retranscrire meme les notes deja transcrites")
    ap.add_argument("--mots", default="", help="noms propres et termes du lieu, separes par des virgules")
    ap.add_argument("--tz", default="Europe/Paris")
    a = ap.parse_args()

    notes = []
    for racine, _, fichiers in os.walk(a.dossier):
        for f in sorted(fichiers):
            if os.path.splitext(f)[1].lower() in AUDIO and not f.startswith("."):
                notes.append(os.path.join(racine, f))
    if not notes:
        sys.exit(f"Aucune note vocale dans {a.dossier}")

    a_faire = [n for n in notes if a.refaire or not os.path.exists(n + ".txt")]
    if a_faire:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            sys.exit("Installer d'abord le moteur de transcription : pip install faster-whisper")
        print(f"Chargement du modele {a.modele}…")
        modele = WhisperModel(a.modele, device="auto", compute_type="int8")
        for i, n in enumerate(a_faire, 1):
            print(f"[{i}/{len(a_faire)}] {os.path.relpath(n, a.dossier)}")
            texte, segs, langue = transcrire(modele, n, a.langue, a.mots)
            with open(n + ".txt", "w", encoding="utf-8") as f:
                f.write(texte + "\n")
            with open(n + ".json", "w", encoding="utf-8") as f:
                json.dump({"langue": langue, "modele": a.modele, "segments": segs}, f, ensure_ascii=False, indent=2)
            print(f"   « {texte[:120]}{'…' if len(texte) > 120 else ''} »")

    # Carnet de bord : les notes dans l'ordre ou elles ont ete dites, avec leur heure.
    rushes = [r for r in inventaire(a.dossier, ZoneInfo(a.tz), {}) if r["nature"] == "audio"]
    lignes = ["# Carnet de bord", "",
              "Notes vocales prises sur le moment, dans l'ordre. C'est du ressenti : les faits qu'elles citent",
              "(noms, chiffres, dates) sont a verifier avant d'entrer dans un script.", ""]
    jour = None
    for r in rushes:
        if r["date"][:10] != jour:
            jour = r["date"][:10]
            lignes += [f"## {jour}", ""]
        heure = r["date"][11:16] if r["fiabilite"] != "basse" else "heure inconnue"
        duree = f", {int(r['duree_s'] // 60)} min {int(r['duree_s'] % 60):02d}" if r["duree_s"] else ""
        lignes += [f"### {heure} · `{r['fichier']}`{duree}", "", (r["transcription"] or "*(pas encore transcrite)*"), ""]
    carnet = os.path.join(a.dossier, "carnet-de-bord.md")
    with open(carnet, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))
    print(f"\n-> {carnet}")


if __name__ == "__main__":
    main()
