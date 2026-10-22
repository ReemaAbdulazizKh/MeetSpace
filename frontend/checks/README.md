# فحوص المتصفح

شغّلي الأوامر من `frontend/` مع تشغيل التطبيق المحلي. بقي مجلد العمل كما كان، ولذلك تشير المسارات `../docs/` إلى أدلة المشروع، وتُحفظ الصور المولدة في `frontend/test-results/` المستبعد من Git.

```powershell
node checks/check-foundation.mjs
node checks/check-calendar.mjs --read-only
node checks/check-calendar-states.mjs
```

هذه الأوامر لا تنشئ حجوزات. فحص الحالات يختبر أيضًا أخطاء HTTP مصطنعة في المتصفح دون قطع الخدمة الفعلية.

`check-chat.mjs` ينشئ حجز اختبار فعليًا. أما `check-calendar.mjs` دون `--read-only` فيغيّر الصيانة مؤقتًا ويلغي تجهيز الاختبار المحدد في التقرير. لا تشغّليهما تلقائيًا؛ يلزم تجهيز جديد مناسب ومراعاة حفظ الأدلة السابقة. `MEETSPACE_TEST_MILESTONE=m4` يختار تقارير M4 بدل M3.
