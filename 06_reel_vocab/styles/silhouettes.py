#!/usr/bin/env python3
"""
Style « Silhouettes » : chaque image est COMPRISE puis REDESSINÉE (aucun pixel
de la vidéo n'est recopié à l'écran).

Compréhension (CPU, onnxruntime)
  - joueurs + ballon : Mask R-CNN v2 (torchvision, COCO « person » / « sports
    ball »), exporté en ONNX -> modeles/maskrcnn_v2_coco.onnx
  - squelette de chaque joueur, approche « top-down » (une boîte = un joueur,
    adapté aux mêlées) : RTMPose-m body7 -> modeles/rtmpose-m_body7_256x192.onnx
  - suivi des joueurs (appariement hongrois boîtes + squelettes), vote de
    l'équipe par piste (couleur majoritaire du maillot -> CLASSE, jamais copiée),
    membres cachés déduits de la mémoire de la piste ou d'un mannequin type
  - horizon de la pelouse, lignes blanches du terrain (droites), ballon

Dessin (illustrateur, esprit affiche futuriste Depero / Balla)
  - chaque joueur = mannequin à volumes simples : membres en fuseaux arrondis,
    torse en volume, tête ovale sans visage ; aplats : maillot (torse + bras),
    short, chaussettes, peau, crampons ; trait noir d'épaisseur constante
  - joueurs dessinés du fond vers l'avant (pieds plus bas = plus près)
  - « on twos » : le dessin change toutes les 2 images
  - fond conçu : pelouse unie + lignes nettes ; au-dessus de l'horizon une
    composition futuriste FIXE (facettes ocre / vermillon / noir / crème)
  - échos (dynamisme) : silhouettes passées en teinte claire si mouvement vif
  - ballon : ellipse blanche orientée, une bande bleue, contour noir

Import : from silhouettes import Style ; st = Style()
         st(rgb_1080x1920) -> rgb (image par image, causal) ; st.reset() entre plans
         st.render_shot(frames) -> liste d'images (plan entier, avec anticipation :
         trous comblés, lissage centré, équipe votée sur toute la piste) — meilleur.
"""
import os
import time
from collections import deque

import cv2
import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
MODELES = os.path.join(os.path.dirname(ICI), "modeles")
DET_ONNX = os.path.join(MODELES, "maskrcnn_v2_coco.onnx")
POSE_ONNX = os.path.join(MODELES, "rtmpose-m_body7_256x192.onnx")

W, H = 1080, 1920
DW, DH = 600, 1066            # résolution de détection
DS = W / DW                   # facteur détection -> image

# ---------------------------------------------------------------- palette (RVB)
ENCRE = (26, 20, 22)
CREME = (244, 233, 205)
OCRE = (226, 160, 56)
OCRE_CL = (238, 202, 122)
VERMILLON = (206, 52, 36)
TERRE = (148, 70, 40)
NOIR = (30, 26, 28)
PELOUSE = (92, 148, 70)
LIGNE = (240, 236, 214)
PEAU = (214, 156, 112)
CRAMPON = (34, 30, 32)
BAL_BLANC = (252, 249, 240)
BAL_BLEU = (30, 64, 170)

EQUIPES = {
    #           maillot          short            chaussettes      liseré
    "ITA": dict(m=(31, 111, 209), s=(22, 62, 150), c=(22, 62, 150), acc=None),
    "RSA": dict(m=(11, 93, 59), s=(242, 238, 224), c=(11, 93, 59), acc=(232, 182, 40)),
    "ARB": dict(m=(226, 84, 44), s=(30, 26, 28), c=(30, 26, 28), acc=None),
    "JAU": dict(m=(226, 214, 64), s=(30, 26, 28), c=(30, 26, 28), acc=None),
    "AUT": dict(m=(236, 226, 200), s=(30, 26, 28), c=(30, 26, 28), acc=None),
}
SHORT_TON = {"blanc": (242, 238, 224), "noir": (30, 26, 28)}

# COCO 17 points
NEZ, OG, OD, ORG, ORD, EG, ED, CG, CD, PG, PD, HG, HD, GG, GD, CHG, CHD = range(17)

_SESS = {}


def _sess(path):
    if path not in _SESS:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = 4
        so.log_severity_level = 3
        _SESS[path] = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
    return _SESS[path]


# ================================================================ COMPRÉHENSION
def detecter(rgb):
    """-> personnes [dict(box, score, mask(bool, rés. détection))], ballons [...]"""
    small = cv2.resize(rgb, (DW, DH), interpolation=cv2.INTER_AREA)
    x = (small.astype(np.float32) / 255).transpose(2, 0, 1)
    b, l, s, m = _sess(DET_ONNX).run(None, {"image": x})
    pers, bal = [], []
    for i in range(len(l)):
        if l[i] == 1 and s[i] >= 0.3:
            pers.append(dict(box=b[i] * DS, score=float(s[i]), mask=m[i, 0] > 0.5))
        elif l[i] == 37 and s[i] >= 0.08:
            bal.append(dict(box=b[i] * DS, score=float(s[i]), mask=m[i, 0] > 0.5))
    return pers, bal


def _affine_boite(box, pad=1.25, out=(192, 256)):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * pad, (y1 - y0) * pad
    ar = out[0] / out[1]
    if w > h * ar:
        h = w / ar
    else:
        w = h * ar
    src = np.float32([[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2], [cx - w / 2, cy + h / 2]])
    dst = np.float32([[0, 0], [out[0], 0], [0, out[1]]])
    return cv2.getAffineTransform(src, dst), (cx, cy, w, h)


