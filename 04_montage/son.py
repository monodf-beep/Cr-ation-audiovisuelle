#!/usr/bin/env python3
"""
Fabrique la bande son du film.

Il n'y a pas de modele de musique ni de bruitage disponible : la piste est
donc synthetisee ici, ce qui a un avantage sur une musique achetee — elle
est calee sur le montage a l'image pres, et le silence tombe exactement ou
il faut.

Ce qu'on entend, dans l'ordre :

  BOURDON    un souffle bas continu, la vallee et les projecteurs
  BUZZ       le ronflement des lampes a decharge, present au debut
  FRAPPE     un coup sur chaque coupe : c'est ce qui rend le montage sec
  GROSSE     une pulsation qui se resserre a mesure que le film avance
  MONTEE     un bruit filtre qui gonfle juste avant une coupe
  FOULE      une rumeur, des mains, un tambour, a partir de la tribune
  SILENCE    coupe totale pendant que le dos apparait
  ACCORD     tout revient d'un coup, puis se tient jusqu'au fondu

Les filtres sont faits par FFT : pas de scipy dans l'environnement, et un
filtrage frequentiel hors ligne suffit largement ici.

Usage : python3 04_montage/son.py
Sortie : 04_montage/champions-26.wav  (48 kHz, stereo)
"""

import wave
import numpy as np

SR = 48000
OUT = "04_montage/champions-26.wav"


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
    return rng.normal(0.0, 1.0, int(duree * SR)).astype(np.float64)


def enveloppe(n, attaque, chute, forme=2.0):
    """Attaque courte, chute exponentielle."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attaque, 1e-6), 0.0, 1.0)
    d = np.exp(-t / max(chute, 1e-6)) ** forme
    return a * d


def pose(piste, x, t0, gain=1.0):
    """Additionne x dans la piste a t0 secondes."""
    i = int(t0 * SR)
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(piste), i + len(x))
    if j > i:
        piste[i:j] += x[:j - i] * gain


# --------------------------------------------------------------------------
# Les sons
# --------------------------------------------------------------------------

def grosse(f0=95.0, f1=42.0, duree=0.55):
    """Grosse caisse : la hauteur tombe, le corps est sub."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    corps = np.sin(2 * np.pi * np.cumsum(f) / SR) * enveloppe(n, 0.001, 0.16, 1.4)
    return corps * 0.9


def frappe(rng, duree=0.9, corps=180.0):
    """Frappe metallique sur la coupe : un claquement, puis une queue."""
    n = int(duree * SR)
    b = filtre(bruit(duree, rng), bas=900.0, haut=9000.0)
    claque = b * enveloppe(n, 0.0005, 0.035, 2.2)
    t = np.arange(n) / SR
    queue = (np.sin(2 * np.pi * corps * t) * 0.5
             + np.sin(2 * np.pi * corps * 2.51 * t) * 0.3) * enveloppe(n, 0.002, 0.30, 1.2)
    return claque * 0.55 + queue * 0.35


def montee(rng, duree):
    """Bruit filtre qui gonfle et s'ouvre vers l'aigu avant une coupe."""
    n = int(duree * SR)
    b = bruit(duree, rng)
    # trois bandes croisees pour simuler un balayage du filtre
    bas = filtre(b, bas=120.0, haut=900.0)
    med = filtre(b, bas=700.0, haut=3000.0)
    aig = filtre(b, bas=2500.0, haut=9000.0)
    t = np.linspace(0.0, 1.0, n)
    x = bas * (1 - t) ** 1.5 + med * (4 * t * (1 - t)) + aig * t ** 2.2
    return x * (t ** 2.0) * 0.6


