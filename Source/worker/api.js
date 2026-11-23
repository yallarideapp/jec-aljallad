// Everything under /api/: the site's content and request form, the photos, and the admin panel.
import { json, fail, HttpError, readJson, readText, sameOrigin, nowIso, rand, hex, line, text } from './util.js';
import { schema, getPrivate, setPrivate } from './schema.js';
import * as A from './auth.js';
import { cleanRequest, requestLimited, row, STATUSES, REQUEST_LIMITS } from './requests.js';
import { cleanContent, seed, readContent, publicView, photoIds, photoType, PHOTO_MAX } from './content.js';
import { cleanSubscription, countSubs, MAX as MAX_SUBS, vapid, sendAll } from './push.js';
import { cleanEmail, mailReady, sendMail } from './mail.js';

/* ---------- alerts for a new request: email and phones, after the request is saved ---------- */
function summaryAr(no, d) {
  return [
    `طلب مشروع جديد ${no}`,
    `الاسم: ${d.name}`, `الهاتف: ${d.phone}`,
    `القطاع: ${d.catAr}${d.subAr ? ' — ' + d.subAr : ''}`,
    `نطاق العمل: ${d.scopeAr.join(' + ')}${d.tradesAr.length ? ' (' + d.tradesAr.join('، ') + ')' : ''}`,
    `المساحة: ${d.area} م² × ${d.floors} = ${d.total} م²`,
    d.loc ? `الموقع: ${d.loc}` : null,
    `موعد البدء: ${d.startAr}`, `المخططات: ${d.drawAr}`,
    d.notes ? `ملاحظات: ${d.notes}` : null,
  ].filter(Boolean).join('\n');
}

async function lastStatus(env, k, ok, err) {
  await setPrivate(env, k, JSON.stringify({ at: nowIso(), ok, err: err || '' }));
}

async function alerts(env, origin, r) {
  const d = r.data, admin = origin + '/admin/#r=' + r.id;
  const jobs = [];
  const to = await getPrivate(env, 'alertEmail');
  if (mailReady(env) && to && (await getPrivate(env, 'mailOn')) !== '0') {
    jobs.push(sendMail(env, to, `طلب مشروع جديد ${r.no} — ${d.name}`, summaryAr(r.no, d) + `\n\nافتح الطلب: ${admin}`, 'req-' + r.no)
      .then(() => lastStatus(env, 'mailLast', true), (e) => lastStatus(env, 'mailLast', false, e.message)));
  }
  // more than 20 requests in the last hour looks like a flood: the panel still lists them, but phones are not woken for each
  const hour = (await env.DB.prepare("SELECT COUNT(*) AS n FROM attempts WHERE kind = 'req' AND at > ?").bind(Date.now() - 3600e3).first()).n;
  if (hour <= 20) {
    jobs.push(sendAll(env, { title: `طلب مشروع جديد ${r.no}`, body: `${d.name} · ${d.catAr} · ${d.total} م²`, url: './#r=' + r.id, tag: 'req-' + r.id }, origin)
      .then((s) => s.devices && lastStatus(env, 'pushLast', s.sent > 0, s.sent ? '' : 'push-failed'), (e) => lastStatus(env, 'pushLast', false, 'push-error')));
  }
  await Promise.allSettled(jobs);
}

