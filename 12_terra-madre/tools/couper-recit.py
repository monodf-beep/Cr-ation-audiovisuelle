"""Montage du recit a partir des deux prises face camera (le recit de 7 min et la prise de fin) :
garde les passages choisis, ramene chaque silence a une courte respiration, et ecrit
- la liste des morceaux (source, debut, fin) dans montage-recit.json, avec la table source -> montage ;
- face-recit.mp4 : image et son montes ensemble (face camera synchrone), accelere (montage.json),
  image eclaircie, voix traitee comme 10_cern/tools/voix-finale.sh.
Usage (dans 12_terra-madre/) : python3 tools/couper-recit.py <dossier des rushes>"""
import json, re, subprocess, sys, os

RUSHES = sys.argv[1]
SOURCES = {"recit": "VID_20261004_160508.mp4", "fin": "VID_20261004_161249.mp4"}

# Passages gardes : (sequence, source, debut, fin) en secondes dans la prise, et ce qui est dit.
PASSAGES = [
    ("sagre",     "recit", 18.3, 29.6, "Les sagre, ce sont des endroits dans les villages en général pour célébrer la gastronomie,"),
    ("sagre",     "recit", 32.6, 37.4, "les produits du terroir, les produits du Piémont."),
    ("gouter",    "recit", 42.85, 46.72, "Ce que j'aime par-dessus tout, c'est"),  # la premiere tentative (40,4) est reprise
    ("gouter",    "recit", 49.4, 55.6, "de trouver des nouveaux produits et surtout de goûter, c'est ça l'important."),
    ("piemont",   "recit", 75.85, 82.85, "On y mange uniquement du territoire, donc en général dans le Piémont on y mange uniquement piémontais,"),
    ("piemont",   "recit", 85.5, 88.4, "on y mange beaucoup, on y mange très bien,"),
    ("sieste",    "recit", 106.55, 111.25, "moi je suis quelqu'un qui fait des siestes."),
    ("turin",     "recit", 137.35, 144.35, "Le week-end dernier j'étais à Turin pour Terra Madre,"),
    ("turin",     "recit", 147.4, 152.4, "pour valoriser le terroir piémontais,"),
    ("viaroma",   "recit", 160.9, 167.8, "surtout que c'était dans via Roma, ils ont refait toute la rue de via Roma."),
    ("vallees",   "recit", 180.8, 182.1, "Et ce week-end,"),
    ("vallees",   "recit", 201.6, 209.35, "dans le Piémont on a des vallées savoyardes bien sûr, on a des vallées occitanes,"),
    ("vallees",   "recit", 214.95, 217.95, "et là j'étais dans une vallée occitane."),
    ("giaveno",   "recit", 229.45, 230.95, "J'étais à Giaveno,"),
    ("giaveno",   "recit", 240.05, 241.2, "c'est un petit village,"),
    ("giaveno",   "recit", 241.45, 250.25, "et là il y avait justement la Sagra dei Funghi, donc pour les champignons."),
    ("plats",     "recit", 260.75, 271.15, "La lasagne avec les champignons, il y avait la salsiccia, la saucisse, c'était exceptionnel."),
    ("influenceur", "fin", 48.6, 63.1, "Moi je vais pas vous montrer des plats, je suis pas un influenceur food, pas encore. Donc faut juste me faire confiance, et me croire."),
    ("cumiana",   "recit", 275.4, 282.15, "Et là je me trouve à Cumiana, entre Giaveno et Pinerolo."),
    ("bulbe",     "recit", 289.05, 292.2, "J'adore ce clocher, le bulbe,"),
    ("bulbe",     "recit", 312.1, 316.0, "qu'on retrouve un peu plus dans le Piémont, pas trop en Savoie,"),
    ("bulbe",     "recit", 318.45, 320.65, "mais c'est la même famille, on va dire."),
    ("francois",  "recit", 362.6, 364.9, "On retrouve beaucoup saint François de Sales,"),
    ("francois",  "recit", 384.85, 391.0, "c'est le saint patron des journalistes,"),
    ("francois",  "recit", 403.3, 406.85, "mais là, non, on ne l'a pas trouvé."),
    ("baroque",   "recit", 407.6, 412.55, "Et surtout le baroque : les églises regorgent de l'art baroque."),
    ("fin",       "recit", 428.45, 433.7, "Je vous remercie et à tout bientôt. Allez, abastou, ciao ciao."),
]
# Morceaux a enlever a l'interieur d'un passage (hesitations, mots repetes), en secondes de la prise.
RETIRER = {"recit": [(386.05, 388.3)],   # « qui ... est le » : « c'est un saint qui est le saint patron » -> « c'est un saint patron »
           "fin": []}
