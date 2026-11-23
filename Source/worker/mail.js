// Email to the company when a request arrives, through Resend (https://resend.com, free up to 100 emails a day).
// Needs the Cloudflare secret RESEND_API_KEY. The address it goes to is set in the admin panel. Without a domain of the
// company's own, Resend sends only from onboarding@resend.dev and only to the address the Resend account was made with:
// make that account with the email that should get the alerts. MAIL_FROM (a variable) changes the sender once a domain
// is verified at Resend.
import { HttpError } from './util.js';

const DAILY = 60;   // at most this many alert emails a day

export const mailReady = (env) => !!env.RESEND_API_KEY;

export function cleanEmail(v) {
  const s = typeof v === 'string' ? v.trim().slice(0, 120) : '';
  if (!s) return '';
  if (!/^[^\s@<>"',;]+@[^\s@<>"',;]+\.[A-Za-z]{2,}$/.test(s)) throw new HttpError('bad-email');
  return s;
}

function base(env) {
  const t = env.TEST_FAKE_BASE;
  if (t && /^http:\/\/127\.0\.0\.1:\d+$/.test(t)) return t;       // tests only: a fake service on this machine
  return 'https://api.resend.com';
}

/* takes one email from today's budget, counted and written in one transaction */
async function takeBudget(env) {
  const now = Date.now(), tok = Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, '0')).join('');
  const r = await env.DB.batch([
    env.DB.prepare(`INSERT INTO attempts (kind, who, at, tok) SELECT 'mail', '-', ?1, ?2
      WHERE (SELECT COUNT(*) FROM attempts WHERE kind = 'mail' AND at > ?3) < ${DAILY}`).bind(now, tok, now - 86400e3),
    env.DB.prepare('SELECT 1 AS ok FROM attempts WHERE tok = ?').bind(tok),
  ]);
  return r[1].results.length > 0;
}

/* true when Resend accepted it; a fixed error code otherwise */
export async function sendMail(env, to, subject, body, key) {
  if (!mailReady(env)) throw new Error('mail-not-set');
  if (!(await takeBudget(env))) throw new Error('mail-budget');
  let r;
  try {
    r = await fetch(base(env) + '/emails', {
      method: 'POST', redirect: 'manual', signal: AbortSignal.timeout(8000),
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json', 'Idempotency-Key': key },
      body: JSON.stringify({ from: env.MAIL_FROM || 'JEC Website <onboarding@resend.dev>', to: [to], subject, text: body }),
    });
  } catch (e) { throw new Error(e && e.name === 'TimeoutError' ? 'mail-timeout' : 'mail-network'); }
  if (r.status >= 200 && r.status < 300) return true;
  throw new Error(r.status === 401 || r.status === 403 ? 'mail-key' : r.status === 422 ? 'mail-refused' : 'mail-' + r.status);
}
