// The admin's password and sessions.
// One admin password for the company. The first one is set with the setup code (ADMIN_SETUP_CODE, a Cloudflare secret);
// the same code also resets a forgotten password. Passwords are kept as PBKDF2-SHA-256 hashes (20,000 rounds: about 4 ms
// of the Worker's 10 ms per request). A session is a random token in an HttpOnly cookie that only /api/admin receives;
// the database keeps its hash. Changing the password ends every other session.
import { b64u, hex, rand, sha256hex, sameSecret, who, HttpError, nowIso } from './util.js';
import { getPrivate, initPrivate } from './schema.js';

export const ROUNDS = 20000;
export const MIN_PASSWORD = 10;
const SESSION_DAYS = 30;
const COOKIE = 'jec_admin';

async function pbkdf2(password, salt, rounds) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  return hex(await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt, iterations: rounds }, key, 256));
}

export function checkPassword(p) {
  if (typeof p !== 'string' || p.length < MIN_PASSWORD) throw new HttpError('password-short');
  if (p.length > 200) throw new HttpError('password-long');
  return p;
}

export async function salt(env) {
  return (await getPrivate(env, 'salt')) || initPrivate(env, 'salt', b64u.enc(rand(16)));
}

export async function whoFor(env, request) { return who(request, await salt(env)); }

/* Every try at the password ('login') or at the setup code ('code') is written down before it is checked, in the same
   step (one transaction) that counts the earlier tries, so tries sent at the same moment cannot all slip under the limit.
   A try that turns out right is taken off the list again. Limits within 15 minutes: 8 tries from one place; for the
   password also 60 in all. The setup code has no limit in all, so nobody can lock the owner out of resetting the
   password from his own connection (the code is long and secret). */
const WINDOW = 15 * 60 * 1000;
export async function claimTry(env, w, kind) {
  const now = Date.now(), tok = hex(rand(12));
  const inAll = kind === 'login' ? 60 : 0;
  const r = await env.DB.batch([
    env.DB.prepare(`INSERT INTO attempts (kind, who, at, tok) SELECT ?1, ?2, ?3, ?4
      WHERE (SELECT COUNT(*) FROM attempts WHERE kind = ?1 AND who = ?2 AND at > ?5) < 8
        AND (?6 = 0 OR (SELECT COUNT(*) FROM attempts WHERE kind = ?1 AND at > ?5) < ?6)`).bind(kind, w, now, tok, now - WINDOW, inAll),
    env.DB.prepare('SELECT 1 AS ok FROM attempts WHERE tok = ?').bind(tok),
  ]);
  if (!r[1].results.length) throw new HttpError('locked', 429);
  return tok;
}
export async function tryWorked(env, tok) {
  await env.DB.prepare('DELETE FROM attempts WHERE tok = ?').bind(tok).run();
}

export async function adminRow(env) {
  return env.DB.prepare('SELECT hash, salt, rounds, gen FROM admin WHERE id = 1').first();
}

export async function setPassword(env, password) {
  const s = rand(16);
  const hash = await pbkdf2(password, s, ROUNDS);
  const r = await env.DB.prepare(
    `INSERT INTO admin (id, hash, salt, rounds, gen, updated) VALUES (1, ?, ?, ?, 1, ?)
     ON CONFLICT(id) DO UPDATE SET hash = excluded.hash, salt = excluded.salt, rounds = excluded.rounds, gen = admin.gen + 1, updated = excluded.updated
     RETURNING gen`
  ).bind(hash, b64u.enc(s), ROUNDS, nowIso()).first();
  await env.DB.prepare('DELETE FROM sessions WHERE gen < ? OR expires < ?').bind(r.gen, Date.now()).run();
  return r.gen;
}

export async function verifyPassword(row, password) {
  if (!row || typeof password !== 'string' || password.length > 200) return false;
  const h = await pbkdf2(password, b64u.dec(row.salt), row.rounds || ROUNDS);
  return sameSecret(h, row.hash);
}

export async function codeMatches(env, code) {
  const want = env.ADMIN_SETUP_CODE;
  if (!want || typeof code !== 'string' || !code) return false;
  return sameSecret(code.trim(), String(want).trim());
}

export async function newSession(env, gen) {
  const token = b64u.enc(rand(32));
  const expires = Date.now() + SESSION_DAYS * 86400 * 1000;
  await env.DB.prepare('INSERT INTO sessions (token, gen, expires) VALUES (?, ?, ?)').bind(await sha256hex(token), gen, expires).run();
  return `${COOKIE}=${token}; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_DAYS * 86400}`;
}
export const clearCookie = `${COOKIE}=; Path=/api/admin; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;

function cookieToken(request) {
  const c = request.headers.get('Cookie') || '';
  for (const part of c.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === COOKIE) return v.join('=');
  }
  return '';
}

/* the session behind the request's cookie, or null */
export async function session(env, request) {
  const token = cookieToken(request);
  if (!token || token.length > 100) return null;
  const th = await sha256hex(token);
  const r = await env.DB.prepare(
    'SELECT s.token, s.gen, s.expires, a.gen AS agen FROM sessions s JOIN admin a ON a.id = 1 WHERE s.token = ?'
  ).bind(th).first();
  if (!r || r.expires < Date.now() || r.gen !== r.agen) return null;
  return { token: th };
}

export async function endSession(env, request) {
  const token = cookieToken(request);
  if (token && token.length <= 100) await env.DB.prepare('DELETE FROM sessions WHERE token = ?').bind(await sha256hex(token)).run();
}
