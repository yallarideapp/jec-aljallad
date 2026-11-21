"""JEC POC — Blender helper library (materials, geometry, imports, lights).
Every mesh is built in world coordinates with its origin at (0,0,0), so box-projected
textures stay continuous across objects."""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__))  # this script's folder (was ~/Desktop/JEC_AlJallad_3D/POC)
TEX = os.path.join(ROOT, 'assets', 'tex')
MOD = os.path.join(ROOT, 'assets', 'models')
HDRI = os.path.join(ROOT, 'assets', 'hdri')

# ---------------------------------------------------------------- collections
def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c

# ---------------------------------------------------------------- materials
def _new_mat(name):
    m = bpy.data.materials.get(name)
    if m: bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (900, 0)
    return m, nt, out

def _bsdf(nt):
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.location = (600, 0); return b

def _img(nt, path, noncolor=False, proj='BOX'):
    n = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.get(os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path))
    if not img:
        img = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        try: img.colorspace_settings.name = 'Non-Color'
        except Exception: pass
    n.image = img; n.projection = proj
    if proj == 'BOX': n.projection_blend = 0.25
    return n

def pbr(name, tex, scale=1.0, tint=(1, 1, 1), rough=(0.0, 1.0), bump=1.0, metal=0.0, rot=0.0, coat=0.0, sat=1.0, bright=1.0):
    """Poly Haven texture set, box-projected in object (=world) space.
    scale = metres covered by one texture tile. rough = (min,max) remap."""
    m, nt, out = _new_mat(name)
    b = _bsdf(nt); L = nt.links
    tc = nt.nodes.new('ShaderNodeTexCoord'); tc.location = (-900, 0)
    mp = nt.nodes.new('ShaderNodeMapping'); mp.location = (-700, 0)
    mp.inputs['Scale'].default_value = (1 / scale, 1 / scale, 1 / scale)
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    d = os.path.join(TEX, tex)
    dif = _img(nt, os.path.join(d, 'diff.jpg')); dif.location = (-400, 300)
    L.new(mp.outputs['Vector'], dif.inputs['Vector'])
    hsv = nt.nodes.new('ShaderNodeHueSaturation'); hsv.location = (-100, 300)
    hsv.inputs['Saturation'].default_value = sat; hsv.inputs['Value'].default_value = bright
    L.new(dif.outputs['Color'], hsv.inputs['Color'])
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.location = (150, 300)
    mul.inputs[0].default_value = 1.0
    _set(mul, 'A', hsv.outputs['Color'], L); mul.inputs[7].default_value = (*tint, 1)
    L.new(mul.outputs[2], b.inputs['Base Color'])
    if os.path.exists(os.path.join(d, 'rough.jpg')):
        r = _img(nt, os.path.join(d, 'rough.jpg'), True); r.location = (-400, 0)
        L.new(mp.outputs['Vector'], r.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.location = (150, 0)
        mr.inputs['To Min'].default_value = rough[0]; mr.inputs['To Max'].default_value = rough[1]
        L.new(r.outputs['Color'], mr.inputs['Value']); L.new(mr.outputs['Result'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = (rough[0] + rough[1]) / 2
    if os.path.exists(os.path.join(d, 'nor.jpg')) and bump > 0:
        n = _img(nt, os.path.join(d, 'nor.jpg'), True); n.location = (-400, -300)
        L.new(mp.outputs['Vector'], n.inputs['Vector'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (150, -300); nm.inputs['Strength'].default_value = bump
        L.new(n.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.08
    L.new(b.outputs['BSDF'], out.inputs['Surface'])
    m.diffuse_color = (*[c * 0.8 for c in tint], 1)
    return m

def _set(mix, which, sock, L):
    # Mix node (RGBA): inputs 6=A color, 7=B color
    L.new(sock, mix.inputs[6] if which == 'A' else mix.inputs[7])

def plain(name, color, rough=0.5, metal=0.0, spec=0.5, emit=None, es=0.0, sheen=0.0, coat=0.0, noise_bump=0.0, noise_scale=40.0):
    m, nt, out = _new_mat(name); b = _bsdf(nt); L = nt.links
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    try: b.inputs['Specular IOR Level'].default_value = spec
    except Exception: pass
    if sheen: b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = 0.4
    if coat: b.inputs['Coat Weight'].default_value = coat
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    if noise_bump:
        tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = noise_scale; nz.inputs['Detail'].default_value = 8
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = noise_bump; bp.inputs['Distance'].default_value = 0.002
        L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    L.new(b.outputs['BSDF'], out.inputs['Surface'])
    m.diffuse_color = (*color, 1)
    return m

def glass(name, tint=(0.9, 0.95, 0.95), rough=0.0, dark=False):
    """Architectural glazing: real glass for camera rays, transparent for shadow rays."""
    m, nt, out = _new_mat(name); L = nt.links
    g = nt.nodes.new('ShaderNodeBsdfPrincipled')
    g.inputs['Base Color'].default_value = (*tint, 1); g.inputs['Roughness'].default_value = rough
    g.inputs['Transmission Weight'].default_value = 1.0; g.inputs['IOR'].default_value = 1.45
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (*tint, 1)
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMixShader')
    L.new(lp.outputs['Is Shadow Ray'], mx.inputs[0]); L.new(g.outputs['BSDF'], mx.inputs[1]); L.new(tr.outputs['BSDF'], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs['Surface'])
    m.diffuse_color = (*tint, 0.3)
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

def emission(name, color, strength):
    m, nt, out = _new_mat(name)
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (*color, 1); e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], out.inputs['Surface']); m.diffuse_color = (*color, 1)
    return m

def ghost(name, color=(0.75, 0.82, 0.9), alpha=0.18):
    m, nt, out = _new_mat(name); L = nt.links
    b = _bsdf(nt); b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = 0.4
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = alpha
    L.new(tr.outputs[0], mx.inputs[1]); L.new(b.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
    try: m.surface_render_method = 'BLENDED'
    except Exception: pass
    return m

# ---------------------------------------------------------------- geometry
def _cuboid(bm, a, b):
    x0, y0, z0 = [min(a[i], b[i]) for i in range(3)]; x1, y1, z1 = [max(a[i], b[i]) for i in range(3)]
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    v = [bm.verts.new(p) for p in P]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([v[i] for i in f])

def boxes(name, specs, mat, col, bevel=0.0, seg=2, smooth=False):
    """specs: list of (x0,y0,z0,x1,y1,z1). One object, origin at world 0."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for s in specs: _cuboid(bm, s[:3], s[3:])
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if mat: me.materials.append(mat)
    if bevel:
        md = ob.modifiers.new('Bevel', 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
        md.harden_normals = True
        try: me.shade_smooth()
        except Exception: pass
    return ob

def box(name, a, b, mat, col, **kw):
    return boxes(name, [(*a, *b)], mat, col, **kw)

def cyl(name, p0, p1, r, mat, col, seg=16):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length,
                          matrix=Matrix.Translation(Vector((0, 0, d.length / 2))))
    q = d.to_track_quat('Z', 'Y')
    bmesh.ops.transform(bm, matrix=Matrix.Translation(p0) @ q.to_matrix().to_4x4(), verts=bm.verts)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if mat: me.materials.append(mat)
    try: me.shade_smooth()
    except Exception: pass
    return ob

def join(name, objs):
    objs = [o for o in objs if o]
    if not objs: return None
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name; return objs[0]

# ---------------------------------------------------------------- imports
def gltf(asset, col, loc=(0, 0, 0), rot=0.0, scale=1.0, name=None):
    """Import a Poly Haven glTF under an empty, placed at loc / rot (deg about Z)."""
    path = os.path.join(MOD, asset, asset + '.gltf')
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name or asset, None); col.objects.link(root)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
        if o.parent is None: o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, math.radians(rot)); root.scale = (scale,) * 3
    return root

def dupe(root, col, loc, rot=0.0, scale=1.0, name=None):
    """Linked duplicate of an imported hierarchy (shares meshes)."""
    def cp(o, parent):
        n = o.copy(); col.objects.link(n); n.parent = parent
        for ch in o.children: cp(ch, n)
        return n
    r = cp(root, None); r.location = loc; r.rotation_euler = (0, 0, math.radians(rot)); r.scale = (scale,) * 3
    if name: r.name = name
    return r

# ---------------------------------------------------------------- lights
def kelvin(k):
    k = k / 100.0
    r = 255 if k <= 66 else 329.698727446 * ((k - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(k) - 161.1195681661 if k <= 66 else 288.1221695283 * ((k - 60) ** -0.0755148492)
    b = 255 if k >= 66 else (0 if k <= 19 else 138.5177312231 * math.log(k - 10) - 305.0447927307)
    return tuple(max(0, min(255, c)) / 255 for c in (r, g, b))

def light(name, kind, loc, col, energy, color=3000, size=0.1, size_y=None, rot=(0, 0, 0), spot=None, blend=0.3):
    l = bpy.data.lights.new(name, kind); l.energy = energy
    l.color = kelvin(color) if isinstance(color, (int, float)) else color
    if kind == 'AREA':
        l.shape = 'RECTANGLE' if size_y else 'SQUARE'; l.size = size
        if size_y: l.size_y = size_y
    elif kind in ('POINT', 'SPOT'):
        l.shadow_soft_size = size
    if kind == 'SPOT' and spot: l.spot_size = math.radians(spot); l.spot_blend = blend
    o = bpy.data.objects.new(name, l); col.objects.link(o); o.location = loc; o.rotation_euler = rot
    return o

def aim(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