/* ---------- public ---------- */
async function postRequest(request, env, ctx, url) {
  const b = await readJson(request);
  if (b.hp) throw new HttpError('bad-request');                  // a field people never see: only bots fill it
  if (b.consent !== true) throw new HttpError('consent-required');
  const c = await readContent(env);
  if (c && c.requestsOn === false) throw new HttpError('requests-off', 403);
  const d = cleanRequest(b);
  const key = typeof b.key === 'string' && /^[A-Za-z0-9_-]{16,64}$/.test(b.key) ? b.key : null;
  if (!key) throw new HttpError('bad-key');
  const again = await env.DB.prepare('SELECT id, no FROM requests WHERE idem = ?').bind(key).first();
  if (again) return json({ ok: true, no: again.no, again: true });
  const w = await A.whoFor(env, request);
  const now = nowIso(), data = JSON.stringify({ ...d, consent: { at: now, policy: line(b.policy, 12) } });
  /* the limits are checked in the same transaction that saves the request, so requests sent at the same moment
     cannot all slip under them: the attempt row is written only while under the limits, and the request only with it */
  const tok = hex(rand(12)), t = Date.now(), L = REQUEST_LIMITS;
  const withTok = 'EXISTS (SELECT 1 FROM attempts WHERE tok = ?)';
  let res;
  try {
    res = await env.DB.batch([
      env.DB.prepare(`INSERT INTO attempts (kind, who, at, tok) SELECT 'req', ?1, ?2, ?3
        WHERE (SELECT COUNT(*) FROM attempts WHERE kind = 'req' AND who = ?1 AND at > ?4) < ${L.hour}
          AND (SELECT COUNT(*) FROM attempts WHERE kind = 'req' AND who = ?1 AND at > ?5) < ${L.day}
          AND (SELECT COUNT(*) FROM attempts WHERE kind = 'req' AND at > ?4) < ${L.allHour}
          AND (SELECT COUNT(*) FROM attempts WHERE kind = 'req' AND at > ?5) < ${L.allDay}`).bind(w, t, tok, t - 3600e3, t - 86400e3),
      env.DB.prepare(`UPDATE counters SET value = value + 1 WHERE name = 'request' AND ${withTok}`).bind(tok),
      env.DB.prepare(`INSERT INTO requests (no, idem, created, updated, status, name, phone, data)
                      SELECT 'JEC-' || printf('%04d', value), ?, ?, ?, 'new', ?, ?, ? FROM counters WHERE name = 'request' AND ${withTok}`)
        .bind(key, now, now, d.name, d.phone, data, tok),
      env.DB.prepare('SELECT id, no FROM requests WHERE idem = ?').bind(key),
    ]);
  } catch (e) {
    const same = await env.DB.prepare('SELECT id, no FROM requests WHERE idem = ?').bind(key).first();   // the same request sent twice at once
    if (same) return json({ ok: true, no: same.no, again: true });
    throw e;
  }
  const saved = res[3].results[0];
  if (!saved) throw new HttpError(await requestLimited(env, w), 429);   // 'too-many' from this place, 'busy' for the whole site
  ctx.waitUntil(alerts(env, url.origin, { id: saved.id, no: saved.no, data: d }).catch(() => {}));
  return json({ ok: true, no: saved.no });
}

async function photo(env, id) {
  if (!/^[a-f0-9]{32}$/.test(id)) return fail('not-found', 404);
  const cacheKey = new Request('https://photo.cache/' + id);
  const cache = caches.default;
  const hit = await cache.match(cacheKey);
  if (hit) return hit;
  const { value, metadata } = await env.PHOTOS.getWithMetadata('photo:' + id, { type: 'arrayBuffer' });
  if (!value) return fail('not-found', 404);
  const res = new Response(value, { headers: {
    'Content-Type': (metadata && metadata.type) || 'application/octet-stream',
    'Cache-Control': 'public, max-age=31536000, immutable', 'X-Content-Type-Options': 'nosniff',
  } });
  await cache.put(cacheKey, res.clone());
  return res;
}

/* ---------- admin ---------- */
async function adminState(request, env) {
  const [row0, s] = await Promise.all([A.adminRow(env), A.session(env, request)]);
  return json({ ok: true, hasPassword: !!row0, auth: !!s, setupReady: !!env.ADMIN_SETUP_CODE });
}

async function setupOrReset(request, env, reset) {
  const b = await readJson(request, 4096);
  const existing = await A.adminRow(env);
  if (existing && !reset) throw new HttpError('already-set', 409);
  if (!env.ADMIN_SETUP_CODE) throw new HttpError('no-setup-code', 503);
  const password = A.checkPassword(b.password);
  const tok = await A.claimTry(env, await A.whoFor(env, request), 'code');
  if (!(await A.codeMatches(env, b.code))) throw new HttpError('bad-code', 403);
  await A.tryWorked(env, tok);
  const gen = await A.setPassword(env, password);
  return json({ ok: true }, 200, { 'Set-Cookie': await A.newSession(env, gen) });
}

async function login(request, env) {
  const b = await readJson(request, 4096);
  const r = await A.adminRow(env);
  if (!r) throw new HttpError('no-password', 409);
  const tok = await A.claimTry(env, await A.whoFor(env, request), 'login');
  if (!(await A.verifyPassword(r, b.password))) throw new HttpError('bad-password', 403);
  await A.tryWorked(env, tok);
  return json({ ok: true }, 200, { 'Set-Cookie': await A.newSession(env, r.gen) });
}

