"""Fix both door handles to their door leaves: two short bronze arms per handle, near its top and bottom,
running from the handle to the bronze stile of the leaf it belongs to."""
import cv2, numpy as np, json, os, sys
from scipy.signal import savgol_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import early
H, W = 1080, 1920
G = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geo.json')))
S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snap.json')))
SRC = {'w1': '/tmp/e', 'w2': '/tmp/w2all'}
IN = {'w1': '/tmp/hf/w1', 'w2': '/tmp/hf/w2'}
OUT = {'w1': '/tmp/hf2/w1', 'w2': '/tmp/hf2/w2'}
for d in OUT.values(): os.makedirs(d, exist_ok=True)
NFR = {'w1': 150, 'w2': 90}


def smooth_series(clip, key):
    ts = sorted(int(t) for t in S[clip] if key in S[clip][t])
    x0 = np.array([S[clip][str(t)][key][0] for t in ts]); x1 = np.array([S[clip][str(t)][key][1] for t in ts])
    if len(ts) >= 7: x0 = savgol_filter(x0, 7, 2); x1 = savgol_filter(x1, 7, 2)
    return {t: (a, b) for t, a, b in zip(ts, x0, x1)}


RF = {c: smooth_series(c, 'RF') for c in ('w1', 'w2')}
LF = {c: smooth_series(c, 'LF') for c in ('w1', 'w2')}


def xfade(clip, t):
    if clip == 'w1' and t in early.E: return early.ramp(t)
    return 1.0


def coverage(xa, xb, ya, yb, box, k=4):
    """anti-aliased coverage of the rectangle [xa,xb]x[ya,yb] inside box (bx0,by0,bx1,by1)"""
    bx0, by0, bx1, by1 = box
    w, h = bx1 - bx0, by1 - by0
    m = np.zeros((h * k, w * k), np.float32)
    X0, X1 = int(round((xa - bx0) * k)), int(round((xb - bx0) * k))
    Y0, Y1 = int(round((ya - by0) * k)), int(round((yb - by0) * k))
    m[max(0, Y0):max(0, Y1), max(0, X0):max(0, X1)] = 1
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA)


def draw_arm(img, xa, xb, yc, th, base, alpha_mod=None):
    """a short horizontal bronze arm from xa to xb, centred on yc, th thick, lit from above"""
    if xb - xa < 0.8: return img
    ya, yb = yc - th / 2, yc + th / 2
    bx0, by0 = int(np.floor(xa)) - 1, int(np.floor(ya)) - 1
    bx1, by1 = int(np.ceil(xb)) + 2, int(np.ceil(yb)) + 2
    bx0, by0, bx1, by1 = max(0, bx0), max(0, by0), min(W, bx1), min(H, by1)
    if bx1 <= bx0 or by1 <= by0: return img
    cov = coverage(xa, xb, ya, yb, (bx0, by0, bx1, by1))
    ys = (np.arange(by0, by1) + 0.5 - ya) / max(th, 1e-3)
    v = np.clip(ys, 0, 1)[:, None]
    # round bar: bright line a quarter down, dark underside
    shade = 1.0 + 0.55 * np.exp(-((v - 0.25) / 0.14) ** 2) - 0.55 * v ** 1.5
    col = np.clip(base[None, None, :] * shade[..., None], 0, 255)
    col = np.broadcast_to(col, (by1 - by0, bx1 - bx0, 3))
    a = cov
    if alpha_mod is not None: a = a * alpha_mod[by0:by1, bx0:bx1]
    reg = img[by0:by1, bx0:bx1].astype(np.float32)
    img[by0:by1, bx0:bx1] = np.clip(reg * (1 - a[..., None]) + col * a[..., None], 0, 255).astype(np.uint8)
    return img


def bar_colour(img, x0, x1, y, th):
    a, b = int(x0 + 0.3 * (x1 - x0)), int(np.ceil(x1 - 0.3 * (x1 - x0)))
    b = max(b, a + 1)
    r = img[int(max(0, y - 2 * th)):int(min(H, y + 2 * th)), a:b].reshape(-1, 3).astype(np.float32)
    return np.median(r, axis=0)


def early_frame(t):
    """the walk up to the door, behind the olive tree: the same arms, hidden where the tree stands in front of them"""
    img = cv2.imread(f'{IN["w1"]}/s{t:03d}.png'); orig = cv2.imread(f'{SRC["w1"]}/s{t:03d}.png')
    g = early.geo(t); x0, x1, y0, y1 = g['RH']; m = g['m']; L = y1 - y0
    th = float(np.clip(0.42 * (x1 - x0), 2.0, 46))
    al = early.ramp(t)
    right = al * (1 - early.occlusion_right(orig, t)); left = al * (1 - early.occlusion(orig, t))
    lx0 = 2 * m - x1
    for y in (y0 + 0.1 * L, y1 - 0.1 * L):
        col = bar_colour(img, x0, x1, y, th)
        if g['RF'][0] > x1 + 0.5: img = draw_arm(img, x1 - 0.5, g['RF'][0] + 0.5, y, th, col, right)
        if lx0 > g['LF'][1] + 0.5: img = draw_arm(img, g['LF'][1] - 0.5, lx0 + 0.5, y, th, col, left)
    return img


def frame(clip, t):
    if clip == 'w1' and t in early.E: return early_frame(t)
    img = cv2.imread(f'{IN[clip]}/s{t:03d}.png')
    rh = G[clip]['RH'].get(str(t)); m = G[clip]['m'].get(str(t))
    if rh is None or m is None: return img
    x0, x1, y0, y1 = rh; L = y1 - y0; bw = x1 - x0
    th = float(np.clip(0.42 * bw, 2.0, 46))
    ys = [y0 + 0.1 * L, y1 - 0.1 * L]
    al = xfade(clip, t)
    occ = None
    if clip == 'w1' and t <= 106:
        V = cv2.imread(f'{SRC[clip]}/s{t:03d}.png').max(2).astype(np.float32)
        occ = 1 - np.clip((150 - V) / 40, 0, 1)
    # right handle -> right leaf's stile
    rf = RF[clip].get(t)
    if rf is not None and rf[0] > x1 + 0.5:
        for y in ys:
            if 0 < y < H - 1:
                img = draw_arm(img, x1 - 0.5, rf[0] + 0.5, y, th, bar_colour(img, x0, x1, y, th))
    # left handle (the mirror of the right one) -> left leaf's stile
    lf = LF[clip].get(t)
    lx0 = 2 * m - x1
    if lf is not None and lx0 > lf[1] + 0.5:
        mod = None
        if al < 1 or occ is not None:
            mod = np.full((H, W), al, np.float32)
            if occ is not None: mod *= occ
        for y in ys:
            if 0 < y < H - 1:
                img = draw_arm(img, lf[1] - 0.5, lx0 + 0.5, y, th, bar_colour(img, x0, x1, y, th), mod)
    return img


if __name__ == '__main__':
    clips = sys.argv[1:] or ['w1', 'w2']
    for clip in clips:
        for t in range(NFR[clip]):
            cv2.imwrite(f'{OUT[clip]}/s{t:03d}.png', frame(clip, t))
        print(clip, 'done')
