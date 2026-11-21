/* Phones and tablets: fetches one film's frame tiles and decodes them here, off the page's main thread,
   so that scrolling the film stays smooth. Each tile is a 1920×1080 WebP holding four frames (2×2).
   The page sends the tiles it needs, nearest first; the decoded tiles go back as ImageBitmaps.
   Every other tile of the film is also fetched in the background and kept compressed (about 250 KB each),
   so scrolling back and forth never waits for the network. */
let base = "", n = 0, tw = 1920, need = [], center = 1, decoding = false;
const blobs = new Map(), loading = new Map(), failed = new Set();
const name = k => `t${String(k).padStart(3, "0")}.webp`;

function get(k){
  if (blobs.has(k)) return Promise.resolve(blobs.get(k));
  if (!loading.has(k)){
    loading.set(k, fetch(base + name(k))
      .then(r => (r.ok ? r.blob() : null)).catch(() => null)
      .then(b => { loading.delete(k); if (b) blobs.set(k, b); else failed.add(k); fill(); decode(); return b; }));
  }
  return loading.get(k);
}

/* the tiles the page needs first, then the rest of the film outward from where the viewer is */
function fill(){
  const queue = need.filter(k => !blobs.has(k) && !loading.has(k) && !failed.has(k));
  if (loading.size < 4){
    const rest = [];
    for (let k = 1; k <= n; k++) if (!blobs.has(k) && !loading.has(k) && !failed.has(k) && !queue.includes(k)) rest.push(k);
    rest.sort((a, b) => Math.abs(a - center) - Math.abs(b - center));
    queue.push(...rest);
  }
  while (loading.size < 4 && queue.length) get(queue.shift());
}

async function decode(){
  if (decoding) return; decoding = true;
  try {
    for (;;){
      const k = need.find(x => blobs.has(x) || failed.has(x));
      if (k === undefined) break;
      need = need.filter(x => x !== k);
      if (failed.has(k)){ failed.delete(k); postMessage({ k, fail: true }); continue; }
      const blob = blobs.get(k), th = Math.round(tw * 9 / 16);
      let bm = null;
      try { bm = await createImageBitmap(blob, tw < 1920 ? { resizeWidth: tw, resizeHeight: th, resizeQuality: "high" } : {}); }
      catch (e){ try { bm = await createImageBitmap(blob); } catch (e2){ bm = null; } }
      if (bm) postMessage({ k, bm }, [bm]); else postMessage({ k, fail: true });
    }
  } finally { decoding = false; }
}

self.onmessage = e => {
  const m = e.data || {};
  if (m.init){
    base = m.init.base; n = m.init.n; tw = m.init.tw || 1920;
    postMessage({ ready: typeof createImageBitmap === "function" && typeof fetch === "function" });
  }
  if (m.tw) tw = m.tw;
  if (m.need){ need = m.need.slice(); if (need.length) center = need[0]; fill(); decode(); }
};
