import cv2, json, sys
v = cv2.VideoCapture(sys.argv[1]); pts=[]; tpl=None; i=0
while True:
    ok, f = v.read()
    if not ok: break
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    if tpl is None:
        cx, cy = 427, 665; tpl = g[cy-90:cy+90, cx-90:cx+90].copy(); pts.append((cx,cy))
    else:
        px, py = pts[-1]
        x0, y0 = max(px-200,0), max(py-200,0)
        zone = g[y0:py+200, x0:px+200]
        r = cv2.matchTemplate(zone, tpl, cv2.TM_CCOEFF_NORMED)
        _, sc, _, loc = cv2.minMaxLoc(r)
        pts.append((x0+loc[0]+90, y0+loc[1]+90))
    i+=1
print(g.shape, len(pts), pts[0], pts[len(pts)//2], pts[-1])
json.dump(pts, open(sys.argv[2],'w'))
