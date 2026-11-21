"""Fill the left glass of the w2 lobby shot where the old handle was, for the frames where
the handle dissolves (w2 40..52), and remove the translucent top of the handle that
lingers there in 48..52.

For each frame (last to first) the lobby behind the hole is taken from later frames
(originals, and frames already cleaned here), each aligned with a local homography.
Pixels are taken from the best-matching source where that source shows clean lobby
(not a handle, its ghost, a stile or a frame edge), the next source fills what is left,
and the result is blended in with Poisson cloning.
Writes /tmp/doorfix/tclean3/w2_TTT.png (the clean base that build.py uses)."""
import cv2, numpy as np, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tfill as T

GEO = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geo.json')))['w2']
SRC = '/tmp/w2all'
OUT = '/tmp/doorfix/tclean3'
sift = cv2.SIFT_create(8000, contrastThreshold=0.01)

GHOST = {48: (32, 140, 240, 460), 49: (36, 110, 265, 425), 50: (22, 100, 265, 425),
         51: (20, 96, 265, 425), 52: (0, 70, 265, 425)}
K = lambda n: np.ones((n, n), np.uint8)


def orig(t):
    return cv2.imread(f'{SRC}/s{t:03d}.png')


# the tracked box misses the handle's shaded left face (40..42) and its top cap (45, 46)
WIDEN = {40: (12, 10, 0), 41: (14, 12, 0), 42: (14, 12, 0), 45: (4, 4, 30), 46: (4, 4, 40)}


def hole_mask(t):
    m = np.zeros((1080, 1920), np.uint8)
    if str(t) in GEO['LHO'] and t <= 48:
        a, b, c, d = T.hole_box(tuple(GEO['LHO'][str(t)]))
        l, r, u = WIDEN.get(t, (0, 0, 0))
        a, b, c = a - l, b + r, c - u
        m[max(0, c):d + 1, max(0, a):b + 1] = 255
    if t in GHOST:
        x0, x1, y0, y1 = GHOST[t]
        m[y0:y1, x0:x1] = 255
    return m


def hinge_stile(img, xmax):
    """right edge of the dark hinge-side stile at the left of the frame, -1 if none"""
    V = img[650:900, :max(1, int(xmax))].max(2).astype(np.float32).mean(0)
    for x in range(len(V) - 1, -1, -1):
        if V[x] < 140:
            return x
    return -1


def bad_mask(t, img, cleaned):
    """pixels of frame t that are not lobby seen through clear glass"""
    m = np.zeros((1080, 1920), np.uint8) if cleaned else cv2.dilate(hole_mask(t), K(11))
    s = str(t)
    if s in GEO['LF']:
        x0, x1 = GEO['LF'][s]; m[:, max(0, int(x0) - 10):int(x1) + 11] = 255
    if s in GEO['RH']:
        x0, x1, y0, y1 = GEO['RH'][s]; m[max(0, int(y0) - 12):int(y1) + 13, max(0, int(x0) - 12):int(x1) + 13] = 255
    if t <= 48:
        xm = GEO['LHO'][s][0] if s in GEO['LHO'] else 400
        h = hinge_stile(img, xm)
        if h >= 0:
            m[:, :h + 8] = 255
    return m


# (feature rows, ramp rows, zone above the ramp?): ceiling and floor get their own alignment
ZONES = [((235, 430), (330, 380), True), ((650, 1080), (700, 760), False)]
REFINE = True
REF_BOTTOM = (430, 480)


