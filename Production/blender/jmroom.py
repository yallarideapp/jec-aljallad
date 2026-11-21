"""Ground-floor room (x 3..15, y -9..-1) and its nine fit-out stages; dusk interiors; world, lights, cameras."""
import bpy, bmesh, math, os, sys, importlib, random
from mathutils import Vector, Matrix
ROOT = os.path.dirname(os.path.abspath(__file__))  # this script's folder (was ~/Desktop/JEC_AlJallad_3D/POC)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import jecpoc as J
import jecmaster as JM
from jecmaster import CX, CY, LV, SL, B, C, clear, tag, wall, frame_specs, glazing_run, cyls, mesh_from_bm

F0 = LV[0]            # raw slab top 0.45
CEIL = 3.95           # underside of the suspended ceiling (clear height 3.5 m)
SOFF = LV[1] - SL     # slab soffit 5.0
BEAMB = LV[1] - 0.65  # beam bottom 4.6
RX0, RX1, RY0, RY1 = 3.0, 15.0, -9.0, -1.0
E6 = (6, 99)

def build_room():
    M = JM.mats(); c = clear("M_Room")
    # ---------------------------------------------------------------- I2 partitions (blockwork)
    door_n = (13.3, 14.3, F0, F0 + 2.4)            # door in the north wall to the private wing
    door_w = (-2.75, -1.55, F0, F0 + 2.4)          # entry door in the west wall (from the lobby)
    nw = []
    nw += wall('y', -1.1, -0.9, 3.1, 8.8, F0, SOFF, [door_n] if False else [])
    nw += wall('y', -1.1, -0.9, 8.8, 9.2, F0, BEAMB, [])
    nw += wall('y', -1.1, -0.9, 9.2, 14.9, F0, SOFF, [door_n])
    ww = wall('x', 2.9, 3.1, -8.7, -1.1, F0, BEAMB, [door_w])
    B("R_Block", nw + ww, M['block'], c, ext=E6, int_=(2, 99))
    # lintels over the doors (precast concrete)
    B("R_Lintels", [(13.15, -1.1, F0 + 2.4, 14.45, -0.9, F0 + 2.6), (2.9, -2.9, F0 + 2.4, 3.1, -1.4, F0 + 2.6)], M['conc'], c, ext=E6, int_=(2, 4))
    # ---------------------------------------------------------------- I1 site state: blocks waiting, cement, work bulbs
    R = random.Random(11)
    pal = []
    for i, (x, y) in enumerate(((11.6, -2.3), (13.0, -2.3))):
        pal.append((x, y, F0, x + 1.2, y + 1.0, F0 + 0.12))
        pal.append((x + 0.03, y + 0.03, F0 + 0.12, x + 1.17, y + 0.97, F0 + 0.12 + 0.2 * (4 + i)))
    B("R_BlockPallets", pal, M['block'], c, ext=E6, int_=(1, 2))
    offc = [(4.2 + R.uniform(0, 4), -1.6 - R.uniform(0, 0.4), F0, 0, 0, 0) for _ in range(5)]
    B("R_Offcuts", [(x, y, z, x + 0.4, y + 0.2, z + 0.2) for (x, y, z, *_r) in offc], M['block'], c, ext=E6, int_=(2, 3))
    bulbs, cables = [], []
    for (x, y) in ((6.2, -5.4), (11.4, -5.6), (12.8, -8.0)):
        cables.append(((x, y, SOFF), (x, y, 3.25)))
        bulbs.append((x, y))
    ob = cyls("R_BulbCables", cables, 0.006, M['dark'], c, seg=4); tag(ob, ext=E6, int_=(1, 7))
    for i, (x, y) in enumerate(bulbs):
        s = J.cyl(f"R_Bulb{i}", (x, y, 3.08), (x, y, 3.25), 0.045, M['emit_warm'], c, seg=10); tag(s, ext=E6, int_=(1, 7))
        L = J.light(f"R_BulbLight{i}", 'POINT', (x, y, 3.1), c, 90, color=3100, size=0.05); tag(L, ext=E6, int_=(1, 7))
    for i, (x, y) in enumerate(((-1.4, -6.3), (0.6, -1.4), (-5.6, -3.6))):
        ob = cyls(f"R_LobbyCable{i}", [((x, y, SOFF), (x, y, 3.25))], 0.006, M['dark'], c, seg=4); tag(ob, ext=E6, int_=(1, 9))
        s_ = J.cyl(f"R_LobbyBulb{i}", (x, y, 3.08), (x, y, 3.25), 0.045, M['emit_warm'], c, seg=10); tag(s_, ext=E6, int_=(1, 9))
        L = J.light(f"R_LobbyLight{i}", 'POINT', (x, y, 3.1), c, 140, color=3100, size=0.05); tag(L, ext=E6, int_=(1, 9))
    # ---------------------------------------------------------------- I3 MEP rough-in
    # HVAC: supply duct along the room, flexible branches to linear diffuser plenums at the facade
    B("R_Duct", [(3.0, -6.15, 4.12, 14.4, -5.55, 4.48)], M['steel'], c, ext=E6, int_=(3, 99))
    B("R_DuctJoints", [(x - 0.03, -6.2, 4.08, x + 0.03, -5.5, 4.52) for x in (4.2, 5.4, 6.6, 7.8, 9.6, 10.8, 12.0, 13.2)], M['steel'], c, ext=E6, int_=(3, 99))
    B("R_Plenums", [(4.2, -8.45, 3.98, 8.0, -7.95, 4.22), (10.0, -8.45, 3.98, 13.8, -7.95, 4.22), (11.0, -2.0, 3.98, 13.0, -1.6, 4.2)], M['steel'], c, ext=E6, int_=(3, 99))
    fl = [((6.1, -6.15, 4.25), (6.1, -7.95, 4.12)), ((11.9, -6.15, 4.25), (11.9, -7.95, 4.12)), ((12.0, -5.55, 4.25), (12.0, -2.0, 4.12))]
    ob = cyls("R_FlexDucts", fl, 0.13, M['steel'], c, seg=14); tag(ob, ext=E6, int_=(3, 99))
    # fire sprinklers: main + branches above the ceiling, drops to pendent heads just below it
    spr = [((3.0, -4.35, 4.5), (14.8, -4.35, 4.5))]
    for x in (5.0, 7.6, 11.0, 13.9):
        spr.append(((x, -8.5, 4.42), (x, -1.4, 4.42)))
    ob = cyls("R_SprPipes", spr, 0.035, M['red'], c, seg=10); tag(ob, ext=E6, int_=(3, 99))
    drops, heads = [], []
    for x in (5.0, 7.6, 11.0, 13.9):
        for y in (-7.3, -2.6):
            drops.append(((x, y, 4.42), (x, y, 3.97)))
            heads.append(((x, y, 3.97), (x, y, 3.915)))
    ob = cyls("R_SprDrops", drops, 0.016, M['red'], c, seg=8); tag(ob, ext=E6, int_=(3, 99))
    ob = cyls("R_SprHeads", heads, 0.022, M['steel'], c, seg=10); tag(ob, ext=E6, int_=(3, 99))
    # chilled water to the fan-coil unit, condensate drain, plumbing from the floor above
    ob = cyls("R_CHW", [((3.0, -1.55, 4.36), (11.0, -1.55, 4.36)), ((3.0, -1.75, 4.36), (11.0, -1.75, 4.36))], 0.055, M['pipe_black'], c, seg=12); tag(ob, ext=E6, int_=(3, 99))
    B("R_FCU", [(11.0, -2.1, 4.1, 13.2, -1.3, 4.52)], M['container'], c, ext=E6, int_=(3, 99), bevel=0.01)
    ob = cyls("R_Drain", [((3.0, -7.0, 4.56), (14.8, -7.0, 4.5)), ((8.2, -7.0, 4.56), (8.2, -7.0, SOFF))], 0.055, M['pvc'], c, seg=12); tag(ob, ext=E6, int_=(3, 99))
    ob = cyls("R_Water", [((3.0, -6.8, 4.3), (14.8, -6.8, 4.3)), ((3.0, -6.65, 4.3), (14.8, -6.65, 4.3))], 0.016, M['pvc'], c, seg=8); tag(ob, ext=E6, int_=(3, 99))
    # power: cable tray + cables in the void, conduits down the walls to back boxes
    B("R_Tray", [(3.0, -1.5, 4.55, 14.8, -1.2, 4.58), (3.0, -1.5, 4.55, 14.8, -1.48, 4.64), (3.0, -1.22, 4.55, 14.8, -1.2, 4.64)], M['steel'], c, ext=E6, int_=(3, 99))
    ob = cyls("R_Cables", [((3.0, -1.35 + i * 0.04, 4.6), (14.8, -1.35 + i * 0.04, 4.6)) for i in range(4)], 0.012, M['dark'], c, seg=5); tag(ob, ext=E6, int_=(3, 99))
    boxes_n = [(4.4, 0.75), (6.2, 0.75), (8.2, 0.75), (10.2, 0.4), (11.15, 1.3), (12.8, 0.4), (13.0, 1.35)]
    cond = []
    for (x, z) in boxes_n: cond.append(((x, -1.115, z + 0.05), (x, -1.115, SOFF)))
    cond += [((3.115, -3.2, 1.4), (3.115, -3.2, BEAMB))]
    ob = cyls("R_Conduits", cond, 0.013, M['conduit'], c, seg=6); tag(ob, ext=E6, int_=(3, 4))
    bx = [(x - 0.04, -1.12, z - 0.04, x + 0.04, -1.1, z + 0.04) for (x, z) in boxes_n] + [(3.1, -3.24, 1.36, 3.12, -3.16, 1.44)]
    B("R_BackBoxes", bx, M['container'], c, ext=E6, int_=(3, 7))
    # ---------------------------------------------------------------- I4 plaster (walls, exposed columns) — thin, so nothing changes size
    def wall_skin(name, t0, t1, mat, st):
        sp = []
        sp += wall('y', t0, t1, 3.115, 8.8, F0, SOFF, [])
        sp += wall('y', t0, t1, 8.8, 9.2, F0, BEAMB, [])
        sp += wall('y', t0, t1, 9.2, 14.885, F0, SOFF, [door_n])
        return B(name, sp, mat, c, ext=E6, int_=st)
    wall_skin("R_PlasterN", -1.115, -1.1, M['plaster'], (4, 7))
    wall_skin("R_PaintN", -1.117, -1.1, M['paint'], (7, 99))
    ww_sk = wall('x', 3.1, 3.115, -8.7, -1.115, F0, BEAMB, [door_w])
    B("R_PlasterW", ww_sk, M['plaster'], c, ext=E6, int_=(4, 7))
    B("R_PaintW", [(a, b_, z0, d + 0.002, e, f) for (a, b_, z0, d, e, f) in ww_sk], M['paint'], c, ext=E6, int_=(7, 99))
    colskin = [(8.685, -3.315, F0, 9.315, -2.685, BEAMB), (8.685, -9.0, F0, 9.315, -8.685, BEAMB),
               (14.685, -3.315, F0, 15.0, -2.685, BEAMB), (14.685, -9.0, F0, 15.0, -8.685, BEAMB), (3.1, -9.0, F0, 3.315, -8.685, BEAMB)]
    B("R_PlasterCols", colskin, M['plaster'], c, ext=E6, int_=(4, 7))
    B("R_PaintCols", [(a - 0.002, b_ - 0.002, z0, d + 0.002, e + 0.002, f) for (a, b_, z0, d, e, f) in colskin], M['paint'], c, ext=E6, int_=(7, 99))
    # ---------------------------------------------------------------- I5 ceiling system: hangers + gypsum board, slots for lights and diffusers
    hang = []
    for x in [3.6 + i * 1.2 for i in range(10)]:
        for y in [-8.4 + j * 1.2 for j in range(7)]:
            if abs(x - 9) < 0.5 and abs(y + 3) < 0.5: continue
            hang.append(((x, y, CEIL + 0.03), (x, y, BEAMB if abs(y + 3) < 0.4 or abs(y + 9) < 0.4 else SOFF)))
    ob = cyls("R_Hangers", hang, 0.004, M['steel'], c, seg=4); tag(ob, ext=E6, int_=(5, 99))
    ceil_specs = []
    # main board with a 0.12 shadow gap along the north wall (LED cove at I7) and holes for the diffuser slots
    holes = [(4.2, 8.0, -8.45, -8.3), (10.0, 13.8, -8.45, -8.3)]
    x_cuts = [3.1, 4.2, 8.0, 10.0, 13.8, 14.9]
    for x0, x1 in zip(x_cuts[:-1], x_cuts[1:]):
        hs = [h for h in holes if h[0] <= (x0 + x1) / 2 <= h[1]]
        ys = [(-8.97, -1.24)]
        for h in hs:
            ys = [(-8.97, h[2]), (h[3], -1.24)]
        for y0, y1 in ys: ceil_specs.append((x0, y0, CEIL, x1, y1, CEIL + 0.013))
    ceil_specs = [s for s in ceil_specs if not (s[0] < 9.0 < s[3] and s[1] < -3.0 < s[4])] + \
                 [s2 for s in ceil_specs if (s[0] < 9.0 < s[3] and s[1] < -3.0 < s[4]) for s2 in
                  [(s[0], s[1], s[2], 8.685, s[4], s[5]), (9.315, s[1], s[2], s[3], s[4], s[5]), (8.685, s[1], s[2], 9.315, -3.315, s[5]), (8.685, -2.685, s[2], 9.315, s[4], s[5])]]
    B("R_CeilBoard", ceil_specs, M['gypsum'], c, ext=E6, int_=(5, 7))
    B("R_CeilPaint", ceil_specs, M['ceil_paint'], c, ext=E6, int_=(7, 99))
    B("R_CoveBox", [(3.1, -1.24, CEIL - 0.12, 14.885, -1.115, CEIL + 0.013)], M['gypsum'], c, ext=E6, int_=(5, 7))
    B("R_CovePaint", [(3.1, -1.24, CEIL - 0.12, 14.885, -1.115, CEIL + 0.013)], M['ceil_paint'], c, ext=E6, int_=(7, 99))
    B("R_DiffSlots", [(4.2, -8.45, CEIL - 0.01, 8.0, -8.3, CEIL + 0.01), (10.0, -8.45, CEIL - 0.01, 13.8, -8.3, CEIL + 0.01)], M['dark'], c, ext=E6, int_=(5, 99))
    # ---------------------------------------------------------------- I6 floor + wall finishes
    floor = [(3.1, -8.97, F0, 14.97, -1.115, F0 + 0.025)]
    B("R_FloorTile", floor, M['tile'], c, ext=E6, int_=(6, 99))
    B("R_Dust", [(3.1, -8.97, F0 + 0.0255, 14.97, -1.115, F0 + 0.026)], M['dust'], c, ext=E6, int_=(6, 8))
    B("R_Feature", [(9.4, -1.148, F0 + 0.025, 12.9, -1.115, CEIL)], M['feature'], c, ext=E6, int_=(6, 99))
    sk = [(3.115, -1.13, F0 + 0.025, 9.4, -1.115, F0 + 0.1), (12.9, -1.13, F0 + 0.025, 13.3, -1.115, F0 + 0.1), (14.3, -1.13, F0 + 0.025, 14.885, -1.115, F0 + 0.1),
          (3.115, -8.97, F0 + 0.025, 3.13, -2.75, F0 + 0.1), (3.115, -1.55, F0 + 0.025, 3.13, -1.13, F0 + 0.1)]
    B("R_Skirting", sk, M['bronze'], c, ext=E6, int_=(6, 99))
    # ---------------------------------------------------------------- I7 paint, doors, lighting, fixtures
    df = frame_specs('y', -1.13, 13.3, 14.3, F0 + 0.025, F0 + 2.4, w=0.07, d=0.06)
    B("R_DoorFrameN", df, M['oak'], c, ext=E6, int_=(7, 99))
    B("R_DoorLeafN", [(13.37, -1.06, F0 + 0.03, 14.23, -1.02, F0 + 2.33)], M['oak'], c, ext=E6, int_=(7, 99))
    B("R_DoorHandle", [(14.08, -1.13, F0 + 1.02, 14.2, -1.11, F0 + 1.05)], M['bronze'], c, ext=E6, int_=(7, 99))
    B("R_DoorW", [(3.03, -2.72, F0 + 0.03, 3.07, -1.58, F0 + 2.33)], M['oak'], c, ext=E6, int_=(7, 99))
    plates = [(x - 0.045, -1.122, z - 0.045, x + 0.045, -1.115, z + 0.045) for (x, z) in boxes_n if not (9.4 < x < 12.9)]
    plates += [(x - 0.045, -1.152, z - 0.045, x + 0.045, -1.148, z + 0.045) for (x, z) in boxes_n if 9.4 < x < 12.9]
    B("R_Plates", plates, M['hwhite'], c, ext=E6, int_=(7, 99))
    dl = [(x, y) for x in (5.2, 7.2, 11.0, 13.0) for y in (-7.6, -5.0, -2.8)]
    rings, ems = [], []
    for i, (x, y) in enumerate(dl):
        ob = J.cyl(f"R_DL{i}", (x, y, CEIL - 0.004), (x, y, CEIL + 0.002), 0.055, M['emit_warm'], c, seg=20); tag(ob, ext=E6, int_=(7, 99))
        L = J.light(f"R_DLLight{i}", 'SPOT', (x, y, CEIL - 0.02), c, 32, color=3000, size=0.03, spot=70, blend=0.6); tag(L, ext=E6, int_=(7, 99))
    B("R_CoveLED", [(3.2, -1.2, CEIL - 0.11, 14.8, -1.17, CEIL - 0.1)], M['emit_cove'], c, ext=E6, int_=(7, 99))
    cl = J.light("R_CoveLight", 'AREA', (9.0, -1.3, CEIL - 0.14), c, 260, color=2900, size=11.4, size_y=0.06, rot=(math.radians(60), 0, 0)); tag(cl, ext=E6, int_=(7, 99))
    B("R_FeatureLED", [(9.36, -1.16, F0 + 0.03, 9.4, -1.12, CEIL - 0.02), (12.9, -1.16, F0 + 0.03, 12.94, -1.12, CEIL - 0.02)], M['emit_cove'], c, ext=E6, int_=(7, 99))
    B("R_CurtainSlot", [(3.2, -8.97, CEIL - 0.005, 14.9, -8.82, CEIL + 0.005)], M['dark'], c, ext=E6, int_=(5, 99))
    # painter's ladder and bucket only while painting
    bk = J.cyl("R_PaintBucket", (6.9, -1.6, F0 + 0.025), (6.9, -1.6, F0 + 0.38), 0.15, M['hwhite'], c, seg=20); tag(bk, ext=E6, int_=(7, 8))
    ldr = os.path.join(J.MOD, 'ladder_sectioned_01', 'ladder_sectioned_01.gltf')
    if os.path.exists(ldr):
        r = J.gltf('ladder_sectioned_01', c, loc=(7.6, -1.45, F0 + 0.025), rot=0, scale=1.0, name="R_Ladder"); tag(r, ext=E6, int_=(7, 8))
    # protective film on the new glazing until the final clean
    film = [(3.4, -8.975, F0 + 0.05, 8.6, -8.97, 4.55), (9.4, -8.975, F0 + 0.05, 14.6, -8.97, 4.55),
            (15.07, -8.6, F0 + 0.05, 15.075, -3.4, 4.55), (15.07, -2.6, F0 + 0.05, 15.075, -1.05, 4.55)]
    B("R_Film", film, M['film'], c, ext=E6, int_=(1, 8))
    # east glazing mullions (inside the two openings either side of column 15,-3)
    mul = [(15.04, y - 0.03, F0, 15.16, y + 0.03, BEAMB) for y in (-7.25, -5.85, -4.45, -1.85)]
    B("R_EastMullions", mul, M['bronze'], c, ext=(5, 99))
    B("R_EastColClad", [(15.0, -3.34, F0, 15.34, -2.66, LV[1] - SL)], M['stone'], c, ext=(5, 99))
    # ---------------------------------------------------------------- I9 furniture and decoration
    furn = []
    def imp(asset, loc, rot, scale=1.0, name=None):
        p = os.path.join(J.MOD, asset, asset + '.gltf')
        if not os.path.exists(p): return None
        r = J.gltf(asset, c, loc=loc, rot=rot, scale=scale, name=name); tag(r, ext=E6, int_=(9, 99)); furn.append(r); return r
    I9 = dict(ext=E6, int_=(9, 99))
    B("R_Rug", [(7.4, -8.15, F0 + 0.026, 13.2, -3.6, F0 + 0.038)], M['rug'], c, bevel=0.008, **I9)
    # modern low sofa in linen (back to the garden glazing, facing the feature wall)
    x0, y0, w, d = 9.65, -7.95, 2.9, 1.02
    B("F_SofaBase", [(x0, y0, F0 + 0.13, x0 + w, y0 + d, F0 + 0.42)], M['linen'], c, bevel=0.035, **I9)
    B("F_SofaArms", [(x0, y0, F0 + 0.13, x0 + 0.22, y0 + d, F0 + 0.63), (x0 + w - 0.22, y0, F0 + 0.13, x0 + w, y0 + d, F0 + 0.63)], M['linen'], c, bevel=0.05, **I9)
    B("F_SofaBack", [(x0 + 0.22, y0, F0 + 0.42, x0 + w - 0.22, y0 + 0.24, F0 + 0.8)], M['linen'], c, bevel=0.05, **I9)
    n = 3; cw = (w - 0.44) / n
    B("F_SofaSeats", [(x0 + 0.22 + i * cw + 0.008, y0 + 0.24, F0 + 0.42, x0 + 0.22 + (i + 1) * cw - 0.008, y0 + d - 0.01, F0 + 0.57) for i in range(n)], M['linen'], c, bevel=0.06, **I9)
    B("F_SofaCushions", [(x0 + 0.22 + i * cw + 0.03, y0 + 0.2, F0 + 0.57, x0 + 0.22 + (i + 1) * cw - 0.03, y0 + 0.44, F0 + 0.98) for i in range(n)], M['linen'], c, bevel=0.08, **I9)
    B("F_SofaLegs", [(x, y, F0 + 0.025, x + 0.05, y + 0.05, F0 + 0.13) for x in (x0 + 0.08, x0 + w - 0.13) for y in (y0 + 0.08, y0 + d - 0.13)], M['bronze'], c, **I9)
    # second sofa along the east glazing, facing the room (L-shaped seating)
    xa, ya, wa, da = 13.38, -7.35, 3.1, 1.02
    B("F_Sofa2Base", [(xa, ya, F0 + 0.13, xa + da, ya + wa, F0 + 0.42)], M['linen'], c, bevel=0.035, **I9)
    B("F_Sofa2Arms", [(xa, ya, F0 + 0.13, xa + da, ya + 0.22, F0 + 0.63), (xa, ya + wa - 0.22, F0 + 0.13, xa + da, ya + wa, F0 + 0.63)], M['linen'], c, bevel=0.05, **I9)
    B("F_Sofa2Back", [(xa + da - 0.24, ya + 0.22, F0 + 0.42, xa + da, ya + wa - 0.22, F0 + 0.8)], M['linen'], c, bevel=0.05, **I9)
    cw2 = (wa - 0.44) / 3
    B("F_Sofa2Seats", [(xa + 0.01, ya + 0.22 + i * cw2 + 0.008, F0 + 0.42, xa + da - 0.24, ya + 0.22 + (i + 1) * cw2 - 0.008, F0 + 0.57) for i in range(3)], M['linen'], c, bevel=0.06, **I9)
    B("F_Sofa2Cush", [(xa + da - 0.46, ya + 0.22 + i * cw2 + 0.03, F0 + 0.57, xa + da - 0.2, ya + 0.22 + (i + 1) * cw2 - 0.03, F0 + 0.98) for i in range(3)], M['linen'], c, bevel=0.08, **I9)
    B("F_Throw", [(xa + 0.15, ya + 0.6, F0 + 0.57, xa + 0.75, ya + 1.2, F0 + 0.61)], M['rug'], c, bevel=0.02, **I9)
    B("F_SideTable", [(12.75, -8.0, F0 + 0.025, 13.25, -7.5, F0 + 0.55)], M['wood_dark'], c, bevel=0.01, **I9)
    imp("modern_arm_chair_01", (10.35, -3.55, F0 + 0.025), 200, 1.0, "F_ArmChairA")
    imp("mid_century_lounge_chair", (8.2, -5.9, F0 + 0.025), -105, 1.0, "F_Lounge")
    imp("modern_coffee_table_01", (11.4, -5.6, F0 + 0.04), 0, 1.0, "F_Table")
    imp("potted_plant_02", (14.35, -8.35, F0 + 0.025), 30, 1.15, "F_PlantA")
    imp("potted_plant_04", (3.8, -8.3, F0 + 0.025), 0, 1.2, "F_PlantB")
    imp("potted_plant_04", (14.4, -1.6, F0 + 0.025), 80, 1.0, "F_PlantC")
    imp("ceramic_vase_01", (11.6, -1.45, F0 + 0.62), 0, 1.4, "F_Vase")
    B("R_Credenza", [(9.9, -1.6, F0 + 0.18, 12.4, -1.16, F0 + 0.6)], M['wood_dark'], c, bevel=0.01, **I9)
    B("R_CredenzaBase", [(10.0, -1.55, F0 + 0.025, 12.3, -1.2, F0 + 0.18)], M['bronze'], c, **I9)
    B("R_ArtFrame", [(4.5, -1.16, 1.25, 7.7, -1.13, 3.05)], M['wood_dark'], c, **I9)
    B("R_ArtCanvas", [(4.56, -1.17, 1.31, 7.64, -1.159, 2.99)], M['art'], c, **I9)
    sp = J.light("R_ArtSpot", 'SPOT', (6.1, -2.4, CEIL - 0.02), c, 60, color=3000, size=0.03, spot=40, blend=0.5)
    J.aim(sp, (6.1, -1.15, 2.1)); tag(sp, ext=E6, int_=(9, 99))
    # sheer curtains gathered at the facade bays
    bm = bmesh.new()
    for (x0, x1) in ((3.4, 4.9), (7.1, 8.6), (9.4, 10.9), (13.1, 14.6)):
        n = 28; verts = []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n; y = -8.86 + 0.06 * math.sin(i * 1.15)
            verts.append((bm.verts.new((x, y, F0 + 0.03)), bm.verts.new((x, y, CEIL - 0.02))))
        for i in range(n): bm.faces.new([verts[i][0], verts[i + 1][0], verts[i + 1][1], verts[i][1]])
    ob = mesh_from_bm("R_Curtains", bm, M['curtain'], c); tag(ob, ext=E6, int_=(9, 99))
    return "room ok: %d furniture" % len(furn)

