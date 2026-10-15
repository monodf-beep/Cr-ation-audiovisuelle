"""Métriques du montage, avec alertes. Adapté de 04_montage/metriques.py (branche HyperFrames), mêmes seuils
(04_montage/BONNES-PRATIQUES.md, section 8). La voix off est en savoyard : pas de débit mesuré mot à mot ;
sous-titres, rythme visuel, volume, écart voix / musique et zones masquées le sont.
Écrit metriques.md. Usage (dans 15_decidia/) : python3 tools/metriques.py [renders/decidia-v3.mp4]"""
import json, os, re, subprocess, sys

rendu = sys.argv[1] if len(sys.argv) > 1 else "renders/decidia-v3.mp4"
SEUILS = {
    "st_mots": (1, 4), "st_caracteres": (None, 24), "st_duree": (0.4, 3.0), "st_cps": (None, 25),
    "st_cles": (0.15, 0.40), "plan_sans_coupe": (None, 4.0), "duree_video": (15, 90),
    "lufs": (-16.5, -13.5), "crete_dbtp": (None, -1.0), "musique_sous_voix": (12, 22),
}
# Exceptions voulues (comme exceptions_rythme pour 10_cern) : notées dans le rapport, pas signalées.
EXCEPTIONS = {"ça veut dire la rioule ?": "question dite d'une traite (24 car. en 1 s) : coupée, un groupe clignoterait à plus de 25 car./s"}
lignes, alertes = [], []
def mesure(cle, valeur, unite="", detail="", seuil=None):
    lo, hi = seuil or SEUILS[cle]
    ok = (lo is None or valeur >= lo) and (hi is None or valeur <= hi)
    borne = f"{'' if lo is None else lo}{' - ' if lo is not None and hi is not None else ''}{'' if hi is None else ('≤ ' if lo is None else '') + str(hi)}"
    lignes.append(f"| {cle} | {valeur:g} {unite} | {borne} | {'ok' if ok else 'ALERTE'} | {detail} |")
    if not ok: alertes.append(f"{cle} = {valeur:g} {unite} (attendu {borne}) {detail}".strip())

# Sous-titres (index.html : data-a / data-b en temps de la vidéo).
html = open("index.html").read()
groupes = re.findall(r'<div class="st[^"]*" data-a="([\d.]+)" data-b="([\d.]+)">(.*?)</div>', html)
cles = 0
for a, b, contenu in groupes:
    a, b = float(a), float(b)
    textes = re.findall(r'<span class="m( cle)?"[^>]*>(.*?)</span>', contenu)
    texte = " ".join(t for _, t in textes).replace("&#x27;", "'")
    cles += any(c for c, _ in textes)
    n = len([w for w in texte.split() if w not in "?!"])
    if texte in EXCEPTIONS:
        lignes.append(f"| st_mots | {n} mots | voulu | ok | « {texte} » à {a:.1f} s : {EXCEPTIONS[texte]} |")
    elif not 1 <= n <= SEUILS["st_mots"][1]: mesure("st_mots", n, "mots", f"« {texte} » à {a:.1f} s")
    if len(texte) > SEUILS["st_caracteres"][1]: mesure("st_caracteres", len(texte), "car.", f"« {texte} » à {a:.1f} s")
    d = b - a
    if not SEUILS["st_duree"][0] <= d <= SEUILS["st_duree"][1]: mesure("st_duree", round(d, 2), "s", f"« {texte} » à {a:.1f} s")
    if d > 0 and len(texte) / d > SEUILS["st_cps"][1]: mesure("st_cps", round(len(texte) / d, 1), "car./s", f"« {texte} » à {a:.1f} s")
mesure("st_cles", round(cles / max(1, len(groupes)), 2), "", f"{cles} groupes sur {len(groupes)}")

# Rendu : durée, coupes (détection de scène), volume, crête.
if os.path.exists(rendu):
    duree = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", rendu],
                                 capture_output=True, text=True).stdout)
    mesure("duree_video", round(duree, 1), "s")
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", rendu, "-vf", "scale=270:-1,select='gt(scene,0.03)',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    coupes = [0.0]
    for x in (float(x) for x in re.findall(r"pts_time:([\d.]+)", log)):
        if x - coupes[-1] > 0.4: coupes.append(x)
    coupes.append(duree)
    # Plans longs voulus (comme exceptions_rythme pour 10_cern) : notés, pas signalés.
    fin = json.load(open("plan.json"))["plans"]["fin"]
    voulus = [(fin[0], fin[1], "carton final à lire")]
    for a, b in zip(coupes, coupes[1:]):
        if b - a > SEUILS["plan_sans_coupe"][1]:
            voulu = next((r for x, y, r in voulus if min(b, y) - max(a, x) > 0.5 * (b - a)), None)
            if voulu: lignes.append(f"| plan_sans_coupe | {b - a:.1f} s | voulu | ok | de {a:.1f} à {b:.1f} s : {voulu} |")
            else: mesure("plan_sans_coupe", round(b - a, 1), "s", f"de {a:.1f} à {b:.1f} s")
    lignes.append(f"| coupes détectées | {len(coupes) - 2} | | | une toutes les {duree / max(1, len(coupes) - 2):.1f} s en moyenne |")
    ebu = subprocess.run(["ffmpeg", "-hide_banner", "-i", rendu, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mesure("lufs", float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)[-1]), "LUFS")
    mesure("crete_dbtp", float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebu)[-1]), "dBTP")
else:
    lignes.append(f"| rendu | absent | | | {rendu} : métriques du rendu non calculées |")

if os.path.exists("assets/mesures-son.json"):
    mesure("musique_sous_voix", json.load(open("assets/mesures-son.json"))["musique_sous_voix_db"], "dB")

# Zones masquées par Instagram et TikTok (tools/zones-sures.cjs, repris de 04_montage/).
try:
    z = subprocess.run(["node", "tools/zones-sures.cjs", "."], capture_output=True, text=True, timeout=600)
    problemes = json.loads(z.stdout) if z.returncode == 0 else None
except Exception:
    problemes = None
if problemes is None:
    lignes.append("| zones_masquees | non mesuré | | | Chrome ou playwright indisponible |")
else:
    for x in problemes:
        mesure("zones_masquees", 1, "texte", f"« {x['texte']} » en zone {x['zone']} de {x['de']:.1f} à {x['a']:.1f} s", seuil=(None, 0))
    if not problemes: lignes.append("| zones_masquees | 0 texte | aucun | ok | haut 250 px, bas 480 px, colonne de droite 140 px |")

rapport = ["# Métriques du montage (15_decidia)", "", "Seuils et raisons : `04_montage/BONNES-PRATIQUES.md`, section 8 (branche HyperFrames).", "",
           f"**{len(alertes)} alerte(s)**" if alertes else "**Aucune alerte.**", ""]
rapport += [f"- {a}" for a in alertes] + ["", "| métrique | valeur | attendu | état | détail |", "|---|---|---|---|---|"] + lignes
open("metriques.md", "w").write("\n".join(rapport) + "\n")
print(f"{len(alertes)} alerte(s)" if alertes else "Aucune alerte.")
for a in alertes: print("  ALERTE", a)