async function changePassword(request, env) {
  const b = await readJson(request, 4096);
  const next = A.checkPassword(b.next);
  const r = await A.adminRow(env);
  const tok = await A.claimTry(env, await A.whoFor(env, request), 'login');
  if (!(await A.verifyPassword(r, b.current))) throw new HttpError('bad-password', 403);
  await A.tryWorked(env, tok);
  const gen = await A.setPassword(env, next);
  return json({ ok: true }, 200, { 'Set-Cookie': await A.newSession(env, gen) });
}

async function listRequests(env, url) {
  const status = url.searchParams.get('status') || '';
  const q = line(url.searchParams.get('q') || '', 60);
  const before = Number(url.searchParams.get('before') || 0);
  const where = [], args = [];
  if (STATUSES.includes(status)) { where.push('status = ?'); args.push(status); }
  if (q) { where.push("(name LIKE ? ESCAPE '\\' OR phone LIKE ? ESCAPE '\\' OR no LIKE ? ESCAPE '\\')"); const l = '%' + q.replace(/[\\%_]/g, (m) => '\\' + m) + '%'; args.push(l, l, l); }
  if (Number.isInteger(before) && before > 0) { where.push('id < ?'); args.push(before); }
  const sql = `SELECT id, no, created, updated, status, name, phone, data, note FROM requests ${where.length ? 'WHERE ' + where.join(' AND ') : ''} ORDER BY id DESC LIMIT 31`;
  const [list, counts] = await env.DB.batch([
    env.DB.prepare(sql).bind(...args),
    env.DB.prepare('SELECT status, COUNT(*) AS n FROM requests GROUP BY status'),
  ]);
  const items = list.results.slice(0, 30).map(row);
  const c = Object.fromEntries(STATUSES.map((s) => [s, 0]));
  for (const x of counts.results) if (x.status in c) c[x.status] = x.n;
  return json({ ok: true, items, more: list.results.length > 30, counts: c });
}

async function oneRequest(request, env, id) {
  if (request.method === 'GET') {
    const r = await env.DB.prepare('SELECT id, no, created, updated, status, name, phone, data, note FROM requests WHERE id = ?').bind(id).first();
    return r ? json({ ok: true, item: row(r) }) : fail('not-found', 404);
  }
  if (request.method === 'DELETE') {
    const r = await env.DB.prepare('DELETE FROM requests WHERE id = ?').bind(id).run();
    return r.meta.changes ? json({ ok: true }) : fail('not-found', 404);
  }
  if (request.method === 'PATCH') {
    const b = await readJson(request, 8192);
    const sets = [], args = [];
    if ('status' in b) { if (!STATUSES.includes(b.status)) throw new HttpError('bad-status'); sets.push('status = ?'); args.push(b.status); }
    if ('note' in b) { sets.push('note = ?'); args.push(text(b.note, 2000)); }
    if (!sets.length) throw new HttpError('nothing');
    sets.push('updated = ?'); args.push(nowIso());
    const r = await env.DB.prepare(`UPDATE requests SET ${sets.join(', ')} WHERE id = ? RETURNING id, no, created, updated, status, name, phone, data, note`).bind(...args, id).first();
    return r ? json({ ok: true, item: row(r) }) : fail('not-found', 404);
  }
  return fail('method', 405);
}

async function adminContent(request, env) {
  if (request.method === 'GET') {
    const c = await readContent(env);
    return json({ ok: true, ...(c || { ...seed(), version: 0, updated: null }), seeded: !c });
  }
  const b = await readJson(request, 256 * 1024);
  const version = Number(b.version);
  if (!Number.isInteger(version) || version < 0) throw new HttpError('bad-version');
  const c = cleanContent(b);
  const now = nowIso(), body = JSON.stringify(c);
  let r;
  if (version === 0) r = await env.DB.prepare('INSERT INTO content (id, json, version, updated) VALUES (1, ?, 1, ?) ON CONFLICT(id) DO NOTHING').bind(body, now).run();
  else r = await env.DB.prepare('UPDATE content SET json = ?, version = version + 1, updated = ? WHERE id = 1 AND version = ?').bind(body, now, version).run();
  if (!r.meta.changes) throw new HttpError('conflict', 409);
  // photos no longer used, uploaded more than a day ago, are deleted
  const used = photoIds(c);
  const old = (await env.DB.prepare('SELECT id FROM photos WHERE created < ?').bind(new Date(Date.now() - 86400e3).toISOString()).all()).results.filter((p) => !used.has(p.id));
  for (const p of old.slice(0, 20)) {
    await env.PHOTOS.delete('photo:' + p.id);
    await env.DB.prepare('DELETE FROM photos WHERE id = ?').bind(p.id).run();
    await caches.default.delete(new Request('https://photo.cache/' + p.id)).catch(() => {});
  }
  return json({ ok: true, version: version + 1, updated: now, projects: c.projects, whatsapp: c.whatsapp, requestsOn: c.requestsOn });
}

