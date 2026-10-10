import cv2,numpy as np
roi=cv2.imread('fr/roi.png').astype(np.float32)
sil=np.load('fr/sil.npy').astype(np.uint8)
H,W=sil.shape
PAD=150
def pad(a,v): return cv2.copyMakeBorder(a,PAD,PAD,PAD,PAD,cv2.BORDER_CONSTANT,value=v)
clean=cv2.inpaint(roi.astype(np.uint8),cv2.dilate(sil,np.ones((7,7),np.uint8)),9,cv2.INPAINT_TELEA).astype(np.float32)
clean=cv2.GaussianBlur(clean,(0,0),3)*0+cv2.blur(clean,(25,25))
F=np.clip(roi/np.maximum(clean,1),0,1)
F[sil==0]=1
F=pad(F,(1,1,1)); S=pad(sil.astype(np.float32),0)
yy,xx=np.mgrid[0:S.shape[0],0:S.shape[1]]
HIP=np.array([345,205])+PAD
legs=((yy-PAD>215)&(xx-PAD>300)).astype(np.float32)
legs=cv2.GaussianBlur(legs,(0,0),4)
HOOF_H=np.array([405,365.])+PAD
HOOF_F=np.array([25,135.])+PAD
def rot(ang,c):
    return np.vstack([cv2.getRotationMatrix2D((float(c[0]),float(c[1])),ang,1),[0,0,1]])
def pose(land,buck,kick):
    """land: deg ccw about hind hooves; buck: deg cw about (moved) front hooves; kick: hind legs deg about hip"""
    M1=np.array([[1,0,land*0.6],[0,1,-land*1.7],[0,0,1.]])@rot(land,HOOF_H)
    ff=(M1@np.r_[HOOF_F,1])[:2]
    M=rot(buck,ff)@M1
    K=rot(kick,HIP)
    def warp(img,A,bv):
        return cv2.warpAffine(img,A[:2],(img.shape[1],img.shape[0]),flags=cv2.INTER_LINEAR,borderValue=bv)
    Fk=F
    if kick:
        # smooth skinning: rotation weight grows from hip down/right
        d=np.clip(((yy-HIP[1])*0.8+(xx-HIP[0])*0.6+10)/70,0,1)
        d=d*d*(3-2*d)
        a=np.deg2rad(kick)*d  # display ccw = math with y down: x'=c*x+s*y
        px=xx-HIP[0]; py=yy-HIP[1]
        c=np.cos(a); sn=np.sin(a)
        mx=(c*px - sn*py)+HIP[0]; my=(sn*px + c*py)+HIP[1]
        Fk=cv2.remap(F,mx.astype(np.float32),my.astype(np.float32),cv2.INTER_LINEAR,borderValue=(1,1,1))
    out=warp(Fk,M,(1,1,1))
    return out  # multiplicative factor map in padded ref coords
if __name__=='__main__':
    rows=[]
    for p in [(26,0,0),(26,8,25),(26,14,45),(26,14,60),(26,6,15)]:
        rows.append((clean_p:=pad(clean,(200,200,200)))*pose(*p))
    cv2.imwrite('fr/poses.jpg',np.hstack(rows).clip(0,255).astype(np.uint8)[::2,::2])
