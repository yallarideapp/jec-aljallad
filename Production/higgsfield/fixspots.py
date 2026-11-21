import cv2, numpy as np, os, subprocess, sys
K9=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(17,17))
def lobby_mask(img):
    L=cv2.cvtColor(img,cv2.COLOR_BGR2LAB)[:,:,0]
    bg=cv2.medianBlur(L,95)
    d=L.astype(np.int16)-bg.astype(np.int16)
    bw=((d>16)&(L>196)).astype(np.uint8); bw[640:]=0
    n,lab,st,cen=cv2.connectedComponentsWithStats(bw,8)
    m=np.zeros(L.shape,np.uint8); found=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if a<8 or a>5200 or max(w,h)>120 or max(w,h)/max(1,min(w,h))>4.6: continue
        if a/(w*h)<0.45: continue                       # ellipse fills ~0.78 of its box
        b=int(bg[int(cen[i][1]),int(cen[i][0])])
        if b<105 or b>232: continue
        # the surroundings must be plain ceiling: a ring around the blob with little texture
        x0,y0,x1,y1=max(0,x-14),max(0,y-12),min(1920,x+w+14),min(1080,y+h+12)
        ring=L[y0:y1,x0:x1].astype(np.float32); inner=np.zeros(ring.shape,bool); inner[max(0,y-6-y0):y+h+6-y0, max(0,x-6-x0):x+w+6-x0]=True
        if ring[~inner].size==0 or ring[~inner].std()>9.5: continue
        m[lab==i]=255; found.append((int(cen[i][0]),int(cen[i][1]),int(a)))
    return cv2.dilate(m,K9), found
def run_lobby(src='fxw2', dst='fxw2o', n=90):
    os.makedirs(dst,exist_ok=True)
    imgs=[cv2.imread(f'{src}/{k:04d}.jpg') for k in range(1,n+1)]
    ms=[]; log=[]
    for k,im in enumerate(imgs):
        m,f=lobby_mask(im)
        if k<26: m[:, :200]=0; m[:, 1750:]=0      # early frames: sun dapples on the stone piers at the frame edges are not lights
        ms.append(m); log.append(len(f))
    for k,im in enumerate(imgs):
        m=ms[k].copy()
        out=cv2.inpaint(im,m,7,cv2.INPAINT_TELEA) if m.any() else im
        # second look: anything a first pass left behind (halo of a big light)
        m2,f2=lobby_mask(out)
        if k<26: m2[:, :200]=0; m2[:, 1750:]=0
        if m2.any(): out=cv2.inpaint(out,cv2.dilate(m2,K9),7,cv2.INPAINT_TELEA)
        cv2.imwrite(f'{dst}/{k+1:04d}.jpg',out,[cv2.IMWRITE_JPEG_QUALITY,97])
    print('lobby spots per frame:',log)
def run_room(src='fx67', dst='fx67o', n=90, first=50, last=89):
    """locked camera: the two downlights left of the column exist only in frames ~58-88; paint them out so the count never drops"""
    os.makedirs(dst,exist_ok=True)
    m=np.zeros((1080,1920),np.uint8)
    for (cx,cy) in ((501,197),(564,279)): cv2.ellipse(m,(cx,cy),(30,19),0,0,360,255,-1)
    for k in range(1,n+1):
        im=cv2.imread(f'{src}/{k:04d}.jpg')
        if first<=k<=last: im=cv2.inpaint(im,m,8,cv2.INPAINT_TELEA)
        cv2.imwrite(f'{dst}/{k:04d}.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,97])
def enc(d, out):
    subprocess.check_call(['ffmpeg','-v','error','-y','-framerate','30','-i',d+'/%04d.jpg','-c:v','libx264','-preset','fast','-crf','10','-pix_fmt','yuv420p','-an',out])
def tail_blend(d, n, tail=9):
    """the model finishes some stages in a single-frame jump; turn the last frames into a short dissolve"""
    a=cv2.imread(f'{d}/{n-tail:04d}.jpg').astype(np.float32); b=cv2.imread(f'{d}/{n:04d}.jpg').astype(np.float32)
    for j in range(1,tail):
        t=j/tail; cv2.imwrite(f'{d}/{n-tail+j:04d}.jpg',(a*(1-t)+b*t).astype(np.uint8),[cv2.IMWRITE_JPEG_QUALITY,97])
def extract(clip, d):
    """frames of clips/<clip>.mp4 into d/0001.jpg ... (only if d is not there yet)"""
    if os.path.isdir(d) and os.listdir(d): return
    os.makedirs(d,exist_ok=True)
    subprocess.check_call(['ffmpeg','-v','error','-y','-i',f'clips/{clip}.mp4','-vsync','0','-q:v','1',f'{d}/%04d.jpg'])
if __name__=='__main__':
    if 'lobby' in sys.argv: extract('w2','fxw2')
    if 'room' in sys.argv: extract('i67','fx67')
    if 'lobby' in sys.argv: run_lobby(); enc('fxw2o','clips/w2f.mp4')
    if 'room' in sys.argv: run_room(); tail_blend('fx67o',90); enc('fx67o','clips/i67f.mp4')
    if 'i34' in sys.argv:
        os.makedirs('fx34',exist_ok=True); subprocess.check_call(['ffmpeg','-v','error','-y','-i','clips/i34.mp4','-vsync','0','-q:v','1','fx34/%04d.jpg'])
        tail_blend('fx34',90); enc('fx34','clips/i34t.mp4')
