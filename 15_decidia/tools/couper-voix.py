"""Montage de la voix off en savoyard : garde les six phrases et ramène chaque silence à une courte respiration.
Adapté de 10_cern/tools/couper-voix.py (branche HyperFrames). Écrit la voix montée (wav, avant accélération)
et voix-montee.json : les phrases avec leurs temps dans le montage, qui servent aux plans et aux sous-titres.
Usage (dans 15_decidia/) : python3 tools/couper-voix.py
Entrée : rushes/15_oct.__15.18.aac (prise de 15 h 18). Sortie : voix-off/voix-montee.wav, voix-montee.json"""
import json, re, subprocess

SRC = "rushes/15_oct.__15.18.aac"
SORTIE, TABLE = "voix-off/voix-montee.wav", "voix-montee.json"

# Phrases (secondes dans la prise) et leur traduction, dictée par Franck. Bornes calées sur les silences et sur
# les mots que la transcription reconnaît (Dècidia, conférence, intelligence artificielle, cycle, marketing).
PHRASES = [
    ("salon",      1.20,  6.70, "Aujourd'hui, j'étais au salon Décidia avec la French Tech et Savoy IA"),
    ("conference", 7.20, 14.40, "pour une conférence sur l'intelligence artificielle adaptée à l'entreprise."),
    ("metier",    15.40, 18.10, "C'est utiliser la capacité, les compétences métiers avant tout,"),
    ("couche",    18.40, 25.00, "et ajouter l'intelligence artificielle en plus, pour une couche supplémentaire."),
    ("cycle",     26.05, 32.95, "Nous avons parlé de tout le cycle marketing et communication."),
    ("merci",     33.85, 39.10, "Grant-marci à Rony et à tous !"),
]
RESPIRATION = 0.30   # silence maximal gardé dans une phrase
ENTRE = 0.45         # pause entre deux phrases
MARGE = 0.06         # garde autour de la parole

log = subprocess.run(["ffmpeg", "-hide_banner", "-i", SRC, "-af", "silencedetect=noise=-34dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
silences = list(zip([float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)],
                    [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]))

def parole(a, b):
    """Intervalles de parole dans [a, b], silences exclus, avec une marge ; recolle les trous courts."""
    morceaux, t = [], a
    for s, e in silences:
        if e <= a or s >= b: continue
        if s > t: morceaux.append((max(a, t - MARGE), min(b, s + MARGE)))
        t = max(t, e)
    if t < b: morceaux.append((max(a, t - MARGE), b))
    fusion = []
    for m in morceaux:
        if fusion and m[0] - fusion[-1][1] <= RESPIRATION: fusion[-1] = (fusion[-1][0], m[1])
        else: fusion.append(m)
    return [m for m in fusion if m[1] - m[0] > 0.12]

coupes, phrases, t = [], [], 0.0
for k, (pid, a, b, fr) in enumerate(PHRASES):
    if k: t += ENTRE
    debut = t
    for i, (x, y) in enumerate(parole(a, b)):
        if i: t += RESPIRATION
        coupes.append({"source": [round(x, 3), round(y, 3)], "montage": [round(t, 3), round(t + y - x, 3)]})
        t += y - x
    phrases.append({"id": pid, "debut": round(debut, 3), "fin": round(t, 3), "fr": fr,
                    "morceaux": [c["montage"] for c in coupes if c["montage"][0] >= debut - 1e-6]})

# Montage audio : chaque morceau avec un fondu de 12 ms, silences numériques entre eux.
filtres, entrees = [], []
for i, c in enumerate(coupes):
    x, y = c["source"]
    filtres.append(f"[0:a]atrim={x}:{y},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={max(0, y - x - 0.012):.3f}:d=0.012[m{i}]")
    entrees.append(f"[m{i}]")
    if i + 1 < len(coupes):
        gap = coupes[i + 1]["montage"][0] - c["montage"][1]
        filtres.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{gap:.3f}[g{i}]")
        entrees.append(f"[g{i}]")
filtres.append("".join(entrees) + f"concat=n={len(entrees)}:v=0:a=1[out]")
subprocess.run(["mkdir", "-p", "voix-off"], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", ";".join(filtres), "-map", "[out]",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", SORTIE], check=True)
json.dump({"duree": round(t, 3), "phrases": phrases, "coupes": coupes}, open(TABLE, "w"), ensure_ascii=False, indent=1)
print(f"voix montée : {t:.2f} s ({len(coupes)} morceaux)")
for p in phrases: print(f"  {p['id']:<11} {p['debut']:6.2f} -> {p['fin']:6.2f}  {p['fr']}")