def bourdon(duree, base=41.2):
    """Souffle bas continu : deux fondamentales desaccordees, tres filtrees."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for mult, amp, det in ((1.0, 1.00, 0.0), (1.005, 0.70, 0.0),
                           (2.0, 0.30, 0.3), (3.0, 0.14, -0.4)):
        x += amp * np.sin(2 * np.pi * (base * mult + det) * t)
    # respiration lente
    x *= 1.0 + 0.20 * np.sin(2 * np.pi * 0.09 * t)
    return filtre(x, haut=420.0) * 0.22


def buzz(duree, rng):
    """Ronflement des lampes : 100 Hz et ses harmoniques, avec du flutter."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, amp in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12)):
        x += amp * np.sin(2 * np.pi * 100.0 * k * t + 0.4 * k)
    x *= 1.0 + 0.05 * filtre(bruit(duree, rng), haut=6.0) * 40.0
    return filtre(x, haut=1400.0) * 0.055


def foule(duree, rng):
    """Rumeur de tribune : bruit rose module lentement, plus des mains."""
    n = int(duree * SR)
    b = bruit(duree, rng)
    rose = filtre(b, bas=180.0, haut=3200.0)
    lent = filtre(bruit(duree, rng), haut=1.6)
    rose *= 1.0 + 2.2 * (lent / (np.abs(lent).max() + 1e-9))
    piste = rose * 0.20
    # des mains eparses
    for t0 in rng.uniform(0.0, duree - 0.2, int(duree * 7)):
        m = int(0.09 * SR)
        c = filtre(bruit(0.09, rng), bas=1200.0, haut=7000.0) * enveloppe(m, 0.0004, 0.022, 2.0)
        pose(piste, c, t0, rng.uniform(0.10, 0.30))
    return piste


def tambour(duree, rng, bpm=104.0):
    """Un tambour de tribune, regulier, un peu lache."""
    piste = np.zeros(int(duree * SR))
    pas = 60.0 / bpm
    t = 0.0
    while t < duree - 0.4:
        n = int(0.40 * SR)
        tt = np.arange(n) / SR
        peau = (np.sin(2 * np.pi * 88.0 * tt) * 0.8
                + np.sin(2 * np.pi * 132.0 * tt) * 0.3)
        coup = (peau + filtre(bruit(0.40, rng), bas=300.0, haut=2600.0) * 0.5)
        pose(piste, coup * enveloppe(n, 0.001, 0.09, 1.5), t + rng.uniform(-0.012, 0.012),
             rng.uniform(0.55, 0.85))
        t += pas
    return piste


