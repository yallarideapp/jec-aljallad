import cv2, numpy as np, json, os, sys
from scipy.signal import savgol_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from erase7 import erase
from overlay import SRC
H, W = 1080, 1920
S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snap.json')))
OUT = {'w1': '/tmp/hf/w1', 'w2': '/tmp/hf/w2'}
for d in OUT.values(): os.makedirs(d, exist_ok=True)
NFR = {'w1': 150, 'w2': 90}
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)


def series(clip, key, i, ts):
    return np.array([S[clip][str(t)][key][i] for t in ts], np.float64)


def smooth(v, win=7):
    if len(v) < win: return v
    return savgol_filter(v, win, 2, mode='interp')


# ---------- geometry per frame (smoothed) ----------
geo = {}
for clip in ('w1', 'w2'):
    ts_all = sorted(int(t) for t in S[clip])
    g = {}
    for key in ('LHO', 'RH'):
        ts = [t for t in ts_all if key in S[clip][str(t)]]
        if clip == 'w2' and key == 'LHO': ts = [t for t in ts if t <= 47]
        vals = [smooth(series(clip, key, i, ts)) for i in range(4)]
        if key == 'RH' and clip == 'w2':      # the last frames move fast: keep them as measured
            raw = [series(clip, key, i, ts) for i in range(4)]
            for i in range(4): vals[i][-4:] = raw[i][-4:]
        g[key] = {t: tuple(v[k] for v in vals) for k, t in enumerate(ts)}
    ts = [t for t in ts_all if 'LF' in S[clip][str(t)] and 'RF' in S[clip][str(t)]]
    m = np.array([(S[clip][str(t)]['LF'][0] + S[clip][str(t)]['LF'][1] + S[clip][str(t)]['RF'][0] + S[clip][str(t)]['RF'][1]) / 4 for t in ts])
    m = smooth(m, 9)
    g['m'] = dict(zip(ts, m))
    if clip == 'w2':          # the top and bottom of the right handle, read off the frames once it is close
        from kf import KF
        from overlay import interp
        for t in list(g['RH']):
            if t >= 46:
                k = interp(KF['w2']['RH'], t)
                if k is not None: g['RH'][t] = (g['RH'][t][0], g['RH'][t][1], k[2], k[3])
    g['LF'] = {t: (S[clip][str(t)]['LF'][0], S[clip][str(t)]['LF'][1]) for t in ts}
    if clip == 'w2':
        g['m'][63] = 862.0; g['m'][64] = 858.0
    geo[clip] = g
# the left handle's last frames, read off the frames by hand (it leaves the screen fast; 47-48 were not tracked)
for t, v in {43: (200, 254, 345, 1058), 44: (176, 236, 345, 1070), 45: (158, 222, 340, 1080), 46: (116, 188, 340, 1080),
             47: (63, 142, 240, 1080), 48: (40, 100, 240, 1080)}.items():
    geo['w2']['LHO'][t] = tuple(float(x) for x in v)
