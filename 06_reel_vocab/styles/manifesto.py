#!/usr/bin/env python3
"""
Style « Manifesto torinese » : affiche lithographique Liberty / Déco
(Codognato, Dudovich, Cappiello, affiches sportives italiennes des années 1930).

Principe
  1. la carte d'étiquettes STABLE vient du Style ligne claire (../stylize.py
     + segmentation MediaPipe des joueurs, visages aplatis, foule repérée)
  2. chaque étiquette est ramenée à un jeu fixe de 8 « encres » litho :
     papier crème, brun-noir, azur, vert Springbok, or, rouge vermillon,
     vert pelouse, chair ; aucune autre couleur ne peut apparaître
  3. tribunes / décor -> un seul grand aplat vermillon à rayons Déco
  4. contour brun-noir épais (silhouette plus épaisse que les détails)
  5. impression : repérage décalé des encres, grain de pierre litho FIXE
     (pas de scintillement), fibres du papier, vignettage chaud, marge papier

Usage : python3 manifesto.py ENTREE SORTIE [--start S --dur D]
        (image -> image, vidéo -> vidéo même taille/cadence, sans son)
Import : from manifesto import Style ; st = Style() ; out = st(rgb) ; st.reset()
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.dirname(ICI))
import stylize as B          # noqa: E402  (non modifié)
import ligne_claire as LC    # noqa: E402  (non modifié : on réutilise sa carte d'étiquettes)

# --- Encres (RVB) -------------------------------------------------------------
PAPIER = (238, 226, 196)      # papier crème (= blanc des maillots, non imprimé)
TRAIT = (50, 32, 26)          # brun-noir du trait litho
AZUR = (34, 104, 184)         # Italie
VERT_SB = (22, 92, 62)        # Springbok
OR = (226, 168, 44)           # or Springbok
FOND = (204, 74, 44)          # vermillon : grand aplat de fond
FOND2 = (188, 62, 38)         # rayon un peu plus sombre (même encre, surimpression)
PELOUSE = (138, 158, 84)      # vert olive clair de la pelouse
CHAIR = (226, 166, 118)       # chair unique, sans traits
BLEU_NUIT = (36, 46, 82)      # marine (shorts, ombres bleues)
ENCRES = [PAPIER, TRAIT, AZUR, VERT_SB, OR, FOND, PELOUSE, CHAIR, BLEU_NUIT]
E_PAP, E_TR, E_AZ, E_SB, E_OR, E_FD, E_PEL, E_CH, E_NUIT = range(len(ENCRES))
I_FOND2 = len(ENCRES)         # indice « rayon » (même zone que le fond)


class Style(LC.Style):
    """Stylisation « manifesto », avec mémoire temporelle (vidéo).

    epaisseur : trait de détail en px pour 1080 de large (silhouette ~1,8x)
    rayons    : rayons Déco dans l'aplat de fond
    marge     : marge papier autour de l'image (fraction de la largeur, 0 = aucune)
    """

    def __init__(self, epaisseur=3.6, temporel=True, cote=540, rayons=True, marge=0.022):
        super().__init__(epaisseur=epaisseur, temporel=temporel, cote=cote)
        self.rayons = rayons
        self.marge = marge
        self._tex = {}                # textures fixes par taille d'image
        self._encre_cache = None

    def reset(self):
        super().reset()
        self._encre_cache = None
        self._prev_fond = None

    # -- étiquette de base -> encre (recalculé seulement si la palette change)
    def _encres(self):
        b = self.base
        if self._encre_cache is not None and self._encre_cache[0] is b.palette:
            return self._encre_cache[1]
        lab = b.palette
        n = len(lab)
        enc_lab = B._lab(ENCRES)
        t = np.zeros(n, np.int32)
        for i in range(n):
            L, a, bb = lab[i]
            c = np.hypot(a, bb)
            h = np.degrees(np.arctan2(bb, a)) % 360
            if L < 30:
                t[i] = E_TR                                  # sombres -> trait
            elif c < 14:
                t[i] = E_PAP if L > 62 else (E_NUIT if L < 45 else E_TR if L < 38 else E_PAP)
            else:                                            # tons colorés : encre la plus proche
                cand = [E_AZ, E_SB, E_OR, E_FD, E_CH, E_NUIT, E_PAP]
                d = np.linalg.norm((enc_lab[cand] - lab[i]) * [0.5, 1, 1], axis=1)
                t[i] = cand[int(np.argmin(d))]
                if 15 < h < 75 and t[i] in (E_FD, E_OR) and c < 45 and L < 75:
                    t[i] = E_CH                              # bruns / orangés ternes -> chair
        fixes = {B.I_AZ: E_AZ, B.I_AZO: E_AZ, B.I_SB: E_SB, B.I_SBO: E_SB, B.I_OR: E_OR,
                 B.I_ORO: E_OR, B.I_BLANC: E_PAP, B.I_PEL: E_PEL, 8: E_PAP, 9: E_TR,
                 10: E_NUIT, 16: E_FD, 17: E_FD}
        for i, e in fixes.items():
            t[i] = e
        for i in list(B.PEAUX) + list(range(b.n_normal + B.N_FOULE, n)):
            t[i] = E_CH                                      # peaux et visages aplatis
        for i in b.i_foule:
            t[int(i)] = E_FD                                 # tribunes -> aplat de fond
        self._encre_cache = (b.palette, t)
        return t

    # -- textures fixes : grain litho, fibres, vignettage, rayons
    def _textures(self, H, W):
        k = (H, W)
        if k in self._tex:
            return self._tex[k]
        rng = np.random.default_rng(1902)                    # Esposizione di Torino
        grain = rng.random((H, W), dtype=np.float32)
        grain = cv2.GaussianBlur(grain, (0, 0), 0.7)
        grain = (grain - grain.mean()) / (grain.std() + 1e-6)
        fib = cv2.resize(rng.random((H // 10 + 2, W // 8 + 2), dtype=np.float32), (W, H),
                         interpolation=cv2.INTER_CUBIC)
        fib = cv2.GaussianBlur(fib, (0, 0), 3) - 0.5
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
        vign = np.clip((r - 0.65) / 0.75, 0, 1) ** 1.6
        # rayons Déco partant d'un soleil hors champ en haut
        ang = np.degrees(np.arctan2(xx - W * 0.5, yy + H * 0.35))
        ray = (np.floor(ang / 7.0) % 2).astype(bool)
        self._tex[k] = (grain, fib, vign, ray)
        return self._tex[k]

    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        pal_avant = self.base.palette
        sortie_base = self.base(rgb)                         # état temporel du Stylizer
        if pal_avant is not None and self.base.palette is not pal_avant \
                and len(self.base.palette) <= self.base.n_normal + B.N_FOULE:
            self.pers.reset()                                # changement de plan
            self._prev_e = None
        etiq = self.base.prev["etiq"].copy()
        h, w = etiq.shape
        prob = self.pers(rgb, w, h)
        self._table()                                        # (prépare les tons de foule)
        pers = np.zeros((h, w), bool)
        if prob is not None:
            etiq, pers = self._joueurs(rgb, etiq, prob)
        self._prev_e = etiq
        e = self._encres()[etiq]

        # nettoyage : miettes hors joueurs, petits îlots dans les grands aplats
        e = np.where(pers, B.Stylizer._mode(e, 3), B.Stylizer._mode(B.Stylizer._mode(e, 5), 7))
        for fond_i in (E_FD, E_PEL):
            n, cc, st, _ = cv2.connectedComponentsWithStats((e != fond_i).astype(np.uint8), connectivity=8)
            pet = st[:, cv2.CC_STAT_AREA] < 0.0006 * w * h
            pet[0] = False
            if n > 1 and pet.any():
                m = pet[cc] & ~pers
                ent = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~m
                if ent.any() and (e[ent] == fond_i).mean() > 0.6:
                    e[m] = fond_i
        # dans un joueur, pas de vermillon (tons bruns/rouges -> chair)
        e[pers & (e == E_FD)] = E_CH
        # grandes masses sombres hors joueurs (toit, panneaux) -> aplat de fond
        n, cc, st, _ = cv2.connectedComponentsWithStats((e == E_TR).astype(np.uint8), connectivity=8)
        if n > 1:
            touche = np.bincount(cc[pers], minlength=n) > 0.05 * st[:, cv2.CC_STAT_AREA]
            gros = (st[:, cv2.CC_STAT_AREA] > 0.004 * w * h) & ~touche
            gros[0] = False
            e[gros[cc]] = E_FD
        # fond (tribunes) : bords simplifiés et lissés dans le temps (pas de « gouttes »)
        fd = (e == E_FD).astype(np.float32)
        fd = cv2.GaussianBlur(fd, (0, 0), 4)
        if self._prev_fond is not None and self._prev_fond.shape == fd.shape:
            fd = 0.6 * fd + 0.4 * self._prev_fond
        self._prev_fond = fd
        fdm = cv2.morphologyEx((fd > 0.5).astype(np.uint8), cv2.MORPH_OPEN,
                               B._disque(int(41 * min(h, w) / 540))).astype(bool) & ~pers
        e[(e == E_FD) & ~fdm] = E_PEL
        e[fdm & ~pers & np.isin(e, (E_PEL, E_PAP, E_TR))] = E_FD
        # décor accroché aux tribunes (panneaux, toit, objets) -> absorbé dans le fond
        dec = (~pers & (e != E_PEL) & (e != E_PAP)).astype(np.uint8)
        n, cc = cv2.connectedComponents(dec, connectivity=8)
        if n > 1:
            ok = np.zeros(n, bool)
            ok[np.unique(cc[(e == E_FD) & (dec > 0)])] = True
            ok[0] = False
            e[ok[cc]] = E_FD
        # vermillon enclavé (ne touchant pas le haut de l'image) -> pelouse
        n, cc = cv2.connectedComponents((e == E_FD).astype(np.uint8), connectivity=8)
        if n > 1:
            haut = np.zeros(n, bool)
            haut[np.unique(cc[:max(2, h // 25)])] = True
            haut[np.unique(cc[:h // 2, :2])] = True          # ou les bords latéraux, en haut
            haut[np.unique(cc[:h // 2, -2:])] = True
            haut[0] = True
            e[~haut[cc]] = E_PEL

        # aplats en pleine résolution, bords arrondis
        enc = np.array(ENCRES + [FOND2], np.uint8)
        ef = cv2.resize(e.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) if (h, w) != (H, W) else e.astype(np.uint8)
        ef = cv2.medianBlur(ef, min(7, max(3, int(round(W / w * 1.6)) | 1)))
        grain, fib, vign, ray = self._textures(H, W)
        if self.rayons:
            ef = np.where((ef == E_FD) & ray, I_FOND2, ef).astype(np.uint8)
        coul = enc[ef].astype(np.float32)

        # contours : frontières entre encres ; silhouette (contre fond/pelouse) plus épaisse
        f = W / 1080.0
        z = W / w
        bord = np.zeros((h, w), np.float32)
        sil = np.zeros((h, w), np.float32)
        decor = np.isin(e, (E_FD, E_PEL))
        for ax in (0, 1):
            a = e[1:] if ax == 0 else e[:, 1:]
            c = e[:-1] if ax == 0 else e[:, :-1]
            da = decor[1:] if ax == 0 else decor[:, 1:]
            dc = decor[:-1] if ax == 0 else decor[:, :-1]
            diff = a != c
            s = diff & (da ^ dc)
            sl = (slice(None, -1), slice(None)) if ax == 0 else (slice(None), slice(None, -1))
            bord[sl][diff & ~(da & dc)] = 1
            sil[sl][s] = 1
        k = min(h, w) / 540.0
        bord = B.Stylizer._sans_miettes(bord, int(12 * k))
        sil = B.Stylizer._sans_miettes(sil, int(12 * k))

        def trait(carte, ep):
            t = cv2.resize(carte, (W, H), interpolation=cv2.INTER_LINEAR) if (h, w) != (H, W) else carte
            t = cv2.GaussianBlur(t, (0, 0), max(0.8, 0.8 * z))
            mx = float(t.max()) if t.max() > 0 else 1.0
            axe = (t > 0.3 * mx).astype(np.uint8)
            dt = cv2.distanceTransform(1 - axe, cv2.DIST_L2, 3)
            return np.clip(0.5 * ep * f + 0.5 - dt, 0, 1)

        t = np.maximum(trait(bord, self.epaisseur), trait(sil, self.epaisseur * 1.5))
        # lignes du terrain (rendu de base) : papier non imprimé sur la pelouse
        pel = cv2.resize((e == E_PEL).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        a_l = np.clip((sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20)
                      / (B.BLANC[0] - B.PELOUSE[0] - 40), 0, 1) * pel
        # seulement les traits fins (les grandes plages claires ne sont pas des lignes)
        r_l = max(5, int(14 * W / 1080)) | 1
        a_l = np.clip(a_l - cv2.morphologyEx(a_l, cv2.MORPH_OPEN, B._disque(r_l)), 0, 1)

        # repérage décalé : la couleur glisse de quelques px sous le trait
        d = max(1, int(round(3 * f)))
        M = np.float32([[1, 0, d], [0, 1, -d * 0.6]])
        coul = cv2.warpAffine(coul, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        coul += (np.array(PAPIER, np.float32) - coul) * a_l[..., None]

        # encre posée sur papier : densité variable (grain de pierre), papier fibreux
        pap = np.array(PAPIER, np.float32)
        dens = np.clip(0.93 + 0.05 * grain + 0.12 * fib, 0.7, 1.0)[..., None]
        out = pap + (coul - pap) * dens
        tr = np.array(TRAIT, np.float32)
        ta = (t * np.clip(0.92 + 0.08 * grain, 0, 1))[..., None]
        out = out * (1 - ta) + tr * ta
        # papier : légère teinte de fibres + grain fin général
        out += (6 * fib + 3.0 * grain)[..., None] * np.array([1, 0.95, 0.8], np.float32)
        # vignettage chaud (papier jauni sur les bords)
        out = out * (1 - 0.22 * vign[..., None]) + np.array([120, 80, 40], np.float32) * 0.22 * vign[..., None]
        # marge papier non imprimée, bord légèrement irrégulier
        if self.marge > 0:
            m = int(round(self.marge * W))
            msk = np.zeros((H, W), np.float32)
            msk[m:H - m, m:W - m] = 1
            msk = cv2.GaussianBlur(msk, (0, 0), 1.0)
            msk = np.clip((msk - 0.5) * 4 + 0.15 * grain + 0.5, 0, 1)[..., None]
            papier = pap + (5 * fib + 3 * grain)[..., None]
            out = papier * (1 - msk) + out * msk
        return np.clip(out, 0, 255).astype(np.uint8)


# --- Entrées / sorties (on réutilise celles de ligne_claire avec ce Style) ---------
def traiter_video(src, dst, start=0.0, dur=None, log=True):
    LC.Style, ancien = Style, LC.Style
    try:
        LC.traiter_video(src, dst, start, dur, log)
    finally:
        LC.Style = ancien


def main():
    ap = argparse.ArgumentParser(description="Style « manifesto » (affiche litho turinoise)")
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
