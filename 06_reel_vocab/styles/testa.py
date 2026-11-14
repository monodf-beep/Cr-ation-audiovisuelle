#!/usr/bin/env python3
"""
Style « Armando Testa / Carosello » (graphisme turinois minimal) — CPU local.

Références : Armando Testa (Punt e Mes, Lavazza, Pippo l'hippopotame),
l'animation du Carosello (Cavandoli « La Linea », Bozzetto) : simplification
radicale, aplats purs, un fond d'UNE seule couleur saturée, beaucoup de vide.

Principe
  1. carte d'étiquettes STABLE (Stylizer de ../stylize.py : flot optique,
     hystérésis, palette figée par plan, visages YuNet) + segmentation des
     joueurs MediaPipe (repris de ligne_claire.py, non modifiés)
  2. réduction à ~11 classes graphiques : fond, pelouse, azur, vert SB, or,
     blanc, sombre, 3 chairs plates, rouge
  3. décor : tout ce qui n'est ni joueur ni pelouse -> UN aplat saturé
     (jaune Testa, ou rouge si l'or sud-africain domine) ; la pelouse devient
     une bande plate limitée par une droite (lissée dans le temps)
  4. formes arrondies : cartes de classes floutées (lissage temporel par flot
     optique) puis argmax en pleine résolution -> silhouettes « galets »
  5. têtes = disques couleur chair, sans aucun trait ; un seul trait noir
     franc autour des silhouettes, lignes du terrain en blanc

Usage : python3 testa.py ENTREE SORTIE [--start S --dur D]
Import : from testa import Style ; st = Style() ; out = st(rgb) ; st.reset()
"""
import argparse
import os
import subprocess
import sys
import time

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.dirname(ICI))
import stylize as B  # noqa: E402
import ligne_claire as LC  # noqa: E402  (segmentation joueurs + nettoyage des tenues)

# --- Palette Testa / Carosello (RVB) -----------------------------------------
GIALLO = (250, 196, 0)          # jaune Testa (fond par défaut)
ROSSO = (222, 46, 38)           # rouge Punt e Mes (fond si beaucoup d'or)
PRATO = (92, 172, 74)           # bande de pelouse, vert franc
NERO = (24, 22, 26)             # trait unique
BIANCO = (252, 250, 242)
CLASSES = [                     # (nom, RVB)
    ("fond", GIALLO), ("prato", PRATO),
    ("azzurro", (24, 108, 214)), ("verde", (6, 98, 62)), ("oro", (252, 186, 18)),
    ("bianco", BIANCO), ("scuro", (34, 32, 44)),
    ("pelle1", (240, 196, 158)), ("pelle2", (196, 132, 90)), ("pelle3", (120, 76, 52)),
    ("rosso", (200, 30, 40)),
]
K = len(CLASSES)
C_FOND, C_PRATO, C_AZ, C_VE, C_OR, C_BI, C_SC, C_P1, C_P2, C_P3, C_RO = range(K)
PELLI = (C_P1, C_P2, C_P3)


