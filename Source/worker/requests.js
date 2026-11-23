// Project requests sent from the estimator on the site.
// The page sends the choices as ids and numbers; the server checks each against the estimator's own lists
// (shared/data.js) and stores them with their Arabic and English names, so the admin reads the request as the visitor saw it.
import '../shared/data.js';
import { HttpError, line, text } from './util.js';

const J = globalThis.JEC;
export const STATUSES = ['new', 'contacted', 'quoted', 'won', 'closed'];

const int = (v, lo, hi) => (Number.isInteger(v) && v >= lo && v <= hi ? v : null);

export function cleanPhone(v) {
  const p = line(v, 30);
  if (!/^[+0-9 ()\-]+$/.test(p)) return '';
  const digits = p.replace(/\D/g, '');
  return digits.length >= 7 && digits.length <= 15 ? p : '';
}

export function cleanRequest(b) {
  const cat = J.CATS.find((c) => c.id === b.cat);
  if (!cat) throw new HttpError('bad-cat');
  const subs = J.SUBS[cat.id] || [];
  const sub = int(b.sub, 0, subs.length - 1) ?? 0;
  if (!Array.isArray(b.scope) || !b.scope.length || b.scope.length > J.SCOPES.length) throw new HttpError('bad-scope');
  const scopes = J.SCOPES.filter((s) => b.scope.includes(s.id));
  if (scopes.length !== new Set(b.scope).size) throw new HttpError('bad-scope');
  const finishing = scopes.some((s) => s.id === 'finishing');
  let trades = [];
  if (finishing) {
    if (!Array.isArray(b.trades) || b.trades.length > J.TRADES.length) throw new HttpError('bad-trades');
    trades = [...new Set(b.trades)].map((i) => int(i, 0, J.TRADES.length - 1));
    if (trades.includes(null)) throw new HttpError('bad-trades');
    trades.sort((x, y) => x - y);
  }
  const area = int(b.area, 20, 20000), floors = int(b.floors, 1, 30);
  if (area === null || floors === null) throw new HttpError('bad-area');
  const start = int(b.start, 0, J.STARTS.length - 1), draw = int(b.draw, 0, J.DRAW.length - 1);
  if (start === null || draw === null) throw new HttpError('bad-choice');
  const name = line(b.name, 80);
  if (name.length < 2) throw new HttpError('bad-name');
  const phone = cleanPhone(b.phone);
  if (!phone) throw new HttpError('bad-phone');
  return {
    cat: cat.id, catAr: cat.sAr, catEn: cat.sEn,
    sub, subAr: subs[sub] ? subs[sub][0] : '', subEn: subs[sub] ? subs[sub][1] : '',
    scope: scopes.map((s) => s.id), scopeAr: scopes.map((s) => s.ar), scopeEn: scopes.map((s) => s.en),
    trades, tradesAr: trades.map((i) => J.TRADES[i].ar), tradesEn: trades.map((i) => J.TRADES[i].en),
    area, floors, total: area * floors,
    loc: line(b.loc, 120),
    start, startAr: J.STARTS[start][0], startEn: J.STARTS[start][1],
    draw, drawAr: J.DRAW[draw][0], drawEn: J.DRAW[draw][1],
    notes: text(b.notes, 2000),
    lang: b.lang === 'en' ? 'en' : 'ar',
    name, phone,
  };
}

/* 5 an hour and 20 a day from one place; 120 an hour and 600 a day for the whole site */
export const REQUEST_LIMITS = { hour: 5, day: 20, allHour: 120, allDay: 600 };

/* after a refused save: which limit it was, for the message the visitor sees */
export async function requestLimited(env, w) {
  const now = Date.now(), h = now - 3600e3, d = now - 86400e3, L = REQUEST_LIMITS;
  const q = (sql, ...a) => env.DB.prepare(sql).bind(...a);
  const r = await env.DB.batch([
    q("SELECT COUNT(*) AS n FROM attempts WHERE kind = 'req' AND who = ? AND at > ?", w, h),
    q("SELECT COUNT(*) AS n FROM attempts WHERE kind = 'req' AND who = ? AND at > ?", w, d),
  ]);
  const n = r.map((x) => x.results[0].n);
  return n[0] >= L.hour || n[1] >= L.day ? 'too-many' : 'busy';
}

export function row(r) {
  let data = {};
  try { data = JSON.parse(r.data); } catch (e) {}
  return { id: r.id, no: r.no, created: r.created, updated: r.updated, status: r.status, name: r.name, phone: r.phone, note: r.note, data };
}
