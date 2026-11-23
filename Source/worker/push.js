// Notifications on the company's phones (Web Push), sent by the server when a request arrives.
// Each phone or computer that turns notifications on in the admin panel gives a subscription (an address at Apple's,
// Google's or Mozilla's push service plus two keys). The server signs each send with its own VAPID key pair, made the first
// time it is needed and kept in the private table, and encrypts the message for that device (RFC 8291, aes128gcm), so the
// push service carries it without being able to read it.
import { b64u, rand, HttpError } from './util.js';
import { getPrivate, initPrivate } from './schema.js';

const enc = new TextEncoder();
const MAX_SUBS = 5;   // each device costs about 1 ms of the free plan's 10 ms when a request arrives
/* the push services browsers use; any other address is refused */
const HOSTS = [/(^|\.)push\.apple\.com$/, /^fcm\.googleapis\.com$/, /^android\.googleapis\.com$/, /(^|\.)push\.services\.mozilla\.com$/, /(^|\.)notify\.windows\.com$/];

export function cleanSubscription(b, env) {
  const s = b && b.subscription;
  if (!s || typeof s.endpoint !== 'string' || s.endpoint.length > 1000 || !s.keys) throw new HttpError('bad-subscription');
  let u; try { u = new URL(s.endpoint); } catch (e) { throw new HttpError('bad-subscription'); }
  const loop = env.TEST_PUSH_LOOPBACK === '1' && u.protocol === 'http:' && u.hostname === '127.0.0.1';
  if (!loop && (u.protocol !== 'https:' || !HOSTS.some((h) => h.test(u.hostname)))) throw new HttpError('bad-push-service');
  let p256dh, auth;
  try { p256dh = b64u.dec(s.keys.p256dh); auth = b64u.dec(s.keys.auth); } catch (e) { throw new HttpError('bad-subscription'); }
  if (p256dh.length !== 65 || p256dh[0] !== 4 || auth.length !== 16) throw new HttpError('bad-subscription');
  const label = typeof b.label === 'string' ? b.label.replace(/[\u0000-\u001F\u007F]/g, '').trim().slice(0, 60) : '';
  return { endpoint: s.endpoint, p256dh: s.keys.p256dh, auth: s.keys.auth, label };
}

export async function countSubs(env) {
  return (await env.DB.prepare('SELECT COUNT(*) AS n FROM push_subs').first()).n;
}
export const MAX = MAX_SUBS;

/* the server's key pair, made once */
export async function vapid(env) {
  let v = await getPrivate(env, 'vapid');
  if (!v) {
    const kp = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
    const pub = b64u.enc(await crypto.subtle.exportKey('raw', kp.publicKey));
    const jwk = await crypto.subtle.exportKey('jwk', kp.privateKey);
    v = await initPrivate(env, 'vapid', JSON.stringify({ pub, jwk }));
  }
  const { pub, jwk } = JSON.parse(v);
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  return { pub, key };
}

async function jwt(key, aud, sub) {
  const head = b64u.enc(enc.encode(JSON.stringify({ typ: 'JWT', alg: 'ES256' })));
  const body = b64u.enc(enc.encode(JSON.stringify({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub })));
  const sig = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, enc.encode(head + '.' + body));
  return head + '.' + body + '.' + b64u.enc(sig);
}

async function hkdf(salt, ikm, info, bytes) {
  const k = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveBits']);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: 'HKDF', hash: 'SHA-256', salt, info }, k, bytes * 8));
}
const cat = (...a) => { const n = a.reduce((x, b) => x + b.length, 0); const o = new Uint8Array(n); let i = 0; for (const b of a) { o.set(b, i); i += b.length; } return o; };

/* RFC 8291: the message encrypted for one device (one record, aes128gcm) */
export async function encrypt(payload, p256dhB64, authB64) {
  const ua = b64u.dec(p256dhB64), secret = b64u.dec(authB64);
  const uaKey = await crypto.subtle.importKey('raw', ua, { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const eph = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const as = new Uint8Array(await crypto.subtle.exportKey('raw', eph.publicKey));
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: 'ECDH', public: uaKey }, eph.privateKey, 256));
  const ikm = await hkdf(secret, shared, cat(enc.encode('WebPush: info\0'), ua, as), 32);
  const salt = rand(16);
  const cek = await hkdf(salt, ikm, enc.encode('Content-Encoding: aes128gcm\0'), 16);
  const nonce = await hkdf(salt, ikm, enc.encode('Content-Encoding: nonce\0'), 12);
  const key = await crypto.subtle.importKey('raw', cek, 'AES-GCM', false, ['encrypt']);
  const plain = cat(enc.encode(payload), new Uint8Array([2]));
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, key, plain));
  const head = new Uint8Array(21 + as.length);
  head.set(salt, 0); new DataView(head.buffer).setUint32(16, 4096); head[20] = as.length; head.set(as, 21);
  return cat(head, ct);
}

/* one message to one device; true when the push service took it, 'gone' when the device is no longer subscribed */
export async function sendOne(env, v, sub, message, origin) {
  const u = new URL(sub.endpoint);
  const token = await jwt(v.key, u.origin, origin.startsWith('https:') ? origin : 'mailto:noreply@example.com');
  const body = await encrypt(JSON.stringify(message), sub.p256dh, sub.auth);
  const r = await fetch(sub.endpoint, {
    method: 'POST', redirect: 'manual', signal: AbortSignal.timeout(8000),
    headers: { Authorization: `vapid t=${token}, k=${v.pub}`, TTL: '86400', Urgency: 'high', 'Content-Encoding': 'aes128gcm', 'Content-Type': 'application/octet-stream' },
    body,
  });
  if (r.status === 404 || r.status === 410) return 'gone';
  if (r.status >= 200 && r.status < 300) return true;
  throw new Error('push-' + r.status);
}

/* to every subscribed device; devices that unsubscribed are dropped */
export async function sendAll(env, message, origin, only) {
  const subs = (await env.DB.prepare('SELECT endpoint, p256dh, auth FROM push_subs').all()).results
    .filter((s) => !only || s.endpoint === only);
  if (!subs.length) return { sent: 0, failed: 0, devices: 0 };
  const v = await vapid(env);
  let sent = 0, failed = 0;
  const now = new Date().toISOString();
  await Promise.all(subs.map(async (s) => {
    try {
      const r = await sendOne(env, v, s, message, origin);
      if (r === 'gone') { await env.DB.prepare('DELETE FROM push_subs WHERE endpoint = ?').bind(s.endpoint).run(); failed++; return; }
      sent++;
      await env.DB.prepare('UPDATE push_subs SET last_ok = ?, last_err = NULL WHERE endpoint = ?').bind(now, s.endpoint).run();
    } catch (e) {
      failed++;
      const code = /^push-\d+$/.test(e.message) ? e.message : (e.name === 'TimeoutError' ? 'timeout' : 'network');
      await env.DB.prepare('UPDATE push_subs SET last_err = ? WHERE endpoint = ?').bind(now + ' ' + code, s.endpoint).run();
    }
  }));
  return { sent, failed, devices: subs.length };
}
