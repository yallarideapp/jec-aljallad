"""Browser tests for the request form and the admin panel, in a real Chromium (Playwright).

  live: python3 tests/browser_test.py live http://127.0.0.1:8788/      (wrangler dev on a fresh database, see run-browser-tests.sh)
  demo: python3 tests/browser_test.py demo http://127.0.0.1:8090/jec-aljallad/   (dist/ on a plain static server, like GitHub Pages)

Needs: pip install playwright && python3 -m playwright install chromium. Screenshots go to $SHOTS (default /tmp/jec-shots).
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

MODE, BASE = sys.argv[1], sys.argv[2]
SHOTS = os.environ.get("SHOTS", "/tmp/jec-shots"); os.makedirs(SHOTS, exist_ok=True)
PHOTO = os.path.join(SHOTS, "upload.jpg")
PASSED, FAILED, ERRORS = [], [], []


def check(name, cond, info=""):
    (PASSED if cond else FAILED).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else f"  -> {info}"))


def watch(page, who):
    page.on("pageerror", lambda e: ERRORS.append((who, str(e))))
    # the demo's api/health probe is a 404 on a static server; failed sign-ins are 401/403 on purpose
    page.on("console", lambda m: ERRORS.append((who, m.text)) if m.type == "error" and "status of 40" not in m.text and "Push API in incognito" not in m.text else None)


def make_photo():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (3000, 2000), (120, 90, 60)); d = ImageDraw.Draw(im)
    for i in range(0, 3000, 100): d.line([(i, 0), (i, 2000)], fill=(200, 180, 140), width=8)
    im.save(PHOTO, quality=95)


def fill_form(pg, name, phone):
    pg.evaluate("document.querySelector('#splash') && document.querySelector('#splash').remove()")
    pg.check("input[name=cat][value=private]", force=True)
    pg.check("input[name=scope][value=finishing]", force=True)
    pg.fill("#name", name); pg.fill("#phone", phone); pg.fill("#loc", "عمّان — خلدا")
    pg.check("#consent", force=True)


def main():
    make_photo()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chromium")
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, bypass_csp=True, service_workers="allow", permissions=["notifications"])
        pg = ctx.new_page(); watch(pg, "site")
        print("site form")
        pg.goto(BASE)
        pg.wait_for_function("document.querySelector('#sendBtn') && !document.querySelector('#sendBtn').hidden", timeout=20000)
        check("send-to-company button shown", True)
        check("preview note only in the demo", pg.is_visible("#demoSend") == (MODE == "demo"))
        pg.evaluate("document.querySelector('#splash') && document.querySelector('#splash').remove()")
        pg.click("#sendBtn")
        errs = pg.eval_on_selector_all("#quote .err", "els => els.filter(e => e.textContent).map(e => e.id)")
        check("empty form: sector, scope, name, phone, consent errors", set(errs) >= {"eCat", "eScope", "eName", "ePhone", "eConsent"}, errs)
        fill_form(pg, "سامي <b>اختبار</b>", "0791234567")
        pg.click("#sendBtn")
        pg.wait_for_function("/JEC-\\d{4}/.test(document.querySelector('#okMsg').textContent)", timeout=15000)
        ok = pg.text_content("#okMsg")
        check("request sent, number shown", "JEC-0001" in ok, ok)
        pg.click("#sendBtn"); time.sleep(.4)
        check("pressing again does not send a copy", "JEC-0001" in pg.text_content("#okMsg"), pg.text_content("#okMsg"))
        pg.locator("#quote .sum").screenshot(path=f"{SHOTS}/{MODE}_site_sent_1440.png")
        check("page not blank where the form is (desktop)", pg.evaluate("""(() => { const r = document.querySelector('#quote .sum').getBoundingClientRect(); return r.height > 300; })()"""))

        print("admin")
        ad = ctx.new_page(); watch(ad, "admin")
        ad.goto(BASE + "admin/")
        if MODE == "live":
            ad.wait_for_selector("#fSetup")
            ad.fill("#code", "wrong-code"); ad.fill("#pw", "a-very-long-pass"); ad.fill("#pw2", "a-very-long-pass"); ad.click("#fSetup [type=submit]")
            ad.wait_for_function("document.querySelector('#aErr').textContent.length > 0")
            check("wrong setup code shows an error", "رمز" in ad.text_content("#aErr"), ad.text_content("#aErr"))
            ad.fill("#code", "test-setup-code-123")
            ad.fill("#pw", "a-very-long-pass"); ad.fill("#pw2", "a-very-long-pass"); ad.click("#fSetup [type=submit]")
        ad.wait_for_selector(".req")
        if MODE == "demo":
            check("demo opens without any password screen", ad.locator("#fSetup, #fLogin, #pw").count() == 0)
        check("the site's request is in the inbox", "JEC-0001" in ad.text_content(".req"), ad.text_content(".req"))
        check("demo badge only in the demo", ad.is_visible("#demoPill") == (MODE == "demo"))
        ad.click(".req"); ad.wait_for_selector(".detail .statuses")
        check("name shown as text, not HTML", ad.text_content(".detail h2") == "سامي <b>اختبار</b>", ad.text_content(".detail h2"))
        check("WhatsApp reply uses 9627…", (ad.get_attribute(".detail a[href^='https://wa.me']", "href") or "").startswith("https://wa.me/962791234567?text="))
        ad.screenshot(path=f"{SHOTS}/{MODE}_admin_detail_1440.png")
        ad.click("[data-set-status=quoted]"); ad.wait_for_timeout(500)
        check("status changed", ad.get_attribute("[data-set-status=quoted]", "aria-pressed") == "true")

        print("gallery")
        ad.click("[data-tab=projects]"); ad.wait_for_selector(".proj")
        check("14 built-in projects listed", ad.locator(".proj").count() == 14)
        ad.click("[data-p=hide][data-i='0']")
        ad.click("[data-act=add-proj]"); ad.wait_for_selector("#fProj")
        ad.set_input_files("#phFile", PHOTO)
        ad.wait_for_function("document.querySelector('#phPrev img')", timeout=20000)
        ad.fill("#pAr", "مشروع جديد <i>x</i>"); ad.fill("#pUrl", "https://www.instagram.com/jallad.contracting/reel/ABC/")
        ad.click("#fProj [type=submit]"); ad.wait_for_selector("#savebar:not([hidden])")
        ad.wait_for_selector("#savebar:not([hidden]) .gold", state="visible"); ad.click("#savebar .gold"); ad.wait_for_selector("#savebar", state="hidden")
        pg.reload(); pg.wait_for_function("document.querySelector('.pcard .pcap b')")
        first = pg.eval_on_selector(".pcard .pcap b", "e => e.innerHTML")
        check("site shows the new project first, escaped", first == "مشروع جديد &lt;i&gt;x&lt;/i&gt;", first)
        check("hidden project left the site (14 - 1 + 1)", pg.text_content("#nProj") == "14", pg.text_content("#nProj"))

        print("settings")
        ad.click("[data-tab=settings]"); ad.wait_for_selector("#sWa")
        ad.fill("#sWa", "0790000000"); ad.locator("#sWa").blur()
        check("number turned into 9627…", ad.input_value("#sWa") == "962790000000", ad.input_value("#sWa"))
        ad.wait_for_selector("#savebar:not([hidden]) .gold", state="visible"); ad.click("#savebar .gold"); ad.wait_for_selector("#savebar", state="hidden")
        ad.click("[data-act=push-on]")
        ad.wait_for_selector("[data-act=push-test], .toast.bad", timeout=15000)
        if MODE == "demo":
            check("notifications on (demo)", ad.locator("[data-act=push-test]").count() == 1)
        pg.reload(); pg.wait_for_function("document.querySelector('#waBtn').href.includes('962790000000')", timeout=15000)
        check("site WhatsApp button uses the saved number", True)
        ad.uncheck("#sReqOn", force=True); ad.wait_for_selector("#savebar:not([hidden])"); ad.wait_for_selector("#savebar:not([hidden]) .gold", state="visible"); ad.click("#savebar .gold"); ad.wait_for_selector("#savebar", state="hidden")
        saved = json.loads(ad.evaluate("fetch('../api/admin/content', {credentials: 'same-origin'}).then(r => r.text())")) if MODE == "live" else None
        pg.reload(); pg.wait_for_timeout(2500)
        check("requests off: site hides the send button", pg.locator("#sendBtn").is_hidden(), saved and saved.get("requestsOn"))

        print("phone layout")
        ad.set_viewport_size({"width": 390, "height": 844}); ad.click("#langBtn")
        ad.click("[data-tab=requests]"); ad.wait_for_selector(".req"); ad.click(".req"); ad.wait_for_selector(".detail-wrap")
        ad.screenshot(path=f"{SHOTS}/{MODE}_admin_detail_390_en.png")
        check("English labels", "Call" in ad.text_content(".detail"))
        ad.click("[data-act=close-req]")
        for w in (390, 320):
            ad.set_viewport_size({"width": w, "height": 740})
            for tab in ("requests", "projects", "settings"):
                ad.click(f"[data-tab={tab}]"); ad.wait_for_timeout(600)
                check(f"admin {tab} fits {w}px", ad.evaluate("document.documentElement.scrollWidth <= innerWidth"))
        ad.screenshot(path=f"{SHOTS}/{MODE}_admin_settings_320.png", full_page=True)
        ad.click("#langBtn")
        if MODE == "live":
            ad.click("[data-tab=settings]"); ad.wait_for_selector("[data-act=logout]"); ad.click("[data-act=logout]"); ad.wait_for_selector("#fLogin")
            ad.fill("#pw", "wrong-password-x"); ad.click("#fLogin [type=submit]"); ad.wait_for_function("document.querySelector('#aErr').textContent")
            check("wrong password shows an error", "غير صحيحة" in ad.text_content("#aErr"), ad.text_content("#aErr"))
            ad.fill("#pw", "a-very-long-pass"); ad.click("#fLogin [type=submit]"); ad.wait_for_selector("#tabs:not([hidden])")
            check("sign in again", True)
        else:
            ad.click("[data-tab=settings]"); ad.wait_for_selector(".sets")
            check("demo settings: no password form, no sign-out", ad.locator("#fPw, [data-act=logout]").count() == 0)
            ad.reload(); ad.wait_for_selector("#tabs:not([hidden])")
            check("demo opens straight in after a reload", ad.locator("#fLogin, #fSetup").count() == 0)
        b.close()
    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    check("no script errors in either page", not ERRORS, ERRORS)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
