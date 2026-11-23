"""Server tests: the request form, the admin panel's API, photos, email and phone alerts, and attempts to abuse them.

Run with tests/run-api-tests.sh (starts `wrangler dev` on a fresh local database with test-only settings).
Needs: Python 3.10+, `pip install cryptography`.

The fake services this script starts on 127.0.0.1:8799 stand in for Resend (email) and for a phone's push service.
The Worker talks to them only because the runner sets TEST_FAKE_BASE and TEST_PUSH_LOOPBACK, which a real deployment
never has.
"""
import base64, json, os, sys, threading, time, struct, http.server, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

BASE = os.environ.get("JEC_BASE", "http://127.0.0.1:8788")
FAKE = 8799
CODE = os.environ.get("JEC_SETUP_CODE", "test-setup-code-123")
PASSED, FAILED = [], []


def check(name, cond, info=""):
    (PASSED if cond else FAILED).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f"  -> {info}"))


def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def unb64u(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---------------- HTTP ----------------
def call(method, path, body=None, cookie=None, origin=BASE, ctype="application/json", raw=None, headers=None):
    h = dict(headers or {})
    data = None
    if raw is not None: data = raw
    elif body is not None: data = json.dumps(body).encode()
    if data is not None and ctype: h["Content-Type"] = ctype
    if origin: h["Origin"] = origin
    if cookie: h["Cookie"] = cookie
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            st, hd, tx = r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        st, hd, tx = e.code, e.headers, e.read()
    try: j = json.loads(tx)
    except Exception: j = None
    return st, j, hd, tx


def cookie_of(hd):
    sc = hd.get("Set-Cookie") or ""
    return sc.split(";")[0], sc


# ---------------- fake Resend + push service ----------------
GOT = []
class Fake(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        GOT.append({"path": self.path, "headers": dict(self.headers), "body": body, "at": time.time()})
        if self.path.startswith("/push/gone"): self.send_response(410); self.end_headers(); return
        if self.path == "/emails": self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"id":"fake"}'); return
        self.send_response(201); self.end_headers()
    def log_message(self, *a): pass


def wait_for(pred, secs=8):
    t = time.time()
    while time.time() - t < secs:
        hit = [g for g in GOT if pred(g)]
        if hit: return hit
        time.sleep(.1)
    return []


# ---------------- Web Push (RFC 8291 / RFC 8292) ----------------
def hkdf(salt, ikm, info, n):
    return HKDF(algorithm=hashes.SHA256(), length=n, salt=salt, info=info).derive(ikm)


def decrypt_push(body, ua_priv, auth):
    salt, rs, idlen = body[:16], struct.unpack(">I", body[16:20])[0], body[20]
    as_pub = body[21:21 + idlen]
    ct = body[21 + idlen:]
    ua_pub = ua_priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    peer = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub)
    secret = ua_priv.exchange(ec.ECDH(), peer)
    ikm = hkdf(auth, secret, b"WebPush: info\x00" + ua_pub + as_pub, 32)
    cek = hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    pt = AESGCM(cek).decrypt(nonce, ct, None)
    return pt[:pt.rindex(b"\x02")]


def verify_vapid(auth_header, aud):
    parts = dict(p.strip().split("=", 1) for p in auth_header[len("vapid "):].split(","))
    token, k = parts["t"], parts["k"]
    head, body, sig = token.split(".")
    claims = json.loads(unb64u(body))
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64u(k))
    raw = unb64u(sig)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    try:
        pub.verify(der, (head + "." + body).encode(), ec.ECDSA(hashes.SHA256())); ok = True
    except Exception: ok = False
    good_claims = claims.get("aud") == aud and time.time() < claims.get("exp", 0) <= time.time() + 24 * 3600 and str(claims.get("sub", "")).startswith(("mailto:", "https:"))
    return ok and good_claims, claims, k


def new_device():
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    return priv, auth, {"p256dh": b64u(pub), "auth": b64u(auth)}


