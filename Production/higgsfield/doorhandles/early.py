"""The walk up to the door (w1), frames 73-99: an olive tree stands between the camera and the door, so the old left handle
cannot simply be painted out and the new one cannot simply be pasted in.

erase(orig, t)            the left leaf's old handle removed where it shows; the tree in front of it is left alone
occlusion(orig, t)        how much of each pixel around the new left handle is tree (1 = the tree hides the handle there)
occlusion_right(orig, t)  the same for the right handle's arms
geo(t), ramp(t)           where the door's bars are in frame t (early.json), and how far the edit has come in

The old handle is a dark bar in front of a flat wall. What replaces it is that wall, row by row, read just right of the
bar. The trunk is told from the bar by what shows beside it (the slit of glass on its left, the wall on its right) and,
where it is lit, by its lighter bark; the leaves by their green. build.py and arms.py call this for these frames."""
import cv2, numpy as np, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
E = {int(k): v for k, v in json.load(open(os.path.join(HERE, 'early.json'))).items()}
H, W = 1080, 1920
SRC = '/tmp/e'
T0, T1 = min(E), max(E)
DARK = 112          # the old handle's pixels are darker than this (V)...
CORE = 94           # ...and its middle darker than this; the bark in front of it is lighter
MINWALL = 138       # the wall behind the glass is at least this bright...
DESK = 165          # ...and the desk in front of it at least this bright: brighter than the lit bark


def geo(t):
    """the same shape build.py and arms.py use: LHO, RH (x0,x1,y0,y1), LF, RF (x0,x1), m"""
    e = E[t]
    return {'LHO': (e['LHO'][0], e['LHO'][1], e['RH'][2] - 60, e['LHO'][2]), 'RH': tuple(e['RH']), 'LF': tuple(e['LF']),
            'RF': tuple(e['RF']), 'HL': tuple(e['HL']), 'J': tuple(e['J']), 'm': e['m']}


def ramp(t):
    """the door takes this shape (two open leaves, a handle each) around frame 72: the edit comes in over three frames"""
    return float(np.clip((t - T0 + 1) / 3.0, 0, 1))


def _V(img):
    return cv2.GaussianBlur(img.max(2).astype(np.float32), (0, 0), 0.6)


def _hstd(V):
    """how uneven the brightness is along the row (seven pixels): a wall's seams and the desk's edge run along the rows"""
    m = cv2.blur(V, (7, 1)); m2 = cv2.blur(V * V, (7, 1))
    return np.sqrt(np.maximum(m2 - m * m, 0))


def wall_rows(img, V, xa, xb, ya, yb, need=3, fill=True):
    """colour of the wall on each row ya..yb-1, from the even (untextured), not dark pixels in columns xa..xb-1: the wall
    behind the glass is flat, the bark and the leaves in front of it are not. Rows without such pixels are filled in from
    the rows above and below."""
    reg = img[ya:yb, xa:xb].astype(np.float32); v = V[ya:yb, xa:xb]
    ok = (_hstd(V)[ya:yb, xa:xb] < 3.2) & (v > DARK)
    out = np.full((yb - ya, 3), np.nan, np.float32)
    for i in range(yb - ya):
        if ok[i].sum() >= need: out[i] = np.median(reg[i][ok[i]], axis=0)
    if not fill: return out
    good = ~np.isnan(out[:, 0])
    if good.sum() == 0: return None
    idx = np.arange(yb - ya)
    for c in range(3): out[:, c] = np.interp(idx, idx[good], out[good, c])
    return out


def _slit(img, V, t, ya, yb):
    """the wall as the slits of glass left of the old handle show it, row by row: colour and brightness of the slit's
    brightest pixel. The slit between the hinge stile and the handle, or, when that one is too narrow, the one left of the
    hinge stile. Returns the colours, their brightness and their green (the bark is browner than any wall: less green).
    None when both are too narrow."""
    g = geo(t)
    for u0, u1 in ((g['HL'][1], g['LHO'][0]), (g['J'][1], g['HL'][0])):
        if u1 - u0 < 2.9: continue
        sa, sb = int(np.ceil(u0)), max(int(np.ceil(u0)) + 1, int(np.floor(u1)))
        k = V[ya:yb, sa:sb].argmax(1); rows = np.arange(ya, yb)
        c = img[rows, sa + k].astype(np.float32)
        return c, c.max(1), c[:, 1]
    return None


