"""Geometry of the JEC master building and its site. Run the build_* functions in order."""
import bpy, bmesh, math, os, sys, importlib, random
from mathutils import Vector, Matrix
ROOT = os.path.dirname(os.path.abspath(__file__))  # this script's folder (was ~/Desktop/JEC_AlJallad_3D/POC)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import jecpoc as J
import jecmaster as JM
from jecmaster import CX, CY, LV, SL, COLW, BD, BW, BAL, CORE, TOPZ, EXT, FRAME, B, C, clear, tag, wall, frame_specs, glazing_run, cols_at, cyls, mesh_from_bm

# ================================================================== GROUND, PIT, FOUNDATIONS
def build_ground():
    M = JM.mats(); c = clear("M_Ground")
    PX0, PX1, PY0, PY1 = -17.5, 17.5, -11.5, 11.5          # excavation
    # plot ground (dirt) with a hole for the pit
    g = []
    g += [(-30, -16, -0.3, 30, PY0, 0.0), (-30, PY1, -0.3, 30, 22, 0.0)]
    g += [(-30, PY0, -0.3, PX0, PY1, 0.0), (PX1, PY0, -0.3, 30, PY1, 0.0)]
    B("G_PlotDirt", g, M['dirt'], c)
    # neighbouring gardens (grass) and the street
    B("G_Gardens", [(-400, -16, -0.3, -30, 400, 0.0), (30, -16, -0.3, 400, 400, 0.0), (-30, 22, -0.3, 30, 400, 0.0)], M['lawn'], c)
    B("G_Sidewalk", [(-400, -19.6, -0.3, 400, -16, 0.15)], M['sidewalk'], c)
    B("G_Curb", [(-400, -19.75, -0.3, 400, -19.55, 0.16)], M['white'], c)
    B("G_Road", [(-400, -28.5, -0.3, 400, -19.6, 0.0)], M['asphalt'], c)
    B("G_FarWalk", [(-400, -32, -0.3, 400, -28.5, 0.15)], M['sidewalk'], c)
    B("G_FarGrass", [(-400, -400, -0.3, 400, -32, 0.1)], M['lawn'], c)
    lines = [(x, -24.15, 0.001, x + 3.0, -23.95, 0.004) for x in range(-300, 300, 9)]
    B("G_RoadLines", lines, M['hwhite'], c)
    # excavation: soil faces + floor (stage 1-2); before digging the pit is full (stage 0); backfilled from stage 3
    D = -2.7
    B("G_PitWalls", [(PX0 - 0.2, PY0, D, PX0, PY1, 0), (PX1, PY0, D, PX1 + 0.2, PY1, 0),
                     (PX0, PY0 - 0.2, D, PX1, PY0, 0), (PX0, PY1, D, PX1, PY1 + 0.2, 0)], M['soil'], c, ext=(1, 3))
    B("G_PitFloor", [(PX0, PY0, D - 0.1, PX1, PY1, D)], M['soil'], c, ext=(1, 3))
    B("G_FillBefore", [(PX0, PY0, D, PX1, PY1, 0.0)], M['dirt'], c, ext=(0, 1))
    B("G_Backfill", [(PX0, PY0, D, PX1, PY1, 0.0)], M['gravel'], c, ext=(3, 99))
    # spoil heap from the dig (stage 1-2), removed before the frame
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=7.5, radius2=1.5, depth=3.2,
                          matrix=Matrix.Translation(Vector((-23.0, 13.0, 1.4))))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=5.0, radius2=1.0, depth=2.2,
                          matrix=Matrix.Translation(Vector((-17.5, 16.5, 0.9))))
    ob = mesh_from_bm("G_SpoilHeap", bm, M['soil'], c); tag(ob, ext=(1, 3))
    md = ob.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.get('heapnoise') or bpy.data.textures.new('heapnoise', 'CLOUDS')
    tx.noise_scale = 1.6; md.texture = tx; md.strength = 0.6
    ob.modifiers.new('s', 'SUBSURF').levels = 2
    return "ground ok"

