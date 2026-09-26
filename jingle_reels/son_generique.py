#!/usr/bin/env python3
"""
Bande son du generique CULTURA SABAUDA (maquette synthetisee).

Tempo 128,57 : un temps = 14 images a 30 i/s. Tous les evenements sont
donnes en images, les memes que dans generique.html, pour que chaque coup
tombe sur une coupe.

  f000  impact d'ouverture, puis une pluie de petites notes : les + qui eclosent
  f014  souffle sur la rotation
  f021  aspiration vers la coupe
  f028  le groove : kick a chaque temps, clap sur 2 et 4, charleston en doubles,
        basse en contretemps, une note pincee par carte (arpege de re mineur)
  f084  les quatre verbes : quatre stabs
  f098  montee : roulement de caisse qui accelere, bruit qui monte
  f108  silence
  f112  DROP : kick, sub, crash, accord
  f126  motif de clarine re, la, re
  f196  coup final
  f210  fin

Usage : python3 jingle_reels/son_generique.py   ->  jingle_reels/out/generique.wav
"""

import os
import wave

import numpy as np

SR = 48000
FPS = 30
DUREE = 210 / FPS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "generique.wav")
rng = np.random.default_rng(11)


def s(f):
    """images -> secondes"""
    return f / FPS


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


# ---------------------------------------------------------------- filtres FFT
def filtre(x, bas=None, haut=None, pente=0.15):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if bas:   # passe-bas
        g *= 1 / (1 + (f / bas) ** (1 / pente * 0.3))
    if haut:  # passe-haut
        g *= 1 / (1 + (haut / np.maximum(f, 1)) ** (1 / pente * 0.3))
    return np.fft.irfft(X * g, len(x))


def balayage(x, fc0, fc1):
    """Passe-bas a un pole dont la coupure glisse de fc0 a fc1 (exponentiel)."""
    n = len(x)
    fc = fc0 * (fc1 / fc0) ** np.linspace(0, 1, n)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


# ---------------------------------------------------------------- instruments
def kick(d=0.45, f0=160, f1=46, dec=0.18):
    t = tt(d)
    f = f1 + (f0 - f1) * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    x[: int(0.003 * SR)] += rng.normal(0, 0.5, int(0.003 * SR))
    return np.tanh(x * 1.6)


def sub(note, d=1.6):
    t = tt(d)
    f = hz(note) * (1 + 1.5 * np.exp(-t / 0.04))
    return np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t / 0.6) * np.minimum(1, t / 0.004)


def clap():
    t = tt(0.25)
    env = np.zeros_like(t)
    for k, d in enumerate((0, 0.011, 0.022)):
        env += (t >= d) * np.exp(-(t - d).clip(0) / (0.006 if k < 2 else 0.07))
    return filtre(rng.normal(0, 1, len(t)), bas=4500, haut=900) * env * 1.4


def hat(ouvert=False):
    t = tt(0.25 if ouvert else 0.05)
    return filtre(rng.normal(0, 1, len(t)), haut=7000) * np.exp(-t / (0.08 if ouvert else 0.012))


def caisse():
    t = tt(0.16)
    ton = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.03)
    return (filtre(rng.normal(0, 1, len(t)), bas=7000, haut=600) * np.exp(-t / 0.045) + ton * 0.6)


def scie(f, t, det=0.0):
    ph = (f * (1 + det)) * t + rng.uniform()
    return 2 * (ph % 1) - 1


def pince(note, d=0.35):
    t = tt(d)
    x = scie(hz(note), t) * 0.6 + np.sign(np.sin(2 * np.pi * hz(note) * t)) * 0.3
    x = filtre(x, bas=3200) * np.exp(-t / 0.09) * np.minimum(1, t / 0.002)
    return x


def basse(note, d=0.2):
    t = tt(d)
    x = scie(hz(note), t) + 0.5 * np.sin(2 * np.pi * hz(note) * t)
    return filtre(x, bas=700) * np.minimum(1, t / 0.003) * np.exp(-t / 0.12)


def accord(notes, d=1.2, bas=5000):
    t = tt(d)
    x = np.zeros_like(t)
    for n in notes:
        for det in (-0.012, -0.005, 0, 0.005, 0.012):
            x += scie(hz(n), t, det)
    x = filtre(x / (5 * len(notes)), bas=bas)
    return x * np.exp(-t / 0.35) * np.minimum(1, t / 0.004)


def clarine(note, d=1.5):
    """cloche de troupeau : partiels inharmoniques"""
    t = tt(d)
    f = hz(note)
    x = np.zeros_like(t)
    for r, a, dec in ((1, 1, 1.6), (2.76, 0.5, 3.5), (5.4, 0.3, 6), (8.93, 0.17, 10), (0.5, 0.2, 2.5)):
        x += a * np.sin(2 * np.pi * f * r * t + rng.uniform(0, 6)) * np.exp(-dec * t)
    x[: int(0.004 * SR)] += rng.normal(0, 0.4, int(0.004 * SR))
    return x / 2


