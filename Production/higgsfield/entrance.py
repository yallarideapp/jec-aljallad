"""Entrance shot without the olive trees in front of the entrance (Jafar, 2026-11-21).

clips/w1.mp4 (150 frames) walks from the street view up to the entrance. The video model grows two olive trees in
planters in front of the entrance while the camera walks: the first one fades in from frame 42, the second from about
frame 52, and from frame 77 to about 132 the camera passes the first tree, which fills the screen and hides the door.
Jafar does not want those trees on screen at all.

This keeps frames 0-40 (the approach, before either tree exists), then a short forward whoosh from frame 40 into the
clear door of frame 133, then frames 134-149 (the door) -> clips/w1t.mp4 (69 frames).

Run from Production/higgsfield:  python3 entrance.py   (needs numpy, opencv-python, ffmpeg)
"""
import os, subprocess, shutil
import numpy as np, cv2

SRC, DST, WORK = 'clips/w1.mp4', 'clips/w1t.mp4', '/tmp/jec_entrance'
KA, KB, LAST = 40, 133, 149            # last approach frame kept / first clear door frame / end of the clip
N = 12                                  # whoosh frames
CA = np.float32([916, 750])             # centre of the glazed entrance on frame KA
CB = np.float32([952, 490])             # centre of the door on frame KB
S = 0.17                                # size of the entrance on frame KA relative to frame KB


def extract():
    if os.path.isdir(WORK): shutil.rmtree(WORK)
    os.makedirs(WORK)
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-vsync', '0', '-start_number', '0', f'{WORK}/s%03d.png'])


def ss(u): return u * u * (3 - 2 * u)


def warp(img, s, c, T, border):
    """scale by s about point c and put c at T"""
    M = np.float32([[s, 0, T[0] - s * c[0]], [0, s, T[1] - s * c[1]]])
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=border)


def zblur(img, s, c, T, L, n=24, border=cv2.BORDER_REFLECT):
    """zoom blur: the average of n copies scaled from s to s*(1+L)"""
    if L < 0.004: return warp(img, s, c, T, border)
    return sum(warp(img, s * (1 + L * j / (n - 1)), c, T, border) for j in range(n)) / n


def whoosh(A, B):
    """A flies toward its entrance while B arrives on top of it, door on door"""
    ones = np.ones(B.shape[:2], np.float32)
    out = []
    for i in range(N):
        u = (i + 1) / (N + 1); e = ss(u)
        T = CA + (CB - CA) * e
        L = 0.28 * np.sin(np.pi * u)                      # blur strongest midway
        a = zblur(A, (1 / S) ** e, CA, T, L)
        b = zblur(B, S ** (1 - e), CB, T, L)
        k = S ** (1 - e)                                  # B is still smaller than the screen: soft edge, gone at the end
        mb = cv2.GaussianBlur(warp(ones, k, CB, T, cv2.BORDER_CONSTANT), (0, 0), max(8.0, 0.09 * B.shape[1] * k))
        mb = np.maximum(mb, float(np.clip((e - 0.88) / 0.08, 0, 1)))
        m = ss(float(np.clip((e - 0.3) / 0.45, 0, 1))) * mb
        out.append(np.clip(a * (1 - m[..., None]) + b * m[..., None], 0, 255).astype(np.uint8))
    return out


if __name__ == '__main__':
    extract()
    load = lambda t: cv2.imread(f'{WORK}/s{t:03d}.png')
    seq = [load(t) for t in range(0, KA + 1)] + whoosh(load(KA).astype(np.float32), load(KB).astype(np.float32)) + \
          [load(t) for t in range(KB + 1, LAST + 1)]
    od = f'{WORK}/out'; os.makedirs(od)
    for j, f in enumerate(seq): cv2.imwrite(f'{od}/{j:04d}.png', f)
    subprocess.check_call(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', f'{od}/%04d.png',
                           '-c:v', 'libx264', '-preset', 'fast', '-crf', '10', '-pix_fmt', 'yuv420p', '-an', DST])
    print(DST, len(seq), 'frames')
