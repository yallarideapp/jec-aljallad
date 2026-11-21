import os, cv2, numpy as np, json, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from kf import KF; from overlay import interp, SRC
H,W=1080,1920
def V_of(f): return cv2.GaussianBlur(f.max(2).astype(np.float32),(0,0),0.8)
def xsnap(V,x,w,y0,y1,S):
    L=y1-y0; ra=int(np.clip(y0+0.25*L,0,H-2)); rb=int(np.clip(y1-0.25*L,ra+2,H))
    wi=max(3,int(round(w))); xa=int(np.clip(x-w/2-S,0,W-wi-1)); xb=int(np.clip(x+w/2+S,xa+wi+1,W))
    P=V[ra:rb,xa:xb].mean(0); c=np.convolve(P,np.ones(wi)/wi,'valid'); i=int(np.argmin(c))
    # sub-pixel edges: strongest falling / rising gradient near the window edges
    g=np.diff(P); l0=max(0,i-2); l1=min(len(g),i+3); r0=max(0,i+wi-3); r1=min(len(g),i+wi+2)
    le=l0+int(np.argmin(g[l0:l1]))+0.5 if l1>l0 else i; re=r0+int(np.argmax(g[r0:r1]))+0.5 if r1>r0 else i+wi
    if re-le<0.6*wi or re-le>1.5*wi: le,re=i,i+wi
    return xa+le, xa+re
def yends(V,x0,x1,y0,y1,S):
    """ends of a dark vertical bar: where the inside stops being darker than both sides"""
    a,b=int(round(x0))+1,int(round(x1))-1
    if b<=a: b=a+1
    ins=V[:,a:b].mean(1); lo=V[:,max(0,a-10):max(1,a-4)].mean(1); hi=V[:,min(W-2,b+4):min(W-1,b+10)].mean(1)
    d=np.minimum(lo,hi)-ins; d=cv2.GaussianBlur(d.reshape(-1,1),(1,0),1.5).ravel()
    L=y1-y0; mid=d[int(y0+0.3*L):int(y1-0.3*L)]
    lvl=np.median(mid) if len(mid) else 20
    thr=0.5*lvl
    out=[]
    for e,sgn in ((y0,-1),(y1,1)):
        ya,yb=int(np.clip(e-S,0,H-1)),int(np.clip(e+S,1,H))
        seg=d[ya:yb]
        if len(seg)<3 or lvl<8: out.append(e); continue
        # last row (moving outward) still above threshold
        if sgn<0:
            idx=np.where(seg>thr)[0]; out.append(float(ya+idx[0]) if len(idx) else e)
        else:
            idx=np.where(seg>thr)[0]; out.append(float(ya+idx[-1]) if len(idx) else e)
    return out[0],out[1],lvl
res={}
for clip,objs in KF.items():
    rng=range(86,150) if clip=='w1' else range(0,65)
    res[clip]={}
    for t in rng:
        f=cv2.imread(f'{SRC[clip]}/s{t:03d}.png'); V=V_of(f); rec={}
        for k,d in objs.items():
            r=interp(d,t)
            if r is None: continue
            x,w,y0,y1=r
            yy0=y0 if y0 is not None else 400; yy1=y1 if y1 is not None else 800
            if k in ('LF','RF') and clip=='w2' and t>=44: yy0,yy1=200,1000
            S=max(4,0.35*w)
            x0,x1=xsnap(V,x,w,yy0,yy1,S)
            if abs((x0+x1)/2-x)>S: x0,x1=x-w/2,x+w/2
            if y0 is not None:
                e0,e1,lvl=yends(V,x0,x1,y0,y1,S=max(8,0.05*(y1-y0)))
            else: e0,e1,lvl=None,None,0
            rec[k]=[round(float(x0),1),round(float(x1),1),None if e0 is None else round(e0,1),None if e1 is None else round(e1,1),round(float(lvl),1)]
        res[clip][t]=rec
json.dump(res,open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snap.json'),'w'))
for clip in res:
    for t in sorted(res[clip]):
        if t%3==0:
            print(clip,t,' '.join(f"{k}:{v[0]:.0f}-{v[1]:.0f} y{v[2]}-{v[3]}" for k,v in res[clip][t].items()))
