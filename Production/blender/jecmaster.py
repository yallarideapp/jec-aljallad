"""JEC MASTER — one building, every stage derived from it.
Stage system: each object carries
    ob["ext"] = [a, b]   visible while a <= exterior_stage < b
    ob["int"] = [a, b]   visible while a <= interior_stage < b
    ob["dusk"] = 0 both / 1 day only / 2 dusk only
Exterior stages: 0 empty site · 1 excavation · 2 foundations · 3 frame to L2 · 4 frame topped out
                 5 envelope (lower floors finished) · 6 completed
Interior stages (ground-floor room): 1 raw · 2 partitions · 3 MEP rough-in · 4 plaster · 5 ceiling
                 6 floor + wall finishes · 7 paint/doors/lighting/fixtures · 8 final clean · 9 furniture
"""
import bpy, bmesh, math, os, sys, importlib, random
from mathutils import Vector, Matrix
ROOT = os.path.dirname(os.path.abspath(__file__))  # this script's folder (was ~/Desktop/JEC_AlJallad_3D/POC)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import jecpoc as J
importlib.reload(J)

CX = [-15, -9, -3, 3, 9, 15]
CY = [-9, -3, 3, 9]
LV = [0.45, 5.25, 8.75, 12.25, 15.75, 19.25, 22.75, 26.25]   # top of slab, L0..L7 (L7 = roof)
SL = 0.25            # slab
COLW = 0.6           # every column, every floor, every stage
BD, BW = 0.65, 0.4   # beam depth (incl. slab), width
BAL = -10.5          # balcony edge (front cantilever 1.5 m)
CORE = (-3, 3, 3, 9)
TOPZ = 29.6          # core overrun top

def EXT(k):   # envelope stage per level: lower floors first
    return 5 if k <= 3 else 6
def FRAME(k): # frame stage for columns of level k / slab of level k+1
    return 3 if k <= 1 else 4

# ------------------------------------------------------------------ helpers
def C(name):
    root = J.coll("MASTER")
    return J.coll(name, root)

def clear(name):
    c = bpy.data.collections.get(name)
    if not c: return C(name)
    for o in list(c.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return c

def tag(ob, ext=(0, 99), int_=(0, 99), dusk=0):
    ob["ext"] = list(ext); ob["int"] = list(int_); ob["dusk"] = dusk
    return ob

def B(name, specs, mat, col, ext=(0, 99), int_=(0, 99), dusk=0, bevel=0.0):
    if not specs: return None
    ob = J.boxes(name, specs, mat, col, bevel=bevel)
    return tag(ob, ext, int_, dusk)

def mesh_from_bm(name, bm, mat, col):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if mat: me.materials.append(mat)
    return ob

def cyls(name, segs, r, mat, col, seg=8, smooth=True):
    """Many cylinders in one mesh. segs: list of (p0, p1)."""
    bm = bmesh.new()
    for p0, p1 in segs:
        p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
        if d.length < 1e-4: continue
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length,
                                    matrix=Matrix.Translation(Vector((0, 0, d.length / 2))))
        q = d.to_track_quat('Z', 'Y')
        bmesh.ops.transform(bm, matrix=Matrix.Translation(p0) @ q.to_matrix().to_4x4(), verts=res['verts'])
    ob = mesh_from_bm(name, bm, mat, col)
    if smooth:
        try: ob.data.shade_smooth()
        except Exception: pass
    return ob

def wall(axis, c0, c1, a0, a1, z0, z1, holes=()):
    """Box specs of a wall with rectangular holes. axis 'x': wall in plane x=[c0,c1] spanning y=[a0,a1];
    axis 'y': wall in plane y=[c0,c1] spanning x. holes: (h0, h1, hz0, hz1) along the span."""
    cuts = sorted(set([a0, a1] + [h[0] for h in holes] + [h[1] for h in holes]))
    out = []
    for s0, s1 in zip(cuts[:-1], cuts[1:]):
        if s1 - s0 < 1e-4 or s0 < a0 - 1e-6 or s1 > a1 + 1e-6: continue
        mid = (s0 + s1) / 2
        zs = [(z0, z1)]
        for h in holes:
            if not (h[0] <= mid <= h[1]): continue
            nz = []
            for p, q in zs:
                if h[3] <= p or h[2] >= q: nz.append((p, q)); continue
                if h[2] > p: nz.append((p, h[2]))
                if h[3] < q: nz.append((h[3], q))
            zs = nz
        for p, q in zs:
            if q - p < 1e-4: continue
            out.append((c0, s0, p, c1, s1, q) if axis == 'x' else (s0, c0, p, s1, c1, q))
    return out

