"""Background city for JEC_MASTER.blend.
Replaces the lawn + scattered trees with streets, neighbouring apartment blocks, a plaza and a hillside town.
Usage in Blender:  import jmcity; jmcity.build_all()
"""
import bpy, bmesh, math, os, random
import jecmaster as jm
J = jm.J
P = jm.ROOT + '/'
TEX = P + 'assets/tex/city/'
BAY, FLH = 4.0, 3.2
FAC = ['facA1', 'facA2', 'facA3', 'facB1', 'facB2', 'facB3', 'facC1', 'facD1']
STONE1, STONE2, STONE3, ROOF, TANK, SOLAR, RAIL = 8, 9, 10, 11, 12, 13, 14
STYLES = [dict(front=3, side=0, stone=STONE1), dict(front=4, side=1, stone=STONE2), dict(front=5, side=2, stone=STONE3),
          dict(front=0, side=0, stone=STONE1), dict(front=6, side=6, stone=STONE1), dict(front=1, side=1, stone=STONE2),
          dict(front=7, side=7, stone=STONE3)]
HAZE = dict(near=70.0, far=900.0, amount=0.70, strength=1.0)
NF = (-118.0, 118.0, -104.0, 132.0)      # near-field rectangle handled by the explicit street grid


# ------------------------------------------------------------------ dusk switch shared by all city materials
def dusk_group():
    g = bpy.data.node_groups.get('NG_JM_DUSK')
    if g: return g
    g = bpy.data.node_groups.new('NG_JM_DUSK', 'ShaderNodeTree')
    g.interface.new_socket('Dusk', in_out='OUTPUT', socket_type='NodeSocketFloat')
    o = g.nodes.new('NodeGroupOutput'); v = g.nodes.new('ShaderNodeValue'); v.name = 'V'
    g.links.new(v.outputs[0], o.inputs[0])
    return g


def set_dusk(d):
    dusk_group().nodes['V'].outputs[0].default_value = 1.0 if d else 0.0


def patch():
    """make jm.set_state also switch the city's lit windows / haze colour"""
    if getattr(jm, '_city_patched', False): return
    orig = jm.set_state

    def set_state(ext=None, it=None, dusk=None):
        r = orig(ext, it, dusk); set_dusk(jm.STATE['dusk']); return r
    jm.set_state = set_state; jm._city_patched = True


# ------------------------------------------------------------------ materials
def _img(path, noncolor=False):
    name = os.path.basename(path)
    im = bpy.data.images.get(name) or bpy.data.images.load(path)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return im


def _new(name):
    m = bpy.data.materials.get(name)
    if m: bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name); m.use_nodes = True
    for n in list(m.node_tree.nodes): m.node_tree.nodes.remove(n)
    return m, m.node_tree, m.node_tree.nodes.new('ShaderNodeOutputMaterial')


def _haze(nt, surf):
    L = nt.links
    cam = nt.nodes.new('ShaderNodeCameraData')
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.clamp = True; mr.name = 'HAZE_RANGE'
    mr.inputs['From Min'].default_value = HAZE['near']; mr.inputs['From Max'].default_value = HAZE['far']
    mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = HAZE['amount']
    L.new(cam.outputs['View Z Depth'], mr.inputs['Value'])
    dg = nt.nodes.new('ShaderNodeGroup'); dg.node_tree = dusk_group()
    mc = nt.nodes.new('ShaderNodeMix'); mc.data_type = 'RGBA'; mc.name = 'HAZE_COL'
    mc.inputs[6].default_value = (0.70, 0.76, 0.84, 1); mc.inputs[7].default_value = (0.20, 0.19, 0.27, 1)
    L.new(dg.outputs[0], mc.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.name = 'HAZE_EM'; em.inputs['Strength'].default_value = HAZE['strength']
    L.new(mc.outputs[2], em.inputs['Color'])
    ms = nt.nodes.new('ShaderNodeMixShader')
    L.new(mr.outputs['Result'], ms.inputs['Fac']); L.new(surf, ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2])
    return ms.outputs[0]


