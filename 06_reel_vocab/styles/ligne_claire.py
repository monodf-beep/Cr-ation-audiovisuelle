#!/usr/bin/env python3
"""
Style « ligne claire » (BD franco-belge) pour les plans de rugby — CPU local.

Principe
  1. le Stylizer de ../stylize.py fournit, image par image, une carte
     d'étiquettes de couleur STABLE dans le temps (flot optique, hystérésis,
     palette figée par plan, visages YuNet aplatis, pelouse/foule/lignes)
  2. on refait ici tout le rendu :
     - palette « ligne claire » : aplats francs, sans ombre (les tons
       d'ombre sont fusionnés dans leur ton clair), noirs relevés,
       blancs papier, pelouse d'un vert uni, foule réduite à 2 tons pastel
     - couleurs voisines fusionnées (moins de taches, moins de traits)
     - contour noir d'épaisseur uniforme, tiré de la carte d'étiquettes
       (donc d'une image déjà débruitée : pas de liseré ni de crénelage)
     - lignes du terrain reprises du rendu de base, en blanc papier
  3. visages : aplat chair sans yeux/bouche/barbe + un simple contour

Usage : python3 ligne_claire.py ENTREE SORTIE [--start S --dur D]
        (image -> image, vidéo -> vidéo même taille/cadence, sans son)
Import : from ligne_claire import Style ; st = Style() ; out = st(rgb)
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

# --- Palette ligne claire (RVB) ----------------------------------------------
PAPIER = (250, 247, 238)       # blanc « papier »
ENCRE = (22, 20, 24)           # trait noir
PELOUSE_LC = (118, 176, 92)    # vert pelouse uni, un peu jaune (façon album)
AZUR_LC = (38, 116, 206)       # Italie
SB_VERT_LC = (22, 108, 70)     # Springbok
OR_LC = (246, 186, 40)
FOULE_LC = [(196, 204, 214), (226, 222, 208)]  # bande de tribune pastel (sombre / clair)


def _lab1(rgb):
    return B._lab([rgb])[0]


MODELE_SEG = os.path.join(os.path.dirname(ICI), "modeles", "selfie_multiclass_256x256.tflite")
# indices de la palette de base utilisables pour les tenues (maillots, shorts, chaussettes)
# (pas de gris clair ni de tons d'ombre : un maillot blanc reste blanc, sans modelé)
KIT = [B.I_AZ, B.I_SB, B.I_OR, B.I_BLANC, 9, 10, 16]


_SEG = None


class _Personnes:
    """Segmentation MediaPipe « selfie multiclass » (fond, cheveux, peau du corps,
    peau du visage, vêtements, accessoires), sur tuiles carrées, lissée dans le temps."""

    def __init__(self):
        self.seg = None
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
            self.mp = mp
            opt = vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=MODELE_SEG),
                                               output_confidence_masks=True)
            global _SEG
            if _SEG is None:           # un seul segmenteur par processus
                _SEG = vision.ImageSegmenter.create_from_options(opt)
            self.seg = _SEG
        except Exception as ex:  # sans MediaPipe : on se contente du Stylizer de base
            print(f"! segmentation indisponible ({ex})", file=sys.stderr)
        self.reset()

    def reset(self):
        self.prev = None

    def __call__(self, rgb, w, h):
        """-> probabilités (h, w, 6) à la résolution de calcul, ou None."""
        if self.seg is None:
            return None
        H, W = rgb.shape[:2]
        c = min(H, W)
        n = max(1, int(np.ceil(max(H, W) / c - 0.05)))   # 9:16 -> 2 tuiles qui se chevauchent
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
        if self.prev is not None and self.prev.shape == p.shape:   # lissage temporel
            p = 0.55 * p + 0.45 * self.prev
        self.prev = p
        return p


class Style:
    """Stylisation ligne claire, avec mémoire temporelle (vidéo).

    epaisseur : épaisseur du trait en px pour une image de 1080 de large
    temporel  : False pour une image isolée
    """

    def __init__(self, epaisseur=3.2, temporel=True, cote=540):
        self.epaisseur = epaisseur
        self.base = B.Stylizer(cote=cote, temporel=temporel)
        self.pers = _Personnes()
        self.reset()

    def reset(self):
        self.base.reset()
        self.pers.reset()
        self._cache = None             # table de couleurs ligne claire
        self._prev_e = None

    # -- palette ligne claire, recalculée seulement si la palette de base change
    def _table(self):
        b = self.base
        n = len(b.palette)
        if self._cache is not None and self._cache[0] == n and self._cache[3] is b.palette:
            return self._cache[1], self._cache[2], self._cache[4]
        lab = b.palette.copy()
        lc = lab.copy()
        # tons ordinaires : noirs relevés, contraste adouci, saturation nette
        lc[:, 0] = 18 + 0.84 * lab[:, 0]
        lc[:, 1:] = lab[:, 1:] * 1.05
        fixes = {B.I_AZ: AZUR_LC, B.I_AZO: AZUR_LC, B.I_SB: SB_VERT_LC, B.I_SBO: SB_VERT_LC,
                 B.I_OR: OR_LC, B.I_ORO: OR_LC, B.I_BLANC: PAPIER, B.I_PEL: PELOUSE_LC}
        for i, c in fixes.items():
            lc[i] = _lab1(c)
        # peaux (et tons de visage ajoutés par le Stylizer) : chair claire, sans modelé
        for i in list(B.PEAUX) + list(range(b.n_normal + B.N_FOULE, n)):
            lc[i, 0] = np.clip(lab[i, 0] + 7, 40, 84)
        foule = set(int(i) for i in b.i_foule)
        # foule : deux tons pastel selon la clarté d'origine
        for r, i in enumerate(sorted(foule, key=lambda j: lab[j, 0])):
            lc[i] = _lab1(FOULE_LC[0 if r < 2 else 1])
        # fusion des couleurs voisines (glouton, ΔE < 9) -> représentant
        rep = np.arange(n)
        prot = {B.I_AZ, B.I_SB, B.I_OR, B.I_PEL, B.I_BLANC}
        ordre = sorted(range(n), key=lambda i: (i not in prot, i))
        reps = []
        for i in ordre:
            if i in foule:
                continue
            for j in reps:
                if np.linalg.norm(lc[i] - lc[j]) < 9 and not (i in prot and j in prot):
                    rep[i] = j
                    break
            else:
                reps.append(i)
        for i in foule:                # deux tons de foule -> deux représentants
            rep[i] = min(j for j in foule if np.allclose(lc[j], lc[i]))
        rgb = B._rgb_of_lab(lc)
        self._cache = (n, rep, rgb, b.palette, foule)
        return rep, rgb, foule

    # -- joueurs : corrige la carte d'étiquettes là où la segmentation voit une personne
    def _joueurs(self, rgb, etiq, prob):
        b = self.base
        h, w = etiq.shape
        petit = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
        lisse = cv2.bilateralFilter(cv2.bilateralFilter(petit, 7, 30, 5), 7, 30, 5)
        lab = cv2.cvtColor(lisse.astype(np.float32) / 255.0, cv2.COLOR_RGB2Lab)
        cl = np.argmax(prob, axis=2)
        pers = (1.0 - prob[..., 0]) > 0.5
        pers = cv2.morphologyEx(pers.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        if pers.sum() < 0.002 * w * h:
            pers = np.zeros((h, w), bool)
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
        # « foule » enclavée (ne touchant pas le haut de l'image) = en fait des joueurs
        n, cc = cv2.connectedComponents(foule.astype(np.uint8), connectivity=8)
        if n > 1:
            haut = np.zeros(n, bool)
            haut[np.unique(cc[:max(2, h // 20)])] = True
            haut[0] = True
            encl = ~haut[cc]
            norm0 = [i for i in range(b.n_normal) if i != B.I_PEL]
            if encl.any():
                e[encl] = proche(norm0, encl)
                foule &= ~encl
        # vêtements / accessoires : couleurs de tenue uniquement
        habit = pers & np.isin(cl, (4, 5, 0))
        e[habit] = proche(KIT, habit)
        hsv = cv2.cvtColor(petit, cv2.COLOR_RGB2HSV)
        Hh, Ss, Vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        azur = habit & (Hh >= 97) & (Hh <= 122) & (Ss > 90) & (Vv > 70)
        sbv = habit & (Ss > 60) & (Vv > 18) & (Hh >= 35) & (Hh <= 90) & (Vv < 170)
        orr = habit & (Hh >= 15) & (Hh <= 32) & (Ss > 100) & (Vv > 110)
        e[azur], e[sbv], e[orr] = B.I_AZ, B.I_SB, B.I_OR
        # plis sombres d'un maillot uni -> couleur du maillot (pas de modelé)
        sombre = habit & np.isin(e, (9, 10)) & (lab[..., 0] < 40)
        for T in (B.I_SB, B.I_AZ):
            dens = cv2.blur((e == T).astype(np.float32), (15, 15))
            m = sombre & (dens > 0.3)
            e[m] = T
        # cheveux : tons non-équipe ; les zones « foule » dans une personne sont recolorées
        norm = [i for i in range(b.n_normal) if i not in (B.I_PEL, B.I_AZ, B.I_AZO, B.I_SB, B.I_SBO)]
        chev = pers & (cl == 1)
        e[chev] = proche(norm, chev)
        reste = pers & foule & ~habit & ~chev
        if reste.any():
            e[reste] = proche(norm, reste)
        # peau (visage + corps) : un seul ton chair par zone, trous (yeux, bouche, barbe) bouchés
        L, A, Bb = lab[..., 0], lab[..., 1], lab[..., 2]
        teinte = np.degrees(np.arctan2(Bb, A)) % 360
        chroma = np.hypot(A, Bb)
        chair = (teinte > 18) & (teinte < 85) & (chroma > 9) & (L > 12)
        # peau du corps : seulement si la couleur est déjà une chair (évite les plis de maillot)
        peau = pers & (((cl == 2) & np.isin(etiq, B.PEAUX)) | (cl == 3)) & chair
        visage = (cl == 3) & pers
        vf = visage.astype(np.uint8)
        n, cc, st, _ = cv2.connectedComponentsWithStats(1 - vf, connectivity=4)
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
            med[0] = np.percentile(lab[m][:, 0], 70)
            d = np.linalg.norm((pal[tons] - med) * wl, axis=1)
            t = int(tons[np.argmin(d)])
            # hystérésis : on garde le ton précédent s'il reste plausible
            if self._prev_e is not None and self._prev_e.shape == e.shape:
                pv = self._prev_e[m]
                pv = pv[np.isin(pv, tons)]
                if len(pv):
                    t0 = int(np.bincount(pv).argmax())
                    if d[list(tons).index(t0)] < d.min() + 12:
                        t = t0
            e[m] = t
        # nettoyage des tenues : filtre de mode (aplats francs, numéros conservés)
        e2 = B.Stylizer._mode(B.Stylizer._mode(e, 5), 7)
        e = np.where(pers & ~peau, e2, e)
        # gros plan : le décor (hors joueurs et pelouse) devient une bande pastel unie
        if pers.mean() > 0.15:
            herbe = (teinte > 95) & (teinte < 170) & (chroma > 12)
            fond = ~cv2.dilate(pers.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) \
                & (e != B.I_PEL) & ~herbe
            Lf = cv2.GaussianBlur(lab[..., 0], (0, 0), 6)
            seuil = np.median(Lf[fond]) if fond.any() else 50
            fs = sorted(b.i_foule, key=lambda j: b.palette[j, 0])
            e[fond] = np.where(Lf[fond] < seuil, fs[0], fs[-1])
        return e, pers

    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        pal_avant = self.base.palette
        sortie_base = self.base(rgb)   # met à jour l'état temporel (étiquettes)
        if pal_avant is not None and self.base.palette is not pal_avant \
                and len(self.base.palette) <= self.base.n_normal + B.N_FOULE:
            self.pers.reset()          # changement de plan détecté par le Stylizer
            self._prev_e = None
        etiq = self.base.prev["etiq"].copy()
        h, w = etiq.shape
        prob = self.pers(rgb, w, h)
        rep, pal, foule = self._table()
        pers = np.zeros((h, w), bool)
        if prob is not None:
            etiq, pers = self._joueurs(rgb, etiq, prob)
        self._prev_e = etiq
        e = rep[etiq]

        # petites miettes isolées -> couleur majoritaire du voisinage
        e = np.where(pers, e, B.Stylizer._mode(e, 3))
        # îlots minuscules posés sur la pelouse (touffes, reflets) -> pelouse
        ipel = rep[B.I_PEL]
        n, cc, st, _ = cv2.connectedComponentsWithStats((e != ipel).astype(np.uint8), connectivity=8)
        pet = st[:, cv2.CC_STAT_AREA] < 0.00025 * w * h
        pet[0] = False
        if n > 1 and pet.any():
            m = pet[cc]
            voisin = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
            # seulement si l'îlot est entouré de pelouse
            ok = np.zeros(n, bool)
            for i in np.nonzero(pet)[0]:
                ok[i] = True
            tot = np.bincount(cv2.dilate(cc.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)[voisin], minlength=n)
            vert = np.bincount(cv2.dilate(cc.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)[voisin & (e == ipel)], minlength=n)
            ok &= vert >= 0.8 * np.maximum(tot, 1)
            e[ok[cc]] = ipel

        # contours : frontières entre aplats de couleurs différentes,
        # sauf à l'intérieur de la foule (tribune = simple bande)
        en_foule = np.isin(e, list(foule))
        pl = B._lab(pal.tolist())[e]
        bord = np.zeros((h, w), np.float32)
        for ax in (0, 1):
            a = pl[1:] if ax == 0 else pl[:, 1:]
            c = pl[:-1] if ax == 0 else pl[:, :-1]
            fa = en_foule[1:] if ax == 0 else en_foule[:, 1:]
            fc = en_foule[:-1] if ax == 0 else en_foule[:, :-1]
            diff = (np.linalg.norm(a - c, axis=2) > 8) & ~(fa & fc)
            if ax == 0:
                bord[:-1][diff] = 1
            else:
                bord[:, :-1][diff] = 1
        # traits trop courts (bruit, joueurs minuscules) supprimés
        k = min(h, w) / 540.0
        bord = B.Stylizer._sans_miettes(bord, int(10 * k))

        # aplats en pleine résolution (bords lissés)
        coul = pal[e]
        if (h, w) != (H, W):
            coul = cv2.resize(coul, (W, H), interpolation=cv2.INTER_NEAREST)
        r = max(3, int(round(W / w * 1.6)) | 1)
        coul = cv2.medianBlur(coul, min(r, 7))

        # lignes du terrain : reprises du rendu de base, posées en blanc papier
        pel = cv2.resize((e == rep[B.I_PEL]).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        a_l = np.clip((sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20)
                      / (B.BLANC[0] - B.PELOUSE[0] - 40), 0, 1) * pel
        # trait : épaisseur uniforme (seuil doux sur une carte agrandie et floutée)
        # (axe lissé du trait, puis épaisseur fixée par transformée de distance)
        f = min(W, H) / 1080.0
        z = W / w
        t = cv2.resize(bord, (W, H), interpolation=cv2.INTER_LINEAR) if (h, w) != (H, W) else bord
        t = cv2.GaussianBlur(t, (0, 0), max(0.8, 0.8 * z))
        axe = (t > 0.5 * float(t.max() if t.max() > 0 else 1) * 0.6).astype(np.uint8)
        dt = cv2.distanceTransform(1 - axe, cv2.DIST_L2, 3)
        demi = max(0.0, 0.5 * max(1.2, self.epaisseur * f) - 0.5 * z * 0.5)
        t = np.clip(demi + 0.5 - dt, 0, 1)

        out = coul
        for a, c in ((a_l, PAPIER), (t, ENCRE)):
            a = np.ascontiguousarray(a, np.float32)
            plein = np.empty_like(out)
            plein[:] = c
            out = cv2.blendLinear(plein, out, a, 1.0 - a)
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
    ap = argparse.ArgumentParser(description="Style ligne claire (BD franco-belge)")
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
