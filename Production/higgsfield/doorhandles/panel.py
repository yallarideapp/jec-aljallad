"""Third pass over w2 42..52, ceiling only: where the filled hole crosses the ceiling light
panel, redraw the panel from its own geometry instead of copying it from other frames
(copies left a stepped edge). The panel is a parallelogram: a flat top and bottom, a
slanted left end and a slanted right end. Its edges are measured outside the hole in the
same frame (the left end, when hidden, from the neighbouring frames), and each column inside
the hole is rebuilt from a clean column of the same frame next to the hole, shifted so its
edges land on the panel's edges there. Differences to the real pixels at the hole's sides
are spread across the hole. Updates tclean3."""
import os, cv2, numpy as np, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate2 as P

THR = 236


def run_edges(V, x, y0, y1):
    col = V[y0:y1, x]; b = np.where(col > THR)[0]
    if len(b) == 0:
        return None
    runs = np.split(b, np.where(np.diff(b) > 1)[0] + 1); r = max(runs, key=len)
    return (r[0] + y0, r[-1] + y0) if len(r) >= 4 else None


def junction(o, hm):
    ys_, xs_ = np.where(hm > 0)
    x = min(1900, xs_.max() + 15) if len(xs_) else 120
    colj = o[200:440, x:x + 10].mean(1).max(1)
    dj = np.where(colj < 120)[0]
    return int(dj[0] + 200 - 4) if len(dj) else 360


def measure(t):
    o = P.orig(t); V = o.max(2).astype(np.float32); hm = P.hole_mask(t)
    J = junction(o, hm)
    bad = (cv2.dilate(hm, P.K(13)) > 0) | (P.bad_mask(t, o, False) > 0)
    pts = []
    for x in range(0, 420):
        if bad[300, x]:
            continue
        e = run_edges(V, x, 250, min(350, J - 6))
        if e:
            pts.append((x, e[0], e[1]))
    pts = np.array(pts, np.float32)
    return pts[(pts[:, 2] - pts[:, 1]) <= 45] if len(pts) else pts


def slope(t):
    return 0.317 + 0.0043 * (t - 43)


def fit_frame(t, pts):
    x, top, bot = pts[:, 0], pts[:, 1], pts[:, 2]
    yT = float(np.median(top[top <= np.percentile(top, 30) + 1]))
    yB = float(np.median(bot[bot >= np.percentile(bot, 70) - 1]))
    s = slope(t)
    lm = bot < yB - 2.5                       # columns on the slanted left end
    lm &= x < x[np.argmax(bot >= yB - 1)] if (bot >= yB - 1).any() else lm
    c = float(np.median(bot[lm] - s * x[lm])) if lm.sum() >= 3 else None
    rm = top > yT + 2.5                       # slanted right end
    s2 = float(np.polyfit(x[rm], top[rm], 1)[0]) if rm.sum() >= 4 else 0.38
    d = float(np.median(top[rm] - s2 * x[rm])) if rm.sum() >= 3 else None
    return dict(yT=yT, yB=yB, c=c, s=s, s2=s2, d=d, xs=x, top=top, bot=bot)


def geometry(ts):
    G = {t: fit_frame(t, measure(t)) for t in ts}
    known = [(t, g['c']) for t, g in G.items() if g['c'] is not None]
    a, b = np.polyfit([k[0] for k in known], [k[1] for k in known], 1)
    for t, g in G.items():
        g['c_fit'] = a * t + b
        g['c_use'] = g['c'] if g['c'] is not None else g['c_fit']
    return G


def top_of(g, x):
    tp = np.full_like(x, g['yT'], dtype=np.float32)
    if g['d'] is not None:
        tp = np.maximum(tp, g['d'] + g['s2'] * x)
    return tp


def bot_of(g, x):
    return np.minimum(g['yB'], g['c_use'] + g['s'] * x)


def synth_col(o, g, xr, x, ys, J):
    """column x rebuilt from reference column xr for rows ys"""
    tp = float(top_of(g, np.float32([x]))[0]); bt = float(bot_of(g, np.float32([x]))[0])
    tr = float(top_of(g, np.float32([xr]))[0]); br = float(bot_of(g, np.float32([xr]))[0])
    src = np.empty(len(ys), np.float32)
    if bt - tp >= 2:
        # above the panel: follow its top edge; inside: stretch; below: follow its bottom edge
        a_ = ys < tp + 2; c_ = ys > bt - 2; m_ = ~a_ & ~c_
        src[a_] = ys[a_] - (tp - tr)
        src[c_] = ys[c_] + (br - bt)
        src[m_] = (tr + 2) + (ys[m_] - (tp + 2)) * ((br - 2) - (tr + 2)) / max(1.0, (bt - 2) - (tp + 2))
    else:                                      # left of the panel's tip: ceiling only
        up = ys < tr - 3
        src[up] = ys[up]
        src[~up] = br + 5 + (ys[~up] - (tr - 3))
    src = np.clip(src, 0, J - 8)
    col = o[:, xr].astype(np.float32)
    y0 = np.floor(src).astype(int); f = (src - y0)[:, None]
    return col[y0] * (1 - f) + col[np.minimum(y0 + 1, 1079)] * f


