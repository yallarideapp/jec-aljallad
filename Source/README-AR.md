# تنظيم كود الموقع (Source)

الصفحة ملف واحد `index.html` فيه HTML و CSS و JavaScript، بدون أي build. معها خادم صغير على Cloudflare (`worker/`) ولوحة تحكم (`admin/`).

## المكتبات الخارجية
- GSAP 3.12.5 و ScrollTrigger من cdnjs.
- خطوط Google Fonts.

## الأقسام بالترتيب
1. الواجهة (hero): فيديو `media/hero_1080.mp4` (والموبايل `hero_540.mp4`) مع صورة `hero_poster.webp`. تحت العنوان زرّان وشريط بالأعمال الأربعة (`.scope`).
2. أسماء المشاريع الحقيقية (`#clients`): تُؤخذ من `brand` في `PROJECTS`، ويختفي القسم إذا ما في أسماء.
3. من نحن وبطاقة الأرقام (`#who`): الأرقام تُحسب في `renderProjects()` من `PROJECTS` و `CATS` و `SKELETON` و `TRADES` و `SERVICES`؛ لا يُكتب رقم باليد.
4. الخدمات (`#services`): `SERVICES`، بطاقات بأيقونات (`ic`).
5. القطاعات (`#sectors`): `CATS` وصور `assets/sectors/` (توضيحية). الضغط على قطاع يعبّئه في الحاسبة.
6. المشاريع الحقيقية (`#projects`): القائمة الأساسية `PROJECTS` (14) في `shared/data.js`، وبعد حفظ المعرض من اللوحة تأتي القائمة من `/api/content`؛ `FILTERS`، وصور `real/` والصور المرفوعة `api/photo/...`، ونافذة تفاصيل `#lb`.
7. فيلم البناء: على الكمبيوتر مقاطع `v/a01a.mp4` … `v/a10.mp4`، وعلى الموبايل `tiles/m/`. فيه رابط «تخطَّ الفيلم» (`.skip`).
8. مراحل العمل (`#process`): `SKELETON` (تسع مراحل عظم) مرقّمة جنب الصورة، ثم التشطيبات الخارجية (`FIN`)، والصورة `renders/frame.webp`.
9. فيلم التشطيب الداخلي (`#fin`): `vi/i01.mp4` … `vi/i07b.mp4`، والموبايل `tiles/im/`. فيه رابط «تخطَّ الفيلم».
10. ما خلف السقف (`#reveal`): `renders/p9.webp` و `renders/x10.webp` مع ملصقات الأنظمة (`TAGPOS`).
11. قبل وبعد: `renders/p1.webp` و `renders/p9.webp`.
12. أعمال التشطيب والترميم (`#trades`): `TRADES`، وصورتا الترميم `real/p04.webp` و `real/p03.webp`.
13. طلب التسعير (`#quote`): ثلاث خطوات (`.next`) ثم الحاسبة. `CATS` و `SUBS` و `SCOPES` و `STARTS` و `DRAW` (من `shared/data.js`). «أرسل الطلب للشركة» (`#sendBtn`) يرسل لـ `/api/request`، أو رسالة واتساب أو نسخ النص، مع الموافقة الإلزامية. رقم واتساب وتشغيل الإرسال عبر الموقع من إعدادات اللوحة.
14. الخاتمة: فيديو النهار إلى الغروب `media/end_daydusk_1080.mp4`.
15. التذييل وسياسة الخصوصية والشروط (`#privacy`، `#terms`) من `LEGAL`.

## الشكل
- الألوان في `:root`: كحلي (`--ink`, `--char`, `--char-2`) وذهبي (`--gold`) من شعار الشركة، وأبيض (`--paper`) ورمادي فاتح (`--mist`) للأقسام الفاتحة. أنواع الأقسام: `.s` و `.s.alt` (كحلي)، `.s.lt` (أبيض)، `.s.mist` (رمادي فاتح).
- الخطوط: Alexandria للعناوين العربية، IBM Plex Sans Arabic للنص، Jost للإنجليزية.
- عنوان كل قسم داخل `.shead` وقبله شَرطة ذهبية مائلة؛ الصور والبطاقات الكحلية بزاوية مقصوصة (`.cut`).
- الأيقونات رموز SVG في أول `<body>`، وتُستدعى بالدالة `icon("الاسم")`.

