#!/usr/bin/env python3
"""
Stylisation « bande dessinée / cel-shading » des plans de rugby, en local (CPU).

Principe (OpenCV pur + détecteur de visages YuNet, aucun service distant)
  1. calcul à basse résolution (petit côté 540 px), lissage bilatéral
  2. stabilité temporelle : flot optique DIS -> l'état précédent (image lissée,
     étiquettes de couleur, masques) est recalé puis mélangé ; hystérésis sur
     les couleurs pour qu'un aplat ne « clignote » pas d'une image à l'autre
  3. zones : pelouse (un vert uni), lignes blanches, foule/tribunes (texture
     dense -> 4 tons calmes, sans contours), peau
  4. couleurs d'équipe forcées : azur Italie, vert Springbok + or
  5. palette figée par plan (couleurs fixes + k-means sur la 1re image)
  6. visages (YuNet, suivis dans le temps) remplis d'un aplat couleur peau,
     sans aucun détail ; toute zone de peau est réduite à un seul ton
  7. contours sombres aux frontières de couleurs contrastées ; rendu final en
     pleine résolution (aplats nets, traits et lignes anticrénelés)

Usage : python3 stylize.py ENTREE.mp4 SORTIE.mp4 [--start S] [--dur D]
Import : from stylize import stylize_frame, Stylizer
         sty = Stylizer(); for img in images: out = sty(img)   # RVB uint8
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
MODELE_VISAGE = os.path.join(ICI, "modeles", "face_detection_yunet_2023mar.onnx")

# --- Couleurs (RVB) ----------------------------------------------------------
AZUR = (20, 112, 214)          # maillot Italie
AZUR_OMBRE = (12, 72, 156)
SB_VERT = (4, 104, 68)         # vert Springbok
SB_OMBRE = (2, 68, 46)
OR = (250, 184, 28)            # or Springbok
OR_OMBRE = (200, 138, 20)
BLANC = (246, 246, 242)
PELOUSE = (84, 158, 70)        # pelouse : un seul vert, identique sur tous les plans
ENCRE = (26, 24, 32)           # couleur des contours
ANCRES = [
    AZUR, AZUR_OMBRE, SB_VERT, SB_OMBRE, OR, OR_OMBRE, BLANC, PELOUSE,
    (200, 200, 200), (34, 34, 38),                                    # gris clair, noir
    (40, 48, 74),                                                     # marine
    (240, 204, 176), (220, 172, 140), (190, 136, 104),                # peaux
    (146, 98, 72), (98, 66, 50),
    (206, 38, 46), (150, 26, 34),                                     # rouges
]
I_AZ, I_AZO, I_SB, I_SBO, I_OR, I_ORO, I_BLANC, I_PEL = range(8)
PEAUX = [11, 12, 13, 14, 15]   # indices des tons chair dans ANCRES
N_FOULE = 4                    # nombre de tons pour la foule


def _lab(rgb_list):
    a = np.asarray(rgb_list, np.float32).reshape(-1, 1, 3) / 255.0
    return cv2.cvtColor(a, cv2.COLOR_RGB2Lab).reshape(-1, 3)


def _rgb_of_lab(lab):
    a = np.asarray(lab, np.float32).reshape(-1, 1, 3)
    return np.clip(cv2.cvtColor(a, cv2.COLOR_Lab2RGB).reshape(-1, 3) * 255 + 0.5, 0, 255).astype(np.uint8)


def _disque(r):
    r = max(3, int(r) | 1)
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))


class _Visages:
    """Détection YuNet + suivi léger (lissage des boîtes, persistance)."""

    def __init__(self):
        self.det = None
        if os.path.exists(MODELE_VISAGE):
            self.det = cv2.FaceDetectorYN.create(MODELE_VISAGE, "", (320, 320), 0.55, 0.3, 50)
        else:
            print("! modèle YuNet absent : visages aplatis seulement via la peau", file=sys.stderr)
        self.pistes = []

    def reset(self):
        self.pistes = []

    def maj(self, bgr, flux=None):
        """Piste = dict(c=[cx, cy, w, h], o=[ox, oy] centre des traits, age, ton)."""
        dets = []
        if self.det is not None:
            h, w = bgr.shape[:2]
            self.det.setInputSize((w, h))
            _, f = self.det.detect(bgr)
            if f is not None:
                for r in f:
                    x, y, bw, bh = (float(v) for v in r[:4])
                    if bw < 6:
                        continue
                    pts = r[4:14].reshape(5, 2)
                    cx, cy = x + bw / 2, y + bh / 2
                    m = pts.mean(0)
                    dets.append(dict(c=[cx, cy, bw, bh], o=[(m[0] - cx) / bw, (m[1] - cy) / bh]))
        if flux is not None:                  # les pistes suivent le mouvement
            for p in self.pistes:
                xi = int(np.clip(p["c"][0], 0, flux.shape[1] - 1))
                yi = int(np.clip(p["c"][1], 0, flux.shape[0] - 1))
                p["c"][0] -= float(flux[yi, xi, 0])
                p["c"][1] -= float(flux[yi, xi, 1])
        res, libres = [], list(range(len(self.pistes)))
        for d in dets:
            best, bd = None, 1e9
            for i in libres:
                p = self.pistes[i]
                dist = np.hypot(p["c"][0] - d["c"][0], p["c"][1] - d["c"][1])
                if dist < 0.7 * max(p["c"][2], d["c"][2]) and dist < bd:
                    best, bd = i, dist
            if best is None:
                d.update(age=0, ton=None)
                res.append(d)
            else:
                libres.remove(best)
                p = self.pistes[best]
                p["c"] = [0.4 * a + 0.6 * b for a, b in zip(p["c"], d["c"])]
                p["o"] = [0.5 * a + 0.5 * b for a, b in zip(p["o"], d["o"])]
                p["age"] = 0
                res.append(p)
        for i in libres:                      # visage perdu : gardé ~0,5 s
            p = self.pistes[i]
            p["age"] += 1
            if p["age"] <= 15:
                res.append(p)
        self.pistes = res
        return res


class Stylizer:
    """Stylisation image par image avec mémoire temporelle (vidéo).

    cote      : petit côté de l'image de calcul (540 = bon compromis vitesse)
    temporel  : lissage temporel (False pour une image isolée)
    epaisseur : facteur d'épaisseur des contours
    """

    def __init__(self, cote=540, temporel=True, epaisseur=1.0):
        self.cote = cote
        self.temporel = temporel
        self.epaisseur = epaisseur
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
        self.visages = _Visages()
        self.reset()

    def reset(self):
        self.prev = None              # état recalé d'une image à l'autre
        self.prev_vignette = None
        self.palette = None
        self.visages.reset()

    # -- palette figée par plan -------------------------------------------------
    def _faire_palette(self, lab, lab_foule, normal, foule):
        anc = _lab(ANCRES)
        rng = np.random.default_rng(0)
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
        pal = [anc]
        px = lab[normal]
        if len(px) > 500:             # couleurs propres au plan
            px = px[rng.choice(len(px), min(len(px), 20000), replace=False)]
            _, _, cen = cv2.kmeans(px.astype(np.float32), 7, None, crit, 2, cv2.KMEANS_PP_CENTERS)
            pal += [c[None] for c in cen if np.min(np.linalg.norm(anc - c, axis=1)) > 10]
        self.n_normal = sum(len(p) for p in pal)
        px = lab_foule[foule]         # tons calmes de la foule
        if len(px) > 500:
            px = px[rng.choice(len(px), min(len(px), 20000), replace=False)]
            _, _, cen = cv2.kmeans(px.astype(np.float32), N_FOULE, None, crit, 2, cv2.KMEANS_PP_CENTERS)
        else:
            cen = _lab([(70, 70, 78), (120, 120, 128), (170, 170, 176), (215, 215, 220)])
        cen = cen[np.argsort(cen[:, 0])]
        pal.append(cen)
        self.palette = np.vstack(pal).astype(np.float32)
        self.i_foule = np.arange(self.n_normal, self.n_normal + N_FOULE)
        self.pal_rgb = _rgb_of_lab(self.palette)

    def _ajout_couleur(self, lab_c):
        self.palette = np.vstack([self.palette, np.asarray(lab_c, np.float32)[None]])
        self.pal_rgb = _rgb_of_lab(self.palette)
        return len(self.palette) - 1

    # -- passe principale ---------------------------------------------------------
    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        s = min(1.0, self.cote / min(H, W))
        w, h = max(2, round(W * s)), max(2, round(H * s))
        petit = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA) if s < 1 else rgb.copy()
        k = min(w, h) / 540.0            # échelle des noyaux

        # changement de plan -> on repart de zéro
        vign = cv2.resize(petit, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
        if self.prev_vignette is not None and (
                self.prev_vignette.shape != vign.shape or np.abs(vign - self.prev_vignette).mean() > 40):
            self.reset()
        self.prev_vignette = vign

        # 1. lissage
        lisse = petit
        for _ in range(3):
            lisse = cv2.bilateralFilter(lisse, 7, 35, 5)
        lab = cv2.cvtColor(lisse.astype(np.float32) / 255.0, cv2.COLOR_RGB2Lab)
        gris = cv2.cvtColor(petit, cv2.COLOR_RGB2GRAY)
        gl = cv2.GaussianBlur(gris, (0, 0), 1.0)
        mag = cv2.magnitude(cv2.Sobel(gl, cv2.CV_32F, 1, 0), cv2.Sobel(gl, cv2.CV_32F, 0, 1))
        dens = cv2.blur((mag > 40).astype(np.float32), (int(31 * k) | 1,) * 2)

        # 2. recalage de l'état précédent (flot optique) et mélange
        flux = carte = None
        P = self.prev
        if self.temporel and P is not None and P["gris"].shape == gris.shape:
            flux = self.dis.calc(gris, P["gris"], None)
            gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
            carte = (gx + flux[..., 0], gy + flux[..., 1])

            def recale(x, interp=cv2.INTER_LINEAR):
                return cv2.remap(x, carte[0], carte[1], interp, borderMode=cv2.BORDER_REPLICATE)

            avant = recale(P["lab"])
            ecart = np.linalg.norm(lab - avant, axis=2)
            pds = (0.75 * np.clip(1.0 - ecart / 12.0, 0, 1))[..., None]
            lab = lab * (1 - pds) + avant * pds
            dens = 0.3 * dens + 0.7 * recale(P["dens"])
        etat = dict(gris=gris, lab=lab.copy(), dens=dens)

        # visages (détectés tôt : leurs abords ne sont jamais traités comme foule)
        pistes = self.visages.maj(cv2.cvtColor(petit, cv2.COLOR_RGB2BGR), flux)
        abords = np.zeros((h, w), np.uint8)
        for p in pistes:
            cx, cy, bw, bh = p["c"]
            cv2.ellipse(abords, (int(cx), int(cy - bh * 0.1)), (int(bw * 1.1) + 1, int(bh * 1.1) + 1),
                        0, 0, 360, 1, -1)

        L = lab[..., 0]
        chroma = np.hypot(lab[..., 1], lab[..., 2])
        teinte = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360

        # 3a. pelouse : grandes zones vert clair
        vert = ((teinte > 95) & (teinte < 170) & (chroma > 14) & (L > 32)).astype(np.uint8)
        vert = cv2.morphologyEx(vert, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, cc, st, _ = cv2.connectedComponentsWithStats(vert, connectivity=4)
        ok = np.zeros(n, bool)
        ok[1:] = st[1:, cv2.CC_STAT_AREA] > 0.01 * w * h
        pelouse = ok[cc]
        # 2e passe : la pelouse a sa propre clarté/saturation (exclut lignes et blancs teintés)
        if pelouse.sum() > 100:
            lm0 = float(np.median(L[pelouse]))
            cm0 = float(np.median(chroma[pelouse]))
            pelouse &= (chroma > 0.6 * cm0) & (L < lm0 + 14)
            pelouse = cv2.morphologyEx(pelouse.astype(np.uint8), cv2.MORPH_OPEN,
                                       np.ones((3, 3), np.uint8)).astype(bool)
        # joueurs en vert (survêtements) : petites taches nettement plus sombres
        if pelouse.any():
            lm = float(np.median(L[pelouse]))
            sombre = (pelouse & (L < lm - 10)).astype(np.uint8)
            n, cc, st, _ = cv2.connectedComponentsWithStats(sombre, connectivity=8)
            pt = st[:, cv2.CC_STAT_AREA] < 0.003 * w * h
            pt[0] = False
            pelouse &= ~pt[cc]
        # zone de jeu = pelouse + ce qu'elle entoure (joueurs, lignes, poteaux)
        zone = cv2.morphologyEx(pelouse.astype(np.uint8), cv2.MORPH_CLOSE, _disque(15 * k))
        n, cc, st, _ = cv2.connectedComponentsWithStats(1 - zone, connectivity=4)
        bordure = np.zeros(n, bool)
        bordure[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
        trou = (~bordure) & (st[:, cv2.CC_STAT_AREA] < 0.04 * w * h)
        trou[0] = False
        zone_jeu = zone.astype(bool) | trou[cc]
        # petits joueurs lointains (taches entourées de pelouse) : pas de contour
        n, cc, st, _ = cv2.connectedComponentsWithStats((zone_jeu & ~pelouse).astype(np.uint8), connectivity=8)
        petit_ok = st[:, cv2.CC_STAT_AREA] < 0.002 * w * h
        petit_ok[0] = False
        minuscule = petit_ok[cc]

        # 3b. lignes blanches : cherchées à haute résolution (traits fins)
        # (on exclut les joueurs : taches non vertes plus épaisses qu'une ligne)
        corps = cv2.morphologyEx((zone_jeu & ~pelouse).astype(np.uint8), cv2.MORPH_OPEN, _disque(5 * k))
        corps = cv2.dilate(corps, _disque(3)).astype(bool)
        pres_pel = zone_jeu & ~corps
        ligne_a = self._lignes(rgb, pres_pel)
        # lignes épaisses (gros plans) : taches claires, ternes et allongées
        lignes_ep = np.zeros((h, w), bool)
        if pelouse.sum() > 100:
            lm = float(np.median(L[pelouse]))
            cm = float(np.median(chroma[pelouse]))
            cand = (zone_jeu & ~pelouse & (L > lm + 10) & (chroma < cm * 0.95)).astype(np.uint8)
            cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            cs, _ = cv2.findContours(cand, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cs:
                aire = cv2.contourArea(c)
                if aire < 40 * k * k:
                    continue
                (_, _), (a, b), _ = cv2.minAreaRect(c)
                if max(a, b) > 4 * max(min(a, b), 1) and aire > 0.35 * a * b:
                    cv2.drawContours(lignes_ep.view(np.uint8), [c], -1, 1, -1)
            lignes_ep &= cand.astype(bool)
            lignes_ep |= cand.astype(bool) & ~corps          # lignes fines entre deux joueurs
        lignes_ep |= (cv2.resize(ligne_a, (w, h), interpolation=cv2.INTER_AREA) > 0.3) & ~corps

        # 3c. foule / tribunes : forte densité de contours hors zone de jeu
        foule = np.clip((dens - 0.28) / 0.14, 0, 1)
        foule[zone_jeu | (abords > 0)] = 0
        # on bouche les trous de la foule (spectateurs proches en manteau sombre…)
        ef = cv2.morphologyEx((foule > 0.5).astype(np.uint8), cv2.MORPH_CLOSE, _disque(15 * k))
        n, cc, st, _ = cv2.connectedComponentsWithStats(1 - ef, connectivity=4)
        bordure = np.zeros(n, bool)
        bordure[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
        trou = ~bordure & (st[:, cv2.CC_STAT_AREA] < 0.01 * w * h)
        trou[0] = False
        ef = (ef > 0) | trou[cc]
        ef &= ~zone_jeu & (abords == 0)
        foule = np.maximum(foule, ef.astype(np.float32))
        foule = cv2.GaussianBlur(foule, (0, 0), 3 * k)
        en_foule = foule > 0.5

        # couleurs : foule très lissée et éteinte, reste un peu plus franc
        q = cv2.resize(lab, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        fond = cv2.resize(cv2.GaussianBlur(q[..., 0], (0, 0), 12 * k), (w, h))
        lab_foule = cv2.resize(cv2.GaussianBlur(q, (0, 0), 5 * k), (w, h))
        # arrière-plan « éclairci » façon décor d'animation : contraste réduit, plus clair
        lab_foule[..., 0] = 0.55 * (fond + (lab_foule[..., 0] - fond) * 0.6) + 0.45 * 72
        lab_foule[..., 1:] *= 0.7
        lab_eff = lab.copy()
        joueurs = zone_jeu & ~pelouse          # sur le terrain : détail fin préservé
        if joueurs.any():
            brut = cv2.cvtColor(cv2.bilateralFilter(petit, 5, 20, 3).astype(np.float32) / 255.0,
                                cv2.COLOR_RGB2Lab)
            lab_eff[joueurs] = brut[joueurs]
        lab_eff[..., 1:] *= 1.15
        lab_eff[en_foule] = lab_foule[en_foule]

        # 4. palette du plan (figée)
        if self.palette is None:
            self._faire_palette(lab_eff, lab_foule, ~pelouse & ~en_foule & ~zone_jeu, en_foule)
        pal = self.palette
        npal = len(pal)

        # 5. distances pondérées (la teinte compte plus que la luminosité)
        wl = np.array([0.6, 1, 1], np.float32)
        X = (lab_eff * wl).reshape(-1, 3)
        C = pal * wl
        d = (X * X).sum(1)[:, None] - 2 * X @ C.T + (C * C).sum(1)[None]
        d = d.reshape(h, w, npal)
        normaux = np.array([i for i in range(self.n_normal) if i != I_PEL])
        e_n = normaux[np.argmin(d[..., normaux], axis=2)]
        e_f = self.i_foule[np.argmin(d[..., self.i_foule], axis=2)]
        etiq = np.where(en_foule, e_f, e_n).astype(np.int32)

        # couleurs d'équipe (seuils mesurés sur les maillots)
        hsv = cv2.cvtColor(lisse, cv2.COLOR_RGB2HSV)
        if joueurs.any():
            hsv[joueurs] = cv2.cvtColor(petit, cv2.COLOR_RGB2HSV)[joueurs]
        Hh, Ss, Vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        libre = ~pelouse & ~en_foule
        azur = libre & (Hh >= 97) & (Hh <= 120) & (Ss > 110) & (Vv > 80)
        etiq[azur] = np.where(Vv[azur] > 115, I_AZ, I_AZO)
        sbv = libre & (Ss > 70) & (Vv > 18) & (
            ((Hh >= 30) & (Hh <= 90) & (Vv < 80)) | ((Hh >= 40) & (Hh <= 85) & (Vv < 150)))
        etiq[sbv] = np.where(Vv[sbv] > 60, I_SB, I_SBO)
        orr = libre & (Hh >= 19) & (Hh <= 32) & (Ss > 110) & (Vv > 120)
        etiq[orr] = np.where(Vv[orr] > 170, I_OR, I_ORO)
        force = azur | sbv | orr
        etiq[pelouse | lignes_ep] = I_PEL

        # hystérésis : on garde l'ancienne couleur tant qu'elle reste proche
        if carte is not None:
            ancien = cv2.remap(P["etiq"].astype(np.float32), carte[0], carte[1],
                               cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE).astype(np.int32)
            ancien = np.minimum(ancien, npal - 1)
            da = np.take_along_axis(d, ancien[..., None], axis=2)[..., 0]
            dn = np.take_along_axis(d, etiq[..., None], axis=2)[..., 0]
            garde = (da < dn + 60.0) & (da < 600) & ~force & (etiq != I_PEL) & (ancien != I_PEL)
            etiq[garde] = ancien[garde]

        # nettoyage : filtre de mode (supprime les miettes), plus doux sur les joueurs
        e3 = self._mode(etiq, 3)
        etiq = np.where(joueurs, e3, self._mode(e3, int(5 * k) | 1))
        if en_foule.any():
            ef = self._mode(etiq, int(11 * k) | 1)
            etiq[en_foule] = ef[en_foule]

        # 6. peau : yeux, bouche… comblés, un seul ton par zone
        peau = np.isin(etiq, PEAUX)
        n, cc, st, _ = cv2.connectedComponentsWithStats((~peau).astype(np.uint8), connectivity=4)
        bordure = np.zeros(n, bool)
        bordure[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
        trou = ~bordure & (st[:, cv2.CC_STAT_AREA] < 0.005 * w * h)
        trou[0] = trou[0] and not peau[0, 0]
        peau_f = (peau | trou[cc]).astype(np.uint8)      # trous (yeux, bouche…) comblés
        n, cc = cv2.connectedComponents(peau_f, connectivity=8)
        if n > 1:
            maj = np.zeros(n, np.int32)
            cpt = np.zeros((n, len(PEAUX)), np.int64)
            for j, ip in enumerate(PEAUX):
                cpt[:, j] = np.bincount(cc[etiq == ip], minlength=n)
            maj[1:] = np.array(PEAUX)[np.argmax(cpt[1:], axis=1)]
            m = cc > 0
            etiq[m] = maj[cc[m]]

        # visages détectés : aplat chair qui suit la forme réelle du visage
        m_vis = np.zeros((h, w), np.int32)
        for p in pistes:
            cx, cy, bw, bh = p["c"]
            coeur = np.zeros((h, w), np.uint8)
            cv2.ellipse(coeur, (int(cx), int(cy + bh * 0.04)), (max(1, int(bw * 0.5)), max(1, int(bh * 0.52))),
                        0, 0, 360, 1, -1)
            ext = np.zeros((h, w), np.uint8)
            cv2.ellipse(ext, (int(cx), int(cy - bh * 0.05)), (max(1, int(bw * 0.62)), max(1, int(bh * 0.72))),
                        0, 0, 360, 1, -1)
            if p["ton"] is None:       # ton chair : mesuré une fois, puis figé
                sel = coeur.astype(bool) & (chroma > 6) & (teinte > 20) & (teinte < 85) & (L > 20)
                if sel.sum() > 5:
                    c = np.percentile(lab[sel], 65, axis=0)
                    c[0] = np.clip(c[0] + 6, 30, 88)
                    c[1:] = c[1:] * 1.1
                else:
                    c = _lab([ANCRES[12]])[0]
                p["ton"] = self._ajout_couleur(c)
                pal = self.palette
            ton_L = float(pal[p["ton"]][0])
            chair = (chroma > 8) & (chroma < 45) & (teinte > 15) & (teinte < 90) & (L > 0.7 * ton_L)
            sel = (coeur > 0) | ((ext > 0) & (np.isin(etiq, PEAUX) | (peau_f > 0) | chair))
            sel = cv2.morphologyEx(sel.astype(np.uint8), cv2.MORPH_CLOSE, _disque(bw * 0.15)) & ext
            m_vis[sel > 0] = p["ton"] + 1
        mv = m_vis > 0
        etiq[mv] = m_vis[mv] - 1
        etat["etiq"] = etiq.copy()
        self.prev = etat

        # 7. contours : frontières entre couleurs bien différentes
        # (un seul pixel d'épaisseur, posé du côté le plus sombre de la frontière)
        pl = pal[etiq]
        Lp = pl[..., 0]
        bord = np.zeros((h, w), bool)
        # écart surtout de teinte : pas de trait entre ombre et lumière d'une même matière
        plw = pl * np.array([0.35, 1, 1], np.float32)
        fort = np.linalg.norm(plw[:, 1:] - plw[:, :-1], axis=2) > 16
        sombre_g = Lp[:, :-1] <= Lp[:, 1:]
        bord[:, :-1] |= fort & sombre_g
        bord[:, 1:] |= fort & ~sombre_g
        fort = np.linalg.norm(plw[1:, :] - plw[:-1, :], axis=2) > 16
        sombre_h = Lp[:-1, :] <= Lp[1:, :]
        bord[:-1, :] |= fort & sombre_h
        bord[1:, :] |= fort & ~sombre_h
        trait = bord.astype(np.float32)
        trait *= (1 - foule) ** 2                            # rien dans la foule
        trait[minuscule] = 0
        trait[cv2.dilate(lignes_ep.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0] = 0
        trait = self._sans_miettes(trait, int(14 * k))

        # 8. rendu pleine résolution
        coul = self.pal_rgb[etiq]
        if s < 1:
            coul = cv2.resize(coul, (W, H), interpolation=cv2.INTER_NEAREST)
            coul = cv2.medianBlur(coul, max(3, int(2 / s) | 1))
            t = cv2.resize(trait, (W, H), interpolation=cv2.INTER_LINEAR)
        else:
            t = trait
        la = ligne_a
        if lignes_ep.any():
            le = cv2.resize(lignes_ep.astype(np.float32), la.shape[::-1], interpolation=cv2.INTER_LINEAR)
            la = np.maximum(la, np.clip((le - 0.3) / 0.4, 0, 1))
        if la.shape[:2] != (H, W):
            la = cv2.resize(la, (W, H), interpolation=cv2.INTER_LINEAR)
        sig = 0.5 * self.epaisseur / s
        t = np.clip(cv2.GaussianBlur(t, (0, 0), sig) * 2.0, 0, 1)
        out = coul
        for a, c in ((la, BLANC), (t, ENCRE)):
            a = np.ascontiguousarray(a, np.float32)
            plein = np.empty_like(out)
            plein[:] = c
            out = cv2.blendLinear(plein, out, a, 1.0 - a)
        return out

    def _lignes(self, rgb, zone):
        """Masque doux des lignes blanches (résolution <= 1080 de petit côté)."""
        H, W = rgb.shape[:2]
        s = min(1.0, 1080 / min(H, W))
        img = cv2.resize(rgb, (round(W * s), round(H * s)), interpolation=cv2.INTER_AREA) if s < 1 else rgb
        h, w = img.shape[:2]
        z = cv2.resize(zone.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        if not z.any():
            return np.zeros((h, w), np.float32)
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2Lab)
        Lu = lab[..., 0]
        ch = (np.abs(lab[..., 1].astype(np.int16) - 128) + np.abs(lab[..., 2].astype(np.int16) - 128))
        ch = np.clip(ch, 0, 255).astype(np.uint8)
        r = _disque(19 * min(h, w) / 1080)
        clair = cv2.subtract(Lu, cv2.morphologyEx(Lu, cv2.MORPH_OPEN, r)).astype(np.float32)
        terne = cv2.subtract(cv2.morphologyEx(ch, cv2.MORPH_CLOSE, r), ch).astype(np.float32)
        a = np.clip((clair - 10) / 14, 0, 1) * np.clip((terne - 4) / 10, 0, 1) * z
        a = cv2.GaussianBlur(a, (0, 0), 0.7)
        return np.clip((a - 0.15) / 0.5, 0, 1)

    @staticmethod
    def _mode(etiq, r):
        """Filtre de mode : chaque pixel prend l'étiquette majoritaire du voisinage."""
        best = np.full(etiq.shape, -1.0, np.float32)
        out = etiq.copy()
        for i in np.unique(etiq):
            sc = cv2.boxFilter((etiq == i).astype(np.float32), -1, (r, r))
            m = sc > best
            best[m] = sc[m]
            out[m] = i
        return out

    @staticmethod
    def _sans_miettes(trait, mini):
        b = (trait > 0.5).astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
        if n <= 1:
            return trait
        ok = np.zeros(n, bool)
        ok[1:] = st[1:, cv2.CC_STAT_AREA] >= mini
        return trait * ok[cc]