def build_foundations():
    M = JM.mats(); c = clear("M_Found")
    pads, blind, stubs, starters = [], [], [], []
    for x in CX:
        for y in CY:
            if CORE[0] <= x <= CORE[1] and CORE[2] <= y <= CORE[3]: continue
            pads.append((x - 1.3, y - 1.3, -2.5, x + 1.3, y + 1.3, -1.6))
            blind.append((x - 1.45, y - 1.45, -2.6, x + 1.45, y + 1.45, -2.5))
            stubs.append((x - 0.3, y - 0.3, -1.6, x + 0.3, y + 0.3, 0.2))
            for dx in (-0.22, 0, 0.22):
                for dy in (-0.22, 0, 0.22):
                    if dx == 0 and dy == 0: continue
                    starters.append(((x + dx, y + dy, 0.15), (x + dx, y + dy, 1.35)))
    pads.append((-3.8, 2.2, -2.5, 3.8, 9.8, -1.6)); blind.append((-3.95, 2.05, -2.6, 3.95, 9.95, -2.5))
    B("F_Blinding", blind, M['conc_floor'], c, ext=(2, 3))
    B("F_Pads", pads, M['conc'], c, ext=(2, 3), bevel=0.01)
    B("F_Stubs", stubs, M['conc'], c, ext=(2, 3))
    # tie beams on every grid line
    tb = []
    for y in CY: tb.append((-15, y - 0.2, -0.6, 15, y + 0.2, 0.2))
    for x in CX: tb.append((x - 0.2, -9, -0.6, x + 0.2, 9, 0.2))
    B("F_TieBeams", tb, M['conc'], c, ext=(2, 3))
    # core walls start on the raft
    cw = []
    cw += [(CORE[0] - 0.125, CORE[2], -1.6, CORE[0] + 0.125, CORE[3], 0.2), (CORE[1] - 0.125, CORE[2], -1.6, CORE[1] + 0.125, CORE[3], 0.2),
           (CORE[0], CORE[3] - 0.125, -1.6, CORE[1], CORE[3] + 0.125, 0.2), (CORE[0], CORE[2] - 0.125, -1.6, CORE[1], CORE[2] + 0.125, 0.2)]
    B("F_CoreBase", cw, M['conc'], c, ext=(2, 3))
    st = cyls("F_Starters", starters, 0.014, M['rebar'], c, seg=5); tag(st, ext=(2, 3))
    return "foundations ok"

# ================================================================== STRUCTURAL FRAME
def build_frame():
    M = JM.mats(); c = clear("M_Frame")
    # ground slab on grade
    B("S_Slab0", [(-15.3, -9.3, 0.2, 15.3, 9.3, LV[0])], M['conc_floor'], c, ext=(3, 99))
    for k in range(0, 7):
        z0, z1 = LV[k], LV[k + 1] - SL
        cols = [(x - COLW / 2, y - COLW / 2, z0, x + COLW / 2, y + COLW / 2, z1) for (x, y) in cols_at(k)
                if not (CORE[0] < x < CORE[1] and CORE[2] < y < CORE[3])]
        B(f"S_Cols{k}", cols, M['conc'], c, ext=(FRAME(k), 99), bevel=0.012)
    for k in range(1, 8):
        z = LV[k]
        if k < 7:
            plate = [(-15.3, BAL, z - SL, 15.3, 9.3, z)]
            xs, ys = CX, CY
        else:
            plate = [(-15.3, -6.0, z - SL, 9.3, 9.3, z)]
            xs, ys = [x for x in CX if x <= 9], [y for y in CY if y >= -3]
        bm_ = []
        for y in ys: bm_.append((min(xs), y - BW / 2, z - BD, max(xs), y + BW / 2, z - SL))
        for x in xs: bm_.append((x - BW / 2, min(ys), z - BD, x + BW / 2, max(ys), z - SL))
        st = FRAME(k - 1)
        B(f"S_Slab{k}", plate, M['conc_floor'], c, ext=(st, 99))
        B(f"S_Beams{k}", bm_, M['conc'], c, ext=(st, 99))
    # core walls with lift / stair openings, each level
    holes = [(-2.45, -1.15, 0, 2.3), (0.35, 1.45, 0, 2.3), (1.75, 2.75, 0, 2.3)]
    for k in range(0, 8):
        z0 = LV[k] - SL; z1 = (LV[k + 1] - SL) if k < 7 else TOPZ
        st = FRAME(min(k, 6))
        hk = [(h[0], h[1], z0 + SL + h[2], z0 + SL + h[3]) for h in holes] if k < 7 else [(-2.45, -1.15, z0 + SL, z0 + SL + 2.3)]
        sp = []
        sp += [(CORE[0] - 0.125, CORE[2], z0, CORE[0] + 0.125, CORE[3], z1), (CORE[1] - 0.125, CORE[2], z0, CORE[1] + 0.125, CORE[3], z1),
               (CORE[0], CORE[3] - 0.125, z0, CORE[1], CORE[3] + 0.125, z1)]
        sp += wall('y', CORE[2] - 0.125, CORE[2] + 0.125, CORE[0] + 0.125, CORE[1] - 0.125, z0, z1, hk)
        B(f"S_Core{k}", sp, M['conc'], c, ext=(st, 99))
    B("S_CoreRoof", [(CORE[0] - 0.125, CORE[2] - 0.125, TOPZ - 0.25, CORE[1] + 0.125, CORE[3] + 0.125, TOPZ)], M['conc_floor'], c, ext=(4, 99))
    # stairs inside the core: two flights per storey with landings
    for k in range(0, 7):
        za, zb = LV[k], LV[k + 1]; h = (zb - za) / 2; n = max(10, round(h / 0.17)); r = h / n
        y0, y1 = 4.3, 7.5; t = (y1 - y0) / n
        sp = []
        for i in range(n):
            sp.append((-2.85, y0 + i * t, za - 0.15, -1.55, y0 + (i + 1) * t, za + (i + 1) * r))
            sp.append((-1.45, y1 - (i + 1) * t, za + h - 0.15, -0.15, y1 - i * t, za + h + (i + 1) * r))
        sp.append((-2.85, y1, za + h - 0.2, -0.15, 8.85, za + h))       # mid landing
        sp.append((-2.85, 3.15, zb - 0.2, -0.15, y0, zb))               # floor landing
        B(f"S_Stair{k}", sp, M['conc'], c, ext=(FRAME(k), 99))
    # temporary works: props under the freshest slabs, starter bars
    def props(name, x0, x1, y0, y1, z0, z1, ext, step=1.5):
        segs = []
        x = x0
        while x <= x1 + 1e-6:
            y = y0
            while y <= y1 + 1e-6:
                if not any(abs(x - cx) < 0.5 and abs(y - cy) < 0.5 for cx in CX for cy in CY):
                    segs.append(((x, y, z0), (x, y, z1)))
                y += step
            x += step
        ob = cyls(name, segs, 0.03, JM.M['steel'], c, seg=6); tag(ob, ext=ext)
        heads = cyls(name + "_Heads", [((s[0][0] - 0.6, s[0][1], z1 - 0.06), (s[0][0] + 0.6, s[0][1], z1 - 0.06)) for s in segs[::2]], 0.06, JM.M['plywood'], c, seg=4, smooth=False)
        tag(heads, ext=ext)
    props("T_Props2", -14.25, 14.25, -9.75, 8.25, LV[1], LV[2] - SL, (3, 4))
    props("T_Props6", -14.25, 14.25, -9.75, 8.25, LV[5], LV[6] - SL, (4, 5))
    props("T_Props7", -14.25, 8.25, -5.25, 8.25, LV[6], LV[7] - SL, (4, 5))
    sb = []
    for (x, y) in cols_at(2):
        if CORE[0] < x < CORE[1] and CORE[2] < y < CORE[3]: continue
        for dx in (-0.22, 0, 0.22):
            for dy in (-0.22, 0, 0.22):
                if dx == 0 and dy == 0: continue
                sb.append(((x + dx, y + dy, LV[2] - 0.05), (x + dx, y + dy, LV[2] + 1.3)))
    ob = cyls("T_StartersL2", sb, 0.014, JM.M['rebar'], c, seg=5); tag(ob, ext=(3, 4))
    # slab-edge formwork and the edge safety barrier on the top slab while it cures
    fw = [(-15.45, BAL - 0.15, LV[2] - 0.3, 15.45, BAL - 0.02, LV[2] + 0.25), (-15.45, BAL, LV[2] - 0.3, -15.32, 9.45, LV[2] + 0.25),
          (15.32, BAL, LV[2] - 0.3, 15.45, 9.45, LV[2] + 0.25), (-15.45, 9.32, LV[2] - 0.3, 15.45, 9.45, LV[2] + 0.25)]
    B("T_EdgeForm2", fw, M['plywood'], c, ext=(3, 4))
    rails = []
    for k in (2,):
        z = LV[k]
        rails += [(-15.4, BAL - 0.1, z + 1.0, 15.4, BAL - 0.05, z + 1.05), (-15.4, BAL - 0.1, z + 0.5, 15.4, BAL - 0.05, z + 0.55)]
        for x in [i * 2.0 - 15 for i in range(16)]: rails.append((x - 0.03, BAL - 0.1, z, x + 0.03, BAL - 0.04, z + 1.05))
    B("T_EdgeRail2", rails, M['yellow'], c, ext=(3, 4))
    return "frame ok"

