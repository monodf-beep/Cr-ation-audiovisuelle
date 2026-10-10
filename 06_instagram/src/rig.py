import cv2,numpy as np
roi=cv2.imread('fr/roi.png').astype(np.float32)
sil=np.load('fr/sil.npy').astype(np.uint8)
PAD=150
def pad(a,v): return cv2.copyMakeBorder(a,PAD,PAD,PAD,PAD,cv2.BORDER_CONSTANT,value=v)
clean=cv2.inpaint(roi.astype(np.uint8),cv2.dilate(sil,np.ones((7,7),np.uint8)),9,cv2.INPAINT_TELEA)
clean=cv2.blur(clean,(25,25)).astype(np.float32)
F=np.clip(roi/np.maximum(clean,1),0,1); F[sil==0]=1
F=pad(F,(1,1,1))
yy,xx=np.mgrid[0:F.shape[0],0:F.shape[1]].astype(np.float32)
X=xx-PAD; Y=yy-PAD
def ss(t): t=np.clip(t,0,1); return t*t*(3-2*t)
SH=np.array([180.,110.]); HIP=np.array([345.,205.])
w_front=ss((195-X)/30)*(Y>30)
w_hind=ss(((Y-HIP[1])*0.8+(X-HIP[0])*0.6+10)/70)*(Y>150)
HOOF_H=np.array([405,365.]); HOOF_F=np.array([20,150.])
def skin(img,ang,c,w):
    if ang==0: return img
    a=np.deg2rad(ang)*w; px=X-c[0]; py=Y-c[1]; co=np.cos(a); s=np.sin(a)
    mx=co*px-s*py+c[0]+PAD; my=s*px+co*py+c[1]+PAD
    return cv2.remap(img,mx.astype(np.float32),my.astype(np.float32),cv2.INTER_LINEAR,borderValue=(1,1,1))
def rot(ang,c):
    c=c+PAD
    return np.vstack([cv2.getRotationMatrix2D((float(c[0]),float(c[1])),ang,1),[0,0,1]])
def fwd_pt(p,ang,c):  # where a rest point goes under skin rotation with weight 1 (inverse of remap)
    a=-np.deg2rad(ang); d=p-c
    return np.array([np.cos(a)*d[0]-np.sin(a)*d[1],np.sin(a)*d[0]+np.cos(a)*d[1]])+c
def pose(land=0,fleg=0,buck=0,kick=0,lift=0):
    img=skin(F,fleg,SH,w_front)
    img=skin(img,kick,HIP,w_hind)
    M1=np.array([[1,0,0],[0,1,-lift],[0,0,1.]])@rot(land,HOOF_H-PAD+PAD-PAD+0) if False else rot(land,HOOF_H)
    ff=fwd_pt(HOOF_F,fleg,SH)
    ffw=(M1@np.r_[ff+PAD,1])[:2]-PAD
    M=rot(buck,ffw)@M1
    M=np.array([[1,0,0],[0,1,-lift],[0,0,1.]])@M
    return cv2.warpAffine(img,M[:2],(img.shape[1],img.shape[0]),flags=cv2.INTER_LINEAR,borderValue=(1,1,1))
if __name__=='__main__':
    import sys
    cl=pad(clean,(200,200,200))
    P=[dict(),dict(fleg=30),dict(fleg=-30),dict(land=24,fleg=40),dict(land=24,fleg=-40),dict(land=24,fleg=40,buck=12,kick=40)]
    cv2.imwrite('fr/rig.jpg',np.hstack([cl*pose(**p) for p in P]).clip(0,255).astype(np.uint8)[::2,::2])
