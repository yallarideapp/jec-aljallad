import cv2, numpy as np
import erase6, erase5
def score(img, out, x0, x1, y0, y1, mx, my):
    """how much of a dark vertical bar is left where the handle was: column darkness against the strip to its right"""
    a=int(max(0,np.floor(x0-mx))); b=int(min(img.shape[1]-1,np.ceil(x1+mx))); c=int(max(0,np.floor(y0-my))); d=int(min(img.shape[0]-1,np.ceil(y1+my)))
    V=out.max(2).astype(np.float32)
    inside=V[c+(d-c)//6:d-(d-c)//6,a:b+1].mean(0)
    ref=V[c+(d-c)//6:d-(d-c)//6,b+2:b+10].mean()
    return float(np.clip(ref-inside,0,None).mean()+0.5*np.abs(np.diff(inside)).mean())
def erase(img, x0, x1, y0, y1, mx, my):
    A=erase5.erase(img,x0,x1,y0,y1,mx,my); B=erase6.erase(img,x0,x1,y0,y1,mx,my)
    sa=score(img,A,x0,x1,y0,y1,mx,my); sb=score(img,B,x0,x1,y0,y1,mx,my)
    return (A if sa<=sb else B)