# ================================================================== ENVELOPE
def build_envelope():
    M = JM.mats(); c = clear("M_Envelope")
    for k in range(0, 7):
        z0 = LV[k]; ztop = LV[k + 1] - SL; st = EXT(k)
        ext = (st, 99)
        if k < 6:
            # ---- front glazing at y = -9 between columns (ground floor: entrance bay handled separately)
            gl, fr = [], []
            for x0, x1 in zip(CX[:-1], CX[1:]):
                if k == 0 and x0 == -3: continue
                g_, f_ = glazing_run('y', -9.0, x0 + 0.34, x1 - 0.34, z0, LV[k + 1] - BD - 0.005, pane=1.33 if k else 1.65)
                gl += g_; fr += f_
            B(f"E_GlassF{k}", gl, M['glass'], c, ext=ext); B(f"E_FrameF{k}", fr, M['bronze'], c, ext=ext)
            # ---- stone cladding of the front columns
            cl = [(x - 0.34, -9.34, z0 - (SL if k else 0), x + 0.34, -8.66, ztop) for x in CX]
            B(f"E_ColClad{k}", cl, M['stone'], c, ext=ext)
        # ---- side and back walls: blockwork first, then stone with window openings
        def side_holes(a0, a1):
            hs = []
            for y0, y1 in zip([v for v in CY if a0 <= v < a1], [v for v in CY if a0 < v <= a1]):
                for cc in (y0 + 1.6, y1 - 1.6):
                    hs.append((cc - 0.7, cc + 0.7, z0 + 0.15, min(ztop - 0.1, z0 + 2.75)))
            return hs
        blk, stn, wg, wf = [], [], [], []
        spans = []
        if k < 6:
            spans += [('x', -15, -9.0, 9.0, -1), ('x', 15, -9.0, 9.0, 1)]
            spans += [('y', 9.0, -15.0, 15.0, 1)]
        else:  # penthouse: west and back walls; east and front are glazed
            spans += [('x', -15, -3.0, 9.0, -1), ('y', 9.0, -15.0, 9.0, 1)]
        for ax, cc, a0, a1, sgn in spans:
            hs = side_holes(a0, a1) if ax == 'x' else [(h0, h1, z0 + 0.15, min(ztop - 0.1, z0 + 2.75)) for xx0, xx1 in zip(CX[:-1], CX[1:]) if not (xx0 >= CORE[0] and xx1 <= CORE[1])
                                                         for h0, h1 in ((xx0 + 1.0, xx0 + 2.6), (xx1 - 2.6, xx1 - 1.0)) if (k < 6 or xx1 <= 9)]
            if k == 0 and ax == 'x' and sgn == 1:
                hs = [(-8.66, -3.34, z0, ztop), (-2.66, -1.0, z0, ztop)] + [h for h in hs if h[0] > -1.0]   # the ground-floor room is glazed on the east
            bt = (cc - 0.1, cc + 0.1)
            st_out = (cc + 0.1, cc + 0.34) if sgn > 0 else (cc - 0.34, cc - 0.1)
            blk += wall(ax, bt[0], bt[1], a0 + 0.3, a1 - 0.3, z0, ztop, hs)
            stn += wall(ax, st_out[0], st_out[1], a0 - 0.34 if ax == 'x' else a0 - 0.34, a1 + 0.34, z0 - SL, ztop, hs)
            for h in hs:
                cpos = (cc + 0.1) if sgn > 0 else (cc - 0.1)
                if ax == 'x': wg.append((cpos - 0.012, h[0], h[2], cpos + 0.012, h[1], h[3]))
                else: wg.append((h[0], cpos - 0.012, h[2], h[1], cpos + 0.012, h[3]))
                wf += frame_specs(ax, cpos, h[0], h[1], h[2], h[3], w=0.06, d=0.12)
                if not (k == 0 and ax == 'x' and sgn == 1 and h[1] <= -1.0):
                    oc = (cc + 0.34 + 0.05) if sgn > 0 else (cc - 0.34 - 0.05)
                    if ax == 'y': oc = cc + 0.34 + 0.05
                    wf += frame_specs(ax, oc, h[0] - 0.09, h[1] + 0.09, h[2] - 0.09, h[3] + 0.09, w=0.09, d=0.1)
        B(f"E_Block{k}", blk, M['block'], c, ext=(5, 99))
        B(f"E_Stone{k}", stn, M['stone'], c, ext=ext)
        B(f"E_WinGlass{k}", wg, M['glass'], c, ext=ext); B(f"E_WinFrame{k}", wf, M['bronze'], c, ext=ext)
    # ---- stone spandrels covering the edge beams above the glazing
    for kk in range(1, 7):
        B(f"E_Spandrel{kk}", [(-15.34, -9.36, LV[kk] - BD - 0.01, 15.34, -9.18, LV[kk] - SL)], M['stone'], c, ext=(EXT(kk - 1), 99))
    B("E_SpandrelPH", [(-15.34, -3.36, LV[7] - BD - 0.01, 9.34, -3.18, LV[7] - SL), (8.82, -3.36, LV[7] - BD - 0.01, 9.18, 9.34, LV[7] - SL)], M['stone'], c, ext=(6, 99))
    # ---- balconies (L1..L6): stone edge band, white soffit, stone deck, glass balustrade, fins
    for k in range(1, 7):
        z = LV[k]; ext = (EXT(k), 99)
        band = [(-15.36, BAL - 0.06, z - 0.32, 15.36, BAL, z + 0.12)]
        band += [(-15.36, BAL, z - 0.32, -15.3, -9.3, z + 0.12), (15.3, BAL, z - 0.32, 15.36, -9.3, z + 0.12)]
        B(f"E_Band{k}", band, M['stone_fin'], c, ext=ext)
        B(f"E_Soffit{k}", [(-15.3, BAL, z - SL - 0.03, 15.3, -9.34, z - SL)], M['white'], c, ext=ext)
        B(f"E_Deck{k}", [(-15.3, BAL, z, 15.3, -9.34, z + 0.04)], M['paving'], c, ext=ext)
        gb, rail = [], []
        for x0, x1 in zip(CX[:-1], CX[1:]):
            gb.append((x0 + 0.22, BAL + 0.07, z + 0.04, x1 - 0.22, BAL + 0.09, z + 1.1))
            rail.append((x0 + 0.22, BAL + 0.05, z + 1.08, x1 - 0.22, BAL + 0.11, z + 1.13))
        if k == 6:   # terrace: balustrade also along the open east side and the open fronts
            gb += [(15.2, BAL + 0.1, z + 0.04, 15.22, 9.2, z + 1.1), (9.4, 9.18, z + 0.04, 15.2, 9.2, z + 1.1), (-15.22, BAL + 0.1, z + 0.04, -15.2, -3.2, z + 1.1)]
            rail += [(15.18, BAL + 0.1, z + 1.08, 15.24, 9.2, z + 1.13), (9.4, 9.16, z + 1.08, 15.2, 9.22, z + 1.13), (-15.24, BAL + 0.1, z + 1.08, -15.18, -3.2, z + 1.13)]
            B("E_TerraceDeck", [(9.4, -9.34, z, 15.3, 9.3, z + 0.04), (-15.3, -9.34, z, 9.4, -3.3, z + 0.04)], M['paving'], c, ext=ext)
        B(f"E_BalGlass{k}", gb, M['glass_bal'], c, ext=ext); B(f"E_BalRail{k}", rail, M['bronze'], c, ext=ext)
        fins = []
        for x in CX:
            ztop = (LV[k + 1] - SL) if k < 6 else (z + 1.35)
            fins.append((x - 0.2, BAL - 0.12, z - 0.32 if k == 1 else z - SL, x + 0.2, -9.34, ztop))
        B(f"E_Fins{k}", fins, M['stone_fin'], c, ext=ext)
        if k <= 5:
            RR = random.Random(100 + k)
            pl, soil, slats = [], [], []
            for i, (x0, x1) in enumerate(zip(CX[:-1], CX[1:])):
                if (i + k) % 2 == 0:
                    pl.append((x0 + 0.5, BAL + 0.14, z + 0.04, x1 - 0.5, BAL + 0.6, z + 0.62))
                    soil.append((x0 + 0.55, BAL + 0.19, z + 0.56, x1 - 0.55, BAL + 0.55, z + 0.6))
                if RR.random() < 0.4:
                    a0 = (x0 + 0.45) if RR.random() < 0.5 else (x1 - 2.05)
                    zt = LV[k + 1] - BD - 0.02
                    slats += [(a0, -9.66, z + 0.04, a0 + 1.6, -9.58, z + 0.1), (a0, -9.66, zt - 0.06, a0 + 1.6, -9.58, zt)]
                    xx = a0
                    while xx < a0 + 1.6 - 0.04:
                        slats.append((xx, -9.67, z + 0.04, xx + 0.045, -9.57, zt)); xx += 0.11
            B(f"E_Planters{k}", pl, M['bronze'], c, ext=ext)
            B(f"E_PlanterSoil{k}", soil, M['dirt'], c, ext=ext)
            B(f"E_Screens{k}", slats, M['bronze'], c, ext=ext)
    # ---- penthouse: front and east glazing, roof canopy, core overrun
    z0, ztop = LV[6], LV[7] - SL
    gl, fr = [], []
    for x0, x1 in zip(CX[:-1], CX[1:]):
        if x1 > 9: continue
        g_, f_ = glazing_run('y', -3.0, x0 + 0.3, x1 - 0.3, z0, LV[7] - BD - 0.005, pane=1.5); gl += g_; fr += f_
    for y0, y1 in zip(CY[1:-1], CY[2:]):
        g_, f_ = glazing_run('x', 9.0, y0 + 0.3, y1 - 0.3, z0, LV[7] - BD - 0.005, pane=1.5); gl += g_; fr += f_
    B("E_GlassPH", gl, M['glass'], c, ext=(6, 99)); B("E_FramePH", fr, M['bronze'], c, ext=(6, 99))
    B("E_PHColClad", [(x - 0.34, y - 0.34, z0, x + 0.34, y + 0.34, ztop) for (x, y) in cols_at(6) if y == -3 or x == 9], M['stone'], c, ext=(6, 99))
    B("E_Canopy", [(-15.42, -6.12, LV[7] - 0.34, 9.42, 9.42, LV[7] + 0.06)], M['white'], c, ext=(6, 99))
    B("E_Parapet", [(-15.42, -6.12, LV[7] + 0.06, 9.42, -5.9, LV[7] + 0.5), (-15.42, 9.2, LV[7] + 0.06, 9.42, 9.42, LV[7] + 0.5),
                    (-15.42, -6.12, LV[7] + 0.06, -15.2, 9.42, LV[7] + 0.5), (9.2, -6.12, LV[7] + 0.06, 9.42, 9.42, LV[7] + 0.5)], M['white'], c, ext=(6, 99))
    B("E_CoreClad", [(CORE[0] - 0.4, CORE[2] - 0.4, LV[7] + 0.06, CORE[1] + 0.4, CORE[3] + 0.4, TOPZ + 0.2)], M['stone'], c, ext=(6, 99))
    # ---- entrance: portal blades, canopy, glazing, pivot doors
    B("E_Portal", [(-4.65, -13.2, LV[0], -4.25, -9.34, 4.75), (4.25, -13.2, LV[0], 4.65, -9.34, 4.75)], M['stone_fin'], c, ext=(5, 99))
    B("E_EntCanopy", [(-4.65, -13.2, 4.4, 4.65, -9.34, 4.75)], M['white'], c, ext=(5, 99))
    gl, fr = [], []
    for a0, a1 in ((-2.66, -1.65), (1.65, 2.66)):
        g_, f_ = glazing_run('y', -9.0, a0, a1, LV[0], LV[1] - BD - 0.005, pane=2.0); gl += g_; fr += f_
    g_, f_ = glazing_run('y', -9.0, -1.65, 1.65, 3.25, LV[1] - BD - 0.005, pane=1.65); gl += g_; fr += f_
    fr += [(-1.7, -9.07, LV[0], -1.6, -8.93, 3.3), (1.6, -9.07, LV[0], 1.7, -8.93, 3.3), (-1.7, -9.07, 3.2, 1.7, -8.93, 3.3)]
    B("E_EntGlass", gl, M['glass'], c, ext=(5, 99)); B("E_EntFrame", fr, M['bronze'], c, ext=(5, 99))
    for nm, x0, x1, px in (("E_DoorL", -1.58, -0.02, -1.48), ("E_DoorR", 0.02, 1.58, 1.48)):
        g = J.boxes(nm, [(x0 - px, -0.012, LV[0] + 0.02 - 0, x1 - px, 0.012, 3.18 - 0)], M['glass'], c)
        f = J.boxes(nm + "_F", [s for s in frame_specs('y', 0.0, x0 - px, x1 - px, LV[0] + 0.02, 3.18, w=0.06, d=0.06)] +
                    [(x0 - px + (0.25 if px < 0 else -0.29), -0.06, 1.0, x0 - px + (0.29 if px < 0 else -0.25), 0.06, 2.4)], M['bronze'], c)
        f.parent = g; g.location = (px, -9.0, 0); tag(g, ext=(5, 99))
    # ---- interior of the raw floor plates is the structure itself; ceiling soffits of balconies get downlights at dusk
    return "envelope ok"