def frame_specs(axis, c, a0, a1, z0, z1, w=0.06, d=0.1):
    """Bronze window frame around an opening (4 bars)."""
    h = d / 2
    if axis == 'x':
        return [(c - h, a0, z0, c + h, a0 + w, z1), (c - h, a1 - w, z0, c + h, a1, z1),
                (c - h, a0, z0, c + h, a1, z0 + w), (c - h, a0, z1 - w, c + h, a1, z1)]
    return [(a0, c - h, z0, a0 + w, c + h, z1), (a1 - w, c - h, z0, a1, c + h, z1),
            (a0, c - h, z0, a1, c + h, z0 + w), (a0, c - h, z1 - w, a1, c + h, z1)]

def glazing_run(axis, c, a0, a1, z0, z1, pane=1.5):
    """Glass + bronze mullions for a full-height run."""
    n = max(1, round((a1 - a0) / pane)); step = (a1 - a0) / n
    glass = [(c - 0.012, a0, z0, c + 0.012, a1, z1)] if axis == 'x' else [(a0, c - 0.012, z0, a1, c + 0.012, z1)]
    fr = frame_specs(axis, c, a0, a1, z0, z1, w=0.07, d=0.14)
    for i in range(1, n):
        a = a0 + i * step
        fr.append((c - 0.06, a - 0.03, z0, c + 0.06, a + 0.03, z1) if axis == 'x' else (a - 0.03, c - 0.06, z0, a + 0.03, c + 0.06, z1))
    return glass, fr

def cols_at(k):
    pts = [(x, y) for x in CX for y in CY]
    if k == 6: pts = [(x, y) for (x, y) in pts if x <= 9 and y >= -3]
    return pts

