import cv2,numpy as np,glob,json
import puppet as P
fs=sorted(glob.glob('w/*.png'))
Hs={int(k):np.array(v) for k,v in json.load(open('H.json')).items()}
for i in range(3): Hs[i]=np.eye(3)
x0,y0=225,830
T=np.array([[1,0,x0-P.PAD],[0,1,y0-P.PAD],[0,0,1.]])
def ease(t): t=min(max(t,0),1); return t*t*(3-2*t)
def eo(t): t=min(max(t,0),1); return 1-(1-t)**3
def ei(t): t=min(max(t,0),1); return t**2
def seg(f,a,b): return (f-a)/(b-a)
def pose(f):
    land=0;buck=0;kick=0
    if f<12: return 0,0,0
    if f<22: land=26*ei(seg(f,12,22))*1.06
    elif f<30: land=26+1.5*np.sin(np.pi*seg(f,22,30))*(1-seg(f,22,30))*-1
    elif f<64: land=26
    elif f<82: land=26*(1-ease(seg(f,64,82)))
    if 32<=f<40: u=eo(seg(f,32,40)); buck=12*u; kick=42*u
    elif 40<=f<48: u=1-ease(seg(f,40,48)); buck=12*u; kick=42*u
    elif 50<=f<55: u=eo(seg(f,50,55)); buck=7*u; kick=30*u
    elif 55<=f<62: u=1-ease(seg(f,55,62)); buck=7*u; kick=30*u
    return land,buck,kick
sil=np.load('fr/sil.npy').astype(np.uint8)
silp=np.zeros((1920,1080),np.uint8); silp[y0:y0+sil.shape[0],x0:x0+sil.shape[1]]=sil
silp=cv2.dilate(silp,np.ones((9,9),np.uint8))
for i,f in enumerate(fs):
    im=cv2.imread(f)
    p=pose(i)
    if p!=(0,0,0) and i in Hs:
        H=Hs[i]
        m=cv2.warpPerspective(silp,H,(1080,1920))
        ys,xs=np.nonzero(m); pad=40
        a,b,c,d=max(ys.min()-pad,0),min(ys.max()+pad,1920),max(xs.min()-pad,0),min(xs.max()+pad,1080)
        sub=im[a:b,c:d]
        cl=cv2.inpaint(sub,m[a:b,c:d],7,cv2.INPAINT_TELEA)
        # smooth the filled area to kill streaks
        bl=cv2.blur(cl,(31,31)); mm=cv2.GaussianBlur(m[a:b,c:d].astype(np.float32)/255,(0,0),6)[...,None]
        cl=(cl*(1-mm)+bl*mm)
        im=im.astype(np.float32); im[a:b,c:d]=cl
        Fm=P.pose(*p)
        Fw=cv2.warpPerspective(Fm,H@T,(1080,1920),flags=cv2.INTER_LINEAR,borderValue=(1,1,1))
        im=np.clip(im*Fw,0,255).astype(np.uint8)
    cv2.imwrite(f'o/{i:04d}.png',im)
print('done')