def mat_fac(key):
    m, nt, out = _new('M_City_' + key); L = nt.links
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); uv = nt.nodes.new('ShaderNodeUVMap')
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = _img(TEX + key + '_col.png')
    tm = nt.nodes.new('ShaderNodeTexImage'); tm.image = _img(TEX + key + '_msk.png', True)
    th = nt.nodes.new('ShaderNodeTexImage'); th.image = _img(TEX + key + '_hgt.png', True)
    hv = nt.nodes.new('ShaderNodeVectorMath'); hv.operation = 'MULTIPLY'; hv.inputs[1].default_value = (0.5, 0.5, 1.0)
    L.new(uv.outputs[0], hv.inputs[0])
    for t in (tc, tm, th): L.new(hv.outputs[0], t.inputs['Vector'])
    L.new(tc.outputs['Color'], b.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.82; rr.inputs['To Max'].default_value = 0.05
    L.new(tm.outputs['Color'], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.55; bp.inputs['Distance'].default_value = 0.07
    L.new(th.outputs['Color'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    # lit windows at dusk: one random value per bay / storey
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L.new(uv.outputs[0], sep.inputs[0])
    fx = nt.nodes.new('ShaderNodeMath'); fx.operation = 'FLOOR'; L.new(sep.outputs['X'], fx.inputs[0])
    fy = nt.nodes.new('ShaderNodeMath'); fy.operation = 'FLOOR'; L.new(sep.outputs['Y'], fy.inputs[0])
    cmb = nt.nodes.new('ShaderNodeCombineXYZ'); L.new(fx.outputs[0], cmb.inputs['X']); L.new(fy.outputs[0], cmb.inputs['Y'])
    wn = nt.nodes.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '2D'; L.new(cmb.outputs[0], wn.inputs['Vector'])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.6; L.new(wn.outputs['Value'], gt.inputs[0])
    dg = nt.nodes.new('ShaderNodeGroup'); dg.node_tree = dusk_group()
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L.new(gt.outputs[0], m1.inputs[0]); L.new(tm.outputs['Color'], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L.new(m1.outputs[0], m2.inputs[0]); L.new(dg.outputs[0], m2.inputs[1])
    m3 = nt.nodes.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'; m3.inputs[1].default_value = 1.8; m3.name = 'LIT_STRENGTH'; L.new(m2.outputs[0], m3.inputs[0])
    wc = nt.nodes.new('ShaderNodeMix'); wc.data_type = 'RGBA'
    wc.inputs[6].default_value = (1.0, 0.60, 0.28, 1); wc.inputs[7].default_value = (1.0, 0.84, 0.62, 1)
    sx = nt.nodes.new('ShaderNodeSeparateColor'); L.new(wn.outputs['Color'], sx.inputs[0]); L.new(sx.outputs[2], wc.inputs[0])
    L.new(wc.outputs[2], b.inputs['Emission Color']); L.new(m3.outputs[0], b.inputs['Emission Strength'])
    L.new(_haze(nt, b.outputs[0]), out.inputs['Surface'])
    return m


def mat_plain(name, color, rough=0.8, metal=0.0, noise=0.0):
    m, nt, out = _new(name); L = nt.links
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if noise:
        tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 0.035; nz.inputs['Detail'].default_value = 6.0
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        mx.inputs[6].default_value = (*[c * (1 - noise) for c in color], 1); mx.inputs[7].default_value = (*[min(1, c * (1 + noise)) for c in color], 1)
        L.new(nz.outputs['Fac'], mx.inputs[0]); L.new(mx.outputs[2], b.inputs['Base Color'])
    L.new(_haze(nt, b.outputs[0]), out.inputs['Surface'])
    return m


def city_mats():
    ms = [mat_fac(k) for k in FAC]
    ms += [mat_plain('M_City_Stone1', (0.686, 0.617, 0.491)), mat_plain('M_City_Stone2', (0.565, 0.491, 0.371)),
           mat_plain('M_City_Stone3', (0.76, 0.716, 0.631)), mat_plain('M_City_Roof', (0.55, 0.54, 0.52), 0.9),
           mat_plain('M_City_Tank', (0.86, 0.86, 0.84), 0.35), mat_plain('M_City_Solar', (0.02, 0.03, 0.07), 0.12),
           mat_plain('M_City_Rail', (0.10, 0.10, 0.11), 0.4, 0.6)]
    return ms


# ------------------------------------------------------------------ mesh helpers
def _face(bm, uvl, pts, uvs, mi):
    f = bm.faces.new([bm.verts.new(p) for p in pts]); f.material_index = mi
    for l, uv in zip(f.loops, uvs): l[uvl].uv = uv
    return f


UV1 = ((0, 0), (1, 0), (1, 1), (0, 1))


def add_box(bm, uvl, T, x0, x1, y0, y1, z0, z1, mi, bottom=False):
    p = [T(x0, y0, z0), T(x1, y0, z0), T(x1, y1, z0), T(x0, y1, z0), T(x0, y0, z1), T(x1, y0, z1), T(x1, y1, z1), T(x0, y1, z1)]
    fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)] + ([(3, 2, 1, 0)] if bottom else [])
    for f in fs: _face(bm, uvl, [p[i] for i in f], UV1, mi)


def add_building(bm, uvl, rng, cx, cy, z0, w, d, nfl, rot, style, detail=False):
    H = nfl * FLH; c, s = math.cos(rot), math.sin(rot)
    T = lambda x, y, z: (cx + x * c - y * s, cy + x * s + y * c, z0 + z)
    hw, hd = w / 2, d / 2
    cor = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    uo, vo = rng.randrange(0, 60), rng.randrange(0, 60)
    for i in range(4):
        (xa, ya), (xb, yb) = cor[i], cor[(i + 1) % 4]
        nb = max(1, round(math.hypot(xb - xa, yb - ya) / BAY)); u0 = uo + i * 7
        _face(bm, uvl, [T(xa, ya, 0), T(xb, yb, 0), T(xb, yb, H), T(xa, ya, H)],
              ((u0, vo), (u0 + nb, vo), (u0 + nb, vo + nfl), (u0, vo + nfl)), style['front'] if i == 0 else style['side'])
    st = style['stone']; t = 0.25; ph = 1.0
    add_box(bm, uvl, T, -hw, hw, -hd, -hd + t, H, H + ph, st); add_box(bm, uvl, T, -hw, hw, hd - t, hd, H, H + ph, st)
    add_box(bm, uvl, T, -hw, -hw + t, -hd + t, hd - t, H, H + ph, st); add_box(bm, uvl, T, hw - t, hw, -hd + t, hd - t, H, H + ph, st)
    _face(bm, uvl, [T(-hw, -hd, H + 0.03), T(hw, -hd, H + 0.03), T(hw, hd, H + 0.03), T(-hw, hd, H + 0.03)], UV1, ROOF)
    bx = rng.uniform(-hw + 2.0, max(-hw + 2.1, hw - 5.6)); by = rng.uniform(-hd + 2.0, max(-hd + 2.1, hd - 6.8))
    add_box(bm, uvl, T, bx, bx + 3.4, by, by + 4.6, H, H + 2.7, st)
    for k in range(rng.randint(2, 5) if nfl > 3 else rng.randint(1, 3)):
        tx = rng.uniform(-hw + 1.0, hw - 2.3); ty = rng.uniform(-hd + 1.0, hd - 2.3)
        add_box(bm, uvl, T, tx + 0.15, tx + 1.0, ty + 0.15, ty + 1.0, H, H + 0.6, RAIL)
        add_box(bm, uvl, T, tx, tx + 1.15, ty, ty + 1.15, H + 0.6, H + 1.95, TANK)
    for k in range(rng.randint(0, 3)):
        sx = rng.uniform(-hw + 1.2, hw - 3.4); sy = rng.uniform(-hd + 1.2, hd - 2.6)
        _face(bm, uvl, [T(sx, sy, H + 0.35), T(sx + 2.0, sy, H + 0.35), T(sx + 2.0, sy + 1.1, H + 1.15), T(sx, sy + 1.1, H + 1.15)], UV1, SOLAR)
        add_box(bm, uvl, T, sx + 0.2, sx + 1.8, sy + 1.12, sy + 1.6, H + 0.9, H + 1.4, TANK)
    if detail and style['front'] in (3, 4, 5):
        nb = max(1, round(w / BAY)); bw = w / nb
        for k in range(1, nfl):
            for b in range(nb):
                x0 = -hw + b * bw + 0.1; x1 = x0 + bw - 0.2; z = k * FLH
                add_box(bm, uvl, T, x0, x1, -hd - 1.3, -hd, z - 0.04, z + 0.16, st, bottom=True)
                add_box(bm, uvl, T, x0, x1, -hd - 1.3, -hd - 1.2, z + 0.16, z + 1.1, st)
                add_box(bm, uvl, T, x0, x0 + 0.1, -hd - 1.2, -hd, z + 0.16, z + 1.1, st)
                add_box(bm, uvl, T, x1 - 0.1, x1, -hd - 1.2, -hd, z + 0.16, z + 1.1, st)


def _finish(bm, name, mats, col, ext=(0, 99)):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob); jm.tag(ob, ext)
    return ob


def boxobj(name, specs, mat, col, ext=(0, 99)):
    """world-space boxes (x0,x1,y0,y1,z0,z1) with one material"""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); T = lambda x, y, z: (x, y, z)
    for (x0, x1, y0, y1, z0, z1) in specs: add_box(bm, uvl, T, x0, x1, y0, y1, z0, z1, 0, bottom=False)
    return _finish(bm, name, [mat], col, ext)


# ------------------------------------------------------------------ terrain + far town
def hfun(x, y):
    r = math.hypot(x, y)
    if r < 150: return 0.0
    t = r - 150
    return 0.075 * t + 0.00006 * t * t + 10 * math.sin(x * 0.009 + 1.1) * math.sin(y * 0.011 + 0.3) * min(1.0, t / 150)


def build_terrain(col):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); N = 72; S = 900.0
    vs = [[bm.verts.new((-S + 2 * S * i / N, -S + 2 * S * j / N, hfun(-S + 2 * S * i / N, -S + 2 * S * j / N) - 0.04)) for j in range(N + 1)] for i in range(N + 1)]
    for i in range(N):
        for j in range(N):
            xa, xb = -S + 2 * S * i / N, -S + 2 * S * (i + 1) / N; ya, yb = -S + 2 * S * j / N, -S + 2 * S * (j + 1) / N
            if xa >= -100.01 and xb <= 100.01 and ya >= -100.01 and yb <= 100.01: continue      # centre is rebuilt around the plot
            f = bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1])); f.smooth = True
    z = -0.04
    for (x0, x1, y0, y1) in ((-100, -30, -100, 100), (30, 100, -100, 100), (-30, 30, -100, -16), (-30, 30, 22, 100)):
        bm.faces.new([bm.verts.new(p) for p in ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))])
    return _finish(bm, 'C_Terrain', [mat_plain('M_City_Ground', (0.36, 0.33, 0.29), 0.92, noise=0.18)], col)