# ================================================================== SITE EQUIPMENT, CRANE, HOARDING
def lattice(name, length, size, n, mat, col, tri=False):
    """Square lattice girder along +Z from 0 to length; wireframe of a triangulated tube."""
    bm = bmesh.new(); rings = []
    s = size / 2
    corners = [(-s, -s), (s, -s), (s, s), (-s, s)] if not tri else [(-s, -s), (s, -s), (0, s)]
    for i in range(n + 1):
        z = length * i / n
        rings.append([bm.verts.new((x, y, z)) for (x, y) in corners])
    m = len(corners)
    for i in range(n):
        for j in range(m):
            a, b2 = rings[i][j], rings[i][(j + 1) % m]; c2, d = rings[i + 1][(j + 1) % m], rings[i + 1][j]
            if (i + j) % 2: bm.faces.new([a, b2, c2]); bm.faces.new([a, c2, d])
            else: bm.faces.new([a, b2, d]); bm.faces.new([b2, c2, d])
    ob = mesh_from_bm(name, bm, mat, col)
    w = ob.modifiers.new('wire', 'WIREFRAME'); w.thickness = max(0.05, size * 0.05); w.use_even_offset = True; w.use_relative_offset = False
    return ob

def build_site():
    M = JM.mats(); c = clear("M_Site")
    # ---- hoarding on the property line with the contractor's name, gate in front
    hz = 2.6; specs = []
    specs += [(-30, -16.05, 0.15, -6.5, -15.95, hz), (6.5, -16.05, 0.15, 30, -15.95, hz)]
    specs += [(-30.05, -16, 0, -29.95, 22, hz), (29.95, -16, 0, 30.05, 22, hz), (-30, 21.95, 0, 30, 22.05, hz)]
    B("H_Panels", specs, M['navy'], c, ext=(0, 6))
    B("H_Band", [(-30, -16.09, 2.25, -6.5, -16.05, 2.45), (6.5, -16.09, 2.25, 30, -16.05, 2.45)], M['gold'], c, ext=(0, 6))
    B("H_Gate", [(-6.5, -16.12, 0.15, 6.5, -16.02, hz - 0.1)], M['hwhite'], c, ext=(0, 6))
    posts = [(x - 0.06, -15.95, 0, x + 0.06, -15.8, hz + 0.05) for x in range(-30, 31, 3)]
    B("H_Posts", posts, M['steel'], c, ext=(0, 6))
    for nm, x, txt, sz in (("H_TextL", -18.2, "JEC | ALJALLAD CONTRACTING", 1.0), ("H_TextR", 18.2, "BUILDING TRUST.  DELIVERING QUALITY.", 0.78)):
        cu = bpy.data.curves.new(nm, 'FONT'); cu.body = txt; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.size = sz; cu.extrude = 0.005
        ob = bpy.data.objects.new(nm, cu); c.objects.link(ob); ob.location = (x, -16.1, 1.3); ob.rotation_euler = (math.radians(90), 0, 0)
        ob.data.materials.append(M['hwhite']); tag(ob, ext=(0, 6))
    # ---- site cabins
    cab = [(-27.6, 12.2, 0, -21.6, 14.6, 2.6), (-27.6, 15.0, 0, -21.6, 17.4, 2.6), (-27.6, 12.2, 2.65, -21.6, 14.6, 5.25)]
    B("H_Cabins", cab, M['container'], c, ext=(0, 6), bevel=0.03)
    win = []
    for (x0, y0, z0, x1, y1, z1) in cab:
        for xx in (x0 + 1.0, x0 + 3.6):
            win.append((xx, y0 - 0.03, z0 + 1.0, xx + 1.4, y0 + 0.01, z0 + 2.0))
    B("H_CabinWin", win, M['dark'], c, ext=(0, 6))
    # ---- materials on site
    import random; R = random.Random(7)
    pal = []
    for i in range(6):
        x, y = -25.5 + (i % 3) * 1.4, -4.0 + (i // 3) * 1.4
        pal.append((x, y, 0, x + 1.2, y + 1.0, 0.12))
        pal.append((x + 0.02, y + 0.02, 0.12, x + 1.18, y + 0.98, 0.12 + 0.2 * R.randint(4, 6)))
    B("H_BlockPallets", pal, M['block'], c, ext=(4, 6))
    rb = []
    for i in range(3):
        y = 2.5 + i * 0.9
        for j in range(30):
            a = R.uniform(0, 6.28); r = R.uniform(0, 0.25)
            rb.append(((-27.5, y + r * math.cos(a), 0.15 + r * math.sin(a) * 0.4 + 0.2), (-19.5, y + r * math.cos(a), 0.15 + r * math.sin(a) * 0.4 + 0.2)))
    ob = cyls("H_RebarBundles", rb, 0.016, M['rebar'], c, seg=4); tag(ob, ext=(2, 4))
    B("H_Timbers", [(-27.5, 6.5 + i * 0.35, 0.0, -21.0, 6.75 + i * 0.35, 0.3) for i in range(4)], M['plywood'], c, ext=(2, 5))
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=3.0, radius2=0.4, depth=1.8, matrix=Matrix.Translation(Vector((-24.0, -10.5, 0.85))))
    ob = mesh_from_bm("H_SandPile", bm, M['gravel'], c); tag(ob, ext=(2, 6)); ob.modifiers.new('s', 'SUBSURF').levels = 2
    # ---- tower crane NE of the building
    cx, cy = 22.0, 13.0; H = 32.0
    B("K_Base", [(cx - 3, cy - 3, -0.2, cx + 3, cy + 3, 0.8)], M['conc'], c, ext=(2, 6))
    mast = lattice("K_Mast", H, 1.8, 22, M['yellow'], c); mast.location = (cx, cy, 0.8); tag(mast, ext=(2, 6))
    ang = math.atan2(-6.0 - cy, -8.0 - cx)       # jib points over the building, towards the camera side
    piv = bpy.data.objects.new("K_Slew", None); c.objects.link(piv); piv.location = (cx, cy, H + 0.8); piv.rotation_euler = (0, 0, ang); tag(piv, ext=(2, 6))
    jib = lattice("K_Jib", 50.0, 1.5, 25, M['yellow'], c, tri=True); jib.parent = piv; jib.rotation_euler = (0, math.radians(90), 0); jib.location = (1.0, 0, 0.9)
    cj = lattice("K_CounterJib", 15.0, 1.4, 7, M['yellow'], c); cj.parent = piv; cj.rotation_euler = (0, math.radians(-90), 0); cj.location = (-1.0, 0, 0.9)
    apex = lattice("K_Apex", 7.0, 1.2, 4, M['yellow'], c); apex.parent = piv; apex.location = (0, 0, 0.0)
    cab2 = J.boxes("K_Cab", [(0.9, -1.8, -0.2, 3.0, -0.9, 2.0)], M['hwhite'], c); cab2.parent = piv
    cwt = J.boxes("K_Counterweight", [(-14.5, -1.0, -1.6, -11.0, 1.0, 0.9)], M['conc'], c); cwt.parent = piv
    ties = cyls("K_Ties", [((0, 0, 7.0), (35.0, 0, 1.6)), ((0, 0, 7.0), (-13.5, 0, 1.6))], 0.045, M['steel'], c, seg=6); ties.parent = piv
    hook = cyls("K_Cable", [((24.0, 0.2, 0.6), (24.0, 0.2, -7.0)), ((24.0, -0.2, 0.6), (24.0, -0.2, -7.0))], 0.02, M['steel'], c, seg=4); hook.parent = piv
    load = J.boxes("K_Load", [(23.0, -0.7, -8.4, 25.0, 0.7, -7.0)], M['plywood'], c); load.parent = piv
    return "site ok"