def fix(t, g, cur):
    o = P.orig(t); hm = P.hole_mask(t); tbad = P.bad_mask(t, o, False)
    J = 0
    ys_, xs_ = np.where(hm > 0)
    x = min(1900, xs_.max() + 15)
    colj = o[200:440, x:x + 10].mean(1).max(1)
    dj = np.where(colj < 120)[0]
    J = int(dj[0] + 200 - 4) if len(dj) else 360
    hm = cv2.dilate(hm, P.K(11))              # the first pass blended 5 px past the hole
    ys_, xs_ = np.where(hm > 0)
    ylo = int(max(ys_.min(), g['yT'] - 25)); yhi = min(J - 6, int(g['yB']) + 14)
    if yhi <= ylo:
        return cur
    rows = np.arange(ylo, yhi)
    # reference: nearest clean column right of the hole with the full flat panel
    inr = (ys_ >= ylo) & (ys_ < yhi)
    hx0, hx1 = xs_[inr].min(), xs_[inr].max()
    cand = []
    for xx, tp_, bt_ in zip(g['xs'], g['top'], g['bot']):
        xx = int(xx)
        if hx0 - 6 <= xx <= hx1 + 6 or tbad[300, xx]:
            continue
        mt = float(top_of(g, np.float32([xx]))[0]); mb = float(bot_of(g, np.float32([xx]))[0])
        if mb - mt < 6 or abs(tp_ - mt) > 2 or abs(bt_ - mb) > 2:
            continue
        if (o[int(mt) - 25:int(mt) - 3, xx].max(1) >= THR).any() or (o[int(mb) + 4:yhi + 6, xx].max(1) >= THR).any():
            continue
        full = (mb - mt) >= 0.85 * (g['yB'] - g['yT'])
        cand.append((min(abs(xx - hx0), abs(xx - hx1)) + (0 if full else 400), xx))
    if not cand:
        print(t, 'no reference column'); return cur
    xr = min(cand)[1]
    res = cur.astype(np.float32).copy()
    region = np.zeros((1080, 1920), bool); region[ylo:yhi] = hm[ylo:yhi] > 0
    cols = np.where(region.any(0))[0]
    xl, xR = cols.min(), cols.max()
    # residuals at the sides of the hole (skip a side that is a stile or the frame edge)
    def side(xs):
        r = []
        for xx in xs:
            if 0 <= xx < 1920 and not tbad[ylo:yhi, xx].any():
                r.append(o[ylo:yhi, xx].astype(np.float32) - synth_col(o, g, xr, xx, rows.astype(np.float32), J))
        if not r:
            return None
        from scipy.ndimage import median_filter, gaussian_filter1d
        m = np.clip(np.median(r, 0), -15, 15)
        return gaussian_filter1d(median_filter(m, (11, 1), mode='nearest'), 2.5, axis=0, mode='nearest')
    rL = side([xl - 2, xl - 3, xl - 4]); rR = side([xR + 2, xR + 3, xR + 4])
    if rL is None: rL = rR
    if rR is None: rR = rL
    if rL is None:
        rL = rR = np.zeros((len(rows), 3), np.float32)
    for xx in cols:
        sel = region[ylo:yhi, xx]
        sc = synth_col(o, g, xr, xx, rows.astype(np.float32), J)
        u = (xx - xl + 1) / (xR - xl + 2)
        sc = sc + rL * (1 - u) + rR * u
        res[ylo:yhi, xx][sel] = sc[sel]
    out = np.clip(res, 0, 255).astype(np.uint8)
    # feather the top and bottom of the redrawn band into what was there
    for k in range(8):
        a = (k + 1) / 9
        for y in ((ylo + k,) if ylo > ys_.min() else ()) + (yhi - 1 - k,):   # no top feather when the band starts at the hole's top
            if ylo <= y < yhi:
                sel = region[y]
                out[y][sel] = (cur[y][sel].astype(np.float32) * (1 - a) + out[y][sel].astype(np.float32) * a).astype(np.uint8)
    return out


if __name__ == '__main__':
    lo, hi = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (42, 52)
    ts = list(range(lo, hi + 1))
    G = geometry(list(range(42, 56)))
    for t in ts:
        g = G[t]
        print(t, {k: (round(float(v), 2) if v is not None else v) for k, v in g.items() if k in ('yT', 'yB', 'c', 'c_use', 's', 's2', 'd')})
        cur = cv2.imread(f'{P.OUT}/w2_{t:03d}.png')
        cv2.imwrite(f'{P.OUT}/w2_{t:03d}.png', fix(t, g, cur))
