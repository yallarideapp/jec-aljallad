# Where every picture and video on the site comes from

## Real (the company's own photos)
- `Source/real/p00 … p13.webp` — photos from the company's Instagram posts (see `SOURCES.md`), resized to WebP.

## AI architectural visualization (not a completed project; the site says so)
The building, workers, machines, surrounding city and the interior room were made for this site:
1. A 3D model in Blender (`Production/blender/JEC_MASTER.blend`) rendered at each construction and finishing stage.
2. Each render turned photoreal with Higgsfield AI (`gpt_image_2_6`, 2688×1520), using the render and a reference photo.
   These stills are in `Media-originals/photoreal_stills/`.
3. Short videos between two of those stills generated with Higgsfield AI (`wan3_0`, native 1920×1080 at 30 fps).

| Site file | Made from |
|---|---|
| `Source/media/hero_1080.mp4`, `hero_540.mp4`, `hero_poster.webp` | Higgsfield video, dusk push-in |
| `Source/media/end_daydusk_*.mp4`, `end_poster*.webp` | Higgsfield video, day to dusk |
| `Source/v/a01a … a10.mp4` (+ `.webp` stills) | Higgsfield videos of the construction, re-encoded for scroll seeking. `a05` is a motion-blur cut made in code between two shots. In `a10` (lobby) the round ceiling lights were removed by image inpainting. |
| `Source/vi/i01 … i07b.mp4` (+ `.webp`) | Higgsfield videos of the interior finishing. `i03` and `i06` end with a short dissolve made in code; in `i06` two extra ceiling lights were removed by inpainting. |
| `Source/tiles/m/*.webp`, `Source/tiles/im/*.webp` | Frames taken from the same videos, for phones |
| `Source/renders/p1.webp`, `p9.webp` | Photoreal stills I1 (raw room) and I9 (finished room) |
| `Source/renders/x10.webp` | Blender render of the ceiling systems (HVAC, sprinklers, chilled water, fan-coil unit, drainage) |

## Third-party material inside the Blender scene
- Textures, HDRI skies and furniture/tree models downloaded from Poly Haven (polyhaven.com, CC0) by `Production/blender/assets/dl2.py` and `dl3.py`.
- City facade textures, stone panels and concrete blocks generated in code (`Production/blender/mk_city_tex.py`, `jecmaster.py`).

## Not used
- No stock photos, no photos of other companies' buildings, no logos of other brands.
