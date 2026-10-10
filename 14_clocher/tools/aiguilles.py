# Recompose le plan du clocher : aiguilles d'origine effacees (plaque propre), aiguilles redessinees
# et animees : recul par a-coups, blocage, casse, chute par gravite, balancier amorti jusqu'au VI.
import cv2, json, sys, subprocess, numpy as np
d = sys.argv[1]  # dossier de travail (z/)
src, sortie = sys.argv[2], sys.argv[3]
W, H, FPS, N = 1080, 1920, 30, 250
cx, cy, ew, eh, ea = np.load(f'{d}/ellipse.npy'); M = np.load(f'{d}/repere.npy')
x0, y0 = np.load(f'{d}/carre.npy'); P = 768
aff = [np.array(r['M']) for r in json.load(open(f'{d}/affine.json'))]
plaque = cv2.imread(f'{d}/cadran-cv.png').astype(np.float32)
masque = cv2.imread(f'{d}/cadran-mask.png', 0)
masque = cv2.dilate(masque, np.ones((11,11),np.uint8)); masque = cv2.GaussianBlur(masque, (0,0), 4).astype(np.float32)/255
ref = cv2.imread(f'{d}/ref.png').astype(np.float32)
g = cv2.cvtColor(ref.astype(np.uint8), cv2.COLOR_BGR2GRAY)
core = (cv2.imread(f'{d}/mask-full.png',0) > 0) & (g < 55)
couleur = ref[core].mean(0); print('couleur aiguilles', couleur)

# ---- choregraphie (angles en degres, sens horaire depuis XII) ----
def spring(t, dur=0.09):  # 0 -> 1 avec leger depassement
    if t <= 0: return 0.0
    if t < dur: return float(np.sin(t/dur*np.pi/2))*1.08
    return 1 + 0.08*np.exp(-(t-dur)*30)*np.cos((t-dur)*55)
rng = np.random.default_rng(7)
bruit = rng.normal(0, 1, 4000)
def tremble(t, amp):
    k = t*FPS*2; i = int(k); f = k-i
    return amp*(bruit[i]*(1-f) + bruit[i+1]*f)
TICKS = [2.45, 2.80, 3.11, 3.38, 3.61, 3.80]
TRY = [4.02, 4.33, 4.58]; CASSE = 4.82
def avant_casse(t):
    a, c = 110.0, 298.0
    for tk in TICKS:
        s = spring(t-tk); a -= 10*s; c -= 1.4*s
    if t > 3.95:
        amp = min((t-3.95)/0.85, 1)
        a += tremble(t, 0.4+1.1*amp); c += tremble(t+20, 0.3*amp)
        for tr in TRY:
            u = t-tr
            if 0 < u < 0.16: a -= 4*np.sin(u/0.16*np.pi/2)
            elif 0.16 <= u < 0.24: a -= 4*(1-(u-0.16)/0.08)
    return a, c
# chute : pendule amorti integre finement
a_casse, c_casse = avant_casse(CASSE)
phi, om = np.radians(a_casse-6-180), 0.0  # petit decroche en arriere a la casse
W0, C, MU = 7.2, 1.6, 2.0
pend = {0: np.degrees(phi)+180}; t = CASSE; dt = 1/(FPS*40); arret = None
while t < N/FPS + 0.1:
    for _ in range(40):
        acc = -W0**2*np.sin(phi) - C*om - MU*np.sign(om)*(abs(om) > 1e-3)
        om += acc*dt; phi += om*dt; t += dt
        if arret is None and t > CASSE+1.5 and abs(phi) < np.radians(1.5) and abs(om) < 0.4: arret = t
        if arret is not None: om = 0.0; phi *= np.exp(-dt*12)
    pend[round((t-CASSE)*FPS)] = np.degrees(phi)+180
print('arret au VI a t=%.2f s' % (arret or -1))
def angles(t):
    if t < CASSE: return avant_casse(t)
    k = round((t-CASSE)*FPS); a = pend.get(k, 180.0)
    c = c_casse + 3*spring(t-CASSE, 0.06)  # l'autre aiguille se decale d'un cran et reste figee
    return a, c