RESPIRATION = 0.28   # silence garde au plus
MARGE = 0.07

def silences(f):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-af", "silencedetect=noise=-34dB:d=0.28", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    d = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(d, e))

SIL = {k: silences(os.path.join(RUSHES, v)) + RETIRER[k] for k, v in SOURCES.items()}
for k in SIL: SIL[k].sort()

def parole(src, a, b):
    morceaux, t = [], a
    for s, e in SIL[src]:
        if e <= a or s >= b: continue
        if s > t: morceaux.append((max(a, t - MARGE), min(b, s + MARGE)))
        t = max(t, e)
    if t < b: morceaux.append((max(a, t - MARGE), b))
    return [(x, y) for x, y in morceaux if y - x > 0.12]

morceaux = []  # (sequence, source, debut, fin, pause_avant)
for seq, src, a, b, _ in PASSAGES:
    for i, (x, y) in enumerate(parole(src, a, b)):
        morceaux.append({"sequence": seq, "source": src, "a": round(x, 3), "b": round(y, 3)})

# Temps dans le montage (vitesse 1) : morceaux bout a bout, respiration entre deux morceaux.
t = 0.0
for i, m in enumerate(morceaux):
    if i:
        prec = morceaux[i - 1]
        meme = prec["source"] == m["source"] and abs(prec["b"] - m["a"]) < 0.01
        t += 0 if meme else min(RESPIRATION, 0.18 if prec["sequence"] == m["sequence"] else RESPIRATION)
    m["t"] = round(t, 3)
    t += m["b"] - m["a"]
duree = t

montage = json.load(open("montage.json"))
v = montage["vitesse"]
json.dump({"_note": "Morceaux du recit (secondes dans la prise) et leur place dans le montage (t, vitesse 1). Fait par tools/couper-recit.py.",
           "vitesse": v, "duree_voix": round(duree, 3), "duree": round(duree / v, 3),
           "passages": [{"sequence": p[0], "texte": p[4]} for p in PASSAGES], "morceaux": morceaux},
          open("montage-recit.json", "w"), ensure_ascii=False, indent=1)

# Image et son montes ensemble, morceau par morceau (fichiers intermediaires : peu de memoire),
# chaque morceau garde sa respiration (le silence reel de la prise), puis tout est recolle.
tmp = "assets/.morceaux"
os.makedirs(tmp, exist_ok=True)
liste = []
for i, m in enumerate(morceaux):
    suivant = morceaux[i + 1]["t"] if i + 1 < len(morceaux) else m["t"] + (m["b"] - m["a"])
    pause = max(0.0, suivant - m["t"] - (m["b"] - m["a"]))
    sortie = f"{tmp}/{i:03d}.mp4"
    # La respiration est un vrai silence (image figee un instant) : la suite de la prise peut etre de la parole coupee.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{m['a']:.3f}", "-to", f"{m['b']:.3f}",
                    "-i", os.path.join(RUSHES, SOURCES[m["source"]]),
                    "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,tpad=stop_mode=clone:stop_duration={pause:.3f}",
                    "-af", f"aresample=48000,aformat=channel_layouts=mono,afade=t=out:st={max(0, m['b'] - m['a'] - 0.03):.3f}:d=0.03,apad=pad_dur={pause:.3f}",
                    "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "14", "-c:a", "pcm_s16le", "-f", "matroska", sortie.replace(".mp4", ".mkv")], check=True)
    liste.append(f"file '{os.path.abspath(sortie.replace('.mp4', '.mkv'))}'")
open(f"{tmp}/liste.txt", "w").write("\n".join(liste) + "\n")
voix = ("highpass=f=80,afftdn=nr=10:nf=-42,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1.0:g=2.5,"
        "equalizer=f=10000:t=h:w=0.7:g=1,deesser=i=0.35,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,"
        "loudnorm=I=-14.5:TP=-1.5:LRA=9")
# Lumiere un peu eclaircie et rechauffee ; vitesse sans changer la hauteur de la voix.
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/liste.txt",
                "-vf", f"eq=brightness=0.03:contrast=1.04:saturation=1.08,colorbalance=rs=0.03:bs=-0.03,setpts=PTS/{v}",
                "-af", f"atempo={v},{voix}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                "-g", "15", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "assets/face-recit.mp4"], check=True)
print(f"{len(morceaux)} morceaux, voix {duree:.1f} s, video {duree / v:.1f} s")
