#!/usr/bin/env python3
"""
Mise en page d'un plan : ecran divise, bandes empilees, visage en incrustation.

Les regles de choix (quand utiliser quoi) sont dans
.claude/skills/montage-mise-en-page/SKILL.md. Ce script ne fait que construire.

Trois dispositions :

  divise A.mp4 B.mp4        deux sources cote a cote (16:9) ou l'une sur l'autre (9:16)
                            ex. avant / apres, deux interlocuteurs, la personne et ce dont elle parle
  pile S1.mp4 [S2.mp4 ...]  2 a 4 bandes empilees, chacune avec son etiquette
                            ex. « TOFU / MOFU / BOFU » : la meme prise repetee, trois niveaux compares
                            une seule source + --decalages : la meme video, decalee dans chaque bande
  incrustation FOND VISAGE  le visage en petit dans un coin, sur l'ecran ou le plan de coupe

Les textes sont poses dans la zone sure des reseaux : en 9:16, rien dans les
250 px du haut, les 420 px du bas (nom du compte, legende) ni les 140 px de
droite (boutons). Une etiquette qui tomberait dessous est remontee.

Exemples :
  python3 04_montage/disposition.py pile prise.mp4 --etiquettes TOFU MOFU BOFU \\
      --sous "10 000 vues" "1 000 vues" "100 vues" --decalages 0 4 8 -o pile.mp4
  python3 04_montage/disposition.py incrustation ecran.mp4 visage.mp4 --coin bd --forme ronde -o pip.mp4
  python3 04_montage/disposition.py divise avant.mp4 apres.mp4 --etiquettes Avant Après -o divise.mp4
"""

import argparse
import os
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outils_video import FORMATS, etiquette, ffmpeg_bin, lancer, sonder  # noqa: E402

ZONE_SURE_916 = {"haut": 250, "bas": 420, "droite": 140}


def couvrir(w, h, cadrage=0.5):
    """Remplit une case w x h sans deformer : agrandit puis recadre. cadrage : 0 = haut, 1 = bas."""
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}:(iw-{w})/2:(ih-{h})*{cadrage},setsar=1")


def zone_sure(fmt, y, h_elem, H):
    if fmt != "9:16":
        return y
    return max(ZONE_SURE_916["haut"], min(y, H - ZONE_SURE_916["bas"] - h_elem))


def entrees_images(pngs):
    args = []
    for p in pngs:
        args += ["-loop", "1", "-i", p]
    return args


