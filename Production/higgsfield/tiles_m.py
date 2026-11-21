import sys, os
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
SRC,DM,Q=sys.argv[1],sys.argv[2],int(sys.argv[3])
n=len([f for f in os.listdir(SRC) if f.startswith('f')])
os.makedirs(DM,exist_ok=True)
for f in os.listdir(DM): os.remove(os.path.join(DM,f))
def mt(k):
    t=Image.new('RGB',(1920,1080))
    for j in range(4):
        i=(k-1)*4+j+1
        if i<=n: t.paste(Image.open(f'{SRC}/f{i:03d}.jpg').convert('RGB').resize((960,540),Image.LANCZOS),((j%2)*960,(j//2)*540))
    t.save(f'{DM}/t{k:03d}.webp',quality=Q,method=5)
if __name__=='__main__':
    nm=(n+3)//4
    with ProcessPoolExecutor(2) as ex: list(ex.map(mt,range(1,nm+1)))
    print(n,nm)
