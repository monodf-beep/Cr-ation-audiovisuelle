import cv2,numpy as np
im=cv2.imread('w/0003.png')
x0,y0,x1,y1=225,830,680,1225
roi=im[y0:y1,x0:x1]
g=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
ink=(g<150).astype(np.uint8)
# keep components connected to horse; drop text (1965 above y~?)
n,lab,st,_=cv2.connectedComponentsWithStats(cv2.dilate(ink,np.ones((9,9),np.uint8)))
big=np.argmax(st[1:,4])+1
reg=(lab==big)
# fill holes -> silhouette
cnts,_=cv2.findContours(reg.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
sil=np.zeros_like(ink);cv2.drawContours(sil,cnts,-1,1,-1)
cv2.imwrite('fr/sil.png',sil*255); cv2.imwrite('fr/roi.png',roi)
np.save('fr/sil.npy',sil)
print(st[big])
