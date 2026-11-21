import json, os, urllib.request, concurrent.futures as cf
op=urllib.request.build_opener(); op.addheaders=[("User-Agent","JEC-POC/1.0")]; urllib.request.install_opener(op)
MOD=['street_lamp_01','sofa_02','sofa_03','concrete_road_barrier','cement_bag','ladder_sectioned_01','planter_box_01','island_tree_01','island_tree_02','tree_small_02','coffee_table_round_01','ArmChair_01','wooden_bucket_01']
jobs=[]
for m in MOD:
    try:
        f=json.load(urllib.request.urlopen(f"https://api.polyhaven.com/files/{m}"))
        g=f['gltf']['1k']['gltf']; jobs.append((g['url'],f'models/{m}/{m}.gltf'))
        for p,v in g.get('include',{}).items(): jobs.append((v['url'],f'models/{m}/{p}'))
    except Exception as e: print('ERR',m,e)
def get(j):
    u,p=j; os.makedirs(os.path.dirname(p),exist_ok=True)
    if not os.path.exists(p): urllib.request.urlretrieve(u,p)
    return os.path.getsize(p)
with cf.ThreadPoolExecutor(10) as ex: s=list(ex.map(get,jobs))
print(len(jobs),'files',round(sum(s)/1e6,1),'MB')
