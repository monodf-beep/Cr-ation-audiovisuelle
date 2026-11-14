#!/usr/bin/env python3
"""
Style « carnet de croquis aquarellé » (reportage dessiné) — CPU local.

Principe
  1. carte d'étiquettes STABLE dans le temps : Stylizer de ../stylize.py
     (flot optique, palette figée par plan, visages YuNet aplatis) corrigée
     par la segmentation de personnes de ligne_claire.py (MediaPipe) :
     tenues forcées aux couleurs d'équipe, peau/visage = un seul ton chair
  2. lavis : chaque aplat devient une couleur diluée (beaucoup de blanc),
     posée avec un léger décalage (« le pinceau déborde »), bords adoucis,
     pigment accumulé sur les bords (auréole), granulation et papier fixés
     à l'écran ; foule = papier nu + lavis très pâle, pelouse = lavis vert clair
  3. trait crayon/encre irrégulier tiré de la carte d'étiquettes (image
     débruitée : pas de liseré), épaisseur et pression variables, deux passes
     légèrement décalées ; « tremblé » volontaire mis à jour à ~10 i/s
  4. visages : lavis chair uni, aucun détail (ni yeux, ni bouche, ni barbe)

Usage : python3 croquis.py ENTREE SORTIE [--start S --dur D]
Import : from croquis import Style ; st = Style() ; out = st(rgb) ; st.reset()
"""
import argparse
import os
import subprocess
import sys
import time

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
sys.path.insert(0, ICI)
import stylize as B           # noqa: E402  (non modifié)
import ligne_claire as LC     # noqa: E402  (réutilisé pour les étiquettes)

PAPIER = np.array((247, 241, 228), np.float32)   # papier chaud
GRAPHITE = np.array((58, 54, 62), np.float32)    # mine / encre diluée
# couleurs de lavis (pigment pur, avant dilution)
LAVIS = {B.I_AZ: (30, 110, 205), B.I_AZO: (30, 110, 205), B.I_SB: (14, 104, 66),
         B.I_SBO: (14, 104, 66), B.I_OR: (240, 176, 30), B.I_ORO: (240, 176, 30),
         B.I_BLANC: (236, 236, 232), B.I_PEL: (118, 172, 84)}
EQUIPE = (B.I_AZ, B.I_AZO, B.I_SB, B.I_SBO, B.I_OR, B.I_ORO)
FPS_TRAIT = 10.0              # cadence du « tremblé » du trait


