#!/usr/bin/env python3
"""
Fabrique la bande son du film.

Elle est calee sur 04_montage/coupes.json, ecrit par le montage : le son
ne recalcule jamais ses propres temps, il lit ceux de l'image. Sans ca il
derive d'une image ou deux a chaque plan, et les frappes tombent a cote.

Ce qu'on entend, dans l'ordre :

  AMORCE     noir, un claquement metallique, la lampe rate, deuxieme
             claquement, puis le ronflement qui monte avec la lumiere
  BOURDON    un souffle bas continu, la vallee
  FRAPPE     un coup sur chaque coupe : c'est ce qui rend le montage sec
  GROSSE     une pulsation qui se resserre : 1 s, puis 1/2, 1/3, 1/4, 1/6
  IMPACT     une chute de hauteur sur les trois vraies bascules
  FOULE      la tribune, qu'on entend nettement sous le plan des supporters
  RAFALE     un gate sur doubles-croches pendant les cinq coupes courtes
  SILENCE    coupe totale pendant que le dos apparait
  ACCORD     tout revient d'un coup, puis se tient
  OUTRO      un coup sec sur le carton, et une resonance qui s'eteint

Les filtres sont faits par FFT : pas de scipy dans l'environnement, et un
filtrage frequentiel hors ligne suffit largement ici.

Usage : python3 04_montage/son.py   (apres 04_montage/film.py)
Sortie : 04_montage/champions-26.wav  (48 kHz, stereo)
"""

import json
import wave
import numpy as np

SR = 48000
OUT = "04_montage/champions-26.wav"
COUPES = "04_montage/coupes.json"


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------

def filtre(x, bas=None, haut=None, pente=2.0):
    """Passe-bande par FFT. bas/haut en Hz, None pour laisser passer."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.ones_like(f)
    if bas is not None:
        g *= 1.0 / (1.0 + (np.maximum(f, 1e-9) / bas) ** (-2 * pente)) ** 0.5
    if haut is not None:
        g *= 1.0 / (1.0 + (f / haut) ** (2 * pente)) ** 0.5
    return np.fft.irfft(X * g, n)


def bruit(duree, rng):
    return rng.normal(0.0, 1.0, max(int(duree * SR), 1)).astype(np.float64)


def enveloppe(n, attaque, chute, forme=2.0):
    t = np.arange(n) / SR
    return np.clip(t / max(attaque, 1e-6), 0.0, 1.0) * np.exp(-t / max(chute, 1e-6)) ** forme


def pose(piste, x, t0, gain=1.0):
    i = int(t0 * SR)
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(piste), i + len(x))
    if j > i:
        piste[i:j] += x[:j - i] * gain


# --------------------------------------------------------------------------
# Les sons
# --------------------------------------------------------------------------

def grosse(duree=0.55, f0=95.0, f1=42.0):
    n = int(duree * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * enveloppe(n, 0.001, 0.16, 1.4) * 0.9


def frappe(rng, duree=0.9, corps=180.0):
    n = int(duree * SR)
    b = filtre(bruit(duree, rng), bas=900.0, haut=9000.0)
    claque = b * enveloppe(n, 0.0005, 0.035, 2.2)
    t = np.arange(n) / SR
    queue = (np.sin(2 * np.pi * corps * t) * 0.5
             + np.sin(2 * np.pi * corps * 2.51 * t) * 0.3) * enveloppe(n, 0.002, 0.30, 1.2)
    return claque * 0.55 + queue * 0.35


def claquement(rng, duree=1.6):
    """Le contacteur d'un projecteur. Ca doit claquer.

    La premiere version etait trop polie : l'attaque etait filtree, le metal
    s'eteignait en un dixieme de seconde et le grave arrivait apres. Un
    contacteur, c'est d'abord une transitoire large bande de deux
    millisecondes — c'est elle qui fait le claquement, pas la resonance qui
    suit. On la laisse donc passer entiere, on lui met un sub dessous qui
    part en meme temps, et le metal sonne plus longtemps derriere.
    """
    n = int(duree * SR)
    t = np.arange(n) / SR

    # la transitoire : large bande, non filtree, deux millisecondes
    crack = bruit(duree, rng) * enveloppe(n, 0.00004, 0.0022, 3.0)
    # juste apres, l'arc electrique
    arc = filtre(bruit(duree, rng), bas=2600.0) * enveloppe(n, 0.0002, 0.014, 2.2)
    # le metal du boitier, qui sonne
    metal = np.zeros(n)
    for f, a in ((317.0, 1.0), (721.0, 0.7), (1187.0, 0.5),
                 (2411.0, 0.35), (4013.0, 0.22), (6221.0, 0.12)):
        metal += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) \
            * np.exp(-t / (0.22 + 60.0 / f))
    # le sub part avec la transitoire, pas apres
    grave = np.sin(2 * np.pi * np.cumsum(38.0 + 130.0 * np.exp(-t / 0.035)) / SR) \
        * enveloppe(n, 0.0004, 0.30, 1.0)
    x = crack * 1.35 + arc * 0.75 + metal * 0.34 + grave * 1.25
    return np.tanh(x * 1.5) * 0.9                    # on l'ecrase, ca durcit l'attaque


def impact(duree=1.8, f0=180.0, f1=32.0):
    """Une chute de hauteur : ce qui fait qu'une bascule s'entend."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * enveloppe(n, 0.002, 0.42, 1.1) * 0.75