async function uploadPhoto(request, env) {
  const declared = (request.headers.get('Content-Type') || '').split(';')[0].trim().toLowerCase();
  if (!['image/webp', 'image/jpeg', 'image/png'].includes(declared)) throw new HttpError('bad-type', 415);
  const bytes = await readText(request, PHOTO_MAX);
  const type = photoType(bytes);
  if (!type || type !== declared) throw new HttpError('bad-image');
  const n = (await env.DB.prepare('SELECT COUNT(*) AS n FROM photos').first()).n;
  if (n >= 500) throw new HttpError('too-many-photos', 409);
  const id = hex(rand(16));
  await env.DB.prepare('INSERT INTO photos (id, type, bytes, created) VALUES (?, ?, ?, ?)').bind(id, type, bytes.length, nowIso()).run();
  try { await env.PHOTOS.put('photo:' + id, bytes, { metadata: { type } }); }
  catch (e) { await env.DB.prepare('DELETE FROM photos WHERE id = ?').bind(id).run(); throw e; }
  return json({ ok: true, id, img: 'api/photo/' + id });
}

async function settings(request, env) {
  if (request.method === 'PUT') {
    const b = await readJson(request, 4096);
    if ('alertEmail' in b) await setPrivate(env, 'alertEmail', cleanEmail(b.alertEmail));
    if ('mailOn' in b) await setPrivate(env, 'mailOn', b.mailOn ? '1' : '0');
  }
  const [alertEmail, mailOn, mailLast, pushLast] = await Promise.all(['alertEmail', 'mailOn', 'mailLast', 'pushLast'].map((k) => getPrivate(env, k)));
  const devices = (await env.DB.prepare('SELECT endpoint, label, created, last_ok, last_err FROM push_subs ORDER BY created').all()).results
    .map((d) => ({ id: d.endpoint.slice(-12), label: d.label, created: d.created, lastOk: d.last_ok, lastErr: d.last_err }));
  return json({
    ok: true, alertEmail: alertEmail || '', mailOn: mailOn !== '0', mailReady: mailReady(env),
    mailLast: mailLast ? JSON.parse(mailLast) : null, pushLast: pushLast ? JSON.parse(pushLast) : null, devices,
  });
}

async function testMail(request, env) {
  const to = await getPrivate(env, 'alertEmail');
  if (!to) throw new HttpError('no-email');
  if (!mailReady(env)) throw new HttpError('mail-not-set', 503);
  try {
    await sendMail(env, to, 'تجربة تنبيهات موقع JEC', 'هذه رسالة تجربة من لوحة تحكم موقع JEC. إذا وصلتك، فتنبيهات الطلبات الجديدة ستصل إلى هذا البريد.', 'test-' + hex(rand(8)));
    await lastStatus(env, 'mailLast', true);
    return json({ ok: true });
  } catch (e) {
    await lastStatus(env, 'mailLast', false, e.message);
    return fail(/^mail-[a-z0-9-]+$/.test(e.message) ? e.message : 'mail-failed', 502);
  }
}

