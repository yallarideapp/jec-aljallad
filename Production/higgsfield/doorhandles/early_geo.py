"""Door bars in the walk (w1), frames 73-98, where a tree stands in front of the door:
per frame the left leaf's old handle (LHO), its hinge stile (HL) and meeting stile (LF), the right handle (RH) and the
right leaf's meeting stile (RF). Seeds were read off column profiles of every frame; each is refined to sub-pixel edges on
the rows where the bar stands clear against the wall. Nothing is smoothed over time: the camera moves unevenly.
Writes early_raw.json (early_fin.py makes early.json from it)."""
import cv2, numpy as np, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = '/tmp/e'
T0, T1 = 73, 98
SEED = {
 'LHO': {73:(825,832),74:(824,831),75:(823,830),76:(821,829),77:(819,827),78:(815,823),79:(814,822),80:(813,821),81:(810,818),82:(809,817),83:(803,812),84:(801,810),85:(800,809),86:(798,807),87:(795,803),88:(790,801),89:(782,794),90:(782,794),91:(781,793),92:(779,791),93:(773,784),94:(768,781),95:(763,776),96:(762,775),97:(761,774),98:(753,766)},
 'HL':  {73:(819,823),74:(817,822),75:(816,821),76:(814,819),77:(811,816),78:(807,812),79:(806,811),80:(804,810),81:(801,807),82:(799,805),83:(793,799),84:(791,797),85:(789,796),86:(787,794),87:(784,791),88:(779,786),89:(773,779),90:(771,778),91:(768,776),92:(765,773),93:(759,767),94:(752,762),95:(747,757),96:(745,755),97:(744,754),98:(735,745)},
 'LF':  {73:(838,842),74:(838,842),75:(837,841),76:(837,841),77:(837,841),78:(836,840),79:(836,840),80:(836,840),81:(835,840),82:(835,840),83:(836,840),84:(836,840),85:(835,840),86:(835,840),87:(833,840),88:(833,839),89:(832,839),90:(832,838),91:(832,838),92:(831,838),93:(830,837),94:(829,836),95:(828,835),96:(827,834),97:(827,834),98:(824,832)},
 'RH':  {73:(957,965),74:(959,966),75:(961,968),76:(963,970),77:(966,973),78:(968,976),79:(972,979),80:(974,981),81:(977,984),82:(979,986),83:(986,994),84:(988,996),85:(990,998),86:(993,1002),87:(994,1003),88:(998,1009),89:(1001,1011),90:(1002,1012),91:(1003,1013),92:(1006,1016),93:(1010,1021),94:(1013,1024),95:(1016,1027),96:(1017,1028),97:(1018,1029),98:(1023,1035)},
 'RF':  {73:(969,976),74:(970,977),75:(972,979),76:(975,981),77:(978,984),78:(984,990),79:(986,992),80:(988,994),81:(991,997),82:(994,1000),83:(1000,1007),84:(1002,1009),85:(1004,1011),86:(1006,1013),87:(1010,1017),88:(1015,1022),89:(1019,1026),90:(1020,1027),91:(1021,1028),92:(1024,1031),93:(1029,1037),94:(1033,1040),95:(1036,1044),96:(1037,1045),97:(1038,1046),98:(1044,1052)},
}


def Vof(t):
    f = cv2.imread(f'{SRC}/s{t:03d}.png')
    return f, cv2.GaussianBlur(f.max(2).astype(np.float32), (0, 0), 0.6)


def edges(V, a, b, rows, need_left=True, need_right=True):
    """sub-pixel left/right edge of the dark bar seeded at columns a..b, on the given rows; None if it cannot be measured"""
    if len(rows) < 5: return None
    xa, xb = a - 7, b + 8
    P = V[rows, xa:xb].mean(0)
    i0, i1 = a - xa, b - xa
    bar = float(P[i0 + 1:i1].min()) if i1 - i0 > 2 else float(P[i0:i1 + 1].min())
    out = []
    for side in (-1, 1):
        if side < 0:
            seg = P[max(0, i0 - 5):i0 + 1]; lvl = float(seg.max())
            if lvl - bar < 40:
                if need_left: return None
                out.append(None); continue
            h = (lvl + bar) / 2; x = None
            for i in range(i0 + 2, max(0, i0 - 5), -1):
                if P[i] <= h < P[i - 1]: x = (i - 1) + (P[i - 1] - h) / (P[i - 1] - P[i]) + 0.5; break
            out.append(None if x is None else xa + x)
        else:
            seg = P[i1:min(len(P), i1 + 6)]; lvl = float(seg.max())
            if lvl - bar < 40:
                if need_right: return None
                out.append(None); continue
            h = (lvl + bar) / 2; x = None
            for i in range(i1 - 2, min(len(P) - 1, i1 + 5)):
                if P[i] <= h < P[i + 1]: x = i + (h - P[i]) / (P[i + 1] - P[i]) + 0.5; break
            out.append(None if x is None else xa + x)
    return out


