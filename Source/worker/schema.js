// The database's tables. The Worker creates them itself the first time it runs (every statement is "if not exists"),
// so a new Cloudflare account needs no migration command. To change a table later, add the statement at the end.

const STATEMENTS = [
  `CREATE TABLE IF NOT EXISTS requests (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     no TEXT NOT NULL UNIQUE,
     idem TEXT UNIQUE,
     created TEXT NOT NULL,
     updated TEXT NOT NULL,
     status TEXT NOT NULL DEFAULT 'new',
     name TEXT NOT NULL,
     phone TEXT NOT NULL,
     data TEXT NOT NULL,
     note TEXT NOT NULL DEFAULT ''
   )`,
  `CREATE INDEX IF NOT EXISTS requests_status ON requests(status, id)`,
  `CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL)`,
  `INSERT OR IGNORE INTO counters (name, value) VALUES ('request', 0)`,
  `CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY CHECK (id = 1), json TEXT NOT NULL, version INTEGER NOT NULL, updated TEXT NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY CHECK (id = 1), hash TEXT NOT NULL, salt TEXT NOT NULL, rounds INTEGER NOT NULL, gen INTEGER NOT NULL, updated TEXT NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, gen INTEGER NOT NULL, expires INTEGER NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS attempts (kind TEXT NOT NULL, who TEXT NOT NULL, at INTEGER NOT NULL, tok TEXT)`,
  `CREATE INDEX IF NOT EXISTS attempts_kind ON attempts(kind, who, at)`,
  `CREATE INDEX IF NOT EXISTS attempts_at ON attempts(at)`,
  `CREATE INDEX IF NOT EXISTS attempts_tok ON attempts(tok)`,
  `CREATE TABLE IF NOT EXISTS private (k TEXT PRIMARY KEY, v TEXT NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS push_subs (endpoint TEXT PRIMARY KEY, p256dh TEXT NOT NULL, auth TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', created TEXT NOT NULL, last_ok TEXT, last_err TEXT)`,
  `CREATE TABLE IF NOT EXISTS photos (id TEXT PRIMARY KEY, type TEXT NOT NULL, bytes INTEGER NOT NULL, created TEXT NOT NULL)`,
];

let ready = null;

/* once per running copy of the Worker */
export function schema(env) {
  if (!ready) ready = env.DB.batch(STATEMENTS.map((s) => env.DB.prepare(s))).catch((e) => { ready = null; throw e; });
  return ready;
}

/* a private value (salts, keys, settings): never sent to a page as it is */
export async function getPrivate(env, k) {
  const r = await env.DB.prepare('SELECT v FROM private WHERE k = ?').bind(k).first();
  return r ? r.v : null;
}
/* set it only if it is not there yet, and return the value that stands (two copies of the Worker may race) */
export async function initPrivate(env, k, v) {
  await env.DB.prepare('INSERT OR IGNORE INTO private (k, v) VALUES (?, ?)').bind(k, v).run();
  return getPrivate(env, k);
}
export async function setPrivate(env, k, v) {
  await env.DB.prepare('INSERT INTO private (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v').bind(k, v).run();
}
