import cv2, numpy as np, os, subprocess, sys
from spots2 import cand
K=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(33,25))
def picks(img,k):
    o,cc=cand(img); keep=[]
    for b in o:
        (cx,cy),(w,h)=b['c'],b['wh']
        top = cy<=14 and k>=40                       # a light half out of the top of the picture
        if not (300<=cx<=1620 and cy<=372): continue
        if not top and not (430<=cx<=1480): continue
        big = 9<=w<=42 and 2<=h<=(20 if top else 16) and w>=1.2*h
        tiny = 5<=w<9 and h<=7 and b['sd']<=6 and b['peak']>=250          # a light almost hidden behind the door leaf
        if not (big or tiny): continue
        if b['peak']<(240 if top else 247) or b['frac']<0.5 or b['sd']>18: continue
        keep.append(b)
    return keep,cc
def fill(im, blob):
    """paint the light out with the plaster colour around it; never drag the dark door frame into the patch"""
    H,W=im.shape[:2]; lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.int16)
    n,cc=cv2.connectedComponents(cv2.dilate(blob,K)); out=im.copy()
    near=cv2.dilate(blob,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,11)))>0     # the thin dark trim ring hugging the light
    for i in range(1,n):
        ys,xs=np.where(cc==i); y0,y1=max(0,ys.min()-30),min(H,ys.max()+31); x0,x1=max(0,xs.min()-36),min(W,xs.max()+37)
        sub=out[y0:y1,x0:x1]; sl=lab[y0:y1,x0:x1]; sm=(cc[y0:y1,x0:x1]==i)
        ceil=(sl[...,0]>120)&(sl[...,0]<215)&(sl[...,1]>128)&(sl[...,2]>134)&~sm
        if ceil.sum()<30: continue
        Lc=np.median(sl[...,0][ceil]); ceil&=np.abs(sl[...,0]-Lc)<14
        col=np.median(sub[ceil],axis=0)
        tmp=sub.copy(); tmp[~ceil & ~sm]=col
        tmp=cv2.inpaint(tmp,sm.astype(np.uint8)*255,5,cv2.INPAINT_TELEA)
        put=sm&((sl[...,0]>Lc-30)|(near[y0:y1,x0:x1]&(sl[...,0]>Lc-80)))
        ac,bc=np.median(sl[...,1][ceil]),np.median(sl[...,2][ceil])
        put&=~((sl[...,2]>bc+9)|(sl[...,1]>ac+7))                    # lit bronze is more orange than plaster: leave it
        nd,dc,ds,_=cv2.connectedComponentsWithStats((sm&~put).astype(np.uint8),8)      # stray dark crumbs of the trim ring
        for j in range(1,nd):
            if ds[j,4]<30: put|=(dc==j)
        a=(cv2.GaussianBlur(put.astype(np.float32),(0,0),1.5)*put)[...,None]
        a=np.where(sl[...,0:1]>Lc+8,1.0,a)*put[...,None]            # the light itself goes completely
        out[y0:y1,x0:x1]=(sub*(1-a)+tmp*a).astype(np.uint8)
    return out
if __name__=='__main__':
    src,dst=sys.argv[1],sys.argv[2]; os.makedirs(dst,exist_ok=True); log={}
    for k in range(1,91):
        im=cv2.imread(f'{src}/{k:04d}.jpg')
        for rep in range(2):
            kp,cc=picks(im,k)
            if not kp: break
            m=np.zeros(im.shape[:2],np.uint8)
            for b in kp: m[cc==b['i']]=255
            im=fill(im,m); log.setdefault(k,[]).append([(b['c'],b['wh']) for b in kp])
        cv2.imwrite(f'{dst}/{k:04d}.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,97])
    for k in sorted(log): print(k,log[k])
