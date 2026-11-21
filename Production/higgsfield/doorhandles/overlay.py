import os, cv2, numpy as np, sys, json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from kf import KF
SRC={'w1':'/tmp/e','w2':'/tmp/w2all'}
COL={'LHO':(0,0,255),'RH':(0,255,0),'LF':(255,0,255),'RF':(255,255,0)}
def interp(d,t):
    ks=sorted(d)
    if t<ks[0] or t>ks[-1]: return None
    out=[]
    for i in range(4):
        pts=[(k,d[k][i]) for k in ks if d[k][i] is not None]
        if len(pts)<2: out.append(None); continue
        xs,ys=zip(*pts)
        if t<xs[0] or t>xs[-1]: out.append(None); continue
        out.append(float(np.interp(t,xs,ys)))
    return out
if __name__=='__main__':
    clip=sys.argv[1]; ts=[int(a) for a in sys.argv[3:]]; tiles=[]
    for t in ts:
        f=cv2.imread(f'{SRC[clip]}/s{t:03d}.png')
        for k,d in KF[clip].items():
            r=interp(d,t)
            if r is None: continue
            x,w,y0,y1=r
            y0=y0 if y0 is not None else 300; y1=y1 if y1 is not None else 900
            cv2.rectangle(f,(int(x-w/2),int(y0)),(int(x+w/2),int(y1)),COL[k],2)
        cv2.putText(f,f'{clip} {t}',(20,50),0,1.5,(0,255,255),3)
        tiles.append(cv2.resize(f,(640,360)))
    while len(tiles)%3: tiles.append(np.zeros_like(tiles[0]))
    rows=[np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]
    cv2.imwrite(sys.argv[2],np.vstack(rows),[cv2.IMWRITE_JPEG_QUALITY,85])