def build_far(col, mats, seed=7):
    rng = random.Random(seed); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); n = 0; sp = 34.0
    k = int(820 / sp)
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            x = i * sp + rng.uniform(-7, 7); y = j * sp + rng.uniform(-7, 7)
            if NF[0] - 16 < x < NF[1] + 16 and NF[2] - 16 < y < NF[3] + 16: continue
            r = math.hypot(x, y)
            if r > 830 or rng.random() < 0.14: continue
            w = rng.choice((16, 20, 20, 24, 24, 28)); d = rng.choice((14, 16, 18, 20))
            nfl = rng.choice((2, 3, 3, 4, 4, 4, 5, 5)) if rng.random() > 0.04 else rng.randint(8, 12)
            rot = math.atan2(-x, y) + rng.uniform(-0.3, 0.3) + (math.pi / 2 if rng.random() < 0.25 else 0)
            style = rng.choice(STYLES[:6]) if rng.random() > 0.06 else STYLES[6]
            add_building(bm, uvl, rng, x, y, hfun(x, y) - 2.6, w, d, nfl, rot, style, detail=False); n += 1
    ob = _finish(bm, 'C_FarTown', mats, col); ob['count'] = n
    return ob


# ------------------------------------------------------------------ near field: streets, pavements, plaza, neighbours
NEAR = [  # cx, cy, w, d, floors, rot_deg, style
    # north row 1 (faces the back street)
    (-96, 51, 28, 20, 3, 0, 1), (-62, 51, 28, 20, 4, 0, 0), (-16, 51, 26, 20, 4, 0, 2), (15, 51, 26, 20, 3, 0, 0), (62, 51, 28, 20, 5, 0, 1), (96, 51, 28, 20, 4, 0, 2),
    # north row 2 / 3
    (-96, 83, 28, 20, 4, 0, 0), (-62, 83, 28, 20, 5, 0, 2), (-16, 83, 26, 20, 4, 0, 1), (15, 83, 26, 20, 5, 0, 6), (62, 83, 28, 20, 4, 0, 0), (96, 83, 28, 20, 4, 0, 1),
    (-96, 115, 28, 20, 4, 0, 2), (-62, 115, 28, 20, 4, 0, 1), (-16, 115, 26, 20, 5, 0, 0), (15, 115, 26, 20, 4, 0, 2), (62, 115, 28, 20, 5, 0, 0), (96, 115, 28, 20, 3, 0, 1),
    # west / east of the plot (face the side streets)
    (-62, 6, 30, 24, 4, 90, 2), (-96, 6, 30, 24, 3, 90, 0), (62, 6, 30, 24, 4, -90, 0), (96, 6, 30, 24, 3, -90, 1),
    # south of the main road, either side of the plaza
    (24, -47, 26, 20, 4, 180, 1), (56, -47, 28, 20, 5, 180, 0), (90, -47, 28, 20, 3, 180, 2), (-66, -47, 26, 20, 4, 180, 0), (-98, -47, 28, 20, 3, 180, 2),
    (-98, -88, 28, 20, 4, 180, 1), (-66, -88, 26, 20, 3, 180, 2), (-34, -90, 26, 20, 4, 180, 0), (-3, -90, 26, 20, 4, 180, 1), (28, -88, 26, 20, 5, 180, 2), (60, -88, 28, 20, 4, 180, 0), (92, -88, 28, 20, 4, 180, 1),
]


