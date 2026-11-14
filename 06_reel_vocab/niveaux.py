#!/usr/bin/env python3
"""
Plan des niveaux du reel : volume perçu (LUFS momentané, fenêtre 400 ms,
mesure EBU R128 de ffmpeg) de chaque couche — voix, musique, ambiance du
stade, effets — et du master, plan par plan.

Usage : python3 niveaux.py montage.json   (après `reel.py montage.json --audio`)
Sortie : DOSSIER_TRAVAIL/niveaux.png et niveaux.txt
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "montage.json", encoding="utf-8"))
work = cfg["travail"]
master = os.path.splitext(cfg["sortie"])[0] + "_son.m4a"


def momentane(path):
    """(temps, LUFS momentané) toutes les 100 ms."""
    err = subprocess.run(["ffmpeg", "-v", "verbose", "-nostats", "-i", path, "-af", "ebur128=framelog=verbose",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    t, m = [], []
    for line in err.splitlines():
        r = re.search(r"t:\s*([\d.]+)\s+.*?M:\s*(-?[\d.]+|-inf)", line)
        if r:
            t.append(float(r.group(1)))
            v = r.group(2)
            m.append(-70.0 if v == "-inf" else max(-70.0, float(v)))
    return np.array(t), np.array(m)


couches = {"voix": "#d4202f", "musique": "#e0a43a", "ambiance": "#3a7d44", "effets": "#2b5fa8"}
mes = {k: momentane(os.path.join(work, "couches", k + ".wav")) for k in couches}
tm, mm = momentane(master)

# découpage en plans
segs, t = [], 0.0
for s in cfg["timeline"]:
    lab = s.get("sv") or {"froid": "ouverture", "accroche": "selfie", "ballon": "focus ballon",
                          "leone": "Leone", "fin": "fin"}.get(s["type"], s["type"])
    segs.append((t, t + s["dur"], lab, s["type"]))
    t += s["dur"]
# fusionne la séquence Leone
fus = []
for a in segs:
    if fus and a[3] == "leone" and fus[-1][3] == "leone":
        fus[-1] = (fus[-1][0], a[1], "Leone", "leone")
    else:
        fus.append(a)
segs = fus

fig, ax = plt.subplots(figsize=(16, 6.5), dpi=130)
fig.patch.set_facecolor("#14110f")
ax.set_facecolor("#1b1816")
for i, (a, b, lab, k) in enumerate(segs):
    if i % 2:
        ax.axvspan(a, b, color="#ffffff", alpha=0.035, lw=0)
    ax.axvline(a, color="#3a332e", lw=0.8)
    ax.text((a + b) / 2, -8.5, lab, rotation=90, ha="center", va="top", fontsize=8.5, color="#d8cfc3")
for k, col in couches.items():
    tt, m = mes[k]
    ax.plot(tt, m, color=col, lw=1.6, label=k, alpha=0.95)
ax.plot(tm, mm, color="#f3ece2", lw=2.4, label="master (après -14 LUFS)", alpha=0.9)
ax.axhline(-14, color="#f3ece2", ls=":", lw=1)
ax.text(t + 0.2, -14, "-14 LUFS\n(cible Instagram)", va="center", fontsize=8, color="#f3ece2")
ax.set_xlim(0, t)
ax.set_ylim(-60, -4)
ax.set_xlabel("temps du reel (s)", color="#d8cfc3")
ax.set_ylabel("volume perçu (LUFS momentané, 400 ms)", color="#d8cfc3")
ax.tick_params(colors="#a89f94")
for sp in ax.spines.values():
    sp.set_color("#3a332e")
leg = ax.legend(loc="lower left", ncol=5, frameon=False, fontsize=9)
for txt in leg.get_texts():
    txt.set_color("#f3ece2")
ax.set_title("Plan des niveaux — « Le rugby en savoyard »", color="#f3ece2", fontsize=13, loc="left")
fig.tight_layout()
png = os.path.join(work, "niveaux.png")
fig.savefig(png, facecolor=fig.get_facecolor())

# tableau : niveau moyen par plan et marge voix / fond (musique + ambiance)
def moyenne_lufs(tt, m, a, b, masque=None):
    sel = (tt >= a) & (tt < b)
    if masque is not None:
        sel &= masque
    v = m[sel]
    v = v[v > -69]
    return float(10 * np.log10(np.mean(10 ** (v / 10)))) if len(v) else None

tv, mv = mes["voix"]
lignes = ["plan                  début  voix  musique  ambiance  effets  master  marge voix/fond"]
for a, b, lab, k in segs:
    parle = mv > -40
    vals = [moyenne_lufs(*mes[c], a, b) for c in ("voix", "musique", "ambiance", "effets")]
    ms = moyenne_lufs(tm, mm, a, b)
    # fond pendant que la voix parle
    fond = []
    for c in ("musique", "ambiance"):
        tt, m = mes[c]
        n = min(len(tt), len(parle))
        x = moyenne_lufs(tt[:n], m[:n], a, b, parle[:n])
        if x is not None:
            fond.append(10 ** (x / 10))
    vv = moyenne_lufs(tv, mv, a, b, parle)
    marge = (vv - 10 * np.log10(sum(fond))) if (vv is not None and fond) else None
    f = lambda x: f"{x:6.1f}" if x is not None else "     —"
    lignes.append(f"{lab[:20]:20s} {a:6.1f} {f(vals[0])} {f(vals[1])}  {f(vals[2])}  {f(vals[3])} {f(ms)}   {f(marge)} dB")
open(os.path.join(work, "niveaux.txt"), "w", encoding="utf-8").write("\n".join(lignes) + "\n")
print("\n".join(lignes))
print("=>", png)