# ---- dessin des aiguilles dans le plan du cadran (unite = rayon du cadran) ----
SS = 3
def vers_px(pts):  # points du cadran -> pixels du carre sur-echantillonne
    q = (M @ np.array(pts).T).T + [cx-x0, cy-y0]
    return np.round(q*SS*16).astype(np.int32)
def fleche(th):
    t = np.radians(th); dv = np.array([np.sin(t), -np.cos(t)]); n = np.array([np.cos(t), np.sin(t)])
    P_ = lambda r, w: dv*r + n*w
    return [P_(-0.07,0.024),P_(0.40,0.02),P_(0.43,0.058),P_(0.61,0.0),P_(0.43,-0.058),P_(0.40,-0.02),P_(-0.07,-0.024)]
def lune(th):
    t = np.radians(th); dv = np.array([np.sin(t), -np.cos(t)]); n = np.array([np.cos(t), np.sin(t)])
    tige = [dv*-0.05+n*0.024, dv*0.43+n*0.02, dv*0.43-n*0.02, dv*-0.05-n*0.024]
    ext = [dv*0.47 + 0.075*(np.cos(u)*dv + np.sin(u)*n) for u in np.linspace(0, 2*np.pi, 60)]
    inn = [dv*0.505 + 0.065*(np.cos(u)*dv + np.sin(u)*n) for u in np.linspace(0, 2*np.pi, 60)]
    return tige, ext, inn
def calque(a, c):
    m = np.zeros((P*SS, P*SS), np.uint8)
    tige, ext, inn = lune(c)
    cv2.fillPoly(m, [vers_px(tige)], 255, cv2.LINE_AA, 4)
    lun = np.zeros_like(m); cv2.fillPoly(lun, [vers_px(ext)], 255, cv2.LINE_AA, 4)
    trou = np.zeros_like(m); cv2.fillPoly(trou, [vers_px(inn)], 255, cv2.LINE_AA, 4)
    m = np.maximum(m, (lun.astype(int)*(255-trou.astype(int))//255).astype(np.uint8))
    cv2.fillPoly(m, [vers_px(fleche(a))], 255, cv2.LINE_AA, 4)
    moyeu = [ [0.10*np.cos(u), 0.10*np.sin(u)] for u in np.linspace(0, 2*np.pi, 80)]
    cv2.fillPoly(m, [vers_px(moyeu)], 255, cv2.LINE_AA, 4)
    m = cv2.resize(m, (P, P), interpolation=cv2.INTER_AREA).astype(np.float32)/255
    return cv2.GaussianBlur(m, (0,0), 1.1)

v = cv2.VideoCapture(src); frames = []
while True:
    ok, f = v.read()
    if not ok: break
    frames.append(f)
T0 = np.array([[1,0,x0],[0,1,y0],[0,0,1]], float)
ff = subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
  '-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p',sortie], stdin=subprocess.PIPE)
anneau = np.zeros((P,P), np.float32); cv2.ellipse(anneau, ((cx-x0, cy-y0),(ew*0.85, eh*0.85), ea), 1, -1)
cv2.ellipse(anneau, ((cx-x0, cy-y0),(ew*0.62, eh*0.62), ea), 0, -1)
for i in range(N):
    j = i if i < len(frames) else 2*(len(frames)-1) - i
    f = frames[j].astype(np.float32)
    A = (np.vstack([aff[j], [0,0,1]]) @ T0)[:2]
    wm = cv2.warpAffine(masque, A, (W,H))[...,None]
    wp = cv2.warpAffine(plaque, A, (W,H))
    wr = cv2.warpAffine(anneau, A, (W,H)) > 0.5
    gain = f[wr].mean(0) / np.maximum(cv2.warpAffine(ref[y0:y0+P, x0:x0+P], A, (W,H))[wr].mean(0), 1)
    f = f*(1-wm) + wp*gain*wm
    a, c = angles(i/FPS)
    al = cv2.warpAffine(calque(a, c), A, (W,H))[...,None]
    f = f*(1-al) + (couleur*gain)*al
    ff.stdin.write(np.clip(f,0,255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