def crash(d=2.0):
    t = tt(d)
    return filtre(rng.normal(0, 1, len(t)), haut=3500) * np.exp(-t / 0.7) * 0.6


def souffle(d, fc0, fc1, montee=True):
    x = balayage(rng.normal(0, 1, int(d * SR)), fc0, fc1)
    n = len(x)
    env = np.linspace(0, 1, n) ** 2 if montee else np.linspace(1, 0, n) ** 2
    return x * env * 2.5


def blip(note):
    t = tt(0.08)
    return np.sin(2 * np.pi * hz(note) * t) * np.exp(-t / 0.02)


# ---------------------------------------------------------------- mix
piste = np.zeros((int(DUREE * SR) + SR, 2))


def poser(x, f, g=1.0, pan=0.0):
    i = int(round(s(f) * SR))
    j = min(len(piste), i + len(x))
    a = (pan + 1) * np.pi / 4
    piste[i:j, 0] += x[: j - i] * g * np.cos(a) * 1.414
    piste[i:j, 1] += x[: j - i] * g * np.sin(a) * 1.414


RE = 62  # re4
PENTA = [62, 65, 67, 69, 72, 74, 77, 79, 81, 84]

# --- ouverture
poser(kick(0.6, 200, 42, 0.3), 0, 1.0)
poser(sub(38, 0.9), 0, 0.6)
poser(clarine(RE + 12, 1.2), 0, 0.5)
for k in range(22):                       # les + qui eclosent
    f = 1 + k * 0.42 + rng.uniform(0, 0.3)
    poser(blip(PENTA[rng.integers(len(PENTA))] + 12), f, 0.22, rng.uniform(-0.9, 0.9))
poser(kick(), 14, 0.9)
poser(souffle(0.25, 600, 9000), 12, 0.25, -0.5)
poser(souffle(s(7), 300, 12000), 21, 0.45)

# --- le groove des cartes
for b in range(4):
    f0 = 28 + b * 14
    poser(kick(), f0, 1.0)
    if b % 2:
        poser(clap(), f0, 0.55)
    for q in range(4):
        poser(hat(q == 2), f0 + q * 3.5, 0.18 if q % 2 else 0.12, 0.3)
    poser(basse(38, 0.18), f0 + 7, 0.7)
    poser(basse(38 if b < 2 else 41, 0.12), f0 + 10.5, 0.5)
ARP = [74, 77, 81, 84, 86, 84, 81, 77]
for k, n in enumerate(ARP):              # une note par carte
    poser(pince(n), 28 + k * 7, 0.35, -0.4 if k % 2 else 0.4)
poser(crash(1.0), 28, 0.35)

# --- les verbes
for k, f in enumerate((84, 88, 91, 95)):
    poser(accord([62 + k * 2, 65 + k * 2, 69 + k * 2], 0.2, 6000), f, 0.5)
    poser(kick(0.2), f, 0.7)
    poser(caisse(), f, 0.35)

# --- la montee
roul = [98 + 10 * (1 - (1 - i / 16) ** 1.7) for i in range(16)]
for i, f in enumerate(roul):
    poser(caisse(), f, 0.2 + 0.35 * i / 16, (-1) ** i * 0.2)
poser(souffle(s(10), 200, 14000), 98, 0.6)
t = tt(s(10))
poser(np.sin(2 * np.pi * np.cumsum(220 * 4 ** (t / t[-1])) / SR) * (t / t[-1]) ** 2 * 0.25, 98, 1.0)

# f108-112 : silence

# --- DROP
poser(kick(0.8, 220, 38, 0.4), 112, 1.2)
poser(sub(26, 1.8), 112, 0.9)
poser(crash(2.2), 112, 0.6)
poser(accord([50, 57, 62, 65, 69], 1.4, 4000), 112, 0.55)
poser(souffle(0.2, 9000, 500, montee=False), 119, 0.35, 0.6)   # Sabauda glisse
for k, (n, f) in enumerate(((RE + 12, 126), (RE + 19, 133), (RE + 24, 140))):
    poser(clarine(n, 1.8), f, 0.7, (-0.3, 0.3, 0)[k])
for b in range(6):
    f0 = 126 + b * 14
    poser(kick(), f0, 0.85)
    if b % 2:
        poser(clap(), f0, 0.45)
    for q in range(4):
        poser(hat(q == 2), f0 + q * 3.5, 0.15 if q % 2 else 0.1, 0.3)
    poser(basse(38, 0.18), f0 + 7, 0.6)
    poser(basse(45 if b % 2 else 41, 0.12), f0 + 10.5, 0.45)
poser(accord([50, 57, 62, 65, 69], 0.6, 6000), 196, 0.5)
poser(clarine(RE + 24, 0.9), 196, 0.6)
poser(sub(26, 0.5), 196, 0.7)

# fin nette
piste = piste[: int(DUREE * SR)]
n = int(0.03 * SR)
piste[-n:] *= np.linspace(1, 0, n)[:, None]
piste = np.tanh(piste / np.abs(piste).max() * 1.6) / np.tanh(1.6) * 0.93

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((piste * 32767).astype("<i2").tobytes())
print(OUT)
