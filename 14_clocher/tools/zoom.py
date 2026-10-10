import cv2, json, sys, subprocess, numpy as np
src, suivi, out = sys.argv[1:4]
p = np.array(json.load(open(suivi)), float)
k = 9; pad = np.pad(p, ((k,k),(0,0)), mode='edge')
lisse = np.array([pad[i:i+2*k+1].mean(0) for i in range(len(p))])
W, H, fps = 1080, 1920, 30
fin_zoom, larg_min = 2.2, 400
v = cv2.VideoCapture(src)
ff = subprocess.Popen(['ffmpeg','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(fps),'-i','-',
  '-i',src,'-map','0:v','-map','1:a?','-shortest','-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p','-c:a','aac',out], stdin=subprocess.PIPE)
i = 0
while True:
    ok, f = v.read()
    if not ok: break
    t = i/fps; a = min(t/fin_zoom, 1); a = a*a*(3-2*a)
    cw = W + (larg_min-W)*a; ch = cw*H/W
    cx = W/2 + (lisse[i][0]-W/2)*a; cy = H/2 + (lisse[i][1]-H/2)*a
    x0 = min(max(cx-cw/2,0),W-cw); y0 = min(max(cy-ch/2,0),H-ch)
    M = np.float32([[W/cw,0,-x0*W/cw],[0,H/ch,-y0*H/ch]])
    ff.stdin.write(cv2.warpAffine(f, M, (W,H), flags=cv2.INTER_LANCZOS4).tobytes()); i += 1
ff.stdin.close(); ff.wait()
