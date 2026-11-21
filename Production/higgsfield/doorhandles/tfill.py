"""Fill the place of the old left handle with what is really behind the glass there, taken from a nearby frame in
which the same part of the lobby is not hidden by the handle (the handle is on the door, the lobby is further away,
so they slide past each other as the camera walks). The nearby frame is registered on the lobby around the hole,
then blended in with Poisson blending so the light matches."""
import cv2, numpy as np, json, os, sys
H, W = 1080, 1920
G = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geo.json')))
S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snap.json')))
SRC = {'w1': '/tmp/e', 'w2': '/tmp/w2all'}
OUT = '/tmp/doorfix/tclean'; os.makedirs(OUT, exist_ok=True)
SEQ = [('w1', t) for t in range(150)] + [('w2', t) for t in range(90)]
IDX = {k: i for i, k in enumerate(SEQ)}
sift = cv2.SIFT_create(4000, contrastThreshold=0.015)
_c = {}


def img(k):
    if k not in _c: _c[k] = cv2.imread(f'{SRC[k[0]]}/s{k[1]:03d}.png')
    return _c[k]


def lho(k):
    v = G[k[0]]['LHO'].get(str(k[1]))
    return None if v is None else tuple(v)


def lf(k):
    v = S[k[0]].get(str(k[1]), {}).get('LF')
    return None if v is None else (v[0], v[1])


def hole_box(b):
    x0, x1, y0, y1 = b; bw = x1 - x0
    mx, my = max(6.0, 0.25 * bw) + 2, 7 + 0.025 * (y1 - y0) + 2
    return (int(max(0, np.floor(x0 - mx))), int(min(W - 1, np.ceil(x1 + mx))),
            int(max(0, np.floor(y0 - my))), int(min(H - 1, np.ceil(y1 + my))))


def feat_mask(k, a, b, c, d):
    """lobby seen through the glass around the hole: right of the hole and above / below it, not the door parts"""
    m = np.zeros((H, W), np.uint8)
    bw = b - a
    xr = min(W, b + max(160, 6 * bw)); ya, yb = max(0, c - 120), min(H, d + 120)
    m[ya:yb, a:xr] = 255
    m[c - 4:d + 5, a - 4:b + 5] = 0
    f = lf(k)
    if f is not None: m[:, max(0, int(f[0]) - 6):int(f[1]) + 7] = 0
    return m


