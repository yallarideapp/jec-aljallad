/* The admin panel's service worker: shows the notifications the server sends when a request arrives, opens the
   request when one is tapped, and keeps the last copy of the panel so it opens even on a weak line.
   It never stores the requests or anything from api/. */
const SHELL = "jec-admin-shell-2";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k.startsWith("jec-admin-") && k !== SHELL) await caches.delete(k);
  await self.clients.claim();
})()));

/* the panel's page (only ./ and ./index.html) and its two scripts: network first, the saved copy when the network fails
   or takes more than 4 seconds */
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url), scope = new URL(self.registration.scope);
  if (req.method !== "GET" || url.origin !== location.origin || url.pathname.includes("/api/")) return;
  const page = req.mode === "navigate" && (url.pathname === scope.pathname || url.pathname === scope.pathname + "index.html");
  const script = /\/shared\/(data|client)\.js$/.test(url.pathname);
  if (!page && !script) return;
  const key = page ? scope.href : req;
  e.respondWith((async () => {
    const cache = await caches.open(SHELL);
    const net = fetch(req).then(res => { if (res.ok && res.type === "basic") cache.put(key, res.clone()); return res; });
    net.catch(() => {});
    const late = new Promise(r => setTimeout(r, 4000));
    try {
      const first = await Promise.race([net, late]);
      if (first) return first;
      const hit = await cache.match(key);
      return hit || await net;
    } catch (err) {
      const hit = await cache.match(key);
      if (hit) return hit;
      throw err;
    }
  })());
});

self.addEventListener("push", e => {
  let m = {};
  try { m = e.data ? e.data.json() : {}; } catch (err) { m = { body: e.data ? e.data.text() : "" }; }
  const title = String(m.title || "JEC").slice(0, 120);
  e.waitUntil((async () => {
    await self.registration.showNotification(title, {
      body: String(m.body || "").slice(0, 240), tag: String(m.tag || "jec"), renotify: true,
      icon: "icon-192.png", badge: "badge-96.png", lang: "ar", dir: "rtl",
      data: { url: typeof m.url === "string" && m.url.startsWith("./") ? m.url : "./" },
    });
    for (const c of await self.clients.matchAll({ type: "window" })) c.postMessage({ type: "push" });
  })());
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const target = new URL((e.notification.data && e.notification.data.url) || "./", self.registration.scope).href;
  e.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const open = wins.find(w => w.url.startsWith(self.registration.scope));
    if (open) { await open.focus(); open.postMessage({ type: "open", url: target }); return; }
    await self.clients.openWindow(target);
  })());
});
