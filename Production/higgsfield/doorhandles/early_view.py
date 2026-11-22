"""Look at the work on frames 73-99 of the walk: `python3 early_view.py erase out.jpg 80 85 90` (each frame as it was and with
the old handle removed), or `occ` instead of `erase` (the tree in front of the new handle, tinted; the handle's place boxed)."""
import cv2, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import early
def view(ts, name, box=(740,880,480,715), fx=3.0, mode='erase'):
    x0,x1,y0,y1=box; r=[]
    for t in ts:
        o=cv2.imread(f'/tmp/e/s{t:03d}.png')
        if mode=='erase':
            c=early.erase(o,t)
            tiles=[o[y0:y1,x0:x1], c[y0:y1,x0:x1]]
        else:
            g=early.geo(t); occ=early.occlusion(o,t); m=g['m']; rx0,rx1,ry0,ry1=g['RH']
            ov=o.astype(np.float32).copy(); ov[...,2]=np.clip(ov[...,2]+occ*90,0,255); ov[...,0]*= (1-0.5*occ)
            ov=ov.astype(np.uint8)
            tiles=[ov[y0:y1,x0:x1]]
        row=[]
        for k,im in enumerate(tiles):
            im=cv2.resize(im,None,fx=fx,fy=fx,interpolation=cv2.INTER_CUBIC)
            if mode!='erase':
                p=lambda x,y:(int((x-x0)*fx),int((y-y0)*fx))
                cv2.rectangle(im,p(2*m-rx1,ry0),p(2*m-rx0,ry1),(0,255,255),1)
            cv2.putText(im,f'{t}',(6,22),0,0.7,(0,255,255),2); row.append(np.pad(im,((0,0),(0,3),(0,0)),constant_values=255))
        r.append(np.pad(np.hstack(row),((0,4),(0,6),(0,0)),constant_values=255))
    cols=len(r) if mode=='erase' and len(r)<=3 else (3 if mode=='erase' else 6)
    while len(r)%cols: r.append(np.full_like(r[0],255))
    cv2.imwrite(name,np.vstack([np.hstack(r[i:i+cols]) for i in range(0,len(r),cols)]),[cv2.IMWRITE_JPEG_QUALITY,90])
if __name__=='__main__':
    mode=sys.argv[1]; ts=[int(a) for a in sys.argv[3:]]
    view(ts, sys.argv[2], mode=mode)