def wall_beside(img, V, x_from, x_to, ya, yb, known=None, slit=None):
    """colour of the wall on each row, read right of column x_from (no further than x_to).
    Rows where that whole stretch is even and bright have nothing of the tree on them: their colours are the wall's.
    On the other rows the first even stretch beside x_from is read; it may be bark, so it is kept only when eight rows
    or more read nearly the same colour and that colour is one of the wall's (in this frame or, `known`, in the frames
    around it) or as bright as the desk. A reading much darker than the slit of glass left of the handle (`slit`) is bark
    too. Rows left without a reading take the slit's colour where the slit is as bright as the desk (lit bark has the
    wall's colour, so a dimmer slit proves nothing), and the rest are filled in from the rows above and below.
    None when no row can be read."""
    n = yb - ya; out = np.full((n, 3), np.nan, np.float32)
    f = img.astype(np.float32); v = V[ya:yb, x_from:x_to]
    sure = (v.min(1) > MINWALL) & (v.max(1) - v.min(1) <= 9)
    G = cv2.GaussianBlur(img[..., 1].astype(np.float32), (0, 0), 0.6)[ya:yb, x_from:x_to]
    if slit is not None: sure &= slit[2] - G.max(1) <= 25
    for i in np.where(sure)[0]: out[i] = np.median(f[ya + i, x_from:x_to], axis=0)
    levels = out[sure]
    if known is not None and len(known): levels = np.vstack([levels, known]) if len(levels) else known
    cand = np.full((n, 3), np.nan, np.float32)
    for i in np.where(~sure)[0]:
        r = v[i]
        if r[0] < MINWALL or (slit is not None and slit[2][i] - G[i, 0] > 25): continue
        k = 1
        while k < len(r) and k < 12 and abs(r[k] - r[0]) <= 8: k += 1
        if k >= 2: cand[i] = np.median(f[ya + i, x_from:x_from + k], axis=0)
    have = np.where(~np.isnan(cand[:, 0]))[0]
    if len(have):
        S = cand[have]
        coherent = (np.abs(S[:, None, :] - S[None, :, :]).max(2) <= 5).sum(1) >= 8
        known = (np.abs(S[:, None, :] - levels[None, :, :]).max(2).min(1) <= 10) if len(levels) else np.zeros(len(S), bool)
        keep = coherent & (known | (S.max(1) >= DESK))
        out[have[keep]] = S[keep]
    if slit is not None:
        # the slit is a little brighter than the glass right of the handle: bring it to the rows that show both
        both = ~np.isnan(out[:, 0]) & (slit[1] >= DESK) & (out.max(1) >= DESK)
        gain = np.median(out[both] / slit[0][both], axis=0) if both.sum() >= 4 else 1.0
        for i in np.where(np.isnan(out[:, 0]) & (slit[1] >= DESK))[0]: out[i] = slit[0][i] * gain
    good = ~np.isnan(out[:, 0])
    if good.sum() == 0: return None
    idx = np.arange(n)
    for c in range(3): out[:, c] = np.interp(idx, idx[good], out[good, c])
    sm = out.copy()                                                # rows read from different places: even them out, keep the desk's edge
    for i in range(n):
        nb = out[max(0, i - 4):i + 5]
        sm[i] = nb[np.abs(nb - out[i]).max(1) <= 14].mean(0)
    return sm


def _strip(t, V=None):
    """columns where the wall beside the old handle is read in frame t, and the rows"""
    g = geo(t)
    b = int(np.ceil(g['LHO'][1])) + 1; lf0, lf1 = g['LF']
    ya, yb = int(g['RH'][2]) - 12, int(min(H - 1, np.ceil(g['LHO'][3]) + 3))
    if lf0 - b >= 9: return b + 2, int(min(b + 18, np.floor(lf0) - 2)), ya, yb
    return int(np.ceil(lf1)) + 3, int(np.ceil(lf1)) + 15, ya, yb      # the strip is too narrow: read right of the stile