# ------------------------------------------------------------------ materials
M = {}
def mats():
    T = os.path.join(J.TEX)
    def get(n, fn):
        m = bpy.data.materials.get(n)
        if m: return m
        return fn()
    M['stone'] = get('M_StonePanel', lambda: mat_stone('M_StonePanel', (0.93, 0.86, 0.74)))
    M['stone_fin'] = get('M_StonePanelFin', lambda: mat_stone('M_StonePanelFin', (0.96, 0.9, 0.8)))
    M['conc'] = get('M_Conc3', lambda: J.pbr('M_Conc3', 'concrete_wall_008', scale=2.2, tint=(0.8, 0.79, 0.76), rough=(0.65, 0.95), bump=0.7, sat=0.25))
    M['conc_floor'] = get('M_ConcFloor', lambda: J.pbr('M_ConcFloor', 'concrete_floor_worn_001', scale=3.5, tint=(0.78, 0.76, 0.73), rough=(0.6, 0.95), bump=0.5, sat=0.3))
    M['block'] = get('M_CMU', lambda: mat_cmu('M_CMU'))
    M['soil'] = get('M_Soil', lambda: J.pbr('M_Soil', 'excavated_soil_wall', scale=4.0, tint=(0.95, 0.85, 0.72), rough=(0.8, 1.0), bump=1.0))
    M['dirt'] = get('M_Dirt', lambda: J.pbr('M_Dirt', 'brown_mud_dry', scale=5.0, tint=(0.95, 0.86, 0.74), rough=(0.8, 1.0), bump=0.8, sat=0.8))
    M['gravel'] = get('M_Gravel', lambda: J.pbr('M_Gravel', 'sandy_gravel', scale=3.0, tint=(0.95, 0.9, 0.82), rough=(0.8, 1.0), bump=1.0))
    M['asphalt'] = get('M_Asphalt', lambda: J.pbr('M_Asphalt', 'asphalt_02', scale=6.0, tint=(0.75, 0.75, 0.75), rough=(0.6, 0.95), bump=0.6))
    M['paving'] = get('M_Paving', lambda: J.pbr('M_Paving', 'precast_stone_paving', scale=3.0, tint=(0.95, 0.91, 0.84), rough=(0.5, 0.9), bump=0.8, sat=0.6))
    M['sidewalk'] = get('M_Sidewalk', lambda: J.pbr('M_Sidewalk', 'concrete_floor_02', scale=3.0, tint=(0.85, 0.84, 0.82), rough=(0.6, 0.95), bump=0.5, sat=0.3))
    M['lawn'] = get('M_Lawn2', lambda: J.pbr('M_Lawn2', 'leafy_grass', scale=3.0, tint=(0.5, 0.72, 0.36), rough=(0.7, 1.0), bump=0.6, sat=1.25))
    M['grass'] = get('M_Grass', lambda: J.pbr('M_Grass', 'sparse_grass', scale=4.0, tint=(0.9, 0.95, 0.8), rough=(0.7, 1.0), bump=0.8))
    M['plywood'] = get('M_Plywood', lambda: J.pbr('M_Plywood', 'plywood', scale=2.4, tint=(1, 0.95, 0.85), rough=(0.6, 0.9), bump=0.3))
    M['plaster'] = get('M_Plaster', lambda: J.pbr('M_Plaster', 'white_plaster_02', scale=2.5, tint=(0.8, 0.79, 0.76), rough=(0.75, 0.95), bump=0.4, sat=0.2))
    M['paint'] = get('M_Paint', lambda: J.pbr('M_Paint', 'painted_plaster_wall', scale=3.0, tint=(0.93, 0.91, 0.87), rough=(0.7, 0.9), bump=0.15, sat=0.15, bright=1.1))
    M['tile'] = get('M_FloorMarble', lambda: mat_floor('M_FloorMarble'))
    M['feature'] = get('M_Feature', lambda: J.pbr('M_Feature', 'marble_01', scale=3.2, tint=(0.95, 0.9, 0.82), rough=(0.12, 0.3), bump=0.15, sat=0.6))
    M['oak'] = get('M_Oak', lambda: J.pbr('M_Oak', 'white_oak_veneer', scale=1.6, tint=(0.9, 0.82, 0.7), rough=(0.35, 0.6), bump=0.2))
    M['rug'] = get('M_RugWool2', lambda: J.pbr('M_RugWool2', 'poly_wool_herringbone', scale=0.6, tint=(0.72, 0.69, 0.64), rough=(0.85, 1.0), bump=0.8, sat=0.3))
    M['linen'] = get('M_Linen2', lambda: J.pbr('M_Linen2', 'rough_linen', scale=0.45, tint=(0.93, 0.89, 0.82), rough=(0.75, 1.0), bump=0.5, sat=0.0, bright=1.25))
    M['bronze'] = get('M_Bronze', lambda: J.plain('M_Bronze', (0.16, 0.12, 0.085), rough=0.33, metal=1.0))
    M['steel'] = get('M_Steel', lambda: J.plain('M_Steel', (0.55, 0.56, 0.57), rough=0.35, metal=1.0, noise_bump=0.1, noise_scale=60))
    M['rebar'] = get('M_RebarRust', lambda: J.plain('M_RebarRust', (0.24, 0.12, 0.07), rough=0.65, metal=0.6, noise_bump=0.3, noise_scale=200))
    M['glass'] = get('M_GlassExt', lambda: J.glass('M_GlassExt', tint=(0.86, 0.91, 0.91), rough=0.01))
    M['glass_bal'] = get('M_GlassBal', lambda: J.glass('M_GlassBal', tint=(0.9, 0.95, 0.94), rough=0.0))
    M['white'] = get('M_WhiteRender', lambda: J.plain('M_WhiteRender', (0.86, 0.85, 0.82), rough=0.65, noise_bump=0.05, noise_scale=30))
    M['yellow'] = get('M_CraneYellow', lambda: J.plain('M_CraneYellow', (0.92, 0.62, 0.04), rough=0.45, metal=0.2))
    M['navy'] = get('M_Hoarding', lambda: J.plain('M_Hoarding', (0.035, 0.06, 0.1), rough=0.45))
    M['hwhite'] = get('M_HoardWhite', lambda: J.plain('M_HoardWhite', (0.9, 0.9, 0.88), rough=0.4))
    M['gold'] = get('M_SignGold', lambda: J.plain('M_SignGold', (0.75, 0.6, 0.35), rough=0.35, metal=0.8))
    M['container'] = get('M_Container', lambda: J.plain('M_Container', (0.82, 0.83, 0.82), rough=0.5, metal=0.2))
    M['dark'] = get('M_DarkPanel', lambda: J.plain('M_DarkPanel', (0.03, 0.035, 0.04), rough=0.3))
    M['red'] = get('M_SprinklerRed', lambda: J.plain('M_SprinklerRed', (0.55, 0.04, 0.03), rough=0.35))
    M['pipe_black'] = get('M_PipeInsul', lambda: J.plain('M_PipeInsul', (0.03, 0.03, 0.03), rough=0.7))
    M['conduit'] = get('M_Conduit', lambda: J.plain('M_Conduit', (0.85, 0.42, 0.08), rough=0.45))
    M['pvc'] = get('M_PVC', lambda: J.plain('M_PVC', (0.82, 0.82, 0.8), rough=0.35))
    M['gypsum'] = get('M_Gypsum', lambda: mat_gypsum())
    M['ceil_paint'] = get('M_CeilPaint', lambda: J.plain('M_CeilPaint', (0.9, 0.89, 0.86), rough=0.8))
    M['film'] = get('M_Film', lambda: mat_film())
    M['dust'] = get('M_Dust', lambda: mat_dust())
    M['emit_warm'] = get('M_EmitWarm', lambda: J.emission('M_EmitWarm', J.kelvin(3000), 18.0))
    M['emit_cove'] = get('M_EmitCove', lambda: J.emission('M_EmitCove', J.kelvin(2900), 10.0))
    M['emit_room'] = get('M_EmitRoom', lambda: J.emission('M_EmitRoom', J.kelvin(2900), 2.2))
    M['curtain'] = get('M_Curtain', lambda: mat_curtain())
    M['wood_dark'] = get('M_WoodDark', lambda: J.pbr('M_WoodDark', 'mocha_oak_veneer', scale=1.6, tint=(0.8, 0.75, 0.7), rough=(0.35, 0.6), bump=0.2))
    M['art'] = get('M_Art', lambda: mat_art())
    return M