def stylize_frame(rgb_uint8):
    """Stylise une image isolée (RVB uint8) -> RVB uint8, même taille."""
    return Stylizer(temporel=False)(rgb_uint8)


# --- Vidéo -------------------------------------------------------------------
def _infos(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:stream_side_data=rotation",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)["streams"][0]
    w, h = st["width"], st["height"]
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    if abs(rot) % 180 == 90:          # ffmpeg redresse les vidéos de téléphone
        w, h = h, w
    return w, h, st["r_frame_rate"]


def stylize_video(src, dst, start=0.0, dur=None, cote=540, log=True):
    w, h, fps = _infos(src)
    cmd_in = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", src]
    if dur:
        cmd_in += ["-t", str(dur)]
    cmd_in += ["-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    cmd_out = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{w}x{h}", "-r", fps, "-i", "-", "-an", "-c:v", "libx264",
               "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", dst]
    pin = subprocess.Popen(cmd_in, stdout=subprocess.PIPE)
    pout = subprocess.Popen(cmd_out, stdin=subprocess.PIPE)
    sty = Stylizer(cote=cote)
    taille = w * h * 3
    n, t0 = 0, time.time()
    while True:
        buf = pin.stdout.read(taille)
        if len(buf) < taille:
            break
        img = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        pout.stdin.write(sty(img).tobytes())
        n += 1
        if log and n % 15 == 0:
            print(f"\r{n} images, {(time.time() - t0) / n:.2f} s/image", end="", file=sys.stderr)
    pin.wait()
    pout.stdin.close()
    pout.wait()
    if log:
        print(f"\r{n} images, {(time.time() - t0) / max(n, 1):.2f} s/image -> {dst}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Stylisation BD / cel-shading d'une vidéo de rugby")
    ap.add_argument("entree")
    ap.add_argument("sortie")
    ap.add_argument("--start", type=float, default=0.0, help="début (s)")
    ap.add_argument("--dur", type=float, default=None, help="durée (s)")
    ap.add_argument("--cote", type=int, default=540, help="petit côté de l'image de calcul (px)")
    a = ap.parse_args()
    stylize_video(a.entree, a.sortie, a.start, a.dur, a.cote)


if __name__ == "__main__":
    main()
