// Small helpers shared by the API modules.

const BASE_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'same-origin',
};

export function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), { status, headers: { ...BASE_HEADERS, ...extra } });
}

/* errors carry a fixed code the pages translate; never a message from the database or a provider */
export const fail = (error, status = 400, extra = {}) => json({ ok: false, error }, status, extra);

export class HttpError extends Error {
  constructor(code, status = 400) { super(code); this.code = code; this.status = status; }
}

/* the body, at most `cap` bytes, as text */
export async function readText(request, cap) {
  const len = Number(request.headers.get('Content-Length') || 0);
  if (len > cap) throw new HttpError('too-large', 413);
  if (!request.body) return '';
  const reader = request.body.getReader();
  const parts = []; let n = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    n += value.byteLength;
    if (n > cap) { try { await reader.cancel(); } catch (e) {} throw new HttpError('too-large', 413); }
    parts.push(value);
  }
  const all = new Uint8Array(n); let o = 0;
  for (const p of parts) { all.set(p, o); o += p.byteLength; }
  return all;
}

export async function readJson(request, cap = 16384) {
  const type = (request.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
  if (type !== 'application/json') throw new HttpError('bad-type', 415);
  const bytes = await readText(request, cap);
  let v;
  try { v = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); } catch (e) { throw new HttpError('bad-json'); }
  if (!v || typeof v !== 'object' || Array.isArray(v)) throw new HttpError('bad-json');
  return v;
}

/* a change must come from a page of this site */
export function sameOrigin(request, url) {
  const o = request.headers.get('Origin');
  if (o) return o === url.origin;
  return request.headers.get('Sec-Fetch-Site') === 'same-origin';
}

export const b64u = {
  enc(buf) {
    const b = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
    let s = ''; for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  },
  dec(str) {
    const s = String(str).replace(/-/g, '+').replace(/_/g, '/');
    const bin = atob(s + '='.repeat((4 - (s.length % 4)) % 4));
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  },
};

export const rand = (n) => crypto.getRandomValues(new Uint8Array(n));
export const hex = (buf) => [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, '0')).join('');
export async function sha256hex(data) {
  const b = typeof data === 'string' ? new TextEncoder().encode(data) : data;
  return hex(await crypto.subtle.digest('SHA-256', b));
}

/* the same length whatever the input, so the time taken says nothing about how much matched */
export async function sameSecret(a, b) {
  const [x, y] = await Promise.all([sha256hex('k:' + String(a)), sha256hex('k:' + String(b))]);
  let d = 0; for (let i = 0; i < x.length; i++) d |= x.charCodeAt(i) ^ y.charCodeAt(i);
  return d === 0;
}

/* a plain string: trimmed, control characters dropped, at most `max` characters */
export function text(v, max) {
  if (typeof v !== 'string') return '';
  return v.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').replace(/\r\n?/g, '\n').trim().slice(0, max);
}
export function line(v, max) { return text(v, max).replace(/\s+/g, ' '); }

export const nowIso = () => new Date().toISOString();

/* who is asking, for rate limits: the address hashed with a private salt; IPv6 addresses are grouped by /56 */
export async function who(request, salt) {
  let ip = request.headers.get('CF-Connecting-IP') || '0.0.0.0';
  if (ip.includes(':')) {
    const parts = ip.split('::');
    const head = parts[0] ? parts[0].split(':') : [];
    const tail = parts.length > 1 && parts[1] ? parts[1].split(':') : [];
    const full = [...head, ...Array(Math.max(0, 8 - head.length - tail.length)).fill('0'), ...tail];
    ip = full.slice(0, 3).join(':') + ':' + (full[3] || '0').padStart(4, '0').slice(0, 2) + '::/56';
  }
  return (await sha256hex(salt + '|' + ip)).slice(0, 32);
}