_LEV = {}


def sure_levels(t):
    """the wall's colours on the rows of frame t where the strip beside the old handle is clear of the tree"""
    if t not in _LEV:
        if t not in E: _LEV[t] = np.zeros((0, 3), np.float32)
        else:
            img = cv2.imread(f'{SRC}/s{t:03d}.png'); V = _V(img)
            xa, xb, ya, yb = _strip(t)
            v = V[ya:yb, xa:xb]
            sure = _segments((v.min(1) > MINWALL) & (v.max(1) - v.min(1) <= 9), 12, gap=0)     # the wall is even over many rows; bark is not
            _LEV[t] = np.array([np.median(img[ya + i, xa:xb].astype(np.float32), axis=0) for i in np.where(sure)[0]], np.float32).reshape(-1, 3)
    return _LEV[t]


def _segments(ok, min_len, gap=2):
    """keep runs of True at least min_len long, bridging gaps of up to `gap` rows"""
    ok = ok.copy(); n = len(ok); i = 0
    idx = np.where(ok)[0]
    for a, b in zip(idx[:-1], idx[1:]):
        if 1 < b - a <= gap + 1: ok[a:b] = True
    out = np.zeros(n, bool); i = 0
    while i < n:
        if ok[i]:
            j = i
            while j < n and ok[j]: j += 1
            if j - i >= min_len: out[i:j] = True
            i = j
        else: i += 1
    return out