def cmd_divise(a, tmp):
    W, H = FORMATS[a.format]
    vertical = a.sens == "v" or (a.sens == "auto" and H > W)
    cw, ch = (W, H // 2) if vertical else (W // 2, H)
    d = [sonder(s)["duree"] for s in a.sources]
    duree = min(d)
    fc = [f"[0:v]{couvrir(cw, ch, a.cadrage)}[c0]", f"[1:v]{couvrir(cw, ch, a.cadrage)}[c1]",
          f"[c0][c1]{'vstack' if vertical else 'hstack'}=inputs=2[v0]"]
    pngs, poses = [], []
    for i, t in enumerate(a.etiquettes or []):
        im = etiquette(t, int(W * 0.05), fond=a.fond, encre=a.encre)
        p = os.path.join(tmp, f"e{i}.png"); im.save(p); pngs.append(p)
        x = int(W * 0.05) + (0 if vertical else i * cw)
        y = (i * ch if vertical else 0) + int(ch * 0.12)
        y = zone_sure(a.format, y, im.height, H)
        poses.append((x, y))
    last = "v0"
    for i, (x, y) in enumerate(poses):
        fc.append(f"[{last}][{2 + i}:v]overlay={x}:{y}[v{i + 1}]"); last = f"v{i + 1}"
    son = ["-map", f"{a.son - 1}:a?"]
    return ["-i", a.sources[0], "-i", a.sources[1]] + entrees_images(pngs), fc, last, son, duree


def cmd_pile(a, tmp):
    W, H = FORMATS[a.format]
    n = max(len(a.sources), len(a.etiquettes or []), len(a.decalages or []))
    if not 2 <= n <= 4:
        raise SystemExit("pile : 2 a 4 bandes.")
    srcs = [a.sources[min(i, len(a.sources) - 1)] for i in range(n)]
    decal = [(a.decalages[i] if a.decalages and i < len(a.decalages) else 0.0) for i in range(n)]
    duree = min(sonder(s)["duree"] - d for s, d in zip(srcs, decal))
    bh = H // n
    entrees, fc = [], []
    for i, (s, d) in enumerate(zip(srcs, decal)):
        entrees += (["-ss", str(d)] if d else []) + ["-i", s]
        fc.append(f"[{i}:v]{couvrir(W, bh, a.cadrage)}[b{i}]")
    fc.append("".join(f"[b{i}]" for i in range(n)) + f"vstack=inputs={n}[v0]")
    pngs, poses = [], []
    for i in range(n):
        t = (a.etiquettes or [None] * n)[i] if a.etiquettes and i < len(a.etiquettes) else None
        s = a.sous[i] if a.sous and i < len(a.sous) else None
        if not t and not s:
            continue
        blocs = []
        if t:
            blocs.append(etiquette(t, int(W * 0.085), fond=a.fond, encre=a.encre))
        if s:
            blocs.append(etiquette(s, int(W * 0.034), fond="noir", encre="blanc"))
        gw = max(b.width for b in blocs); gh = sum(b.height for b in blocs) + 12 * (len(blocs) - 1)
        g = Image.new("RGBA", (gw, gh), (0, 0, 0, 0)); yy = 0
        for b in blocs:
            g.paste(b, ((gw - b.width) // 2, yy), b); yy += b.height + 12
        p = os.path.join(tmp, f"e{i}.png"); g.save(p); pngs.append(p)
        y = i * bh + (bh - gh) // 2
        y = zone_sure(a.format, y, gh, H)
        if y < i * bh or y + gh > (i + 1) * bh:
            print(f"  bande {i + 1} : etiquette deplacee pour rester hors de l'interface du reseau", file=sys.stderr)
        poses.append((int(W * 0.06), y))
    last = "v0"
    for k, (x, y) in enumerate(poses):
        fc.append(f"[{last}][{n + k}:v]overlay={x}:{y}[v{k + 1}]"); last = f"v{k + 1}"
    son = ["-map", f"{a.son - 1}:a?"]
    return entrees + entrees_images(pngs), fc, last, son, duree


def masque_forme(w, h, forme, bord, tmp):
    m = Image.new("L", (w, h), 0); d = ImageDraw.Draw(m)
    if forme == "ronde":
        d.ellipse([0, 0, w - 1, h - 1], fill=255)
    else:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(min(w, h) * 0.12), fill=255)
    pm = os.path.join(tmp, "masque.png"); m.save(pm)
    cadre = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(cadre)
    if bord:
        if forme == "ronde":
            d.ellipse([0, 0, w - 1, h - 1], outline=(255, 255, 255, 255), width=bord)
        else:
            d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(min(w, h) * 0.12), outline=(255, 255, 255, 255), width=bord)
    pc = os.path.join(tmp, "cadre.png"); cadre.save(pc)
    return pm, pc


def cmd_incrustation(a, tmp):
    W, H = FORMATS[a.format]
    fond, visage = a.sources[0], a.sources[1]
    duree = min(sonder(fond)["duree"], sonder(visage)["duree"])
    pw = int(W * a.taille) // 2 * 2
    ph = pw if a.forme == "ronde" else int(pw * 4 / 3) // 2 * 2
    marge = int(W * 0.04)
    x = marge if a.coin in ("bg", "hg") else W - pw - marge - (ZONE_SURE_916["droite"] if a.format == "9:16" else 0)
    y = marge if a.coin in ("hg", "hd") else H - ph - marge
    y = zone_sure(a.format, y, ph, H)
    pm, pc = masque_forme(pw, ph, a.forme, max(2, W // 270), tmp)
    fc = [f"[0:v]{couvrir(W, H, 0.5)}[f]",
          f"[1:v]{couvrir(pw, ph, a.cadrage)},format=rgba[vi]",
          "[2:v]format=gray[mq]",
          "[vi][mq]alphamerge[vr]",
          f"[f][vr]overlay={x}:{y}[v1]",
          f"[v1][3:v]overlay={x}:{y}[v2]"]
    son = ["-map", f"{a.son - 1}:a?"]
    return ["-i", fond, "-i", visage] + entrees_images([pm, pc]), fc, "v2", son, duree


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["divise", "pile", "incrustation"])
    ap.add_argument("sources", nargs="+")
    ap.add_argument("-o", "--sortie", required=True)
    ap.add_argument("--format", default="9:16", choices=list(FORMATS))
    ap.add_argument("--etiquettes", nargs="*")
    ap.add_argument("--sous", nargs="*", help="pile : ligne sous chaque etiquette (ex. un chiffre)")
    ap.add_argument("--decalages", nargs="*", type=float, help="pile : secondes de decalage par bande")
    ap.add_argument("--sens", default="auto", choices=["auto", "h", "v"], help="divise : cote a cote (h) ou l'un sur l'autre (v)")
    ap.add_argument("--cadrage", type=float, default=0.35, help="0 = garder le haut de l'image, 0.5 = centre ; 0.35 garde le visage")
    ap.add_argument("--coin", default="bd", choices=["bd", "bg", "hd", "hg"], help="incrustation : bas-droite, bas-gauche, haut-droite, haut-gauche")
    ap.add_argument("--taille", type=float, default=0.30, help="incrustation : largeur du visage, en part de la largeur")
    ap.add_argument("--forme", default="ronde", choices=["ronde", "arrondie"])
    ap.add_argument("--son", type=int, default=1, help="numero de la source dont on garde le son (une seule piste)")
    ap.add_argument("--fond", default="rose", help="couleur du bloc d'etiquette (hex ou blanc, noir, rouge, rose, creme, marine)")
    ap.add_argument("--encre", default="noir")
    a = ap.parse_args()
    if a.mode == "incrustation" and a.son == 1:
        a.son = 2  # par defaut on entend la personne, pas l'ecran
    with tempfile.TemporaryDirectory() as tmp:
        entrees, fc, last, son, duree = {"divise": cmd_divise, "pile": cmd_pile, "incrustation": cmd_incrustation}[a.mode](a, tmp)
        cmd = [ffmpeg_bin(), "-y", "-hide_banner"] + entrees + [
            "-filter_complex", ";".join(fc), "-map", f"[{last}]"] + son + [
            "-t", f"{duree:.3f}", "-r", "25", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", a.sortie]
        lancer(cmd)
    print(f"-> {a.sortie} ({a.mode}, {a.format}, {duree:.1f} s)")


if __name__ == "__main__":
    main()