def poses(rgb, boxes):
    """RTMPose top-down : (N,17,3) x, y, confiance."""
    if not len(boxes):
        return np.zeros((0, 17, 3), np.float32)
    crops, geo = [], []
    mean = np.float32([123.675, 116.28, 103.53])
    std = np.float32([58.395, 57.12, 57.375])
    for b in boxes:
        M, g = _affine_boite(b)
        c = cv2.warpAffine(rgb, M, (192, 256), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        crops.append(((c.astype(np.float32) - mean) / std).transpose(2, 0, 1))
        geo.append(g)
    sx, sy = _sess(POSE_ONNX).run(None, {"input": np.stack(crops)})
    out = np.zeros((len(boxes), 17, 3), np.float32)
    for i, (cx, cy, w, h) in enumerate(geo):
        ix, iy = sx[i].argmax(1), sy[i].argmax(1)
        vx, vy = sx[i].max(1), sy[i].max(1)
        px, py = ix / 2.0, iy / 2.0
        out[i, :, 0] = cx - w / 2 + px / 192 * w
        out[i, :, 1] = cy - h / 2 + py / 256 * h
        out[i, :, 2] = np.minimum(vx, vy)
    return out


def horizon(rgb):
    """Ligne haute de la pelouse (y en px 1080x1920, droite horizontale), 0 si tout pelouse."""
    sm = cv2.resize(rgb, (135, 240), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV).astype(np.float32)
    # couleur de référence de la pelouse : bas de l'image, pixels verts
    bas = hsv[-60:].reshape(-1, 3)
    vb = bas[(bas[:, 0] > 28) & (bas[:, 0] < 95) & (bas[:, 1] > 35)]
    if len(vb) < 200:
        return 0.0
    rh, rs = np.median(vb[:, 0]), np.median(vb[:, 1])
    g = ((np.abs(hsv[..., 0] - rh) < 13) & (hsv[..., 1] > 0.55 * rs) & (hsv[..., 2] > 45)).astype(np.float32)
    f = np.convolve(g.mean(1), np.ones(3) / 3, "same")
    # frontière la plus haute : au-dessus pas de pelouse, en dessous surtout pelouse
    # (les joueurs masquent une partie de la pelouse, d'où un seuil modéré)
    if f[:12].mean() > 0.5:
        return 0.0
    by = None
    for y in range(6, 240 - 30):
        if f[max(0, y - 18):y].mean() < 0.15 and f[y:y + 30].mean() > 0.3 and f[y:y + 4].mean() > 0.2:
            by = y
            break
    if by is None:
        return 0.0
    return by * H / 240.0


def couleur_pitch(rgb, hz):
    sm = cv2.resize(rgb, (135, 240), interpolation=cv2.INTER_AREA)
    y0 = int(hz * 240 / H) + 4
    p = sm[y0:].reshape(-1, 3)
    if len(p) < 50:
        return None
    hsv = cv2.cvtColor(p[None], cv2.COLOR_RGB2HSV)[0]
    ok = (hsv[:, 0] > 30) & (hsv[:, 0] < 90) & (hsv[:, 1] > 50)
    return np.median(hsv[ok], 0) if ok.sum() > 30 else None


def lignes_terrain(rgb, hz, masques):
    """Lignes blanches de la pelouse -> [(theta, rho, poids)] (coords 1080x1920)."""
    f = 4
    sm = cv2.resize(rgb, (W // f, H // f), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV)
    wht = ((hsv[..., 1] < 70) & (hsv[..., 2] > 165)).astype(np.uint8)
    wht[: int(hz / f) + 6] = 0
    if masques is not None:
        wht[cv2.dilate(masques, np.ones((7, 7), np.uint8)) > 0] = 0
    # une ligne de terrain est fine : on retire les grosses taches
    wht &= (cv2.morphologyEx(wht, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) == 0).astype(np.uint8)
    segs = cv2.HoughLinesP(wht * 255, 1, np.pi / 180, 30, minLineLength=70, maxLineGap=12)
    out = []
    if segs is None:
        return out
    for x0, y0, x1, y1 in segs.reshape(-1, 4):
        th = np.arctan2(y1 - y0, x1 - x0) % np.pi
        nx, ny = -np.sin(th), np.cos(th)
        rho = (x0 * nx + y0 * ny) * f
        L = np.hypot(x1 - x0, y1 - y0) * f
        for o in out:
            dth = abs((o[0] - th + np.pi / 2) % np.pi - np.pi / 2)
            if dth < 0.06 and abs(o[1] - rho) < 30:
                o[2] += L
                break
        else:
            out.append([th, rho, L])
    return [o for o in out if o[2] > 380]


def classe_couleur(rgb, kp, mask_full):
    """Histogramme de classes de tenue dans le torse et le short (pixels -> classes)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    def zone(pts, r):
        m = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(m, cv2.convexHull(np.int32(pts)), 1)
        if r > 0:
            m = cv2.erode(m, np.ones((r, r), np.uint8))
        return (m > 0) & mask_full

    def hist(sel):
        if sel.sum() < 30:
            return None
        h, s, v = hsv[..., 0][sel].astype(int), hsv[..., 1][sel].astype(int), hsv[..., 2][sel].astype(int)
        c = dict(
            bleu=((h >= 96) & (h <= 128) & (s > 90) & (v > 60)).sum(),
            vert=((h >= 38) & (h <= 92) & (s > 45) & (v < 125)).sum(),
            rouge=(((h <= 12) | (h >= 168)) & (s > 110) & (v > 90)).sum(),
            jaune=((h >= 22) & (h <= 40) & (s > 110) & (v > 150)).sum(),
            blanc=((s < 45) & (v > 165)).sum(),
            noir=(v < 55).sum(),
        )
        n = float(sel.sum())
        return {k: c[k] / n for k in c}

    t = kp[[EG, ED, HD, HG], :2]
    mid = t.mean(0)
    torse = mid + (t - mid) * 0.7
    hg, hd, gg, gd = kp[HG, :2], kp[HD, :2], kp[GG, :2], kp[GD, :2]
    short = np.array([hg, hd, hd + (gd - hd) * 0.35, hg + (gg - hg) * 0.35])
    return hist(zone(torse, 3)), hist(zone(short, 3))


# ================================================================ GÉOMÉTRIE DU DESSIN
def fuseau(p, q, r1, r2, n=14):
    """Polygone d'un membre : deux cercles reliés par leurs tangentes."""
    p, q = np.float32(p), np.float32(q)
    d = q - p
    L = float(np.hypot(*d))
    if L < 1e-3 or L <= abs(r1 - r2):
        r = max(r1, r2)
        c = p if r1 >= r2 else q
        t = np.linspace(0, 2 * np.pi, 2 * n, endpoint=False)
        return np.stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)], 1)
    a = np.arctan2(d[1], d[0])
    phi = np.arccos(np.clip((r1 - r2) / L, -1, 1))
    t1 = np.linspace(a + phi, a + 2 * np.pi - phi, n)
    t2 = np.linspace(a - phi, a + phi, n)
    A = np.stack([p[0] + r1 * np.cos(t1), p[1] + r1 * np.sin(t1)], 1)
    B = np.stack([q[0] + r2 * np.cos(t2), q[1] + r2 * np.sin(t2)], 1)
    return np.concatenate([A, B])


def cercles_hull(cs, n=20):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.concatenate([np.stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)], 1) for c, r in cs])
    return cv2.convexHull(np.float32(pts))[:, 0]