def _leafy(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return (hsv[..., 0] >= 18) & (hsv[..., 0] <= 50) & (hsv[..., 1] > 50)


def _runs(v):
    """(start, end) of each run of equal values"""
    out = []; i = 0; n = len(v)
    while i < n:
        j = i
        while j < n and v[j] == v[i]: j += 1
        out.append((i, j)); i = j
    return out


def erase_mask(orig, t):
    """the pixels of the old handle that show in frame t.
    Row by row: the handle shows whole when the slit of glass on its left and the wall on its right both show. Where the
    trunk has come over the slit, or stands dark against the handle's right side, its edge inside the handle cannot be
    seen (dark on dark): it is taken as a straight line across the handle, from the row where the trunk covers the
    handle whole to the row where the handle shows whole."""
    g = geo(t); V = _V(orig)
    x0, x1, _, yb = g['LHO']; hl0, hl1 = g['HL']; j0, j1 = g['J']; lf0 = g['LF'][0]
    ya, yb = int(g['RH'][2]) - 12, int(min(H - 1, np.ceil(yb) + 3))
    a, b = int(np.floor(x0)) - 1, int(np.ceil(x1)) + 1           # the bar's columns, one pixel of edge each side
    n = yb - ya; ys = np.arange(ya, yb)
    dark = V[ya:yb, a:b] < DARK
    c0 = int(round(x0)) + 2; c1 = max(c0 + 1, int(round(x1)) - 2)
    corev = V[ya:yb, c0:c1].mean(1); core = corev < CORE
    # the wall on each row: read between the bar and the leaf's other stile; rows where the trunk stands there take it
    # from the rows above and below
    wa, wb, _, _ = _strip(t)
    known = [sure_levels(k) for k in range(t - 3, t + 4) if k != t]
    known = np.vstack(known) if sum(len(k) for k in known) else None
    wall = wall_beside(orig, V, wa, wb, ya, yb, known, _slit(orig, V, t, ya, yb))
    if wall is None: return np.zeros((H, W), np.float32), (ya, yb, a, b), None
    wv = wall.max(1)
    # the slit of glass between the hinge stile and the handle; in the first frames it is too narrow to judge
    sa, sb = int(np.ceil(hl1)), max(int(np.ceil(hl1)) + 1, int(np.floor(x0)))
    if x0 - hl1 < 2.9:
        ja, jb = int(np.ceil(j1)), max(int(np.ceil(j1)) + 1, int(np.floor(hl0)))      # ...then the slit left of the hinge stile must show
        lmax = V[ya:yb, ja:jb].max(1)
        left_clear = (lmax > corev + 35) & (lmax > 100)
    else: left_clear = V[ya:yb, sa:sb].max(1) > wv - (45 if x0 - hl1 < 4 else 32)
    wr = int(max(3, min(10, np.floor(lf0) - 1 - b)))
    rmax = V[ya:yb, b + 1:b + 1 + int(np.clip(np.floor(lf0) - 2 - b, 1, 3))].max(1)
    right_clear = (rmax > corev + 35) & (rmax > 100)             # wall or bark; not the trunk's dark side, not foliage
    leaf = _leafy(orig)
    rdark = V[ya:yb, b:b + wr] < DARK + 20
    rleaf = (leaf[ya:yb, b:b + wr] & rdark).sum(1) >= max(2, 0.34 * wr)
    A = core & left_clear & right_clear
    B = core & ~left_clear & right_clear
    C = core & left_clear & ~right_clear & ~rleaf
    state = np.zeros(n, np.int8); state[A] = 1; state[B] = 2; state[C] = 3      # 0: the handle does not show on this row
    runs = [[i, j, int(state[i])] for (i, j) in _runs(state)]
    for k, r in enumerate(runs):                                   # a run of one or two rows is noise: it joins the run before it
        if r[1] - r[0] <= 2 and k > 0: r[2] = runs[k - 1][2]
    for i, j, v in runs: state[i:j] = v
    runs = _runs(state)
    for k in range(1, len(runs) - 1):                              # a short gap inside a stretch of one kind: the same
        (i, j) = runs[k]
        if state[i] == 0 and j - i <= 4 and state[i - 1] == state[j] and state[j] in (2, 3): state[i:j] = state[j]
    xs = np.arange(a, b)[None, :] + 0.5
    sel = np.zeros((n, b - a), bool); sel[state == 1] = True
    okB = np.zeros(n, bool); okC = np.zeros(n, bool)
    lim = np.ones((H, W), np.float32)                              # 1 = may be replaced; soft along the trunk's edge
    xall = np.arange(W)[None, :] + 0.5
    # lit bark right against the handle, or over its right side: the handle ends where the row turns lighter
    bark = (state == 1) & (rmax <= wv - 32)
    for i in np.where(bark)[0]:
        r = V[ya + i, a:b]; q = r < min(r.min() + 30, DARK)
        k = int(np.argmax(q))
        while k < len(q) and q[k]: k += 1
        sel[i, k:] = False
        lim[ya + i] = np.clip(a + k + 1 - xall, 0, 1)
    for (i, j) in _runs(state):
        v = state[i]
        if v not in (2, 3): continue
        top = int(i > 0 and state[i - 1] == 1); bot = int(j < n and state[j] == 1)       # only a row that shows the handle whole is a clear end
        if top == 0 and bot == 0: continue                         # covered above and below: leave it
        # the trunk's edge inside the handle: at the covered end of the stretch it stands at the handle's far side, at
        # the clear end at its near side, and it is straight in between
        near, far = (a, b) if v == 2 else (b, a)
        if top != 0 and bot != 0: e0 = e1 = near
        elif top == 0: e0, e1 = far, near
        else: e0, e1 = near, far
        xe = (e0 + (e1 - e0) * (np.arange(i, j) - i + 0.5) / (j - i))[:, None]
        if v == 2:
            sel[i:j] = xs >= xe - 0.5; okB[i:j] = True
            lim[ya + i:ya + j] = np.clip(xall - xe + 0.5, 0, 1)
        else:
            sel[i:j] = xs <= xe + 0.5; okC[i:j] = True
            lim[ya + i:ya + j] = np.clip(xe - xall + 0.5, 0, 1)
    A = state == 1
    rows = _segments(A | okB | okC, 8)
    m = np.zeros((H, W), np.uint8)
    m[ya:yb, a:b] = (dark & sel & rows[:, None]).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 5), np.uint8))                  # the bar's blurred edges
    al = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 0.7)
    al[m > 0] = np.maximum(al[m > 0], 0.9)
    for i in np.where(~right_clear & ~okC)[0]: lim[ya + i, b:] = 0     # dark right against the bar: not ours
    al *= lim
    al[:, :int(np.ceil(hl1 + 0.8))] = 0
    return al, (ya, yb, a, b), wall