# ================================================================== LANDSCAPE (completed)
def build_landscape():
    M = JM.mats(); c = clear("M_Land")
    E = (6, 99)
    B("L_Plaza", [(-20.0, -15.0, 0.0, 20.0, -9.34, LV[0])], M['paving'], c, ext=E)
    steps = []
    for i, (y0, y1, z) in enumerate(((-16.0, -15.0, 0.30), (-15.0, -14.6, 0.45))):
        pass
    steps = [(-20.0, -16.0, 0.0, 20.0, -15.55, 0.3), (-20.0, -15.55, 0.0, 20.0, -15.0, 0.45)]
    B("L_Steps", steps, M['paving'], c, ext=E)
    B("L_PlotGround", [(-30, -16, 0.0, -20.0, 22, 0.03), (20.0, -16, 0.0, 30, 22, 0.03), (-20.0, -15.0, 0.0, 20.0, -9.3, 0.03),
                       (-20.0, 9.3, 0.0, 20.0, 22, 0.03), (-20.0, -9.3, 0.0, -15.3, 9.3, 0.03), (15.3, -9.3, 0.0, 20.0, 9.3, 0.03)], M['lawn'], c, ext=E)
    B("L_Paths", [(-20.0, -9.3, 0.031, -15.3, -7.2, 0.06), (15.3, -9.3, 0.031, 20.0, -7.2, 0.06), (-15.3, 9.3, 0.031, 15.3, 11.5, 0.06)], M['paving'], c, ext=E)
    B("L_BoundaryWalls", [(-30.15, -16, 0, -29.85, 22, 1.4), (29.85, -16, 0, 30.15, 22, 1.4), (-30, 21.85, 0, 30, 22.15, 1.4),
                          (-30, -16.15, 0, -20.0, -15.85, 0.9), (20.0, -16.15, 0, 30, -15.85, 0.9)], M['stone'], c, ext=E)
    pl = [(-17.5, -14.6, LV[0], -11.5, -12.2, LV[0] + 0.6), (11.5, -14.6, LV[0], 17.5, -12.2, LV[0] + 0.6)]
    B("L_Planters", pl, M['stone_fin'], c, ext=E)
    B("L_PlanterSoil", [(p[0] + 0.15, p[1] + 0.15, p[5] - 0.08, p[3] - 0.15, p[4] - 0.15, p[5] - 0.05) for p in pl], M['dirt'], c, ext=E)
    # trees, shrubs, lamps (Poly Haven CC0)
    cache = {}
    def imp(asset, loc, rot=0, scale=1.0, ext=E, name=None):
        if not os.path.exists(os.path.join(J.MOD, asset, asset + '.gltf')): return None
        if asset in cache: r = J.dupe(cache[asset], c, loc, rot, scale, name)
        else: r = J.gltf(asset, c, loc=loc, rot=rot, scale=scale, name=name); cache[asset] = r
        tag(r, ext=ext); return r
    t1 = imp("island_tree_01", (-14.5, -13.4, LV[0] + 0.55), 20, 0.75)
    t2 = imp("island_tree_01", (14.5, -13.4, LV[0] + 0.55), 140, 0.7)
    for i, (x, y) in enumerate(((-16.5, -12.9), (-12.6, -13.9), (12.6, -12.9), (16.4, -13.9))):
        imp("shrub_02", (x, y, LV[0] + 0.5), i * 70, 1.1)
    imp("jacaranda_tree", (-27.0, 5.0, 0), 30, 1.0)
    imp("jacaranda_tree", (24.0, 12.5, 0), 200, 1.05)
    imp("island_tree_02", (-24.0, 16.0, 0), 80, 1.0)
    for x in (-24, -8, 8, 24):
        imp("street_lamp_01", (x, -19.0, 0.15), 180, 1.0, ext=(0, 99))
    # neighbours: mature trees only, no buildings
    nb = []
    R = random.Random(3)
    spots = []
    for i in range(140):
        for _ in range(40):
            x = R.uniform(-170, 170); y = R.uniform(-12, 200)
            if -34 < x < 34 and y < 27: continue                # keep the plot and its walls clear
            if y < 0 and -90 < x < 30: continue                  # keep the camera corridor (south-west) open
            if any((x - a) ** 2 + (y - b) ** 2 < 49 for a, b in spots): continue
            spots.append((x, y)); break
    for x in range(30, 170, 12):                                 # trees along the far side of the street, east of the view
        spots.append((x + R.uniform(-3, 3), -36 + R.uniform(-2, 2)))
    for i, (x, y) in enumerate(spots):
        asset = ("jacaranda_tree", "island_tree_02", "tree_small_02", "island_tree_01")[i % 4]
        imp(asset, (x, y, 0), R.uniform(0, 360), R.uniform(1.0, 1.5), ext=(0, 99))
    for i, (x, y) in enumerate(((-33, -12), (-33, 0), (-33, 10), (33, -12), (33, 0), (33, 10), (-15, 25), (0, 25), (15, 25))):
        imp("shrub_01", (x, y, 0), i * 47, 2.2, ext=(0, 99))
    return "landscape ok"


