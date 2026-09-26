"""Metriques d'un montage vertical, avec alertes (seuils : 04_montage/BONNES-PRATIQUES.md, section 8).
Mesure la voix (debit, pauses), les sous-titres (taille des groupes, temps de lecture, mots-cles), le rythme
visuel (duree sans changement de plan, sur le rendu) et le son (volume, crete, musique sous la voix).
Ecrit un rapport lisible : <projet>/metriques.md.
Usage : python3 04_montage/metriques.py 10_cern [renders/cern-reportage.mp4]"""
import json, os, re, subprocess, sys

projet = sys.argv[1]
rendu = os.path.join(projet, sys.argv[2] if len(sys.argv) > 2 else "renders/cern-reportage.mp4")
P = lambda f: os.path.join(projet, f)

# Seuils. min/max : alerte en dehors ; les valeurs viennent des pratiques courantes des Reels, TikTok, Shorts.
SEUILS = {
    "debit_mpm":        (150, 185),   # mots par minute pendant la parole (radio ~150, formats courts 160-180)
    "debit_sequence":   (135, 200),   # par sequence : une sequence trop lente ou trop precipitee
    "pause_max":        (None, 0.6),  # s ; au-dela, un blanc s'entend (sauf changement de sequence : 0.9)
    "pause_sequence":   (None, 0.9),
    "accroche_premier_mot": (None, 0.5),  # s avant le premier mot
    "accroche_duree":   (None, 3.0),  # s pour dire le sujet
    "st_mots":          (1, 4),       # unites par groupe (mot, ou expression comme « Pays de Gex »)
    "st_caracteres":    (None, 24),  # une ligne a 66 px sur 1000 px utiles
    "st_duree":         (0.4, 3.0),   # s a l'ecran : trop court = clignote, illisible ; trop long = image figee
    "st_cps":           (None, 25),   # car./s ; groupes cales sur la voix : lus en l'entendant (17 = norme des
                                      # sous-titres classiques en phrases, trop strict ici)
    "st_cles":          (0.15, 0.40), # part des groupes avec un mot-cle
    "plan_sans_coupe":  (None, 4.0),  # s sans changement franc d'image (coupe, punch-in)
    "duree_video":      (15, 90),     # s
    "lufs":             (-16.5, -13.5),
    "crete_dbtp":       (None, -1.0),
    "musique_sous_voix": (12, 22),    # dB d'ecart voix / musique pendant la parole
}

lignes, alertes = [], []
def mesure(cle, valeur, unite="", detail="", seuil=None):
    lo, hi = seuil or SEUILS[cle]
    ok = (lo is None or valeur >= lo) and (hi is None or valeur <= hi)
    borne = f"{'' if lo is None else lo}{' - ' if lo is not None and hi is not None else ''}{'' if hi is None else ('≤ ' if lo is None else '') + str(hi)}"
    etat = "ok" if ok else "ALERTE"
    lignes.append(f"| {cle} | {valeur:g} {unite} | {borne} | {etat} | {detail} |")
    if not ok: alertes.append(f"{cle} = {valeur:g} {unite} (attendu {borne}) {detail}".strip())

montage = json.load(open(P("montage.json")))
V = montage["vitesse"]

# --- Voix (voix-mots.json, temps de la voix ramenes a la video) ---
mots = [(m[0], m[1] / V, m[2] / V) for m in json.load(open(P("voix-mots.json")))["mots"]]
seqs = [(r["id"], r["debut_voix"] / V, r["fin_voix"] / V) for r in json.load(open(P("reperes.json")))["reperes"]]
limites = [s[1] for s in seqs[1:]]
pauses = [(mots[i][2], mots[i + 1][1] - mots[i][2]) for i in range(len(mots) - 1)]
# Un nombre se dit en plusieurs mots (« cent soixante ») : il compte double.
poids = lambda t: 2 if re.search(r"\d", t) else 1
parole = sum(max(0, b - a) for _, a, b in mots) + sum(min(p, 0.6) for _, p in pauses)
n_mots = sum(poids(m[0]) for m in mots)
mesure("debit_mpm", round(n_mots / parole * 60), "mots/min", f"{n_mots / parole:.2f} mots/s")
for nom, a, b in seqs:
    n = [m for m in mots if a <= m[1] < b]
    if len(n) >= 6:
        duree = n[-1][2] - n[0][1]
        mesure("debit_sequence", round(sum(poids(m[0]) for m in n) / duree * 60), "mots/min", nom)
for t, p in pauses:
    changement = any(abs(t + p / 2 - l) < 1.0 for l in limites)
    cle = "pause_sequence" if changement else "pause_max"
    if p > SEUILS[cle][1]: mesure(cle, round(p, 2), "s", f"a {t:.1f} s")