async function push(request, env, url, action) {
  if (action === 'key') return json({ ok: true, key: (await vapid(env)).pub });
  const b = await readJson(request, 4096);
  if (action === 'subscribe') {
    const s = cleanSubscription(b, env);
    const exists = await env.DB.prepare('SELECT 1 FROM push_subs WHERE endpoint = ?').bind(s.endpoint).first();
    if (!exists && (await countSubs(env)) >= MAX_SUBS) throw new HttpError('too-many-devices', 409);
    await env.DB.prepare(`INSERT INTO push_subs (endpoint, p256dh, auth, label, created) VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth, label = excluded.label`).bind(s.endpoint, s.p256dh, s.auth, s.label, nowIso()).run();
    return json({ ok: true });
  }
  if (action === 'unsubscribe') {
    if (typeof b.endpoint === 'string') await env.DB.prepare('DELETE FROM push_subs WHERE endpoint = ?').bind(b.endpoint).run();
    else if (typeof b.id === 'string' && /^[\x21-\x7e]{1,12}$/.test(b.id)) await env.DB.prepare('DELETE FROM push_subs WHERE substr(endpoint, -12) = ?').bind(b.id).run();
    return json({ ok: true });
  }
  if (action === 'test') {
    const r = await sendAll(env, { title: 'تجربة إشعارات JEC', body: 'الإشعارات شغّالة على هذا الجهاز.', url: './', tag: 'test' }, url.origin, typeof b.endpoint === 'string' ? b.endpoint : null);
    await lastStatus(env, 'pushLast', r.sent > 0, r.sent ? '' : 'push-failed');
    return json({ ok: true, ...r });
  }
  return fail('not-found', 404);
}

/* old rate-limit hashes (kept two days) and expired sessions: removed every night (wrangler.jsonc "triggers"), and at
   most once an hour while requests come in */
export async function cleanup(env) {
  await schema(env);
  const now = Date.now();
  await env.DB.batch([
    env.DB.prepare('DELETE FROM attempts WHERE at < ?').bind(now - 2 * 86400e3),
    env.DB.prepare('DELETE FROM sessions WHERE expires < ?').bind(now),
  ]);
}
let lastSweep = 0;
function sweep(env, ctx) {
  const now = Date.now();
  if (now - lastSweep < 3600e3) return;
  lastSweep = now;
  ctx.waitUntil(cleanup(env).catch(() => {}));
}

/* ---------- router ---------- */
export async function api(request, env, ctx, url) {
  const p = url.pathname, m = request.method;
  try {
    if (!env.DB) return fail('no-database', 503);
    await schema(env);
    sweep(env, ctx);
    if (m !== 'GET' && m !== 'HEAD' && !sameOrigin(request, url)) return fail('origin', 403);

    if (p === '/api/health') return json({ ok: true, live: true });
    if (p === '/api/content' && m === 'GET') return json(publicView(await readContent(env)));
    if (p === '/api/request' && m === 'POST') return await postRequest(request, env, ctx, url);
    if (p.startsWith('/api/photo/') && m === 'GET') return await photo(env, p.slice(11));

    if (p.startsWith('/api/admin/')) {
      const a = p.slice(11);
      if (a === 'state' && m === 'GET') return await adminState(request, env);
      if (a === 'setup' && m === 'POST') return await setupOrReset(request, env, false);
      if (a === 'reset' && m === 'POST') return await setupOrReset(request, env, true);
      if (a === 'login' && m === 'POST') return await login(request, env);
      if (a === 'logout' && m === 'POST') { await A.endSession(env, request); return json({ ok: true }, 200, { 'Set-Cookie': A.clearCookie }); }
      if (!(await A.session(env, request))) return fail('auth', 401, { 'Set-Cookie': A.clearCookie });
      if (a === 'password' && m === 'POST') return await changePassword(request, env);
      if (a === 'requests' && m === 'GET') return await listRequests(env, url);
      const rm = /^requests\/(\d{1,9})$/.exec(a);
      if (rm) return await oneRequest(request, env, Number(rm[1]));
      if (a === 'content' && (m === 'GET' || m === 'PUT')) return await adminContent(request, env);
      if (a === 'photo' && m === 'POST') return await uploadPhoto(request, env);
      if (a === 'settings' && (m === 'GET' || m === 'PUT')) return await settings(request, env);
      if (a === 'mail/test' && m === 'POST') return await testMail(request, env);
      const pm = /^push\/(key|subscribe|unsubscribe|test)$/.exec(a);
      if (pm && (pm[1] === 'key' ? m === 'GET' : m === 'POST')) return await push(request, env, url, pm[1]);
    }
    return fail('not-found', 404);
  } catch (e) {
    if (e instanceof HttpError) return fail(e.code, e.status);
    console.error('api', p, e && e.stack || e);
    return fail('server', 500);
  }
}