def req_body(**kw):
    b = {"cat": "private", "sub": 0, "scope": ["skeleton", "finishing"], "trades": [0, 2, 4], "area": 300, "floors": 2,
         "loc": "Amman", "start": 1, "draw": 0, "name": "Test Person", "phone": "0791234567", "notes": "", "lang": "ar",
         "consent": True, "policy": "2026-11-23", "key": b64u(os.urandom(18))}
    b.update(kw); return b


def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", FAKE), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print("public")
    st, j, _, _ = call("GET", "/api/health"); check("health says live", st == 200 and j == {"ok": True, "live": True}, j)
    st, j, _, _ = call("GET", "/api/content"); check("no saved gallery yet: site uses its built-in list", j and j["projects"] is None and j["requestsOn"] is True, j)
    st, j, _, _ = call("POST", "/api/request", req_body(), origin="https://evil.example"); check("request from another site refused", st == 403 and j["error"] == "origin", (st, j))
    st, j, _, _ = call("POST", "/api/request", req_body(), ctype="text/plain"); check("not JSON refused", st in (400, 415) and not j["ok"], (st, j))
    st, j, _, _ = call("POST", "/api/request", raw=b'{"x":"' + b"a" * 40000 + b'"}'); check("oversized body refused", st == 413, (st, j))
    st, j, _, _ = call("POST", "/api/request", raw=b"{not json"); check("broken JSON refused", st == 400, (st, j))
    st, j, _, _ = call("POST", "/api/request", req_body(consent=False)); check("no consent refused", j["error"] == "consent-required", j)
    st, j, _, _ = call("POST", "/api/request", req_body(hp="http://spam")); check("honeypot filled refused", st == 400 and not j["ok"], j)
    for name, kw, code in [("bad sector", {"cat": "x"}, "bad-cat"), ("no scope", {"scope": []}, "bad-scope"), ("unknown scope", {"scope": ["x"]}, "bad-scope"),
                           ("bad trade", {"trades": [99]}, "bad-trades"), ("area too big", {"area": 999999}, "bad-area"), ("area not a number", {"area": "300"}, "bad-area"),
                           ("bad start", {"start": 9}, "bad-choice"), ("no name", {"name": " "}, "bad-name"), ("no phone", {"phone": ""}, "bad-phone"),
                           ("letters in phone", {"phone": "call me"}, "bad-phone"), ("bad key", {"key": "short"}, "bad-key")]:
        st, j, _, _ = call("POST", "/api/request", req_body(**kw)); check("refused: " + name, j and j.get("error") == code, (st, j))

    print("admin setup")
    st, j, _, _ = call("GET", "/api/admin/state"); check("no password yet, setup code present", j["hasPassword"] is False and j["setupReady"] is True and j["auth"] is False, j)
    st, j, _, _ = call("GET", "/api/admin/requests"); check("admin list without sign-in refused", st == 401, (st, j))
    st, j, _, _ = call("POST", "/api/admin/setup", {"code": "wrong", "password": "a-very-long-pass"}); check("wrong setup code refused", st == 403 and j["error"] == "bad-code", j)
    st, j, _, _ = call("POST", "/api/admin/setup", {"code": CODE, "password": "short"}); check("short password refused", j["error"] == "password-short", j)
    st, j, hd, _ = call("POST", "/api/admin/setup", {"code": CODE, "password": "first-password-1"})
    ck, raw = cookie_of(hd)
    check("setup sets a session cookie", st == 200 and ck.startswith("jec_admin="), (st, j, raw))
    check("cookie is HttpOnly, Secure, SameSite=Strict, Path=/api/admin", all(x in raw for x in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/api/admin")), raw)
    st, j, _, _ = call("POST", "/api/admin/setup", {"code": CODE, "password": "another-password"}); check("second setup refused", st == 409 and j["error"] == "already-set", j)
    st, j, _, _ = call("GET", "/api/admin/requests", cookie="jec_admin=" + "A" * 43); check("made-up cookie refused", st == 401, st)
    st, j, _, _ = call("POST", "/api/admin/logout", cookie=ck, origin="https://evil.example"); check("admin POST from another site refused", st == 403, st)

    print("push and email setup")
    st, j, _, _ = call("GET", "/api/admin/push/key", cookie=ck); check("VAPID public key", st == 200 and len(unb64u(j["key"])) == 65, j)
    dev_priv, dev_auth, keys = new_device()
    st, j, _, _ = call("POST", "/api/admin/push/subscribe", {"subscription": {"endpoint": "https://evil.example/push/1", "keys": keys}, "label": "x"}, cookie=ck)
    check("push address outside the known services refused", j["error"] == "bad-push-service", j)
    st, j, _, _ = call("POST", "/api/admin/push/subscribe", {"subscription": {"endpoint": f"http://127.0.0.1:{FAKE}/push/dev1", "keys": {"p256dh": "AAAA", "auth": keys["auth"]}}}, cookie=ck)
    check("bad device key refused", j["error"] == "bad-subscription", j)
    st, j, _, _ = call("POST", "/api/admin/push/subscribe", {"subscription": {"endpoint": f"http://127.0.0.1:{FAKE}/push/dev1", "keys": keys}, "label": "iPhone · app"}, cookie=ck)
    check("device registered", st == 200 and j["ok"], j)
    _, _, gk = new_device()
    call("POST", "/api/admin/push/subscribe", {"subscription": {"endpoint": f"http://127.0.0.1:{FAKE}/push/gone1", "keys": gk}, "label": "old phone"}, cookie=ck)
    st, j, _, _ = call("PUT", "/api/admin/settings", {"alertEmail": "not an email"}, cookie=ck); check("bad email refused", j["error"] == "bad-email", j)
    st, j, _, _ = call("PUT", "/api/admin/settings", {"alertEmail": "owner@example.com", "mailOn": True}, cookie=ck)
    check("email saved; key present", j["alertEmail"] == "owner@example.com" and j["mailReady"] is True and len(j["devices"]) == 2, j)

    print("test alerts")
    GOT.clear()
    st, j, _, _ = call("POST", "/api/admin/mail/test", cookie=ck); check("test email accepted", st == 200 and j["ok"], j)
    m = wait_for(lambda g: g["path"] == "/emails")
    if m:
        e = json.loads(m[0]["body"])
        check("test email: key, idempotency key, address", m[0]["headers"].get("Authorization") == "Bearer re_dummy_for_tests" and m[0]["headers"].get("Idempotency-Key", "").startswith("test-") and e["to"] == ["owner@example.com"], m[0]["headers"])
    else: check("test email reached the email service", False)
    st, j, _, _ = call("POST", "/api/admin/push/test", {}, cookie=ck)
    check("test push: one sent, the gone device dropped", j["sent"] == 1 and j["devices"] == 2, j)
    p = wait_for(lambda g: g["path"] == "/push/dev1")
    if p:
        h = p[0]["headers"]
        ok, claims, k = verify_vapid(h["Authorization"], f"http://127.0.0.1:{FAKE}")
        check("push signed with a valid VAPID token for this service", ok, claims)
        check("push headers (aes128gcm, TTL, urgency)", h.get("Content-Encoding") == "aes128gcm" and h.get("TTL") and h.get("Urgency") == "high", h)
        msg = json.loads(decrypt_push(p[0]["body"], dev_priv, dev_auth))
        check("push decrypts on the device", msg.get("title") == "تجربة إشعارات JEC", msg)
    else: check("push reached the push service", False)
    st, j, _, _ = call("GET", "/api/admin/settings", cookie=ck); check("410 Gone device removed", len(j["devices"]) == 1 and j["devices"][0]["label"] == "iPhone · app", j["devices"])
    _, _, wk = new_device()
    call("POST", "/api/admin/push/subscribe", {"subscription": {"endpoint": f"http://127.0.0.1:{FAKE}/push/win/AbC%3d%3d", "keys": wk}, "label": "Windows"}, cookie=ck)
    st, j, _, _ = call("GET", "/api/admin/settings", cookie=ck); win = [d for d in j["devices"] if d["label"] == "Windows"]
    st, j, _, _ = call("POST", "/api/admin/push/unsubscribe", {"id": win[0]["id"]}, cookie=ck)
    st, j, _, _ = call("GET", "/api/admin/settings", cookie=ck); check("device whose address ends in %3d can be removed", [d["label"] for d in j["devices"]] == ["iPhone · app"], j["devices"])
    extra = []
    for n in range(5):
        _, _, k5 = new_device()
        extra.append(call("POST", "/api/admin/push/subscribe", {"subscription": {"endpoint": f"http://127.0.0.1:{FAKE}/push/x{n}", "keys": k5}}, cookie=ck)[1])
    check("at most 5 devices", [e.get("error") for e in extra] == [None, None, None, None, "too-many-devices"], extra)
    for n in range(4): call("POST", "/api/admin/push/unsubscribe", {"endpoint": f"http://127.0.0.1:{FAKE}/push/x{n}"}, cookie=ck)

    print("requests")
    GOT.clear()
    body = req_body(name="<img src=x onerror=alert(1)>", notes="line1\nline2")
    st, j, _, _ = call("POST", "/api/request", body); check("request saved with a number", st == 200 and j["no"] == "JEC-0001", j)
    st, j2, _, _ = call("POST", "/api/request", body); check("same request sent again: same number, no copy", j2.get("again") is True and j2["no"] == "JEC-0001", j2)
    mails = wait_for(lambda g: g["path"] == "/emails"); pushes = wait_for(lambda g: g["path"] == "/push/dev1")
    check("one email for the request", len(mails) == 1 and "JEC-0001" in json.loads(mails[0]["body"])["subject"], [json.loads(x["body"])["subject"] for x in mails])
    if pushes:
        msg = json.loads(decrypt_push(pushes[0]["body"], dev_priv, dev_auth))
        check("one push for the request, opens it", len(pushes) == 1 and "JEC-0001" in msg["title"] and msg["url"].startswith("./#r="), msg)
    else: check("push for the request", False)
    key = b64u(os.urandom(18)); same = req_body(key=key)
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda _: call("POST", "/api/request", same)[1], range(8)))
    nos = {r.get("no") for r in res if r and r.get("ok")}
    check("8 copies sent at once make one request", len(nos) == 1, res)
    st, j, _, _ = call("GET", "/api/admin/requests", cookie=ck)
    check("list: 2 requests, newest first, counts", [i["no"] for i in j["items"]] == ["JEC-0002", "JEC-0001"] and j["counts"]["new"] == 2, j)
    first = j["items"][1]
    check("stored name kept as text", first["name"] == "<img src=x onerror=alert(1)>" and first["data"]["tradesAr"] and first["data"]["total"] == 600, first)
    check("consent time and policy version kept with the request", first["data"]["consent"]["policy"] == "2026-11-23" and first["data"]["consent"]["at"], first["data"].get("consent"))
    st, j, _, _ = call("GET", "/api/admin/requests?q=" + urllib.parse.quote("%_"), cookie=ck); check("search with % and _ is literal", j["items"] == [], j)
    st, j, _, _ = call("GET", "/api/admin/requests?q=JEC-0002", cookie=ck); check("search by number", [i["no"] for i in j["items"]] == ["JEC-0002"], j)
    st, j, _, _ = call("PATCH", f"/api/admin/requests/{first['id']}", {"status": "hacked"}, cookie=ck); check("unknown status refused", j["error"] == "bad-status", j)
    st, j, _, _ = call("PATCH", f"/api/admin/requests/{first['id']}", {"status": "quoted", "note": "called"}, cookie=ck); check("status and note saved", j["item"]["status"] == "quoted" and j["item"]["note"] == "called", j)
    st, j, _, _ = call("GET", "/api/admin/requests?status=quoted", cookie=ck); check("filter by status", [i["id"] for i in j["items"]] == [first["id"]] and j["counts"]["quoted"] == 1, j)
    st, j, _, _ = call("DELETE", f"/api/admin/requests/{first['id']}", cookie=ck); check("request deleted", j["ok"], j)
    st, j, _, _ = call("GET", f"/api/admin/requests/{first['id']}", cookie=ck); check("deleted request gone", st == 404, st)
    with ThreadPoolExecutor(12) as ex: res = list(ex.map(lambda _: call("POST", "/api/request", req_body()), range(12)))
    saved = [r[1]["no"] for r in res if r[0] == 200]; refused = [r[1]["error"] for r in res if r[0] == 429]
    check("12 requests at once from one address: only up to 5 an hour saved", len(saved) == 3 and refused == ["too-many"] * 9, (saved, refused))
    st, j, _, _ = call("GET", "/api/admin/requests", cookie=ck)
    nos = sorted(i["no"] for i in j["items"])
    check("numbers stay in sequence without gaps after refusals", nos == ["JEC-0002", "JEC-0003", "JEC-0004", "JEC-0005"], nos)

    print("gallery")
    st, j, _, _ = call("GET", "/api/admin/content", cookie=ck); check("admin gets the built-in list to start", j["seeded"] is True and len(j["projects"]) == 14 and j["version"] == 0, (j.get("seeded"), len(j.get("projects", []))))
    projects = j["projects"]
    def put(version, ps, **kw): return call("PUT", "/api/admin/content", {"version": version, "projects": ps, "whatsapp": kw.get("wa", ""), "requestsOn": kw.get("on", True)}, cookie=ck)
    for name, change, code in [("image outside the site", {"img": "https://evil.example/x.webp"}, "bad-image"), ("image path escape", {"img": "real/../x.webp"}, "bad-image"),
                               ("javascript: link", {"url": "javascript:alert(1)"}, "bad-url"), ("http link", {"url": "http://example.com"}, "bad-url"),
                               ("video outside the site", {"video": "https://evil.example/v.mp4"}, "bad-video"), ("unknown sector", {"cat": "x"}, "bad-cat"),
                               ("no title", {"ar": "", "en": ""}, "bad-title")]:
        ps = [dict(projects[0], **change)] + projects[1:]
        st, j, _, _ = put(0, ps); check("gallery refused: " + name, j.get("error") == code, j)
    st, j, _, _ = put(0, projects * 5); check("more than 60 projects refused", j["error"] == "bad-projects", j)
    st, j, _, _ = put(0, projects, wa="12"); check("bad WhatsApp number refused", j["error"] == "bad-whatsapp", j)
    ps = [dict(p) for p in projects]; ps[0]["hidden"] = True; ps[1]["ar"] = "<b>عنوان</b>"; ps[1]["tAr"] = ["a"] * 20
    st, j, _, _ = put(0, ps, wa="0790000000", on=True); check("gallery saved (version 1)", j["ok"] and j["version"] == 1 and j["whatsapp"] == "0790000000".replace("0", "0") and len(j["projects"][1]["tAr"]) == 8, j)
    st, j, _, _ = put(0, ps); check("save from an older copy refused (409)", st == 409 and j["error"] == "conflict", (st, j))
    st, j, _, _ = call("GET", "/api/content"); check("site gets the saved list without hidden projects", len(j["projects"]) == 13 and all(not p["hidden"] for p in j["projects"]) and j["version"] == 1, len(j["projects"]))

    print("photos")
    st, j, _, _ = call("POST", "/api/admin/photo", raw=b"<svg/>", ctype="image/svg+xml", cookie=ck); check("SVG refused", st == 415, (st, j))
    st, j, _, _ = call("POST", "/api/admin/photo", raw=b"GIF89a....", ctype="image/png", cookie=ck); check("not really a PNG refused", j["error"] == "bad-image", j)
    st, j, _, _ = call("POST", "/api/admin/photo", raw=b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * (2 * 1024 * 1024), ctype="image/webp", cookie=ck); check("photo over 1.5 MB refused", st == 413, (st, j))
    st, j, _, _ = call("POST", "/api/admin/photo", raw=b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 64, ctype="image/webp", cookie=ck)
    check("WebP stored", st == 200 and j["img"] == "api/photo/" + j["id"], j)
    pid = j["id"]
    st, _, hd, tx = call("GET", "/api/photo/" + pid); check("photo served with its type and long cache", st == 200 and hd.get("Content-Type") == "image/webp" and "immutable" in hd.get("Cache-Control", "") and hd.get("X-Content-Type-Options") == "nosniff", dict(hd))
    st, _, _, _ = call("GET", "/api/photo/" + "0" * 32); check("unknown photo 404", st == 404, st)
    st, _, _, _ = call("GET", "/api/photo/..%2Fsecret"); check("bad photo id 404", st == 404, st)
    st, j, _, _ = call("POST", "/api/admin/photo", raw=b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 64, ctype="image/webp"); check("photo upload without sign-in refused", st == 401, st)

    print("password and sessions")
    st, j, _, _ = call("POST", "/api/admin/password", {"current": "wrong-password", "next": "second-password-2"}, cookie=ck); check("change with wrong current refused", j["error"] == "bad-password", j)
    st, j, _, _ = call("POST", "/api/admin/password", {"current": "first-password-1", "next": "short"}, cookie=ck); check("short new password refused", j["error"] == "password-short", j)
    st, j, hd, _ = call("POST", "/api/admin/password", {"current": "first-password-1", "next": "second-password-2"}, cookie=ck)
    ck2, _ = cookie_of(hd); check("password changed, new session", st == 200 and ck2 and ck2 != ck, (st, j))
    st, _, _, _ = call("GET", "/api/admin/requests", cookie=ck); check("old session signed out after the change", st == 401, st)
    st, _, _, _ = call("GET", "/api/admin/requests", cookie=ck2); check("new session works", st == 200, st)
    st, j, hd, _ = call("POST", "/api/admin/logout", cookie=ck2); check("sign out clears the cookie", "Max-Age=0" in (hd.get("Set-Cookie") or ""), hd.get("Set-Cookie"))
    st, _, _, _ = call("GET", "/api/admin/requests", cookie=ck2); check("session gone after sign out", st == 401, st)
    st, j, hd, _ = call("POST", "/api/admin/reset", {"code": CODE, "password": "third-password-3"}); ck3, _ = cookie_of(hd)
    check("forgotten password reset with the setup code", st == 200 and ck3, j)
    st, j, hd, _ = call("POST", "/api/admin/login", {"password": "third-password-3"}); check("sign in with the new password", st == 200, j)

    print("lockout")
    with ThreadPoolExecutor(30) as ex: codes = list(ex.map(lambda i: call("POST", "/api/admin/login", {"password": f"wrong-{i}-xxxxxx"})[1]["error"], range(30)))
    check("30 wrong passwords at once: at most 7 checked, the rest locked", codes.count("bad-password") <= 7 and codes.count("locked") >= 23, (codes.count("bad-password"), codes.count("locked")))
    st, j, _, _ = call("POST", "/api/admin/login", {"password": "third-password-3"}); check("even the right password waits while locked", j["error"] == "locked", j)
    st, j, hd, _ = call("POST", "/api/admin/reset", {"code": CODE, "password": "fourth-password-4"})
    check("the owner can still reset with the setup code while sign-in is locked", st == 200 and cookie_of(hd)[0], (st, j))
    with ThreadPoolExecutor(20) as ex: codes = list(ex.map(lambda i: call("POST", "/api/admin/reset", {"code": f"guess-{i}", "password": "fifth-password-5"})[1]["error"], range(20)))
    check("20 setup-code guesses at once: at most 8 checked", codes.count("bad-code") <= 8 and codes.count("locked") >= 12, (codes.count("bad-code"), codes.count("locked")))

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED: print("FAILED:", *FAILED, sep="\n  ")
    srv.shutdown()
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    import urllib.parse
    main()