def clear_rows(V, a, b, ya, yb, left=True, right=True, wall=145, dark=115):
    c = V[ya:yb, a + 1:b].mean(1) if b - a > 2 else V[ya:yb, a:b + 1].mean(1)
    ok = c < dark
    if left: ok &= V[ya:yb, a - 5:a - 2].mean(1) > wall
    if right: ok &= V[ya:yb, b + 3:b + 6].mean(1) > wall
    return np.arange(ya, yb)[ok]


def vspan(V, a, b, side, ya=470, yb=716):
    """rows where the bar a..b is dark against the wall on the given side (+1 right, -1 left)"""
    c = V[ya:yb, a + 1:b].mean(1)
    w = V[ya:yb, b + 3:b + 6].mean(1) if side > 0 else V[ya:yb, a - 5:a - 2].mean(1)
    return ya, (w - c > 50), (w > 140)


if __name__ == '__main__':
    res = {}
    for t in range(T0, T1 + 1):
        f, V = Vof(t); r = {}
        for k in ('LHO', 'HL', 'LF', 'RH', 'RF'):
            a, b = SEED[k][t]
            if k == 'LHO':
                rows = clear_rows(V, a, b, 520, 700, left=False, right=True); e = edges(V, a, b, rows, need_left=False)
            elif k == 'HL':
                rows = clear_rows(V, a, b, 696, 714, left=False, right=True); e = edges(V, a, b, rows, need_left=False)
            elif k == 'LF':
                rows = clear_rows(V, a, b, 600, 714); e = edges(V, a, b, rows)
            elif k == 'RH':
                rows = clear_rows(V, a, b, 540, 690, left=True, right=False); e = edges(V, a, b, rows, need_right=False)
            else:
                rows = clear_rows(V, a, b, 690, 714); e = edges(V, a, b, rows)
            x0 = float(a) if e is None or e[0] is None else float(e[0])
            x1 = float(b + 1) if e is None or e[1] is None else float(e[1])
            if abs(x0 - a) > 2.5: x0 = float(a)
            if abs(x1 - (b + 1)) > 2.5: x1 = float(b + 1)
            r[k] = [round(x0, 2), round(x1, 2), len(rows)]
        # vertical ends: bottom of both handles, top of the right one
        a, b = SEED['RH'][t]
        ya, dk, wl = vspan(V, a, b, -1)
        idx = np.where(dk)[0]
        # longest run of dark rows (allowing gaps of 3 rows)
        runs = []; s = idx[0]; p = idx[0]
        for i in idx[1:]:
            if i - p > 4: runs.append((s, p)); s = i
            p = i
        runs.append((s, p)); s, p = max(runs, key=lambda q: q[1] - q[0])
        r['RH'] += [int(ya + s), int(ya + p + 1), bool(s > 0 and wl[max(0, s - 3):s].mean() > 0.6)]
        a, b = SEED['LHO'][t]
        ya, dk, wl = vspan(V, a, b, +1)
        idx = np.where(dk)[0]; r['LHO'] += [int(ya + idx[0]) if len(idx) else None, int(ya + idx[-1] + 1) if len(idx) else None]
        res[t] = r
        print(t, ' '.join(f"{k}:{v[0]:.1f}-{v[1]:.1f}({v[2]})" + (f" y{v[3]}-{v[4]}" if len(v) > 3 else '') + (f" top{'ok' if v[5] else '?'}" if len(v) > 5 else '') for k, v in r.items()))
    json.dump(res, open(os.path.join(HERE, 'early_raw.json'), 'w'))
