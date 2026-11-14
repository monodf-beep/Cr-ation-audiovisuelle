#!/usr/bin/env python3
"""
Futurisme « hybride » : le décor futuriste validé (facettes, lignes de force,
pelouse) + chaque joueur peint d'après la VRAIE image, mais proprement.

Pour chaque joueur détecté (segmentation par instance, Mask R-CNN) :
  1. on prend ses vrais pixels (forme réelle du corps, plis, volumes) ;
  2. on les ramène à quelques encres fixes (couleur d'équipe + son ombre,
     or, crème, deux tons de peau, sombre, rouge arbitre) ;
  3. on lisse les zones (vote des couleurs sur un voisinage : plus de
     confettis, les petites taches disparaissent, les bords deviennent nets) ;
  4. contour noir franc autour du joueur, trait fin entre les zones.
Le ballon est redessiné (ellipse blanche, bande bleue, contour).
Animation « en deux » : un dessin toutes les deux images.
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import futurismo_v1 as FUT          # décor validé
import silhouettes as SIL           # détecteur (Mask R-CNN ONNX)

ENCRES = {                           # RGB
    "azur": (36, 112, 214), "azur_ombre": (22, 66, 150),
    "vert": (14, 98, 62), "vert_ombre": (8, 56, 36),
    "or": (236, 184, 44), "creme": (242, 234, 216),
    "peau": (212, 156, 116), "peau_ombre": (150, 92, 62),
    "sombre": (34, 28, 28), "rouge": (214, 44, 40),
}
NOMS = list(ENCRES)
PAL = np.array([ENCRES[n] for n in NOMS], np.uint8)
PAL_LAB = cv2.cvtColor(PAL[None], cv2.COLOR_RGB2LAB)[0].astype(np.float32)


def _lisse_labels(lab, n, sigma):
    """Vote local : chaque pixel prend l'encre majoritaire autour de lui."""
    best = np.full(lab.shape, -1.0, np.float32)
    out = lab.copy()
    for k in range(n):
        m = (lab == k).astype(np.float32)
        if not m.any():
            continue
        b = cv2.GaussianBlur(m, (0, 0), sigma)
        sel = b > best
        out[sel] = k
        best[sel] = b[sel]
    return out


class Style:
    def __init__(self, echos=True):
        self.fut = FUT.Style()
        self.reset()

    def reset(self):
        self.fut.reset()
        self.k = 0
        self.prev = None

    def _joueur(self, rgb, m, toile, trait):
        ys, xs = np.nonzero(m)
        if len(ys) < 400:
            return
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        pad = 12
        y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
        y1, x1 = min(m.shape[0], y1 + pad), min(m.shape[1], x1 + pad)
        mm = m[y0:y1, x0:x1].astype(np.float32)
        # silhouette lissée (bords dessinés, pas pixelisés)
        h = max(8, (y1 - y0))
        sig = max(2.0, h / 90)
        mm = cv2.GaussianBlur(mm, (0, 0), sig) > 0.5
        if mm.sum() < 300:
            return
        crop = cv2.bilateralFilter(rgb[y0:y1, x0:x1], 9, 40, 9)
        lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB).astype(np.float32)
        # encre la plus proche (distance Lab, luminance moins pondérée : les ombres
        # restent dans la famille de leur couleur)
        d = ((lab[..., None, :] - PAL_LAB[None, None]) * np.array([0.6, 1.0, 1.0], np.float32)) ** 2
        lab_id = d.sum(-1).argmin(-1).astype(np.int32)
        lab_id[~mm] = -1
        # zones propres : deux passes de vote (petit puis grand voisinage)
        k = len(NOMS)
        tmp = np.where(mm, lab_id, 0)
        tmp = _lisse_labels(tmp, k, max(2.5, h / 70))
        tmp = _lisse_labels(tmp, k, max(4.0, h / 40))
        couleur = PAL[tmp]
        sub = toile[y0:y1, x0:x1]
        sub[mm] = couleur[mm]
        # traits : contour franc + séparation fine entre zones
        ep = max(3, int(h / 60))
        cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cs = [cv2.approxPolyDP(c, max(1.0, h / 250), True) for c in cs]
        cv2.drawContours(sub, cs, -1, (20, 16, 16), ep, lineType=cv2.LINE_AA)
        bord = cv2.morphologyEx(tmp.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        bord &= mm
        bord = cv2.dilate(bord.astype(np.uint8), np.ones((max(1, ep // 2),) * 2, np.uint8)) > 0
        sub[bord] = (sub[bord] * 0.25 + np.array([20, 16, 16]) * 0.75).astype(np.uint8)

    def _ballon(self, bal, toile, H, W):
        if not bal:
            return
        b = max(bal, key=lambda d: d["score"])
        m = cv2.resize(b["mask"].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cs:
            return
        c = max(cs, key=cv2.contourArea)
        if len(c) < 5 or cv2.contourArea(c) < 60:
            return
        (cx, cy), (a, bb), ang = cv2.fitEllipse(c)
        ax = (int(a / 2), int(bb / 2))
        cv2.ellipse(toile, (int(cx), int(cy)), ax, ang, 0, 360, ENCRES["creme"], -1, cv2.LINE_AA)
        cv2.ellipse(toile, (int(cx), int(cy)), (max(1, ax[0] // 5), ax[1]), ang, 0, 360, ENCRES["azur"], -1, cv2.LINE_AA)
        cv2.ellipse(toile, (int(cx), int(cy)), ax, ang, 0, 360, (20, 16, 16), max(2, ax[1] // 8), cv2.LINE_AA)

    def __call__(self, rgb):
        self.k += 1
        fond = self.fut(rgb)                  # le décor évolue à chaque image (lignes de force)
        if self.prev is not None and self.k % 2 == 0:
            return self.prev                  # « en deux » : on garde le dessin précédent
        H, W = rgb.shape[:2]
        pers, bal = SIL.detecter(rgb)
        toile = fond.copy()
        # du plus loin (haut de l'image) au plus proche (bas) : les recouvrements se lisent
        items = []
        for p in pers:
            m = cv2.resize(p["mask"].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
            if m.sum() > 0.0015 * H * W:
                ys = np.nonzero(m)[0]
                items.append((ys.max(), m))
        for _, m in sorted(items, key=lambda x: x[0]):
            self._joueur(rgb, m, toile, True)
        self._ballon(bal, toile, H, W)
        self.prev = toile
        return toile
