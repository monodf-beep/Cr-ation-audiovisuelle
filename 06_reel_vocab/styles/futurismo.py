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
     - joueurs : couleurs d'équipe conservées (azur ; vert, or, blanc),
       autres tons ramenés à la palette chaude, silhouette anguleuse
     - « dinamismo » : échos décalés et dégressifs des joueurs, tirés des
       images précédentes (caméra compensée) + petit décalage le long du
       mouvement : déterministe, pas de scintillement
     - contours noirs épais, silhouette en polygone
  3. visages : aplat chair sans yeux, bouche ni barbe (hérité)

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


def _lab(c):
    return B._lab(c)


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
        self.hist = deque(maxlen=10)   # (couleur, masque, position caméra)
        self.cam = np.zeros(2, np.float32)
        self.dir = self.dir0.copy()
        self.vit = 0.0
        self.apex = None
        self.gris = None
        self._fac = None

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
        etiq = b.prev["etiq"].copy()
        h, w = etiq.shape
        k = min(h, w) / 540.0
        prob = st.pers(rgb, w, h)
        rep, pal, foule = st._table()
        pers = np.zeros((h, w), bool)
        if prob is not None:
            etiq, pers = st._joueurs(rgb, etiq, prob)
        st._prev_e = etiq
        e = rep[etiq]
        e = np.where(pers, e, B.Stylizer._mode(e, 5))

        # zones : pelouse / figures (joueurs, même minuscules) / fond
        ipel = rep[B.I_PEL]
        pel = e == ipel
        crowd = np.isin(e, list(foule))
        zone = cv2.morphologyEx(pel.astype(np.uint8), cv2.MORPH_CLOSE, B._disque(15 * k))
        n, cc, sts, _ = cv2.connectedComponentsWithStats(1 - zone, connectivity=4)
        bordure = np.zeros(n, bool)
        bordure[np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))] = True
        trou = ~bordure & (sts[:, cv2.CC_STAT_AREA] < 0.08 * w * h)
        trou[0] = False
        zone = zone.astype(bool) | trou[cc]
        fig = ((zone & ~pel) | pers)
        fig = cv2.morphologyEx(fig.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        # silhouette anguleuse : polygone simplifié de chaque figure ;
        # les miettes (bouts de ligne, panneaux lointains) hors personnes sont ignorées
        cs, _ = cv2.findContours(fig, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        poly = []
        for c in cs:
            a = cv2.contourArea(c)
            x, y, bw, bh = cv2.boundingRect(c)
            if a > 70 * k * k or (a > 8 * k * k and pers[y:y + bh, x:x + bw].mean() > 0.3):
                poly.append(cv2.approxPolyDP(c, 1.6 * k, True))
        figp = np.zeros((h, w), np.uint8)
        cv2.fillPoly(figp, poly, 1)
        fig = figp.astype(bool)
        pel &= ~fig

        # couleurs des figures (aplats), pixels hors figure -> voisin le plus proche
        pf = self._pal_fig(pal, rep)
        efig = e.copy()
        hors = fig & (np.isin(e, list(foule)) | pel | (e == ipel))
        if hors.any():
            m = (~hors & fig & ~np.isin(e, list(foule)) & (e != ipel)).astype(np.uint8)
            if m.any():
                _, lab_i = cv2.distanceTransformWithLabels(1 - m, cv2.DIST_L2, 3,
                                                           labelType=cv2.DIST_LABEL_PIXEL)
                ys, xs = np.nonzero(m)
                src = np.zeros(lab_i.max() + 1, np.int32)
                src[lab_i[ys, xs]] = e[ys, xs]
                efig[hors] = src[lab_i[hors]]
        col_fig = pf[efig]

        # mouvement : caméra (fond) et action (figures), lissés
        gris = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (w // 2, h // 2),
                          interpolation=cv2.INTER_AREA)
        dcam = np.zeros(2, np.float32)
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
                    a = min(0.12, 0.03 * sp)
                    d = (1 - a) * self.dir + a * (v / sp)
                    self.dir = d / max(1e-6, np.linalg.norm(d))
                self.vit = 0.9 * self.vit + 0.1 * sp
        self.gris = gris
        self.cam = self.cam + dcam
        dvec = self.dir

        # échos (dinamismo) : images passées, caméra compensée, + décalage synthétique
        self.hist.append((col_fig, fig.astype(np.float32), self.cam.copy()))
        pas = (0.022 + 0.004 * min(self.vit, 4.0)) * max(h, w)    # décalage par écho
        echo_c = np.zeros((h, w, 3), np.float32)
        echo_a = np.zeros((h, w), np.float32)
        for j, (ret, alpha) in enumerate(((6, 0.22), (4, 0.36), (2, 0.55))):
            idx = max(0, len(self.hist) - 1 - ret) if self.temporel else len(self.hist) - 1
            c0, m0, cam0 = self.hist[idx]
            nk = 3 - j
            off = (self.cam - cam0) - dvec * pas * nk * 0.5
            M = np.float32([[1, 0, off[0]], [0, 1, off[1]]])
            c1 = cv2.warpAffine(c0, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
            m1 = cv2.warpAffine(m0, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
            # écho : couleur du joueur délavée vers la crème
            c1 = 0.7 * c1.astype(np.float32) + 0.3 * np.float32(CREMA)
            a1 = m1 * alpha
            echo_c = echo_c * (1 - a1[..., None]) + c1 * a1[..., None]
            echo_a = echo_a * (1 - a1) + a1
        echo_c = echo_c / np.maximum(echo_a[..., None], 1e-4)

        # --- rendu pleine résolution ---------------------------------------------
        z = W / w
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

        # échos puis figures
        ea = cv2.resize(echo_a, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        ec = cv2.resize(echo_c, (W, H), interpolation=cv2.INTER_NEAREST)
        out = out * (1 - ea) + ec * ea
        cf = cv2.resize(col_fig, (W, H), interpolation=cv2.INTER_NEAREST)
        cf = cv2.medianBlur(cf, min(7, max(3, int(round(z * 1.6)) | 1)))
        fa = cv2.resize(fig.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        fa = np.clip((cv2.GaussianBlur(fa, (0, 0), 0.6 * z) - 0.5) * 3 + 0.5, 0, 1)[..., None]
        out = out * (1 - fa) + cf.astype(np.float32) * fa

        # contours : frontières d'aplats dans les figures + silhouette épaisse
        f = min(W, H) / 1080.0
        labf = B._lab(pf.tolist())[efig]
        bord = np.zeros((h, w), np.float32)
        dh = np.linalg.norm(labf[:, 1:] - labf[:, :-1], axis=2) > 14
        dv = np.linalg.norm(labf[1:] - labf[:-1], axis=2) > 14
        bord[:, 1:][dh] = 1
        bord[1:][dv] = 1
        bord *= cv2.erode(fig.astype(np.uint8), np.ones((3, 3), np.uint8))
        bord = B.Stylizer._sans_miettes(bord, int(8 * k))
        t_in = self._trait(bord, W, H, 2.6 * f, z)
        sil = np.zeros((H, W), np.uint8)
        polyF = [np.round(p.astype(np.float32) * z).astype(np.int32) for p in poly]
        cv2.polylines(sil, polyF, True, 255, max(2, int(round(5.0 * f))), cv2.LINE_AA)
        # contour d'écho : trait fin noir, transparence de l'écho
        t_ec = cv2.Canny((ea[..., 0] * 255).astype(np.uint8), 40, 90).astype(np.float32) / 255
        t_ec = cv2.GaussianBlur(cv2.dilate(t_ec, np.ones((2, 2), np.uint8)), (0, 0), 0.6) * 0.6
        t = np.maximum(np.maximum(t_in, sil.astype(np.float32) / 255), np.clip(t_ec, 0, 1) * (1 - fa[..., 0]))
        out = out * (1 - t[..., None]) + np.float32(ENCRE) * t[..., None]

        # grain de toile fixe (identique à chaque image : pas de scintillement)
        out = out + self._grain(W, H)[..., None]
        return np.clip(out + 0.5, 0, 255).astype(np.uint8)

    def _trait(self, bord, W, H, ep, z):
        t = cv2.resize(bord, (W, H), interpolation=cv2.INTER_LINEAR)
        t = cv2.GaussianBlur(t, (0, 0), max(0.8, 0.8 * z))
        axe = (t > 0.3 * float(t.max() if t.max() > 0 else 1)).astype(np.uint8)
        dt = cv2.distanceTransform(1 - axe, cv2.DIST_L2, 3)
        return np.clip(max(0.6, 0.5 * ep - 0.25 * z) + 0.5 - dt, 0, 1)

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
        nrm = np.array([-d[1], d[0]], np.float32)
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
        # fondu : plein près de la pointe, s'efface vers le bord
        _ = nrm
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
