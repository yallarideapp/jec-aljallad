# AGENTS.md — JEC | AlJallad Contracting website (proof of concept for the company's approval)

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
  `renders/` (before/after, "behind the ceiling", the process still), `real/` (photos of the 14 real JEC projects),
  `assets/` (company logo, sector images).
- One page, in this order: hero → construction film → who we are + stats → process (9 structural steps, exterior finishing) →
  finishing film → behind the ceiling → before/after → finishing trades + renovation → sectors → real projects (filters, lightbox) →
  services → quote estimator (send to the company or WhatsApp, consent) → end → footer. `#privacy` and `#terms` open the legal overlay.
  The company sections come from the first JEC site (2026-11-18), restyled into this design. The estimator's choices and the
  built-in project list (`TRADES`, `CATS`, `SUBS`, `SCOPES`, `STARTS`, `DRAW`, `PROJECTS`) live in `Source/shared/data.js`, shared
  by the page, the admin panel and the server; `SKELETON`, `SERVICES`, `FILTERS`, `LEGAL`, `CFG` stay in the script of index.html.
- `Source/shared/client.js` — how the page and the admin panel call the server (`JECAPI`). On `*.github.io` and pages opened
  from the file it runs a demo kept in the browser's localStorage (`jec-demo-v1`): requests, gallery and photos stay in that
  browser, and both pages say so. The demo panel has no password (Jafar, 2026-11-23: "it asks me for a password remove it");
  it holds no real data. The real panel on Cloudflare keeps its password: removing it there would put customers' names and
  phones and the site's gallery in anyone's hands, so do that only if Jafar asks for the real version explicitly. On localhost it asks `api/health` (so `node server.cjs` is the demo and
  `wrangler dev` the real thing). On any other host it is always the real thing: a server error shows as an error, never as
  the demo (a visitor's request must not silently stay in his browser).
- `Source/admin/` — the admin panel (PWA: `index.html`, `manifest.webmanifest`, `sw.js`, icons). Requests inbox, projects gallery
  editor, settings (requests on/off, company WhatsApp number, phone notifications, alert email, password). Arabic RTL with EN.
- `Source/worker/` — the server: `index.js` (routes `/api/*` and `/media/*`), `api.js` (all API routes), `auth.js` (admin password
  and sessions), `requests.js`, `content.js` (gallery), `push.js` (Web Push, VAPID, RFC 8291), `mail.js` (Resend), `schema.js`
  (the Worker creates its own D1 tables), `util.js`. Bindings: D1 `DB`, KV `PHOTOS` (no ids: the first deploy creates them).
- `Source/tests/` — `run-api-tests.sh` (94 server checks with fake email and push services) and `run-browser-tests.sh`
  (Playwright: the real version on `wrangler dev` and the demo on a static server).
- `Source/server.cjs` — local preview server with HTTP Range support (the scroll film seeks inside videos).
- Cloudflare: `Source/wrangler.jsonc` (Worker `jec-aljallad`, assets from `Source/dist`), `Source/package.json` (wrangler pinned, lockfile committed),
  `Source/tools/build-dist.mjs` (`npm run build`: copies the runtime files and `_headers` into `dist/`, refuses files over 25 MiB),
  `Source/_headers` (security headers and `X-Robots-Tag: noindex` while this is a proof of concept),
  `Source/worker/index.js` (`/api/*` and `/media/*` run through it; `/media/*` answers byte-range requests so the hero and end videos play on iPhone).
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
4. Truthfulness: the building is not a completed JEC project. Jafar decided (2026-11-21) to remove every on-page label that says it is
   AI-made or a visualization (badges, captions, credits, "illustrative" chips). Do not add them back unless he asks. Still: never write
   that JEC built this building or invent statistics, awards, years, clients or quotes. The Terms ("Images & films") keep one plain line
   that the films' building and the sector images are illustrative scenes, not specific completed projects.
5. The real-projects section starts from `PROJECTS` in `shared/data.js`: 14 posts of @jallad.contracting with names and links exactly
   as published. Do not add, rename or invent projects in code. Once the company saves the gallery in the admin panel, the site shows
   the saved list (from `/api/content`) instead; that list is the company's to edit. Brand names shown there feed the trademark notice
   in the footer and the Terms (`LEGAL.notice()`). Every project string is escaped before it goes into the page.
   The stats in "who we are" are counts of that real data (projects, sectors, steps, trades, services); never add invented figures.
6a. Legal: `LEGAL` is the single source for the Privacy Policy, Terms, footer notice and the estimator consent. It must describe what the
   code does: «أرسل الطلب للشركة» stores the request in D1 on Cloudflare, seen only in the admin panel; alerts go encrypted through the
   devices' push services and, if set, by email through Resend; a salted hash of the IP with the time is kept two days for rate limits;
   «أرسل عبر واتساب» sends nothing to a server; visitors get no cookies (only the admin's session cookie); the preview keeps test
   requests in the browser. Update `LAST_UPDATED` when you change it. Jordan PDPL No. 24 of 2023. The company's WhatsApp number is set
   in the admin panel (`CFG.WHATSAPP_NUMBER` is only the fallback and stays empty; empty opens WhatsApp's chat picker);
   `CFG.RATES` stays null unless JEC confirms JOD/m² ranges.
6b. Server and admin (Jafar, 2026-11-23): requests reach the company through the site (saved, with a number `JEC-0001`) or WhatsApp,
   the visitor's choice; the admin turns the site route off in Settings. Alerts: email (Resend, `RESEND_API_KEY`) and Web Push to
   the admin panel installed on phones. The Worker checks everything the page sends against `shared/data.js` (never trust the page),
   requires `consent: true` (stored with the time and the policy date), same origin on every non-GET, an idempotency key, the
   honeypot `hp` empty. Rate limits (5/hour, 20/day per salted IP hash; 120/hour, 600/day for the site, then `busy`) and the
   login lockout are counted and recorded in the same D1 batch as the action, so parallel requests cannot slip past them
   (the reviewer proved 60 parallel guesses got through the first version). Admin: one password (PBKDF2-SHA-256, 20,000 rounds
   because of the free plan's 10 ms CPU, at least 10 characters), first set and reset only with the `ADMIN_SETUP_CODE` secret;
   session cookie HttpOnly, Secure, SameSite=Strict, Path=/api/admin; 8 tries per address in 15 minutes (60 in all for the
   password; the setup code has no total, so the owner can always reset from his own connection). Gallery saves use a version
   check (409 on conflict). Photos: PNG/JPEG/WebP by their first bytes, at most 1.5 MB, in KV. Push only to the known push
   services (Apple, Google, Mozilla, Microsoft), at most 5 devices (each costs about 1 ms of CPU per alert), and no push while
   more than 20 requests arrived in the last hour. A nightly cron (`triggers` in wrangler.jsonc) deletes hashes older than two days.
   `TEST_PUSH_LOOPBACK` and `TEST_FAKE_BASE` exist only for the tests; never set them on Cloudflare. Run both test scripts after
   changing the server, the form or the panel. Secrets are typed by Jafar in the Cloudflare dashboard, never in the repo or a chat.
6. Keep: the side menu (`#menuBtn` floats at the top corner and stays visible while the bar hides; `#drawer` lists every section,
   the quote button, Instagram, language, the legal links and the admin panel link; Escape, the backdrop and any link close it).
   Arabic RTL by default with the AR/EN toggle (localStorage key `jec-lang`, wrapped in try/catch; the old key `jec-poc-lang` is only read),
   `prefers-reduced-motion` handling, the slim nav that hides on scroll down, the quote estimator and the Instagram DM link.
7. Film player: desktop `VScrub` seeks H.264 clips frame by frame; every touch device (phones, iPad, any width) and screens ≤820 px
   (`lite`) use `Scrub`, which draws WebP tiles (4 frames of 960×540 per tile). Smooth scrolling on phones: `Source/assets/tiles-worker.js`
   fetches every tile of the film in the background (kept compressed) and decodes the needed ones off the main thread, sending
   ImageBitmaps scaled to the canvas (decoding on the main thread was what made the film stutter). Without a worker (old browser,
   page opened from the file) the tiles load as images decoded before use. Memory stays bounded for iPhone Safari: anchor tiles every
   10 tiles, plus 8 tiles ahead in the scroll direction and 3 behind (up to 8 behind kept), only while the film is near the screen;
   dropped tiles are closed at once. Do not go back to decoding every tile; iOS closes tabs that hold too many decoded images.
   The glide toward the scroll position is time-based (110 ms), so it feels the same at 60 and 120 Hz. Touch screens get no live
   backdrop blur (bar, menu button, stage list).
   `ScrollTrigger.config({ignoreMobileResize:true})` stops the iPhone address bar from re-measuring the pinned sections.
   The `FILM` constant in index.html holds clip names, frame counts and stage boundaries. Change it together with the media.
   Every film file's address carries a version stamp (`?v=...`), so a changed file is fetched again at once while an unchanged one
   stays in the visitor's browser cache. Most files carry the base stamp `MV` (next to `FILM`); `FV` lists the files whose stamp
   differs. After changing any file in `v/`, `vi/`, `tiles/` or `assets/tiles-worker.js`, run
   `python3 Production/higgsfield/stamps.py`: it gives only the changed files a new stamp and writes `FV`. Do not change `MV` by hand
   (Jafar, 2026-11-22: after each update his computer re-downloaded the whole 127 MB film and the film froze on every scene).
   Clips must stay GOP 6, no B-frames, each file under 20 MiB (see `Production/higgsfield/README.md`).
   Slow connections (Jafar, 2026-11-22): on desktop the clip on screen downloads first and alone, then two at a time; when the
   viewer has stopped (not while scrolling on) on a shot that is still missing, downloads far from it that are not half done are
   dropped so it gets the whole line; while scrolling on, a shot passed on the way starts no download beyond two at a time.
   Stand-in on desktop: while the video of the scene on screen is still downloading, `VScrub` draws the phone's tiles on a canvas
   in the film (`pv`, a driven `Scrub` with `all: false`: the worker fetches only the tiles asked for, ahead of a fast scroll,
   every other one when the scroll is fast, cancelling tiles already passed; once the viewer stops, the tile on screen comes
   first and alone). A stand-in frame is drawn only within 6 phone frames of the right moment of the same shot; otherwise the
   scene's still, which is hidden until it has loaded so a slow line never shows another scene. The stand-in closes for good
   once every video is in. Measured on a first visit at 20 Mbit/s, scrolling through the film in 30 s: picture frozen 0.2% of
   the time (91% before); at 8 Mbit/s 9% (about 99% before). With a stand-in there is no bulk load of every scene's still. The first clip is short (`a01a` = 20 frames, 2.5 MB; `a01a2` = the rest of
   that shot) so the film moves within a few seconds. While the part on screen is still downloading, a small notice
   (`.ld`, «جارٍ تحميل هذا المشهد» with a percentage on desktop) shows on the film after 0.4 s; a fast connection never sees it.
   When Chrome/Edge/Android report a slow or data-saving connection, the hero plays its 540p video.
7a. Whole pictures on phones (Jafar, 2026-11-21): every full-screen picture (hero, both films, the ceiling reveal, the end shot)
   sits in a `.frame`. On wide screens the frame fills the screen as before. On upright screens (`max-aspect-ratio: 13/10`:
   phones, iPad held upright) the frame is the whole 16:9 picture at full width and the text sits under it; landscape phones
   show the whole picture centred with dark sides. Do not go back to cropping the picture's sides on phones. On upright
   screens the reveal shows coloured dots only; the names are in the legend under the picture. Before/after, sector cards,
   the renovation pair and the process image also keep their whole picture on narrow screens.
8. Construction order on screen: glass only after structure, blockwork and stone. Interior order is fixed:
   raw → partitions → MEP → plaster → ceiling → floor/wall finishes → paint/doors/lighting → cleaning → furniture last.
9. No secrets, `.env` files or customer data in `Source/`.
10. Link preview (Jafar, 2026-11-22): the `og:*` and `twitter:*` tags in the head of index.html give the shared link a picture
   (`Source/assets/og.jpg`, 1200×630, from the hero still with the logo and the company name) and a title. Crawlers need full
   addresses, so they point to the GitHub Pages preview; change `og:url`, `og:image` and `twitter:image` when the domain is attached.
11. Splash (Jafar, 2026-11-22): `#splash`, the first element in `<body>`: a gold line drawing of a concrete frame rising floor by
   floor on the ground line, then «JEC», «شركة الجلاد للمقاولات» and ALJALLAD CONTRACTING. It leaves 0.15 s after its last line
   of text has finished and the hero still has loaded (about 2 s), at most 4.5 s after the page opens, or at once on a tap,
   scroll or key. Not shown with reduced motion or when the page opens on a section link (`#privacy`, `#fin`...). It stores
   nothing. Without the script it fades out by itself after 5 s. The SVG paths use `pathLength="1"`; do not add
   `vector-effect: non-scaling-stroke` (Chrome then draws the hidden part of each line as dots).

## Media and 3D
- Re-encode the film: `Production/higgsfield/README.md`. `venc.py` with `jobs_v5.json` reproduces `Source/v` and `Source/vi` byte for byte.
- Entrance shot (Jafar, 2026-11-21): in the clip `w1` the video model grows two olive trees in planters in front of the entrance
  while the camera walks up, and one of them fills the screen just before the door. Three edited versions were tried the same day
  (tree cut out with a whoosh; walk cut short; walk kept with the trees painted out) and Jafar then asked for the original back.
  The walk itself is used as generated (`a09a` 75 + `a09b` 75 frames, `FILM.Ad` total 1068). Do not edit the trees again unless he asks.
  `Production/higgsfield/entrance.py` (the last edited version, makes `clips/w1t.mp4`) is kept for reference and is not in use.
  A clean version of this walk needs a regenerated clip, which costs Higgsfield credits.
- Door handles (Jafar, 2026-11-21): the generated entrance doors had a different handle on each leaf, the left one by the hinge.
  In `w1` (walk) and `w2f` (lobby) the left handle is removed, the glass behind it filled with the real lobby, and a mirrored copy
  of the right handle placed on the left leaf; both handles are fixed to their leaf by two bronze arms. The site uses the results,
  `clips/w1h.mp4` and `clips/w2h.mp4` (same frame counts); scripts and steps in `Production/higgsfield/doorhandles/README.md`.
  In the walk the doors are fixed from frame 73, where they first take their shape, although an olive tree stands in front
  of them until frame 99 (Jafar, 2026-11-22: the old handle still showed there and jumped to its new place afterwards): the
  old handle is removed only where it shows, and the new one and its arms are hidden where the trunk or the leaves are in
  front (`early.py`). The tree itself is not touched.
  Jafar checks the door glass closely and judges a change on the live preview: check every frame at 3x before uploading, and
  send him a before/after with the link.
- 3D: `Production/blender/JEC_MASTER.blend` (Blender 5.3, Cycles, texture paths relative to the .blend).
  The scripts find their own folder through `__file__`; inside Blender run
  `import sys; sys.path.insert(0, '<project>/Production/blender'); import jecmaster, jmcity`.
- New AI images or videos cost Higgsfield credits on Jafar's account. Ask him before generating.

## Known gaps
- The city behind the building is not the same in every exterior shot (each anchor still was made photoreal separately).
- Video is native 1920×1080 at 30 fps; no 2K/4K version exists.
- Privacy Policy and Terms exist (`#privacy`, `#terms`) but need the owner's review (not legal advice). The company WhatsApp number is still missing.
- Cloudflare is not connected yet: Jafar connects the repo himself (`Cloudflare-guide.md`), adds D1 Edit to the build token if the
  first build fails, and sets `ADMIN_SETUP_CODE` (and optionally `RESEND_API_KEY`). Tested locally with `wrangler dev` only:
  no real push service, no real email and no real iPhone have been tried yet.
- Native master films on disk are the v4 cut (`Documents/Archives/films_v4`); the v5 film exists as the clips in `Source/v`, `Source/vi`.
