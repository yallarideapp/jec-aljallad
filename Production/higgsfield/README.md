# From Higgsfield clips to the site's film

Run everything from this folder. Needs Python 3 with `numpy`, `pillow`, `opencv-python`, and `ffmpeg`/`ffprobe` on the PATH
(macOS or Linux; temporary files go to /tmp). Inputs are `clips/<name>.mp4` (kept on the Mac, not on GitHub).

## Clips
| Clip | Shot |
|---|---|
| v1c | empty plot → excavation (unbranded machines) |
| v2 | excavation → foundations |
| v3, v4 | foundations → ground slab and columns → first slabs |
| v5 | street camera: frame rising to the roof |
| v6n | frame → blockwork and stone, window openings still empty, crane removed |
| v7n | glazing, then hoarding removed (completion) |
| w1, w2 → w2f | approach to the entrance, lobby (w2f = lobby with the round ceiling lights removed) |
| i12 … i79 (i34t, i67f) | interior stages; i34t and i67f end with a short dissolve, i67f also without two extra ceiling lights |
| hero, v8 | hero dusk push-in, day to dusk (used for `Source/media`, encoded in v4) |

## 1. Repairs (only if a source clip changes)
```bash
python3 fixspots.py lobby          # clips/w2.mp4 -> fxw2 -> fxw2o (first pass) -> clips/w2f.mp4
python3 spots3.py fxw2o fxw2p      # second pass: lights next to the door frame
ffmpeg -y -framerate 30 -i fxw2p/%04d.jpg -c:v libx264 -preset fast -crf 10 -pix_fmt yuv420p -an clips/w2f.mp4
python3 fixspots.py room           # clips/i67.mp4 -> clips/i67f.mp4
python3 fixspots.py i34            # clips/i34.mp4 -> clips/i34t.mp4
```

## 2. Desktop clips → `Source/v`, `Source/vi` (each with a `.webp` still)
```bash
python3 venc.py "$(cat jobs_v5.json)"
```
Settings: H.264 CRF 20, GOP 6, no B-frames, `ipratio=1.1`, `aq-mode=3`, 30 fps, no audio. The player seeks to exact frames while
scrolling, so every frame must decode fast and look as good as a keyframe. Clips of 150 frames are split in two (75 + 75) to keep
each file under 20 MiB. With the same clips, this reproduces the published files byte for byte.
`JEC_FILM_OUT=/some/dir/ python3 venc.py ...` writes somewhere else for a test.

## 3. Phone frames → `Source/tiles/m`, `Source/tiles/im`
```bash
python3 assemble.py A "$(python3 -c 'import json;print(json.dumps(json.load(open("plans_v5.json"))["A"]))')"
python3 tiles_m.py A ../../Source/tiles/m 60
python3 assemble.py I "$(python3 -c 'import json;print(json.dumps(json.load(open("plans_v5.json"))["I"]))')"
python3 tiles_m.py I ../../Source/tiles/im 60
```
`assemble.py` prints the frame total and stage boundaries.

## 4. Keep the page in step
If frame counts change, update `FILM` in `Source/index.html`: `Ad.clips` (name, frames), `Ad.seg`, `Id.anchors`, and the phone totals
and boundaries `Am`, `Im` printed by `assemble.py`.

## Higgsfield IDs of the photoreal anchor stills (usable as references in new generations)
S0 3397fef2-f5ae-43b5-a133-ae1c7733afec · S1 038f962c-9472-4cc0-90af-65c7c07b1708 · S2 47095789-54d7-48b9-b76d-a13705387f6c ·
S2b 76813883-d184-46a1-a815-e6c9d6f96265 · S3 af944aa7-8aac-46ea-9209-e7f3dd50d211 · S3K4 774a7f19-d643-4bda-ae43-5ab46e349a91 ·
S4 8d5be165-77e7-4503-95e8-c0f563e71b34 · S5 db5882a2-1123-47ef-aa7e-4cc556670c72 · S5n 28f25cc0-40ce-4429-8d3b-6e9d6667dc85 ·
S6 ffa3c9bb-f281-4286-8da1-ff37d49795ec · S7 dusk 2b05c893-b7d0-4dec-bf15-f652f19761f4 · duskA cdba7d61-5ad0-4a50-a7b7-dd37de571d46 ·
entrance 6c373c3f-fdeb-404c-b56a-9bee22c152ad · lobby a7589142-72cc-4b84-a1f1-f666614e5f38 ·
I1 e8091690-9587-4ab3-883f-abd73434a8a2 · I2 95e3c3c3-a427-436b-a70c-11471df21ea3 · I3 8e407b52-60fe-4d37-8640-f58f4ecea3da ·
I4 232c864f-b32f-47f0-9808-3de4640bfb58 · I5 eafee231-d5e2-4fce-ba48-ea64c6842502 · I6 18f157a5-a000-4dab-9666-437e2970e0d2 ·
I7 55920e43-ad51-4a77-9244-bff7db78730a · I9 3e7c081d-79b3-4468-a9b5-fb6bc4d429ef

Models: stills `gpt_image_2_6` (2K, two references: the Blender render and a reference photo); videos `wan3_0` 1080p with start and end
frame, no audio. `gemini_omni_flash_1_2` and `minimax_h3` failed; `nano_banana_pro` changed the framing. New generations cost credits:
ask Jafar first.
