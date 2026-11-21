# JEC | AlJallad Contracting — أين يوجد كل شيء

## GitHub و Cloudflare
- الكود على GitHub في المستودع العام `yallarideapp/jec-aljallad`، وهذا المجلد نسخة منه. Cloudflare يبني المجلد `Source` وينشره مع كل push. الخطوات في `Cloudflare-guide.md`.
- الملفات الكبيرة (Blender، الخامات، الريندرات، مقاطع الفيديو الأصلية، الأرشيف) تبقى في هذا المجلد على الماك فقط.

## الظاهر في المجلد
- `JEC-AlJallad-complete-with-demo/` مجلد التسليم: ملف المصدر، نسخة العرض، الوثائق، ودليل Cloudflare.
- `JEC-AlJallad-complete-with-demo.zip` نفس مجلد التسليم مضغوطاً، للإرسال.

## الداخلي (مخفي بعد تشغيل سكربت التغليف، وما زال موجوداً)
- `Source/` كود الموقع. التعديل هنا فقط.
- `Demo/` نسخة العرض، تتولّد من `Source`.
- `Documents/` المصادر، أصل الصور، الصور الأصلية، صفحات المراجعة، والأرشيف.
- `Production/` ملفات Blender و Higgsfield، لا تدخل أي ZIP.
- `AGENTS.md` قواعد لأي وكيل برمجي يعمل على المشروع (يقرؤه تلقائياً).
- `JEC-ALJALLAD-CONTEXT.md` السياق والحالة وسجل التعديلات.
- `Cloudflare-guide.md` دليل ربط GitHub و Cloudflare والنطاق.
- `UPDATE-PACKAGE.command` / `.cmd` يعيد توليد Demo والـ ZIPs ومجلد التسليم.
- `START-DEMO.command` / `.cmd` يفتح نسخة العرض.

لرؤية الملفات المخفية على الماك: في Finder اضغط Cmd + Shift + نقطة.