def chaikin(p, it=2):
    for _ in range(it):
        q = np.roll(p, -1, 0)
        p = np.concatenate([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p


def union(polys, pad=4):
    """Contour extérieur lissé de l'union de polygones (pour un aplat unique)."""
    allp = np.concatenate(polys)
    x0, y0 = np.floor(allp.min(0)) - pad
    x1, y1 = np.ceil(allp.max(0)) + pad
    k = 2.0
    m = np.zeros((int((y1 - y0) * k) + 1, int((x1 - x0) * k) + 1), np.uint8)
    for p in polys:
        cv2.fillPoly(m, [np.int32(np.round((p - [x0, y0]) * k * 16))], 255, cv2.LINE_8, 4)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < 20:
            continue
        c = cv2.approxPolyDP(c, 1.2, True)[:, 0].astype(np.float32)
        if len(c) >= 3:
            out.append(chaikin(c, 2) / k + [x0, y0])
    return out


def _pts(p):
    return np.int32(np.round(np.asarray(p) * 16)).reshape(-1, 1, 2)


def piece(img, polys, col, lw, trait=True):
    if isinstance(polys, np.ndarray):
        polys = [polys]
    pp = [_pts(p) for p in polys]
    cv2.fillPoly(img, pp, col, cv2.LINE_AA, 4)
    if trait and lw > 0:
        cv2.polylines(img, pp, True, ENCRE, lw, cv2.LINE_AA, 4)


# ================================================================ MANNEQUIN
def completer_pose(kp, ref_rel, box):
    """Remplace les points peu sûrs : mémoire de la piste (relative au bassin) sinon
    mannequin type orienté par le torse, sinon boîte. -> (17,2), visible(17)"""
    k = kp[:, :2].copy()
    c = kp[:, 2]
    vis = c > 0.35
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    tors_ok = (c[[EG, ED, HG, HD]] > 0.2).all()
    if not tors_ok:
        # torse inconnu : mannequin debout dans la boîte
        cx = (x0 + x1) / 2
        T = bh * 0.3
        mh = np.float32([cx, y0 + bh * 0.52])
        u = np.float32([0, -1])
    else:
        ms, mh = (k[EG] + k[ED]) / 2, (k[HG] + k[HD]) / 2
        T = max(float(np.hypot(*(ms - mh))), 0.2 * max(bw, bh))
        u = (ms - mh) / max(1e-3, float(np.hypot(*(ms - mh))))
    v = np.float32([-u[1], u[0]])
    if ref_rel is not None:
        tpl = mh + ref_rel * T
    else:
        # mannequin type (coords torse : y le long du torse, x en travers), côté gauche = +x
        T_ = {NEZ: (0, 1.45), OG: (0.05, 1.5), OD: (-0.05, 1.5), ORG: (0.12, 1.45), ORD: (-0.12, 1.45),
              EG: (0.25, 1.0), ED: (-0.25, 1.0), CG: (0.32, 0.55), CD: (-0.32, 0.55),
              PG: (0.34, 0.12), PD: (-0.34, 0.12), HG: (0.15, 0), HD: (-0.15, 0),
              GG: (0.17, -0.85), GD: (-0.17, -0.85), CHG: (0.18, -1.7), CHD: (-0.18, -1.7)}
        tpl = np.stack([mh + T * (T_[i][1] * u + T_[i][0] * v) for i in range(17)])
    for i in range(17):
        if not vis[i] and not (tors_ok and i in (EG, ED, HG, HD)):
            k[i] = tpl[i]
    return k, vis


class Joueur:
    """Données de dessin d'un joueur pour une image."""
    __slots__ = ("id", "k", "vis", "T", "eq", "short", "pied", "depth", "box", "mvt", "proche")


def mannequin(j, lw_fixe=None):
    """-> liste ordonnée (du fond vers l'avant) de (polygones, couleur, trait)."""
    k, T = j.k, j.T
    eqc = EQUIPES[j.eq]
    mail, sh, ch = eqc["m"], j.short, eqc["c"]
    ms, mh = (k[EG] + k[ED]) / 2, (k[HG] + k[HD]) / 2
    axe = ms - mh
    la = max(1e-3, float(np.hypot(*axe)))
    u = axe / la
    v = np.float32([-u[1], u[0]])
    # côtés : « proche » = côté le plus sûr (dessiné devant)
    near_left = j.proche
    far = "D" if near_left else "G"
    near = "G" if near_left else "D"
    S = {"G": dict(e=EG, c=CG, p=PG, h=HG, g=GG, ch=CHG), "D": dict(e=ED, c=CD, p=PD, h=HD, g=GD, ch=CHD)}

    def bras(s):
        e, c, p = k[S[s]["e"]], k[S[s]["c"]], k[S[s]["p"]]
        dp = p - c
        lp = max(1e-3, float(np.hypot(*dp)))
        main = p + dp / lp * 0.1 * T
        return [
            ([fuseau(c, main, 0.10 * T, 0.085 * T)], PEAU),
            ([fuseau(e, c, 0.14 * T, 0.105 * T)], mail),
        ]

    def jambe(s):
        h, g, chv = k[S[s]["h"]], k[S[s]["g"]], k[S[s]["ch"]]
        tib = chv - g
        lt = max(1e-3, float(np.hypot(*tib)))
        perp = np.float32([-tib[1], tib[0]]) / lt
        if perp[0] * j.pied < 0:
            perp = -perp
        bout = chv + perp * 0.30 * T + tib / lt * 0.05 * T
        return [
            ([fuseau(chv, bout, 0.085 * T, 0.065 * T)], CRAMPON),
            ([fuseau(g, chv, 0.125 * T, 0.085 * T)], ch),
            ([fuseau(h, g, 0.19 * T, 0.13 * T)], PEAU),
        ]

    out = []
    for p, c in bras(far)[::-1]:
        out.append((p, c, True))
    for s in (far, near):
        for p, c in jambe(s):
            out.append((p, c, True))
    # short : bassin + haut des cuisses, un seul aplat
    hg, hd, gg, gd = k[HG], k[HD], k[GG], k[GD]
    bass = cercles_hull([(hg, 0.2 * T), (hd, 0.2 * T), (mh + u * 0.15 * T, 0.24 * T)])
    cg = fuseau(hg, hg + (gg - hg) * 0.42, 0.2 * T, 0.17 * T)
    cd = fuseau(hd, hd + (gd - hd) * 0.42, 0.2 * T, 0.17 * T)
    out.append((union([bass, cg, cd]), sh, True))
    # cou + tête
    face = [i for i in (NEZ, OG, OD, ORG, ORD) if j.vis[i]]
    hc0 = ms + u * 0.5 * T
    if len(face) >= 2:
        fc = k[face].mean(0)
        d = fc - ms
        ld = float(np.hypot(*d))
        hc = ms + d / max(ld, 1e-3) * np.clip(ld, 0.38 * T, 0.6 * T)
        hc = 0.6 * hc + 0.4 * hc0
    else:
        hc = hc0
    out.append(([fuseau(ms, hc, 0.11 * T, 0.11 * T)], PEAU, True))
    # torse : volume arrondi épaules -> bassin
    lsh = max(float(np.hypot(*(k[EG] - k[ED]))) / 2, 0.19 * T)
    lhp = max(float(np.hypot(*(k[HG] - k[HD]))) / 2, 0.16 * T)
    vv = (k[EG] - k[ED])
    vv = vv / max(1e-3, float(np.hypot(*vv))) if np.hypot(*vv) > 0.15 * T else v
    torse = cercles_hull([
        (ms + vv * (lsh - 0.04 * T), 0.17 * T), (ms - vv * (lsh - 0.04 * T), 0.17 * T),
        (mh + u * 0.55 * la, max(lsh, lhp) * 0.95),
        (mh + vv * lhp * 0.8, 0.17 * T), (mh - vv * lhp * 0.8, 0.17 * T),
    ], 24)
    out.append(([torse], mail, True))
    if eqc["acc"] is not None:                                  # un seul liseré or : le col
        out.append(("col", eqc["acc"], (ms + u * 0.06 * T, hc)))
    dh = hc - ms
    ang = np.degrees(np.arctan2(dh[1], dh[0])) + 90
    tete = cv2.ellipse2Poly((int(hc[0] * 16), int(hc[1] * 16)), (int(0.23 * T * 16), int(0.28 * T * 16)),
                            int(ang), 0, 360, 8).astype(np.float32) / 16
    out.append(([tete], PEAU, True))
    for p, c in bras(near)[::-1]:
        out.append((p, c, True))
    return out


def dessiner_joueur(img, j, lw):
    parts = mannequin(j)
    for p, c, t in parts:
        if isinstance(p, str):           # liseré du col
            a, hc = t
            r = 0.15 * j.T
            dh = hc - a
            ang = np.degrees(np.arctan2(dh[1], dh[0]))
            cv2.ellipse(img, (int(a[0] * 16), int(a[1] * 16)), (int(r * 16), int(r * 0.55 * 16)), ang + 90,
                        200, 340, c, max(2, lw - 1), cv2.LINE_AA, 4)
            continue
        piece(img, p, c, lw, t)
    return parts


def silhouette_echo(img, j, col):
    polys = []
    for p, c, t in mannequin(j):
        if not isinstance(p, str):
            polys += list(p)
    for pp in union(polys):
        cv2.fillPoly(img, [_pts(pp)], col, cv2.LINE_AA, 4)


def dessiner_ballon(img, b, lw):
    (cx, cy), (a, bb), ang = b
    th = np.deg2rad(ang)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]], np.float32)
    t = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    ell = np.stack([a * np.cos(t), bb * np.sin(t)], 1) @ R.T + [cx, cy]
    piece(img, ell, BAL_BLANC, 0)
    x = np.linspace(0.08 * a, 0.32 * a, 10)
    y = bb * np.sqrt(np.clip(1 - (x / a) ** 2, 0, 1))
    band = np.concatenate([np.stack([x, y], 1), np.stack([x[::-1], -y[::-1]], 1)]) @ R.T + [cx, cy]
    piece(img, band, BAL_BLEU, 0)
    cv2.polylines(img, [_pts(ell)], True, ENCRE, lw, cv2.LINE_AA, 4)


