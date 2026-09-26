"""Applique la vitesse du montage (montage.json) aux temps fixes d'index.html et de reperes.json.
Les temps de reference sont en « temps de la voix » (vitesse 1) : attributs data-voix-start / data-voix-duration /
data-voix-media-start (crees au premier passage a partir des valeurs en place), debut_voix / fin_voix dans
reperes.json. Les animations GSAP, elles, sont accelerees dans le script d'index.html (constante VITESSE).
Les videos d'illustration gardent leur vitesse normale (on en montre simplement moins) ; la face camera,
accelere comme la voix (tools/face-voix.py), cale son data-media-start sur la video.
Usage (dans 10_cern/) : python3 tools/vitesse.py"""
import json, re

V = json.load(open("montage.json"))["vitesse"]
html = open("index.html").read()

def balise(m):
    t = m.group(0)
    if "data-start=" not in t or 'class="st' in t: return t
    def attr(nom):
        x = re.search(rf'\s{nom}="([^"]*)"', t)
        return x.group(1) if x else None
    for nom in ("start", "duration", "media-start"):
        if attr(f"data-{nom}") is not None and attr(f"data-voix-{nom}") is None:
            t = t.replace(f' data-{nom}="{attr(f"data-{nom}")}"', f' data-{nom}="{attr(f"data-{nom}")}" data-voix-{nom}="{attr(f"data-{nom}")}"')
    for nom in ("start", "duration"):
        if attr(f"data-voix-{nom}") is not None:
            t = re.sub(rf'(\s)data-{nom}="[^"]*"', rf'\1data-{nom}="{round(float(attr(f"data-voix-{nom}")) / V, 3):g}"', t, count=1)
    if "face-voix" in t and attr("data-voix-media-start") is not None:
        t = re.sub(r'(\s)data-media-start="[^"]*"', rf'\1data-media-start="{round(float(attr("data-voix-media-start")) / V, 3):g}"', t, count=1)
    return t

html = re.sub(r"<(?:div|video|audio|img)\b[^>]*>", balise, html)
html, n = re.subn(r"const VITESSE = [\d.]+;", f"const VITESSE = {V};", html)
assert n == 1, "const VITESSE introuvable dans index.html"
open("index.html", "w").write(html)

r = json.load(open("reperes.json"))
for x in r["reperes"]:
    x.setdefault("debut_voix", x["debut"]); x.setdefault("fin_voix", x["fin"])
    x["debut"], x["fin"] = round(x["debut_voix"] / V, 2), round(x["fin_voix"] / V, 2)
open("reperes.json", "w").write(json.dumps(r, ensure_ascii=False, indent=2))
duree = json.load(open("montage.json"))["duree"]
print(f"vitesse {V} : video de {duree / V:.2f} s (voix {json.load(open('montage.json'))['duree_voix'] / V:.2f} s)")
