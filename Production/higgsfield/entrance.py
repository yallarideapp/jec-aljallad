"""Entrance shot without the olive tree in front of the door (Jafar, 2026-11-21).

clips/w1.mp4 (150 frames) walks up to the entrance; from frame 77 to about 132 the camera passes an olive tree whose
planter stands right in front of the door, so the tree fills the screen and hides the entrance. This keeps frames 0-76
(the approach, the tree still small in its planter), replaces 77-133 with a short forward whoosh to the clear door,
and keeps 134-149 (the door, branch-free) -> clips/w1t.mp4 (103 frames).

The whoosh starts from frame 76 with the tree painted out (the door taken from frame 133, the balcony above from the
bay to its left), zooms that clean facade toward the door while frame 133 arrives on top of it, aligned door on door.
Run from Production/higgsfield:  python3 entrance.py   (needs numpy, opencv-python, ffmpeg)
"""
import os, subprocess, shutil
import numpy as np, cv2

SRC, DST, WORK = 'clips/w1.mp4', 'clips/w1t.mp4', '/tmp/jec_entrance'
KA, KB, LAST = 76, 133, 149            # last approach frame kept / first clear door frame / end of the clip
N = 10                                  # whoosh frames
# the door portal measured on frame 76 (behind the tree) and the door frame on frame 133
A_RECT, B_RECT = (727, 430, 1150, 745), (292, 37, 1612, 942)
TREE_AREA = [[700, 225], [1170, 225], [1180, 470], [1160, 742], [990, 742], [985, 760], [860, 760], [855, 742], [700, 742]]
BAY = 420                               # one balcony bay to the left, in pixels on frame 76


def extract():
    if os.path.isdir(WORK): shutil.rmtree(WORK)
    os.makedirs(WORK)
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-vsync', '0', '-start_number', '0', f'{WORK}/s%03d.png'])


def load(t): return cv2.imread(f'{WORK}/s{t:03d}.png').astype(np.float32)


def door_map():
    (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = A_RECT, B_RECT
    sx, sy = (ax1 - ax0) / (bx1 - bx0), (ay1 - ay0) / (by1 - by0)
    return sx, sy, np.float32([[sx, 0, ax0 - sx * bx0], [0, sy, ay0 - sy * by0]])


def clean_a(A, B):
    """frame KA with the tree removed"""
    H, W = A.shape[:2]
    sx, sy, M = door_map()
    Bm = cv2.warpAffine(cv2.GaussianBlur(B, (0, 0), 1.2), M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT)
    ref = (slice(470, 700), slice(1040, 1140))          # clear part of the portal on frame KA: match the light
    for c in range(3):
        a, b = A[ref][..., c], Bm[ref][..., c]
        Bm[..., c] = (Bm[..., c] - b.mean()) * (a.std() / (b.std() + 1e-3)) + a.mean()
    Up = np.zeros_like(A); Up[:, BAY:] = A[:, :-BAY]
    hsv = cv2.cvtColor(A.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    g, r, v = A[..., 1], A[..., 2], hsv[..., 2]
    fol = ((g >= r * 0.93) & (v < 200)) | (v < 95)
    area = np.zeros((H, W), np.uint8); cv2.fillPoly(area, [np.int32(TREE_AREA)], 1)
    m = (fol & (area > 0)).astype(np.uint8) * 255
    m = cv2.dilate(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)), np.ones((17, 17), np.uint8))
    rows = np.arange(H)[:, None]
    portal = np.zeros((H, W), np.float32); portal[438:738, 735:1142] = 1; portal = cv2.GaussianBlur(portal, (0, 0), 5)
    mt = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 5) * (area > 0)
    src = np.where((rows < 432)[..., None], Up, Bm)
    alpha = np.maximum(mt, portal * (rows >= 430))
    O = np.clip(A * (1 - alpha[..., None]) + src * alpha[..., None], 0, 255).astype(np.uint8)
    hsv2 = cv2.cvtColor(O, cv2.COLOR_BGR2HSV); g2, r2 = O[..., 1].astype(np.float32), O[..., 2].astype(np.float32)
    left = (((g2 >= r2 * 0.95) & (hsv2[..., 2] < 170)) & (area > 0) & (rows < 725)).astype(np.uint8) * 255
    left = cv2.dilate(cv2.morphologyEx(left, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), np.ones((7, 7), np.uint8))
    return cv2.inpaint(O, left, 6, cv2.INPAINT_TELEA).astype(np.float32)


def ss(u): return u * u * (3 - 2 * u)


def warp(img, sxy, c, T, k=1.0, border=cv2.BORDER_REFLECT):
    """scale by sxy about point c, put c at T, then scale by k about T"""
    M = np.float32([[k * sxy[0], 0, T[0] - k * sxy[0] * c[0]], [0, k * sxy[1], T[1] - k * sxy[1] * c[1]]])
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def zblur(img, sxy, c, T, L, n=24, border=cv2.BORDER_REFLECT):
    if L < 0.004: return warp(img, sxy, c, T, 1.0, border)
    return sum(warp(img, sxy, c, T, 1 + L * j / (n - 1), border) for j in range(n)) / n


def whoosh(A, Ac, B):
    sx, sy, M = door_map()
    CB = np.float32([(B_RECT[0] + B_RECT[2]) / 2, (B_RECT[1] + B_RECT[3]) / 2])
    CA = M @ np.append(CB, 1.0)                           # the same point of the door on frame KA
    ones = np.ones(B.shape[:2], np.float32)
    out = []
    for i in range(N):
        u = (i + 1) / (N + 1); e = ss(u)
        T = CA + (CB - CA) * e
        L = 0.2 * np.sin(np.pi * u)                       # zoom blur, strongest midway
        k = min(1.0, u / 0.12)                            # the tree fades out within the first two frames of the move
        As = A * (1 - k) + Ac * k
        a = zblur(As, ((1 / sx) ** e, (1 / sy) ** e), CA, T, L)
        b = zblur(B, (sx ** (1 - e), sy ** (1 - e)), CB, T, L)
        mb = cv2.GaussianBlur(warp(ones, (sx ** (1 - e), sy ** (1 - e)), CB, T, 1.0, cv2.BORDER_CONSTANT), (0, 0), 18)
        m = ss(float(np.clip((e - 0.15) / 0.5, 0, 1))) * mb
        out.append(np.clip(a * (1 - m[..., None]) + b * m[..., None], 0, 255).astype(np.uint8))
    return out


if __name__ == '__main__':
    extract()
    A, B = load(KA), load(KB)
    Ac = clean_a(A, B)
    seq = [cv2.imread(f'{WORK}/s{t:03d}.png') for t in range(0, KA + 1)] + whoosh(A, Ac, B) + \
          [cv2.imread(f'{WORK}/s{t:03d}.png') for t in range(KB + 1, LAST + 1)]
    od = f'{WORK}/out'; os.makedirs(od)
    for j, f in enumerate(seq): cv2.imwrite(f'{od}/{j:04d}.png', f)
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', f'{od}/%04d.png',
                           '-c:v', 'libx264', '-preset', 'fast', '-crf', '10', '-pix_fmt', 'yuv420p', '-an', DST])
    print(DST, len(seq), 'frames')