# ================================================================ DÉCOR FIXE
def composition_fond(graine=11):
    """Composition futuriste fixe (écran) : facettes anguleuses + coins de force."""
    rng = np.random.default_rng(graine)
    img = np.zeros((H, W, 3), np.uint8)
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    n = 6
    angs = np.deg2rad(np.array([-58, -32, 24, 47, 66, -74]) + rng.uniform(-5, 5, n))
    px = rng.uniform(0.15, 0.85, n) * W
    py = rng.uniform(0.04, 0.5, n) * H
    cid = np.zeros((H, W), np.int32)
    for i in range(n):
        cid |= (((gx - px[i]) * np.sin(angs[i]) - (gy - py[i]) * np.cos(angs[i])) > 0).astype(np.int32) << i
    pal = np.array([CREME, OCRE, VERMILLON, OCRE_CL, NOIR, TERRE, CREME, OCRE, VERMILLON, OCRE_CL], np.uint8)
    perm = rng.permutation(1 << n)
    img[:] = pal[perm[cid] % len(pal)]
    # quelques coins de force (triangles très allongés) partant d'un foyer à gauche
    fx, fy = -0.15 * W, 0.42 * H
    for k, (a0, da, col) in enumerate([(-20, 5, NOIR), (-8, 3, CREME), (-31, 4, VERMILLON), (2, 2.5, NOIR)]):
        a1, a2 = np.deg2rad(a0), np.deg2rad(a0 + da)
        L = 2.2 * W
        tri = np.float32([[fx, fy], [fx + L * np.cos(a1), fy + L * np.sin(a1)], [fx + L * np.cos(a2), fy + L * np.sin(a2)]])
        cv2.fillPoly(img, [_pts(tri)], col, cv2.LINE_AA, 4)
    # traits noirs sur deux des droites de l'arrangement
    for i in (1, 3):
        d = np.float32([np.cos(angs[i]), np.sin(angs[i])])
        p0 = np.float32([px[i], py[i]]) - d * 3000
        p1 = np.float32([px[i], py[i]]) + d * 3000
        cv2.line(img, tuple(_pts(p0)[0, 0]), tuple(_pts(p1)[0, 0]), NOIR, 6, cv2.LINE_AA, 4)
    return img


def grain_papier(graine=3):
    rng = np.random.default_rng(graine)
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 0.8)
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
    return (1.0 + 0.035 * g / g.std())[..., None]


# ================================================================ SUIVI
class Euro:
    """Filtre « one euro » vectoriel (lissage causal adaptatif)."""

    def __init__(self, fc=1.2, beta=0.015, dc=1.0):
        self.fc, self.beta, self.dc = fc, beta, dc
        self.x = None
        self.dx = None

    @staticmethod
    def _a(fc, dt):
        r = 2 * np.pi * fc * dt
        return r / (r + 1)

    def __call__(self, x, dt):
        if self.x is None:
            self.x, self.dx = x.copy(), np.zeros_like(x)
            return x
        dx = (x - self.x) / dt
        a = self._a(self.dc, dt)
        self.dx = a * dx + (1 - a) * self.dx
        fc = self.fc + self.beta * np.abs(self.dx)
        a = self._a(fc, dt)
        self.x = a * x + (1 - a) * self.x
        return self.x


class Piste:
    _n = 0

    def __init__(self, obs):
        Piste._n += 1
        self.id = Piste._n
        self.obs = {}          # index d'image dessinée -> obs
        self.votes = {}
        self.vshort = {}
        self.rel = None        # pose relative mémorisée (17,2) en unités T
        self.relc = np.zeros(17, np.float32)
        self.box = obs["box"]
        self.vel = np.zeros(4, np.float32)
        self.last = -1
        self.hits = 0
        self.euro = Euro()
        self.T = None
        self.pied = 1.0
        self.hist = deque(maxlen=6)

    def equipe(self):
        if not self.votes:
            return "AUT"
        e = max(self.votes, key=self.votes.get)
        return e

    def short(self):
        return EQUIPES[self.equipe()]["s"]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / max(u, 1e-6)


def apparier(pistes, dets):
    from scipy.optimize import linear_sum_assignment
    if not pistes or not dets:
        return [], list(range(len(pistes))), list(range(len(dets)))
    C = np.ones((len(pistes), len(dets)), np.float32) * 9
    for i, p in enumerate(pistes):
        pb = p.box + p.vel
        ph = pb[3] - pb[1]
        for j, d in enumerate(dets):
            db = d["box"]
            o = iou(pb, db)
            dc = np.hypot((pb[0] + pb[2] - db[0] - db[2]) / 2, (pb[1] + pb[3] - db[1] - db[3]) / 2) / max(ph, 1)
            ds = abs(np.log(max(db[3] - db[1], 1) / max(ph, 1)))
            if o > 0.1 or dc < 0.6:
                C[i, j] = (1 - o) + 0.8 * dc + 0.5 * ds
    r, c = linear_sum_assignment(C)
    m = [(i, j) for i, j in zip(r, c) if C[i, j] < 2.0]
    mi = {i for i, _ in m}
    mj = {j for _, j in m}
    return m, [i for i in range(len(pistes)) if i not in mi], [j for j in range(len(dets)) if j not in mj]


def _hist_vote(h):
    if h is None:
        return None
    eq = {"ITA": h["bleu"], "RSA": h["vert"], "ARB": h["rouge"] * 0.8, "JAU": h["jaune"] * 0.6}
    e = max(eq, key=eq.get)
    seuil = {"ITA": 0.12, "RSA": 0.12, "ARB": 0.22, "JAU": 0.22}[e]
    return (e, eq[e]) if eq[e] > seuil else None



# ================================================================ MÊLÉE
def _debout(d):
    kp = d["kp"]
    ms, mh = (kp[EG, :2] + kp[ED, :2]) / 2, (kp[HG, :2] + kp[HD, :2]) / 2
    v = ms - mh
    ang = np.degrees(np.arctan2(abs(v[0]), -v[1]))
    tc = kp[[EG, ED, HG, HD], 2].mean()
    return ang < 38 and tc > 0.35


