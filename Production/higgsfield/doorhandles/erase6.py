import cv2, numpy as np
def erase(img, x0, x1, y0, y1, mx, my):
    """remove a vertical bar: brightness by frequency-selective reconstruction, colour carried straight across
    from the two sides (row by row, smoothed), so no colour of its own is invented"""
    H,W=img.shape[:2]; bw=x1-x0
    a=int(max(0,np.floor(x0-mx))); b=int(min(W,np.ceil(x1+mx)+1)); c=int(max(0,np.floor(y0-my))); d=int(min(H,np.ceil(y1+my)+1))
    cx0=int(max(0,a-max(80,3*bw))); cx1=int(min(W,b+max(80,3*bw))); cy0=int(max(0,c-80)); cy1=int(min(H,d+80))
    crop=img[cy0:cy1,cx0:cx1]
    hole=np.zeros(crop.shape[:2],np.uint8); la,lb,lc,ld=a-cx0,b-cx0,c-cy0,d-cy0; hole[lc:ld,la:lb]=255
    ycc=cv2.cvtColor(crop,cv2.COLOR_BGR2YCrCb); Y=ycc[...,0]
    # the door stile (dark bronze) stands just left of this handle: it must not feed the fill
    E=int(max(10,0.6*bw)); inv=hole.copy(); inv[lc:ld,max(0,la-E):la]=255
    Yf=np.zeros_like(Y); cv2.xphoto.inpaint(Y,255-inv,Yf,cv2.xphoto.INPAINT_FSR_FAST)
    C=ycc[...,1:].astype(np.float32); n=lb-la
    def side(xa,xb):
        xa,xb=max(0,xa),min(C.shape[1],xb)
        return None if xb-xa<1 else C[lc:ld,xa:xb].mean(1)
    L=side(lb,lb+4); R=side(lb,lb+4)
    if L is None: L=R
    if R is None: R=L
    L=cv2.GaussianBlur(L.reshape(-1,1,2),(1,0),4).reshape(-1,2); R=cv2.GaussianBlur(R.reshape(-1,1,2),(1,0),4).reshape(-1,2)
    u=np.linspace(0,1,n)[None,:,None]
    C2=C.copy(); C2[lc:ld,la:lb]=L[:,None,:]*(1-u)+R[:,None,:]*u
    fill=cv2.cvtColor(np.dstack([Yf,np.clip(C2,0,255).astype(np.uint8)]),cv2.COLOR_YCrCb2BGR)
    m=cv2.GaussianBlur(hole.astype(np.float32)/255,(0,0),1.0); m=np.maximum(m,cv2.erode(hole,np.ones((3,3),np.uint8)).astype(np.float32)/255)[...,None]
    out=img.copy(); out[cy0:cy1,cx0:cx1]=np.clip(crop*(1-m)+fill*m,0,255).astype(np.uint8)
    return out
