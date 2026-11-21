// Copies the site's runtime files from Source/ into Source/dist/ for Cloudflare.
// The list matches $RuntimeFiles and $RuntimeDirs in tools/package-store.ps1, plus _headers.
import { cpSync, rmSync, mkdirSync, existsSync, statSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC = join(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(SRC, 'dist');
const FILES = ['index.html', '_headers'];
const DIRS = ['v', 'vi', 'tiles', 'media', 'renders', 'real'];
const LIMIT = 25 * 1024 * 1024;          // Cloudflare's per-file limit for static assets
const SKIP = new Set(['.DS_Store', 'Thumbs.db', 'desktop.ini']);

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });
for (const f of [...FILES, ...DIRS]) {
  if (!existsSync(join(SRC, f))) throw new Error(`Missing in Source: ${f}`);
  cpSync(join(SRC, f), join(DIST, f), { recursive: true, filter: (p) => !SKIP.has(p.split(/[\\/]/).pop()) });
}

let count = 0, bytes = 0;
const walk = (d) => {
  for (const e of readdirSync(d, { withFileTypes: true })) {
    const p = join(d, e.name);
    if (e.isDirectory()) { walk(p); continue; }
    const s = statSync(p).size;
    if (s > LIMIT) throw new Error(`Over 25 MiB, Cloudflare will refuse it: ${p}`);
    count++; bytes += s;
  }
};
walk(DIST);
console.log(`dist: ${count} files, ${(bytes / 1048576).toFixed(1)} MB`);
