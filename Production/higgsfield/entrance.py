"""Entrance shot without the olive trees in front of the entrance (Jafar, 2026-11-21).

clips/w1.mp4 (150 frames) walks from the street view up to the entrance and through the door. While the camera walks,
the video model grows two olive trees in planters in front of the entrance (the first from frame 42, the second from
about frame 52), and from frame 77 to about 132 the camera passes the first tree, which fills the screen.
Jafar wants the walk into the building kept, without those two trees.

What this does -> clips/w1t.mp4 (119 frames):
  frames 0-33    untouched
  frames 34-76   the same camera walk, with the ground floor between the left pier and the building's corner replaced
                 by one clean storefront that is tracked onto the facade (it fades in over frames 34-45, before the
                 trees appear); the tree tops above it are painted out; the street lamp stays
  26 frames      the walk continues from frame 76 straight to the door of frame 133 (the stretch where the tree
                 filled the screen is not used)
  frames 134-149 untouched (the door)

The clean storefront ("plate") is built on frame 76: the door is frame 133's door, the bays right of it repeat the
one clear glazed bay of frame 76. The facade is tracked from frame 76 back to frame 30 on its upper floors.

Run from Production/higgsfield:  python3 entrance.py   (needs numpy, opencv-python, ffmpeg)
"""
import os, subprocess, shutil
import numpy as np, cv2

SRC, DST, WORK = 'clips/w1.mp4', 'clips/w1t.mp4', '/tmp/jec_entrance'
W, H = 1920, 1080
K0, KA, KB, LAST = 34, 76, 133, 149      # plate fades in from K0 / last frame of the walk / first clear door frame / end
FADE = 12                                # frames over which the plate fades in
N = 26                                   # frames of the walk from frame KA to the door
CW, XC = 2100, 2030                      # plate canvas width; the building's corner, in frame-KA coordinates
BAND = (443, 748)                        # ground floor on frame KA: under the stone band, down to the ground line
X0 = 650                                 # the plate starts at the pier left of the entrance
SB = 385                                 # top of the stone band under the first-floor balconies
A_RECT, B_RECT = (727, 443, 1150, 745), (292, 37, 1612, 942)   # the entrance on frame KA / the door frame on frame KB
# the two tree tops above the ground floor on frame KA (they are lower in earlier frames: px per frame)
POLY_MID = [(690, 446), (690, 395), (712, 335), (760, 285), (820, 250), (880, 232), (960, 228), (1030, 240), (1090, 265), (1145, 300), (1185, 350), (1195, 446)]
POLY_RIGHT = [(1425, 446), (1430, 410), (1470, 385), (1540, 368), (1620, 362), (1700, 372), (1750, 395), (1775, 446)]
TOPS = ((POLY_MID, 228, 4.0), (POLY_RIGHT, 362, 1.5))
LAMP_X = 1416.0                          # the street lamp's pole on frame KA
# lamp height / ground-floor height, read off the frames (the lamp stands in front of the facade, so it grows faster)
LAMP_H = {34: 1.29, 40: 1.34, 46: 1.38, 52: 1.46, 58: 1.56, 64: 1.72, 70: 1.92, 76: 2.23}


def extract():
    if os.path.isdir(WORK): shutil.rmtree(WORK)
    os.makedirs(WORK)
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-vsync', '0', '-start_number', '0', f'{WORK}/s%03d.png'])


def load(t): return cv2.imread(f'{WORK}/s{t:03d}.png')
def ss(u): return u * u * (3 - 2 * u)
def mp(Hm, x, y):
    p = Hm @ np.array([x, y, 1.0]); return p[:2] / p[2]


