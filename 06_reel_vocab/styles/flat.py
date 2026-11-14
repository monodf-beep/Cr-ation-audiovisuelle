#!/usr/bin/env python3
"""
Style « flat design / motion design vectoriel » (façon infographie animée).

Principe (CPU seul, s'appuie sur ../stylize.py sans le modifier)
  1. le Stylizer de base fournit des étiquettes de couleur stables dans le
     temps (flot optique + hystérésis), la pelouse, la foule, les lignes, et
     les visages (YuNet) déjà remplis d'un aplat chair
  2. chaque étiquette est ramenée à une palette « flat » très réduite :
     maillots (couleur + ombre), blanc, un ton chair sans détail, quelques
     neutres ; la pelouse = un vert graphique ; les tribunes = un dégradé doux
  3. option MediaPipe (selfie multiclass) : peau du visage forcée en aplat,
     cheveux en un ton sombre -> aucun trait du visage
  4. contours « vectoriels » : masques par couleur floutés puis argmax en
     pleine résolution (courbes lisses, pas de crénelage ni d'escalier)
  5. lignes du terrain : blanc net (seuil doux), pas de contour noir

Usage  : python3 flat.py ENTREE SORTIE [--start S --dur D]
         (image -> image, vidéo -> vidéo même taille / même cadence, sans son)
Import : from flat import Style ; st = Style() ; out = st(rgb) ; st.reset()
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
RACINE = os.path.dirname(ICI)
sys.path.insert(0, RACINE)
import stylize as B  # noqa: E402  (Stylizer de base, non modifié)

MODELE_SEG = os.path.join(RACINE, "modeles", "selfie_multiclass_256x256.tflite")

# --- Palette flat (RVB) ------------------------------------------------------
PELOUSE = (88, 168, 86)
LIGNE = (250, 250, 246)
TRIB_HAUT = (54, 62, 96)        # dégradé des tribunes (haut -> bas)
TRIB_BAS = (102, 112, 146)
AZUR, AZUR_O = (34, 124, 226), (20, 84, 172)
VERT, VERT_O = (20, 112, 74), (10, 74, 50)
OR, OR_O = (250, 192, 44), (214, 150, 28)
BLANC, BLANC_O = (246, 246, 242), (196, 204, 216)
PEAU_C, PEAU_M, PEAU_F = (236, 190, 156), (200, 146, 110), (132, 90, 66)
SOMBRE = (38, 40, 52)           # cheveux, chaussures, noir
MARINE = (30, 36, 60)
GRIS = (150, 158, 172)
ROUGE = (218, 64, 62)
ORANGE = (238, 112, 48)
JAUNE = (226, 222, 60)

COULEURS = [PELOUSE, AZUR, AZUR_O, VERT, VERT_O, OR, OR_O, BLANC, BLANC_O,
            PEAU_C, PEAU_M, PEAU_F, SOMBRE, MARINE, GRIS, ROUGE, JAUNE, TRIB_HAUT, ORANGE]
(F_PEL, F_AZ, F_AZO, F_VE, F_VEO, F_OR, F_ORO, F_BL, F_BLO,
 F_PC, F_PM, F_PF, F_SO, F_MA, F_GR, F_RO, F_JA, F_TRIB, F_ORA) = range(len(COULEURS))
PEAUX_F = [F_PC, F_PM, F_PF]
# couleurs « génériques » pour tout ce qui n'est ni équipe, ni peau, ni décor
GENERIQUES = [F_BL, F_BLO, F_SO, F_MA, F_GR, F_RO, F_JA, F_AZ, F_VE, F_OR]

_SEG = None


class _Personnes:
    """Segmentation MediaPipe (fond, cheveux, peau corps, peau visage, habits,
    accessoires) sur tuiles carrées, lissée dans le temps. None si absent."""

    def __init__(self):
        self.seg = None
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
            global _SEG
            if _SEG is None:
                opt = vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=MODELE_SEG),
                                                   output_confidence_masks=True)
                _SEG = vision.ImageSegmenter.create_from_options(opt)
            self.mp, self.seg = mp, _SEG
        except Exception as ex:
            print(f"! segmentation indisponible ({ex})", file=sys.stderr)
        self.reset()

    def reset(self):
        self.prev = None

    def __call__(self, rgb, w, h):
        if self.seg is None:
            return None
        H, W = rgb.shape[:2]
        c = min(H, W)
        n = max(1, int(np.ceil(max(H, W) / c - 0.05)))
        acc = np.zeros((h, w, 6), np.float32)
        cnt = np.zeros((h, w, 1), np.float32)
        s = w / W
        for i in range(n):
            o = 0 if n == 1 else round(i * (max(H, W) - c) / (n - 1))
            tuile = rgb[o:o + c] if H >= W else rgb[:, o:o + c]
            t = np.ascontiguousarray(cv2.resize(tuile, (256, 256), interpolation=cv2.INTER_AREA))
            r = self.seg.segment(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=t))
            m = np.stack([cm.numpy_view().reshape(256, 256) for cm in r.confidence_masks], -1)
            o2, c2 = round(o * s), round(c * s)
            if H >= W:
                o2 = min(o2, h - c2)
                acc[o2:o2 + c2] += cv2.resize(m, (w, c2))
                cnt[o2:o2 + c2] += 1
            else:
                o2 = min(o2, w - c2)
                acc[:, o2:o2 + c2] += cv2.resize(m, (c2, h))
                cnt[:, o2:o2 + c2] += 1
        p = acc / np.maximum(cnt, 1)
        if self.prev is not None and self.prev.shape == p.shape:
            p = 0.55 * p + 0.45 * self.prev
        self.prev = p
        return p


class Style:
    """Flat design vectoriel, avec mémoire temporelle (vidéo).

    temporel : False pour une image isolée
    lissage  : douceur des contours (px de calcul) — plus grand = plus « vecteur »
    """

    def __init__(self, temporel=True, cote=540, lissage=1.6):
        self.base = B.Stylizer(cote=cote, temporel=temporel)
        self.pers = _Personnes()
        self.lissage = lissage
        self.temporel = temporel
        self.lab_f = B._lab(COULEURS)
        self.reset()

    def reset(self):
        self.base.reset()
        self.pers.reset()
        self._pal_id = None
        self._table = None
        self._prev_sc = None

    # -- table : étiquette de base -> couleur flat (recalculée si la palette change)
    def _faire_table(self):
        b = self.base
        pal = b.palette
        t = np.zeros(len(pal), np.int32)
        gen = np.array(GENERIQUES)
        for i, c in enumerate(pal):
            if i < len(B.ANCRES):
                t[i] = {B.I_AZ: F_AZ, B.I_AZO: F_AZO, B.I_SB: F_VE, B.I_SBO: F_VEO, B.I_OR: F_OR,
                        B.I_ORO: F_ORO, B.I_BLANC: F_BL, B.I_PEL: F_PEL, 8: F_BLO, 9: F_SO, 10: F_MA,
                        11: F_PC, 12: F_PC, 13: F_PM, 14: F_PM, 15: F_PF, 16: F_RO, 17: F_RO}[i]
            elif i in b.i_foule:
                t[i] = F_TRIB
            elif i >= b.n_normal + B.N_FOULE:      # ton chair d'un visage suivi
                t[i] = PEAUX_F[int(np.argmin(np.abs(self.lab_f[PEAUX_F, 0] - c[0])))]
            else:                                  # couleur propre au plan -> neutre le plus proche
                d = np.linalg.norm((self.lab_f[gen] - c) * np.array([0.7, 1, 1]), axis=1)
                t[i] = gen[int(np.argmin(d))]
        self._table = t
        self._pal_id = (id(pal), len(pal))

    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        b = self.base
        pal_avant = b.palette
        sortie_base = b(rgb)                       # met à jour l'état temporel
        if pal_avant is not None and b.palette is not pal_avant \
                and len(b.palette) <= b.n_normal + B.N_FOULE:
            self.pers.reset()                      # nouveau plan détecté
            self._prev_sc = None
        if self._pal_id != (id(b.palette), len(b.palette)):
            self._faire_table()
        etiq = b.prev["etiq"]
        h, w = etiq.shape
        k = min(h, w) / 540.0
        e = self._table[etiq]
        lab = b.prev["lab"]
        prob = self.pers(rgb, w, h)
        if prob is not None:
            perso = cv2.dilate(((1 - prob[..., 0]) > 0.5).astype(np.uint8), B._disque(3 * k)).astype(bool)
        else:
            perso = np.zeros((h, w), bool)
        # personnes prises pour de la foule (gros plans texturés) : on les reclasse
        a_refaire = perso & (e == F_TRIB)
        # « foule » sous le bord haut de la pelouse (mêlée texturée, joueurs flous) :
        # impossible en vrai -> reclassée entièrement
        cum = np.cumsum((e == F_PEL), axis=0)
        haut = np.argmax(cum >= max(4, int(6 * k)), axis=0).astype(np.float32)
        haut[cum[-1] < max(4, int(6 * k))] = h
        sous = (np.arange(h)[:, None] > haut[None, :] + 8 * k) & (e == F_TRIB)
        a_refaire_tout = sous & ~a_refaire
        a_refaire |= sous
        # tout ce qui n'est ni pelouse ni tribune : couleur flat la plus proche
        libre = (e != F_PEL) & (e != F_TRIB) | a_refaire
        visage_base = etiq >= b.n_normal + B.N_FOULE
        cand = np.array([F_AZ, F_AZO, F_VE, F_VEO, F_OR, F_ORO, F_BL, F_BLO, F_PC, F_PM, F_PF,
                         F_SO, F_MA, F_GR, F_RO, F_JA, F_ORA])
        X = (lab * np.array([0.6, 1, 1], np.float32)).reshape(-1, 3)
        C = self.lab_f[cand] * np.array([0.6, 1, 1], np.float32)
        d = (X * X).sum(1)[:, None] - 2 * X @ C.T + (C * C).sum(1)[None]
        proche = cand[np.argmin(d, 1)].reshape(h, w)
        # règles d'équipe (seuils HSV du Stylizer de base) sur l'image lissée
        rgb_l = np.clip(cv2.cvtColor(lab, cv2.COLOR_Lab2RGB) * 255, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(rgb_l, cv2.COLOR_RGB2HSV)
        Hh, Ss, Vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        azur = (Hh >= 95) & (Hh <= 122) & (Ss > 100) & (Vv > 70)
        sbv = (Ss > 60) & (Vv > 18) & (((Hh >= 30) & (Hh <= 90) & (Vv < 80)) | ((Hh >= 40) & (Hh <= 85) & (Vv < 150)))
        orr = (Hh >= 17) & (Hh <= 32) & (Ss > 110) & (Vv > 120)
        proche[azur] = np.where(Vv[azur] > 125, F_AZ, F_AZO)
        proche[sbv] = np.where(Vv[sbv] > 62, F_VE, F_VEO)
        proche[orr] = np.where(Vv[orr] > 175, F_OR, F_ORO)
        # étiquettes d'équipe / peau déjà décidées par la base : prioritaires
        sur = np.isin(e, [F_AZ, F_AZO, F_VE, F_VEO, F_OR, F_ORO]) & ~a_refaire
        proche[sur] = e[sur]
        proche[np.isin(e, PEAUX_F) & ~a_refaire] = e[np.isin(e, PEAUX_F) & ~a_refaire]
        proche[visage_base] = e[visage_base]
        # couleur très saturée prise pour de la peau (maillot orange de l'arbitre…)
        vif = np.isin(proche, PEAUX_F) & (np.hypot(lab[..., 1], lab[..., 2]) > 40) & ~visage_base
        if vif.any():
            cv_ = np.array([F_ORA, F_RO, F_OR])
            dv = np.linalg.norm(lab[vif][:, None, :] - self.lab_f[cv_][None], axis=2)
            proche[vif] = cv_[np.argmin(dv, 1)]
        # herbe prise pour un maillot vert (ombres, herbe entre les joueurs) :
        # tout pixel proche de la couleur médiane de la pelouse redevient pelouse
        mp = (e == F_PEL) & (b.prev["etiq"] == B.I_PEL)
        if mp.sum() > 200:
            ref = np.median(lab[mp], axis=0)
            dg = np.linalg.norm((lab - ref) * np.array([0.8, 1, 1], np.float32), axis=2)
            herbe = (dg < 17) & ~visage_base & ~perso & np.isin(proche, [F_VE, F_VEO, F_GR, F_MA, F_BLO, F_JA])
            proche[herbe] = F_PEL
        # halo gris entre un maillot azur et l'herbe -> ombre azur
        pres_az = cv2.dilate(np.isin(proche, [F_AZ, F_AZO]).astype(np.uint8), B._disque(7 * k)).astype(bool)
        proche[pres_az & np.isin(proche, [F_GR, F_MA, F_BLO])] = F_AZO
        # dans la foule reclassée, on ne garde que maillots / blanc / peau (sinon : tribune)
        utile = np.isin(proche, [F_AZ, F_AZO, F_VE, F_VEO, F_OR, F_ORO, F_BL] + PEAUX_F)
        proche[a_refaire & ~a_refaire_tout & ~utile] = F_TRIB
        e = np.where(libre, proche, e)

        # peau : MediaPipe (visage + corps) -> aplat chair ; rouge sur peau = peau
        peau = np.isin(e, PEAUX_F)
        if prob is not None:
            visage = prob[..., 3] > 0.4
            corps = (prob[..., 2] > 0.6) & np.isin(e, [F_RO, F_PC, F_PM, F_PF, F_SO, F_GR, F_BLO])
            cheveux = (prob[..., 1] > 0.5) & ~np.isin(e, [F_AZ, F_AZO, F_VE, F_VEO, F_OR, F_BL])
            e[cheveux & (e != F_PEL)] = F_SO
            peau |= (visage | corps) & (e != F_PEL)
        # taches vertes isolées sur la pelouse (herbe plus sombre) -> pelouse
        vt = np.isin(e, [F_VE, F_VEO]).astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(vt, connectivity=8)
        if n > 1:
            ring = cv2.dilate(vt, np.ones((5, 5), np.uint8)).astype(bool) & ~vt.astype(bool)
            lab_r = cv2.dilate(cc.astype(np.float32), np.ones((5, 5), np.uint8)).astype(np.int32)
            tot = np.bincount(lab_r[ring], minlength=n)
            ver = np.bincount(lab_r[ring & (e == F_PEL)], minlength=n)
            herbe = (ver >= 0.92 * np.maximum(tot, 1)) & (st[:, cv2.CC_STAT_AREA] < 0.02 * w * h)
            herbe[0] = False
            e[herbe[cc] & ~perso] = F_PEL
        # liseré vert sombre autour des joueurs (flou de l'image source) -> pelouse
        for _ in range(2):
            vt = np.isin(e, [F_VE, F_VEO]).astype(np.uint8)
            ouv = cv2.morphologyEx(vt, cv2.MORPH_OPEN, B._disque(2.2 * k))
            fin = (vt > ouv) & cv2.dilate((e == F_PEL).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            e[fin] = F_PEL
        # liseré de « transition » (vert/gris) entre un joueur et la pelouse -> pelouse
        pres_pel = cv2.dilate((e == F_PEL).astype(np.uint8), B._disque(4 * k)).astype(bool)
        pres_j = cv2.dilate(np.isin(e, [F_AZ, F_AZO, F_BL, F_OR] + PEAUX_F).astype(np.uint8),
                            B._disque(4 * k)).astype(bool)
        tr = np.isin(e, [F_VE, F_VEO, F_GR, F_BLO, F_MA]).astype(np.uint8)
        ouv = cv2.morphologyEx(tr, cv2.MORPH_OPEN, B._disque(3 * k)).astype(bool)
        e[tr.astype(bool) & ~ouv & pres_pel & pres_j & ~np.isin(e, PEAUX_F)] = F_PEL
        n, cc = cv2.connectedComponents(cv2.dilate(peau.astype(np.uint8), np.ones((3, 3), np.uint8)), connectivity=8)
        if n > 1:
            cpt = np.stack([np.bincount(cc[e == f], minlength=n) for f in PEAUX_F], 1)
            maj = np.array(PEAUX_F)[np.argmax(cpt, 1)]
            maj[cpt.sum(1) == 0] = F_PM
            e[peau] = maj[cc[peau]]
            # trous dans la peau (yeux, bouche, barbe) comblés
            n2, c2, st, _ = cv2.connectedComponentsWithStats((~peau).astype(np.uint8), connectivity=4)
            bord = np.zeros(n2, bool)
            bord[np.unique(np.concatenate([c2[0], c2[-1], c2[:, 0], c2[:, -1]]))] = True
            trou = ~bord & (st[:, cv2.CC_STAT_AREA] < 0.003 * w * h)
            trou[0] = False
            mt = trou[c2]
            if mt.any():
                f = cv2.dilate(np.where(peau, e, 0).astype(np.uint8), np.ones((5, 5), np.uint8))
                e[mt] = np.where(f[mt] > 0, f[mt], F_PM)
        # simplification : petites miettes absorbées, décor plus simplifié que les joueurs
        decor = np.isin(e, [F_PEL, F_TRIB])
        e1 = B.Stylizer._mode(e, 3)
        e2 = B.Stylizer._mode(e1, int(9 * k) | 1)
        joueur = cv2.dilate((~decor).astype(np.uint8), B._disque(4 * k)).astype(bool)
        e = np.where(joueur, e1, e2)
        # arrière-plan hors personnes et loin de la pelouse (panneaux, tribunes proches) :
        # très simplifié -> grandes formes
        loin = ~perso & ~cv2.dilate((e == F_PEL).astype(np.uint8), B._disque(10 * k)).astype(bool) \
            & (e != F_TRIB)
        if loin.any():
            e3 = B.Stylizer._mode(e, int(17 * k) | 1)
            e[loin] = e3[loin]
        # îlots minuscules sur la pelouse ou en tribune -> fond
        for fond in (F_PEL, F_TRIB):
            n, cc, st, _ = cv2.connectedComponentsWithStats((e != fond).astype(np.uint8), connectivity=8)
            pt = st[:, cv2.CC_STAT_AREA] < 0.00012 * w * h
            pt[0] = False
            m = pt[cc]
            if m.any():
                autour = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
                if (e[autour] == fond).mean() > 0.7:
                    e[m] = fond

        # contours vectoriels : masques par couleur floutés, lissés dans le temps
        pres = np.unique(e)
        sig = self.lissage * k
        sc = np.zeros((len(pres), h, w), np.float32)
        for j, f in enumerate(pres):
            sc[j] = cv2.GaussianBlur((e == f).astype(np.float32), (0, 0), sig)
        idx = np.zeros(len(COULEURS), np.int32) - 1
        idx[pres] = np.arange(len(pres))
        P = self._prev_sc
        if self.temporel and P is not None and P[1].shape[1:] == (h, w) and b.prev is not None:
            # mélange léger avec les scores précédents (recalés par le flot du Stylizer)
            # -> les frontières ne tremblent plus d'un pixel à l'autre
            flux = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST).calc(
                b.prev["gris"], P[2], None) if P[2].shape == b.prev["gris"].shape else None
            if flux is not None:
                gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
                mx, my = gx + flux[..., 0], gy + flux[..., 1]
                for j, f in enumerate(pres):
                    if f in P[0]:
                        av = cv2.remap(P[1][P[0].index(f)], mx, my, cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_REPLICATE)
                        sc[j] = 0.6 * sc[j] + 0.4 * av
        self._prev_sc = (list(pres), sc.copy(), b.prev["gris"])

        # argmax en pleine résolution (scores agrandis en bilinéaire = courbes lisses)
        best = None
        lab_full = np.zeros((H, W), np.uint8)
        for j, f in enumerate(pres):
            s = cv2.resize(sc[j], (W, H), interpolation=cv2.INTER_LINEAR) if (h, w) != (H, W) else sc[j]
            if best is None:
                best = s
                lab_full[:] = f
            else:
                m = s > best
                best = np.maximum(best, s)
                lab_full[m] = f
        coul = np.array(COULEURS, np.uint8)[lab_full]

        # tribunes : dégradé vertical doux (le même pour toute l'image)
        trib = lab_full == F_TRIB
        if trib.any():
            ys = np.nonzero(trib.any(1))[0]
            y0, y1 = ys[0], max(ys[-1], ys[0] + 1)
            a = np.clip((np.arange(H, dtype=np.float32) - y0) / (y1 - y0), 0, 1)[:, None, None]
            grad = (np.array(TRIB_HAUT, np.float32) * (1 - a) + np.array(TRIB_BAS, np.float32) * a)
            coul = np.where(trib[..., None], np.broadcast_to(grad, (H, 1, 3)).astype(np.uint8), coul)

        # anticrénelage des frontières (flou léger seulement près des bords)
        bordure = cv2.morphologyEx(lab_full, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        flou = cv2.GaussianBlur(coul, (0, 0), 0.9 * max(1.0, W / 1080))
        coul = np.where(bordure[..., None], flou, coul)

        # lignes du terrain : reprises du rendu de base, seuil doux -> blanc net
        pel = cv2.resize((e == F_PEL).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        a_l = (sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20) / (B.BLANC[0] - B.PELOUSE[0] - 40)
        a_l = cv2.GaussianBlur(np.clip(a_l, 0, 1) * pel, (0, 0), 1.2 * max(1.0, W / 1080))
        a_l = np.clip((a_l - 0.3) / 0.25, 0, 1)
        # points blancs isolés (reflets, herbe) supprimés : on garde les vrais segments
        n, cc, st, _ = cv2.connectedComponentsWithStats((a_l > 0.5).astype(np.uint8), connectivity=8)
        if n > 1:
            lg = np.maximum(st[:, cv2.CC_STAT_WIDTH], st[:, cv2.CC_STAT_HEIGHT])
            ok = lg > 0.02 * max(W, H)
            ok[0] = False
            a_l = a_l * cv2.dilate(ok[cc].astype(np.uint8), np.ones((5, 5), np.uint8))
        plein = np.empty_like(coul)
        plein[:] = LIGNE
        return cv2.blendLinear(plein, coul, a_l, 1.0 - a_l)


# --- Entrées / sorties -------------------------------------------------------
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
    ap = argparse.ArgumentParser(description="Style flat design / motion design vectoriel")
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
