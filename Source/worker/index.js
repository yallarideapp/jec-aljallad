// The site's files in dist/ are served directly. Two paths reach this code first (run_worker_first in wrangler.jsonc):
// /api/* is the server: the request form, the projects gallery, photos and the admin panel (api.js);
// /media/* are the hero and end videos, played by <video> elements: iPhone Safari plays a video only when the server
// answers byte-range requests with 206. If the asset already comes back as 206 it is passed through; otherwise the
// requested bytes are cut here.
import { api, cleanup } from './api.js';

export default {
  /* every night (wrangler.jsonc "triggers"): old rate-limit hashes and expired sessions are deleted */
  async scheduled(event, env, ctx) { ctx.waitUntil(cleanup(env)); },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/')) return api(request, env, ctx, url);
    const range = request.headers.get('Range');
    const res = await env.ASSETS.fetch(request);
    if (res.status !== 200 || (request.method !== 'GET' && request.method !== 'HEAD')) return res;

    if (!range) {
      const out = new Response(res.body, res);
      out.headers.set('Accept-Ranges', 'bytes');
      return out;
    }

    const m = /^bytes=(\d*)-(\d*)$/.exec(range.trim());
    if (!m || (m[1] === '' && m[2] === '')) return res;          // several ranges or a malformed header: whole file
    const buf = await res.arrayBuffer();
    const size = buf.byteLength;
    let start, end;
    if (m[1] === '') { start = Math.max(0, size - Number(m[2])); end = size - 1; }      // bytes=-N (last N bytes)
    else { start = Number(m[1]); end = m[2] === '' ? size - 1 : Math.min(Number(m[2]), size - 1); }
    if (!(start <= end) || start >= size) {
      return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}`, 'Accept-Ranges': 'bytes' } });
    }
    const headers = new Headers(res.headers);
    headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
    headers.set('Content-Length', String(end - start + 1));
    headers.set('Accept-Ranges', 'bytes');
    return new Response(request.method === 'HEAD' ? null : buf.slice(start, end + 1), { status: 206, headers });
  }
};
