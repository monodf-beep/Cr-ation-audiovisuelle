"""Montage de la voix off a partir d'une prise libre : garde les passages choisis et ramene
chaque silence a une courte respiration. Ecrit la voix montee (wav) et la table de correspondance
source -> montage (json), qui sert a recaler les images et les sous-titres.
Usage : python3 tools/couper-voix.py <prise.wav> <sortie.wav> <sortie.json>"""
import json, re, subprocess, sys

src, sortie, table = sys.argv[1:4]

# Passages gardes (secondes dans la prise), avec la sequence du montage qu'ils racontent.
PASSAGES = [
    ("accroche",     0.0,   10.9, "La langue savoyarde au CERN ! Eh oui, jeudi dernier, le 24 septembre,"),
    ("carte",        10.9,  19.5, "je suis allé au CERN, à Genève, dans un projet Interreg du Grand Genève,"),
    ("cern",         19.5,  33.3, "et ça s'est passé ici, au Globe du CERN, le Globe de la science et de l'innovation."),
    ("projet",       33.3,  58.8, "Ce projet culturel, c'est sur ce territoire du Grand Genève, un territoire à cheval entre le Pays de Gex, la Haute-Savoie et Genève."),
    ("sur-place",    58.8,  72.4, "Et pourquoi j'étais là ? Justement pour représenter l'Enstitut de la Lengoua Savoyârda."),
    ("culture",      72.4,  98.8, "Ce projet Interreg sur la culture, c'est les festivals de jazz, les salles de théâtre, les musées, les orchestres, mais aussi travailler sur un bien commun, une culture commune : déjà 160 acteurs, 140 structures, des deux côtés de la frontière."),
    ("globe",        102.2, 130.9, "Et qu'en est-il du savoyard ? Eh bien le savoyard est aussi une langue de Genève, pas seulement de Savoie : le Cé qu'è lainô, l'hymne de Genève, est écrit en savoyard. C'est une langue commune à nos territoires, un bien commun."),
    ("merci",        180.6, 183.4, "Et je remercie Laetitia Picard pour son invitation."),
]
# Reprises a enlever (faux departs, phrases dites deux fois), calees sur les silences de la prise.
EXCLURE = [(24.1, 26.3), (58.7, 64.45), (111.8, 117.85),
           (92.26, 93.5)]            # « 140… » dit une premiere fois, avant « 140 structures »
# Mots retires au milieu d'une phrase : coupe franche, sans marge ni respiration.
RETIRER = [(16.34, 16.94)]           # « Alcotra » (erreur : le projet est Interreg France-Suisse)
RESPIRATION = 0.35   # duree maximale d'un silence garde
MARGE = 0.08         # garde autour de la parole

# Silences de la prise.
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "silencedetect=noise=-38dB:d=0.35", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
debuts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
fins = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
silences = list(zip(debuts, fins)) + EXCLURE
silences.sort()

def sans_mots(morceaux):
    """Retire les mots de RETIRER ; les deux bouts sont recolles sans pause (drapeau colle)."""
    out = []
    for x, y in morceaux:
        bouts, colle = [(x, y)], False
        for a, b in RETIRER:
            nouveaux = []
            for u, v in bouts:
                if b <= u or a >= v: nouveaux.append((u, v))
                else:
                    if a > u: nouveaux.append((u, a))
                    if b < v: nouveaux.append((b, v))
            bouts = nouveaux
        for i, bout in enumerate(bouts):
            out.append((bout[0], bout[1], i > 0))
    return out

def parole(a, b):
    """Intervalles de parole dans [a, b], silences exclus, avec une marge."""
    morceaux, t = [], a
    for s, e in silences:
        if e <= a or s >= b: continue
        if s > t: morceaux.append((max(a, t - MARGE), min(b, s + MARGE)))
        t = max(t, e)
    if t < b: morceaux.append((max(a, t - MARGE), b))
    # Recoller les morceaux separes par moins d'une respiration.
    fusion = []
    for m in morceaux:
        if fusion and m[0] - fusion[-1][1] <= RESPIRATION: fusion[-1] = (fusion[-1][0], m[1])
        else: fusion.append(m)
    return fusion

coupes, sections, t = [], [], 0.0
for seq, a, b, texte in PASSAGES:
    debut_section = t
    for i, (x, y, colle) in enumerate(sans_mots(parole(a, b))):
        if coupes and not colle: t += RESPIRATION if i else RESPIRATION * 1.6   # pause un peu plus longue entre passages
        coupes.append({"source": [round(x, 3), round(y, 3)], "montage": [round(t, 3), round(t + y - x, 3)]})
        t += y - x
    sections.append({"sequence": seq, "debut": round(debut_section, 3), "fin": round(t, 3), "texte": texte})

# Montage audio : chaque morceau avec un fondu de 15 ms, silences numeriques entre eux.
filtres, entrees = [], []
for i, c in enumerate(coupes):
    x, y = c["source"]
    filtres.append(f"[0:a]atrim={x}:{y},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={max(0, y - x - 0.015)}:d=0.015[m{i}]")
    if i + 1 < len(coupes):
        gap = coupes[i + 1]["montage"][0] - c["montage"][1]
        entrees.append(f"[m{i}]")
        if gap > 0.001:
            filtres.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{gap:.3f}[g{i}]")
            entrees.append(f"[g{i}]")
    else:
        entrees.append(f"[m{i}]")
filtres.append("".join(entrees) + f"concat=n={len(entrees)}:v=0:a=1[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(filtres), "-map", "[out]",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", sortie], check=True)
json.dump({"duree": round(t, 3), "sections": sections, "coupes": coupes}, open(table, "w"), ensure_ascii=False, indent=1)
print(f"voix montee : {t:.1f} s, {len(coupes)} morceaux")
for s in sections: print(f"  {s['sequence']:<12} {s['debut']:6.1f} -> {s['fin']:6.1f}  ({s['fin'] - s['debut']:4.1f} s)")