def _bruit(h, w, echelle, graine):
    """Bruit lisse dans [-1, 1] (valeurs aléatoires interpolées)."""
    r = np.random.default_rng(graine)
    gh, gw = max(2, int(h / echelle) + 2), max(2, int(w / echelle) + 2)
    n = cv2.resize(r.standard_normal((gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(n / 1.6, -1, 1)


class _Textures:
    """Textures fixées à l'écran (papier, granulation, taches), calculées une fois par taille."""

    def __init__(self, H, W):
        f = min(H, W) / 1080.0
        r = np.random.default_rng(7)
        # grain du papier : bruit fin + fibres légèrement étirées
        g = r.standard_normal((H, W)).astype(np.float32)
        fin = cv2.GaussianBlur(g, (0, 0), 0.8 * f + 0.4)
        fibre = cv2.GaussianBlur(g, (0, 0), sigmaX=4 * f, sigmaY=1.2 * f)
        moy = _bruit(H, W, 220 * f, 3)
        self.papier = 1.0 + 0.020 * fin / (fin.std() + 1e-6) + 0.012 * fibre / (fibre.std() + 1e-6) \
            + 0.012 * moy
        # granulation du pigment : le pigment se dépose dans les creux du papier
        gr = cv2.GaussianBlur(r.standard_normal((H, W)).astype(np.float32), (0, 0), 1.8 * f + 0.5)
        gr = gr / (gr.std() + 1e-6)
        self.granul = np.clip(1.0 + 0.07 * gr + 0.07 * _bruit(H, W, 7 * f, 4), 0.7, 1.3)
        # taches de lavis (dilution irrégulière à grande échelle)
        self.taches = 1.0 + 0.16 * _bruit(H, W, 130 * f, 5) + 0.08 * _bruit(H, W, 40 * f, 6)
        # marges : le lavis s'arrête de façon irrégulière près des bords de l'image
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy]) / (min(H, W) * 0.035)
        d = d + 0.9 * _bruit(H, W, 60 * f, 8)
        self.marge = np.clip(d - 0.3, 0, 1).astype(np.float32)


class Style:
    """Aquarelle + crayon, avec mémoire temporelle (vidéo).

    fps : cadence de la vidéo (pour caler le tremblé du trait à ~10 i/s)
    temporel : False pour une image isolée
    """

    def __init__(self, temporel=True, fps=25.0, cote=540, epaisseur=2.6):
        self.lc = LC.Style(temporel=temporel, cote=cote)
        self.fps = fps
        self.epaisseur = epaisseur
        self._tex = None
        self.reset()

    def reset(self):
        self.lc.reset()
        self.n = 0
        self._pal = None
        self._warps = None

    # -- couleurs de lavis : pigment + dilution par étiquette (avec cache)
    def _lavis(self, pal, foule):
        b = self.lc.base
        key = (len(pal), id(b.palette))
        if self._pal is not None and self._pal[0] == key:
            return self._pal[1], self._pal[2]
        n = len(pal)
        col = pal.astype(np.float32).copy()
        dil = np.full(n, 0.62, np.float32)          # densité de pigment (1 = pur)
        lab = B._lab(pal.tolist())
        peaux = set(B.PEAUX) | set(range(b.n_normal + B.N_FOULE, n))
        for i in range(n):
            # tons neutres sombres (shorts, ombres, cheveux) : lavis gris de Payne léger
            if lab[i, 0] < 38 and i not in peaux:
                col[i] = (96, 94, 112)
                dil[i] = 0.30
        for i, c in LAVIS.items():
            if i < n:
                col[i] = c
        dil[[i for i in (B.I_AZ, B.I_AZO, B.I_SB, B.I_SBO) if i < n]] = 0.74
        dil[[i for i in (B.I_OR, B.I_ORO) if i < n]] = 0.78
        if B.I_BLANC < n:
            dil[B.I_BLANC] = 0.10                    # blanc = papier réservé
        if B.I_PEL < n:
            dil[B.I_PEL] = 0.40                      # pelouse : lavis vert clair
        for i in peaux:
            # chair : lavis uni, réchauffé (peaux foncées = terre de Sienne)
            col[i] = np.clip(col[i] * (0.9, 0.8, 0.72) + (20, 8, 0), 0, 255)
            dil[i] = 0.55 if lab[i, 0] > 55 else 0.62
        for i in foule:
            col[i] = (0.5 * col[i] + 0.5 * np.array((200, 190, 170))).astype(np.float32)
            dil[i] = 0.10                            # foule : presque papier nu
        # densité équivalente : couleur « pure » dont la dilution donne la couleur cible
        self._pal = (key, col, dil)
        return col, dil

    def _deformations(self, h, w):
        """3 champs de déplacement lisses (tremblé du trait), fixés par taille."""
        if self._warps is not None and self._warps[0] == (h, w):
            return self._warps[1]
        f = min(h, w) / 1080.0
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        ws = []
        for k in range(3):
            dx = 1.6 * f * _bruit(h, w, 70 * f, 20 + k) + 0.6 * f * _bruit(h, w, 18 * f, 40 + k)
            dy = 1.6 * f * _bruit(h, w, 70 * f, 30 + k) + 0.6 * f * _bruit(h, w, 18 * f, 50 + k)
            ws.append((xx + dx, yy + dy))
        self._warps = ((h, w), ws)
        return ws

    def _etiquettes(self, rgb):
        """Reprend la 1re moitié de ligne_claire.Style.__call__ : carte d'étiquettes finale."""
        lc = self.lc
        pal_avant = lc.base.palette
        sortie_base = lc.base(rgb)
        if pal_avant is not None and lc.base.palette is not pal_avant \
                and len(lc.base.palette) <= lc.base.n_normal + B.N_FOULE:
            lc.pers.reset()
            lc._prev_e = None
        etiq = lc.base.prev["etiq"].copy()
        h, w = etiq.shape
        prob = lc.pers(rgb, w, h)
        rep, pal, foule = lc._table()
        pers = np.zeros((h, w), bool)
        if prob is not None:
            etiq, pers = lc._joueurs(rgb, etiq, prob)
        lc._prev_e = etiq
        e = rep[etiq]                  # couleurs voisines fusionnées (moins de taches)
        e = np.where(pers, e, B.Stylizer._mode(e, 3))
        # îlots (touffes d'herbe, reflets) entourés de pelouse hors joueurs -> pelouse
        ip = rep[B.I_PEL]
        n, cc, st, _ = cv2.connectedComponentsWithStats((e != ip).astype(np.uint8), connectivity=8)
        if n > 1:
            pet = st[:, cv2.CC_STAT_AREA] < 0.0006 * w * h
            pet[0] = False
            m = pet[cc] & ~pers
            autour = cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~m
            if m.any():
                # composante dont le voisinage est majoritairement pelouse
                dil = cv2.dilate(cc.astype(np.float32) * m, np.ones((5, 5), np.uint8)).astype(np.int32)
                tot = np.bincount(dil[autour], minlength=n)
                vert = np.bincount(dil[autour & (e == ip)], minlength=n)
                ok = pet & (vert >= 0.75 * np.maximum(tot, 1))
                e[ok[cc] & ~pers] = ip
        return e, pers, pal, foule, sortie_base

    def __call__(self, rgb):
        H, W = rgb.shape[:2]
        if self._tex is None or self._tex.papier.shape != (H, W):
            self._tex = _Textures(H, W)
        tx = self._tex
        e, pers, pal_lc, foule, sortie_base = self._etiquettes(rgb)
        h, w = e.shape
        col, dil = self._lavis(B._rgb_of_lab(self.lc.base.palette), foule)
        en_foule = np.isin(e, list(foule))
        peau = np.isin(e, list(B.PEAUX) + list(range(self.lc.base.n_normal + B.N_FOULE, len(col))))

        # --- lavis (basse résolution) ------------------------------------------------
        c_pig = col[e]                                   # couleur du pigment
        d = dil[e].copy()                                # densité de pigment
        # modelé doux : lumière/ombre très floue (aucun détail de visage possible)
        petit = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
        L = cv2.cvtColor(petit, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        Lf = cv2.GaussianBlur(L, (0, 0), 5)
        mod = np.clip(1.25 - 0.6 * Lf, 0.75, 1.25)
        mod[peau | en_foule] = 1.0
        d *= mod
        # auréole : le pigment s'accumule au bord de chaque zone
        fr = np.zeros((h, w), np.uint8)
        fr[:-1] |= (e[:-1] != e[1:]).astype(np.uint8)
        fr[:, :-1] |= (e[:, :-1] != e[:, 1:]).astype(np.uint8)
        dist = cv2.distanceTransform(1 - fr, cv2.DIST_L2, 3)
        k = min(h, w) / 540.0
        d *= 1.0 + 0.45 * np.exp(-dist / (1.6 * k)) * (~en_foule)
        # bords mouillés : on adoucit la couleur et la densité (le lavis « bave »)
        sig = 1.4 * k
        c_pig = cv2.GaussianBlur(c_pig, (0, 0), sig)
        d = cv2.GaussianBlur(d.astype(np.float32), (0, 0), sig)
        # pleine résolution, avec un léger décalage du lavis par rapport au trait
        f = min(H, W) / 1080.0
        M = np.float32([[W / w, 0, 5 * f], [0, H / h, 4 * f]])
        c_pig = cv2.warpAffine(c_pig, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        d = cv2.warpAffine(d, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        # lignes du terrain : papier réservé (le lavis vert s'interrompt)
        pel = cv2.resize((e == B.I_PEL).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
        a_l = np.clip((sortie_base[..., 0].astype(np.float32) - B.PELOUSE[0] - 20)
                      / (B.BLANC[0] - B.PELOUSE[0] - 40), 0, 1) * pel
        a_l = cv2.GaussianBlur(a_l, (0, 0), 1.2 * f)
        d *= 1.0 - 0.85 * a_l
        # granulation + taches + marges irrégulières
        d = np.clip(d * tx.granul * tx.taches * tx.marge, 0, 1)
        # mélange soustractif simple : papier filtré par le pigment
        filtre = c_pig / PAPIER
        out = PAPIER * (1.0 - d[..., None] * (1.0 - np.clip(filtre, 0.02, 1.2)))

        # --- trait crayon --------------------------------------------------------------
        pl = B._lab(col.tolist())[e]
        # poids du trait : silhouette des joueurs = appuyé, frontières contrastées =
        # moyen, frontières faibles = à peine effleurées
        bord = np.zeros((h, w), np.float32)
        for ax in (0, 1):
            a = pl[1:] if ax == 0 else pl[:, 1:]
            c = pl[:-1] if ax == 0 else pl[:, :-1]
            fa = en_foule[1:] if ax == 0 else en_foule[:, 1:]
            fc = en_foule[:-1] if ax == 0 else en_foule[:, :-1]
            de = np.linalg.norm(a - c, axis=2)
            poids = np.where(de > 30, 0.8, np.where(de > 14, 0.35, 0.0)) * ~(fa | fc)
            # à l'intérieur d'un joueur : seulement les bords de maillot, à peine appuyés
            pa = pers[1:] if ax == 0 else pers[:, 1:]
            pc = pers[:-1] if ax == 0 else pers[:, :-1]
            ea = e[1:] if ax == 0 else e[:, 1:]
            ec = e[:-1] if ax == 0 else e[:, :-1]
            maillot = np.isin(ea, EQUIPE) | np.isin(ec, EQUIPE)
            poids = np.where(pa & pc, np.where(maillot & (de > 30), 0.45, 0.18 * (de > 30)), poids)
            if ax == 0:
                bord[:-1] = np.maximum(bord[:-1], poids)
            else:
                bord[:, :-1] = np.maximum(bord[:, :-1], poids)
        if pers.any():
            pu = pers.astype(np.uint8)
            sil = (cv2.dilate(pu, np.ones((3, 3), np.uint8)) != pu) & ~en_foule
            bord[sil] = 1.0
        bord = B.Stylizer._sans_miettes(bord, int(26 * k))
        poids = cv2.resize(cv2.dilate(bord, np.ones((3, 3), np.uint8)), (W, H), interpolation=cv2.INTER_LINEAR)
        t = cv2.resize(bord, (W, H), interpolation=cv2.INTER_LINEAR)
        t = cv2.GaussianBlur(t, (0, 0), 0.8 * W / w)
        axe = (t > 0.12).astype(np.uint8)
        dt = cv2.distanceTransform(1 - axe, cv2.DIST_L2, 3)
        # tremblé : champ de déformation changé à ~10 i/s (jamais à chaque image)
        ws = self._deformations(H, W)
        etape = max(1, int(round(self.fps / FPS_TRAIT)))
        j = (self.n // etape) % 3
        self.n += 1
        # épaisseur et pression variables le long du trait (bruit fixe)
        pres = np.clip(0.7 + 0.6 * _bruit_cache(self, H, W), 0.0, 1.2)   # 0 = trait levé
        demi = 0.5 * self.epaisseur * f * (0.5 + 0.6 * pres)
        a1 = np.clip(demi + 0.5 - cv2.remap(dt, ws[j][0], ws[j][1], cv2.INTER_LINEAR,
                                                borderMode=cv2.BORDER_REPLICATE), 0, 1)
        j2 = (j + 1) % 3
        a2 = np.clip(0.55 * demi + 0.5 - cv2.remap(dt, ws[j2][0] + 1.5 * f, ws[j2][1] - 1.0 * f,
                                                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), 0, 1)
        a = np.maximum(a1 * (0.5 + 0.4 * pres), 0.4 * a2) * np.clip(poids * 1.15, 0, 1)
        # la mine accroche le grain du papier
        a = np.clip(a * (0.8 + 0.25 * tx.granul), 0, 1) * np.clip(tx.marge * 1.5, 0.25, 1)
        out = out * (1 - a[..., None]) + GRAPHITE * a[..., None]

        out *= tx.papier[..., None]
        return np.clip(out, 0, 255).astype(np.uint8)


def _bruit_cache(st, H, W):
    """Bruit de pression du trait, mis en cache sur l'objet Style."""
    c = getattr(st, "_pres", None)
    if c is None or c.shape != (H, W):
        st._pres = _bruit(H, W, 90 * min(H, W) / 1080.0, 77)
    return st._pres


# --- Entrées / sorties -------------------------------------------------------------
def traiter_video(src, dst, start=0.0, dur=None, log=True):
    w, h, fps = LC._infos(src)
    num, den = (fps.split("/") + ["1"])[:2]
    cin = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", src]
    if dur:
        cin += ["-t", str(dur)]
    cin += ["-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    cout = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
            "-r", fps, "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", dst]
    pin = subprocess.Popen(cin, stdout=subprocess.PIPE)
    pout = subprocess.Popen(cout, stdin=subprocess.PIPE)
    st, n, t0, taille = Style(fps=float(num) / float(den)), 0, time.time(), w * h * 3
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
    ap = argparse.ArgumentParser(description="Style carnet de croquis aquarellé")
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