# ================================================================== DUSK: lit interiors seen from outside
def build_dusk():
    M = JM.mats(); c = clear("M_Dusk")
    D = dict(ext=(6, 99), int_=(9, 99), dusk=2)
    R = random.Random(5)
    for k in range(1, 6):
        z0, z1 = LV[k], LV[k + 1] - SL
        B(f"D_Floor{k}", [(-14.7, -8.97, z0, 14.7, -2.6, z0 + 0.03)], M['oak'], c, **D)
        B(f"D_Ceil{k}", [(-14.7, -8.97, z1 - 0.55, 14.7, -2.6, z1 - 0.53)], M['ceil_paint'], c, **D)
        B(f"D_Back{k}", [(-14.7, -2.62, z0, 14.7, -2.6, z1 - 0.53)], M['paint'], c, **D)
        B(f"D_Party{k}", [(x - 0.1, -8.95, z0, x + 0.1, -2.6, z1 - 0.53) for x in (-9, 3)], M['paint'], c, **D)
        fur = []
        for x0, x1 in zip(CX[:-1], CX[1:]):
            if R.random() < 0.7:
                xm = (x0 + x1) / 2 + R.uniform(-1, 1)
                fur.append((xm - 1.2, -5.4, z0 + 0.03, xm + 1.2, -4.5, z0 + 0.45))
                fur.append((xm - 1.2, -4.6, z0 + 0.03, xm + 1.2, -4.4, z0 + 0.85))
        B(f"D_Furn{k}", fur, M['linen'], c, **D)
        for i, (x0, x1) in enumerate(zip(CX[:-1], CX[1:])):
            L = J.light(f"D_L{k}_{i}", 'AREA', ((x0 + x1) / 2, -5.6, z1 - 0.6), c, R.uniform(160, 260), color=R.choice((2800, 3000, 3200)), size=3.0, size_y=2.0)
            tag(L, **D)
        # sheer curtains in some bays (slightly drawn)
        bm = bmesh.new()
        for x0, x1 in zip(CX[:-1], CX[1:]):
            if R.random() < 0.45:
                a0 = x0 + 0.4; a1 = a0 + R.uniform(1.0, 2.4); n = 18; vs = []
                for i in range(n + 1):
                    x = a0 + (a1 - a0) * i / n; y = -8.82 + 0.05 * math.sin(i * 1.3)
                    vs.append((bm.verts.new((x, y, z0 + 0.03)), bm.verts.new((x, y, z1 - 0.55))))
                for i in range(n): bm.faces.new([vs[i][0], vs[i + 1][0], vs[i + 1][1], vs[i][1]])
        ob = mesh_from_bm(f"D_Curt{k}", bm, M['curtain'], c); tag(ob, **D)
        # balcony soffit downlights
        dl = [(x, BAL_Y(), z0 - SL - 0.035) for x in [-13.5 + 3 * i for i in range(10)]]
        for i, p in enumerate(dl):
            if i % 2: continue
            L = J.light(f"D_Soff{k}_{i}", 'SPOT', p, c, 40, color=2900, size=0.05, spot=80, blend=0.8); tag(L, **D)
        B(f"D_SoffDisc{k}", [(x - 0.05, -9.95 - 0.05, z0 - SL - 0.04, x + 0.05, -9.95 + 0.05, z0 - SL - 0.03) for (x, _y, _z) in dl], M['emit_warm'], c, **D)
    # penthouse
    z0, z1 = LV[6], LV[7] - SL
    B("D_PHFloor", [(-14.7, -2.97, z0, 8.7, 8.7, z0 + 0.03)], M['oak'], c, **D)
    B("D_PHCeil", [(-14.7, -2.97, z1 - 0.4, 8.7, 8.7, z1 - 0.38)], M['ceil_paint'], c, **D)
    for i, x in enumerate((-12, -6, 0, 6)):
        L = J.light(f"D_PH{i}", 'AREA', (x, 0.5, z1 - 0.45), c, 260, color=2900, size=3.0); tag(L, **D)
    for i, x in enumerate((-12, -6, 0, 6)):
        L = J.light(f"D_PHSoff{i}", 'SPOT', (x, -4.6, LV[7] - 0.36), c, 70, color=2900, size=0.05, spot=80, blend=0.8); tag(L, **D)
    # lobby finished (dusk view through the entrance)
    z0 = LV[0]
    B("D_LobbyFloor", [(-8.7, -8.97, z0, 2.9, 2.85, z0 + 0.03)], M['tile'], c, **D)
    B("D_LobbyCeil", [(-8.7, -8.97, CEIL, 2.9, 2.85, CEIL + 0.02)], M['ceil_paint'], c, **D)
    B("D_LobbyWall", [(-2.9, 2.62, z0, 2.9, 2.85, CEIL)], M['feature'], c, **D)
    B("D_LobbyDesk", [(-2.2, -0.6, z0, 2.2, 0.2, z0 + 1.05)], M['wood_dark'], c, **D)
    for i, (x, y) in enumerate(((-6, -6), (-6, -1), (0, -6), (0, -2.5), (-6, 2))):
        L = J.light(f"D_Lob{i}", 'AREA', (x, y, CEIL - 0.05), c, 160, color=3000, size=1.2); tag(L, **D)
    B("D_LobbyLED", [(-2.9, 2.6, CEIL - 0.06, 2.9, 2.62, CEIL - 0.03)], M['emit_cove'], c, **D)
    # facade wash, entrance, street lamps
    for i, x in enumerate((-4.45, 4.45)):
        L = J.light(f"D_Portal{i}", 'SPOT', (x, -13.0, 0.5), c, 120, color=2900, size=0.05, spot=30, blend=0.6)
        J.aim(L, (x, -11.0, 4.6)); tag(L, **D)
    for i, x in enumerate((-24, -8, 8, 24)):
        L = J.light(f"D_Street{i}", 'POINT', (x, -18.4, 7.2), c, 900, color=3200, size=0.15); tag(L, ext=(0, 99), dusk=2)
    # the fit-out room seen from outside at dusk keeps its own lights (I7+)
    return "dusk ok"

