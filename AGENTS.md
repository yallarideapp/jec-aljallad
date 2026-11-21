# AGENTS.md — JEC | AlJallad Contracting website (proof of concept)

Read `JEC-ALJALLAD-CONTEXT.md` first (Arabic). It has the current status, what is real and what is AI-made,
the behaviours to keep, open requests, and the change log shared by Claude and ChatGPT.

## Where it lives
- GitHub: **public** repo `yallarideapp/jec-aljallad` (Jafar's choice: anyone with the link can read it), branch `main`.
  Cloudflare builds `Source/` and deploys on every push to `main` (Workers with static assets; settings in `Cloudflare-guide.md`).
- The project folder on Jafar's Mac, `~/Documents/ChatGPT/JEC | AlJallad Contracting`, is a clone of this repo plus the heavy local-only files.
  GitHub and that folder must always match: pull before you start, and after every change commit, push, and pull the folder.
  Fetch and rebase before editing: Jafar, ChatGPT and Claude all push here.
- Preview link: https://yallarideapp.github.io/jec-aljallad/ — `.github/workflows/pages.yml` publishes the runtime files of `Source/`
  to GitHub Pages on every push to `main` (adds a `noindex` meta tag, since Pages ignores `_headers`). Cloudflare stays the planned host.
- Because the repo is public, never commit secrets, tokens, `.env` files, customer data, prices or agreements.
- Commit as `yallarideapp <227899290+yallarideapp@users.noreply.github.com>`. No tool or assistant names in commits, code or guides.
- The repo holds the site, agent files, guides, scripts and the photoreal stills. The heavy files (Blender scene, textures, renders,
  video clips, archives, QC sheets) stay in the project folder on Jafar's Mac and are listed in `.gitignore`.

## Layout
- `Source/` — the only place website code is edited. Static site, no framework (`npm run build` only copies files for Cloudflare):
  `index.html` (HTML, CSS and JS in one file; GSAP 3.12.5 + ScrollTrigger from cdnjs; Google Fonts),
  media in `v/` (exterior film clips), `vi/` (interior film clips), `tiles/` (phone frames), `media/` (hero and end videos),
  `renders/` (before/after and "behind the ceiling"), `real/` (photos of the 10 real JEC projects).
- `Source/server.cjs` — local preview server with HTTP Range support (the scroll film seeks inside videos).
- Cloudflare: `Source/wrangler.jsonc` (Worker `jec-aljallad`, assets from `Source/dist`), `Source/package.json` (wrangler pinned, lockfile committed),
  `Source/tools/build-dist.mjs` (`npm run build`: copies the runtime files and `_headers` into `dist/`, refuses files over 25 MiB),
  `Source/_headers` (security headers and `X-Robots-Tag: noindex` while this is a proof of concept),
  `Source/worker/index.js` (only `/media/*` runs through it: answers byte-range requests so the hero and end videos play on iPhone).
  When adding a runtime folder, add it to `build-dist.mjs` and to `$RuntimeDirs` in `package-store.ps1`.
- `Source/tools/package-store.ps1` — builds `Demo/`, both ZIPs, the delivery folder and the complete ZIP.
- Generated, never edited by hand: `Source/dist/`, `Demo/`, `JEC-AlJallad-complete-with-demo/`, `JEC-AlJallad-complete-with-demo.zip`.
- `Documents/` — `SOURCES.md`, `IMAGE-ASSETS.md`, `README-AR.md`, `Media-originals/` (photoreal stills);
  on the Mac only: `Evidence/` (QC sheets) and `Archives/` (older site versions and films, the client's first site source, early tests).
- `Production/` — never in any ZIP. `blender/` = master 3D scene and its Python scripts (scene and textures on the Mac only);
  `higgsfield/` = the scripts that turn the AI video clips into `Source/v`, `Source/vi`, `Source/tiles` (clips on the Mac only).

## Run
- Preview: `START-DEMO.command` (macOS) / `START-DEMO.cmd` (Windows), or `node Source/server.cjs` → http://localhost:8080.
  Without Node the page opens from the file; it works, but seeking in the film is less precise.
- Same as Cloudflare: in `Source/`, `npm ci` then `npm run dev` → http://localhost:8787 (applies `_headers` and the Worker).
- Package: `UPDATE-PACKAGE.command` (macOS) / `UPDATE-PACKAGE.cmd` (Windows). Needs PowerShell 7
  (`brew install --cask powershell` on macOS). Prints a JSON summary; fails if a ZIP check fails.

## Rules
1. Edit code only in `Source/`, then run the package script so Demo and the ZIPs catch up.
2. Keep the delivery layout and the hidden internal items (the script re-hides them).
3. This is a proof of concept for the client's approval. Do not attach a domain, remove `noindex`, buy anything or contact the client
   unless Jafar asks. The client's existing website is separate and must not be overwritten.
4. Truthfulness: the building is an AI architectural visualization (Blender model + Higgsfield AI). Keep every badge and note that
   says so, in both languages. Never present it as a completed JEC project. No invented statistics, awards, years, clients or quotes.
5. The real-projects section (`REAL` in index.html) lists 10 posts of @jallad.contracting with names and links exactly as published.
   Do not add, rename or invent projects.
6. Keep: Arabic RTL by default with the AR/EN toggle (localStorage key `jec-poc-lang`, wrapped in try/catch),
   `prefers-reduced-motion` handling, the slim nav that hides on scroll down, contact through the Instagram DM link.
7. Film player: desktop `VScrub` seeks H.264 clips frame by frame; phone `Scrub` draws WebP tiles (4 frames of 960×540 per tile).
   The `FILM` constant in index.html holds clip names, frame counts and stage boundaries. Change it together with the media.
   Clips must stay GOP 6, no B-frames, each file under 20 MiB (see `Production/higgsfield/README.md`).
8. Construction order on screen: glass only after structure, blockwork and stone. Interior order is fixed:
   raw → partitions → MEP → plaster → ceiling → floor/wall finishes → paint/doors/lighting → cleaning → furniture last.
9. No secrets, `.env` files or customer data in `Source/`.

## Media and 3D
- Re-encode the film: `Production/higgsfield/README.md`. `venc.py` with `jobs_v5.json` reproduces `Source/v` and `Source/vi` byte for byte.
- 3D: `Production/blender/JEC_MASTER.blend` (Blender 5.3, Cycles, texture paths relative to the .blend).
  The scripts find their own folder through `__file__`; inside Blender run
  `import sys; sys.path.insert(0, '<project>/Production/blender'); import jecmaster, jmcity`.
- New AI images or videos cost Higgsfield credits on Jafar's account. Ask him before generating.

## Known gaps
- The city behind the building is not the same in every exterior shot (each anchor still was made photoreal separately).
- Video is native 1920×1080 at 30 fps; no 2K/4K version exists.
- No privacy policy or terms pages yet (the site has no forms; it uses Google Fonts and cdnjs). Add them before a public launch.
- Cloudflare is not connected yet: Jafar connects the repo himself (`Cloudflare-guide.md`). Tested locally with `wrangler dev` only.
- Native master films on disk are the v4 cut (`Documents/Archives/films_v4`); the v5 film exists as the clips in `Source/v`, `Source/vi`.