mesure("accroche_premier_mot", round(mots[0][1], 2), "s")
mesure("accroche_duree", round(seqs[0][2], 2), "s", "sequence d'accroche")

# --- Sous-titres (index.html, groupes .st ; data-a/b en temps de la voix) ---
html = open(P("index.html")).read()
groupes = re.findall(r'<div class="st[^"]*" data-a="([\d.]+)" data-b="([\d.]+)">(.*?)</div>', html)
cles = 0
for a, b, contenu in groupes:
    a, b = float(a) / V, float(b) / V
    textes = re.findall(r'<span class="m( cle)?"[^>]*>(.*?)</span>', contenu)
    texte = " ".join(t for _, t in textes)
    cles += any(c for c, _ in textes)
    n = len(textes)
    if not 1 <= n <= SEUILS["st_mots"][1]:
        mesure("st_mots", n, "mots", f"« {texte} » a {a:.1f} s")
    if len(texte) > SEUILS["st_caracteres"][1]: mesure("st_caracteres", len(texte), "car.", f"« {texte} » a {a:.1f} s")
    d = b - a
    if not SEUILS["st_duree"][0] <= d <= SEUILS["st_duree"][1]: mesure("st_duree", round(d, 2), "s", f"« {texte} » a {a:.1f} s")
    if d > 0 and len(texte) / d > SEUILS["st_cps"][1]: mesure("st_cps", round(len(texte) / d, 1), "car./s", f"« {texte} » a {a:.1f} s")
mesure("st_cles", round(cles / max(1, len(groupes)), 2), "", f"{cles} groupes sur {len(groupes)}")

# --- Rendu : duree, coupes, son ---
if os.path.exists(rendu):
    duree = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", rendu],
                                 capture_output=True, text=True).stdout)
    mesure("duree_video", round(duree, 1), "s")
    # Changements francs d'image (coupes, flashs, punch-in) : detection de scene sur une image reduite.
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", rendu, "-vf", "scale=270:-1,select='gt(scene,0.08)',showinfo",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    # Seuil bas : un flash blanc etale la coupe sur plusieurs images. Les sous-titres restent en dessous.
    # Detections a moins de 0,4 s l'une de l'autre = une seule coupe.
    coupes = [0.0]
    for x in (float(x) for x in re.findall(r"pts_time:([\d.]+)", log)):
        if x - coupes[-1] > 0.4: coupes.append(x)
    coupes.append(duree)
    # Plans longs voulus (montage.json, exceptions_rythme, en temps de la voix) : notes, pas signales.
    exceptions = [(e["de"] / V, e["a"] / V, e["raison"]) for e in montage.get("exceptions_rythme", [])]
    for a, b in zip(coupes, coupes[1:]):
        if b - a > SEUILS["plan_sans_coupe"][1]:
            voulu = next((r for x, y, r in exceptions if min(b, y) - max(a, x) > 0.5 * (b - a)), None)
            if voulu: lignes.append(f"| plan_sans_coupe | {b - a:.1f} s | voulu | ok | de {a:.1f} a {b:.1f} s : {voulu} |")
            else: mesure("plan_sans_coupe", round(b - a, 1), "s", f"de {a:.1f} a {b:.1f} s")
    lignes.append(f"| coupes detectees | {len(coupes) - 2} | | | une toutes les {duree / max(1, len(coupes) - 2):.1f} s en moyenne |")
    ebu = subprocess.run(["ffmpeg", "-hide_banner", "-i", rendu, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mesure("lufs", float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)[-1]), "LUFS")
    mesure("crete_dbtp", float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebu)[-1]), "dBTP")
else:
    lignes.append(f"| rendu | absent | | | {rendu} : metriques du rendu non calculees |")

def lufs(f, fin):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-t", str(fin), "-i", f, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])
if os.path.exists(P("assets/musique.mp3")) and os.path.exists(P("assets/voix-off.mp3")):
    fin_voix = montage["duree_voix"] / V
    mesure("musique_sous_voix", round(lufs(P("assets/voix-off.mp3"), fin_voix) - lufs(P("assets/musique.mp3"), fin_voix), 1), "dB")

rapport = [f"# Metriques du montage ({os.path.basename(projet)})", "",
           f"Vitesse {V} · seuils et raisons : `04_montage/BONNES-PRATIQUES.md`, section 8.", "",
           f"**{len(alertes)} alerte(s)**" if alertes else "**Aucune alerte.**", ""]
rapport += [f"- {a}" for a in alertes] + ["", "| metrique | valeur | attendu | etat | detail |", "|---|---|---|---|---|"] + lignes
open(P("metriques.md"), "w").write("\n".join(rapport) + "\n")
print(f"{len(alertes)} alerte(s)" if alertes else "Aucune alerte.")
for a in alertes: print("  ALERTE", a)
print(f"rapport : {P('metriques.md')}")