def BAL_Y(): return -9.95

# ================================================================== WORLD, SUN, RENDER SETTINGS, CAMERAS
def hdri_sun_dir(img):
    import numpy as np
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3].sum(axis=2)
    yy, xx = np.unravel_index(np.argmax(px), px.shape)
    u = (xx + 0.5) / w; v = (yy + 0.5) / h
    phi = (u - 0.5) * 2 * math.pi        # azimuth around Z in Blender equirect convention
    theta = (v - 0.5) * math.pi          # elevation (pixels stored bottom-up)
    return phi, theta

def build_world(sun_az_deg=245.0):
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("JEC_World"); sc.world = w
    w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground'); bg.name = 'BG'
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.name = 'HDRI'
    mp = nt.nodes.new('ShaderNodeMapping'); mp.name = 'HDRI_Map'; tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], env.inputs['Vector'])
    nt.links.new(env.outputs[0], bg.inputs['Color']); nt.links.new(bg.outputs[0], out.inputs['Surface'])
    day = bpy.data.images.load(os.path.join(J.HDRI, 'qwantani_late_afternoon_puresky_2k.hdr'), check_existing=True); day.name = 'DAY_HDR'
    dusk = bpy.data.images.load(os.path.join(J.HDRI, 'qwantani_dusk_2_puresky_2k.hdr'), check_existing=True); dusk.name = 'DUSK_HDR'
    env.image = day
    phi, theta = hdri_sun_dir(day)
    # rotate the environment so its sun sits at the requested azimuth (measured like a compass: 0 = north/+Y, 90 = east/+X)
    want = math.radians(90.0 - sun_az_deg)      # compass -> math angle from +X
    rot = (math.pi - phi) - want
    w['rot_day'] = rot; w['rot_dusk'] = math.radians(-60)
    mp.inputs['Rotation'].default_value[2] = rot
    bg.inputs['Strength'].default_value = 1.0
    sun = bpy.data.objects.get('SUN')
    if not sun:
        ld = bpy.data.lights.new('SUN', 'SUN'); sun = bpy.data.objects.new('SUN', ld); sc.collection.objects.link(sun)
    elev = max(theta, math.radians(12))
    d = Vector((math.cos(want) * math.cos(elev), math.sin(want) * math.cos(elev), math.sin(elev)))   # towards the sun
    sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sun.data.energy = 4.2; sun.data.angle = math.radians(0.8); sun.data.color = J.kelvin(5600)
    # render settings
    r = sc.render; r.engine = 'CYCLES'; cy = sc.cycles
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'METAL'; prefs.get_devices()
        for dv in prefs.devices: dv.use = True
        cy.device = 'GPU'
    except Exception: pass
    cy.samples = 64; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.025; cy.use_denoising = True
    try: cy.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    cy.max_bounces = 8; cy.diffuse_bounces = 4; cy.glossy_bounces = 4; cy.transmission_bounces = 8; cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.blur_glossy = 0.5
    r.use_persistent_data = True
    r.resolution_x = 1920; r.resolution_y = 1080; r.resolution_percentage = 100; r.fps = 30
    vs = sc.view_settings
    for vt in ('AgX', 'Filmic'):
        try: vs.view_transform = vt; break
        except Exception: pass
    for lk in ('AgX - Medium High Contrast', 'Medium High Contrast', 'None'):
        try: vs.look = lk; break
        except Exception: pass
    vs.exposure = 0.0
    return {"sun_az": sun_az_deg, "hdri_sun_elev_deg": round(math.degrees(theta), 1), "rot": round(math.degrees(rot), 1)}