## أهم الأجزاء في JavaScript
- `FILM`: أسماء المقاطع وعدد فريمات كل مقطع وحدود المراحل للكمبيوتر (`Ad`, `Id`) والموبايل (`Am`, `Im`). أي تغيير بالفيديو يجب أن ينعكس هنا.
- `VScrub` (الكمبيوتر): يحمّل كل مقطع كاملاً ويقفز للفريم المطلوب حسب التمرير. يحمّل المقطع الظاهر أولاً، ويعرض صورة ثابتة للمقطع حتى يصل. Shift+D يعرض توقيت القفز.
- `Scrub` (الموبايل): يرسم الفريمات من صور WebP (كل صورة فيها 4 فريمات 960×540) مع تلاشٍ بين الفريمات.
- اللغة: المتغير `lang` ومفتاح `jec-lang` في localStorage. كل نص له نسختان `data-lang="ar"` و `data-lang="en"`.
- الحركة المخففة: عند `prefers-reduced-motion` تظهر صور ثابتة بدل الحركة.

## Cloudflare
- `wrangler.jsonc`: اسم الـ Worker `jec-aljallad`، والملفات من `dist`.
- `npm run build` (الملف `tools/build-dist.mjs`) ينسخ `index.html` و `_headers` والمجلدات `v` و `vi` و `tiles` و `media` و `renders` و `real` و `assets` و `shared` و `admin` إلى `dist`، ويرفض أي ملف أكبر من 25 ميجابايت. أي مجلد جديد للموقع يُضاف هنا وفي `tools/package-store.ps1`.
- `_headers`: رؤوس الأمان (CSP وغيرها) و `X-Robots-Tag: noindex` ما دام الموقع تجريبياً.
- `worker/index.js`: يمر عليه `/api/*` (الخادم) و `/media/*` (يرد على طلبات Range، لأن سفاري على الآيفون لا يشغّل الفيديو بدونها).
- الخادم (`worker/`): `api.js` كل المسارات، `auth.js` كلمة سر اللوحة والجلسات، `requests.js` فحص الطلبات، `content.js` المعرض، `push.js` الإشعارات (VAPID)، `mail.js` الإيميل (Resend)، `schema.js` الجداول (تنعمل لحالها)، `util.js`. الربط: D1 باسم `DB` و KV باسم `PHOTOS`. الأسرار: `ADMIN_SETUP_CODE` و `RESEND_API_KEY` (في لوحة Cloudflare فقط).
- `shared/client.js`: الصفحة واللوحة بيكلّموا الخادم من خلاله؛ إذا ما في خادم (GitHub Pages أو `node server.cjs`) بيشتغل وضع عرض محفوظ بالمتصفح (`jec-demo-v1`).
- `admin/`: لوحة التحكم (تطبيق ويب يتثبّت على التلفون): `index.html`، `sw.js` (الإشعارات)، `manifest.webmanifest`، الأيقونات.
- الاختبارات: `bash tests/run-api-tests.sh` و `bash tests/run-browser-tests.sh`.
- `npm run dev` يشغّل نسخة Cloudflare المحلية على http://localhost:8787.

## التشغيل
- `START-DEMO.command` (ماك) أو `START-DEMO.cmd` (ويندوز)، أو `node server.cjs` ثم http://localhost:8080.

## قواعد المقاطع
- مقاطع `v/` و `vi/`: H.264، 1920×1080، 30 فريم/ثانية، GOP 6، بدون B-frames، CRF 20، كل ملف أقل من 20 ميجابايت.
- تتولّد من `Production/higgsfield` (انظر README هناك). لا تعدّلها يدوياً.
