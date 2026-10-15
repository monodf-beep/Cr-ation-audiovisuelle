"""Mixe la bande-son du montage -> assets/bande-son.wav (lue par index.html), d'après plan.json (tools/monter.py).

Règles (04_montage/BONNES-PRATIQUES.md, section 5) : voix devant ; musique instrumentale environ 16 dB sous la voix,
qui remonte quand personne ne parle (accroche, carton final) ; effets doux, seulement sur une image qui les
justifie (photo qui apparaît -> déclencheur, carte qui glisse -> papier, logo qui saute -> pop, montée vers le
carton final) ; ambiance de foule seulement sur les images du salon. Mixage final à -15 LUFS, crête -1,5 dB.
Usage (dans 15_decidia/) : python3 tools/bande-son.py"""
import json, re, subprocess
import numpy as np

SR = 48000
PLAN = json.load(open("plan.json"))
TOTAL = PLAN["total"]
P, A, V = PLAN["plans"], PLAN["ancres"], PLAN["voix"]

def charger(chemin, filtre=None):
    cmd = ["ffmpeg", "-v", "error", "-i", chemin]
    if filtre: cmd += ["-af", filtre]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    brut = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(brut, np.float32).reshape(-1, 2).copy()

def lufs(x):
    """Sonie intégrée (EBU R128) d'un signal."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                        "-af", "ebur128", "-f", "null", "-"], input=x.astype(np.float32).tobytes(), capture_output=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr.decode())
    return float(m[-1]) if m else -70.0

def a_niveau(x, cible):
    return x * 10 ** ((cible - lufs(x)) / 20)

piste = np.zeros((int(TOTAL * SR) + SR, 2), np.float32)
voix_seule, musique_seule = np.zeros_like(piste), np.zeros_like(piste)   # pour mesurer l'écart voix / musique
def poser(x, t, gain_db=0.0, aussi=None):
    i = int(round(t * SR)); x = x[: max(0, len(piste) - i)] * 10 ** (gain_db / 20)
    piste[i:i + len(x)] += x
    if aussi is not None: aussi[i:i + len(x)] += x

def enveloppe(points, n):
    """Gain (dB) linéaire par morceaux : [(temps, dB), ...] -> facteur par échantillon."""
    ts, dbs = zip(*points)
    return 10 ** (np.interp(np.arange(n) / SR, ts, dbs) / 20)[:, None].astype(np.float32)

# Voix off (déjà traitée à -16 LUFS par voix-finale.sh) : phrases 1 à 5, puis le « Grant-marci ».
voix = charger("assets/voix-off.wav")
poser(voix[: int(V["fin_a"] * SR) + int(0.15 * SR)], V["debut_a"], aussi=voix_seule)
poser(voix[int(V["debut_b_voix"] * SR): int(V["fin_b_voix"] * SR) + int(0.2 * SR)], V["debut_b"], aussi=voix_seule)

# Son direct : même traitement sobre que la voix, au même niveau, fondus courts aux coupes.
for nom, (t, chemin) in PLAN["direct"].items():
    x = charger(chemin, "highpass=f=90,afftdn=nr=6:nf=-40,acompressor=threshold=-20dB:ratio=3:attack=8:release=120,"
                        "afade=t=in:d=0.03,areverse,afade=t=in:d=0.05,areverse")
    poser(a_niveau(x, -16.5), t)

parle = [(V["debut_a"], V["debut_a"] + V["fin_a"]), (V["debut_b"], V["debut_b"] + V["fin_b_voix"] - V["debut_b_voix"])]
direct = [(t, t + len(charger(c)) / SR) for t, c in PLAN["direct"].values()]

# Musique « Curiosity » (Mixkit, validée par Franck) : -32 LUFS sous la voix (16 dB dessous), -35 sous le son
# direct (prise de téléphone, plus fragile), -22 sur l'accroche et le carton final.
mus = charger("sons/musique-curiosity.mp3")[: len(piste)]
mus = a_niveau(mus, -22.0)
pts = [(0, -6), (0.25, 0), (P["hook"][1] - 0.15, 0)]
for a, b in sorted(parle + direct):
    niveau = -10 if (a, b) in parle else -13
    pts += [(a - 0.12, niveau), (b + 0.05, niveau)]
f = P["fin"][0]
pts += [(f - 0.4, -10), (f + 0.3, 0), (TOTAL - 1.4, 0), (TOTAL, -40)]
pts.sort()
poser(mus * enveloppe(pts, len(mus)), 0, aussi=musique_seule)

# Ambiance de salon (Mixkit, validée « fond sonore d'un salon ») : seulement sur les images du salon.
foule = a_niveau(charger("sons/ambiance-foule-2.wav")[: int(TOTAL * SR)], -40.0)
salon = [(0, -40), (P["hook"][1] - 0.15, -40), (P["hook"][1] + 0.1, -6), (P["entreprises"][0], -6), (P["cabine"][1], -6),
         (P["couches"][0], -40), (TOTAL, -40)]
poser(foule * enveloppe(salon, len(foule)), 0)

# Effets : un par image qui le justifie. Réglés à la crête, pas à la sonie : un déclencheur photo dure 0,39 s,
# moins que le bloc de 400 ms de la mesure EBU R128 (qui renvoie alors -70 LUFS et ferait monter le son de 46 dB).
# Crêtes en dBFS, la voix culminant vers -3 dBFS avant le gain final.
def effet(nom, t, crete=-16.0):
    x = charger(f"sons/{nom}")
    poser(x * 10 ** ((crete - 20 * np.log10(np.abs(x).max() + 1e-9)) / 20), t)
effet("whoosh-doux-1.wav", P["duo"][0] - 0.22, -15)           # accroche -> le duo
effet("clic-interface-1.wav", A["arvi"] - 0.16, -16)          # digital zoom sur Rony, premier cran
effet("clic-interface-1.wav", A["arvi"] - 0.02, -16)          # deuxième cran
effet("pop-doux-3.wav", A["frenchtech_logo"] - 0.03, -14)     # le logo French Tech saute
effet("pop-doux-3.wav", A["savoyia_logo"] - 0.03, -14)        # la sphère de Savoy IA
effet("whoosh-doux-3.wav", P["affiche"][1] - 0.32, -15)       # zoom-through : on plonge dans le programme
effet("whoosh-doux-1.wav", P["bientot"][0] + 0.45, -17)       # le téléphone s'agrandit
for plan in ("salle", "scene", "merci"):           # une photo apparaît
    effet("declencheur-photo-1.wav", P[plan][0] - 0.02, -13)
effet("pop-doux-3.wav", A["ent_1"] - 0.03, -14)               # « Enteligença » claque
effet("pop-doux-3.wav", A["art_1"] - 0.03, -14)               # « artificèla » claque
effet("page-papier-2.wav", A["carte_a"], -16)                 # la carte « compétences métiers » glisse
effet("clic-interface-1.wav", A["en_plus"], -17)              # la carte IA se décode en français
effet("page-papier-2.wav", A["carte_b"] - 0.2, -14)           # la couche IA se pose dessus
effet("whoosh-doux-1.wav", A["cycle"], -18)                   # l'anneau éclot
for k in range(5):                                            # chaque étape du cycle se pose sur l'anneau
    effet("clic-interface-1.wav", P["cycle"][0] + 0.62 + 0.3 * k + 0.4, -17)
effet("pop-doux-3.wav", A["marketing"] - 0.03, -14)           # « Marketing » claque
effet("pop-doux-3.wav", A["communication"] - 0.03, -14)       # « Communication » claque
effet("whoosh-doux-3.wav", P["cycle"][1] - 0.45, -15)         # le cycle file vers la caméra, vers le stand
effet("riser-doux-1.wav", P["fin"][0] - 2.45, -15)            # montée vers le carton final
effet("pop-doux-3.wav", P["fin"][0] + 1.0, -16)               # logos du carton final
effet("pop-doux-3.wav", P["fin"][0] + 1.25, -16)
effet("clic-interface-1.wav", A["hashtag"], -18)              # le hashtag se décode

# Niveau final : -15 LUFS par un gain fixe (un loudnorm en une passe aplatirait les baisses de la musique),
# puis un limiteur pour garder la crête sous -1,5 dB.
piste = a_niveau(piste[: int(TOTAL * SR)], -15.0)
brut = piste.astype(np.float32).tobytes()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                "-af", "alimiter=limit=0.84:attack=2:release=60:level=false", "-ar", str(SR), "-c:a", "pcm_s16le",
                "assets/bande-son.wav"], input=brut, check=True)
# Écart voix / musique pendant la voix off (04_montage/BONNES-PRATIQUES.md : 12 à 22 dB).
fen = np.concatenate([np.arange(int(a * SR), int(b * SR)) for a, b in parle])
ecart = lufs(voix_seule[fen]) - lufs(musique_seule[fen])
json.dump({"musique_sous_voix_db": round(ecart, 1)}, open("assets/mesures-son.json", "w"))
print(f"bande-son : {TOTAL:.2f} s, {lufs(charger('assets/bande-son.wav')):.1f} LUFS, musique {ecart:.1f} dB sous la voix")
