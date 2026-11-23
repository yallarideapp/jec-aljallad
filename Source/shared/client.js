/* How the site (index.html) and the admin panel (admin/) talk to the server: JECAPI.call(method, path, body).
   On Cloudflare the server answers under api/. On the GitHub Pages preview (*.github.io), or a page opened from the file,
   there is no server: a demo stand-in then keeps the requests, the gallery and the photos in this
   browser only (localStorage), so the panel can be tried and shown. Nothing sent there reaches the company; the pages say so.
   The demo is chosen by the address alone, never because the real server failed to answer (a visitor's request would
   then stay in his browser): on any other host a failure is shown as an error. On this machine (localhost) the server
   is asked, so `node server.cjs` runs the demo and `wrangler dev` the real thing.
   A classic script (sets globalThis.JECAPI). Needs shared/data.js first. */
globalThis.JECAPI = (() => {
  let base = "", mode = null, modeP = null;
  const KEY = "jec-demo-v1", PHOTO = "jec-demo-photo-";

  function setBase(b){ base = b || ""; }
  function detect(){
    if (!modeP) modeP = (async () => {
      const h = location.hostname;
      if (location.protocol === "file:" || /(^|\.)github\.io$/i.test(h)) return "demo";
      if (!/^(localhost|127\.0\.0\.1|\[::1\])$/.test(h)) return "live";
      try {
        const ctl = typeof AbortController === "function" ? new AbortController() : null;
        const t = ctl ? setTimeout(() => ctl.abort(), 6000) : 0;
        const r = await fetch(base + "api/health", { cache: "no-store", signal: ctl ? ctl.signal : undefined });
        clearTimeout(t);
        if (r.ok && (r.headers.get("content-type") || "").includes("json")){ const j = await r.json(); if (j && j.live) return "live"; }
      } catch (e) {}
      return "demo";
    })().then(m => (mode = m));
    return modeP;
  }

  async function call(method, path, body){
    const m = await detect();
    if (m === "demo") { try { return await demo(method, path, body); } catch (e) { return { ok: false, error: e && e.code || "demo-error", status: e && e.status || 400 }; } }
    const init = { method, credentials: "same-origin", cache: "no-store", headers: {} };
    if (typeof Blob !== "undefined" && body instanceof Blob){ init.body = body; init.headers["Content-Type"] = body.type; }
    else if (body !== undefined){ init.body = JSON.stringify(body); init.headers["Content-Type"] = "application/json"; }
    let r;
    try { r = await fetch(base + "api/" + path, init); } catch (e) { return { ok: false, error: "network", status: 0 }; }
    let j = null; try { j = await r.json(); } catch (e) {}
    if (!j || typeof j !== "object") return { ok: false, error: "server", status: r.status };
    j.status = r.status; return j;
  }

  /* a picture's address from this page; photos uploaded in the demo live in this browser */
  function img(p){
    if (!p) return "";
    if (p.startsWith("api/photo/") && mode === "demo"){ try { return localStorage.getItem(PHOTO + p.slice(10)) || ""; } catch (e) { return ""; } }
    return base + p;
  }

  /* ---------------- the demo stand-in ---------------- */
  const err = (code, status = 400) => { const e = new Error(code); e.code = code; e.status = status; throw e; };
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  const save = s => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { err("demo-full", 507); } };
  const now = () => new Date().toISOString();
  const hexOf = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
  const randHex = n => hexOf(crypto.getRandomValues(new Uint8Array(n)));
  const STATUSES = ["new", "contacted", "quoted", "won", "closed"];
  function seed(){
    return { projects: JEC.PROJECTS.map((p, i) => ({ id: "s" + (i + 1), img: p.img, video: p.video || "", url: p.url || "", type: p.url ? (p.type === "reel" ? "reel" : "post") : "none",
      cat: p.cat, st: p.st === "live" ? "live" : "done", reno: !!p.reno, h: !!p.h, hidden: false, brand: p.brand || "", ar: p.ar, en: p.en,
      dAr: p.dAr || "", dEn: p.dEn || "", tAr: p.tAr || [], tEn: p.tEn || [] })), whatsapp: "", requestsOn: true };
  }
  function labels(b){
    const J = JEC, cat = J.CATS.find(c => c.id === b.cat); if (!cat) err("bad-cat");
    const subs = J.SUBS[cat.id] || [], sub = Number.isInteger(b.sub) && b.sub >= 0 && b.sub < subs.length ? b.sub : 0;
    const scopes = J.SCOPES.filter(s => (b.scope || []).includes(s.id)); if (!scopes.length) err("bad-scope");
    const trades = scopes.some(s => s.id === "finishing") ? [...new Set(b.trades || [])].filter(i => Number.isInteger(i) && i >= 0 && i < J.TRADES.length).sort((x, y) => x - y) : [];
    const area = Math.max(20, Math.min(20000, b.area | 0)), floors = Math.max(1, Math.min(30, b.floors | 0));
    const start = Math.max(0, Math.min(J.STARTS.length - 1, b.start | 0)), draw = Math.max(0, Math.min(J.DRAW.length - 1, b.draw | 0));
    const name = String(b.name || "").trim().slice(0, 80); if (name.length < 2) err("bad-name");
    const phone = String(b.phone || "").trim().slice(0, 30), digits = phone.replace(/\D/g, "");
    if (!/^[+0-9 ()\-]+$/.test(phone) || digits.length < 7 || digits.length > 15) err("bad-phone");
    return { cat: cat.id, catAr: cat.sAr, catEn: cat.sEn, sub, subAr: subs[sub] ? subs[sub][0] : "", subEn: subs[sub] ? subs[sub][1] : "",
      scope: scopes.map(s => s.id), scopeAr: scopes.map(s => s.ar), scopeEn: scopes.map(s => s.en),
      trades, tradesAr: trades.map(i => J.TRADES[i].ar), tradesEn: trades.map(i => J.TRADES[i].en),
      area, floors, total: area * floors, loc: String(b.loc || "").trim().slice(0, 120),
      start, startAr: J.STARTS[start][0], startEn: J.STARTS[start][1], draw, drawAr: J.DRAW[draw][0], drawEn: J.DRAW[draw][1],
      notes: String(b.notes || "").trim().slice(0, 2000), lang: b.lang === "en" ? "en" : "ar", name, phone };
  }
  async function notifyDemo(r){
    try {
      if (localStorage.getItem("jec-demo-push") !== "1" || !("Notification" in window) || Notification.permission !== "granted" || !navigator.serviceWorker) return;
      const reg = await navigator.serviceWorker.getRegistration(new URL(base + "admin/", location.href).href);
      if (reg) await reg.showNotification("طلب مشروع جديد " + r.no, { body: `${r.name} · ${r.data.catAr} · ${r.data.total} م²`, icon: base + "admin/icon-192.png", badge: base + "admin/badge-96.png", tag: "req-" + r.id, data: { url: "./#r=" + r.id }, lang: "ar", dir: "rtl" });
    } catch (e) {}
  }
  async function demo(method, path, body){
    const s = load(), [route, query] = path.split("?"), q = new URLSearchParams(query || "");
    s.requests = s.requests || []; s.counter = s.counter || 0; s.settings = s.settings || { alertEmail: "", mailOn: true };
    if (route === "content" && method === "GET"){ const c = s.content || seed(); return { ok: true, demo: true, projects: s.content ? c.projects.filter(p => !p.hidden) : null, whatsapp: c.whatsapp, requestsOn: c.requestsOn, version: s.content ? s.content.version : 0 }; }
    if (route === "request" && method === "POST"){
      if (body.consent !== true) err("consent-required");
      if (s.content && s.content.requestsOn === false) err("requests-off", 403);
      const old = s.requests.find(r => r.idem && r.idem === body.key); if (old) return { ok: true, no: old.no, again: true, demo: true };
      const d = labels(body); s.counter++;
      d.consent = { at: now(), policy: String(body.policy || "").slice(0, 12) };
      const r = { id: s.counter, no: "JEC-" + String(s.counter).padStart(4, "0"), idem: body.key, created: now(), updated: now(), status: "new", name: d.name, phone: d.phone, note: "", data: d };
      s.requests.push(r); save(s); notifyDemo(r);
      return { ok: true, no: r.no, demo: true };
    }
    if (!route.startsWith("admin/")) err("not-found", 404);
    const a = route.slice(6);
    /* the demo has no password (Jafar, 2026-11-23): it holds no real data, so the panel opens straight away.
       The real panel on Cloudflare keeps its password. */
    if (a === "state") return { ok: true, demo: true, hasPassword: true, auth: true, setupReady: true };
    if (["setup", "reset", "login", "logout", "password"].includes(a)) return { ok: true, demo: true };
    if (a === "requests" && method === "GET"){
      const st = q.get("status") || "", term = (q.get("q") || "").trim().toLowerCase(), before = Number(q.get("before") || 0);
      let list = s.requests.slice().reverse();
      if (STATUSES.includes(st)) list = list.filter(r => r.status === st);
      if (term) list = list.filter(r => (r.name + " " + r.phone + " " + r.no).toLowerCase().includes(term));
      if (before) list = list.filter(r => r.id < before);
      const counts = Object.fromEntries(STATUSES.map(x => [x, s.requests.filter(r => r.status === x).length]));
      return { ok: true, items: list.slice(0, 30), more: list.length > 30, counts };
    }
    const rm = /^requests\/(\d+)$/.exec(a);
    if (rm){
      const i = s.requests.findIndex(r => r.id === Number(rm[1])); if (i < 0) err("not-found", 404);
      if (method === "GET") return { ok: true, item: s.requests[i] };
      if (method === "DELETE"){ s.requests.splice(i, 1); save(s); return { ok: true }; }
      const r = s.requests[i];
      if ("status" in body){ if (!STATUSES.includes(body.status)) err("bad-status"); r.status = body.status; }
      if ("note" in body) r.note = String(body.note || "").slice(0, 2000);
      r.updated = now(); save(s); return { ok: true, item: r };
    }
    if (a === "content"){
      if (method === "GET") return s.content ? { ok: true, ...s.content, seeded: false } : { ok: true, ...seed(), version: 0, updated: null, seeded: true };
      const v = s.content ? s.content.version : 0; if (body.version !== v) err("conflict", 409);
      if (!Array.isArray(body.projects)) err("bad-projects");
      const wa = String(body.whatsapp || "").replace(/\D/g, ""); if (wa && (wa.length < 8 || wa.length > 15)) err("bad-whatsapp");
      s.content = { projects: body.projects, whatsapp: wa, requestsOn: body.requestsOn !== false, version: v + 1, updated: now() };
      const used = new Set(body.projects.map(p => String(p.img || "")).filter(x => x.startsWith("api/photo/")).map(x => x.slice(10)));
      for (const k of Object.keys(localStorage)) if (k.startsWith(PHOTO) && !used.has(k.slice(PHOTO.length)) && !(s.fresh || []).includes(k.slice(PHOTO.length))) localStorage.removeItem(k);
      s.fresh = []; save(s); return { ok: true, ...s.content };
    }
    if (a === "photo" && method === "POST"){
      const url = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(body); });
      const id = randHex(16);
      try { localStorage.setItem(PHOTO + id, url); } catch (e) { err("demo-full", 507); }
      s.fresh = (s.fresh || []).concat(id); save(s);
      return { ok: true, id, img: "api/photo/" + id };
    }
    if (a === "settings"){
      if (method === "PUT"){ if ("alertEmail" in body) s.settings.alertEmail = String(body.alertEmail || "").trim(); if ("mailOn" in body) s.settings.mailOn = !!body.mailOn; save(s); }
      return { ok: true, demo: true, alertEmail: s.settings.alertEmail, mailOn: s.settings.mailOn, mailReady: false, mailLast: null, pushLast: null, devices: [] };
    }
    if (a === "mail/test") err("demo-only", 409);
    if (a === "push/key") return { ok: true, demo: true, key: null };
    err("not-found", 404);
  }

  return { setBase, detect, call, img, get mode(){ return mode; } };
})();
