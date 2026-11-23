// What the company edits in the admin panel and the site shows: the projects gallery, the company's WhatsApp number and
// whether the site takes requests. One row, saved whole with a version number: a save made from an older copy is refused
// (409) instead of overwriting someone else's change. Until the first save the site shows the built-in projects.
import '../shared/data.js';
import { HttpError, line, text, rand, hex } from './util.js';

const J = globalThis.JEC;
const MAX_PROJECTS = 60;
const IMG = /^(real\/[A-Za-z0-9_-]{1,40}\.webp|api\/photo\/[a-f0-9]{32})$/;
const VIDEO = /^((real|media)\/[A-Za-z0-9_-]{1,40}\.mp4)?$/;

function httpsUrl(v) {
  const s = line(v, 300);
  if (!s) return '';
  try { const u = new URL(s); if (u.protocol === 'https:' && u.hostname.includes('.')) return u.href; } catch (e) {}
  throw new HttpError('bad-url');
}
const tags = (v) => (Array.isArray(v) ? v.map((t) => line(t, 30)).filter(Boolean).slice(0, 8) : []);

export function cleanProject(p, seen) {
  if (!p || typeof p !== 'object') throw new HttpError('bad-project');
  let id = typeof p.id === 'string' && /^[a-z0-9]{1,24}$/.test(p.id) ? p.id : '';
  if (!id || seen.has(id)) id = 'p' + hex(rand(5));
  seen.add(id);
  const img = typeof p.img === 'string' ? p.img : '';
  if (!IMG.test(img)) throw new HttpError('bad-image');
  const video = typeof p.video === 'string' ? p.video : '';
  if (!VIDEO.test(video)) throw new HttpError('bad-video');
  if (!J.CATS.some((c) => c.id === p.cat)) throw new HttpError('bad-cat');
  let ar = line(p.ar, 100), en = line(p.en, 100);
  if (!ar && !en) throw new HttpError('bad-title');
  ar = ar || en; en = en || ar;
  const url = httpsUrl(p.url);
  return {
    id, img, video, url,
    type: url ? (p.type === 'reel' ? 'reel' : 'post') : 'none',
    cat: p.cat, st: p.st === 'live' ? 'live' : 'done', reno: !!p.reno, h: !!p.h, hidden: !!p.hidden,
    brand: line(p.brand, 60), ar, en,
    dAr: text(p.dAr, 600), dEn: text(p.dEn, 600), tAr: tags(p.tAr), tEn: tags(p.tEn),
  };
}

export function cleanContent(b) {
  if (!Array.isArray(b.projects) || b.projects.length > MAX_PROJECTS) throw new HttpError('bad-projects');
  const seen = new Set();
  const projects = b.projects.map((p) => cleanProject(p, seen));
  const whatsapp = String(b.whatsapp || '').replace(/\D/g, '');
  if (whatsapp && (whatsapp.length < 8 || whatsapp.length > 15)) throw new HttpError('bad-whatsapp');
  return { projects, whatsapp, requestsOn: b.requestsOn !== false };
}

/* the built-in list, as the admin first sees it */
export function seed() {
  const seen = new Set();
  return {
    projects: J.PROJECTS.map((p, i) => cleanProject({ ...p, id: 's' + (i + 1) }, seen)),
    whatsapp: '', requestsOn: true,
  };
}

export async function readContent(env) {
  const r = await env.DB.prepare('SELECT json, version, updated FROM content WHERE id = 1').first();
  if (!r) return null;
  return { ...JSON.parse(r.json), version: r.version, updated: r.updated };
}

/* the photo ids the saved gallery uses */
export const photoIds = (c) => new Set((c.projects || []).map((p) => (p.img.startsWith('api/photo/') ? p.img.slice(10) : '')).filter(Boolean));

/* what the site sees: no hidden projects */
export function publicView(c) {
  if (!c) return { ok: true, live: true, projects: null, whatsapp: '', requestsOn: true, version: 0 };
  return { ok: true, live: true, projects: c.projects.filter((p) => !p.hidden), whatsapp: c.whatsapp, requestsOn: c.requestsOn, version: c.version };
}

/* photos: PNG, JPEG or WebP, told by their first bytes, at most 1.5 MB */
export const PHOTO_MAX = 1.5 * 1024 * 1024;
export function photoType(b) {
  if (b.length > 12 && b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return 'image/webp';
  if (b.length > 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47 && b[4] === 0x0d && b[5] === 0x0a && b[6] === 0x1a && b[7] === 0x0a) return 'image/png';
  return '';
}
