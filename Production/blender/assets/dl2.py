import json, os, urllib.request, concurrent.futures as cf
op=urllib.request.build_opener(); op.addheaders=[("User-Agent","JEC-POC/1.0")]; urllib.request.install_opener(op)
TEX=['excavated_soil_wall','brown_mud_dry','dry_ground_rocks','asphalt_02','precast_stone_paving','white_sandstone_blocks_02','large_sandstone_blocks_01','rough_block_wall','concrete_wall_003','concrete_floor_worn_001','white_plaster_02','sandy_gravel','plywood','marble_tiles','sparse_grass','wood_floor','painted_plaster_wall','gravel_stones']
jobs=[]
for t in TEX:
    f=json.load(urllib.request.urlopen(f"https://api.polyhaven.com/files/{t}"))
    for m,key in [('Diffuse','diff'),('nor_gl','nor'),('Rough','rough'),('Displacement','disp')]:
        if m in f and '2k' in f[m]:
            jobs.append((f[m]['2k']['jpg']['url'],f'tex/{t}/{key}.jpg'))
def get(j):
    u,p=j; os.makedirs(os.path.dirname(p),exist_ok=True)
    if not os.path.exists(p): urllib.request.urlretrieve(u,p)
    return os.path.getsize(p)
with cf.ThreadPoolExecutor(10) as ex: s=list(ex.map(get,jobs))
print(len(jobs),'files',round(sum(s)/1e6,1),'MB')
