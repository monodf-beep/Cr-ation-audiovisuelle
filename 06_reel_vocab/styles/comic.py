#!/usr/bin/env python3
"""
Style « comic pop / Spider-Verse » pour les plans de rugby — CPU local.

Principe
  1. le Stylizer de ../stylize.py fournit une carte d'étiquettes de couleur
     STABLE dans le temps (flot optique, hystérésis, palette figée par plan,
     visages YuNet aplatis, pelouse/foule/lignes) + une image Lab lissée
     et recalée temporellement
  2. segmentation MediaPipe « selfie multiclass » (si disponible) : tenues
     ramenées aux couleurs d'équipe, peau/visage en un seul aplat chair
  3. rendu comic :
     - aplats francs et saturés (les tons d'ombre sont fusionnés)
     - ombres en trame Ben-Day : points sur une grille FIXE à l'écran (pas de
       scintillement), rayon proportionnel à l'ombre (lissée dans le temps)
     - encre noire d'épaisseur variable : silhouettes des joueurs épaisses,
       détails fins, trait plus gras côté ombre
     - léger décalage d'impression des couleurs par rapport à l'encre
     - décor simplifié : tribunes en 2 tons + trame claire + traits de vitesse
  4. visages : aplat chair, aucune trame ni détail (ni yeux, ni bouche, ni barbe)

Usage : python3 comic.py ENTREE SORTIE [--start S --dur D]
        (image -> image, vidéo -> vidéo même taille/cadence, sans son)
Import : from comic import Style ; st = Style() ; out = st(rgb)   # RVB uint8
         st.reset() entre deux plans.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
import stylize as B  # noqa: E402  (Stylizer de base, non modifié)

MODELE_SEG = os.path.join(os.path.dirname(ICI), "modeles", "selfie_multiclass_256x256.tflite")

# --- Palette comic (RVB) -------------------------------------------------------
ENCRE = (16, 14, 26)            # encre (noir légèrement bleuté)
PAPIER = (252, 248, 236)        # blanc papier
PELOUSE_C = (96, 184, 72)       # vert pelouse pop
AZUR_C = (22, 118, 232)         # Italie
SB_VERT_C = (10, 122, 74)       # Springbok
OR_C = (255, 196, 26)
FOULE_C = [(64, 70, 138), (150, 104, 196)]   # tribunes : indigo / violet pop (2 tons)
DECALAGE = (5, 3)               # décalage d'impression des couleurs (px à 1080)
PAS_TRAME = 13                  # pas de la trame Ben-Day (px à 1080)

KIT = [B.I_AZ, B.I_AZO, B.I_SB, B.I_SBO, B.I_OR, B.I_ORO, B.I_BLANC, 8, 9, 10, 16, 17]
OMBRES = {B.I_AZO: B.I_AZ, B.I_SBO: B.I_SB, B.I_ORO: B.I_OR}


def _lab1(rgb):
    return B._lab([rgb])[0]


class _Personnes:
    """Segmentation MediaPipe (fond, cheveux, peau corps, peau visage, vêtements,
    accessoires) sur tuiles carrées, lissée dans le temps."""

    def __init__(self):
        self.seg = None
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
            self.mp = mp
            opt = vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=MODELE_SEG),
                                               output_confidence_masks=True)
            self.seg = vision.ImageSegmenter.create_from_options(opt)
        except Exception as ex:  # sans MediaPipe : Stylizer de base seul
            print(f"! segmentation indisponible ({ex})", file=sys.stderr)
        self.reset()

    def reset(self):
        self.prev = None

    def __call__(self, rgb, w, h):
        if self.seg is None:
            return None
        H, W = rgb.shape[:2]
        c = min(H, W)
        n = max(1, int(np.ceil(max(H, W) / c - 0.05)) + (1 if max(H, W) > 1.2 * c else 0))
        acc = np.zeros((h, w, 6), np.float32)
        cnt = np.zeros((h, w, 1), np.float32)
        for i in range(n):
            o = 0 if n == 1 else round(i * (max(H, W) - c) / (n - 1))
            tuile = rgb[o:o + c] if H >= W else rgb[:, o:o + c]
            t = np.ascontiguousarray(cv2.resize(tuile, (256, 256), interpolation=cv2.INTER_AREA))
            r = self.seg.segment(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=t))
            m = np.stack([cm.numpy_view().reshape(256, 256) for cm in r.confidence_masks], -1)
            s = w / W
            o2, c2 = round(o * s), round(c * s)
            if H >= W:
                o2 = min(o2, h - c2)
                acc[o2:o2 + c2] += cv2.resize(m, (w, c2), interpolation=cv2.INTER_LINEAR)
                cnt[o2:o2 + c2] += 1
            else:
                o2 = min(o2, w - c2)
                acc[:, o2:o2 + c2] += cv2.resize(m, (c2, h), interpolation=cv2.INTER_LINEAR)
                cnt[:, o2:o2 + c2] += 1
        p = acc / np.maximum(cnt, 1)
        if self.prev is not None and self.prev.shape == p.shape:
            p = 0.55 * p + 0.45 * self.prev
        self.prev = p
        return p


def _grille(H, W, pas):
    """Distance (en fraction du pas) au centre de point le plus proche,
    grille tournée de 45° et FIXE à l'écran."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (x + y) / (pas * 1.4142)
    v = (x - y) / (pas * 1.4142)
    du = u - np.round(u)
    dv = v - np.round(v)
    return np.sqrt(du * du + dv * dv).astype(np.float32)


