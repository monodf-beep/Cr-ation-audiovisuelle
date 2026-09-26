"""Habillage sonore du montage -> assets/effets.mp3 (une piste, meme duree que la video).
Sons de la bibliotheque validee (04_montage/bibliotheque.json), telecharges a la source (licence Mixkit :
pas de redistribution, donc hors depot) et gardes en cache dans assets/sons/.
Regle (04_montage/BONNES-PRATIQUES.md, section 5) : peu d'effets, doux, et seulement si l'image le justifie
(pas de murmure de foule sur un plan ou Franck est seul, par exemple).
Usage (dans 10_cern/) : python3 tools/habillage-sonore.py"""
import json, os, subprocess, urllib.request

DUREE = 88.5
BIBLIO = {s["id"]: s for s in json.load(open("../04_montage/bibliotheque.json"))["sons"]}

# (son, debut dans la video, volume, duree gardee ou None, fondu d'entree, fondu de sortie)
REPERES = [
    ("declencheur-photo-1", 50.85, 0.55, None, 0, 0),     # la photo du badge apparait
    ("riser-doux-1",        68.3,  0.30, None, 0.6, 0),    # monte vers « Une langue commune, un territoire commun »
    ("page-papier-2",       80.95, 0.60, None, 0, 0),      # la page de l'article arrive
    ("page-papier-2",       83.3,  0.35, None, 0, 0),      # et defile
]

os.makedirs("assets/sons", exist_ok=True)
entrees, filtres = [], []
for i, (son, t, vol, garde, f_in, f_out) in enumerate(REPERES):
    url = BIBLIO[son]["fichier_source"]
    local = f"assets/sons/{son}{os.path.splitext(url)[1]}"
    if not os.path.exists(local):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as r, open(local, "wb") as f: f.write(r.read())
    entrees += ["-i", local]
    d = garde or BIBLIO[son]["duree"]
    chaine = f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-16:TP=-2,atrim=0:{d},asetpts=PTS-STARTPTS"
    if f_in: chaine += f",afade=t=in:d={f_in}"
    if f_out: chaine += f",afade=t=out:st={max(0, d - f_out)}:d={f_out}"
    ms = int(t * 1000)
    filtres.append(chaine + f",volume={vol},adelay={ms}|{ms}[s{i}]")
filtres.append("".join(f"[s{i}]" for i in range(len(REPERES))) + f"amix=inputs={len(REPERES)}:normalize=0:duration=longest,apad,atrim=0:{DUREE}[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", ";".join(filtres), "-map", "[out]",
                "-ar", "48000", "-b:a", "192k", "assets/effets.mp3"], check=True)
print(f"habillage sonore : assets/effets.mp3 ({len(REPERES)} effets)")
