# Production files (not part of any ZIP, mostly not on GitHub)

The heavy files live only in the project folder on Jafar's Mac (now `Documents/ChatGPT/JEC | AlJallad Contracting/Production`). GitHub holds the scripts.

## blender/
- `JEC_MASTER.blend` — the master scene (Blender 5.3, Cycles, AgX): one building with exterior stages (`ext`) and interior stages (`int`),
  city, cameras CAM_K0…K6 (exterior), CAM_ROOM, CAM_WALK, CAM_DUSK_A/B. Texture paths are relative, so the folder can move as a whole.
- `JEC_MASTER_backup_2026-11-20_1821.blend` — previous save. `JEC_POC.blend` (+ backup) — the older v3 scene.
- Scripts (on GitHub too): `jecpoc.py` (helpers), `jecmaster.py` (building, stage tags, `set_state`, render queue), `jmbuild.py`, `jmroom.py`
  (room stages), `jmcity.py` (city, K cameras, anchor stills, `anchor_S5n` / `render_S5n`), `mk_city_tex.py`, `assets/dl2.py`, `assets/dl3.py`.
- `JEC_MASTER_runtime_changes_2026-11-20.md` — fixes applied inside the .blend.
- Folders on the Mac only: `assets/` (Poly Haven textures, HDRI, models), `final/` (finished renders), `frames/`, `previews/`, `renders/`.

Use inside Blender (Python console or the Blender MCP):
```python
import sys; sys.path.insert(0, '<project>/Production/blender')
import jecmaster as jm, jmcity as jc
jc.anchor_state('S3')          # exterior anchors: S0, S1, S2, S2a, S2b, S2f, S3 … S7 (see ANCHOR in jmcity.py)
jc.render_S5n('<out>.jpg')     # stone and blockwork done, no glass, no crane
```

## higgsfield/
- `clips/` (Mac only) — the Higgsfield videos used by the site, native 1920×1080 at 30 fps, plus the repaired `w2f`, `i34t`, `i67f`.
  The raw generations also remain in the Higgsfield account.
- Scripts and settings (on GitHub): see `higgsfield/README.md`.