def mat_stone(name, tint):
    """Jordanian limestone cladding: 1.2 x 0.6 m panels, running bond, 6 mm joints, per-panel tone,
    micro-texture from Poly Haven beige_wall_001. Box-projected in object space."""
    m, nt, out = J._new_mat(name); L = nt.links
    b = J._bsdf(nt)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ma = nt.nodes.new('ShaderNodeMapping'); ma.inputs['Scale'].default_value = (1 / 2.4, 1 / 2.4, 1 / 1.2)
    mb = nt.nodes.new('ShaderNodeMapping'); mb.inputs['Scale'].default_value = (1 / 2.0, 1 / 2.0, 1 / 2.0)
    L.new(tc.outputs['Object'], ma.inputs['Vector']); L.new(tc.outputs['Object'], mb.inputs['Vector'])
    pdir = os.path.join(J.TEX, 'stone_panels')
    pc = J._img(nt, os.path.join(pdir, 'col.png'), True); pc.projection_blend = 0.05
    ph = J._img(nt, os.path.join(pdir, 'h.png'), True); ph.projection_blend = 0.05
    L.new(ma.outputs[0], pc.inputs['Vector']); L.new(ma.outputs[0], ph.inputs['Vector'])
    d = os.path.join(J.TEX, 'beige_wall_001')
    dif = J._img(nt, os.path.join(d, 'diff.jpg')); L.new(mb.outputs[0], dif.inputs['Vector'])
    hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.35; hs.inputs['Value'].default_value = 1.25
    L.new(dif.outputs['Color'], hs.inputs['Color'])
    m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs[0].default_value = 1.0
    L.new(hs.outputs['Color'], m1.inputs[6]); m1.inputs[7].default_value = (*tint, 1)
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs[0].default_value = 1.0
    L.new(m1.outputs[2], m2.inputs[6]); L.new(pc.outputs['Color'], m2.inputs[7])
    L.new(m2.outputs[2], b.inputs['Base Color'])
    rr = J._img(nt, os.path.join(d, 'rough.jpg'), True); L.new(mb.outputs[0], rr.inputs['Vector'])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.5; mr.inputs['To Max'].default_value = 0.8
    L.new(rr.outputs['Color'], mr.inputs['Value']); L.new(mr.outputs['Result'], b.inputs['Roughness'])
    nn = J._img(nt, os.path.join(d, 'nor.jpg'), True); L.new(mb.outputs[0], nn.inputs['Vector'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.5
    L.new(nn.outputs['Color'], nm.inputs['Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.8; bp.inputs['Distance'].default_value = 0.004
    L.new(ph.outputs['Color'], bp.inputs['Height']); L.new(nm.outputs['Normal'], bp.inputs['Normal']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    L.new(b.outputs['BSDF'], out.inputs['Surface']); m.diffuse_color = (*tint, 1)
    return m

def mat_cmu(name):
    """Concrete masonry units 400 x 200 mm with 10 mm joints, box-projected."""
    m, nt, out = J._new_mat(name); L = nt.links; b = J._bsdf(nt)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ma = nt.nodes.new('ShaderNodeMapping'); ma.inputs['Scale'].default_value = (1 / 0.8, 1 / 0.8, 1 / 0.4)
    mb = nt.nodes.new('ShaderNodeMapping'); mb.inputs['Scale'].default_value = (1 / 1.2, 1 / 1.2, 1 / 1.2)
    L.new(tc.outputs['Object'], ma.inputs['Vector']); L.new(tc.outputs['Object'], mb.inputs['Vector'])
    pdir = os.path.join(J.TEX, 'cmu')
    pc = J._img(nt, os.path.join(pdir, 'col.png'), True); pc.projection_blend = 0.05
    ph = J._img(nt, os.path.join(pdir, 'h.png'), True); ph.projection_blend = 0.05
    L.new(ma.outputs[0], pc.inputs['Vector']); L.new(ma.outputs[0], ph.inputs['Vector'])
    d = os.path.join(J.TEX, 'concrete_wall_008')
    dif = J._img(nt, os.path.join(d, 'diff.jpg')); L.new(mb.outputs[0], dif.inputs['Vector'])
    hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.2; hs.inputs['Value'].default_value = 1.1
    L.new(dif.outputs['Color'], hs.inputs['Color'])
    m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs[0].default_value = 1.0
    L.new(hs.outputs['Color'], m1.inputs[6]); L.new(pc.outputs['Color'], m1.inputs[7])
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs[0].default_value = 1.0
    L.new(m1.outputs[2], m2.inputs[6]); m2.inputs[7].default_value = (0.8, 0.79, 0.76, 1)
    L.new(m2.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.92
    nn = J._img(nt, os.path.join(d, 'nor.jpg'), True); L.new(mb.outputs[0], nn.inputs['Vector'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8; L.new(nn.outputs['Color'], nm.inputs['Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = 0.008
    L.new(ph.outputs['Color'], bp.inputs['Height']); L.new(nm.outputs['Normal'], bp.inputs['Normal']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    L.new(b.outputs['BSDF'], out.inputs['Surface']); m.diffuse_color = (0.6, 0.6, 0.58, 1)
    return m

def mat_floor(name):
    """Large-format honed marble tiles 1.2 x 0.6 m, fine joints, per-tile tone (flat XY projection)."""
    m, nt, out = J._new_mat(name); L = nt.links; b = J._bsdf(nt)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ma = nt.nodes.new('ShaderNodeMapping'); ma.inputs['Scale'].default_value = (1 / 2.4, 1 / 1.2, 1)
    mb = nt.nodes.new('ShaderNodeMapping'); mb.inputs['Scale'].default_value = (1 / 2.4, 1 / 2.4, 1)
    L.new(tc.outputs['Object'], ma.inputs['Vector']); L.new(tc.outputs['Object'], mb.inputs['Vector'])
    pdir = os.path.join(J.TEX, 'stone_panels')
    pc = J._img(nt, os.path.join(pdir, 'col.png'), True, proj='FLAT'); ph = J._img(nt, os.path.join(pdir, 'h.png'), True, proj='FLAT')
    L.new(ma.outputs[0], pc.inputs['Vector']); L.new(ma.outputs[0], ph.inputs['Vector'])
    d = os.path.join(J.TEX, 'marble_01')
    dif = J._img(nt, os.path.join(d, 'diff.jpg'), proj='FLAT'); L.new(mb.outputs[0], dif.inputs['Vector'])
    hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.45; hs.inputs['Value'].default_value = 1.15
    L.new(dif.outputs['Color'], hs.inputs['Color'])
    gm = nt.nodes.new('ShaderNodeGamma'); gm.inputs['Gamma'].default_value = 0.35
    L.new(pc.outputs['Color'], gm.inputs['Color'])
    m1 = nt.nodes.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs[0].default_value = 1.0
    L.new(hs.outputs['Color'], m1.inputs[6]); L.new(gm.outputs['Color'], m1.inputs[7])
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs[0].default_value = 1.0
    L.new(m1.outputs[2], m2.inputs[6]); m2.inputs[7].default_value = (0.97, 0.94, 0.9, 1)
    L.new(m2.outputs[2], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.14
    try: b.inputs['Coat Weight'].default_value = 0.25; b.inputs['Coat Roughness'].default_value = 0.06
    except Exception: pass
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.002
    L.new(ph.outputs['Color'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    L.new(b.outputs['BSDF'], out.inputs['Surface']); m.diffuse_color = (0.9, 0.88, 0.85, 1)
    return m

def mat_gypsum():
    """Unpainted gypsum board: off-white with taped joints (1.2 x 2.4 m sheets)."""
    m, nt, out = J._new_mat('M_Gypsum'); L = nt.links
    b = J._bsdf(nt); b.inputs['Roughness'].default_value = 0.85
    tc = nt.nodes.new('ShaderNodeTexCoord'); br = nt.nodes.new('ShaderNodeTexBrick')
    br.offset = 0.0; br.squash = 1.0
    br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.03
    br.inputs['Brick Width'].default_value = 2.4; br.inputs['Row Height'].default_value = 1.2
    br.inputs['Color1'].default_value = (0.74, 0.75, 0.73, 1); br.inputs['Color2'].default_value = (0.71, 0.72, 0.7, 1)
    br.inputs['Mortar'].default_value = (0.86, 0.86, 0.84, 1)
    L.new(tc.outputs['Object'], br.inputs['Vector']); L.new(br.outputs['Color'], b.inputs['Base Color'])
    L.new(b.outputs['BSDF'], out.inputs['Surface']); m.diffuse_color = (0.75, 0.75, 0.73, 1)
    return m

def mat_film():
    """Blue protective film on new glazing (translucent)."""
    m, nt, out = J._new_mat('M_Film'); L = nt.links
    b = J._bsdf(nt); b.inputs['Base Color'].default_value = (0.25, 0.45, 0.75, 1); b.inputs['Roughness'].default_value = 0.35
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.7
    L.new(b.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def mat_dust():
    """Construction dust film over a finished floor (patchy)."""
    m, nt, out = J._new_mat('M_Dust'); L = nt.links
    b = J._bsdf(nt); b.inputs['Base Color'].default_value = (0.62, 0.6, 0.56, 1); b.inputs['Roughness'].default_value = 0.95
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.6; nz.inputs['Detail'].default_value = 6
    cr = nt.nodes.new('ShaderNodeMapRange'); cr.inputs['From Min'].default_value = 0.35; cr.inputs['From Max'].default_value = 0.7
    cr.inputs['To Min'].default_value = 0.15; cr.inputs['To Max'].default_value = 0.75
    L.new(tc.outputs['Object'], nz.inputs['Vector']); L.new(nz.outputs['Fac'], cr.inputs['Value'])
    mx = nt.nodes.new('ShaderNodeMixShader'); L.new(cr.outputs['Result'], mx.inputs[0])
    L.new(tr.outputs[0], mx.inputs[1]); L.new(b.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def mat_curtain():
    m, nt, out = J._new_mat('M_Curtain'); L = nt.links
    b = J._bsdf(nt); b.inputs['Base Color'].default_value = (0.92, 0.9, 0.86, 1); b.inputs['Roughness'].default_value = 0.9
    try: b.inputs['Subsurface Weight'].default_value = 0.0
    except Exception: pass
    tl = nt.nodes.new('ShaderNodeBsdfTranslucent'); tl.inputs['Color'].default_value = (0.95, 0.92, 0.85, 1)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    m1 = nt.nodes.new('ShaderNodeMixShader'); m1.inputs[0].default_value = 0.45
    L.new(b.outputs[0], m1.inputs[1]); L.new(tl.outputs[0], m1.inputs[2])
    m2 = nt.nodes.new('ShaderNodeMixShader'); m2.inputs[0].default_value = 0.35
    L.new(m1.outputs[0], m2.inputs[1]); L.new(tr.outputs[0], m2.inputs[2]); L.new(m2.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def mat_art():
    """Abstract canvas: soft warm gradients (original, procedural)."""
    m, nt, out = J._new_mat('M_Art'); L = nt.links
    b = J._bsdf(nt); b.inputs['Roughness'].default_value = 0.9
    tc = nt.nodes.new('ShaderNodeTexCoord'); w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = 0.9
    w.inputs['Distortion'].default_value = 6.0; w.inputs['Detail'].default_value = 3
    ramp = nt.nodes.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
    e[0].color = (0.78, 0.66, 0.52, 1); e[1].color = (0.93, 0.89, 0.82, 1)
    el = e.new(0.55); el.color = (0.45, 0.33, 0.24, 1)
    L.new(tc.outputs['Object'], w.inputs['Vector']); L.new(w.outputs['Fac'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    L.new(b.outputs['BSDF'], out.inputs['Surface'])
    return m

# ------------------------------------------------------------------ stage switching
STATE = {"ext": 6, "int": 1, "dusk": False}

def _vis(ob, ext, it, dusk):
    o = ob
    while o is not None and "ext" not in o: o = o.parent
    if o is None: return True
    a, b = o["ext"]; c, d = o["int"]; dk = o.get("dusk", 0)
    if not (a <= ext < b and c <= it < d): return False
    if dk == 1 and dusk: return False
    if dk == 2 and not dusk: return False
    return True

def set_state(ext=None, it=None, dusk=None):
    if ext is not None: STATE["ext"] = ext
    if it is not None: STATE["int"] = it
    if dusk is not None: STATE["dusk"] = dusk
    e, i, d = STATE["ext"], STATE["int"], STATE["dusk"]
    root = bpy.data.collections.get("MASTER")
    if not root: return
    for ob in list(root.all_objects):
        v = _vis(ob, e, i, d)
        ob.hide_render = not v; ob.hide_viewport = not v
    w = bpy.context.scene.world
    if w and w.node_tree:
        env = w.node_tree.nodes.get('HDRI')
        img = bpy.data.images.get('DUSK_HDR' if d else 'DAY_HDR')
        if env and img: env.image = img
        bg = w.node_tree.nodes.get('BG')
        if bg: bg.inputs['Strength'].default_value = 0.55 if d else 1.0
        mp = w.node_tree.nodes.get('HDRI_Map')
        if mp: mp.inputs['Rotation'].default_value[2] = w.get('rot_dusk' if d else 'rot_day', 0.0)
    sun = bpy.data.objects.get('SUN')
    if sun: sun.hide_render = bool(d); sun.hide_viewport = bool(d)
    return dict(STATE)

bpy.app.driver_namespace['jm_set_state'] = set_state


# ------------------------------------------------------------------ timer-based render queue (MCP calls return immediately)
def queue(jobs, tag, then=None):
    import json, time
    sc = bpy.context.scene; O = bpy.data.objects; st = {"i": 0, "log": []}
    logp = os.path.join(ROOT, 'previews', f'{tag}_log.json')
    def step():
        if st["i"] >= len(jobs):
            json.dump(st["log"] + [["DONE", 0]], open(logp, 'w'))
            if then: bpy.app.timers.register(then, first_interval=1.0)
            return None
        j = jobs[st["i"]]; st["i"] += 1; t = time.time()
        try:
            set_state(ext=j.get('ext', 6), it=j.get('int', 1), dusk=j.get('dusk', False))
            sc.camera = O[j['cam']]; sc.frame_set(j.get('frame', 1))
            if 'exp' in j: sc.view_settings.exposure = j['exp']
            rx, ry = j.get('res', (1920, 1080)); sc.render.resolution_x = rx; sc.render.resolution_y = ry
            sc.render.resolution_percentage = j.get('pct', 100); sc.cycles.samples = j.get('spp', 32)
            fmt = j.get('fmt', 'JPEG'); sc.render.image_settings.file_format = fmt
            if fmt == 'JPEG': sc.render.image_settings.quality = j.get('q', 90)
            sc.render.filepath = j['out']; bpy.ops.render.render(write_still=True)
            st["log"].append([os.path.basename(j['out']), round(time.time() - t, 1)])
        except Exception as e:
            st["log"].append([j['out'], "ERR " + repr(e)])
        json.dump(st["log"], open(logp, 'w')); return 0.2
    bpy.app.timers.register(step, first_interval=0.5)
bpy.app.driver_namespace['jm_queue'] = queue
