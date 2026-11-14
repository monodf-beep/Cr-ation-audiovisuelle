import sys,cv2,numpy as np
sys.path.insert(0,'/home/user/Cr-ation-audiovisuelle/06_reel_vocab/styles')
import silhouettes as SIL
PAPIER=np.array([240,231,212],np.float32); NOIR=np.array([28,22,24],np.float32)
# familles d'encre : rampe sombre -> clair (4 tons)
R={'azur':[(14,34,92),(24,74,170),(40,116,220),(128,178,238)],
   'vert':[(6,36,24),(10,74,46),(20,112,70),(120,176,130)],
   'peau':[(92,52,36),(150,92,62),(212,156,116),(238,204,170)],
   'blanc':[(70,64,62),(150,142,132),(226,216,198),(246,240,226)],
   'rouge':[(96,14,16),(160,26,26),(216,48,40),(238,140,120)],
   'pel':[(52,92,40),(74,124,52),(96,150,62),(128,176,84)],
   'ocre':[(60,40,30),(150,70,40),(222,160,50),(240,225,190)]}
def familles(rgb,joueur):
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB).astype(np.float32); hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    h,s,v=[hsv[...,i].astype(np.int32) for i in range(3)]
    f=np.full(h.shape,'blanc',object)
    f[(s>70)&(h>=95)&(h<=130)]='azur'
    f[(s>60)&(h>=35)&(h<=92)]='vert'
    f[(s>50)&((h<=22)|(h>=170))&(v>60)]='peau'
    f[(s>150)&((h<=6)|(h>=172))&(v>120)]='rouge'
    fj=f.copy()
    ff=f.copy(); ff[:]= 'ocre'; ff[(s>60)&(h>=30)&(h<=92)]='pel'
    return np.where(joueur,fj,ff)
def lisse(f,sig):
    noms=list(R); best=np.full(f.shape,-1,np.float32); out=np.zeros(f.shape,np.int32)
    for k,n in enumerate(noms):
        b=cv2.GaussianBlur((f==n).astype(np.float32),(0,0),sig); sel=b>best; out[sel]=k; best[sel]=b[sel]
    return out,noms
def base(path):
    rgb=cv2.cvtColor(cv2.imread(path),cv2.COLOR_BGR2RGB)
    pers,bal=SIL.detecter(rgb); H,W=rgb.shape[:2]; m=np.zeros((H,W),bool)
    for p in pers:
        mm=cv2.resize(p['mask'].astype(np.uint8),(W,H),interpolation=cv2.INTER_LINEAR)>0
        if mm.sum()>0.004*H*W: m|=mm
    m=cv2.GaussianBlur(m.astype(np.float32),(0,0),4)>0.5
    doux=cv2.edgePreservingFilter(rgb,flags=1,sigma_s=40,sigma_r=0.35)
    L=cv2.cvtColor(doux,cv2.COLOR_RGB2LAB)[...,0].astype(np.float32)/255
    fam,noms=lisse(familles(doux,m),5)
    # fond : simplifié fortement
    Lf=cv2.GaussianBlur(L,(0,0),14); L=np.where(m,L,Lf)
    return rgb,m,L,fam,noms
def contour(img,m,ep=5):
    cs,_=cv2.findContours(m.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img,cs,-1,tuple(int(x) for x in NOIR),ep,cv2.LINE_AA)
def grain(img):
    g=np.random.default_rng(3).normal(0,5,img.shape[:2]).astype(np.float32)[...,None]
    return np.clip(img.astype(np.float32)+g,0,255).astype(np.uint8)
def serigraphie(path):
    rgb,m,L,fam,noms=base(path)
    # 4 tons par famille, seuils relatifs à la famille (égalisation locale)
    out=np.zeros_like(rgb)
    for k,n in enumerate(noms):
        sel=fam==k
        if not sel.any(): continue
        q=np.quantile(L[sel],[0.2,0.55,0.85]); lv=np.digitize(cv2.GaussianBlur(L,(0,0),2.2),q)
        ramp=np.array(R[n],np.uint8); out[sel]=ramp[lv[sel]]
    contour(out,m); return grain(out)
def trame(path):
    rgb,m,L,fam,noms=base(path)
    out=np.zeros_like(rgb)
    for k,n in enumerate(noms): out[fam==k]=R[n][2] if n not in('ocre',) else R[n][3]
    H,W=L.shape; yy,xx=np.mgrid[0:H,0:W].astype(np.float32); a=np.deg2rad(30); p=11
    u=(xx*np.cos(a)+yy*np.sin(a))/p; v=(-xx*np.sin(a)+yy*np.cos(a))/p
    d=np.sqrt((u-np.round(u))**2+(v-np.round(v))**2)
    Ln=L.copy()
    for k in range(len(noms)):
        sel=fam==k
        if sel.any(): lo,hi=np.quantile(L[sel],[0.05,0.9]); Ln[sel]=np.clip((L[sel]-lo)/max(hi-lo,1e-3),0,1)
    r=0.62*(1-cv2.GaussianBlur(Ln,(0,0),2))**0.9
    dots=np.clip((r-d)*p/1.2+0.5,0,1)[...,None]
    encre=np.array([24,30,70],np.float32)
    o=out.astype(np.float32)*(1-dots*0.92)+encre*dots*0.92
    o=o.astype(np.uint8); contour(o,m,6); return grain(o)
def gravure(path):
    rgb,m,L,fam,noms=base(path)
    out=np.zeros((*L.shape,3),np.float32)
    for k,n in enumerate(noms):
        c=np.array(R[n][3 if n in('ocre','blanc') else 2],np.float32); out[fam==k]=PAPIER*0.45+c*0.55
    H,W=L.shape; yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    Ln=L.copy()
    for k in range(len(noms)):
        sel=fam==k
        if sel.any(): lo,hi=np.quantile(L[sel],[0.05,0.9]); Ln[sel]=np.clip((L[sel]-lo)/max(hi-lo,1e-3),0,1)
    D=1-cv2.GaussianBlur(Ln,(0,0),1.8)
    def hach(ang,per,seuil):
        a=np.deg2rad(ang); t=(xx*np.cos(a)+yy*np.sin(a))/per; tri=np.abs(t-np.round(t))*2
        w=np.clip((D-seuil)/(1-seuil),0,1)*0.75
        return np.clip((w-tri)*per/1.5+0.5,0,1)
    ink=np.maximum(hach(40,9,0.15),hach(-35,9,0.55))
    ed=cv2.Canny((cv2.GaussianBlur(L,(0,0),2)*255).astype(np.uint8),30,80); ed=cv2.dilate(ed,np.ones((2,2),np.uint8))>0
    ink=np.maximum(ink,(ed&m).astype(np.float32))[...,None]
    o=(out*(1-ink)+NOIR*ink).astype(np.uint8); contour(o,m,5); return o
import PIL.Image as I
for nom,fn in [('serigraphie',serigraphie),('trame',trame),('gravure',gravure)]:
    for p in ['melee','b']:
        I.fromarray(fn(p+'.png')).save(f'{nom}_{p}.jpg',quality=90); print(nom,p,flush=True)
