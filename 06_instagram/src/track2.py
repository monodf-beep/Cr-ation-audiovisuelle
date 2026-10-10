import cv2,numpy as np,glob,json
fs=sorted(glob.glob('w/*.png'))
s=0.5
S=np.diag([s,s,1.])
def ld(f): return cv2.GaussianBlur(cv2.resize(cv2.imread(f,0),None,fx=s,fy=s),(0,0),1.5).astype(np.float32)
ref=ld(fs[3])
tm=np.zeros(ref.shape,np.uint8); tm[int(680*s):int(1500*s),int(60*s):int(1000*s)]=255  # logo+text area in ref
H=np.eye(3,dtype=np.float32);out={}
order=list(range(3,len(fs)))+list(range(2,-1,-1))
for i in order:
    if i==2: H=np.eye(3,dtype=np.float32)
    g=ld(fs[i]);ok=True
    try:
        cc,Hn=cv2.findTransformECC(ref,g,H.copy(),cv2.MOTION_HOMOGRAPHY,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,200,1e-5),tm,5)
    except cv2.error: ok=False;cc=0
    if ok and cc>0.6: H=Hn
    else: ok=False
    Hf=np.linalg.inv(S)@H@S
    out[i]=Hf.tolist()
    print(i,round(float(cc),3),ok,flush=True)
    if i>3 and cc<0.3 and i>95: break
json.dump(out,open('H.json','w'))