json.dump({c: {k: {str(t): v for t, v in d.items()} for k, d in g.items()} for c, g in geo.items()}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geo.json'), 'w'))

# ---------- when ----------
def xfade(clip, t):
    if clip == 'w2': return 1.0
    u = np.clip((t - 98) / 6.0, 0, 1)     # before frame 99 the old handle is behind the tree trunk
    return float(u * u * (3 - 2 * u))

EDIT = {'w1': range(99, 150), 'w2': range(0, 65)}
ERASE_FSR = {'w1': range(99, 150), 'w2': range(0, 49)}
GHOST_FIX = range(49, 53)
ERASE_PROP = {'w1': range(0), 'w2': range(0)}


def margins(x0, x1, y0, y1):
    bw = x1 - x0
    return max(6.0, 0.25 * bw), 7 + 0.025 * (y1 - y0)


def box(x0, x1, y0, y1):
    mx, my = margins(x0, x1, y0, y1)
    return (int(max(0, np.floor(x0 - mx))), int(min(W - 1, np.ceil(x1 + mx))),
            int(max(0, np.floor(y0 - my))), int(min(H - 1, np.ceil(y1 + my))))


def propagate(prev_clean, prev_orig, cur_orig, x0, x1, y0, y1):
    a, b, c, d = box(x0, x1, y0, y1)
    pad = 160
    X0, X1, Y0, Y1 = max(0, a - pad), min(W, b + pad + 1), max(0, c - 60), min(H, d + 61)
    g1 = cv2.cvtColor(cur_orig[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
    g0 = cv2.cvtColor(prev_orig[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
    fl = dis.calc(g1, g0, None)          # cur pixel p is at p + fl(p) in prev
    la, lb, lc, ld = a - X0, b - X0, c - Y0, d - Y0
    e = 4                                # exclude a few pixels around the bar from the background flow
    ext_a, ext_b = la - e, lb + e
    rows = np.arange(lc, ld + 1)
    def side(xa, xb):
        xa, xb = max(0, xa), min(fl.shape[1], xb)
        if xb - xa < 1: return None
        return np.median(fl[lc:ld + 1, xa:xb], axis=1)
    L = side(ext_a - 4, ext_a); R = side(ext_b + 1, ext_b + 5)
    if L is None: L = R
    if R is None: R = L
    k = 9
    L = cv2.GaussianBlur(L.astype(np.float32).reshape(-1, 1, 2), (1, k), 0).reshape(-1, 2)
    R = cv2.GaussianBlur(R.astype(np.float32).reshape(-1, 1, 2), (1, k), 0).reshape(-1, 2)
    xs = np.arange(ext_a, ext_b + 1)
    u = ((xs - ext_a) / max(1, ext_b - ext_a))[None, :, None]
    F = L[:, None, :] * (1 - u) + R[:, None, :] * u
    gx, gy = np.meshgrid(xs, rows)
    mapx = (gx + F[..., 0] + X0).astype(np.float32); mapy = (gy + F[..., 1] + Y0).astype(np.float32)
    Wp = cv2.remap(prev_clean, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    cur = cur_orig[Y0 + lc:Y0 + ld + 1, X0 + ext_a:X0 + ext_b + 1].astype(np.float32)
    # seam: match the warped fill to the current frame on both sides, row by row
    nl = min(4, la - ext_a) if la - ext_a > 0 else 0
    dl = (cur[:, :e] - Wp[:, :e]).mean(1) if ext_a >= 0 else None
    dr = (cur[:, -e:] - Wp[:, -e:]).mean(1)
    if dl is None: dl = dr
    dl = cv2.GaussianBlur(dl.reshape(-1, 1, 3), (1, 15), 0).reshape(-1, 3)
    dr = cv2.GaussianBlur(dr.reshape(-1, 1, 3), (1, 15), 0).reshape(-1, 3)
    D = dl[:, None, :] * (1 - u) + dr[:, None, :] * u
    fill = np.clip(Wp + D, 0, 255)
    out = cur_orig.copy().astype(np.float32)
    # place, feathered over the excluded rim
    m = np.zeros((ld - lc + 1, ext_b - ext_a + 1), np.float32)
    m[:, e:-e] = 1
    m = cv2.GaussianBlur(m, (0, 0), 1.2); m[:, e + 1:-e - 1] = 1
    xa0 = X0 + ext_a
    sl = (slice(Y0 + lc, Y0 + ld + 1), slice(max(0, xa0), X0 + ext_b + 1))
    cx = max(0, -xa0)
    region = out[sl]
    mm = m[:, cx:][..., None]
    out[sl] = region * (1 - mm) + fill[:, cx:] * mm
    # soften the top and bottom joins
    return np.clip(out, 0, 255).astype(np.uint8)


def paste(dst, orig, rh, m, alpha, occ_rows=None, lf=None):
    x0, x1, y0, y1 = rh
    sa, sb = int(np.floor(x0)) - 3, int(np.ceil(x1)) + 4
    sc, sd = int(np.floor(y0)) - 3, int(np.ceil(y1)) + 4
    sa, sb, sc, sd = max(0, sa), min(W, sb), max(0, sc), min(H, sd)
    xs = np.arange(sa, sb) + 0.5; ys = np.arange(sc, sd) + 0.5
    ax = np.clip(np.minimum(xs - x0, x1 - xs) + 0.5, 0, 1)
    ay = np.clip(np.minimum(ys - y0, y1 - ys) + 0.5, 0, 1)
    if y1 >= H - 1.5: ay[ys > y0] = np.maximum(ay[ys > y0], (ys[ys > y0] - y0 > 0.5))
    if y0 <= 0.5: ay[ys < y1] = np.maximum(ay[ys < y1], (y1 - ys[ys < y1] > 0.5))
    A = (ay[:, None] * ax[None, :]).astype(np.float32)
    layer = np.zeros((H, W, 3), np.float32); amap = np.zeros((H, W), np.float32)
    layer[sc:sd, sa:sb] = orig[sc:sd, sa:sb]; amap[sc:sd, sa:sb] = A
    M = np.float32([[-1, 0, 2 * m], [0, 1, 0]])
    layer = cv2.warpAffine(layer, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    amap = cv2.warpAffine(amap, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    if occ_rows is not None:
        V = orig.max(2).astype(np.float32)
        occ = np.clip((150 - V) / 40, 0, 1)
        if lf is not None:
            occ[:, int(lf[0]) - 2:int(lf[1]) + 3] = 0
        amap = amap * (1 - occ)
    amap = amap * alpha
    out = dst.astype(np.float32) * (1 - amap[..., None]) + layer * amap[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    for clip in (sys.argv[1:] or ['w1', 'w2']):
        g = geo[clip]; prev_clean = prev_orig = None
        for t in range(NFR[clip]):
            orig = cv2.imread(f'{SRC[clip]}/s{t:03d}.png')
            if t not in EDIT[clip]:
                cv2.imwrite(f'{OUT[clip]}/s{t:03d}.png', orig); continue
            al = xfade(clip, t)
            clean = orig
            tg = f'/tmp/doorfix/tclean3/{clip}_{t:03d}.png'
            if clip == 'w2' and t in GHOST_FIX and os.path.exists(tg):   # the handle's top lingering on the glass
                clean = cv2.imread(tg)
            elif t in g['LHO']:
                x0, x1, y0, y1 = g['LHO'][t]
                tc = f'/tmp/doorfix/tclean3/{clip}_{t:03d}.png'
                if t in ERASE_FSR[clip] and os.path.exists(tc):
                    clean = cv2.imread(tc)
                elif t in ERASE_FSR[clip]:
                    mx, my = margins(x0, x1, y0, y1)
                    if clip == 'w1' and t < 104:      # the tree trunk stands just left of the handle here
                        import erase_shift
                        clean = erase_shift.erase(orig, x0, x1, y0, y1, mx, my)
                    else:
                        clean = erase(orig, x0, x1, y0, y1, mx, my)
                elif t in ERASE_PROP[clip] and prev_clean is not None:
                    clean = propagate(prev_clean, prev_orig, orig, x0, x1, y0, y1)
            prev_clean, prev_orig = clean, orig
            frame = (orig.astype(np.float32) * (1 - al) + clean.astype(np.float32) * al).astype(np.uint8) if al < 1 else clean.copy()
            if t in g['RH'] and t in g['m']:
                occ = (clip == 'w1' and t <= 106)
                frame = paste(frame, orig, g['RH'][t], g['m'][t], al, occ_rows=occ or None, lf=g['LF'].get(t))
            cv2.imwrite(f'{OUT[clip]}/s{t:03d}.png', frame)
        print(clip, 'done')
