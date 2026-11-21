# Door handles of the entrance doors (clips w1 → w1h, w2f → w2h)

In the generated walk (`w1`) and lobby (`w2f`) the two door leaves had different handles: the left leaf's handle stood by the
hinge, away from the meeting edge, and did not match the right one. Jafar asked on 2026-11-21 for handles that are logical and
fixed to the door. These scripts:

1. remove the left leaf's handle and fill the glass behind it with the lobby that is really there;
2. paste a mirrored copy of the right handle on the left leaf, at the same height and the same distance from the meeting edge;
3. add two bronze arms per handle that fix it to its leaf's stile (top and bottom, shaded and lit like the bar).

The results are `clips/w1h.mp4` (150 frames) and `clips/w2h.mp4` (90 frames), which `jobs_v5.json` and `plans_v5.json` use.
Those two clips are the masters: keep them on the Mac with the other clips. The scripts are kept so the work can be redone or
adjusted; their order matters because each pass starts from the files the earlier one wrote.

Needs Python 3 with `numpy`, `scipy`, `opencv-contrib-python` (for `cv2.xphoto`) and `ffmpeg`. Work files go to `/tmp`.

## Frames in
```bash
mkdir -p /tmp/e /tmp/w2all
ffmpeg -i ../clips/w1.mp4  -vsync 0 -start_number 0 /tmp/e/s%03d.png
ffmpeg -i ../clips/w2f.mp4 -vsync 0 -start_number 0 /tmp/w2all/s%03d.png
```

## Steps
| Step | Script | What it does |
|---|---|---|
| 1 | `kf.py` | Hand-read keyframes of the old left handle (LHO), the right handle (RH) and the two meeting stiles (LF, RF). |
| 2 | `snap.py` | Snaps the keyframes to the real edges in every frame → `snap.json`. |
| 3 | `build.py` | Smooths the geometry (→ `geo.json`, door centre `m` = mirror axis) and writes the frames with the mirrored handle → `/tmp/hf`. It takes the clean glass from `/tmp/doorfix/tclean3` when a frame is there. |
| 4 | `tfill3.py` | Glass behind the old handle for w1 99–149 and w2 0–39: each column from the nearest later frame where that spot is clear, aligned on the lobby, Poisson-blended. |
| 5 | `plate2.py` | w2 40–52, where the handle dissolves (and a faint copy of its top lingers on the glass in 48–52): lobby from later frames with a local alignment per depth zone. Run `REFINE=1 python3 plate2.py 40 52`, then `REFINE=0 python3 plate2.py 40 46`. |
| 6 | `panel.py` | w2 42–52: redraws the ceiling light panel inside the filled area from its own edges (copies from other frames left a stepped edge). |
| 7 | `build.py`, then `arms.py` | Final frames with the mirrored handle and its arms → `/tmp/hf2`. |

`erase5.py`, `erase6.py`, `erase7.py` and `erase_shift.py` are the spatial fills `build.py` falls back to when no clean frame
exists; `tfill.py` holds helpers used by steps 4–6.

## Clips out
```bash
ffmpeg -y -framerate 30 -i /tmp/hf2/w1/s%03d.png -c:v libx264 -preset fast -crf 10 -pix_fmt yuv420p -an ../clips/w1h.mp4
ffmpeg -y -framerate 30 -i /tmp/hf2/w2/s%03d.png -c:v libx264 -preset fast -crf 10 -pix_fmt yuv420p -an ../clips/w2h.mp4
```
Then from `Production/higgsfield`: `venc.py` for `a09a`, `a09b`, `a10`; `assemble.py A` and `tiles_m.py A` (see `../README.md`);
and change `MV` in `Source/index.html`.

Before uploading a change here, show Jafar a before/after of the door glass: he checks it closely.
