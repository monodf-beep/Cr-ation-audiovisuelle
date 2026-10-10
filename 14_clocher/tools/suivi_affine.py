# Suivi affine du cadran dans le plan recadre : pour chaque image i, matrice 2x3 qui envoie
# les coordonnees de l'image de reference (n 90) vers celles de l'image i.
import cv2, json, sys, numpy as np
src_zoom, suivi_src, sortie = sys.argv[1:4]
REF, W, H, fps = 90, 1080, 1920, 30
fin_zoom, larg_min = 2.2, 400
p = np.array(json.load(open(suivi_src)), float)
k = 9; pad = np.pad(p, ((k,k),(0,0)), mode='edge')
lisse = np.array([pad[i:i+2*k+1].mean(0) for i in range(len(p))])
def Z(i):  # meme recadrage que zoom.py : p_out = (p_src - o) * s
    t = i/fps; a = min(t/fin_zoom, 1); a = a*a*(3-2*a)
    cw = W + (larg_min-W)*a; ch = cw*H/W
    cx = W/2 + (lisse[i][0]-W/2)*a; cy = H/2 + (lisse[i][1]-H/2)*a
    x0 = min(max(cx-cw/2,0),W-cw); y0 = min(max(cy-ch/2,0),H-ch)
    return np.array([x0,y0]), W/cw
v = cv2.VideoCapture(src_zoom); imgs = []
while True:
    ok, f = v.read()
    if not ok: break
    imgs.append(cv2.cvtColor(cv2.resize(f, (W//2, H//2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32))
oR, sR = Z(REF); tpl = imgs[REF]; res = []
crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-6)
prev = None
for i in range(len(imgs)):
    oi, si = Z(i); s = si/sR
    tr = (oR/sR*0 + 0)  # p_out_i = ((p_ref/sR + oR) + (pts_i - pts_ref) - oi) * si
    b = ((oR + p[i] - p[REF] - oi) * si)
    M = np.array([[s,0,b[0]/2],[0,s,b[1]/2]], np.float32)  # echelle demi-resolution
    if prev is not None and i > REF - 60: M = prev.copy() if i != REF else M
    try:
        cc, M = cv2.findTransformECC(tpl, imgs[i], M, cv2.MOTION_AFFINE, crit, None, 5)
    except cv2.error:
        cc = -1
    prev = M
    M2 = M.copy(); M2[:,2] *= 2
    res.append({'M': M2.tolist(), 'cc': float(cc)})
json.dump(res, open(sortie,'w'))
print(len(res), 'cc min', min(r['cc'] for r in res), [round(res[j]['cc'],3) for j in range(0,len(res),20)])