def register(kt, ks, a, b, c, d):
    """affine map taking source frame ks to target frame kt, fitted on the lobby around the hole (on crops)"""
    bw = b - a
    X0, X1 = max(0, a - 30), min(W, b + max(220, 7 * bw)); Y0, Y1 = max(0, c - 160), min(H, d + 160)
    P = 240
    SX0, SX1, SY0, SY1 = max(0, X0 - P), min(W, X1 + P), max(0, Y0 - P), min(H, Y1 + P)
    gt = cv2.cvtColor(img(kt)[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY); gs = cv2.cvtColor(img(ks)[SY0:SY1, SX0:SX1], cv2.COLOR_BGR2GRAY)
    mt = feat_mask(kt, a, b, c, d)[Y0:Y1, X0:X1]
    ms = np.full(gs.shape, 255, np.uint8)
    bs = lho(ks)
    if bs is not None:
        sa, sb, sc, sd = hole_box(bs); ms[max(0, sc - SY0):max(0, sd - SY0 + 1), max(0, sa - 8 - SX0):max(0, sb + 8 - SX0 + 1)] = 0
    f = lf(ks)
    if f is not None: ms[:, max(0, int(f[0]) - 6 - SX0):max(0, int(f[1]) + 7 - SX0)] = 0
    kt_, dt = sift.detectAndCompute(gt, mt); ks_, ds = sift.detectAndCompute(gs, ms)
    if dt is None or ds is None or len(kt_) < 8 or len(ks_) < 8: return None, 0
    mm = cv2.BFMatcher().knnMatch(dt, ds, k=2)
    good = [p[0] for p in mm if len(p) == 2 and p[0].distance < 0.8 * p[1].distance]
    if len(good) < 8: return None, 0
    pt = np.float32([kt_[g.queryIdx].pt for g in good]) + [X0, Y0]; ps = np.float32([ks_[g.trainIdx].pt for g in good]) + [SX0, SY0]
    A, inl = cv2.estimateAffine2D(ps, pt, method=cv2.RANSAC, ransacReprojThreshold=1.5, maxIters=4000, confidence=0.999)
    if A is None: return None, 0
    return np.vstack([A, [0, 0, 1]]), int(inl.sum())


def ring_err(kt, Hm, a, b, c, d):
    """how well the registered source matches the target on a band right of / above / below the hole"""
    pad = 22
    X0, X1, Y0, Y1 = max(0, a - 2), min(W, b + pad), max(0, c - pad), min(H, d + pad)
    w = cv2.warpPerspective(img(ks_cur[0]), Hm, (W, H), flags=cv2.INTER_LINEAR)
    m = np.zeros((H, W), bool); m[Y0:Y1, X0:X1] = True; m[c:d + 1, a - 2:b + 1] = False
    t = img(kt).astype(np.float32); s = w.astype(np.float32)
    return float(np.abs(t[m] - s[m]).mean())


ks_cur = [None]


def usable(kt, ks, Hm, a, b, c, d):
    """the hole of kt, seen in ks, must lie in the lobby: right of ks's handle, left of the door's free stile"""
    corners = np.float32([[a, c], [b, c], [a, d], [b, d], [(a + b) / 2, (c + d) / 2]]).reshape(-1, 1, 2)
    p = cv2.perspectiveTransform(corners, np.linalg.inv(Hm)).reshape(-1, 2)
    if p[:, 0].min() < 2 or p[:, 0].max() > W - 3 or p[:, 1].min() < 0 or p[:, 1].max() > H - 1: return False
    bs = lho(ks)
    if bs is None: return False
    sa, sb, sc, sd = hole_box(bs)
    if not (p[:, 0].min() > sb + 2 or p[:, 0].max() < sa - 70): return False
    f = lf(ks)
    if f is not None and p[:, 0].max() >= f[0] - 3: return False
    return True


def fill(kt, base):
    b = lho(kt)
    if b is None: return None
    a, bb, c, d = hole_box(b)
    i = IDX[kt]; best = None
    for off in sorted(range(-30, 31), key=abs):
        if abs(off) < 2: continue
        j = i + off
        if j < 0 or j >= len(SEQ): continue
        ks = SEQ[j]
        if lho(ks) is None: continue
        Hm, n = register(kt, ks, a, bb, c, d)
        if Hm is None or n < 8: continue
        if not usable(kt, ks, Hm, a, bb, c, d): continue
        ks_cur[0] = ks; e = ring_err(kt, Hm, a, bb, c, d)
        if e > 14: continue
        best = (ks, Hm, n, e); break
    if best is None: return None
    ks, Hm, n, e = best
    warped = cv2.warpPerspective(img(ks), Hm, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    pad = 24
    X0, X1, Y0, Y1 = max(0, a - pad), min(W, bb + pad + 1), max(0, c - pad), min(H, d + pad + 1)
    dst = base[Y0:Y1, X0:X1].copy(); src = warped[Y0:Y1, X0:X1].copy()
    mask = np.zeros(dst.shape[:2], np.uint8); mask[c - Y0:d - Y0 + 1, a - X0:bb - X0 + 1] = 255
    center = ((X1 - X0) // 2, (Y1 - Y0) // 2)
    try:
        out = cv2.seamlessClone(src, dst, mask, center, cv2.NORMAL_CLONE)
    except cv2.error:
        return None
    res = base.copy(); res[Y0:Y1, X0:X1] = out
    return res, ks, (n, round(e, 1))


if __name__ == '__main__':
    ks_ = [k for k in SEQ if lho(k) is not None and ((k[0] == 'w1' and k[1] >= 99) or k[0] == 'w2')]
    if len(sys.argv) > 1: ks_ = [k for k in ks_ if k[0] == sys.argv[1] and (len(sys.argv) < 3 or str(k[1]) in sys.argv[2].split(','))]
    log = {}
    for k in ks_:
        r = fill(k, img(k))
        if r is None: log[f'{k[0]}{k[1]}'] = None; continue
        res, ks, n = r
        cv2.imwrite(f'{OUT}/{k[0]}_{k[1]:03d}.png', res)
        log[f'{k[0]}{k[1]}'] = (f'{ks[0]}{ks[1]}', n)
    print(log)
