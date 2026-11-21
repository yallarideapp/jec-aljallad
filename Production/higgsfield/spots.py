import cv2, numpy as np, sys
def ceil_mask():
    m=np.zeros((1080,1920),np.uint8)
    poly=np.array([[190,0],[1920,0],[1920,110],[1818,152],[1818,172],[1660,186],[1660,206],[1232,368],[584,368]],np.int32)
    cv2.fillPoly(m,[poly],255)
    m[60:400,598:780]=0                      # column
    return cv2.erode(m,np.ones((9,9),np.uint8))
def blobs(img, m, tb=22, td=14):
    L=cv2.cvtColor(img,cv2.COLOR_BGR2LAB)[:,:,0].astype(np.int16)
    bg=cv2.medianBlur(L.astype(np.uint8),45).astype(np.int16)
    out=[]
    for pol,th in (('b',tb),('d',td)):
        d=(L-bg) if pol=='b' else (bg-L)
        bw=((d>th)&(m>0)).astype(np.uint8)
        n,lab,st,cen=cv2.connectedComponentsWithStats(bw,8)
        for i in range(1,n):
            x,y,w,h,a=st[i]
            if a<10 or a>2500 or max(w,h)>70 or max(w,h)/max(1,min(w,h))>3.5: continue
            out.append((pol,int(cen[i][0]),int(cen[i][1]),int(a),int(w),int(h)))
    return out
if __name__=='__main__':
    m=ceil_mask()
    for f in sys.argv[1:]:
        img=cv2.imread(f'fx67/{int(f):04d}.jpg'); bl=blobs(img,m)
        print(f, [(p,x,y,a) for p,x,y,a,w,h in bl])
        vis=img.copy(); vis[m==0]=(vis[m==0]*0.45).astype(np.uint8)
        for p,x,y,a,w,h in bl: cv2.circle(vis,(x,y),22,(0,0,255) if p=='b' else (255,0,0),2)
        cv2.imwrite(f'/tmp/sp/v{f}.jpg',vis[:420],[cv2.IMWRITE_JPEG_QUALITY,85])
