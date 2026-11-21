# تنظيم كود الموقع (Source)

موقع ثابت بملف واحد `index.html` فيه HTML و CSS و JavaScript، بدون أي build.

## المكتبات الخارجية
- GSAP 3.12.5 و ScrollTrigger من cdnjs.
- خطوط Google Fonts.

## الأقسام بالترتيب
1. الواجهة (hero): فيديو `media/hero_1080.mp4` (والموبايل `hero_540.mp4`) مع صورة `hero_poster.webp`.
2. فيلم البناء: من الأرض الفاضية حتى اللوبي. على الكمبيوتر مقاطع `v/a01a.mp4` … `v/a10.mp4`، وعلى الموبايل `tiles/m/t001.webp` … `t088.webp`.
3. التشطيب الداخلي بتسع مراحل: `vi/i01.mp4` … `vi/i07b.mp4`، والموبايل `tiles/im/`.
4. «ما خلف السقف»: `renders/p9.webp` (الغرفة الواقعية) و `renders/x10.webp` (نموذج Blender للأنظمة) مع ملصقات الأنظمة (ثابت `TAGPOS`).
5. قبل وبعد: `renders/p1.webp` و `renders/p9.webp`.
6. المشاريع الحقيقية: ثابت `REAL` وصور `real/`. الأسماء والروابط كما نُشرت على @jallad.contracting.
7. النهاية: فيديو النهار إلى الغروب `media/end_daydusk_1080.mp4` وزر التواصل عبر رسائل إنستغرام.

## أهم الأجزاء في JavaScript
- `FILM`: أسماء المقاطع وعدد فريمات كل مقطع وحدود المراحل للكمبيوتر (`Ad`, `Id`) والموبايل (`Am`, `Im`). أي تغيير بالفيديو يجب أن ينعكس هنا.
- `VScrub` (الكمبيوتر): يحمّل كل مقطع كاملاً ويقفز للفريم المطلوب حسب التمرير. يحمّل المقطع الظاهر أولاً، ويعرض صورة ثابتة للمقطع حتى يصل. Shift+D يعرض توقيت القفز.
- `Scrub` (الموبايل): يرسم الفريمات من صور WebP (كل صورة فيها 4 فريمات 960×540) مع تلاشٍ بين الفريمات.
- اللغة: المتغير `lang` ومفتاح `jec-poc-lang` في localStorage. كل نص له نسختان `data-lang="ar"` و `data-lang="en"`.
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
