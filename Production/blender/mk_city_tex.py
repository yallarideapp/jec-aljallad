# Procedural facade tiles for the background city. One tile = 2 bays x 2 storeys (8.0 x 6.4 m, 160 px/m), each window slightly different.
from PIL import Image, ImageFilter
import numpy as np, os, sys
OUT = sys.argv[1]
PX = 160; BW, FH = 4.0, 3.2
W, H = int(2*BW*PX), int(2*FH*PX)
FRAME = np.array((62,58,54))/255
def stone(seed, base):
    rng = np.random.default_rng(seed)
    n = rng.normal(0,1,(H//16,W//16))
    lo = np.asarray(Image.fromarray(np.uint8(np.clip(128+n*44,0,255))).resize((W,H),Image.BICUBIC).filter(ImageFilter.GaussianBlur(5)),float)/255-0.5
    fine = rng.normal(0,1,(H,W))*0.02
    col = np.zeros((H,W,3))
    for c in range(3): col[...,c] = base[c]/255*(1+lo*0.16+fine)
    hgt = np.full((H,W),0.8)
    ch = int(0.4*PX); cw = int(0.8*PX)
    for r,y in enumerate(range(0,H,ch)):
        off = (r%2)*(cw//2)
        for x in range(off-cw,W,cw):
            col[y+2:y+ch,max(0,x+2):max(0,x+cw)] *= 1+rng.normal(0,0.035)
        col[y:y+2] *= 0.82; hgt[y:y+2] = 0.5
        for x in range(off,W,cw):
            col[y:y+ch,x:x+2] *= 0.86; hgt[y:y+ch,x:x+2] = 0.5
    # weathering streaks from the top of every storey
    for k in range(2):
        y0 = k*int(FH*PX); g = np.linspace(0.90,1.0,int(0.9*PX))[:,None,None]
        col[y0:y0+int(0.9*PX)] *= g
    return col,hgt,rng
def rect(x0,y0,x1,y1):
    return int(x0*PX),int(x1*PX),H-int(y1*PX),H-int(y0*PX)
def window(col,hgt,msk,rng,x0,y0,x1,y1,mull=1,frame=0.06,sill=True,shutter=0.0,glass=(50,60,68),curtain=0.0,blind=0.0):
    X0,X1,Y0,Y1 = rect(x0,y0,x1,y1); f = max(3,int(frame*PX))
    col[max(0,Y0-6):Y1+6,max(0,X0-6):X1+6] *= 0.76
    if shutter>0:
        s=int(shutter*PX); col[Y0-s:Y0,X0:X1] = np.array((168,160,146))/255; hgt[Y0-s:Y0,X0:X1]=0.7
    col[Y0:Y1,X0:X1] = FRAME; hgt[Y0:Y1,X0:X1] = 0.2
    g = np.array(glass)/255*rng.uniform(0.8,1.25)
    gh, gw = Y1-Y0-2*f, X1-X0-2*f
    gy = np.linspace(1.4,0.7,gh)[:,None,None]; gx = (1+0.12*np.sin(np.linspace(0,3.1,gw)+rng.uniform(0,3)))[None,:,None]
    pane = g[None,None,:]*gy*gx
    if curtain>0:      # drawn curtains seen through the glass
        cwid = int(gw*curtain); cc = np.array((176,166,148))/255*rng.uniform(0.75,1.05)
        fold = (1+0.10*np.sin(np.arange(cwid)*0.55))[None,:,None]
        if rng.random()<0.5: pane[:, :cwid] = cc[None,None,:]*fold*np.linspace(1.0,0.8,gh)[:,None,None]
        else: pane[:, gw-cwid:] = cc[None,None,:]*fold*np.linspace(1.0,0.8,gh)[:,None,None]
    if blind>0:        # roller shutter partly down
        bh = int(gh*blind); pane[:bh] = (np.array((172,166,154))/255)[None,None,:]*(1-0.10*((np.arange(bh)//5)%2))[:,None,None]
    col[Y0+f:Y1-f,X0+f:X1-f] = pane
    msk[Y0+f:Y1-f,X0+f:X1-f] = 1
    if blind>0: msk[Y0+f:Y0+f+int(gh*blind),X0+f:X1-f] = 0
    for k in range(1,mull+1):
        xm = X0+(X1-X0)*k//(mull+1)
        col[Y0:Y1,xm-f//2:xm+f//2+1] = FRAME; msk[Y0:Y1,xm-f//2:xm+f//2+1] = 0
    if sill:
        s=int(0.07*PX); e=int(0.08*PX)
        col[Y1:Y1+s,max(0,X0-e):X1+e] = np.array((226,218,200))/255; hgt[Y1:Y1+s,max(0,X0-e):X1+e]=1.0
        col[Y1+s:Y1+s+5,max(0,X0-e):X1+e] *= 0.68
def ac_unit(col,hgt,x,y):
    X0,X1,Y0,Y1 = rect(x,y,x+0.85,y+0.6)
    col[Y0:Y1,X0:X1] = np.array((214,214,208))/255; hgt[Y0:Y1,X0:X1] = 1.0
    for yy in range(Y0+8,Y1-6,7): col[yy:yy+2,X0+8:X1-8] *= 0.7
    col[Y1:Y1+6,X0:X1] *= 0.6
def save(name,col,hgt,msk):
    Image.fromarray(np.uint8(np.clip(col,0,1)*255)).save(OUT+name+'_col.png')
    Image.fromarray(np.uint8(np.clip(hgt,0,1)*255)).filter(ImageFilter.GaussianBlur(0.8)).save(OUT+name+'_hgt.png')
    Image.fromarray(np.uint8(np.clip(msk,0,1)*255)).save(OUT+name+'_msk.png')
CELLS = [(0,0),(BW,0),(0,FH),(BW,FH)]
BASES = {'1':(206,192,164),'2':(188,172,142),'3':(222,214,196)}
VAR = [dict(curtain=0.0),dict(curtain=0.45),dict(blind=0.5),dict(curtain=0.3)]
for t,base in BASES.items():
    col,hgt,rng = stone(10+int(t),base); msk=np.zeros((H,W))
    for k,(ox,oy) in enumerate(CELLS):
        window(col,hgt,msk,rng,ox+1.0,oy+1.0,ox+3.0,oy+2.55,mull=1,shutter=0.18,**VAR[(k+int(t))%4])
    ac_unit(col,hgt,BW+3.05,0.28)
    save('facA'+t,col,hgt,msk)
    col,hgt,rng = stone(20+int(t),base); msk=np.zeros((H,W))
    for k,(ox,oy) in enumerate(CELLS):
        window(col,hgt,msk,rng,ox+0.45,oy+0.16,ox+3.55,oy+2.5,mull=2,sill=False,shutter=0.16,**VAR[(k+1+int(t))%4])
        X0,X1,Y0,Y1 = rect(ox,oy,ox+BW,oy+0.16); col[Y0:Y1,X0:X1] = np.array((214,206,188))/255; hgt[Y0:Y1,X0:X1]=1.0
        X0,X1,Y0,Y1 = rect(ox,oy+2.9,ox+BW,oy+FH); col[Y0:Y1,X0:X1] *= 0.6
        X0,X1,Y0,Y1 = rect(ox+0.15,oy+0.16,ox+3.85,oy+1.12)
        col[Y0:Y1,X0:X1] = col[Y0:Y1,X0:X1]*0.72+np.array((120,136,144))/255*0.28
        col[Y0:Y0+4,X0:X1] = FRAME
        for x in range(X0,X1,int(1.2*PX)): col[Y0:Y1,x:x+3] = FRAME
    save('facB'+t,col,hgt,msk)
col,hgt,rng = stone(31,BASES['1']); msk=np.zeros((H,W))
for k,(ox,oy) in enumerate(CELLS):
    window(col,hgt,msk,rng,ox+0.75,oy+0.75,ox+1.65,oy+2.6,mull=0,**VAR[k]); window(col,hgt,msk,rng,ox+2.35,oy+0.75,ox+3.25,oy+2.6,mull=0,**VAR[(k+2)%4])
save('facC1',col,hgt,msk)
col,hgt,rng = stone(41,(198,196,188)); msk=np.zeros((H,W))
for k,(ox,oy) in enumerate(CELLS):
    window(col,hgt,msk,rng,ox,oy+0.85,ox+BW,oy+2.95,mull=3,frame=0.05,sill=False,glass=(44,58,72),blind=(0.3 if k==1 else 0.0))
save('facD1',col,hgt,msk)
print(len(os.listdir(OUT)))
