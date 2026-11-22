"""The old left handle (LHO) and the hinge stile beside it (HL), measured on the rows where the pattern
stile | slit of glass | handle | wall shows clearly. Writes early_pat.json (used by early_fin.py)."""
import cv2, numpy as np, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HERE, 'early.json')))


def runs_of(d):
    d = np.append(d, False); out = []; s = None
    for i, k in enumerate(d):
        if k and s is None: s = i
        if not k and s is not None: out.append((s, i)); s = None
    return out


res = {}
for t in range(73, 99):
    f = cv2.imread(f'/tmp/e/s{t:03d}.png'); V = cv2.GaussianBlur(f.max(2).astype(np.float32), (0, 0), 0.6)
    e = E[str(t)]; xa = int(e['J'][0]) - 8; xb = int(e['LF'][0]) - 1
    cand = []
    for y in range(int(e['RH'][2]) - 10, int(e['LHO'][2]) - 2):
        row = V[y, xa:xb]; rs = [(a + xa, b + xa) for a, b in runs_of(row < 112)]
        for k in range(len(rs) - 1, 0, -1):
            a, b = rs[k]; pa, pb = rs[k - 1]
            if not (5 <= b - a <= 17): continue
            if b + 6 > xb + 1 or V[y, b + 1:b + 6].min() < 135: continue
            if not (1 <= a - pb <= 10 and 3 <= pb - pa <= 14): continue
            if V[y, pb:a].max() < 125: continue
            cand.append((y, pa, pb, a, b)); break
    if not cand: continue
    c = np.array(cand); med = np.median(c[:, 1:], 0)
    c = c[np.all(np.abs(c[:, 1:] - med) <= 2, axis=1)]
    if len(c) < 10: continue
    rows = c[:, 0]; P = V[rows, xa:xb].mean(0)

    def cross(i0, up):
        lo = P[max(0, i0 - 4):i0 + 5]; h = (lo.min() + lo.max()) / 2
        for i in range(max(1, i0 - 3), min(len(P) - 1, i0 + 4)):
            if up and P[i - 1] <= h < P[i]: return float(xa + (i - 1) + (h - P[i - 1]) / (P[i] - P[i - 1]) + 0.5)
            if (not up) and P[i - 1] > h >= P[i]: return float(xa + (i - 1) + (P[i - 1] - h) / (P[i - 1] - P[i]) + 0.5)
        return None
    m = c[:, 1:].mean(0)
    v = [cross(int(round(m[0])) - xa, False), cross(int(round(m[1])) - xa, True), cross(int(round(m[2])) - xa, False), cross(int(round(m[3])) - xa, True)]
    if None in v: continue
    res[t] = {'HL': [round(v[0], 2), round(v[1], 2)], 'LHO': [round(v[2], 2), round(v[3], 2)], 'n': int(len(c))}
json.dump(res, open(os.path.join(HERE, 'early_pat.json'), 'w'))
if __name__ == '__main__':
    for t, r in res.items(): print(t, r)
