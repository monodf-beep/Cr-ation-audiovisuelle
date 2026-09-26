"""Installe les sons candidats de la bibliotheque sur le VPS (appele par ops/vps/synchro.sh ; rapide si tout est la).
Pour chaque son de catalogue.json absent de fichiers/sons/ : telechargement a la source, puis mp3 normalise
(effets : -16 LUFS ; musiques : -20 LUFS, 90 s au plus avec fondu de sortie ; ambiances : 60 s au plus).
Cree aussi donnees/etat.json au premier passage, avec les choix deja faits (04_montage/bibliotheque.json).
Usage : python3 bibliotheque/installer-sons.py"""
import json, os, subprocess, tempfile, urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
SONS = os.path.join(ICI, "fichiers", "sons")
ETAT = os.path.join(ICI, "donnees", "etat.json")
os.makedirs(SONS, exist_ok=True)
os.makedirs(os.path.dirname(ETAT), exist_ok=True)

nouveaux = 0
for s in json.load(open(os.path.join(ICI, "catalogue.json")))["sons"]:
    sortie = os.path.join(SONS, s["id"] + ".mp3")
    if os.path.exists(sortie): continue
    with tempfile.TemporaryDirectory() as tmp:
        brut = os.path.join(tmp, "source" + os.path.splitext(s["fichier_source"])[1])
        try:
            req = urllib.request.Request(s["fichier_source"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(brut, "wb") as f: f.write(r.read())
        except Exception as e:
            print(f"telechargement impossible : {s['id']} ({e})"); continue
        if s["type"] == "musique":
            filtre, debit = "atrim=0:90,loudnorm=I=-20:TP=-2,afade=t=out:st=88:d=2", "160k"
        elif s["duree"] > 20:
            filtre, debit = "atrim=0:60,loudnorm=I=-16:TP=-2,afade=t=out:st=58:d=2", "128k"
        else:
            filtre, debit = "loudnorm=I=-16:TP=-2", "128k"
        ok = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brut, "-af", filtre, "-ar", "48000", "-b:a", debit, sortie + ".tmp.mp3"]).returncode == 0
        if ok: os.replace(sortie + ".tmp.mp3", sortie); nouveaux += 1
        else: print(f"conversion impossible : {s['id']}")

if not os.path.exists(ETAT):
    choix = {}
    try:
        b = json.load(open(os.path.join(ICI, "..", "04_montage", "bibliotheque.json")))
        for cle in ("sons", "musiques", "effets_graphiques"):
            for x in b.get(cle, []): choix[x["id"]] = "garde"
    except Exception: pass
    json.dump({"choix": choix, "televerses": []}, open(ETAT, "w"), ensure_ascii=False, indent=1)
if nouveaux: print(f"bibliotheque : {nouveaux} son(s) installe(s)")
