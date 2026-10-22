# MeetSpace — إعداد Render لخدمة واحدة

حالة 22 أكتوبر 2026: الكود مجهز واختُبر محليًا بوضع الاستضافة؛ **لم يُنشر على Render ولم يُرفع إلى GitHub من هذه الجلسة**. طلب المالكة الاستضافة واستخدام Groq هو الإذن اللاحق الذي يغيّر قيد التشغيل المحلي السابق. ملفات العرض وحزمة الأدلة السابقة لقطات تاريخية ولم تُحدّث لتدّعي وجود نشر ناجح.

## الخدمة

Create → Web Service → مستودع `https://github.com/ReemaAbdulazizKh/MeetSpace.git`.

| الحقل | القيمة |
|---|---|
| Branch | main |
| Language / Runtime | Python 3 |
| Root Directory | فارغ — جذر المستودع |
| Build Command | `python scripts/build_render.py` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/healthz` |

سكريبت البناء يثبت requirements ثم ينفذ npm ci وnpm run build داخل frontend. Node22 محدد في `.node-version`؛ يجب توفر npm في بيئة البناء. لا يُشغّل seed أو أي أداة فحص تغيّر البيانات. ملفات frontend/dist ناتج بناء وليست مطلوبة في Git. FastAPI يقدم هذا المجلد فقط؛ `/api` تبقى للخادم. لا Static Site ثانية ولا VITE_API_URL مطلوبة.

## Environment

| Key | Value |
|---|---|
| APP_ENV | production |
| MODEL_PROVIDER | groq |
| GROQ_MODEL | qwen/qwen3.8-27b |
| GROQ_API_KEY | المفتاح الخاص — داخل Render فقط |
| FIREBASE_PROJECT_ID | smart-room-booking-agent |
| GOOGLE_APPLICATION_CREDENTIALS | /etc/secrets/firebase-service-account.json |
| DEMO_USERNAME | اسم دخول تختاره المالكة، مثل reviewer |
| DEMO_PASSWORD | كلمة مرور خاصة من16حرفًا على الأقل؛ لا تستخدم المثال ككلمة مرور |

اتركي FRONTEND_ORIGIN **غير معرف** في Render كي يؤخذ عنوان الخدمة من RENDER_EXTERNAL_URL الذي توفره Render. إن كان مضبوطًا على localhost فاحذفيه من إعدادات Render. عند استخدام نطاق خاص يُضبط FRONTEND_ORIGIN على أصل HTTPS الفعلي بلا مسار أو شرطة أخيرة. لا تنسخي ملف .env المحلي إلى GitHub.

Secret Files: الاسم `firebase-service-account.json`، والمحتوى ملف اعتماد Firebase الخاص. المفتاح الذي ظهر في المحادثة ينبغي استبداله من صفحة مفاتيح حساب الخدمة، وتحديث النسختين المحلية وRender دون عرض المحتوى. لا يُرفع ملف الاعتماد إلى المستودع.

## حماية التجربة وحدودها

الرابط يقدم نافذة دخول Basic Auth من المتصفح بكلمة المرور التي تختارها المالكة. الحماية تشمل الواجهة وAPI وSwagger والملفات الثابتة، بينما /healthz يعرض حالة حياة بسيطة فقط، دون Firestore أو نموذج أو أسرار. طلبات الكتابة يجب أن تتضمن Origin مطابقًا للأصل المعتمد. Render يوفر HTTPS؛ لا تشاركي كلمة المرور إلا مع المقيّم المقصود.

هذه بوابة مشتركة للتجربة، **ليست مصادقة لكل موظف أو فصل صلاحيات مسؤول آمنًا بين مستخدمين موثوقين**. من يملك بيانات الدخول يستطيع تبديل أدوار العرض التجريبية. لا بيانات حقيقية أو نشر استخدام مؤسسي. جلسات المحادثة مؤقتة في ذاكرة عملية واحدة؛ لا تضيفي workers أو توسعًا لعدة نسخ. إعادة التشغيل تفقد المسودة والعرض المعلق، لكن الحجوزات المحفوظة تبقى في Firestore. حدود Groq قد تنتج429؛ لم يُلغ هذا القيد.

## التحقق المنفذ وحدود الدليل

-43 اختبارًا معزولًا ناجحًا بعد تعديل مصدر الرد وفق المزود الحالي، تشمل الدخول الخاطئ/المفقود، حماية المسارات، Origin مفقود/أجنبي وطلب صالح.
- اختبار تطبيق FastAPI الحقيقي محليًا بوضع production مع ناتج React: الصفحة401 دون دخول، الصفحة200 وHTML فعلي مع دخول، API المسؤول401 دون دخول، مسار ملف اعتماد404، تعديل من موقع أجنبي403، healthz200.
- تأكدنا أن .env وملف خدمة Firebase الحالي مستبعدان من Git وغير متتبعين؛ نمط عام يستبعد ملفات Firebase الجديدة كذلك. حزمة المصادر ZIP والمجلد المنسوخ مستبعدان لتجنب رفع أرشيفات غير لازمة.
- لا إنشاء/إلغاء حجز أو تغيير صيانة أو بيانات Firestore أثناء هذا التجهيز. لا اختبار تشغيل على Render نفسه حتى ترفع المالكة الكود وتنفذ Deploy؛ لا ادعاء نجاح بيئة البناء البعيدة أو رابط عام الآن.

## ما بعد رفع الكود

1. ارفعي ملفات التطبيق وscripts/build_render.py وملفات الاعتماد البرمجية المعتادة و.node-version؛ استبعدي .env وJSON الاعتماد وnode_modules/.venv والأرشيفات.
2. ضعي القيم أعلاه ثم Deploy؛ عند النجاح افتحي رابط onrender.com وأدخلي اسم وكلمة مرور التجربة.
3. تأكدي من /healthz، ثم من داخل الواجهة افحصي الاتصال بـGroq وFirestore. مجرد Live لا يثبت نجاح النموذج والحفظ.
4. سجلي رابط الوصول ونتائج المقيّم الحقيقية في قائمة الأدلة لاحقًا، لا تغيّري حالة Missing إلى Fulfilled قبل الدليل. أي اختبار حجز جديد يبقى معلنًا ببيانات وهمية ولا يحذف سجلات سابقة.

مراجع: [Render FastAPI](https://render.com/docs/deploy-fastapi)، [Native runtimes](https://render.com/docs/native-runtimes)، [الأسرار](https://render.com/docs/configure-environment-variables)، [Starlette StaticFiles](https://www.starlette.io/staticfiles/). اعتماد الخدمة ونشرها الخارجي ليسا منفذين في هذا التغيير.
