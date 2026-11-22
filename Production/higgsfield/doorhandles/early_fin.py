"""early.json: the bars of the door for w1 frames 73..99 (x-edges measured by early_geo.py and early_pat.py, vertical ends
measured or read off). Run early_geo.py, this, early_pat.py, then this again."""
import json, cv2, numpy as np, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'early_raw.json'))); S = json.load(open(os.path.join(HERE, 'snap.json')))['w1']
# top of the right handle where foliage hides it (read off the frames: a little above where it comes out of the leaves)
RH_TOP = {73: 592, 74: 590, 75: 588, 76: 585, 77: 581, 78: 574, 79: 566, 80: 565, 81: 563, 82: 558, 83: 552, 84: 549, 85: 546, 86: 542, 87: 539}
# its width where the edges could not be measured (a dark window stands behind it)
RH_W = {82: 8.0, 83: 8.4, 84: 8.8, 85: 9.1, 86: 9.5}
# the door frame's jamb, left of the hinge stile (columns read off the profiles; the slit of glass between the two is looked at)
J = {73: (807, 815), 74: (806, 814), 75: (804, 812), 76: (803, 811), 77: (800, 808), 78: (795, 803), 79: (794, 802), 80: (792, 800), 81: (788, 797), 82: (786, 795), 83: (779, 788), 84: (777, 786), 85: (775, 784), 86: (773, 783), 87: (769, 779), 88: (762, 773), 89: (756, 765), 90: (755, 765), 91: (752, 763), 92: (748, 761), 93: (742, 754), 94: (736, 749), 95: (728, 741), 96: (726, 740), 97: (724, 739), 98: (714, 729)}
out = {}
for t in range(73, 99):
    r = R[str(t)]; f = cv2.imread(f'/tmp/e/s{t:03d}.png'); V = cv2.GaussianBlur(f.max(2).astype(np.float32), (0, 0), 0.6)
    e = {'HL': r['HL'][:2], 'LF': r['LF'][:2], 'RF': r['RF'][:2], 'J': [float(J[t][0]), float(J[t][1] + 1)]}
    x0, x1 = r['RH'][:2]
    if t in RH_W:
        c = (x0 + x1) / 2; x0, x1 = c - RH_W[t] / 2, c + RH_W[t] / 2
    a, b = int(round(x0)) + 2, int(round(x1)) - 2
    c = V[600:716, a:max(a + 1, b)].mean(1); w = V[600:716, a - 9:a - 5].mean(1)
    idx = np.where((w - c) > 35)[0]; yb = 600 + int(idx[-1]) + 1
    dk = np.where(c < 120)[0]; yb2 = 600 + int(dk[-1]) + 1 if len(dk) else yb
    y1 = min(yb, yb2 + 3, 689)
    y0 = S[str(t)]['RH'][2] if (str(t) in S and 'RH' in S[str(t)]) else RH_TOP[t]
    e['RH'] = [round(x0, 2), round(x1, 2), float(y0), float(y1)]
    lb = r['LHO'][4]
    e['LHO'] = [r['LHO'][0], r['LHO'][1], None if (lb is None or 88 <= t <= 92) else float(lb)]   # 88-92: the trunk hides its bottom
    out[t] = e
# the old handle and the hinge stile, measured where their pattern shows clearly (early_pat.py), where there is such a measure
PAT = os.path.join(HERE, 'early_pat.json')
if os.path.exists(PAT):
    for t, r in json.load(open(PAT)).items():
        t = int(t)
        if r['n'] >= 10:
            out[t]['HL'] = r['HL']; out[t]['LHO'][:2] = r['LHO']
ts = [t for t in out if out[t]['LHO'][2] is not None]
for t in out:
    if out[t]['LHO'][2] is None: out[t]['LHO'][2] = float(np.interp(t, ts, [out[k]['LHO'][2] for k in ts]))
    e = out[t]; e['m'] = round((e['LF'][0] + e['LF'][1] + e['RF'][0] + e['RF'][1]) / 4, 2)
# frame 99 is done the same way: the trunk has only just left the old handle and there is no clean plate of the glass for
# it. Read off the frame; the two handles and the door's middle as build.py has them for the frames that follow.
out[99] = {'HL': [731.8, 742.8], 'LF': [822.5, 832.5], 'RF': [1044.5, 1054.5], 'J': [711.5, 727.5],
           'RH': [1025.0, 1036.7, 510.0, 674.0], 'LHO': [749.3, 763.9, 695.0], 'm': 938.22}
json.dump(out, open(os.path.join(HERE, 'early.json'), 'w'))
if __name__ == '__main__':
    for t, e in out.items():
        print(t, 'RH', e['RH'], 'LHO', e['LHO'], 'HL', e['HL'], 'LF', e['LF'], 'RF', e['RF'], 'm', e['m'])