def cam(name, loc, target, lens):
    ob = bpy.data.objects.get(name)
    if not ob:
        cd = bpy.data.cameras.new(name); ob = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; J.aim(ob, target); ob.data.lens = lens; ob.data.sensor_width = 36; ob.data.clip_start = 0.05; ob.data.clip_end = 600
    return ob

def build_cameras():
    cam("CAM_HERO", (-31.0, -47.0, 18.0), (1.5, -1.0, 11.5), 25)
    cam("CAM_DUSK_A", (-30.0, -58.0, 4.0), (0.0, -3.0, 13.0), 32)
    cam("CAM_DUSK_B", (-21.0, -53.0, 3.2), (1.5, -3.0, 13.0), 32)
    cam("CAM_ROOM", (4.4, -3.4, 1.5), (14.6, -5.3, 1.45), 18)
    return "cams ok"

# ================================================================== WALK: hero -> entrance -> raw lobby -> the room
EXP_RAW = 1.6
WALK = [
    (1,   (-31.0, -47.0, 18.0), (1.5, -1.0, 11.5), 25),
    (40,  (-22.5, -40.5, 11.5), (0.5, -4.0, 8.0), 26),
    (80,  (-9.5, -31.5, 4.4),   (0.0, -8.0, 4.2), 25),
    (115, (-1.6, -22.0, 1.8),   (0.0, -9.0, 2.6), 24),
    (140, (0.0, -15.6, 2.05),   (0.0, -6.0, 2.2), 23),
    (160, (0.0, -11.3, 2.0),    (0.0, -3.0, 2.0), 22),
    (176, (0.0, -8.6, 1.95),    (0.2, -1.0, 1.95), 21),
    (196, (0.3, -6.0, 1.9),     (2.5, -0.5, 1.9), 20),
    (216, (1.6, -3.6, 1.85),    (6.0, -1.8, 1.85), 19),
    (232, (3.0, -2.6, 1.82),    (10.0, -3.8, 1.75), 18.5),
    (248, (4.4, -3.4, 1.8),     (14.6, -5.3, 2.15), 18),
]
def build_walk():
    sc = bpy.context.scene
    camo = cam("CAM_WALK", WALK[0][1], WALK[0][2], WALK[0][3])
    tgt = bpy.data.objects.get("CAM_WALK_T") or bpy.data.objects.new("CAM_WALK_T", None)
    if tgt.name not in sc.collection.objects: sc.collection.objects.link(tgt)
    camo.animation_data_clear(); tgt.animation_data_clear(); camo.data.animation_data_clear()
    for cn in list(camo.constraints): camo.constraints.remove(cn)
    tc = camo.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    for f, loc, t, lens in WALK:
        camo.location = loc; camo.keyframe_insert('location', frame=f)
        tgt.location = t; tgt.keyframe_insert('location', frame=f)
        camo.data.lens = lens; camo.data.keyframe_insert('lens', frame=f)
    # entrance doors open as the camera arrives
    for nm, ang in (("E_DoorL", 80), ("E_DoorR", -80)):
        d = bpy.data.objects.get(nm)
        if not d: continue
        d.animation_data_clear()
        for f, a in ((1, 0), (128, 0), (158, ang)):
            d.rotation_euler = (0, 0, math.radians(a)); d.keyframe_insert('rotation_euler', frame=f)
    sc.frame_start = 1; sc.frame_end = WALK[-1][0]
    vs = sc.view_settings
    if sc.animation_data and sc.animation_data.action:
        try:
            from bpy_extras import anim_utils
            cb = anim_utils.action_get_channelbag_for_slot(sc.animation_data.action, sc.animation_data.action_slot)
            for fc in [f for f in cb.fcurves if f.data_path == 'view_settings.exposure']: cb.fcurves.remove(fc)
        except Exception: pass
    for f, e in ((1, 0.0), (150, 0.0), (172, 0.9), (196, EXP_RAW), (248, EXP_RAW)):
        vs.exposure = e; vs.keyframe_insert('exposure', frame=f)
    # room camera = last walk pose
    cam("CAM_ROOM", WALK[-1][1], WALK[-1][2], WALK[-1][3])
    return {"frames": WALK[-1][0]}
