#!/usr/bin/env python3
"""
Style « Futurismo » (Balla, Boccioni, Depero) pour les plans de rugby — CPU local.

Principe
  1. ligne_claire.Style (non modifié) fournit la carte d'étiquettes STABLE
     (Stylizer de base : flot optique, hystérésis, palette figée, visages
     YuNet aplatis) + la segmentation des personnes MediaPipe
  2. rendu futuriste refait ici :
     - fond (tribunes, ciel, décor) = grandes facettes anguleuses fixes
       (arrangement de droites obliques), palette chaude : ocre, vermillon,
       noir, crème ; légère parallaxe qui suit le mouvement de caméra
     - pelouse = deux verts olive alternés selon les mêmes facettes (prisme)
     - « linee di forza » : quelques coins pointus noirs/vermillon/crème
       qui partent derrière l'action, dans le sens du mouvement
     - joueurs : affiche « propre » — peu de grands aplats :
         * couleurs d'équipe conservées (azur ; vert, or), blanc = crème
         * une seule teinte chair par personne, une seule teinte de cheveux
         * îlots et miettes fusionnés dans l'aplat voisin dominant
         * frontières lissées (argmax de masques flous, en pleine résolution)
     - « dinamismo » : 2 échos = silhouettes nettes en aplat (couleur
       dominante du joueur délavée), décalées (images passées, caméra
       compensée + décalage dans le sens du mouvement) ; aucun écho quand
       l'action est quasi immobile ou en très gros plan
     - ballon : détecté (blanc + bande bleue, ellipse), suivi dans le temps
       et redessiné : ellipse blanche nette, bande bleue propre, contour noir
     - contours noirs épais, silhouette en polygone
  3. visages : aplat chair sans yeux, bouche ni barbe (hérité + forcé)

Usage : python3 futurismo.py ENTREE SORTIE [--start S --dur D]
        (image -> image, vidéo -> vidéo même taille/cadence, sans son)
Import : from futurismo import Style ; st = Style() ; out = st(rgb)
         st.reset() entre deux plans.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import deque

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.dirname(ICI))
import stylize as B  # noqa: E402
import ligne_claire as LC  # noqa: E402

# --- Palette futuriste (RVB) ---------------------------------------------------
OCRE = (224, 158, 52)
OCRE_CL = (238, 200, 118)
VERMIGLIO = (208, 50, 34)
TERRA = (150, 66, 36)
NERO = (28, 22, 22)
CREMA = (243, 230, 198)
PRATO = [(118, 146, 62), (140, 164, 78)]          # pelouse : deux verts olive
FOND = [CREMA, OCRE, OCRE_CL, VERMIGLIO, NERO, TERRA, CREMA, OCRE]   # tirage pondéré
FIG_CHAUD = [NERO, TERRA, OCRE, CREMA, (96, 84, 76)]                  # tons non-équipe
ENCRE = (20, 16, 16)

# --- Palette des figures (classes d'aplats) ---------------------------------------
GRIS = (96, 84, 76)
PEAUX_F = [(238, 194, 152), (212, 152, 106), (166, 106, 70), (112, 70, 46)]   # chair clair -> foncé
BAL_BLANC = (250, 247, 238)
BAL_BLEU = (34, 62, 164)
FP = [NERO, TERRA, OCRE, CREMA, GRIS, LC.AZUR_LC, LC.SB_VERT_LC, LC.OR_LC] + PEAUX_F + [BAL_BLANC, BAL_BLEU, VERMIGLIO]
C_NERO, C_TERRA, C_OCRE, C_CREMA, C_GRIS, C_AZ, C_SB, C_OR = range(8)
C_PEAU = list(range(8, 8 + len(PEAUX_F)))
C_BB, C_BL, C_VE = 8 + len(PEAUX_F), 9 + len(PEAUX_F), 10 + len(PEAUX_F)
C_EQUIPE = (C_AZ, C_SB, C_OR)
FP_RGB = np.array(FP, np.uint8)
FP_LAB = B._lab(FP)
PEAU_L = FP_LAB[C_PEAU, 0]
C_SKIN = 99                    # classe provisoire « peau » (résolue par personne)


def _lab(c):
    return B._lab(c)


def _remplir_trous(m, frac, maxi=None):
    """Bouche les trous (composantes du complément ne touchant pas le bord)."""
    m8 = m.astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(1 - m8, connectivity=4)
    if n <= 1:
        return m.astype(bool)
    bord = np.zeros(n, bool)
    bord[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
    lim = frac * m8.sum() if maxi is None else min(frac * m8.sum(), maxi)
    trou = ~bord & (st[:, cv2.CC_STAT_AREA] < lim)
    trou[0] = False
    return m.astype(bool) | trou[cc]


class Style:
    """Stylisation futuriste, avec mémoire temporelle (vidéo).

    temporel  : False pour une image isolée (échos synthétiques)
    direction : direction du mouvement par défaut (x, y), vers la droite
    graine    : tirage des facettes et des lignes de force
    """

    def __init__(self, temporel=True, cote=540, direction=(1.0, -0.12), graine=7):
        self.lc = LC.Style(temporel=temporel, cote=cote)
        self.temporel = temporel
        self.dir0 = np.array(direction, np.float32) / np.linalg.norm(direction)
        self.graine = graine
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
        self.reset()

    def reset(self):
        self.lc.reset()
        self.hist = deque(maxlen=10)   # (polygones, couleurs, position caméra)
        self.cam = np.zeros(2, np.float32)
        self.dir = self.dir0.copy()
        self.vit = 0.0
        self.apex = None
        self.gris = None
        self._fac = None
        self.prev_c = None             # carte de classes précédente (hystérésis des tons)
        self.g_echo = None             # intensité des échos (lissée)
        self.bal = None                # piste du ballon
        self.bal_att = None            # détection en attente de confirmation

    # -- facettes : arrangement de droites fixes (par taille d'image) -------------
    def _facettes(self, W, H, dx, dy):
        rng = np.random.default_rng(self.graine)
        n = 7
        ang = np.deg2rad(rng.choice([-62, -48, -30, 28, 44, 60, 75, -78], n, replace=False)
                         + rng.uniform(-6, 6, n))
        px = rng.uniform(0.1, 0.9, n) * W
        py = rng.uniform(0.1, 0.9, n) * H
        gx, gy = np.meshgrid(np.arange(W, dtype=np.float32) - dx, np.arange(H, dtype=np.float32) - dy)
        cid = np.zeros((H, W), np.int32)
        for i in range(n):
            s = (gx - px[i]) * np.sin(ang[i]) - (gy - py[i]) * np.cos(ang[i]) > 0
            cid |= s.astype(np.int32) << i
        return cid

    def _couleurs_fond(self, cid):
        """Couleur de chaque facette : tirage déterministe + léger décalage de ton."""
        m = 1 << 7
        h = (np.arange(m) * 2654435761) % 4294967296
        rng = np.random.default_rng(self.graine + 1)
        perm = rng.permutation(m)
        fond = np.zeros((m, 3), np.float32)
        pre = np.zeros((m, 3), np.float32)
        for i in range(m):
            c = np.array(FOND[perm[i] % len(FOND)], np.float32)
            dl = ((h[i] >> 8) % 21 - 10) * 0.9
            fond[i] = np.clip(c + dl, 0, 255)
            pre[i] = PRATO[(bin(i).count("1")) % 2]
        return fond.astype(np.uint8)[cid], pre.astype(np.uint8)[cid]

    # -- couleurs des figures : équipes conservées, le reste ramené au chaud ------
    def _pal_fig(self, pal, rep):
        b = self.lc.base
        lab = B._lab(pal.tolist())
        chaud = B._lab(FIG_CHAUD)
        garde = {B.I_AZ, B.I_SB, B.I_OR, B.I_BLANC} | set(B.PEAUX) \
            | set(range(b.n_normal + B.N_FOULE, len(b.palette)))
        garde = {int(rep[i]) for i in garde if i < len(rep)}
        out = pal.copy()
        for i in range(len(pal)):
            if i in garde:
                continue
            out[i] = FIG_CHAUD[int(np.argmin(np.linalg.norm(chaud - lab[i], axis=1)))]
        out[rep[B.I_BLANC]] = CREMA
        return out

    def _classes_etiq(self, pf, rep):
        """Étiquette (après rep) -> classe d'aplat FP (ou C_SKIN pour la peau)."""
        b = self.lc.base
        n = len(pf)
        peau = {int(rep[i]) for i in list(B.PEAUX) + list(range(b.n_normal + B.N_FOULE, len(b.palette)))
                if i < len(rep)}
        out = np.zeros(n, np.int32)
        cand = np.array(FP[:8], np.float32)
        for i in range(n):
            if i in peau:
                out[i] = C_SKIN
            else:
                out[i] = int(np.argmin(np.linalg.norm(cand - pf[i].astype(np.float32), axis=1)))
        out[int(rep[B.I_AZ])] = C_AZ
        out[int(rep[B.I_SB])] = C_SB
        out[int(rep[B.I_OR])] = C_OR
        out[int(rep[B.I_BLANC])] = C_CREMA
        return out

    # -- nettoyage de la carte de classes (basse résolution) -----------------------
    def _tenues(self, lab, ci, autre):
        """Classe des vêtements / reste des figures d'après la couleur (Lab stable) :
        couleurs d'équipe franches, sinon crème ou noir. Hystérésis par pixel."""
        L, A, Bb = lab[..., 0], lab[..., 1], lab[..., 2]
        C = np.hypot(A, Bb)
        hue = np.degrees(np.arctan2(Bb, A)) % 360
        pv = self.prev_c if (self.prev_c is not None and self.prev_c.shape == ci.shape) else None

        def regles(r):
            # r = 1 : strict ; r < 1 : relâché (pour garder la classe précédente)
            m = {}
            m[C_SB] = (hue > 105) & (hue < 215) & (C > np.where(L < 25, 5.0, 9.0) * r)
            m[C_AZ] = (hue > 225) & (hue < 315) & (C > 14 * r)
            m[C_OR] = (hue > 62) & (hue < 102) & (C > 38 * r) & (L > 55 * r)
            m[C_VE] = ((hue < 58) | (hue > 340)) & (C > 46 * r) & (L > 30)
            return m
        out = ci.copy()
        strict = regles(1.0)
        res = np.where(L > 44, C_CREMA, C_NERO).astype(np.int32)
        for c in (C_OR, C_VE, C_AZ, C_SB):
            res[strict[c]] = c
        if pv is not None:
            rel = regles(0.6)
            for c in (C_SB, C_AZ, C_OR, C_VE):
                keep = (pv == c) & rel[c]
                res[keep] = c
            keep = (pv == C_CREMA) & (L > 36) & (res == C_NERO)
            res[keep] = C_CREMA
            keep = (pv == C_NERO) & (L < 52) & (res == C_CREMA)
            res[keep] = C_NERO
        # les couleurs d'équipe déjà trouvées par le Stylizer de base sont gardées
        m = autre & ~np.isin(ci, C_EQUIPE)
        out[m] = res[m]
        return out

    def _nettoyer(self, ci, fig, cl, pers, lab_src, lab_st, k, ballon=None):
        h, w = ci.shape
        L = lab_src[..., 0]
        equipe = np.isin(ci, C_EQUIPE)
        hors_bal = np.ones((h, w), bool) if ballon is None else ~ballon
        # peau : étiquettes chair + peau MediaPipe (ombres comprises), hors couleurs d'équipe
        skin = (ci == C_SKIN)
        if cl is not None:
            skin |= pers & ((cl == 2) | (cl == 3)) & ~equipe
        skin &= hors_bal
        # visages suivis : toujours un aplat chair plein (anonymat)
        for p in self.lc.base.visages.pistes:
            if p.get("age", 0) > 8:
                continue
            cx, cy, bw, bh = p["c"]
            e = np.zeros((h, w), np.uint8)
            cv2.ellipse(e, (int(cx), int(cy + bh * 0.04)), (max(1, int(bw * 0.5)), max(1, int(bh * 0.55))),
                        0, 0, 360, 1, -1)
            skin |= e.astype(bool) & fig
        skin &= fig
        skin = cv2.morphologyEx(skin.astype(np.uint8), cv2.MORPH_CLOSE, B._disque(3 * k)).astype(bool) & fig
        skin = _remplir_trous(skin, 0.12) & fig & hors_bal
        cheveux = np.zeros((h, w), bool)
        if cl is not None:
            cheveux = pers & (cl == 1) & ~equipe & ~skin & fig & hors_bal
        autre = fig & ~skin & ~cheveux & hors_bal
        out = self._tenues(lab_st, ci, autre)
        out[skin] = C_PEAU[1]
        # une teinte chair par personne (composante connexe de peau)
        n, cc, st, _ = cv2.connectedComponentsWithStats(skin.astype(np.uint8), connectivity=8)
        for i in range(1, n):
            x, y, bw, bh, a = st[i]
            sl = (slice(y, y + bh), slice(x, x + bw))
            m = cc[sl] == i
            pv = None if self.prev_c is None else self.prev_c[sl]
            t = self._ton_dans(m, L[sl], pv, C_PEAU, PEAU_L - 4, 8)
            out[sl][m] = t
        # cheveux : un seul ton sombre par composante
        n, cc, st, _ = cv2.connectedComponentsWithStats(cheveux.astype(np.uint8), connectivity=8)
        ch_c = [C_NERO, C_TERRA, C_OCRE]
        ch_L = np.array([22.0, 45.0, 68.0])
        for i in range(1, n):
            x, y, bw, bh, a = st[i]
            sl = (slice(y, y + bh), slice(x, x + bw))
            m = cc[sl] == i
            pv = None if self.prev_c is None else self.prev_c[sl]
            out[sl][m] = self._ton_dans(m, L[sl], pv, ch_c, ch_L, 10)
        if ballon is not None:
            out[ballon & fig] = C_BB
        out[~fig] = -1
        out[out == C_SKIN] = C_PEAU[1]
        # îlots : composantes trop petites -> aplat voisin (le plus proche)
        aire_fig = max(1, int(fig.sum()))
        amin = float(np.clip(0.004 * aire_fig, 14 * k * k, 700 * k * k))
        petit = np.zeros((h, w), bool)
        for c in np.unique(out):
            if c < 0 or c == C_BB:
                continue
            m = (out == c).astype(np.uint8)
            n, cc, st, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
            if n <= 1:
                continue
            lim = amin * (0.35 if c == C_OR else 1.0)     # chiffres des maillots : gardés
            pt = st[:, cv2.CC_STAT_AREA] < lim
            pt[0] = False
            if pt.any():
                petit |= pt[cc]
        out = self._combler(out, petit, fig)
        return out

    def _ton_dans(self, m, Lsrc, pv, choix, centres, marge):
        Lm = float(np.percentile(Lsrc[m], 60))
        j = int(np.argmin(np.abs(centres - Lm)))
        t = int(choix[j])
        if pv is not None:
            p = pv[m]
            p = p[np.isin(p, choix)]
            if len(p) > 0.3 * m.sum():
                t0 = int(np.bincount(p).argmax())
                j0 = list(choix).index(t0)
                if abs(centres[j0] - Lm) < abs(centres[j] - Lm) + marge:
                    t = t0
        return t

    @staticmethod
    def _combler(out, trou, fig):
        """Pixels `trou` (et figure sans classe) -> classe du pixel valide le plus proche."""
        inval = (trou | (out < 0)) & fig
        if not inval.any():
            return out
        valide = fig & ~inval
        if not valide.any():
            out[inval] = C_CREMA
            return out
        _, lab_i = cv2.distanceTransformWithLabels((~valide).astype(np.uint8), cv2.DIST_L2, 3,
                                                   labelType=cv2.DIST_LABEL_PIXEL)
        ys, xs = np.nonzero(valide)
        src = np.zeros(lab_i.max() + 1, np.int32)
        src[lab_i[ys, xs]] = out[ys, xs]
        out = out.copy()
        out[inval] = src[lab_i[inval]]
        return out

    # -- ballon ----------------------------------------------------------------------
    def _detecter_ballon(self, petit, fig, skin, k):
        """Ballon = tache blanche + bande bleue de forme elliptique (près des mains)."""
        h, w = skin.shape
        hsv = cv2.cvtColor(cv2.medianBlur(petit, 3), cv2.COLOR_RGB2HSV)
        Hh, S, V = hsv[..., 0].astype(np.int16), hsv[..., 1].astype(np.int16), hsv[..., 2].astype(np.int16)
        blanc = (S < 46) & (V > 172)
        bleu = (Hh >= 100) & (Hh <= 140) & (S > 45) & (V > 25)
        self._bal_coul = blanc | bleu
        best, bs = None, 0.0
        for r in (3, 5, 7):
            cand = (blanc | bleu).astype(np.uint8)
            cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, B._disque(r))
            cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            n, cc, st, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
            for i in range(1, n):
                x, y, bw, bh, a = st[i]
                if a < 22 * k * k or a > 0.2 * w * h:
                    continue
                sl = (slice(y, y + bh), slice(x, x + bw))
                m = cc[sl] == i
                wf = float(blanc[sl][m].mean())
                bf = float(bleu[sl][m].mean())
                if wf < 0.3 or bf < 0.06 or wf + bf < 0.8:
                    continue
                # partie la plus « épaisse » seulement (coupe les appendices collés au ballon)
                m = _remplir_trous(m, 0.5)
                dtm = cv2.distanceTransform(np.pad(m.astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
                ry, rx = np.unravel_index(int(np.argmax(dtm)), dtm.shape)
                rr = float(dtm[ry, rx])
                if rr < 2.5 * k:
                    continue
                yy, xx = np.ogrid[:bh, :bw]
                m = m & (((yy - ry) ** 2 + (xx - rx) ** 2) < (1.9 * rr) ** 2)
                cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                c = max(cs, key=cv2.contourArea)
                pts = cv2.convexHull(c).reshape(-1, 2)
                gx, gy = pts[:, 0] + x, pts[:, 1] + y
                ok = (gx > 1) & (gx < w - 2) & (gy > 1) & (gy < h - 2)
                if ok.sum() < 5:
                    continue
                (ex, ey), (d1, d2), ang = cv2.fitEllipse(pts[ok].reshape(-1, 1, 2).astype(np.float32))
                if not (np.isfinite(ex) and d1 > 3 and d2 > 3):
                    continue
                if max(d1, d2) / min(d1, d2) > 2.2:
                    continue
                em = np.zeros((h, w), np.uint8)
                cv2.ellipse(em, ((ex + x, ey + y), (d1, d2), ang), 1, -1)
                em = em.astype(bool)
                if em.sum() < 12:
                    continue
                reg = np.zeros((h, w), bool)
                reg[sl] = m
                hm = np.zeros((h, w), np.uint8)
                cv2.fillPoly(hm, [cv2.convexHull(c) + np.int32([x, y])], 1)
                occ = hm.astype(bool) | (skin & em)
                iou = (occ & em).sum() / max(1, (occ | em).sum())
                plein = reg[em].mean()
                if iou < 0.78 or plein < 0.45:
                    continue
                main = (skin & cv2.dilate(em.astype(np.uint8), B._disque(5 * k)).astype(bool)).any()
                sc = iou * min(1.0, bf / 0.15) * (1.15 if main else 1.0)
                if self.bal is not None:      # continuité avec la piste (position, taille)
                    dd = np.linalg.norm(np.array([ex + x, ey + y]) - self.bal["c"]) / max(4.0, float(self.bal["ax"].max()))
                    rt = np.sqrt(d1 * d2 / max(1.0, float(self.bal["ax"].prod())))
                    if rt < 0.55 or rt > 1.8:
                        continue
                    sc *= (1.3 if dd < 0.8 else 0.8) * float(np.exp(-2.0 * abs(np.log(rt))))
                if sc > bs:
                    bs, best = sc, dict(c=np.array([ex + x, ey + y], np.float32),
                                         ax=np.array([d1, d2], np.float32), ang=float(ang), sc=sc)
        if best is None:
            return None
        bl = (bleu & ~skin).astype(np.float32)
        best["bleu"] = cv2.GaussianBlur(bl, (0, 0), 0.8)
        return best

    def _suivre_ballon(self, det, dcam):
        """Piste lissée : confirmation sur 2 images, maintien 2 images sans détection."""
        P = self.bal
        if P is not None:
            P["c"] = P["c"] + P.get("v", np.zeros(2, np.float32))
        if det is not None:
            if P is not None and np.linalg.norm(det["c"] - P["c"]) < 0.9 * float(P["ax"].max()) + 6:
                v = det["c"] - (P["c"] - P.get("v", 0))
                P["v"] = 0.5 * P.get("v", np.zeros(2, np.float32)) + 0.5 * v * 0.5
                P["c"] = 0.35 * P["c"] + 0.65 * det["c"]
                # axes / angle : ordre (grand, petit) pour un lissage cohérent
                P["ax"] = 0.6 * P["ax"] + 0.4 * det["ax"]
                da = ((det["ang"] - P["ang"] + 90) % 180) - 90
                P["ang"] = (P["ang"] + 0.4 * da) % 180
                P["miss"] = 0
                P["bleu_img"] = det["bleu"]
                return P
            A = self.bal_att
            if A is not None and det["sc"] > 0.8 and A["sc"] > 0.8 \
                    and np.linalg.norm(det["c"] - A["c"]) < 0.9 * float(A["ax"].max()) + 6:
                det["miss"] = 0
                det["v"] = np.zeros(2, np.float32)
                det["can"] = None
                det["bleu_img"] = det["bleu"]
                self.bal_att = None
                self.bal = det
                return det
            self.bal_att = det
            if P is None or not self.temporel:
                if not self.temporel:
                    det.update(miss=0, v=np.zeros(2, np.float32), can=None, bleu_img=det["bleu"])
                    self.bal = det
                    return det
                return None
        else:
            self.bal_att = None
        if P is not None:
            P["miss"] = P.get("miss", 0) + 1
            P["v"] = P.get("v", np.zeros(2, np.float32)) * 0.5
            P["bleu_img"] = None
            if P["miss"] > 2:
                self.bal = None
                return None
            return P
        return None

    def _affine_ballon(self, P, z, n=64):
        """Affine canonique (n x n, disque unité) -> image (échelle z)."""
        a, b = P["ax"] * 0.5
        t = np.deg2rad(P["ang"])
        ca, sa = np.cos(t), np.sin(t)
        c = P["c"]
        # u,v dans [-1,1] ; (u * a) le long de l'axe d1 (orienté par ang), (v * b) perpendiculaire
        s = 2.0 / (n - 1)
        M = np.float32([[a * ca * s, -b * sa * s, 0], [a * sa * s, b * ca * s, 0]])
        M[:, 2] = c - M[:, :2] @ np.float32([(n - 1) / 2, (n - 1) / 2])
        return M * np.float32([[z, z, z], [z, z, z]]) if z != 1 else M

    def _bande_ballon(self, P, h, w):
        """Masque canonique de la bande bleue, lissé dans le temps."""
        n = 64
        M = self._affine_ballon(P, 1.0, n)
        if P.get("bleu_img") is not None:
            can = cv2.warpAffine(P["bleu_img"], M, (n, n), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            can = cv2.GaussianBlur(can, (0, 0), 2.5)
            if P.get("can") is None or not self.temporel:
                P["can"] = can
            else:
                P["can"] = 0.55 * P["can"] + 0.45 * can
        return P.get("can")

    # -- passe principale --------------------------------------------------------------
    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        st = self.lc
        b = st.base
        pal_avant = b.palette
        sortie_base = b(rgb)
        if pal_avant is not None and b.palette is not pal_avant \
                and len(b.palette) <= b.n_normal + B.N_FOULE:
            st.pers.reset()            # changement de plan
            st._prev_e = None
            self.hist.clear()
            self.gris = None
            self.apex = None
            self.prev_c = None
            self.bal = None
            self.bal_att = None
            self.g_echo = None
        etiq = b.prev["etiq"].copy()
        h, w = etiq.shape
        k = min(h, w) / 540.0
        prob = st.pers(rgb, w, h)
        rep, pal, foule = st._table()
        pers = np.zeros((h, w), bool)
        cl = None
        if prob is not None:
            etiq, pers = st._joueurs(rgb, etiq, prob)
            cl = np.argmax(prob, axis=2)
        st._prev_e = etiq
        e = rep[etiq]
        e = np.where(pers, e, B.Stylizer._mode(e, 5))
        petit = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
        lab_src = cv2.cvtColor(cv2.bilateralFilter(petit, 7, 30, 5).astype(np.float32) / 255.0,
                               cv2.COLOR_RGB2Lab)

        # zones : pelouse / figures (joueurs, même minuscules) / fond
        ipel = rep[B.I_PEL]
        pel = e == ipel
        zone = cv2.morphologyEx(pel.astype(np.uint8), cv2.MORPH_CLOSE, B._disque(15 * k))
        n, cc, sts, _ = cv2.connectedComponentsWithStats(1 - zone, connectivity=4)
        bordure = np.zeros(n, bool)
        bordure[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
        trou = ~bordure & (sts[:, cv2.CC_STAT_AREA] < 0.08 * w * h)
        trou[0] = False
        zone = zone.astype(bool) | trou[cc]
        fig = ((zone & ~pel) | pers)
        fig = cv2.morphologyEx(fig.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        # silhouette lissée puis polygone anguleux ; trous de la silhouette bouchés
        fig = (cv2.GaussianBlur(fig.astype(np.float32), (0, 0), 1.2 * k) > 0.5)
        fig = _remplir_trous(fig, 0.03, 400 * k * k).astype(np.uint8)
        cs, _ = cv2.findContours(fig, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        poly = []
        for c in cs:
            a = cv2.contourArea(c)
            x, y, bw, bh = cv2.boundingRect(c)
            if a > 90 * k * k or (a > 14 * k * k and pers[y:y + bh, x:x + bw].mean() > 0.3):
                eps = float(np.clip(0.012 * np.sqrt(a), 1.4, 4.5)) * k
                poly.append(cv2.approxPolyDP(c, eps, True))
        figp = np.zeros((h, w), np.uint8)
        cv2.fillPoly(figp, poly, 1)
        fig = figp.astype(bool)
        pel &= ~fig
        figfrac = float(fig.mean())

        # couleurs des figures -> classes d'aplats, nettoyées
        pf = self._pal_fig(pal, rep)
        cls_e = self._classes_etiq(pf, rep)
        ci = cls_e[e]
        hors = fig & (np.isin(e, list(foule)) | (e == ipel))
        ci[hors] = -1
        ci = self._combler(ci, np.zeros_like(fig), fig)
        # ballon : détection + suivi (avant le nettoyage : il n'est ni peau ni tenue)
        skin0 = (ci == C_SKIN)
        if cl is not None:
            skin0 = skin0 | (pers & ((cl == 2) | (cl == 3)))
        det = self._detecter_ballon(petit, fig | pers, skin0, k)
        P = self._suivre_ballon(det, None)
        bal_lr = None
        if P is not None:
            em = np.zeros((h, w), np.uint8)
            cv2.ellipse(em, ((float(P["c"][0]), float(P["c"][1])), (float(P["ax"][0]), float(P["ax"][1])),
                             float(P["ang"])), 1, -1)
            bal_lr = em.astype(bool) & self._bal_coul
            fig = fig | em.astype(bool)
        ci = self._nettoyer(ci, fig, cl, pers, lab_src, b.prev["lab"], k, bal_lr)
        ci[~fig] = -1

        # mouvement : caméra (fond) et action (figures), lissés
        gris = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (w // 2, h // 2),
                          interpolation=cv2.INTER_AREA)
        dcam = np.zeros(2, np.float32)
        sp = 0.0
        if self.temporel and self.gris is not None and self.gris.shape == gris.shape:
            fl = self.dis.calc(self.gris, gris, None) * 2.0       # précédent -> courant
            f2 = cv2.resize(fig.astype(np.uint8), (w // 2, h // 2), interpolation=cv2.INTER_NEAREST) > 0
            fondm = ~f2
            if fondm.sum() > 50:
                dcam = np.median(fl[fondm], axis=0).astype(np.float32)
            if f2.sum() > 30:
                v = np.median(fl[f2], axis=0) - dcam
                sp = float(np.linalg.norm(v))
                if sp > 0.3:
                    a = min(0.05, 0.015 * sp)       # lent : lignes de force sans balancement
                    d = (1 - a) * self.dir + a * (v / sp)
                    self.dir = d / max(1e-6, np.linalg.norm(d))
                self.vit = 0.9 * self.vit + 0.1 * sp
        self.gris = gris
        self.cam = self.cam + dcam
        dvec = self.dir

        # --- rendu pleine résolution ---------------------------------------------
        z = W / w
        f = min(W, H) / 1080.0
        # facettes du fond (parallaxe douce avec la caméra)
        dx, dy = self.cam * z * 0.3
        cid = self._facettes(W, H, float(dx), float(dy))
        fond, pre = self._couleurs_fond(cid)
        pelF = cv2.resize(pel.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        pelF = cv2.GaussianBlur(pelF, (0, 0), 0.7 * z)[..., None]
        out = (fond * (1 - pelF) + pre * pelF)
        # arêtes des facettes : fin trait noir
        fe = np.zeros((H, W), np.float32)
        fe[:, 1:] += cid[:, 1:] != cid[:, :-1]
        fe[1:, :] += cid[1:, :] != cid[:-1, :]
        fe = np.clip(cv2.GaussianBlur(cv2.dilate(fe, np.ones((2, 2), np.uint8)), (0, 0), 0.6), 0, 1)
        fe *= (0.6 - 0.48 * pelF[..., 0])           # arêtes discrètes sur la pelouse
        out = out * (1 - fe[..., None]) + np.float32(NERO) * fe[..., None]
        # lignes du terrain (rendu de base) en crème
        pel_n = cv2.resize(pel.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        a_l = np.clip((sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20)
                      / (B.BLANC[0] - B.PELOUSE[0] - 40), 0, 1) * pel_n
        out = out * (1 - a_l[..., None]) + np.float32(CREMA) * a_l[..., None]

        # lignes de force : coins pointus derrière l'action, dans le sens du mouvement
        out = self._forces(out, fig, z, W, H)

        # échos : silhouettes nettes en aplat, tirées des images passées
        polyF = [np.round(p.reshape(-1, 2).astype(np.float32) * z).astype(np.int32) for p in poly]
        cols = self._couleurs_echo(poly, ci, h, w)
        self.hist.append((polyF, cols, self.cam.copy()))
        out = self._echos(out, sp, figfrac, dvec, z, W, H, f)

        # figures : classes en pleine résolution, frontières lissées
        sig = float(np.clip(np.sqrt(figfrac) * 4.5, 1.1, 3.2)) * k
        CF = self._classes_pleine(ci, fig, sig, W, H)
        fa8 = np.zeros((H, W), np.uint8)
        if polyF:
            cv2.fillPoly(fa8, [(p * 4) for p in polyF], 255, cv2.LINE_AA, shift=2)
        fa = fa8.astype(np.float32) / 255
        # ballon redessiné
        if P is not None:
            band = self._bande_ballon(P, h, w)
            M = self._affine_ballon(P, z, 64)
            ell = np.zeros((H, W), np.uint8)
            cpx = P["c"] * z
            cv2.ellipse(ell, ((float(cpx[0]), float(cpx[1])), (float(P["ax"][0] * z), float(P["ax"][1] * z)),
                              float(P["ang"])), 1, -1, cv2.LINE_8)
            ell = ell.astype(bool)
            doigts = np.isin(CF, C_PEAU) & ell
            # doigts : seulement des zones de peau franches (pas des miettes)
            doigts = cv2.morphologyEx(doigts.astype(np.uint8), cv2.MORPH_OPEN, B._disque(5 * f)).astype(bool)
            bal = ell & ~doigts
            CF[bal] = C_BB
            if band is not None:
                bF = cv2.warpAffine(band, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
                CF[bal & (bF > 0.42)] = C_BL
            fa = np.maximum(fa, cv2.GaussianBlur(ell.astype(np.float32), (0, 0), 0.8))
        cf = FP_RGB[np.clip(CF, 0, len(FP) - 1)].astype(np.float32)
        fa3 = fa[..., None]
        out = out * (1 - fa3) + cf * fa3

        # contours : frontières d'aplats (pleine résolution) + silhouette épaisse
        bord = np.zeros((H, W), np.uint8)
        dh = CF[:, 1:] != CF[:, :-1]
        dv = CF[1:] != CF[:-1]
        bord[:, 1:][dh] = 1
        bord[1:][dv] = 1
        bord[fa < 0.5] = 0
        dt = cv2.distanceTransform(1 - bord, cv2.DIST_L2, 3)
        t_in = np.clip(1.25 * f + 0.5 - dt, 0, 1)
        sil = np.zeros((H, W), np.uint8)
        cv2.polylines(sil, polyF, True, 255, max(2, int(round(5.0 * f))), cv2.LINE_AA)
        if P is not None:
            cpx = P["c"] * z
            cv2.ellipse(sil, ((float(cpx[0]), float(cpx[1])), (float(P["ax"][0] * z), float(P["ax"][1] * z)),
                              float(P["ang"])), 255, max(2, int(round(4.0 * f))), cv2.LINE_AA)
        t = np.maximum(t_in, sil.astype(np.float32) / 255)
        out = out * (1 - t[..., None]) + np.float32(ENCRE) * t[..., None]

        self.prev_c = ci
        # grain de toile fixe (identique à chaque image : pas de scintillement)
        out = out + self._grain(W, H)[..., None]
        return np.clip(out + 0.5, 0, 255).astype(np.uint8)

    def _classes_pleine(self, ci, fig, sig, W, H):
        """Argmax de masques de classe flous, agrandis en pleine résolution :
        frontières courbes et nettes, sans escaliers ni miettes."""
        h, w = ci.shape
        best = np.full((H, W), -1.0, np.float32)
        CF = np.full((H, W), C_CREMA, np.int32)
        dil = cv2.dilate(fig.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        # on étend les classes un peu hors figure (bord de silhouette sans trou)
        ci2 = ci.copy()
        ci2 = self._combler(ci2, np.zeros_like(fig), dil)
        ci2[~dil] = -1
        for c in np.unique(ci2):
            if c < 0:
                continue
            m = (ci2 == c).astype(np.float32)
            m = cv2.GaussianBlur(m, (0, 0), sig)
            mF = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
            sel = mF > best
            best[sel] = mF[sel]
            CF[sel] = c
        return CF

    def _couleurs_echo(self, poly, ci, h, w):
        """Couleur d'écho de chaque silhouette : aplat dominant (hors peau), délavé."""
        cols = []
        for p in poly:
            m = np.zeros((h, w), np.uint8)
            cv2.fillPoly(m, [p], 1)
            v = ci[(m > 0) & (ci >= 0) & ~np.isin(ci, C_PEAU)]
            if len(v) == 0:
                v = ci[(m > 0) & (ci >= 0)]
            c = int(np.bincount(v).argmax()) if len(v) else C_CREMA
            col = 0.62 * np.float32(FP[c]) + 0.38 * np.float32(CREMA)
            cols.append(col)
        return cols

    def _echos(self, out, sp, figfrac, dvec, z, W, H, f):
        # intensité : mouvement réel de l'action, aucune en très gros plan
        g_mvt = float(np.clip((max(self.vit, sp * 0.5) - 0.4) / 1.6, 0, 1))
        g_gp = float(np.clip((0.30 - figfrac) / 0.15, 0, 1))
        g = (0.35 + 0.65 * g_mvt) * g_gp
        if not self.temporel:
            g = 0.8 * g_gp
        self.g_echo = g if self.g_echo is None else 0.85 * self.g_echo + 0.15 * g
        g = self.g_echo
        if g < 0.03 or not self.hist:
            return out
        pas = (0.022 + 0.004 * min(self.vit, 4.0)) * max(H, W) / z
        ep = max(1, int(round(2.0 * f)))
        for ret, alpha, nk in ((6, 0.42, 2), (3, 0.62, 1)):
            idx = max(0, len(self.hist) - 1 - ret) if self.temporel else len(self.hist) - 1
            polys, cols, cam0 = self.hist[idx]
            off = ((self.cam - cam0) - dvec * pas * nk * 0.5) * z
            calque = np.zeros((H, W), np.uint8)
            coul = np.zeros((H, W, 3), np.float32)
            for p, c in zip(polys, cols):
                q = np.round((p.astype(np.float32) + off) * 4).astype(np.int32)
                m = np.zeros((H, W), np.uint8)
                cv2.fillPoly(m, [q], 255, cv2.LINE_AA, shift=2)
                coul[m > 0] = c
                calque = np.maximum(calque, m)
            a = calque.astype(np.float32) / 255 * (alpha * g)
            out = out * (1 - a[..., None]) + coul * a[..., None]
            # contour fin de l'écho
            tr = np.zeros((H, W), np.uint8)
            qs = [np.round((p.astype(np.float32) + off) * 4).astype(np.int32) for p in polys]
            cv2.polylines(tr, qs, True, 255, ep, cv2.LINE_AA, shift=2)
            ta = tr.astype(np.float32) / 255 * (0.55 * g)
            out = out * (1 - ta[..., None]) + np.float32(ENCRE) * ta[..., None]
        return out

    def _grain(self, W, H):
        if self._fac is None or self._fac[0] != (W, H):
            rng = np.random.default_rng(3)
            g = rng.normal(0, 1, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
            g = cv2.GaussianBlur(g, (0, 0), 0.8)
            g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[:H, :W]
            self._fac = ((W, H), g * 5.0 / max(1e-6, g.std()))
        return self._fac[1]

    def _forces(self, out, fig, z, W, H):
        """5 coins effilés partant derrière le centre de l'action (lissé)."""
        n, cc, st, cen = cv2.connectedComponentsWithStats(fig.astype(np.uint8), connectivity=8)
        if n > 1:
            # centre de la plus grosse figure (le porteur, le groupe)
            i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            c = cen[i].astype(np.float32) * z
        else:
            c = np.array([W * 0.5, H * 0.55], np.float32)
        if self.apex is None or not self.temporel:
            self.apex = c
        else:
            self.apex = 0.92 * self.apex + 0.08 * c
        d = self.dir
        L = 1.3 * np.hypot(W, H)
        a0 = self.apex + d * 0.06 * max(W, H)      # pointe un peu devant l'action
        couche = np.zeros((H, W, 3), np.float32)
        alpha = np.zeros((H, W), np.float32)
        specs = [(-0.32, 0.05, NERO), (-0.16, 0.035, VERMIGLIO), (0.0, 0.05, CREMA),
                 (0.17, 0.04, NERO), (0.33, 0.03, VERMIGLIO)]
        for ang, larg, col in specs:
            ca, sa = np.cos(ang), np.sin(ang)
            v = np.array([-(d[0] * ca - d[1] * sa), -(d[0] * sa + d[1] * ca)], np.float32)
            nv = np.array([-v[1], v[0]], np.float32)
            p0 = a0
            p1 = a0 + v * L + nv * larg * L
            p2 = a0 + v * L - nv * larg * L
            pts = np.round(np.stack([p0, p1, p2]) * 4).astype(np.int32)
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [pts], 255, cv2.LINE_AA, shift=2)
            mf = m.astype(np.float32) / 255
            couche = couche * (1 - mf[..., None]) + np.float32(col) * mf[..., None]
            alpha = np.maximum(alpha, mf)
        a = alpha * 0.62
        return out * (1 - a[..., None]) + couche * a[..., None]


# --- Entrées / sorties -----------------------------------------------------------
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
    ap = argparse.ArgumentParser(description="Style Futurismo (Balla, Boccioni, Depero)")
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