def accord(duree, base=82.4):
    """L'accord final : quinte et octave, tenu, qui s'ouvre."""
    n = int(duree * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for mult, amp in ((1.0, 1.0), (1.5, 0.55), (2.0, 0.45), (3.0, 0.22), (4.0, 0.12)):
        x += amp * np.sin(2 * np.pi * base * mult * t + mult)
    ouverture = np.clip(t / 0.9, 0.0, 1.0)
    return filtre(x, haut=2200.0) * 0.22 * ouverture


# --------------------------------------------------------------------------
# Le montage sonore, cale sur le decoupage
# --------------------------------------------------------------------------

# (t, plan) — les coupes du film, dans l'ordre. Voir 04_montage/film.py.
COUPES = [
    (0.0,  "R2"), (2.5,  "ECUSSON"),
    (5.0,  "MATS"), (6.0, "CRAMPONS"),
    (9.0,  "FACE"), (12.0, "FORZA"), (13.5, "MANCHE"), (15.0, "FORCE"),
    (16.2, "FACE2"), (17.2, "FLAG"),
    (18.2, "ULTRAS"),
    (20.2, "NOIR"),
    (20.7, "DOS"), (23.6, "26"), (24.3, "CHAMPIONS"), (25.0, "CLUSA"),
    (25.7, "CROIX"),
]
FIN = 27.5
T_SILENCE, D_SILENCE = 20.2, 0.5
T_DOS = 20.7


def construire():
    rng = np.random.default_rng(1961)
    n = int(FIN * SR)
    p = np.zeros(n)

    # --- nappe continue -----------------------------------------------------
    pose(p, bourdon(FIN), 0.0, 1.0)
    pose(p, buzz(9.5, rng), 0.0, 1.0)                     # les lampes, avant le match

    # --- la pulsation, qui se resserre --------------------------------------
    t, pas = 5.0, 1.0
    while t < T_SILENCE - 0.1:
        pose(p, grosse(), t, 0.85)
        if t > 9.0:
            pas = 0.5                                      # deux fois plus dense
        if t > 16.0:
            pas = 0.25                                     # la montee finale
        t += pas
    t = T_DOS
    while t < FIN - 0.5:                                   # tout revient d'un coup
        pose(p, grosse(), t, 0.95)
        t += 0.5

    # --- une frappe sur chaque coupe ----------------------------------------
    for tc, nom in COUPES:
        if nom in ("NOIR",):
            continue
        gain = 0.9 if nom in ("FACE", "DOS", "ULTRAS") else 0.55
        pose(p, frappe(rng, corps=rng.uniform(150.0, 230.0)), tc, gain)

    # --- des montees avant les trois vraies bascules -------------------------
    pose(p, montee(rng, 2.2), 6.8, 0.55)                   # vers le maillot
    pose(p, montee(rng, 2.0), 16.2, 0.85)                  # vers la tribune
    pose(p, montee(rng, 1.6), 18.6, 1.00)                  # vers le noir

    # --- la tribune ---------------------------------------------------------
    d = T_SILENCE - 9.0
    f = foule(d, rng)
    f *= np.linspace(0.15, 1.0, len(f)) ** 1.6             # elle monte
    pose(p, f, 9.0, 0.9)
    pose(p, tambour(T_SILENCE - 13.0, rng), 13.0, 0.55)

    d2 = FIN - T_DOS
    f2 = foule(d2, rng)
    f2 *= np.clip(np.linspace(0.0, 1.0, len(f2)) / 0.06, 0.0, 1.0)   # d'un coup
    pose(p, f2, T_DOS, 1.15)
    pose(p, tambour(d2 - 0.6, rng), T_DOS, 0.6)

    # --- l'accord final -----------------------------------------------------
    pose(p, accord(FIN - T_DOS), T_DOS, 1.0)

    # --- la courbe generale -------------------------------------------------
    # Sans elle la piste est plate d'un bout a l'autre : tous les elements
    # sont deja la des la premiere seconde, donc rien n'arrive jamais. Le
    # film demarre a un tiers du volume et ne joue plein que sur le dos.
    t = np.arange(n) / SR
    reperes = [(0.0, 0.32), (5.0, 0.40), (9.0, 0.56),
               (16.0, 0.76), (18.2, 0.92), (T_SILENCE, 0.92),
               (T_DOS, 1.00), (FIN, 1.00)]
    p *= np.interp(t, [r[0] for r in reperes], [r[1] for r in reperes])

    # --- le silence : rien ne le traverse -----------------------------------
    i0, i1 = int(T_SILENCE * SR), int((T_SILENCE + D_SILENCE) * SR)
    fondu = int(0.02 * SR)
    p[i0 - fondu:i0] *= np.linspace(1.0, 0.0, fondu)
    p[i0:i1] = 0.0

    # --- sortie -------------------------------------------------------------
    p[-int(0.9 * SR):] *= np.linspace(1.0, 0.0, int(0.9 * SR)) ** 1.5
    p[:int(0.05 * SR)] *= np.linspace(0.0, 1.0, int(0.05 * SR))

    # --- limitation douce et stereo -----------------------------------------
    p = np.tanh(p * 1.25) * 0.88
    # une largeur legere : les aigus decales, le bas au centre
    haut = filtre(p, bas=900.0)
    bas = p - haut
    dec = int(0.0009 * SR)
    st = np.stack([bas + np.roll(haut, dec) * 0.9,
                   bas + np.roll(haut, -dec) * 0.9], axis=1)
    # on normalise apres l'elargissement, sinon le decalage repasse au-dessus
    g = np.abs(st).max()
    if g > 0:
        st *= 0.94 / g
    return np.clip(st, -1.0, 1.0)


if __name__ == "__main__":
    st = construire()
    data = (st * 32767).astype("<i2")
    with wave.open(OUT, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"{OUT}  {len(st)/SR:.1f}s  {len(COUPES)} coupes marquees")