def build_near(col, mats, seed=3):
    rng = random.Random(seed); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    for (cx, cy, w, d, nfl, rot, st) in NEAR:
        add_building(bm, uvl, rng, cx, cy, -0.04, w, d, nfl, math.radians(rot), STYLES[st], detail=True)
    return _finish(bm, 'C_NearBuildings', mats, col)


def _seg(a0, a1, gaps):
    """split [a0,a1] removing the gap intervals"""
    out = []; cur = a0
    for g0, g1 in sorted(gaps):
        if g1 <= cur or g0 >= a1: continue
        if g0 > cur: out.append((cur, g0))
        cur = max(cur, g1)
    if cur < a1: out.append((cur, a1))
    return out


def build_streets(col):
    M = jm.M; XS = [(-44.0, -36.0), (36.0, 44.0)]            # side streets (run north from the main road)
    YS = [(28.0, 36.0), (64.0, 70.0), (96.0, 102.0)]          # cross streets north of the plot
    asp = []; walk = []; lots = []
    for (x0, x1) in XS:
        asp.append((x0, x1, -19.6, 132.0, -0.3, 0.0))
    for (y0, y1) in YS:
        for (a, b) in _seg(-118.0, 118.0, XS): asp.append((a, b, y0, y1, -0.3, 0.0))
    # pavements: 3 m bands beside every carriageway, broken at junctions
    def band_x(x0, x1, ya, yb):
        for (a, b) in _seg(ya, yb, [(y0 - 3, y1 + 3) for (y0, y1) in YS]): walk.append((x0, x1, a, b, -0.04, 0.15))
    def band_y(y0, y1, xa, xb):
        for (a, b) in _seg(xa, xb, [(x0 - 3, x1 + 3) for (x0, x1) in XS]): walk.append((a, b, y0, y1, -0.04, 0.15))
    band_x(-47, -44, -16, 132); band_x(-36, -33, -16, 132); band_x(33, 36, -16, 132); band_x(44, 47, -16, 132)
    for (y0, y1) in YS:
        band_y(y0 - 3, y0, -118, 118); band_y(y1, y1 + 3, -118, 118)
    # main road pavements (replace the old continuous ones) + plaza on the south side
    band_y(-19.6, -16.0, -400, 400)
    for (a, b) in _seg(-400, 400, [(-50, 8)]): walk.append((a, b, -32.0, -28.5, -0.04, 0.15))
    plaza = [(-50, 8, -76, -28.5, -0.04, 0.15)]
    # planting / paving strips around the plot hoarding line
    walk += [(-33, -30.3, -16, 25), (30.3, 33, -16, 25), (-33, 33, 22.3, 25)]
    walk = [w if len(w) == 6 else (w[0], w[1], w[2], w[3], -0.04, 0.15) for w in walk]
    # paved lots under the neighbours
    for (cx, cy, w, d, nfl, rot, st) in NEAR:
        ww, dd = (w, d) if rot in (0, 180) else (d, w)
        lots.append((cx - ww / 2 - 3, cx + ww / 2 + 3, cy - dd / 2 - 3, cy + dd / 2 + 3, -0.04, 0.03))
    obs = [boxobj('C_Streets', asp, M['asphalt'], col), boxobj('C_Pavements', walk, M['sidewalk'], col),
           boxobj('C_Plaza', plaza, M['paving'], col), boxobj('C_Lots', lots, M['paving'], col)]
    # plaza furniture: planters + benches
    pl = []; be = []
    for (x, y) in ((-44, -70), (-30, -70), (-16, -70), (-2, -70), (-46, -36), (4, -36)):
        pl.append((x - 1.6, x + 1.6, y - 1.6, y + 1.6, 0.15, 0.7))
    for x in (-37, -23, -9):
        be.append((x - 1.1, x + 1.1, -70.3, -69.7, 0.15, 0.6))
    obs += [boxobj('C_PlazaPlanters', pl, M['stone_fin'], col), boxobj('C_PlazaBenches', be, M['conc'], col)]
    # low boundary walls between neighbouring lots
    wl = []
    for (cx, cy, w, d, nfl, rot, st) in NEAR:
        ww, dd = (w, d) if rot in (0, 180) else (d, w)
        x0, x1, y0, y1 = cx - ww / 2 - 3, cx + ww / 2 + 3, cy - dd / 2 - 3, cy + dd / 2 + 3
        if rot == 0: wl += [(x0, x0 + 0.25, y0, y1, 0, 1.3), (x1 - 0.25, x1, y0, y1, 0, 1.3), (x0, x1, y1 - 0.25, y1, 0, 1.3)]
        elif rot == 180: wl += [(x0, x0 + 0.25, y0, y1, 0, 1.3), (x1 - 0.25, x1, y0, y1, 0, 1.3), (x0, x1, y0, y0 + 0.25, 0, 1.3)]
        elif rot == 90: wl += [(x0, x1, y0, y0 + 0.25, 0, 1.3), (x0, x1, y1 - 0.25, y1, 0, 1.3), (x0, x0 + 0.25, y0, y1, 0, 1.3)]
        else: wl += [(x0, x1, y0, y0 + 0.25, 0, 1.3), (x0, x1, y1 - 0.25, y1, 0, 1.3), (x1 - 0.25, x1, y0, y1, 0, 1.3)]
    obs.append(boxobj('C_LotWalls', wl, M['stone_fin'], col))
    return obs