def track():
    """homographies frame KA -> frame t of the facade plane, from features on the floors above the ground floor"""
    ox, oy = 1500, 5000
    canon = np.zeros((6200, 6000), np.uint8); canon[0:oy + 395] = 255
    for x0, y0, x1, y1 in ((640, 200, 1230, 395), (1340, 200, 1860, 395)):       # tree tops and the lantern
        canon[oy + y0:oy + y1, ox + x0:ox + x1] = 0
    T = np.float32([[1, 0, -ox], [0, 1, -oy], [0, 0, 1]])
    lk = dict(winSize=(25, 25), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    Hs = {KA: np.eye(3)}
    prev = cv2.cvtColor(load(KA), cv2.COLOR_BGR2GRAY)
    for t in range(KA - 1, K0 - 5, -1):
        cur = cv2.cvtColor(load(t), cv2.COLOR_BGR2GRAY)
        m = cv2.warpPerspective(canon, Hs[t + 1] @ T, (W, H), flags=cv2.INTER_NEAREST)
        m[:6] = 0; m[-6:] = 0; m[:, :6] = 0; m[:, -6:] = 0
        p0 = cv2.goodFeaturesToTrack(prev, 3000, 0.005, 7, mask=m, blockSize=5)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, **lk)
        pb, st2, _ = cv2.calcOpticalFlowPyrLK(cur, prev, p1, None, **lk)
        ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.abs(p0 - pb).reshape(-1, 2).max(1) < 0.5)
        M, _ = cv2.findHomography(p0[ok].reshape(-1, 2), p1[ok].reshape(-1, 2), cv2.RANSAC, 0.8, maxIters=5000, confidence=0.999)
        Hs[t] = M @ Hs[t + 1]; Hs[t] /= Hs[t][2, 2]
        prev = cur
    return Hs


def find_lamp(Hs):
    """the street lamp on every frame: pole centre, half width, foot, and the height of the ground floor beside it"""
    res, xp = {}, LAMP_X
    for t in range(KA, K0 - 1, -1):
        v = load(t).max(2).astype(np.float32)
        cx = np.linalg.inv(Hs[t]) @ np.array([xp, 800, 1.0]); cx = cx[0] / cx[2]
        yg, yt = mp(Hs[t], cx, 747)[1], mp(Hs[t], cx, 443)[1]; bh = yg - yt
        r0, r1 = int(yg + 0.03 * bh), int(yg + 0.20 * bh)                          # the pole against the pavement
        win = int(max(14, 0.09 * bh)); xs = np.arange(int(xp) - win, int(xp) + win + 1)
        dark = (v[r0:r1, xs[0]:xs[-1] + 1] < 75).mean(0)
        k = max(3, int(0.035 * bh)) | 1; xi = xs[int(np.argmax(np.convolve(dark, np.ones(k) / k, 'same')))]
        idx = np.where((v[r0:r1, xi - 2 * k:xi + 2 * k + 1] < 75).mean(0) > 0.5)[0]
        xc, hw = (xi - 2 * k + idx.mean(), (idx.max() - idx.min() + 1) / 2) if len(idx) else (xi, k / 2)
        y, miss = r1, 0
        while y < H - 1 and miss < 5:
            miss = 0 if v[y, int(xc) - int(hw) - 3:int(xc) + int(hw) + 4].min() < 80 else miss + 1
            y += 1
        res[t] = (float(xc), float(hw), y - 5, float(bh)); xp = xc
    return res


def lamp_matte(f, t, lamps):
    """1 where the frame's own street lamp must stay in front of the plate"""
    x, hw, base, bh = lamps[t]
    ks = sorted(LAMP_H); hl = float(np.interp(t, ks, [LAMP_H[k] for k in ks])) * bh; top = base - hl
    dark = np.clip((105 - f.max(2).astype(np.float32)) / 30, 0, 1)
    K = np.zeros(f.shape[:2], np.float32)
    y0, y1, x0, x1 = int(top + 0.16 * hl), int(min(H - 1, base)), int(round(x - hw - 2.5)), int(round(x + hw + 2.5)) + 1
    K[y0:y1, x0:x1] = dark[y0:y1, x0:x1]                                           # the pole
    hx0, hx1, hy0, hy1 = int(x - 0.075 * hl), int(x + 0.075 * hl), int(top - 0.03 * hl), int(top + 0.165 * hl)
    hs = cv2.cvtColor(f[hy0:hy1, hx0:hx1], cv2.COLOR_BGR2HSV)                      # the lantern: dark frame, pale glass
    K[hy0:hy1, hx0:hx1] = np.maximum(dark[hy0:hy1, hx0:hx1], ((hs[..., 1] < 45) & (hs[..., 2] > 130)).astype(np.float32))
    return cv2.GaussianBlur(K, (0, 0), 0.7)