class Style(LC.Style):
    """Stylisation Testa / Carosello avec mémoire temporelle (vidéo)."""

    def __init__(self, epaisseur=6.0, temporel=True, cote=540, arrondi=2.2):
        self.arrondi = arrondi          # rayon de « galet » (px à la résolution de calcul)
        self.temporel = temporel
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
        super().__init__(epaisseur=epaisseur, temporel=temporel, cote=cote)

    def reset(self):
        super().reset()
        self._map = None                # palette de base -> classe Testa
        self._soft = None               # cartes de classes du plan précédent
        self._gris = None
        self._droite = None             # bord haut de la pelouse (a, b) : y = a x + b
        self._fond = None               # couleur de fond figée pour le plan
        self._rayon = None              # rayon d'arrondi figé pour le plan

    # -- correspondance palette de base -> classes Testa (cachée par palette)
    def _classes(self):
        b = self.base
        if self._map is not None and self._map[0] is b.palette and len(self._map[1]) == len(b.palette):
            return self._map[1]
        lab = b.palette
        n = len(lab)
        ref = B._lab([c for _, c in CLASSES])
        cand = np.array([C_AZ, C_VE, C_OR, C_BI, C_SC, C_P1, C_P2, C_P3, C_RO])
        wl = np.array([0.7, 1, 1], np.float32)
        m = np.empty(n, np.int32)
        for i in range(n):
            d = np.linalg.norm((ref[cand] - lab[i]) * wl, axis=1)
            m[i] = cand[np.argmin(d)]
        fixes = {B.I_AZ: C_AZ, B.I_AZO: C_AZ, B.I_SB: C_VE, B.I_SBO: C_VE, B.I_OR: C_OR,
                 B.I_ORO: C_OR, B.I_BLANC: C_BI, 8: C_BI, 9: C_SC, 10: C_SC, 16: C_RO, 17: C_RO,
                 B.I_PEL: C_PRATO}
        for i, c in fixes.items():
            m[i] = c
        # chairs : 3 tons plats selon la clarté (peaux de base + tons de visage ajoutés)
        for i in list(B.PEAUX) + list(range(b.n_normal + B.N_FOULE, n)):
            Lv = lab[i, 0]
            m[i] = C_P1 if Lv > 66 else (C_P2 if Lv > 44 else C_P3)
        for i in b.i_foule:
            m[i] = C_FOND
        self._map = (b.palette, m)
        return m

    # -- bord haut de la pelouse : une droite robuste, lissée dans le temps
    def _bande(self, pel, w, h):
        if pel.mean() < 0.12:
            return None
        cols = np.arange(0, w, 4)
        f = cv2.blur(pel.astype(np.float32), (1, max(3, h // 30)))
        ys, xs = [], []
        for c in cols:
            idx = np.nonzero(f[:, c] > 0.7)[0]
            if len(idx):
                ys.append(idx[0])
                xs.append(c)
        if len(xs) < len(cols) * 0.4:
            return self._droite
        xs, ys = np.array(xs, np.float32), np.array(ys, np.float32)
        a, b = np.polyfit(xs, ys, 1)
        for _ in range(2):              # rejet des colonnes aberrantes (joueurs, poteaux)
            r = np.abs(ys - (a * xs + b))
            ok = r < max(3.0, 2.0 * np.median(r))
            if ok.sum() > 10:
                a, b = np.polyfit(xs[ok], ys[ok], 1)
        if self._droite is not None:
            a = 0.8 * self._droite[0] + 0.2 * a
            b = 0.8 * self._droite[1] + 0.2 * b
        self._droite = (float(a), float(b))
        return self._droite

    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        pal_avant = self.base.palette
        sortie_base = self.base(rgb)
        if pal_avant is not None and self.base.palette is not pal_avant \
                and len(self.base.palette) <= self.base.n_normal + B.N_FOULE:
            self.reset_plan()
        etiq = self.base.prev["etiq"].copy()
        h, w = etiq.shape
        k = min(h, w) / 540.0
        prob = self.pers(rgb, w, h)
        pers = np.zeros((h, w), bool)
        if prob is not None:
            etiq, pers = self._joueurs(rgb, etiq, prob)
        self._prev_e = etiq
        cl = self._classes()[etiq]

        # figures = joueurs (segmentation) + îlots non-pelouse entourés de pelouse
        pel = cl == C_PRATO
        autre = (~pel & (cl != C_FOND)).astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(autre, connectivity=8)
        fig = np.zeros(n, bool)
        if n > 1:
            anneau = cv2.dilate(cc.astype(np.float32), B._disque(7 * k)).astype(np.int32)
            ring = (anneau > 0) & (cc == 0)
            tot = np.bincount(anneau[ring], minlength=n)
            vert = np.bincount(anneau[ring & pel], minlength=n)
            surp = np.bincount(cc[pers], minlength=n)
            fig = ((vert > 0.55 * np.maximum(tot, 1)) & (st[:, cv2.CC_STAT_AREA] < 0.06 * w * h)) \
                | (surp > 0.3 * st[:, cv2.CC_STAT_AREA])
            fig[0] = False
        # miettes (touffes, reflets) : écartées sauf si la segmentation y voit un joueur
        fig &= (st[:, cv2.CC_STAT_AREA] > 0.0003 * w * h) | (surp > 0) if n > 1 else fig
        figure = fig[cc] | (pers & (cl != C_PRATO) & (cl != C_FOND))
        # chair : un seul ton plat par zone de peau (pas d'ombres = pas de traits)
        n2, cc2 = cv2.connectedComponents(np.isin(cl, PELLI).astype(np.uint8), connectivity=8)
        if n2 > 1:
            cpt = np.stack([np.bincount(cc2[cl == t], minlength=n2) for t in PELLI], 1)
            maj = np.array(PELLI)[np.argmax(cpt, 1)]
            m = cc2 > 0
            cl[m] = maj[cc2[m]]
        # dans une personne, le « fond » restant prend une couleur de tenue sombre
        cl[pers & (cl == C_FOND)] = C_SC

        # décor : bande de pelouse sous une droite, aplat uni au-dessus
        droite = self._bande(pel, w, h)
        if droite is None:              # gros plan : pas de pelouse, tout le décor en aplat
            bande = np.zeros((h, w), bool)
        else:
            yy = np.arange(h, dtype=np.float32)[:, None]
            xx = np.arange(w, dtype=np.float32)[None]
            bande = yy >= droite[0] * xx + droite[1]
        cl = np.where(figure, cl, np.where(bande, C_PRATO, C_FOND))

        # têtes : disques chair pleins (aucun trait de visage)
        for p in self.base.visages.pistes:
            cx, cy, bw, bh = p["c"]
            r = int(0.56 * max(bw, bh))
            if r < 2:
                continue
            disque = np.zeros((h, w), np.uint8)
            cv2.circle(disque, (int(cx), int(cy - 0.04 * bh)), r, 1, -1)
            d = disque > 0
            if (figure[d] | pers[d]).mean() < 0.5:   # visage du public : ignoré
                continue
            v = cl[d]
            v = v[np.isin(v, PELLI)]
            ton = int(np.bincount(v).argmax()) if len(v) else C_P2
            cl[d] = ton
            figure |= d

        # couleur de fond figée pour le plan : rouge si l'or domine, sinon jaune
        if self._fond is None:
            nf = max(1, int(figure.sum()))
            self._fond = ROSSO if (cl[figure] == C_OR).sum() > 0.10 * nf else GIALLO

        # formes arrondies : one-hot flouté, recalé par flot optique, mélangé
        soft = np.eye(K, dtype=np.float32)[cl]
        soft[..., 2:] *= 1.25           # les petites figures résistent au flou
        # gros plan -> formes plus grosses et plus rondes (rayon figé pour le plan)
        if self._rayon is None:
            self._rayon = self.arrondi * k * (1.0 + 1.6 * min(0.6, float(figure.mean())))
        soft = cv2.GaussianBlur(soft, (0, 0), self._rayon)
        gris = cv2.cvtColor(cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        if self.temporel and self._soft is not None and self._soft.shape == soft.shape:
            fl = self.dis.calc(gris, self._gris, None)
            gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
            avant = cv2.remap(self._soft, gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
            soft = 0.55 * soft + 0.45 * avant
        self._soft, self._gris = soft, gris

        # rendu pleine résolution : argmax des cartes agrandies (contours lisses)
        grand = cv2.resize(soft, (W, H), interpolation=cv2.INTER_LINEAR) if (h, w) != (H, W) else soft
        lab_f = np.argmax(grand, axis=2).astype(np.uint8)
        couleurs = np.array([c for _, c in CLASSES], np.uint8)
        couleurs[C_FOND] = self._fond
        out = couleurs[lab_f]

        # lignes du terrain (rendu de base) en blanc, seulement sur la bande
        pb = cv2.resize((self.base.prev["etiq"] == B.I_PEL).astype(np.uint8), (W, H),
                        interpolation=cv2.INTER_NEAREST)
        pr = ((lab_f == C_PRATO) & (pb > 0)).astype(np.float32)
        a_l = np.clip((sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20)
                      / (B.BLANC[0] - B.PELOUSE[0] - 40), 0, 1)
        f = min(W, H) / 1080.0
        a_l = cv2.dilate(a_l, B._disque(3 * f + 2))
        a_l = np.clip(cv2.GaussianBlur(a_l, (0, 0), 1.2 * f) * 1.6 - 0.3, 0, 1) * pr

        # un seul trait franc : le pourtour des silhouettes
        fg = (lab_f >= 2).astype(np.uint8)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, B._disque(3 * f + 2))
        dt = cv2.distanceTransform(fg, cv2.DIST_L2, 5)
        t = np.clip(self.epaisseur * f + 0.5 - dt, 0, 1) * (fg > 0)

        for a, c in ((a_l, BIANCO), (t.astype(np.float32), NERO)):
            a = np.ascontiguousarray(a, np.float32)
            plein = np.empty_like(out)
            plein[:] = c
            out = cv2.blendLinear(plein, out, a, 1.0 - a)
        return cv2.GaussianBlur(out, (0, 0), 0.6 * max(1.0, f))   # anticrénelage léger

    def reset_plan(self):
        """Changement de plan détecté par le Stylizer : on oublie l'état propre au plan."""
        self.pers.reset()
        self._prev_e = None
        self._soft = self._gris = self._droite = self._fond = self._rayon = None
        self._map = None


# --- Entrées / sorties ----------------------------------------------------------
def traiter_video(src, dst, start=0.0, dur=None, log=True):
    w, h, fps = LC._infos(src)
    cin = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", src]
    if dur:
        cin += ["-t", str(dur)]
    cin += ["-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    cout = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
            "-r", fps, "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", dst]
    pin = subprocess.Popen(cin, stdout=subprocess.PIPE)
    pout = subprocess.Popen(cout, stdin=subprocess.PIPE)
    st, n, t0, taille = Style(), 0, time.time(), w * h * 3
    while True:
        buf = pin.stdout.read(taille)
        if len(buf) < taille:
            break
        pout.stdin.write(st(np.frombuffer(buf, np.uint8).reshape(h, w, 3)).tobytes())
        n += 1
        if log and n % 15 == 0:
            print(f"\r{n} images, {(time.time() - t0) / n:.2f} s/image", end="", file=sys.stderr)
    pin.wait()
    pout.stdin.close()
    pout.wait()
    if log:
        print(f"\r{n} images, {(time.time() - t0) / max(n, 1):.2f} s/image -> {dst}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Style Armando Testa / Carosello")
    ap.add_argument("entree")
    ap.add_argument("sortie")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    a = ap.parse_args()
    if os.path.splitext(a.entree)[1].lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        img = cv2.imread(a.entree, cv2.IMREAD_COLOR)[..., ::-1].copy()
        out = Style(temporel=False)(img)
        cv2.imwrite(a.sortie, out[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 93])
    else:
        traiter_video(a.entree, a.sortie, a.start, a.dur)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)                        # évite le bruit de fermeture de MediaPipe


if __name__ == "__main__":
    main()
