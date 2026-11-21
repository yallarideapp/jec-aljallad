"""Fill the old left handle's place with the lobby really behind the glass, column by column, going backwards in time
from the moment the handle leaves the screen. A column comes from the nearest later original frame in which that
part of the lobby is clear of the handle, or else from the already-cleaned next frames. Every candidate column must
agree with what is seen just above and below the hole (where nothing hides the lobby). Poisson-blended in."""
import cv2, numpy as np, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tfill as T
H, W = 1080, 1920
OUT = '/tmp/doorfix/tclean3'; os.makedirs(OUT, exist_ok=True)
ORIG_OFFS = list(range(2, 27, 2))
CLEAN_OFFS = [4, 3, 2, 1]
clean = {}


def handle_box_src(ks):
    b = T.lho(ks)
    if b is not None: return T.hole_box(b)
    if ks[0] == 'w2' and ks[1] > 48: return (-200, -190, 0, H)
    return None


def stile_right(ks, hs, c, d):
    """right edge of the dark bronze hinge-side stile left of the handle in ks"""
    if hs[0] < 10: return -1
    V = T.img(ks)[int(max(0, c)):int(min(H, d)), :int(hs[0]) - 2].max(2).astype(np.float32).mean(0)
    dark = V < 125; run = 0
    for x in range(len(V) - 1, -1, -1):
        run = run + 1 if dark[x] else 0
        if run >= 6: return x + run
    return -1


def band_err(target, warped, cols, c, d, h=12):
    t1 = target[max(0, c - h - 2):c - 2, cols].astype(np.float32); s1 = warped[max(0, c - h - 2):c - 2, cols].astype(np.float32)
    t2 = target[d + 3:min(H, d + 3 + h), cols].astype(np.float32); s2 = warped[d + 3:min(H, d + 3 + h), cols].astype(np.float32)
    e = []
    if t1.size: e.append(np.abs(t1 - s1).mean((0, 2)))
    if t2.size: e.append(np.abs(t2 - s2).mean((0, 2)))
    return np.max(e, axis=0) if e else np.zeros(len(cols))


def fill(kt):
    b = T.lho(kt); a, bb, c, d = T.hole_box(b)
    i = T.IDX[kt]; cols = np.arange(a, bb + 1); ym = (c + d) / 2.0
    target = T.img(kt)
    choice = np.full(len(cols), -1); srcs = []
    cands = [('orig', o) for o in ORIG_OFFS] + [('clean', o) for o in CLEAN_OFFS]
    for kind, off in cands:
        if (choice >= 0).all(): break
        j = i + off
        if j >= len(T.SEQ) or j < 0: continue
        ks = T.SEQ[j]
        if kind == 'clean' and ks not in clean and not (ks[0] == 'w2' and ks[1] > 48): continue
        hs = handle_box_src(ks) if kind == 'orig' else None
        if kind == 'orig' and hs is None: continue
        A, nin = T.register(kt, ks, a, bb, c, d)
        if A is None or nin < (20 if kind == 'orig' else 10): continue
        Ai = np.linalg.inv(A)
        xs = [Ai[0, 0] * cols + Ai[0, 1] * y + Ai[0, 2] for y in (c, ym, d)]
        lo, hi = np.min(xs, axis=0), np.max(xs, axis=0)
        ok = (lo > 2) & (hi < W - 3)
        if hs is not None:
            if off > 0 or kind == 'clean': ok &= lo > hs[1] + 3
            else: ok &= (hi < hs[0] - 3) & (lo > stile_right(ks, hs, c, d) + 3)
        f = T.lf(ks)
        if f is not None: ok &= hi < f[0] - 4
        ok &= choice < 0
        if not ok.any(): continue
        srcimg = T.img(ks) if kind == 'orig' else clean.get(ks, T.img(ks))
        warped = cv2.warpAffine(srcimg, A[:2], (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        err = band_err(target, warped, cols, c, d)
        err = cv2.medianBlur(np.clip(err, 0, 255).astype(np.uint8).reshape(1, -1), 5).ravel().astype(np.float32) if len(err) >= 5 else err
        ok &= err < (36 if (kt[0] == 'w2' and kt[1] >= 38) else 22)   # the last frames blur fast
        if not ok.any(): continue
        choice[ok] = len(srcs); srcs.append((kind, ks, warped, nin))
    if not srcs or (choice < 0).mean() > 0.3: return None, None
    if (choice < 0).any():                       # a few columns left: take them from the nearest covered column's frame
        idx = np.where(choice >= 0)[0]
        for k in np.where(choice < 0)[0]: choice[k] = choice[idx[np.argmin(np.abs(idx - k))]]
    comp = np.zeros((H, W, 3), np.float32)
    for k, (kind, ks, warped, nin) in enumerate(srcs):
        sel = cols[choice == k]; comp[:, sel] = warped[:, sel]
    for e in np.where(np.diff(choice) != 0)[0]:
        x = a + e + 1
        for dx in (-1, 0):
            xx = x + dx
            if a < xx < bb: comp[c:d + 1, xx] = 0.5 * comp[c:d + 1, xx] + 0.25 * (comp[c:d + 1, xx - 1] + comp[c:d + 1, xx + 1])
    pad = 24
    X0, X1, Y0, Y1 = max(0, a - pad), min(W, bb + pad + 1), max(0, c - pad), min(H, d + pad + 1)
    src = target[Y0:Y1, X0:X1].copy()
    src[c - Y0:d - Y0 + 1, a - X0:bb - X0 + 1] = np.clip(comp[c:d + 1, a:bb + 1], 0, 255).astype(np.uint8)
    dst = target[Y0:Y1, X0:X1].copy()
    mask = np.zeros(dst.shape[:2], np.uint8); mask[c - Y0 + 1:d - Y0, a - X0 + 1:bb - X0] = 255
    out = cv2.seamlessClone(src, dst, mask, ((X1 - X0) // 2, (Y1 - Y0) // 2), cv2.NORMAL_CLONE)
    res = target.copy(); res[Y0:Y1, X0:X1] = out
    return res, [(kind[0] + f'{ks[0]}{ks[1]}', nin, int((choice == k).sum())) for k, (kind, ks, w_, nin) in enumerate(srcs)]


if __name__ == '__main__':
    order = [k for k in T.SEQ if T.lho(k) is not None and (k[0] == 'w2' or k[1] >= 99)][::-1]
    if len(sys.argv) > 1:
        lo, hi = int(sys.argv[1]), int(sys.argv[2])
        order = [k for k in order if k[0] == 'w2' and lo <= k[1] <= hi]
        for t in range(hi + 1, 49):
            f = f'{OUT}/w2_{t:03d}.png'
            if os.path.exists(f): clean[('w2', t)] = cv2.imread(f)
    log = {}
    for k in order:
        res, info = fill(k)
        if res is None: log[f'{k[0]}{k[1]}'] = None; continue
        clean[k] = res
        cv2.imwrite(f'{OUT}/{k[0]}_{k[1]:03d}.png', res); log[f'{k[0]}{k[1]}'] = info
        print(k, info, flush=True)
    print('failed:', [k for k, v in log.items() if v is None])