def build_greenery():
    M = JM.mats(); c = clear("M_Green")
    cache = {}
    def imp(asset, loc, rot, scale, ext):
        if not os.path.exists(os.path.join(J.MOD, asset, asset + '.gltf')): return None
        if asset in cache: r = J.dupe(cache[asset], c, loc, rot, scale)
        else: r = J.gltf(asset, c, loc=loc, rot=rot, scale=scale); cache[asset] = r
        tag(r, ext=ext); return r
    R = random.Random(9)
    for k in range(1, 6):
        z = LV[k]
        for i, (x0, x1) in enumerate(zip(CX[:-1], CX[1:])):
            if (i + k) % 2: continue
            n = 6
            for j in range(n):
                x = x0 + 0.8 + (x1 - x0 - 1.6) * (j + 0.5) / n
                imp(("shrub_02", "shrub_04", "shrub_02")[(i + j + k) % 3], (x + R.uniform(-0.15, 0.15), BAL + 0.37, z + 0.56), R.uniform(0, 360), R.uniform(1.0, 1.35), (EXT(k), 99))
    z = LV[6]
    for j, (x, y) in enumerate(((10.5, -9.8), (12.5, -9.8), (14.4, -9.8), (14.4, -7.0), (14.4, 0.0), (14.4, 6.0), (-14.4, -9.8), (-11.0, -9.8))):
        B(f"G_TerrPlanter{j}", [(x - 0.8, y - 0.35, z + 0.04, x + 0.8, y + 0.35, z + 0.7)], M['stone_fin'], c, ext=(6, 99))
        imp(("shrub_02", "shrub_04")[j % 2], (x, y, z + 0.66), R.uniform(0, 360), 0.9, (6, 99))
    return "greenery ok: %d" % len(c.objects)