class Style:
    """Stylisation comic pop avec mémoire temporelle (vidéo).

    epaisseur : épaisseur de base de l'encre (px pour 1080 de large)
    temporel  : False pour une image isolée
    """

    def __init__(self, epaisseur=3.0, temporel=True, cote=540, vitesse=True):
        self.epaisseur = epaisseur
        self.vitesse = vitesse
        self.base = B.Stylizer(cote=cote, temporel=temporel)
        self.pers = _Personnes()
        self._grilles = {}
        self.reset()

    def reset(self):
        self.base.reset()
        self.pers.reset()
        self._cache = None
        self._prev_e = None
        self._prev_omb = None

    # -- palette comic (recalculée seulement si la palette de base change) ----------
    def _table(self):
        b = self.base
        n = len(b.palette)
        if self._cache is not None and self._cache[0] == n and self._cache[3] is b.palette:
            return self._cache[1], self._cache[2], self._cache[4]
        lab = b.palette
        lc = lab.copy()
        lc[:, 0] = 14 + 0.86 * lab[:, 0]           # noirs relevés (l'encre reste le noir)
        lc[:, 1:] = lab[:, 1:] * 1.2                # couleurs pop
        fixes = {B.I_AZ: AZUR_C, B.I_AZO: AZUR_C, B.I_SB: SB_VERT_C, B.I_SBO: SB_VERT_C,
                 B.I_OR: OR_C, B.I_ORO: OR_C, B.I_BLANC: PAPIER, B.I_PEL: PELOUSE_C}
        for i, c in fixes.items():
            lc[i] = _lab1(c)
        for i in list(B.PEAUX) + list(range(b.n_normal + B.N_FOULE, n)):   # chairs
            lc[i, 0] = np.clip(lab[i, 0] + 8, 42, 84)
            lc[i, 1:] = lab[i, 1:] * 1.1
        foule = set(int(i) for i in b.i_foule)
        for r, i in enumerate(sorted(foule, key=lambda j: lab[j, 0])):
            lc[i] = _lab1(FOULE_C[0 if r < 2 else 1])
        # fusion des couleurs voisines (ΔE < 10) -> moins de taches, moins de traits
        rep = np.arange(n)
        for i, j in OMBRES.items():
            rep[i] = j
        prot = {B.I_AZ, B.I_SB, B.I_OR, B.I_PEL, B.I_BLANC}
        ordre = sorted(range(n), key=lambda i: (i not in prot, i))
        reps = []
        for i in ordre:
            if i in foule or i in OMBRES:
                continue
            for j in reps:
                if np.linalg.norm(lc[i] - lc[j]) < 10 and not (i in prot and j in prot):
                    rep[i] = j
                    break
            else:
                reps.append(i)
        for i in foule:
            rep[i] = min(j for j in foule if np.allclose(lc[j], lc[i]))
        rgb = B._rgb_of_lab(lc)
        self._cache = (n, rep, rgb, b.palette, foule)
        return rep, rgb, foule

    # -- joueurs : corrige les étiquettes là où la segmentation voit une personne -----
    def _joueurs(self, rgb, etiq, prob):
        b = self.base
        h, w = etiq.shape
        petit = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
        lisse = cv2.bilateralFilter(cv2.bilateralFilter(petit, 7, 30, 5), 7, 30, 5)
        lab = cv2.cvtColor(lisse.astype(np.float32) / 255.0, cv2.COLOR_RGB2Lab)
        cl = np.argmax(prob, axis=2)
        pers = (1.0 - prob[..., 0]) > 0.5
        pers = cv2.morphologyEx(pers.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        vide = np.zeros((h, w), bool)
        if pers.sum() < 0.002 * w * h:
            return etiq, vide, vide
        pal = b.palette
        wl = np.array([0.6, 1, 1], np.float32)

        def proche(idx, m):
            idx = np.asarray(idx)
            X = lab[m] * wl
            C = pal[idx] * wl
            d = (X * X).sum(1)[:, None] - 2 * X @ C.T + (C * C).sum(1)[None]
            return idx[np.argmin(d, axis=1)]

        e = etiq.copy()
        foule = np.isin(e, b.i_foule)
        habit = pers & np.isin(cl, (4, 5, 0))
        e[habit] = proche(KIT, habit)
        hsv = cv2.cvtColor(petit, cv2.COLOR_RGB2HSV)
        Hh, Ss, Vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        azur = habit & (Hh >= 97) & (Hh <= 122) & (Ss > 90) & (Vv > 70)
        sbv = habit & (Ss > 60) & (Vv > 18) & (Hh >= 35) & (Hh <= 90) & (Vv < 170)
        orr = habit & (Hh >= 15) & (Hh <= 32) & (Ss > 100) & (Vv > 110)
        e[azur], e[sbv], e[orr] = B.I_AZ, B.I_SB, B.I_OR
        norm = [i for i in range(b.n_normal) if i not in (B.I_PEL, B.I_AZ, B.I_AZO, B.I_SB, B.I_SBO)]
        chev = pers & (cl == 1)
        e[chev] = proche(norm, chev)
        reste = pers & foule & ~habit & ~chev
        if reste.any():
            e[reste] = proche(norm, reste)
        # peau : un ton chair par zone ; trous du visage (yeux, bouche, barbe) bouchés
        peau = pers & np.isin(cl, (2, 3))
        visage = (cl == 3) & pers
        n, cc, st, _ = cv2.connectedComponentsWithStats(1 - visage.astype(np.uint8), connectivity=4)
        bordure = np.zeros(n, bool)
        bordure[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
        trou = ~bordure & (st[:, cv2.CC_STAT_AREA] < 0.01 * w * h)
        trou[0] = False
        visage |= trou[cc]
        visage = cv2.morphologyEx(visage.astype(np.uint8), cv2.MORPH_CLOSE, B._disque(7)) > 0
        peau |= visage
        n, cc = cv2.connectedComponents(peau.astype(np.uint8), connectivity=8)
        tons = np.array(B.PEAUX)
        for i in range(1, n):
            m = cc == i
            if m.sum() < 6:
                continue
            med = np.median(lab[m], axis=0)
            d = np.linalg.norm((pal[tons] - med) * wl, axis=1)
            t = int(tons[np.argmin(d)])
            if self._prev_e is not None and self._prev_e.shape == e.shape:   # hystérésis
                pv = self._prev_e[m]
                pv = pv[np.isin(pv, tons)]
                if len(pv):
                    t0 = int(np.bincount(pv).argmax())
                    if d[list(tons).index(t0)] < d.min() + 12:
                        t = t0
            e[m] = t
        e2 = B.Stylizer._mode(e, 5)
        e = np.where(pers & ~peau, e2, e)
        return e, pers, visage

    def _grille(self, H, W):
        pas = max(5.0, PAS_TRAME * min(H, W) / 1080.0)
        cle = (H, W)
        if cle not in self._grilles:
            g = _grille(H, W, pas)
            # traits de vitesse : segments horizontaux fixes (motif pseudo-aléatoire figé)
            rng = np.random.default_rng(7)
            vit = np.zeros((H, W), np.float32)
            f = min(H, W) / 1080.0
            for _ in range(int(40 * max(H, W) / 1920 + 10)):
                y = int(rng.uniform(0, H))
                x0 = int(rng.uniform(-0.2, 0.9) * W)
                lg = int(rng.uniform(0.15, 0.5) * W)
                cv2.line(vit, (x0, y), (x0 + lg, y), 1.0, max(1, int(round(2.2 * f))), cv2.LINE_AA)
            self._grilles[cle] = (g, vit, pas)
        return self._grilles[cle]

    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        b = self.base
        sortie_base = b(rgb)                      # met à jour l'état temporel
        etiq = b.prev["etiq"].copy()
        lab_t = b.prev["lab"]                     # Lab lissé + recalé dans le temps
        h, w = etiq.shape
        prob = self.pers(rgb, w, h)
        rep, pal, foule = self._table()
        pers = visage = np.zeros((h, w), bool)
        if prob is not None:
            etiq, pers, visage = self._joueurs(rgb, etiq, prob)
        self._prev_e = etiq
        k = min(h, w) / 540.0
        # îlots « foule » isolés (dans une mêlée, un maillot…) -> couleur ordinaire la plus proche
        ef = np.isin(etiq, list(foule)).astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(ef, connectivity=8)
        petit_f = st[:, cv2.CC_STAT_AREA] < 0.015 * w * h
        petit_f[0] = False
        ilots = petit_f[cc]
        # « foule » sous le haut de la pelouse (mêlée, arbitre…) : faux positif
        pel0 = etiq == B.I_PEL
        haut = np.where(pel0.any(0), pel0.argmax(0), h)
        haut = cv2.erode(haut.astype(np.float32)[None], np.ones((1, int(41 * k) | 1), np.uint8))[0]
        sous = np.arange(h)[:, None] > haut[None, :] + 0.03 * h
        if pel0.mean() > 0.2:            # plan large (beaucoup de pelouse) seulement
            ilots |= (ef > 0) & sous
        if ilots.any():
            idx = np.array([i for i in range(b.n_normal) if i != B.I_PEL])
            X = lab_t[ilots] * np.float32([0.6, 1, 1])
            C = b.palette[idx] * np.float32([0.6, 1, 1])
            d = (X * X).sum(1)[:, None] - 2 * X @ C.T + (C * C).sum(1)[None]
            etiq[ilots] = idx[np.argmin(d, axis=1)]
        e = rep[etiq]
        e = np.where(pers, e, B.Stylizer._mode(e, 3))
        en_foule = np.isin(e, list(foule))
        pel = e == rep[B.I_PEL]
        chair = np.isin(etiq, list(B.PEAUX) + list(range(b.n_normal + B.N_FOULE, len(b.palette)))) | visage

        # --- ombre (0..1) : plus sombre que la moyenne de son aplat, ou ton d'ombre ---
        L = cv2.GaussianBlur(lab_t[..., 0], (0, 0), 2.0 * k)
        n_e = int(e.max()) + 1
        cnt = np.bincount(e.ravel(), minlength=n_e).astype(np.float32)
        moy = np.bincount(e.ravel(), weights=L.ravel(), minlength=n_e) / np.maximum(cnt, 1)
        omb = np.clip((moy[e] - L - 4.0) / 16.0, 0, 1)
        omb = np.maximum(omb, 0.55 * np.isin(etiq, list(OMBRES)).astype(np.float32))
        omb = cv2.GaussianBlur(omb, (0, 0), 2.5 * k)
        if self._prev_omb is not None and self._prev_omb.shape == omb.shape and b.prev is not None:
            omb = 0.5 * omb + 0.5 * self._prev_omb      # lissage temporel
        self._prev_omb = omb
        omb_r = omb.copy()
        omb_r[chair | pel | en_foule] = 0               # pas de trame sur visages/peau/pelouse
        omb_r = np.clip((omb_r - 0.12) / 0.7, 0, 1)

        # --- contours (carte d'étiquettes = image déjà débruitée) ---
        pl = B._lab(pal.tolist())[e]
        bord = np.zeros((h, w), np.float32)
        for ax in (0, 1):
            a = pl[1:] if ax == 0 else pl[:, 1:]
            c = pl[:-1] if ax == 0 else pl[:, :-1]
            fa = en_foule[1:] if ax == 0 else en_foule[:, 1:]
            fc = en_foule[:-1] if ax == 0 else en_foule[:, :-1]
            diff = (np.linalg.norm(a - c, axis=2) > 9) & ~(fa | fc)
            if ax == 0:
                bord[:-1][diff] = 1
            else:
                bord[:, :-1][diff] = 1
        bord = B.Stylizer._sans_miettes(bord, int(18 * k))
        # silhouette des joueurs : trait gras
        sil = np.zeros((h, w), np.float32)
        if pers.any():
            pm = cv2.GaussianBlur(pers.astype(np.float32), (0, 0), 1.2 * k)
            sil = ((pm > 0.35) & (pm < 0.65)).astype(np.float32)
            sil = B.Stylizer._sans_miettes(sil, int(20 * k))

        # --- rendu pleine résolution ---
        f = W / 1080.0 if H >= W else H / 1080.0
        f = max(f, min(H, W) / 1080.0)
        coul = pal[e]
        if (h, w) != (H, W):
            coul = cv2.resize(coul, (W, H), interpolation=cv2.INTER_NEAREST)
        coul = cv2.medianBlur(coul, min(max(3, int(round(W / w * 1.6)) | 1), 7))

        g, vit, pas = self._grille(H, W)
        up = lambda x: cv2.resize(x, (W, H), interpolation=cv2.INTER_LINEAR) if (h, w) != (H, W) else x

        def pose(fond, dessus, a):
            """mélange rapide (uint8) : fond*(1-a) + dessus*a"""
            a = np.ascontiguousarray(a, np.float32)
            if not isinstance(dessus, np.ndarray) or dessus.ndim == 1:
                plein = np.empty_like(fond)
                plein[:] = dessus
                dessus = plein
            return cv2.blendLinear(dessus, fond, a, 1.0 - a)

        aa = 1.2 / pas
        # trame Ben-Day : rayon du point ~ racine de l'ombre (aire ∝ ombre)
        o = up(omb_r)
        pt = np.clip((0.62 * np.sqrt(o) - g) * (1 / aa) + 0.5, 0, 1)
        pt[o < 0.02] = 0
        out = pose(coul, cv2.convertScaleAbs(coul, alpha=0.5, beta=-6), pt)   # même teinte, foncée
        # pelouse : trame légère en dégradé vertical (fixe à l'écran), plus marquée en haut
        pg = up(pel.astype(np.float32))
        if pg.max() > 0:
            grad = np.clip(0.24 - 0.36 * np.arange(H, dtype=np.float32) / H, 0, None)[:, None]
            pt_g = np.clip((grad - g) * (1 / aa) + 0.5, 0, 1) * pg * (grad > 0.02)
            out = pose(out, cv2.convertScaleAbs(coul, alpha=0.82, beta=0), pt_g)
        # tribunes : trame claire régulière + traits de vitesse
        fo = up(en_foule.astype(np.float32))
        if fo.max() > 0:
            pt_f = np.clip((0.26 - g) * (1 / aa) + 0.5, 0, 1) * fo
            out = pose(out, cv2.convertScaleAbs(coul, alpha=0.7, beta=76), pt_f)
            if self.vitesse:
                out = pose(out, PAPIER, vit * fo * 0.55)

        # lignes du terrain en blanc papier (reprises du rendu de base)
        pel_up = cv2.resize(pel.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        a_l = np.clip((sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20)
                      * (1.0 / (B.BLANC[0] - B.PELOUSE[0] - 40)), 0, 1) * pel_up
        out = pose(out, PAPIER, a_l)

        # décalage d'impression : couleurs (+ trame) décalées par rapport à l'encre
        dx, dy = int(round(DECALAGE[0] * f)), int(round(DECALAGE[1] * f))
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        out = cv2.warpAffine(out, M, (W, H), borderMode=cv2.BORDER_REPLICATE)

        # encre à épaisseur variable : fine de base, grasse sur silhouettes et côté ombre
        # (flou à basse résolution, seuil doux en pleine résolution = trait net, sans crénelage)
        tb = up(cv2.GaussianBlur(bord, (0, 0), 0.9))
        ts = up(cv2.GaussianBlur(sil, (0, 0), 1.45))
        om_up = up(omb)
        ep = self.epaisseur * f
        t1 = np.clip((tb - np.clip(0.40 - 0.05 * ep * (1 + 0.8 * om_up), 0.06, 0.4)) * 10, 0, 1)
        t2 = np.clip((ts - np.clip(0.30 - 0.04 * ep * (1 + 0.8 * om_up), 0.05, 0.35)) * 12.5, 0, 1)
        out = pose(out, ENCRE, np.maximum(t1, t2))
        return out


# --- Entrées / sorties -------------------------------------------------------------
def _infos(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)["streams"][0]
    return st["width"], st["height"], st["r_frame_rate"]


def traiter_video(src, dst, start=0.0, dur=None, log=True):
    w, h, fps = _infos(src)
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
    ap = argparse.ArgumentParser(description="Style comic pop / Spider-Verse")
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


if __name__ == "__main__":
    main()
