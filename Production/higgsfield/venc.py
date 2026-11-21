import subprocess, sys, os, json, numpy as np
from PIL import Image
import os as _os
OUT=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'..','..','Source')+'/'   # writes into Source/v and Source/vi
OUT=_os.environ.get('JEC_FILM_OUT',OUT)
# quality first: no denoise, CRF 20, and P-frames kept close to I-frame quality (a scrubbed film rests on any frame, not only on keyframes)
X264=['-c:v','libx264','-preset','medium','-crf','20','-g','6','-keyint_min','6','-sc_threshold','0','-bf','0','-refs','2','-x264-params','ipratio=1.1:aq-mode=3','-pix_fmt','yuv420p','-movflags','+faststart','-an']
DN='null'
def nb(p): return int(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames','-of','csv=p=0',p]).decode().strip())
def enc_clip(src, dst, a=None, b=None):
    vf=DN if a is None else f'trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS'
    subprocess.check_call(['ffmpeg','-v','error','-y','-i',src,'-vf',vf,'-r','30']+X264+[dst])
def enc_seq(pattern, dst, dn=True):
    subprocess.check_call(['ffmpeg','-v','error','-y','-framerate','30','-i',pattern]+(['-vf',DN] if dn else [])+['-r','30']+X264+[dst])
def poster(src, dst):
    subprocess.check_call(['ffmpeg','-v','error','-y','-i',src,'-frames:v','1','-q:v','1',f'/tmp/p{os.getpid()}.png'])
    Image.open(f'/tmp/p{os.getpid()}.png').convert('RGB').save(dst,quality=80,method=6)
def frames(src, d):
    os.makedirs(d,exist_ok=True)
    for f in os.listdir(d): os.remove(os.path.join(d,f))
    subprocess.check_call(['ffmpeg','-v','error','-y','-i',src,'-vsync','0','-q:v','1',d+'/%04d.jpg'])
    return sorted(os.listdir(d))
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
def whoosh(a_clip, b_clip, dst, n=18):
    d='venc/whoosh'; os.makedirs(d,exist_ok=True)
    for f in os.listdir(d): os.remove(os.path.join(d,f))
    subprocess.check_call(['ffmpeg','-v','error','-y','-sseof','-0.05','-i',a_clip,'-update','1','-q:v','1','/tmp/wa.png'])
    subprocess.check_call(['ffmpeg','-v','error','-y','-i',b_clip,'-frames:v','1','-q:v','1','/tmp/wb.png'])
    A=np.asarray(Image.open('/tmp/wa.png').convert('RGB'),dtype=np.float32); B=np.asarray(Image.open('/tmp/wb.png').convert('RGB'),dtype=np.float32); W=A.shape[1]
    for t in range(1,n+1):
        al=t/(n+1); s=al*al*(3-2*al); L=420*np.sin(np.pi*al)
        a=shift(hblur(A,L),-s*W*0.42); b=shift(hblur(B,L),(1-s)*W*0.42); m=np.clip((s-0.25)/0.5,0,1)
        Image.fromarray(np.clip(a*(1-m)+b*m,0,255).astype(np.uint8)).save(f'{d}/{t:04d}.jpg',quality=95)
    enc_seq(d+'/%04d.jpg', dst, dn=False)
def blend_tail(src, dst, tail=9):
    d='venc/tail'; fs=frames(src,d); n=len(fs)
    a=Image.open(f'{d}/{fs[n-tail-1]}').convert('RGB'); b=Image.open(f'{d}/{fs[n-1]}').convert('RGB')
    for j in range(tail-1):
        Image.blend(a,b,(j+1)/tail).save(f'{d}/{fs[n-tail+j]}',quality=95)
    enc_seq(d+'/%04d.jpg', dst)
if __name__=='__main__':
    job=json.loads(sys.argv[1])   # [[kind, out, src, ...], ...]
    res={}
    for it in job:
        kind,out,src=it[0],it[1],it[2]
        dst=OUT+out+'.mp4'
        if kind=='clip': enc_clip('clips/'+src+'.mp4',dst)
        elif kind=='part': enc_clip('clips/'+src+'.mp4',dst,it[3],it[4])
        elif kind=='tail': blend_tail('clips/'+src+'.mp4',dst)
        elif kind=='whoosh': whoosh('clips/'+src+'.mp4','clips/'+it[3]+'.mp4',dst)
        poster(dst, OUT+out+'.webp')
        res[out]=[nb(dst), round(os.path.getsize(dst)/2**20,1)]
        print(out,res[out],flush=True)
