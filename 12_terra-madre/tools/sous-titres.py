"""Sous-titres par groupes de 1 a 3 mots (04_montage/BONNES-PRATIQUES.md, section 2), en temps de la video.
Mots : transcription faster-whisper de la voix montee (data/voix-montee.mots.json, deja en temps de la video),
orthographe corrigee ici. Ecrit data/sous-titres.json.
Usage (dans 12_terra-madre/) : python3 tools/sous-titres.py"""
import json, re

# Orthographe (whisper) -> texte affiche
CORRIGE = {"sagrées": "sagre", "Villaroma": "via Roma", "Fungi": "Funghi", "bulb": "bulbe", "Piedmont": "Piémont",
           "piémont": "Piémont", "Pinerole": "Pinerolo", "Salle": "Sales", "Savoyard": "savoyardes", "Occitane": "occitanes",
           "agréer": "sagre", "Savoissa": "Savoie", "Sagrées": "sagre", "Desfonghi": "dei Funghi", "Kumiana": "Cumiana", "Fongi": "Funghi", "Fonghi": "Funghi"}
SINGULIER = {"une vallée": "occitane"}
# Expressions gardees entieres, et mots-cles (bloc bleu)
EXPRESSIONS = ["la lasagne", "Terra Madre", "via Roma", "Sagra dei Funghi", "saint François de Sales", "influenceur food", "même famille",
               "patron des journalistes", "vallées occitanes", "vallées savoyardes", "vallée occitane", "art baroque", "ciao ciao"]
CLES = {"sagre", "gastronomie", "terroir", "Piémont", "goûter", "piémontais", "siestes", "Turin", "Terra Madre", "via Roma",
        "vallées savoyardes", "vallées occitanes", "vallée occitane", "Giaveno", "Sagra dei Funghi", "champignons", "la lasagne",
        "salsiccia", "influenceur food", "Cumiana", "Pinerolo", "clocher", "bulbe", "Savoie", "même famille",
        "saint François de Sales", "patron des journalistes", "art baroque", "abastou"}
PETITS = {"de", "du", "la", "le", "les", "à", "et", "un", "une", "des", "en", "dans", "pour", "on", "y", "qui", "que", "ce", "c'est",
          "d", "l", "j", "qu", "m", "n", "au", "par", "mais", "avec", "est", "a", "je", "il", "me", "se", "plus", "pas", "trop", "très"}

mots = []
for seg in json.load(open("data/voix-montee.mots.json")):
    for w in seg["mots"]:
        mots.append({"t": w["a"], "f": max(w["b"], w["a"] + 0.08), "m": w["m"].strip()})
mots.sort(key=lambda x: x["t"])
# Recolle les apostrophes (« c », « 'est ») et retire la ponctuation sauf ? !
fus = []
for w in mots:
    if fus and (w["m"].startswith("'") or w["m"].startswith("-")):
        fus[-1]["m"] += w["m"]; fus[-1]["f"] = w["f"]
    else:
        fus.append(dict(w))
for w in fus:
    m = re.sub(r"[.,;:«»\"]", "", w["m"]).replace("'", "’") if False else re.sub(r"[.,;:«»\"]", "", w["m"])
    base = m.strip("?! ")
    w["m"] = m.replace(base, CORRIGE.get(base, base)) if base else m
txt = [w for w in fus if w["m"].strip()]
# « une vallée occitanes » -> « occitane »
for i in range(1, len(txt)):
    if txt[i]["m"] == "occitanes" and txt[i - 1]["m"] == "vallée":
        txt[i]["m"] = "occitane"
    if txt[i]["m"] == "savoyardes" and txt[i - 1]["m"] == "langue":
        txt[i]["m"] = "savoyarde"
# Corrections sur plusieurs mots (transcription)
PHRASES = [(["Sagra", "de", "Desfonghi"], "Sagra dei Funghi"), (["Sagre", "des", "Fongi"], "Sagra dei Funghi"),
           (["Sagre", "dei", "Funghi"], "Sagra dei Funghi"), (["Sagre", "des", "Funghi"], "Sagra dei Funghi"), (["Sagra", "des", "Funghi"], "Sagra dei Funghi"),
           (["à", "basse-tout"], "abastou"), (["Les", "Sagrées"], "Les sagre"), (["de", "lasagne"], "la lasagne")]
i = 0
while i < len(txt):
    for avant, apres in PHRASES:
        if [w["m"] for w in txt[i:i + len(avant)]] == avant:
            txt[i:i + len(avant)] = [{"t": txt[i]["t"], "f": txt[i + len(avant) - 1]["f"], "m": apres}]
            break
    i += 1
# Unites : expressions entieres
unites, i = [], 0
while i < len(txt):
    pris = False
    for e in EXPRESSIONS:
        n = len(e.split())
        bloc = " ".join(w["m"] for w in txt[i:i + n])
        if bloc.lower() == e.lower():
            unites.append({"t": txt[i]["t"], "f": txt[i + n - 1]["f"], "m": e}); i += n; pris = True; break
    if not pris:
        unites.append(txt[i]); i += 1
# Groupes : 1 a 3 unites, 20 caracteres, coupe aux pauses (> 0,3 s en video)
groupes, cur = [], []
def ferme():
    global cur
    if not cur: return
    # pas de petit mot en fin de groupe
    while len(cur) > 1 and cur[-1]["m"].lower() in PETITS:
        report = cur.pop()
        groupes.append(cur); cur = [report]; return
    groupes.append(cur); cur = []
for u in unites:
    nouvelle_phrase = u["m"][:1].isupper() and u["m"] not in CLES and not u["m"].startswith(("Piémont", "Turin", "Giaveno", "Cumiana", "Pinerolo", "Savoie", "Terra", "Sagra"))
    if cur and (nouvelle_phrase or u["t"] - cur[-1]["f"] > 0.3 or len(cur) >= 3 or len(" ".join(x["m"] for x in cur + [u])) > 20):
        ferme()
    cur.append(u)
ferme()
out = []
for g in groupes:
    cle = next((x["m"] for x in g if x["m"] in CLES), None)
    out.append({"debut": round(g[0]["t"], 3), "fin": round(g[-1]["f"], 3), "mots": [x["m"] for x in g], "cle": cle})
# Chaque groupe reste jusqu'au suivant (au plus 0,4 s de plus), 0,4 s minimum
for i, g in enumerate(out):
    suiv = out[i + 1]["debut"] if i + 1 < len(out) else g["fin"] + 0.4
    g["fin"] = round(min(suiv, max(g["debut"] + 0.4, g["fin"] + 0.4)), 3)  # jamais deux groupes a l'ecran
json.dump(out, open("data/sous-titres.json", "w"), ensure_ascii=False, indent=0)
n = sum(1 for g in out if g["cle"])
print(len(out), "groupes,", n, "avec mot-cle", f"({100 * n // len(out)} %)")
for g in out: print(f'{g["debut"]:6.2f} {" ".join(g["mots"])}{"  [" + g["cle"] + "]" if g["cle"] else ""}')