# ------------------------------------------------------------------ trees / lamps
TREES = [  # x, y, kind index, scale factor
    (30, -30.3, 0, 1.0), (46, -30.3, 1, 0.9), (62, -30.3, 0, 1.05), (78, -30.3, 1, 1.0), (94, -30.3, 0, 0.95),
    (-64, -30.3, 1, 1.0), (-80, -30.3, 0, 0.95), (-96, -30.3, 1, 1.05),
    (-45.5, -8, 0, 0.9), (-45.5, 8, 1, 1.0), (-45.5, 22, 0, 0.95), (45.5, -8, 1, 0.95), (45.5, 8, 0, 1.0), (45.5, 22, 1, 0.9),
    (-26, 37.5, 0, 1.0), (-10, 37.5, 1, 0.9), (6, 37.5, 0, 1.05), (22, 37.5, 1, 1.0), (-70, 37.5, 0, 0.9), (-54, 37.5, 1, 1.0), (56, 37.5, 0, 1.0), (72, 37.5, 1, 0.95),
    (-44, -70, 1, 0.9), (-30, -70, 0, 0.85), (-16, -70, 1, 0.9), (-2, -70, 0, 0.85),
    (-79, 6, 1, 1.0), (79, 6, 0, 1.0), (-32, 67, 0, 0.9), (32, 67, 1, 0.95), (0, 99, 0, 1.0), (-79, 99, 1, 0.9), (79, 67, 0, 0.95),
]