def montee(rng, duree):
    n = int(duree * SR)
    b = bruit(duree, rng)
    bas = filtre(b, bas=120.0, haut=900.0)
    med = filtre(b, bas=700.0, haut=3000.0)
    aig = filtre(b, bas=2500.0, haut=9000.0)
    t = np.linspace(0.0, 1.0, n)
    return (bas * (1 - t) ** 1.5 + med * (4 * t * (1 - t)) + aig * t ** 2.2) * t ** 2.0 * 0.6


def bourdon(duree, base=41.2):
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for mult, amp, det in ((1.0, 1.00, 0.0), (1.005, 0.70, 0.0),
                           (2.0, 0.30, 0.3), (3.0, 0.14, -0.4)):
        x += amp * np.sin(2 * np.pi * (base * mult + det) * t)
    x *= 1.0 + 0.20 * np.sin(2 * np.pi * 0.09 * t)
    return filtre(x, haut=420.0) * 0.22


def buzz(duree, rng):
    """Le ronflement d'une lampe a decharge : 100 Hz et ses harmoniques."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, amp in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12)):
        x += amp * np.sin(2 * np.pi * 100.0 * k * t + 0.4 * k)
    x *= 1.0 + 0.05 * filtre(bruit(duree, rng), haut=6.0) * 40.0
    return filtre(x, haut=1400.0) * 0.075


def foule(duree, rng, densite=7):
    """Rumeur de tribune : bruit rose module lentement, plus des mains."""
    n = int(duree * SR)
    rose = filtre(bruit(duree, rng), bas=180.0, haut=3200.0)
    lent = filtre(bruit(duree, rng), haut=1.6)
    rose *= 1.0 + 2.2 * (lent / (np.abs(lent).max() + 1e-9))
    piste = rose * 0.20
    for t0 in rng.uniform(0.0, max(duree - 0.2, 0.01), int(duree * densite)):
        m = int(0.09 * SR)
        c = filtre(bruit(0.09, rng), bas=1200.0, haut=7000.0) * enveloppe(m, 0.0004, 0.022, 2.0)
        pose(piste, c, t0, rng.uniform(0.10, 0.30))
    return piste


def voix(duree, rng):
    """Le grain d'un chant lointain : des formants sur la rumeur.

    Une foule ne fait pas que du bruit blanc filtre — on entend une hauteur.
    Quelques formants tres flous suffisent a la faire reconnaitre comme
    humaine sans qu'on cherche a comprendre des paroles.
    """
    n = int(duree * SR)
    x = np.zeros(n)
    for f, a in ((196.0, 1.0), (294.0, 0.55), (392.0, 0.40), (588.0, 0.22), (784.0, 0.12)):
        detune = 1.0 + 0.012 * filtre(bruit(duree, rng), haut=3.0) * 30.0
        x += a * np.sin(2 * np.pi * f * np.cumsum(detune) / SR)
    souffle = np.abs(filtre(bruit(duree, rng), haut=2.2))
    x *= 0.5 + 1.6 * souffle / (souffle.max() + 1e-9)
    return filtre(x, bas=150.0, haut=2200.0) * 0.16


def cris(duree, rng, densite=3.2):
    """Des cris, pas seulement une rumeur.

    Une tribune qui rugit s'entend a ses transitoires : des bouffees courtes
    et desynchronisees qui montent au-dessus du bruit de fond. Sans elles on
    entend un souffle, jamais des gens.
    """
    piste = np.zeros(max(int(duree * SR), 1))
    for t0 in rng.uniform(0.0, max(duree - 0.7, 0.01), max(int(duree * densite), 1)):
        d = rng.uniform(0.35, 0.85)
        m = int(d * SR)
        tt = np.arange(m) / SR
        base = rng.uniform(210.0, 380.0)
        c = np.zeros(m)
        for k, a in ((1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2), (6, 0.1)):
            gliss = base * k * (1.0 + 0.10 * np.exp(-tt / (d * 0.35)))
            c += a * np.sin(2 * np.pi * np.cumsum(gliss) / SR + rng.uniform(0, 6.28))
        c += filtre(bruit(d, rng), bas=900.0, haut=5000.0) * 0.8   # le souffle du cri
        env = np.clip(tt / 0.05, 0, 1) * np.exp(-np.maximum(tt - d * 0.35, 0) / (d * 0.3))
        pose(piste, filtre(c * env, bas=170.0, haut=3600.0), t0, rng.uniform(0.35, 0.9))
    return piste * 0.10


def tambour(duree, rng, bpm=104.0):
    piste = np.zeros(max(int(duree * SR), 1))
    pas, t = 60.0 / bpm, 0.0
    while t < duree - 0.4:
        n = int(0.40 * SR)
        tt = np.arange(n) / SR
        peau = np.sin(2 * np.pi * 88.0 * tt) * 0.8 + np.sin(2 * np.pi * 132.0 * tt) * 0.3
        coup = peau + filtre(bruit(0.40, rng), bas=300.0, haut=2600.0) * 0.5
        pose(piste, coup * enveloppe(n, 0.001, 0.09, 1.5),
             t + rng.uniform(-0.012, 0.012), rng.uniform(0.55, 0.85))
        t += pas
    return piste


def accord(duree, base=82.4):
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for mult, amp in ((1.0, 1.0), (1.5, 0.55), (2.0, 0.45), (3.0, 0.22), (4.0, 0.12)):
        x += amp * np.sin(2 * np.pi * base * mult * t + mult)
    return filtre(x, haut=2200.0) * 0.22 * np.clip(t / 0.9, 0.0, 1.0)


# --------------------------------------------------------------------------
# Le montage sonore
# --------------------------------------------------------------------------

def construire(j):
    rng = np.random.default_rng(1961)
    fin = j["fin"]
    n = int(fin * SR)
    p = np.zeros(n)
    coupes = [(t, nom) for t, nom, _ in j["coupes"]]
    quand = {}
    for t, nom in coupes:
        quand.setdefault(nom, []).append(t)

    t_amorce = quand["MACRO-LAMPE"][0]
    t_ultras = quand["CLIP-ULTRAS"][0]
    t_rafale = quand["CLIP-CRAMPONS"][-1]
    t_dos = quand["CLIP-DOS"][0]
    t_calme = quand["DOS"][0]          # le plan long ou tout retombe
    t_noir = next(a for a, _ in j["noirs"] if abs(a - t_dos) < 1.0)

    # --- l'amorce : deux claquements, cales sur les deux eclairs ----------
    duree_amorce = coupes[1][0] - t_amorce
    for u, g in ((0.115, 1.00), (0.285, 0.72)):
        pose(p, claquement(rng), t_amorce + u * duree_amorce, g)
    pose(p, impact(f0=140.0), t_amorce + 0.115 * duree_amorce, 0.9)
    # le ronflement s'installe avec la lumiere
    d_buzz = t_ultras - t_amorce
    b = buzz(d_buzz, rng)
    b *= np.clip(np.linspace(0.0, 1.0, len(b)) / 0.10, 0.0, 1.0) * np.linspace(1.0, 0.35, len(b))
    pose(p, b, t_amorce + 0.115 * duree_amorce)

    pose(p, bourdon(fin), 0.0)

    # --- la pulsation, qui se resserre ------------------------------------
    # Le tempo de base est monte : la ou le film battait a 60, il bat a 100,
    # et les paliers suivent. Une pulsation lente etait juste pour une
    # ouverture, jamais pour les vingt secondes qui suivent.
    NOIRE = 60.0 / 100.0
    paliers = [(coupes[1][0], NOIRE), (quand["CLIP-FACE"][0], NOIRE / 2),
               (quand["CLIP-FLAG"][0], NOIRE / 3), (t_ultras, NOIRE / 4),
               (t_rafale, NOIRE / 6)]
    t = paliers[0][0]
    while t < t_noir - 0.05:
        pas = next(v for s, v in reversed(paliers) if t >= s - 1e-6)
        pose(p, grosse(), t, 0.85 if pas > NOIRE / 2.5 else 0.60)
        t += pas
    t = t_dos                                   # tout revient d'un coup
    while t < t_calme - 0.15:
        pose(p, grosse(), t, 0.95)
        t += NOIRE / 2

    # --- une frappe sur chaque coupe --------------------------------------
    gros = {"CLIP-FACE", "CLIP-ULTRAS", "CLIP-DOS"}
    for t, nom in coupes:
        if nom in ("MACRO-LAMPE", "DOS"):       # ni l'amorce ni l'apaisement
            continue
        pose(p, frappe(rng, corps=rng.uniform(150.0, 230.0)),
             t, 0.9 if nom in gros else 0.55)

    # --- les trois bascules ------------------------------------------------
    for t, g, f0 in ((quand["CLIP-FACE"][0], 0.8, 150.0), (t_ultras, 0.9, 200.0),
                     (t_dos, 1.0, 260.0)):
        pose(p, impact(f0=f0), t, g)
    pose(p, montee(rng, 1.8), quand["CLIP-FACE"][0] - 1.8, 0.55)
    pose(p, montee(rng, 1.6), t_ultras - 1.6, 0.85)
    pose(p, montee(rng, 1.4), t_noir - 1.4, 1.00)

    # --- la tribune : on doit entendre des gens, pas un souffle ------------
    d = t_noir - quand["CLIP-FACE"][0]
    f = foule(d, rng)
    f *= np.linspace(0.18, 1.0, len(f)) ** 1.5
    pose(p, f, quand["CLIP-FACE"][0], 0.85)
    pose(p, cris(d, rng, densite=1.1), quand["CLIP-FACE"][0], 0.5)
    # sous le plan du noyau au drapeau, ils crient
    d_u = (t_rafale - t_ultras) + 1.0
    pose(p, foule(d_u, rng, densite=16), t_ultras, 1.30)
    pose(p, voix(d_u, rng), t_ultras, 1.25)
    pose(p, cris(d_u, rng, densite=4.5), t_ultras, 1.35)
    pose(p, tambour(t_noir - t_ultras, rng), t_ultras, 0.75)

    # --- la rafale : un gate sur doubles-croches ---------------------------
    t = t_rafale
    while t < t_noir - 0.05:
        m = int(0.11 * SR)
        g = filtre(bruit(0.11, rng), bas=500.0, haut=7000.0) * enveloppe(m, 0.0006, 0.026, 2.0)
        pose(p, g, t, 0.55)
        t += NOIRE / 6

    # --- apres le silence : tout revient d'un coup -------------------------
    d2 = t_calme - t_dos
    f2 = foule(d2, rng, densite=14)
    f2 *= np.clip(np.linspace(0.0, 1.0, len(f2)) / 0.04, 0.0, 1.0)
    pose(p, f2, t_dos, 1.35)
    pose(p, voix(d2, rng), t_dos, 1.2)
    pose(p, cris(d2, rng, densite=4.0), t_dos, 1.3)
    pose(p, tambour(d2, rng), t_dos, 0.7)
    pose(p, accord(fin - t_dos), t_dos)

    # --- l'apaisement : tout retombe, il ne reste que la salle -------------
    # Le dernier plan ne recoit ni frappe ni pulsation. La foule s'eloigne
    # au lieu de s'arreter net : c'est le contraste avec la rafale qui fait
    # exister la rafale.
    d3 = fin - t_calme
    lointain = filtre(foule(d3, rng, densite=5), haut=1100.0)
    lointain *= np.linspace(1.0, 0.10, len(lointain)) ** 1.6
    pose(p, lointain, t_calme, 0.85)
    pose(p, impact(2.6, f0=120.0), t_calme, 0.55)

    # --- la courbe generale -------------------------------------------------
    # Sans elle la piste est plate d'un bout a l'autre : tous les elements
    # sont deja la des la premiere seconde, donc rien n'arrive jamais.
    t = np.arange(n) / SR
    reperes = [(0.0, 0.22), (t_amorce + 0.5, 0.34), (quand["CLIP-FACE"][0], 0.58),
               (t_ultras, 0.88), (t_rafale, 1.00), (t_noir, 1.00),
               (t_dos, 1.00), (t_calme, 0.62), (fin, 0.30)]
    p *= np.interp(t, [r[0] for r in reperes], [r[1] for r in reperes])

    # --- le silence : rien ne le traverse -----------------------------------
    i0, i1 = int(t_noir * SR), int(t_dos * SR)
    fondu = int(0.02 * SR)
    p[i0 - fondu:i0] *= np.linspace(1.0, 0.0, fondu)
    p[i0:i1] = 0.0

    # --- sortie -------------------------------------------------------------
    q = int(0.8 * SR)
    p[-q:] *= np.linspace(1.0, 0.0, q) ** 1.4
    p[:int(0.05 * SR)] *= np.linspace(0.0, 1.0, int(0.05 * SR))

    p = np.tanh(p * 1.30) * 0.88
    haut = filtre(p, bas=900.0)
    bas = p - haut
    dec = int(0.0009 * SR)
    st = np.stack([bas + np.roll(haut, dec) * 0.9,
                   bas + np.roll(haut, -dec) * 0.9], axis=1)
    g = np.abs(st).max()
    if g > 0:
        st *= 0.94 / g
    return np.clip(st, -1.0, 1.0)


if __name__ == "__main__":
    with open(COUPES) as fp:
        j = json.load(fp)
    st = construire(j)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    print(f"{OUT}  {len(st)/SR:.2f}s  {len(j['coupes'])} coupes marquees")
