# تنظيم كود الموقع (Source)

موقع ثابت بملف واحد `index.html` فيه HTML و CSS و JavaScript، بدون أي build.

## المكتبات الخارجية
- GSAP 3.12.5 و ScrollTrigger من cdnjs.
- خطوط Google Fonts.

## الأقسام بالترتيب
1. الواجهة (hero): فيديو `media/hero_1080.mp4` (والموبايل `hero_540.mp4`) مع صورة `hero_poster.webp`.
2. فيلم البناء: على الكمبيوتر مقاطع `v/a01a.mp4` … `v/a10.mp4`، وعلى الموبايل `tiles/m/`.
3. من نحن والأرقام (`#who`): الأرقام عدّ للبيانات الحقيقية (عدد المشاريع يُحسب من `PROJECTS`).
4. مراحل العمل (`#process`): `SKELETON` (تسع مراحل عظم) والتشطيبات الخارجية، مع صورة `renders/frame.webp`.
5. فيلم التشطيب الداخلي (`#fin`): `vi/i01.mp4` … `vi/i07b.mp4`، والموبايل `tiles/im/`.
6. ما خلف السقف (`#reveal`): `renders/p9.webp` و `renders/x10.webp` مع ملصقات الأنظمة (`TAGPOS`).
7. قبل وبعد: `renders/p1.webp` و `renders/p9.webp`.
8. أعمال التشطيب والترميم (`#trades`): `TRADES`، وصورتا الترميم `real/p04.webp` و `real/p03.webp`.
9. القطاعات (`#sectors`): `CATS` وصور `assets/sectors/` (توضيحية). الضغط على قطاع يعبّئه في الحاسبة.
10. المشاريع الحقيقية (`#projects`): `PROJECTS` (14) و `FILTERS`، وصور `real/`، ونافذة تفاصيل `#lb`.
11. الخدمات (`#services`): `SERVICES`.
12. حاسبة طلب التسعير (`#quote`): `CATS` و `SUBS` و `SCOPES` و `STARTS` و `DRAW`، ورسالة واتساب أو نسخ النص، مع الموافقة الإلزامية.
13. الخاتمة: فيديو النهار إلى الغروب `media/end_daydusk_1080.mp4`.
14. التذييل وسياسة الخصوصية والشروط (`#privacy`، `#terms`) من `LEGAL`.

## أهم الأجزاء في JavaScript
- `FILM`: أسماء المقاطع وعدد فريمات كل مقطع وحدود المراحل للكمبيوتر (`Ad`, `Id`) والموبايل (`Am`, `Im`). أي تغيير بالفيديو يجب أن ينعكس هنا.
- `VScrub` (الكمبيوتر): يحمّل كل مقطع كاملاً ويقفز للفريم المطلوب حسب التمرير. يحمّل المقطع الظاهر أولاً، ويعرض صورة ثابتة للمقطع حتى يصل. Shift+D يعرض توقيت القفز.
- `Scrub` (الموبايل): يرسم الفريمات من صور WebP (كل صورة فيها 4 فريمات 960×540) مع تلاشٍ بين الفريمات.
- اللغة: المتغير `lang` ومفتاح `jec-lang` في localStorage. كل نص له نسختان `data-lang="ar"` و `data-lang="en"`.
- الحركة المخففة: عند `prefers-reduced-motion` تظهر صور ثابتة بدل الحركة.

## Cloudflare
- `wrangler.jsonc`: اسم الـ Worker `jec-aljallad`، والملفات من `dist`.
- `npm run build` (الملف `tools/build-dist.mjs`) ينسخ `index.html` و `_headers` والمجلدات `v` و `vi` و `tiles` و `media` و `renders` و `real` إلى `dist`، ويرفض أي ملف أكبر من 25 ميجابايت. أي مجلد جديد للموقع يُضاف هنا وفي `tools/package-store.ps1`.
- `_headers`: رؤوس الأمان (CSP وغيرها) و `X-Robots-Tag: noindex` ما دام الموقع تجريبياً.
- `worker/index.js`: يمر عليه فقط `/media/*` ليرد على طلبات Range، لأن سفاري على الآيفون لا يشغّل الفيديو بدونها.
- `npm run dev` يشغّل نسخة Cloudflare المحلية على http://localhost:8787.

## التشغيل
- `START-DEMO.command` (ماك) أو `START-DEMO.cmd` (ويندوز)، أو `node server.cjs` ثم http://localhost:8080.

## قواعد المقاطع
- مقاطع `v/` و `vi/`: H.264، 1920×1080، 30 فريم/ثانية، GOP 6، بدون B-frames، CRF 20، كل ملف أقل من 20 ميجابايت.
- تتولّد من `Production/higgsfield` (انظر README هناك). لا تعدّلها يدوياً.