def build_trees(col):
    land = bpy.data.collections['M_Land']
    def root(prefix):
        for o in land.objects:
            if o.parent is None and o.name.split('.')[0] == prefix: return o
    kinds = [r for r in (root('jacaranda_tree'), root('island_tree_02'), root('island_tree_01')) if r]
    rng = random.Random(11); n = 0
    for o in [o for o in col.objects if o.get('city_tree')]:
        for ch in list(o.children_recursive): bpy.data.objects.remove(ch)
        bpy.data.objects.remove(o)
    for (x, y, k, s) in TREES:
        r = kinds[k % len(kinds)]
        t = J.dupe(r, col, (x, y, 0.1), rng.uniform(0, 360), r.scale[0] * s, 'C_Tree%02d' % n)
        jm.tag(t, (0, 99)); t['city_tree'] = 1; n += 1
    lamp = root('street_lamp_01')
    if lamp:
        for i, (x, y) in enumerate([(-46, -52), (4, -52), (20, -30), (52, -30), (84, -30), (-72, -30), (-46, 0), (46, 0), (-18, 37), (14, 37)]):
            t = J.dupe(lamp, col, (x, y, 0.15), 0, lamp.scale[0], 'C_Lamp%02d' % i); jm.tag(t, (0, 99)); t['city_tree'] = 1
    return n


# ------------------------------------------------------------------ retire the old park
def retire_old():
    n = 0
    for name in ('G_Gardens', 'G_FarGrass', 'G_Sidewalk', 'G_FarWalk', 'G_Curb'):
        o = bpy.data.objects.get(name)
        if o: o['ext'] = [99, 100]; n += 1
    for o in bpy.data.collections['M_Land'].objects:      # scattered neighbour trees / shrubs outside the plot
        if o.parent is None and o.name.split('.')[0] in ('tree_small_02', 'shrub_01', 'island_tree_01', 'island_tree_02', 'jacaranda_tree') and list(o.get('ext', [])) == [0, 99]:
            o['ext'] = [99, 100]; n += 1
    for o in bpy.data.collections['M_Green'].objects:     # balcony / terrace planting
        if o.parent is None: o['ext'] = [99, 100]; n += 1
    for o in bpy.data.objects:
        if o.name.startswith('E_Planter'): o['ext'] = [99, 100]; n += 1
    return n


