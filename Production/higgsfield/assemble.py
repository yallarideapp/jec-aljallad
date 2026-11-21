import sys, os, subprocess, json, numpy as np
from PIL import Image
OUT=sys.argv[1]; plan=json.loads(sys.argv[2])   # [[clip, nframes_out, drop_first], ...] or ["whoosh", n]
os.makedirs(OUT,exist_ok=True)
def nb(p): return int(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames','-of','csv=p=0',p]).decode().strip())
def grab(p, idxs, tag):
    d=f'work/{tag}'; os.makedirs(d,exist_ok=True)
    sel='+'.join(f'eq(n\\,{i})' for i in idxs)
    subprocess.check_call(['ffmpeg','-v','error','-y','-i',p,'-vf',f"select='{sel}',hqdn3d=1.2:1.2:3:3",'-vsync','0','-q:v','2',f'{d}/%03d.jpg'])
    return [f'{d}/{k+1:03d}.jpg' for k in range(len(idxs))]
def hblur(a, L):
    if L<2: return a
    k=int(L)|1; pad=k//2
    ap=np.pad(a,((0,0),(pad,pad),(0,0)),mode='edge').astype(np.float32)
    c=np.cumsum(ap,axis=1); c=np.concatenate([np.zeros_like(c[:,:1]),c],axis=1)
    return (c[:,k:]-c[:,:-k])/k
def shift(a, dx):
    dx=int(dx); W=a.shape[1]
    if dx==0: return a
    out=np.empty_like(a)
    if dx<0: out[:,:W+dx]=a[:,-dx:]; out[:,W+dx:]=a[:,-1:]
    else: out[:,dx:]=a[:,:W-dx]; out[:,:dx]=a[:,:1]
    return out
seq=[]; seg=[]; pend=None
for item in plan:
    if item[0]=='whoosh': pend=item[1]; continue
    clip,n,drop=item; p=f'clips/{clip}.mp4'; N=nb(p)
    idxs=[int(round(x)) for x in np.linspace(0,N-1,n)]
    if drop: idxs=idxs[1:]
    fr=grab(p,idxs,clip)
    if pend:
        A=np.asarray(Image.open(seq[-1]).convert('RGB'),dtype=np.float32); B=np.asarray(Image.open(fr[0]).convert('RGB'),dtype=np.float32); W=A.shape[1]
        d='work/whoosh'; os.makedirs(d,exist_ok=True)
        for t in range(1,pend+1):
            al=t/(pend+1); s=al*al*(3-2*al); L=420*np.sin(np.pi*al)
            a=shift(hblur(A,L),-s*W*0.42); b=shift(hblur(B,L),(1-s)*W*0.42)
            m=np.clip((s-0.25)/0.5,0,1)
            out=np.clip(a*(1-m)+b*m,0,255).astype(np.uint8); fn=f'{d}/{len(seg)}_{t:02d}.jpg'; Image.fromarray(out).save(fn,quality=92); seq.append(fn)
        seg.append(len(seq)); pend=None
    seq+=fr; seg.append(len(seq))
if len(seq)%2: seq.append(seq[-1]); seg[-1]=len(seq)
for i,f in enumerate(seq,1):
    dst=f'{OUT}/f{i:03d}.jpg'
    if os.path.lexists(dst): os.remove(dst)
    os.symlink(os.path.abspath(f),dst)
print(json.dumps({'total':len(seq),'seg':seg}))
