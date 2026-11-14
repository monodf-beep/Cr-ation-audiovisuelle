#!/usr/bin/env python3
"""Construit prompteur.html à partir de montage.json : les répliques suivent
toujours le montage (aucun minutage tapé à la main)."""
import base64, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(os.path.join(HERE, "..", "montage.json"), encoding="utf-8"))
SILENCES = {"froid": "Ouverture : le stade et le commentateur. Silence.",
            "ballon": "Focus sur le ballon. Silence.",
            "leone": "Finale à la Leone. Silence total."}
cues, t = [], 0.0
tl = c["timeline"]
mots = [s for s in tl if s["type"] == "mot"]
for s in tl:
    t0, t1 = round(t, 3), round(t + s["dur"], 3)
    k = s["type"]
    if k in SILENCES:
        if cues and cues[-1].get("silence") and cues[-1]["text"] == SILENCES[k]:
            cues[-1]["t1"] = t1
        else:
            cues.append({"t0": t0, "t1": t1, "silence": True, "text": SILENCES[k]})
    elif k == "accroche":
        cues.append({"t0": t0, "t1": t1, "say": round(t0 + 0.05, 3),
                     "text": s.get("voix", "Turin. Et si on parlait rugby… en savoyard ?")})
    elif k == "mot":
        last = s is mots[-1]
        txt = ("Et pour finir… " + s["sv"][0].lower() + s["sv"][1:] + " !") if last else s["sv"]
        cues.append({"t0": t0, "t1": t1, "say": round(t0 + (0.25 if last else 0.55), 3), "text": txt, "fr": s["fr"]})
    elif k == "fin":
        cues.append({"t0": t0, "t1": t1, "say": round(t0 + 0.15, 3),
                     "text": s.get("voix", "Tu en connaissais combien ? Dis-le en commentaire !")})
    t += s["dur"]
src = open(os.path.join(HERE, "source.html"), encoding="utf-8").read()
font = base64.b64encode(open(os.path.join(HERE, "..", "polices", "Semplicita-Medium.otf"), "rb").read()).decode()
out = (src.replace("__CUES__", json.dumps(cues, ensure_ascii=False, indent=1))
          .replace("__TOTAL__", f"{t:.2f}").replace("__SEMPLICITA__", font))
open(os.path.join(HERE, "prompteur.html"), "w", encoding="utf-8").write(out)
print(f"{len(cues)} répliques, {t:.1f} s")
