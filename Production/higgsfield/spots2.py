import cv2, numpy as np, sys
def cand(img):
    """leftover downlights: small bright blobs sitting on plain ceiling colour, even right next to the bronze door frame"""
    lab=cv2.cvtColor(img,cv2.COLOR_BGR2LAB); L=lab[:,:,0]
    op=cv2.morphologyEx(L,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(61,31)))
    d=L.astype(np.int16)-op.astype(np.int16)
    bw=((d>12)&(L>188)).astype(np.uint8); bw[600:]=0
    n,cc,st,cen=cv2.connectedComponentsWithStats(bw,8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if a<6 or a>2600 or w>110 or h>60: continue
        if h>w*1.25: continue                      # vertical glints on the frame
        if a/(w*h)<0.5: continue
        # ceiling test: most of a band around the blob is warm, mid-bright, untextured plaster
        x0,y0,x1,y1=max(0,x-18),max(0,y-14),min(1920,x+w+18),min(1080,y+h+14)
        patch=lab[y0:y1,x0:x1].astype(np.int16); inner=np.zeros(patch.shape[:2],bool)
        inner[max(0,y-4-y0):y+h+4-y0, max(0,x-4-x0):x+w+4-x0]=True
        ring=patch[~inner]
        if ring.size==0: continue
        Lr=ring[:,0]; ok=(Lr>120)&(Lr<215)&(ring[:,1]>128)&(ring[:,2]>134)
        frac=ok.mean(); med=np.median(Lr[ok]) if ok.any() else 0
        sd=Lr[ok].std() if ok.sum()>20 else 99
        out.append(dict(i=i,c=(int(cen[i][0]),int(cen[i][1])),wh=(int(w),int(h)),a=int(a),frac=round(float(frac),2),med=int(med),sd=round(float(sd),1),peak=int(L[cc==i].max())))
    return out,cc
if __name__=='__main__':
    d=sys.argv[1]
    for k in range(int(sys.argv[2]),int(sys.argv[3])+1,int(sys.argv[4])):
        im=cv2.imread(f'{d}/{k:04d}.jpg'); o,_=cand(im)
        print(k,[ (b['c'],b['wh'],b['a'],b['frac'],b['sd'],b['peak']) for b in o])