def warp(img, bad, H):
    w = cv2.warpPerspective(img, H, (1920, 1080), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    ok = cv2.warpPerspective(255 - bad, H, (1920, 1080), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return w, cv2.erode(ok, K(3)) > 0


def refine(w, ok, tgt, hm, tbad, R=8):
    """Per-row-band small shifts so the lobby inside the hole lines up with the lobby just
    left and right of it (the ceiling, wall and floor sit at different depths)."""
    rows = np.where(hm.any(1))[0]
    y0, y1 = rows.min(), rows.max()
    L = np.full(1080, -1); Rr = np.full(1080, -1)
    for y in rows:
        xs = np.where(hm[y] > 0)[0]; L[y], Rr[y] = xs.min(), xs.max()
    tg = tgt.astype(np.float32); wf = w
    centers = [c for c in range(y0, y1 + 1, 16) if c < REF_BOTTOM[1] + 40] or [y0]
    sh = []
    for yc in centers:
        ya, yb = max(y0, yc - 24), min(y1, yc + 24)
        pts_y, pts_x = [], []
        for y in range(ya, yb + 1):
            for x in list(range(max(0, L[y] - 40), L[y] - 3)) + list(range(Rr[y] + 4, min(1920, Rr[y] + 41))):
                pts_y.append(y); pts_x.append(x)
        py = np.array(pts_y); px = np.array(pts_x)
        if len(py) == 0:
            sh.append((0, 0, False)); continue
        keep = (tbad[py, px] == 0)
        py, px = py[keep], px[keep]
        if len(py) < 300:
            sh.append((0, 0, False)); continue
        T0 = tg[py, px]
        best = None; base = None
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                qy = np.clip(py + dy, 0, 1079); qx = np.clip(px + dx, 0, 1919)
                v = ok[qy, qx]
                if v.mean() < 0.9:
                    continue
                d = T0[v] - wf[qy, qx][v]
                e = float(np.abs(d - d.mean(0)).mean())
                if dx == 0 and dy == 0:
                    base = e
                if best is None or e < best[0]:
                    best = (e, dx, dy)
        if best is None or base is None or best[0] > base - 0.8:
            sh.append((0, 0, base is not None)); continue
        sh.append((best[1], best[2], True))
    cy = np.array(centers, np.float32)
    dx = np.array([s_[0] for s_ in sh], np.float32); dy = np.array([s_[1] for s_ in sh], np.float32)
    from scipy.ndimage import median_filter, gaussian_filter1d
    if len(dx) >= 3:
        dx = gaussian_filter1d(median_filter(dx, 3, mode='nearest'), 1.2, mode='nearest')
        dy = gaussian_filter1d(median_filter(dy, 3, mode='nearest'), 1.2, mode='nearest')
    yy = np.arange(1080, dtype=np.float32)
    DX = np.interp(yy, cy, dx); DY = np.interp(yy, cy, dy)
    # only the ceiling band: lower down, row-wise shifts bend the pillars
    lim = np.clip((REF_BOTTOM[1] - yy) / (REF_BOTTOM[1] - REF_BOTTOM[0]), 0, 1)
    DX *= lim; DY *= lim
    mx = (np.arange(1920, dtype=np.float32)[None, :] + DX[:, None]).astype(np.float32)
    my = (yy[:, None] + DY[:, None] + np.zeros((1, 1920), np.float32)).astype(np.float32)
    w2 = cv2.remap(w, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ok2 = cv2.remap(ok.astype(np.uint8), mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0
    return w2, ok2, (dx.round(1).tolist(), dy.round(1).tolist())


_fc = {}


def features(key, img, bad):
    if key not in _fc:
        mk = np.zeros((1080, 1920), np.uint8); mk[60:1080, 0:1100] = 255; mk[bad > 0] = 0
        _fc[key] = sift.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), mk)
    return _fc[key]


def align(tgt_k, tgt_d, sk, sd, win, yr=(0, 1080)):
    sel = [i for i, k in enumerate(tgt_k) if win[0] <= k.pt[0] < win[1] and yr[0] <= k.pt[1] < yr[1]]
    if len(sel) < 20 or sd is None:
        return None
    d1 = tgt_d[sel]
    mm = cv2.BFMatcher().knnMatch(d1, sd, k=2)
    good = [p[0] for p in mm if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(good) < 15:
        return None
    pt = np.float32([tgt_k[sel[g.queryIdx]].pt for g in good]); ps = np.float32([sk[g.trainIdx].pt for g in good])
    H, inl = cv2.findHomography(ps, pt, cv2.RANSAC, 2.0, maxIters=8000)
    if H is None or inl.sum() < 20:
        return None
    return H, int(inl.sum())


def clean_frame(t, done):
    tgt = orig(t); hm = hole_mask(t)
    tbad = bad_mask(t, tgt, False)
    ys, xs = np.where(hm > 0)
    win = (max(0, xs.min() - 260), min(1920, xs.max() + 480))
    tmask = np.zeros((1080, 1920), np.uint8); tmask[60:1080, 0:1100] = 255
    tmask[cv2.dilate(tbad, K(15)) > 0] = 0
    tk, td = sift.detectAndCompute(cv2.cvtColor(tgt, cv2.COLOR_BGR2GRAY), tmask)
    ring = (cv2.dilate(hm, K(41)) > 0) & (hm == 0) & (tbad == 0)
    cands = []
    srcs = [(s, orig(s), False) for s in range(t + 1, min(90, t + 15))]
    srcs += [(s, done[s], True) for s in range(t + 1, t + 4) if s in done]
    for s, img, cl in srcs:
        bad = bad_mask(s, img, cl)
        sk, sd = features((s, cl), img, bad)
        r = align(tk, td, sk, sd, win)
        if r is None:
            continue
        H, n = r
        w, ok = warp(img, bad, H)
        # the ceiling is another plane than the floor and the lobby wall: give the top
        # of the hole its own alignment, fitted on the ceiling, and ramp between the two
        w = w.astype(np.float32)
        yy = np.arange(1080, dtype=np.float32)
        for (fy0, fy1), (r0, r1), up in ZONES:
            if not ((ys.min() < r1) if up else (ys.max() > r0)):
                continue
            rz = align(tk, td, sk, sd, (max(0, win[0] - 150), win[1] + 150), (fy0, fy1))
            if rz is None:
                continue
            wz, okz = warp(img, bad, rz[0])
            # weight 1 on the zone's side of the ramp r0..r1
            wy = np.clip((r1 - yy) / (r1 - r0), 0, 1) if up else np.clip((yy - r0) / (r1 - r0), 0, 1)
            wy = wy[:, None]
            w = wz.astype(np.float32) * wy[..., None] + w * (1 - wy[..., None])
            ok = np.where(wy >= 1, okz, np.where(wy <= 0, ok, okz & ok))
        w = w.astype(np.float32)
        if REFINE:
            w, ok, _ = refine(w, ok, tgt, hm, tbad)
        rr = ring & ok
        if rr.sum() < 300:
            continue
        diff = tgt.astype(np.float32)[rr] - w.astype(np.float32)[rr]
        off = diff.mean(0)
        err = float(np.abs(diff - off).mean())
        cands.append((err + 0.15 * abs(s - t), s, cl, n, w + off, ok))
    need = hm > 0
    # one source for the whole hole when one can: mixing sources doubles edges inside it
    cands.sort(key=lambda c: (0 if (c[5] & need).sum() >= 0.995 * need.sum() else 1, c[0]))
    fill = np.zeros((1080, 1920, 3), np.float32); have = np.zeros((1080, 1920), bool)
    used = []
    for err, s, cl, n, w, ok in cands:
        take = need & ~have & ok
        if take.sum() == 0:
            continue
        fill[take] = w[take]; have |= take; used.append((s, cl, n, round(err, 1), int(take.sum())))
        if (need & ~have).sum() == 0:
            break
    left = need & ~have
    comp = tgt.copy()
    comp[have] = np.clip(fill[have], 0, 255).astype(np.uint8)
    if left.sum():
        comp = cv2.inpaint(comp, left.astype(np.uint8) * 255, 6, cv2.INPAINT_TELEA)
    # around the hole the source is the best candidate where it shows clean lobby
    around = tgt.copy()
    if cands:
        w0, ok0 = cands[0][4], cands[0][5]
        around[ok0] = np.clip(w0[ok0], 0, 255).astype(np.uint8)
    return blend(tgt, comp, around, hm), used, int(left.sum())


def blend(tgt, comp, around, hm):
    """Poisson blend. OpenCV erodes the clone mask by 3 px and takes the border values
    from the destination there, so the mask is grown past the hole and the hole itself
    is pre-filled; the source is continuous across the hole edge (best source around it)."""
    ys, xs = np.where(hm > 0)
    a, b, c, d = xs.min(), xs.max(), ys.min(), ys.max()
    pad = 24
    X0, X1, Y0, Y1 = max(0, a - pad), min(1920, b + pad + 1), max(0, c - pad), min(1080, d + pad + 1)
    hk = hm[Y0:Y1, X0:X1] > 0
    dst = tgt[Y0:Y1, X0:X1].copy()
    srcc = around[Y0:Y1, X0:X1].copy()
    srcc[hk] = comp[Y0:Y1, X0:X1][hk]
    dst[hk] = srcc[hk]
    mask = cv2.dilate(hk.astype(np.uint8) * 255, K(11))
    mask[0, :] = mask[-1, :] = 0; mask[:, 0] = mask[:, -1] = 0   # seamlessClone clears these itself
    br = cv2.boundingRect(mask)
    p = (br[0] + br[2] // 2, br[1] + br[3] // 2)
    out = cv2.seamlessClone(srcc, dst, mask, p, cv2.NORMAL_CLONE)
    res = tgt.copy(); region = res[Y0:Y1, X0:X1]
    keep = mask > 0
    region[keep] = out[keep]
    region[hk & ~keep] = srcc[hk & ~keep]
    return res


if __name__ == '__main__':
    lo, hi = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (40, 52)
    done = {}
    for s_ in range(hi + 1, hi + 5):   # frames cleaned by an earlier run
        if os.path.exists(f'{OUT}/w2_{s_:03d}.png') and s_ <= 52:
            done[s_] = cv2.imread(f'{OUT}/w2_{s_:03d}.png')
    REFINE = (os.environ.get('REFINE', '1') == '1')
    for t in range(hi, lo - 1, -1):
        res, used, left = clean_frame(t, done)
        done[t] = res
        cv2.imwrite(f'{OUT}/w2_{t:03d}.png', res)
        print(t, used, 'left', left, flush=True)