def restyle_plot():
    o = bpy.data.objects.get('L_PlotGround')
    if o and o.material_slots: o.material_slots[0].material = jm.M['paving']
    o = bpy.data.objects.get('L_Paths')
    if o and o.material_slots: o.material_slots[0].material = jm.M['sidewalk']


def build_all():
    patch(); col = jm.C('M_City'); mats = city_mats()
    r = retire_old(); restyle_plot()
    build_terrain(col); far = build_far(col, mats); build_near(col, mats); build_streets(col); nt = build_trees(col)
    jm.set_state()
    return dict(retired=r, far=far.get('count'), trees=nt)


patch()


# ------------------------------------------------------------------ construction cameras (one continuous low path) + anchor states
KCAMS = {   # name: (position, target, lens mm)
    'K0':  ((-26.5, -13.2, 1.75), (8.0, 6.0, 3.0), 22),
    'K1':  ((-24.5, -13.6, 3.2), (0.0, 1.0, -1.2), 22),
    'K2':  ((-21.5, -13.4, 2.3), (2.0, 1.0, -1.3), 21),
    'K2a': ((-22.5, -13.8, 2.0), (0.0, 0.0, 0.8), 21),
    'K2f': ((-23.5, -14.0, 1.8), (0.0, -1.0, 2.6), 20),
    'K2b': ((-24.5, -14.2, 1.7), (0.0, -1.5, 3.4), 20),
    'K3':  ((-28.6, -15.0, 3.6), (-1.0, -2.0, 6.5), 19),
    'K4':  ((-37.0, -27.0, 2.0), (-2.0, -3.0, 13.0), 16),
    'K5':  ((-35.0, -33.0, 2.6), (-1.0, -3.0, 13.5), 21),
    'K6':  ((-32.0, -40.0, 3.2), (0.0, -3.0, 13.0), 24),
}
SUB_HIDE = ['S_Beams1', 'S_Beams2', 'S_Cols1', 'S_Core1', 'S_Slab1', 'S_Slab2', 'S_Stair1', 'T_EdgeForm2', 'T_EdgeRail2', 'T_Props2', 'T_Props2_Heads', 'T_StartersL2']
ANCHOR = {  # key: (ext stage, dusk, extra objects to hide, extra objects to show)
    'S0': (0, 0, [], []), 'S1': (1, 0, [], []), 'S2': (2, 0, [], []),
    'S2a': (3, 0, SUB_HIDE + ['S_Cols0', 'S_Core0', 'S_Stair0'], []),
    'S2f': (3, 0, SUB_HIDE + ['S_Cols0', 'S_Core0', 'S_Stair0'], ['TMP_ColForm', 'TMP_ColYokes']),
    'S2b': (3, 0, SUB_HIDE, []),
    'S3': (3, 0, [], []), 'S4': (4, 0, [], []), 'S5': (5, 0, [], []), 'S6': (6, 0, [], []), 'S7': (6, 1, [], []),
}


def build_kcams():
    from mathutils import Vector
    col = jm.C('M_City'); out = []
    for name, (pos, tgt, lens) in KCAMS.items():
        n = 'CAM_' + name; o = bpy.data.objects.get(n)
        if not o:
            o = bpy.data.objects.new(n, bpy.data.cameras.new(n)); col.objects.link(o)
        o.location = pos; o.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
        o.data.lens = lens; o.data.sensor_width = 36; o.data.clip_start = 0.1; o.data.clip_end = 3000
        out.append(n)
    return out


def anchor_state(key, it=1):
    ext, dusk, hide, show = ANCHOR[key]
    jm.set_state(ext, 9 if dusk else it, bool(dusk))
    for n in ('TMP_ColForm', 'TMP_ColYokes'):
        o = bpy.data.objects.get(n)
        if o: o.hide_render = True; o.hide_viewport = True
    for n in hide:
        o = bpy.data.objects.get(n)
        if o:
            for ch in [o] + list(o.children_recursive): ch.hide_render = True; ch.hide_viewport = True
    for n in show:
        o = bpy.data.objects.get(n)
        if o: o.hide_render = False; o.hide_viewport = False