def trouver_melee(rgb, dets):
    """Mêlée / maul : >= 4 joueurs penchés imbriqués, les deux équipes au contact.
    -> (dict mêlée | None, joueurs restant à dessiner un par un)"""
    pen = [d for d in dets if not _debout(d)]
    if len(pen) < 4:
        return None, dets
    # groupe connexe (boîtes qui se touchent)
    n = len(pen)
    lab = list(range(n))

    def f(i):
        while lab[i] != i:
            i = lab[i]
        return i
    for i in range(n):
        for j in range(i + 1, n):
            a, b = pen[i]["box"], pen[j]["box"]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                lab[f(i)] = f(j)
    grp = {}
    for i in range(n):
        grp.setdefault(f(i), []).append(i)
    g = max(grp.values(), key=len)
    if len(g) < 4:
        return None, dets
    mb = np.zeros((DH, DW), bool)
    for i in g:
        mb |= pen[i]["mask"]
    ys, xs = np.nonzero(mb)
    y0, y1 = np.percentile(ys, 2) * DS, np.percentile(ys, 98) * DS
    x0, x1 = np.percentile(xs, 1) * DS, np.percentile(xs, 99) * DS
    if (x1 - x0) < 1.3 * (y1 - y0):
        return None, dets
    # ligne de contact : séparation bleu | vert le long de la mêlée
    m = cv2.resize(mb.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, sa, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    bleu = ((h >= 96) & (h <= 128) & (sa > 90) & (v > 60) & m).sum(0).astype(np.float32)
    vert = ((h >= 38) & (h <= 92) & (sa > 45) & (v < 125) & m).sum(0).astype(np.float32)
    if bleu.sum() < 300 or vert.sum() < 300:
        return None, dets
    cb, cv_ = np.cumsum(bleu), np.cumsum(vert)
    # bleu à gauche, vert à droite (ou l'inverse) : coût minimal
    c1 = cv_ + (cb[-1] - cb)         # vert à gauche + bleu à droite = erreurs si bleu à gauche
    c2 = cb + (cv_[-1] - cv_)
    if c1.min() <= c2.min():
        xc, gauche, droite = float(np.argmin(c1)), "ITA", "RSA"
    else:
        xc, gauche, droite = float(np.argmin(c2)), "RSA", "ITA"
    xsb = np.arange(W, dtype=np.float32)
    mb_b = (h >= 96) & (h <= 128) & (sa > 90) & (v > 60) & m
    mb_v = (h >= 38) & (h <= 92) & (sa > 45) & (v < 125) & m
    yb, xb = np.nonzero(mb_b)
    yv, xv = np.nonzero(mb_v)
    if gauche == "ITA":
        dxp, dyp = xv.mean() - xb.mean(), yv.mean() - yb.mean()
    else:
        dxp, dyp = xb.mean() - xv.mean(), yb.mean() - yv.mean()
    # le paquet le plus proche descend plus bas dans l'image : on n'en garde qu'une partie
    pente = float(np.clip(0.2 * dyp / max(abs(dxp), 1.0), -0.5, 0.5))
    membres = {id(pen[i]) for i in g}
    # échelle (px par mètre) : longueur d'un paquet non coupé par le cadre (~3 m),
    # sinon taille des joueurs debout proches, sinon taille des boîtes penchées
    cyaw = np.cos(np.arctan2(pente, np.sin(ELEV)))
    ech = []
    if x0 > 60:
        ech.append((xc - x0) / (3.0 * cyaw))
    if x1 < W - 60:
        ech.append((x1 - xc) / (3.0 * cyaw))
    for d in dets:
        b = d["box"]
        if id(d) not in membres and _debout(d) and abs(b[3] - y1) < 0.6 * (y1 - y0) and b[0] > 4 and b[2] < W - 4:
            ech.append((b[3] - b[1]) / 1.85)
    if not ech:
        ech.append(np.percentile([max(pen[i]["box"][2] - pen[i]["box"][0], pen[i]["box"][3] - pen[i]["box"][1]) for i in g], 75) / 1.0)
    ech = float(np.median(ech))
    reste = []
    for d in dets:
        if id(d) in membres:
            continue
        b = d["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if x0 < cx < x1 and y0 < cy < y1 and (not _debout(d) or b[1] > y0 - 0.25 * (y1 - y0)):
            continue                       # dans la mêlée : redessiné par le modèle
        reste.append(d)
    return dict(y0=y0, y1=y1, x0=x0, x1=x1, xc=xc, pente=pente, ech=ech, g=gauche, d=droite), reste


# Mêlée en 3D (mètres ; X = axe de poussée, Y = travers, Z = haut), projetée avec
# la caméra de la retransmission (élévation fixe, lacet tiré de l'image).
# rôles : (X épaules, Y, rôle) pour le paquet qui pousse vers +X
PAQUET = [(-0.22, -0.56, "P"), (-0.22, 0.0, "P"), (-0.22, 0.56, "P"),
          (-0.98, -0.29, "L"), (-0.98, 0.29, "L"),
          (-0.92, -0.82, "F"), (-0.92, 0.82, "F"), (-1.72, 0.0, "8")]
ELEV = np.deg2rad(16)


def _corps_melee(Xs, Y, sd, role, pompe, rng):
    """Squelette 3D (17,3) d'un joueur lié en mêlée, poussant vers sd*X."""
    k = np.zeros((17, 3), np.float32)
    dz = rng.uniform(-0.04, 0.04)
    S = np.float32([Xs, Y, 0.66 + dz])
    Hh = np.float32([Xs - sd * 0.56, Y, 0.74 + dz * 0.5])
    head = np.float32([Xs + sd * 0.2, Y, 0.5 + dz])
    L = np.float32([0, 1, 0]) * sd          # côté gauche du joueur
    for i in (NEZ, OG, OD, ORG, ORD):
        k[i] = head
    k[EG], k[ED] = S + 0.21 * L, S - 0.21 * L
    k[HG], k[HD] = Hh + 0.16 * L, Hh - 0.16 * L
    for hi, gi, ci, sg, st in ((HG, GG, CHG, 1, 0.0), (HD, GD, CHD, -1, 0.18)):
        k[gi] = Hh + sg * 0.19 * L + np.float32([sd * 0.12, 0, -0.34])
        k[ci] = Hh + sg * 0.21 * L + np.float32([-sd * (0.36 + st + 0.06 * pompe), 0, -0.70 - dz * 0.5])
    if role == "8":
        bras = ((0.18, 0.3, 0.6), (0.42, 0.34, 0.66))
    elif role == "L":
        bras = ((0.16, 0.34, 0.62), (0.38, 0.4, 0.7))
    else:                                    # bras de liaison sur le dos du voisin
        bras = ((0.0, 0.33, 0.72), (-0.14, 0.45, 0.74))
    (ex, ey, ez), (wx, wy, wz) = bras
    for (ei, wi), sg in (((CG, PG), 1), ((CD, PD), -1)):
        k[ei] = np.float32([Xs + sd * ex, Y, ez]) + sg * ey * L
        k[wi] = np.float32([Xs + sd * wx, Y, wz]) + sg * wy * L
    if role == "P":                          # bras extérieur du pilier : vers le sol, en appui
        k[CD] = np.float32([Xs + sd * 0.18, Y, 0.36]) - 0.3 * L
        k[PD] = np.float32([Xs + sd * 0.36, Y, 0.16]) - 0.34 * L
    return k


def joueurs_melee(sc, t):
    """Modèle de mêlée : 2 x 8 joueurs penchés (dos plats, têtes basses, bras liés),
    construit en 3D puis projeté ; calé sur la masse détectée (ligne de contact,
    hauteur, orientation de l'axe)."""
    e = ELEV
    yaw = float(np.clip(np.arctan2(sc.get("pente", 0.0), np.sin(e)), -0.95, 0.95))
    cy_, sy_ = np.cos(yaw), np.sin(yaw)

    def proj(P):
        u = P[..., 0] * cy_ - P[..., 1] * sy_
        v = (P[..., 0] * sy_ + P[..., 1] * cy_) * np.sin(e) - P[..., 2] * np.cos(e)
        return np.stack([u, v], -1)

    corps = []
    for sd, eq, dy in ((1, sc["g"], 0.0), (-1, sc["d"], 0.28)):
        for k, (Xs, Y, role) in enumerate(PAQUET):
            rng = np.random.default_rng(97 + k + (sd > 0) * 13)
            ph = 1.7 * k + (0.9 if sd < 0 else 0)
            pompe = np.sin(2 * np.pi * t / 13.0 + ph)
            Xs_ = sd * Xs + sd * 0.015 * pompe
            K3 = _corps_melee(Xs_, Y + dy, sd, role, pompe, rng)
            corps.append((sd, eq, k, K3))
    allp = np.concatenate([proj(c[3]) for c in corps])
    vb = allp[:, 1].max()
    # échelle : la masse projetée doit couvrir la masse détectée (hauteur visible,
    # et longueur des paquets quand ils ne sont pas coupés par le cadre)
    bh = sc["y1"] - sc["y0"]
    best, s = 1e9, sc["ech"]
    for cand in np.linspace(120, 700, 59):
        X = sc["xc"] + cand * allp[:, 0]
        Yv = sc["y1"] + cand * (allp[:, 1] - vb)
        vis = (X > 0) & (X < W)
        if vis.sum() < 20:
            continue
        c = abs((Yv[vis].max() - Yv[vis].min()) - bh) / bh
        if sc["x0"] > 60:
            c += 0.5 * abs(X.min() - sc["x0"]) / bh
        if sc["x1"] < W - 60:
            c += 0.5 * abs(X.max() - sc["x1"]) / bh
        if c < best:
            best, s = c, cand
    out = []
    for sd, eq, k, K3 in corps:
        P = proj(K3)
        k17 = np.float32(np.stack([sc["xc"] + s * P[:, 0], sc["y1"] + s * (P[:, 1] - vb)], 1))
        sol = proj(np.float32([(K3[HG, 0] + K3[HD, 0]) / 2, (K3[HG, 1] + K3[HD, 1]) / 2, 0.0]))
        j = Joueur()
        j.id, j.k, j.vis, j.T = 10000 + (sd > 0) * 100 + k, k17, np.ones(17, bool), 0.62 * s
        j.box = np.float32([k17[:, 0].min(), k17[:, 1].min(), k17[:, 0].max(), k17[:, 1].max()])
        j.eq = eq
        j.short = EQUIPES[eq]["s"]
        j.pied = -float(sd) if cy_ > 0 else float(sd)
        # côté gauche du joueur (+Y si sd>0) vers la caméra ?
        j.proche = (sd > 0)
        j.depth = float(sc["y1"] + s * (sol[1] - vb))
        j.mvt = 0.0
        out.append(j)
    return out


# ================================================================ STYLE
class Style:
    def __init__(self, echos=True, lignes=True, graine=11):
        self.echos = echos
        self.lignes = lignes
        self.fond = composition_fond(graine)
        self.grain = grain_papier()
        self.reset()

    def reset(self):
        self.k = 0
        self.pistes = []
        self.prev = None
        self.prev_small = None
        self.hz = None
        self.lig = []
        self.bal = None
        self.bal_miss = 99
        self.sc = None
        self.temps = []

    # -- analyse d'une image (sur les images paires) ------------------------------
    def analyser(self, rgb):
        t0 = time.time()
        hz = horizon(rgb)
        pers, bals = detecter(rgb)
        # tri : pas de spectateurs (pieds au-dessus de la pelouse), pas de miettes
        keep = []
        for d in pers:
            x0, y0, x1, y1 = d["box"]
            w, h = x1 - x0, y1 - y0
            if y1 < hz + 0.012 * H or h < 45:
                continue
            # joueur coupé par le bord du cadre : on ne dessine pas un morceau
            if (x0 < 6 or x1 > W - 6) and w < 0.33 * h:
                continue
            if w < 0.12 * h:
                continue
            keep.append(d)
        # doublons (même joueur détecté deux fois) : recouvrement de masques
        keep.sort(key=lambda d: -d["score"])
        final = []
        for d in keep:
            a = d["mask"].sum()
            dup = False
            for e in final:
                inter = (d["mask"] & e["mask"]).sum()
                if inter > 0.7 * max(1, min(a, e["mask"].sum())):
                    dup = True
                    break
            if not dup and a > 0:
                final.append(d)
        kps = poses(rgb, [d["box"] for d in final])
        mfull = None
        for d, kp in zip(final, kps):
            m = cv2.resize(d["mask"].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
            # contrôle par le masque : un point loin de la silhouette perd sa confiance
            dist = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 3)
            T0 = 0.25 * (d["box"][3] - d["box"][1])
            for i in range(17):
                x, y = int(np.clip(kp[i, 0], 0, W - 1)), int(np.clip(kp[i, 1], 0, H - 1))
                if dist[y, x] > 0.35 * T0:
                    kp[i, 2] *= 0.4
            d["kp"] = kp
            ht, hs = classe_couleur(rgb, kp, m)
            d["vote"] = _hist_vote(ht)
            d["vshort"] = None
            if hs is not None:
                s = max(hs, key=hs.get)
                if hs[s] > 0.25:
                    d["vshort"] = s
            sm = d["mask"].astype(np.uint8)
            mfull = sm if mfull is None else np.maximum(mfull, sm)
        sc, final = trouver_melee(rgb, final)
        lig = []
        if self.lignes:
            mm = None
            if mfull is not None:
                mm = cv2.resize(mfull, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST)
            lig = lignes_terrain(rgb, hz, mm)
        # ballon : proche d'un joueur, sous l'horizon, taille plausible
        bal = None
        for b in sorted(bals, key=lambda b: -b["score"]):
            x0, y0, x1, y1 = b["box"]
            w, h = x1 - x0, y1 - y0
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if cy < hz or max(w, h) < 14 or max(w, h) > 220:
                continue
            if sc is not None and sc["x0"] < cx < sc["x1"] and sc["y0"] - 30 < cy < sc["y1"]:
                continue
            # porté : près d'un poignet ou contre le buste d'un joueur
            pres = False
            for d in final:
                kq = d["kp"]
                Tq = 0.27 * (d["box"][3] - d["box"][1])
                for a in (PG, PD):
                    if kq[a, 2] > 0.25 and np.hypot(*(kq[a, :2] - [cx, cy])) < 0.8 * Tq:
                        pres = True
                bu = kq[[EG, ED, HG, HD], :2].mean(0)
                if np.hypot(*(bu - [cx, cy])) < 0.7 * Tq:
                    pres = True
            if not pres and b["score"] < 0.6:
                continue
            # un ballon est clair et peu saturé (pas un crampon fluo)
            bm = cv2.resize(b["mask"].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
            if bm.sum() < 20:
                continue
            hsvb = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[bm]
            if np.median(hsvb[:, 1]) > 85 or np.median(hsvb[:, 2]) < 140:
                continue
            # pas collé à une cheville (crampons, chaussettes blanches)
            pied = False
            for d in final:
                Tq = 0.25 * (d["box"][3] - d["box"][1])
                for a in (CHG, CHD):
                    if d["kp"][a, 2] > 0.3 and np.hypot(*(d["kp"][a, :2] - [cx, cy])) < 0.45 * Tq:
                        pied = True
            if pied and b["score"] < 0.6:
                continue
            ell = None
            cs, _ = cv2.findContours(b["mask"].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            if cs:
                c = max(cs, key=cv2.contourArea)
                if len(c) >= 5:
                    (ex, ey), (ea, eb), ang = cv2.fitEllipse(c.astype(np.float32))
                    ell = ((ex * DS, ey * DS), (ea * DS, eb * DS), ang)
            if ell is None:
                ell = ((cx, cy), (w, h), 0.0)
            (ex, ey), (ea, eb), ang = ell
            if ea < eb:
                ea, eb, ang = eb, ea, ang + 90
            ea = max(ea, 1.3 * eb)
            eb = max(eb, ea / 1.8)
            bal = (np.float32([ex, ey]), np.float32([ea / 2, eb / 2]), ang, b["score"])
            break
        self.temps.append(time.time() - t0)
        return dict(hz=hz, dets=final, lig=lig, bal=bal, sc=sc)

    # -- suivi causal --------------------------------------------------------------
    def suivre(self, an, idx, lisse=True):
        dets = an["dets"]
        vivantes = [p for p in self.pistes if idx - p.last <= 3]
        m, pn, dn = apparier(vivantes, dets)
        for i, j in m:
            p, d = vivantes[i], dets[j]
            nb = d["box"]
            p.vel = 0.5 * p.vel + 0.5 * (nb - p.box)
            p.box = nb
            p.last = idx
            p.hits += 1
            p.obs[idx] = d
        for j in dn:
            p = Piste(dets[j])
            p.last = idx
            p.hits = 1
            p.obs[idx] = dets[j]
            self.pistes.append(p)
        for i in pn:
            p = vivantes[i]
            p.box = p.box + p.vel
        self.pistes = [p for p in self.pistes if idx - p.last <= 3]
        for p in self.pistes:
            d = p.obs.get(idx)
            if d is None:
                continue
            if d["vote"] is not None:
                e, w = d["vote"]
                p.votes[e] = p.votes.get(e, 0) + w
            if d["vshort"] is not None:
                p.vshort[d["vshort"]] = p.vshort.get(d["vshort"], 0) + 1

    def joueur_de(self, p, kp, box, idx, mvt=0.0):
        k, vis = completer_pose(kp, p.rel if p.relc.sum() > 4 else None, box)
        ms, mh = (k[EG] + k[ED]) / 2, (k[HG] + k[HD]) / 2
        bw, bh = box[2] - box[0], box[3] - box[1]
        Tm = float(np.hypot(*(ms - mh)))
        cuisse = np.mean([np.hypot(*(k[HG] - k[GG])), np.hypot(*(k[HD] - k[GD]))])
        T = max(Tm, 0.75 * cuisse, 0.2 * max(bw, bh))
        p.T = T if p.T is None else 0.7 * p.T + 0.3 * T
        T = p.T
        # mémoire relative (points sûrs seulement)
        rel = (k - mh) / T
        if p.rel is None:
            p.rel = rel.copy()
        c = kp[:, 2] > 0.5
        p.rel[c] = 0.5 * p.rel[c] + 0.5 * rel[c]
        p.relc[c] += 1
        # orientation des pieds
        if kp[NEZ, 2] > 0.4 and abs(kp[NEZ, 0] - ms[0]) > 0.12 * T:
            p.pied = 0.7 * p.pied + 0.3 * np.sign(kp[NEZ, 0] - ms[0])
        j = Joueur()
        j.id, j.k, j.vis, j.T, j.box = p.id, k, vis, T, box
        j.eq = p.equipe()
        j.short = p.short()
        j.pied = 1.0 if p.pied >= 0 else -1.0
        cg = kp[[EG, CG, PG, HG, GG, CHG], 2].mean()
        cd = kp[[ED, CD, PD, HD, GD, CHD], 2].mean()
        j.proche = cg >= cd
        j.depth = max(k[CHG, 1], k[CHD, 1], box[3] - 0.05 * bh)
        j.mvt = mvt
        return j

    # -- rendu d'une image dessinée ------------------------------------------------
    def rendre(self, hz, lig, joueurs, echos, bal):
        img = self.fond.copy()
        hzi = int(round(hz))
        img[hzi:] = PELOUSE
        for th, rho, _ in lig:
            nx, ny = -np.sin(th), np.cos(th)
            p0 = np.float32([nx * rho, ny * rho])
            d = np.float32([np.cos(th), np.sin(th)])
            a, b = p0 - d * 4000, p0 + d * 4000
            cv2.line(img, tuple(_pts(a)[0, 0]), tuple(_pts(b)[0, 0]), LIGNE, 9, cv2.LINE_AA, 4)
        img[:max(hzi, 0)] = self.fond[:max(hzi, 0)]
        if hzi > 0:
            cv2.line(img, (0, hzi), (W, hzi), ENCRE, 7, cv2.LINE_AA)
        for j, col in echos:
            silhouette_echo(img, j, col)
        for j in sorted(joueurs, key=lambda j: j.depth):
            lw = int(np.clip(0.075 * j.T, 3, 6))
            dessiner_joueur(img, j, lw)
        if bal is not None:
            dessiner_ballon(img, ((bal[0][0], bal[0][1]), (bal[1][0], bal[1][1]), bal[2]), 5)
        out = img.astype(np.float32) * self.grain
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def _teinte(c, f):
        return tuple(int(round(a * (1 - f) + b * f)) for a, b in zip(c, PELOUSE))

    def _echos(self, p, j):
        out = []
        if not self.echos or len(p.hist) < 3:
            return out
        mh = (j.k[HG] + j.k[HD]) / 2
        for lag, f in ((4, 0.72), (2, 0.5)):
            if len(p.hist) > lag:
                old = p.hist[-1 - lag]
                d = np.hypot(*(((old.k[HG] + old.k[HD]) / 2) - mh))
                if 0.55 * j.T < d < 2.5 * j.T and 0.8 < old.T / j.T < 1.25:
                    out.append((old, self._teinte(EQUIPES[j.eq]["m"], f)))
        return out

    # -- image par image (causal) ---------------------------------------------------
    def coupe(self, rgb):
        s = cv2.cvtColor(cv2.resize(rgb, (54, 96), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32)
        c = self.prev_small is not None and np.abs(s - self.prev_small).mean() > 28
        self.prev_small = s
        return c

    def __call__(self, rgb):
        if self.coupe(rgb):
            self.pistes, self.hz, self.lig, self.bal = [], None, [], None
            self.k = self.k + (self.k % 2)      # on redessine tout de suite
        if self.k % 2 == 1 and self.prev is not None:
            self.k += 1
            return self.prev
        idx = self.k // 2
        an = self.analyser(rgb)
        self.hz = an["hz"] if self.hz is None else 0.7 * self.hz + 0.3 * an["hz"]
        self.lig = an["lig"]
        self.suivre(an, idx)
        joueurs, echos = [], []
        for p in self.pistes:
            if p.hits < 2 and idx - p.last > 0:
                continue
            d = p.obs.get(idx)
            if d is None:
                d = p.obs[p.last]
            kp = d["kp"].copy()
            kp[:, :2] = p.euro(kp[:, :2], 2 / 30.0)
            j = self.joueur_de(p, kp, p.box, idx)
            echos += self._echos(p, j)
            p.hist.append(j)
            joueurs.append(j)
        b = an["bal"]
        if b is not None:
            if self.bal is None:
                self.bal = list(b[:3])
            else:
                self.bal[0] = 0.4 * self.bal[0] + 0.6 * b[0]
                self.bal[1] = 0.6 * self.bal[1] + 0.4 * b[1]
                self.bal[2] = b[2]
            self.bal_miss = 0
        else:
            self.bal_miss += 1
            if self.bal_miss > 3:
                self.bal = None
        sc = an["sc"]
        if sc is not None:
            if self.sc is None:
                self.sc = dict(sc)
            else:
                for c in ("y0", "y1", "x0", "x1", "xc", "pente", "ech"):
                    self.sc[c] = 0.7 * self.sc[c] + 0.3 * sc[c]
                self.sc["g"], self.sc["d"] = sc["g"], sc["d"]
            self.sc_miss = 0
        else:
            self.sc_miss = getattr(self, "sc_miss", 0) + 1
            if self.sc_miss > 4:
                self.sc = None
        if self.sc is not None:
            joueurs += joueurs_melee(self.sc, idx)
        self.prev = self.rendre(self.hz, self.lig, joueurs, echos, self.bal)
        self.k += 1
        return self.prev

    # -- plan entier (anticipation) -------------------------------------------------
    def render_shot(self, frames, log=None):
        """Plan entier : analyse toutes les 2 images, pistes complétées dans les deux
        sens (trous comblés), lissage centré pondéré par la confiance, équipe votée
        sur toute la piste. -> liste d'images (même longueur que frames)."""
        n = len(frames)
        # découpe en sous-plans aux coupes franches
        bornes = [0]
        self.prev_small = None
        for k in range(n):
            if self.coupe(np.asarray(frames[k])) and k > 0:
                bornes.append(k)
        bornes.append(n)
        out = []
        for a, b in zip(bornes[:-1], bornes[1:]):
            out += self._shot(frames[a:b], log)
        return out

    def _shot(self, frames, log=None):
        self.reset()
        n = len(frames)
        idxs = list(range(0, n, 2))
        ans = []
        for t, k in enumerate(idxs):
            an = self.analyser(np.asarray(frames[k]))
            ans.append(an)
            self.suivre(an, t)
            if log:
                log(f"  analyse {k}/{n} {self.temps[-1]:.2f}s  {len(an['dets'])} joueurs")
        Np = len(idxs)
        hz = np.array([a["hz"] for a in ans], np.float32)
        hz = np.array([np.median(hz[max(0, t - 3):t + 4]) for t in range(Np)], np.float32)
        if np.ptp(hz) < 0.08 * H:
            hz[:] = np.median(hz)
        scs = [a["sc"] for a in ans]
        nsc = sum(x is not None for x in scs)
        melee = [None] * Np
        if nsc >= max(2, 0.4 * Np):
            keys = ("y0", "y1", "x0", "x1", "xc", "pente", "ech")
            vals = {c: np.array([x[c] if x is not None else np.nan for x in scs], np.float32) for c in keys}
            gl = [x["g"] for x in scs if x is not None]
            g = max(set(gl), key=gl.count)
            for t in range(Np):
                lo, hi = max(0, t - 3), min(Np, t + 4)
                md = {c: float(np.nanmedian(vals[c][lo:hi])) if np.isfinite(vals[c][lo:hi]).any()
                      else float(np.nanmedian(vals[c])) for c in keys}
                md["g"], md["d"] = g, ("RSA" if g == "ITA" else "ITA")
                melee[t] = md
        # pistes : interpolation des trous, lissage centré
        tracks = []
        for p in self.pistes_all():
            ts = sorted(p.obs)
            if len(ts) < 2 and p.obs[ts[0]]["score"] < 0.8:
                continue
            if len(ts) < 2 and Np > 3:
                continue
            K = np.zeros((Np, 17, 3), np.float32)
            Bx = np.zeros((Np, 4), np.float32)
            have = np.zeros(Np, bool)
            for t in ts:
                K[t] = p.obs[t]["kp"]
                Bx[t] = p.obs[t]["box"]
                have[t] = True
            t0, t1 = ts[0], ts[-1]
            for t in range(t0, t1 + 1):
                if not have[t]:
                    a = max(u for u in ts if u < t)
                    b = min(u for u in ts if u > t)
                    if b - a > 5:
                        continue
                    w = (t - a) / (b - a)
                    K[t] = (1 - w) * K[a] + w * K[b]
                    K[t, :, 2] = np.minimum(K[a, :, 2], K[b, :, 2]) * 0.8
                    Bx[t] = (1 - w) * Bx[a] + w * Bx[b]
                    have[t] = True
            # lissage centré (gauss sigma 0.9 image dessinée), pondéré par la confiance
            Ks = K.copy()
            g = np.exp(-0.5 * (np.arange(-2, 3) / 0.9) ** 2)
            for t in range(Np):
                if not have[t]:
                    continue
                num = np.zeros((17, 2), np.float32)
                den = np.zeros((17, 1), np.float32)
                for o, wg in zip(range(-2, 3), g):
                    u = t + o
                    if 0 <= u < Np and have[u]:
                        c = np.maximum(K[u, :, 2:3], 0.05) * wg
                        num += K[u, :, :2] * c
                        den += c
                Ks[t, :, :2] = num / den
            tracks.append((p, Ks, Bx, have))
        # rendu
        Piste_rel_reset = {}
        res = [None] * n
        bal = self._ballon_shot(ans, tracks)
        for t, k in enumerate(idxs):
            joueurs, echos = [], []
            for p, Ks, Bx, have in tracks:
                if not have[t]:
                    continue
                if p.id not in Piste_rel_reset:
                    p.rel, p.relc, p.T, p.hist = None, np.zeros(17, np.float32), None, deque(maxlen=6)
                    Piste_rel_reset[p.id] = 1
                j = self.joueur_de(p, Ks[t], Bx[t], t)
                echos += self._echos(p, j)
                p.hist.append(j)
                joueurs.append(j)
            if melee[t] is not None:
                joueurs += joueurs_melee(melee[t], t)
            img = self.rendre(float(hz[t]), ans[t]["lig"], joueurs, echos, bal[t])
            res[k] = img
            if k + 1 < n:
                res[k + 1] = img
        return res

    def pistes_all(self):
        # toutes les pistes créées pendant l'analyse (y compris mortes)
        seen = {}
        for p in self._toutes:
            seen[p.id] = p
        return list(seen.values())

    def _ballon_shot(self, ans, tracks):
        """Ballon sur le plan entier. Chaque détection est rattachée à son porteur
        (poignets / buste les plus proches) ; entre deux détections, ou juste avant /
        après, le ballon suit le porteur (position relative interpolée)."""
        Np = len(ans)

        def repere(k, box):
            mh = (k[HG, :2] + k[HD, :2]) / 2
            ms = (k[EG, :2] + k[ED, :2]) / 2
            T = max(float(np.hypot(*(ms - mh))), 0.22 * (box[3] - box[1]))
            return mh, T

        obs = []
        for t, a in enumerate(ans):
            b = a["bal"]
            if b is None:
                continue
            best = None
            for i, (p, Ks, Bx, have) in enumerate(tracks):
                if not have[t]:
                    continue
                k = Ks[t]
                mh, T = repere(k, Bx[t])
                pts = [k[PG, :2], k[PD, :2], (k[EG, :2] + k[ED, :2] + k[HG, :2] + k[HD, :2]) / 4]
                d = min(np.hypot(*(q - b[0])) for q in pts)
                if d < 1.1 * T and (best is None or d < best[0]):
                    best = (d, i, (b[0] - mh) / T, T)
            if best is not None:
                obs.append(dict(t=t, i=best[1], rel=best[2], T=best[3], b=b))
            elif b[3] > 0.5:
                obs.append(dict(t=t, i=None, rel=None, T=None, b=b))
        # confirmation : au moins 2 détections pour le même porteur (ou proches dans le temps)
        conf = []
        for o in obs:
            n_same = sum(1 for q in obs if q is not o and q["i"] == o["i"] and o["i"] is not None)
            n_near = sum(1 for q in obs if q is not o and abs(q["t"] - o["t"]) <= 3)
            if n_same >= 1 or n_near >= 1:
                conf.append(o)
        res = [None] * Np
        for t in range(Np):
            if not conf:
                break
            av = [o for o in conf if o["t"] <= t]
            ap = [o for o in conf if o["t"] >= t]
            pr = av[-1] if av else None
            nx = ap[0] if ap else None
            cand = [o for o in (pr, nx) if o is not None and abs(o["t"] - t) <= 8]
            if not cand:
                continue
            o = min(cand, key=lambda o: abs(o["t"] - t))
            if o["i"] is not None:
                p, Ks, Bx, have = tracks[o["i"]]
                if not have[t]:
                    continue
                rel = o["rel"]
                if pr is not None and nx is not None and pr["i"] == nx["i"] == o["i"] and nx["t"] > pr["t"]:
                    w = (t - pr["t"]) / (nx["t"] - pr["t"])
                    rel = (1 - w) * pr["rel"] + w * nx["rel"]
                mh, T = repere(Ks[t], Bx[t])
                c = mh + rel * T
                ax = o["b"][1] * T / o["T"]
                res[t] = (c, ax, o["b"][2], 0)
            elif o["t"] == t:
                res[t] = (o["b"][0], o["b"][1], o["b"][2], 0)
        # lissage léger de la position
        out = []
        for t in range(Np):
            r = res[t]
            if r is None:
                out.append(None)
                continue
            num, den = np.zeros(2, np.float32), 0.0
            for u, w in ((t - 1, 0.25), (t, 0.5), (t + 1, 0.25)):
                if 0 <= u < Np and res[u] is not None:
                    num += w * res[u][0]
                    den += w
            out.append((num / den, r[1], r[2], 0))
        return out


# conservation de toutes les pistes pour le mode « plan entier »
_orig_suivre = Style.suivre


def _suivre_mem(self, an, idx, lisse=True):
    if not hasattr(self, "_toutes") or idx == 0:
        self._toutes = []
    _orig_suivre(self, an, idx, lisse)
    ids = {p.id for p in self._toutes}
    self._toutes += [p for p in self.pistes if p.id not in ids]


Style.suivre = _suivre_mem


if __name__ == "__main__":
    import sys
    a = cv2.cvtColor(cv2.imread(sys.argv[1]), cv2.COLOR_BGR2RGB)
    a = cv2.resize(a, (W, H))
    st = Style()
    cv2.imwrite(sys.argv[2], cv2.cvtColor(st(a), cv2.COLOR_RGB2BGR))