def erase(orig, t):
    al, (ya, yb, a, b), wall = erase_mask(orig, t)
    if wall is None or al.max() == 0: return orig.copy()
    wimg = orig.astype(np.float32).copy(); wimg[ya:yb, a - 12:b + 6] = wall[:, None, :]
    out = orig.astype(np.float32) * (1 - al[..., None]) + wimg * al[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _nonwall(orig, V, xa, xb, xw, ya, yb):
    """the pixels of columns xa..xb-1, rows ya..yb-1 that are not the wall (1) - the wall being read, row by row, from
    the even pixels of columns xa..xw-1"""
    v = V[ya:yb, xa:xb]
    wall = wall_rows(orig, V, xa, xw, ya, yb)
    if wall is None:
        nw = v < 150
    else:
        reg = cv2.GaussianBlur(orig, (0, 0), 0.6)[ya:yb, xa:xb].astype(np.float32)
        dist = np.sqrt(((reg - wall[:, None, :]) ** 2).sum(2))
        far = (dist > 17).astype(np.uint8)
        far = cv2.morphologyEx(far, cv2.MORPH_OPEN, np.ones((5, 1), np.uint8))     # not a seam of the wall or the desk's edge
        dim = (wall.max(1)[:, None] - v > 24).astype(np.uint8)
        dim = cv2.morphologyEx(dim, cv2.MORPH_OPEN, np.ones((5, 1), np.uint8))
        nw = (dim > 0) | (far > 0) | (v < DARK)
    nw = cv2.morphologyEx(nw.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    k, lab, st, _ = cv2.connectedComponentsWithStats(nw, connectivity=8)
    for i in range(1, k):
        if st[i, cv2.CC_STAT_AREA] < 8: nw[lab == i] = 0
    return nw


def occlusion(orig, t):
    """1 where the tree stands in front of the new left handle and its arms, 0 where the wall shows"""
    g = geo(t); V = _V(orig)
    x0, x1, y0, y1 = g['RH']; m = g['m']
    dx1 = 2 * m - x0
    xa, xb = int(g['LF'][1]) + 1, int(np.ceil(dx1)) + 4
    ya, yb = int(max(0, y0 - 14)), int(min(H, y1 + 14))
    nw = _nonwall(orig, V, xa, xb, min(W, xb + 26), ya, yb)
    nw[:, :2] &= nw[:, 2:3]                                        # the stile's own soft edge is not the tree
    occ = np.zeros((H, W), np.float32)
    occ[ya:yb, xa:xb] = cv2.GaussianBlur(nw.astype(np.float32), (0, 0), 0.7)
    return occ


def occlusion_right(orig, t):
    """1 on the rows where the tree hangs in front of the right handle's arms (between the handle and its leaf's stile).
    The gap between the two is a few pixels wide, so it is judged from the wall just right of the stile."""
    g = geo(t); V = _V(orig)
    x0, x1, y0, y1 = g['RH']; rf0, rf1 = g['RF']
    xa = int(np.ceil(rf1)) + 2
    ya, yb = int(max(0, y0 - 14)), int(min(H, y1 + 14))
    nw = _nonwall(orig, V, xa, xa + 8, min(W, xa + 26), ya, yb)
    row = cv2.GaussianBlur((nw.mean(1) > 0.5).astype(np.float32).reshape(-1, 1), (0, 0), 1.0)
    occ = np.zeros((H, W), np.float32)
    occ[ya:yb, int(x1) - 2:int(np.ceil(rf0)) + 3] = row
    return occ