def render_still(cam, key, out, pct=100, spp=96, exp=0.0, res=(1920, 1080), it=1, q=95):
    """synchronous still: camera object name, anchor key, output path"""
    S = bpy.context.scene; anchor_state(key, it)
    S.camera = bpy.data.objects[cam]; S.frame_set(1)
    S.render.resolution_x, S.render.resolution_y = res; S.render.resolution_percentage = pct
    S.cycles.samples = spp; S.view_settings.exposure = exp
    S.render.image_settings.file_format = 'JPEG'; S.render.image_settings.quality = q
    S.render.filepath = out
    bpy.ops.render.render(write_still=True)
    return out


# ---- 2026-11-20: runtime changes written back into the file ----
# Camera poses actually used for final/kext (moved north so the back of the south hoarding posts is out of frame).
KCAMS.update({
    'K0':  ((-26.5, -12.0, 1.75), (6.0, 10.0, 3.0), 22),
    'K1':  ((-24.5, -12.6, 3.2), (0.0, 2.5, -1.2), 22),
    'K2':  ((-21.5, -12.8, 2.3), (2.0, 2.5, -1.3), 21),
    'K2a': ((-22.5, -12.8, 2.0), (0.0, 1.5, 0.8), 21),
    'K2f': ((-23.5, -13.0, 1.8), (0.0, 0.5, 2.6), 20),
    'K2b': ((-24.5, -13.2, 1.7), (0.0, 0.0, 3.4), 20),
    'K3':  ((-28.6, -14.6, 3.6), (-1.0, -1.0, 6.5), 19),
})
SAND_PILE_X = 48.0   # H_SandPile.location.x: moved from the SW to the SE corner so the SW corner is free for the K cameras


def move_sand_pile():
    import bpy as _bpy
    ob = _bpy.data.objects.get('H_SandPile')
    if ob:
        ob.location.x = SAND_PILE_X


def kqueue(jobs, tag):
    """Timer queue for anchor stills. jobs: dicts with cam, key, out and optional pct, spp, exp, res, it, q.
    Progress is written to previews/{tag}_log.json and ends with ["DONE", 0]."""
    import bpy as _bpy, json, time, os as _os
    import jecmaster as _jm
    log = []
    path = _jm.ROOT + '/previews/%s_log.json' % tag
    jobs = list(jobs)

    def step():
        if not jobs:
            log.append(['DONE', 0])
            open(path, 'w').write(json.dumps(log))
            return None
        j = jobs.pop(0)
        t = time.time()
        render_still(j['cam'], j['key'], j['out'], pct=j.get('pct', 100), spp=j.get('spp', 96), exp=j.get('exp', 0.0),
                     res=j.get('res', (1920, 1080)), it=j.get('it', 1), q=j.get('q', 95))
        log.append([_os.path.basename(j['out']), round(time.time() - t, 1)])
        open(path, 'w').write(json.dumps(log))
        return 0.2

    _bpy.app.timers.register(step, first_interval=0.2)


# ---- 2026-11-21: S5n anchor (stone and blockwork finished, window openings still empty, crane gone) ----
# Used for the v5 film: S4 -> S5n -> S6, so the glazing only appears after the structure and stone are done.
S5N_HIDE = ['E_BalGlass', 'E_BalRail', 'E_DoorL', 'E_DoorR', 'E_EntFrame', 'E_EntGlass', 'E_FrameF', 'E_FramePH',
            'E_GlassF', 'E_GlassPH', 'E_Screens', 'E_WinFrame', 'E_WinGlass']


def anchor_S5n(it=1):
    """S5, plus every E_ object whose exterior stage starts at 6, minus glass, frames, doors and railings; crane (K_*) hidden.
    To render it use render_S5n(out); render_still() would reset the state through anchor_state()."""
    anchor_state('S5', it)
    for o in bpy.data.objects:
        e = o.get('ext')
        if o.name.startswith('E_') and e is not None and int(e[0]) == 6:
            hid = o.name in S5N_HIDE
            o.hide_render = hid; o.hide_viewport = hid
    for o in bpy.data.objects:
        if o.name in S5N_HIDE or o.name.startswith('K_'):
            for ch in [o] + list(o.children_recursive):
                ch.hide_render = True; ch.hide_viewport = True


def render_S5n(out, cam='CAM_K4', pct=100, spp=96, exp=0.0, res=(1920, 1080), q=95):
    """S5n still with the same settings as render_still."""
    S = bpy.context.scene; anchor_S5n()
    S.camera = bpy.data.objects[cam]; S.frame_set(1)
    S.render.resolution_x, S.render.resolution_y = res; S.render.resolution_percentage = pct
    S.cycles.samples = spp; S.view_settings.exposure = exp
    S.render.image_settings.file_format = 'JPEG'; S.render.image_settings.quality = q
    S.render.filepath = out
    bpy.ops.render.render(write_still=True)
    return out
