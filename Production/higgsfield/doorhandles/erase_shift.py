import cv2, numpy as np
def erase(img, x0, x1, y0, y1, mx, my):
    """fill the box with the same-size strip just to its right (what is behind the glass there), matched in
    brightness to the rows just above and below the box"""
    H,W=img.shape[:2]; f=img.astype(np.float32)
    a=int(max(0,np.floor(x0-mx))); b=int(min(W-1,np.ceil(x1+mx))); c=int(max(0,np.floor(y0-my))); d=int(min(H-1,np.ceil(y1+my)))
    n=b-a+1; src=f[c:d+1,b+2:b+2+n]
    if src.shape[1]<n: src=np.pad(src,((0,0),(0,n-src.shape[1]),(0,0)),mode='edge')
    src=src[:,::-1]                                    # mirrored, so its edge meets the box's right edge
    k=4; v=np.linspace(0,1,d-c+1)[:,None,None]
    top=f[max(0,c-k):c,a:b+1].mean(0)-f[max(0,c-k):c,b+2:b+2+n][:,::-1].mean(0) if c>=k else 0
    bot=f[d+1:d+1+k,a:b+1].mean(0)-f[d+1:d+1+k,b+2:b+2+n][:,::-1].mean(0) if d+1+k<=H else 0
    top=np.asarray(top); bot=np.asarray(bot)
    if top.ndim==2: top=cv2.GaussianBlur(top.reshape(1,-1,3),(9,1),0).reshape(-1,3)
    if bot.ndim==2: bot=cv2.GaussianBlur(bot.reshape(1,-1,3),(9,1),0).reshape(-1,3)
    fill=src+(top*(1-v) if np.ndim(top) else 0)+(bot*v if np.ndim(bot) else 0)
    out=f.copy(); out[c:d+1,a:b+1]=fill
    m=np.zeros((H,W),np.float32); m[c:d+1,a:b+1]=1; m=cv2.GaussianBlur(m,(0,0),1.0); m[c+1:d,a+1:b]=1
    return np.clip(f*(1-m[...,None])+out*m[...,None],0,255).astype(np.uint8)