def door_map():
    (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = A_RECT, B_RECT
    sx, sy = (ax1 - ax0) / (bx1 - bx0), (ay1 - ay0) / (by1 - by0)
    return sx, sy, np.float32([[sx, 0, ax0 - sx * bx0], [0, sy, ay0 - sy * by0]])


def build_plate(Hs, A, B):
    """the clean facade on frame KA; returns it and the colour match of frame KB's door to frame KA's light"""
    A = A.astype(np.float32); B = B.astype(np.float32)
    U = cv2.warpPerspective(load(40), np.linalg.inv(Hs[40]), (CW, H), flags=cv2.INTER_LANCZOS4).astype(np.float32)
    U = np.clip(U + 0.9 * (U - cv2.GaussianBlur(U, (0, 0), 2.2)), 0, 255)          # frame 40: before the trees
    ref = (slice(250, 440), slice(330, 680))
    for c in range(3): U[..., c] *= A[ref][..., c].mean() / U[ref][..., c].mean()
    P = np.zeros((H, CW, 3), np.float32); P[:, :W] = A; P[:, W:] = U[:, W:]
    # above the ground floor: the tree tops and the lantern out of frame KA
    tm = np.zeros((H, CW), np.uint8)
    cv2.fillPoly(tm, [np.int32(POLY_MID)], 1); cv2.fillPoly(tm, [np.int32(POLY_RIGHT)], 1)
    tm[325:462, 1366:1464] = 1; tm[446:] = 0
    for x in range(X0, W):                                                         # behind the balustrade glass
        ys = np.where(tm[:SB, x])[0]
        if len(ys): P[ys.min():SB, x] = P[max(0, ys.min() - 5):ys.min(), x].mean(0)
    rows = np.arange(H)[:, None]
    P = np.where(((tm > 0) & (rows < SB))[..., None], cv2.GaussianBlur(P, (0, 0), 1.5), P)
    bm = cv2.GaussianBlur(((tm > 0) & (rows >= SB - 4)).astype(np.float32), (0, 0), 2.0)[..., None]
    P = P * (1 - bm) + U * bm                                                      # the stone band: frame 40's
    # the ground floor: pier, entrance, then pier + glazed bay + the same bay mirrored, up to the corner
    y0, y1 = 440, 750
    pier, G = A[y0:y1, 1150:1205].copy(), A[y0:y1, 1205:1335].copy()
    G[452 - y0:464 - y0, 100:] = G[466 - y0:478 - y0, 100:]                        # the lamp's arm in front of the glass
    P[y0:y1, X0:1150] = A[y0:y1, X0:1150]
    x, segs, i = 1150, (pier, G, G[:, ::-1]), 0
    while x < XC - 70:
        seg = segs[i % 3]; w = min(seg.shape[1], XC - 65 - x)
        if w <= 0: break
        P[y0:y1, x:x + w] = seg[:, :w]; x += w; i += 1
    P[y0:y1, x:CW] = cv2.resize(pier, (CW - x, y1 - y0))
    sx, sy, M = door_map()
    Bm = cv2.warpAffine(cv2.GaussianBlur(B, (0, 0), 1.2), M, (CW, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT)
    ref = (slice(480, 700), slice(1050, 1140)); match = []                         # clear part of the entrance on KA
    for c in range(3):
        a, b = A[ref][..., c], Bm[ref][..., c]
        match.append((a.std() / (b.std() + 1e-3), a.mean(), b.mean()))
        Bm[..., c] = (Bm[..., c] - match[c][2]) * match[c][0] + match[c][1]
    ax0, ay0, ax1, ay1 = A_RECT
    pm = np.zeros((H, CW), np.float32); pm[ay0 + 2:ay1, ax0 + 4:ax1 - 4] = 1; pm = cv2.GaussianBlur(pm, (0, 0), 3)[..., None]
    return np.clip(P * (1 - pm) + Bm * pm, 0, 255).astype(np.uint8), match


def tree_tops(t):
    out = []
    for poly, top, k in TOPS:
        f = max(0.0, (446 - min(440, top + (KA - t) * k)) / (446 - top))
        m = np.zeros((H, CW), np.uint8); cv2.fillPoly(m, [np.int32([(x, 446 - (446 - y) * f) for x, y in poly])], 1); out.append(m)
    return out


def clean(t, Hs, P, lamps):
    """frame t of the walk without the two trees"""
    R8 = load(t); R = R8.astype(np.float32); Ht = Hs[t]
    wp = lambda m: cv2.warpPerspective(m, Ht, (W, H), flags=cv2.INTER_LINEAR)
    s = np.sqrt(abs(np.linalg.det(Ht[:2, :2])))
    Pw = wp(cv2.GaussianBlur(P, (0, 0), max(0.01, 0.45 * (1 / s - 1))) if s < 0.95 else P).astype(np.float32)
    w = ss(float(np.clip((t - K0 + 1) / FADE, 0, 1)))
    mid, right = tree_tops(t)
    up = mid.copy(); up[SB:] = 0; m = wp(up) > 0                                   # middle tree, behind the balustrade glass:
    F = R.copy(); pd = np.zeros((H, W), np.float32)                                # continue each column from above the tree
    for x in np.where(m.any(0))[0]:
        ys = np.where(m[:, x])[0]; y0, y1 = ys.min(), ys.max() + 1
        F[y0:y1, x] = R[max(0, y0 - 4):y0, x].mean(0); pd[y0:y1, x] = 1
    F = np.where(pd[..., None] > 0, cv2.GaussianBlur(F, (0, 0), 1.0), F)
    apd = (cv2.GaussianBlur(pd, (0, 0), 1.5) * w)[..., None]
    o = R * (1 - apd) + F * apd
    band = np.zeros((H, CW), np.float32); band[BAND[0]:BAND[1], X0:XC] = 1
    low = np.maximum(mid, right).astype(np.float32); low[:SB] = right[:SB]         # tree tops on the stone band
    a = cv2.GaussianBlur(np.maximum(wp(band), wp(low)), (0, 0), 2.0)
    a = (a * (1 - lamp_matte(R8, t, lamps)) * w)[..., None]
    return np.clip(o * (1 - a) + Pw * a, 0, 255).astype(np.uint8)


def warp(img, s, c, T, border=cv2.BORDER_REFLECT, k=1.0):
    """scale by s=(sx,sy) about point c, put c at T, then scale by k about T"""
    M = np.float32([[k * s[0], 0, T[0] - k * s[0] * c[0]], [0, k * s[1], T[1] - k * s[1] * c[1]]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=border)


def walk_in(C, B, match):
    """from the clean frame KA to the door of frame KB: both are kept registered on the entrance, so the door
    stays put while it grows; frame KB takes over from the middle outwards"""
    C = C.astype(np.float32); B = B.astype(np.float32)
    sx, sy, M = door_map()
    CB = np.float32([(B_RECT[0] + B_RECT[2]) / 2, (B_RECT[1] + B_RECT[3]) / 2]); CA = M @ np.append(CB, 1.0)
    Bmatch = np.stack([(B[..., c] - match[c][2]) * match[c][0] + match[c][1] for c in range(3)], -1)
    a0, b0 = 0.63, 0.2                                   # leaves frame KA at the walk's own speed, arrives slowly
    out = []
    for i in range(1, N + 1):
        u = i / (N + 1)
        e = (u ** 3 - 2 * u * u + u) * a0 + (3 * u * u - 2 * u ** 3) + (u ** 3 - u * u) * b0
        T = CA + (CB - CA) * e
        a = warp(C, (sx ** -e, sy ** -e), CA, T)
        b = warp(Bmatch * (1 - e) + B * e, (sx ** (1 - e), sy ** (1 - e)), CB, T)
        cov = np.zeros((H, W), np.float32)               # frame KB down to the door sill first, its pavement later
        cov[8:int(B_RECT[3] + (H - B_RECT[3]) * ss(float(np.clip((e - 0.45) / 0.5, 0, 1)))) - 6, 10:W - 10] = 1
        k = (sx * sy) ** ((1 - e) / 2)
        m = cv2.GaussianBlur(warp(cov, (sx ** (1 - e), sy ** (1 - e)), CB, T, cv2.BORDER_CONSTANT), (0, 0), 4 + 14 * k)
        m = np.maximum(m, float(np.clip((e - 0.93) / 0.06, 0, 1)))[..., None]
        f = a * (1 - m) + b * m
        L = 0.05 * np.sin(np.pi * u)                     # a little motion blur away from the door
        if L > 0.004: f = sum(warp(f, (1, 1), T, T, k=1 + L * (j / 11 - 0.5)) for j in range(12)) / 12
        out.append(np.clip(f, 0, 255).astype(np.uint8))
    return out


if __name__ == '__main__':
    extract()
    Hs = track(); lamps = find_lamp(Hs)
    P, match = build_plate(Hs, load(KA), load(KB))
    seq = [load(t) for t in range(0, K0)] + [clean(t, Hs, P, lamps) for t in range(K0, KA + 1)]
    seq += walk_in(seq[-1], load(KB), match) + [load(t) for t in range(KB + 1, LAST + 1)]
    od = f'{WORK}/out'; os.makedirs(od)
    for j, f in enumerate(seq): cv2.imwrite(f'{od}/{j:04d}.png', f)
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', f'{od}/%04d.png',
                           '-c:v', 'libx264', '-preset', 'fast', '-crf', '10', '-pix_fmt', 'yuv420p', '-an', DST])
    print(DST, len(seq), 'frames')
