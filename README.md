# MeetSpace — AI-Powered Room Booking Assistant

## 🌐 رابط التطبيق — Live Demo

### [افتحي MeetSpace](https://meetspace-fucc.onrender.com/)

**https://meetspace-fucc.onrender.com/**

## 📦 تحميل أكواد المشروع

[تحميل MeetSpace_Project_Code.zip](MeetSpace_Project_Code.zip?raw=true)

نسخة ZIP من أكواد المشروع وملفات التشغيل والوثائق، دون مفاتيح أو ملفات اعتماد. تبقى الأكواد الأصلية في المستودع لتشغيل Render.

**ملف العرض:** [MeetSpace — Final Presentation (PDF)](MeetSpace_SDAIA_Final_Updated_EN.pdf)

## عن المشروع

**إعداد: Reema Abdulaziz Alkharaan**  
**البرنامج: دورة رفع الإنتاجية بالذكاء الاصطناعي — أكاديمية سدايا**

مساعد حجز قاعات بالعربية والإنجليزية باستخدام React/Vite وFastAPI وQwen3.8 27B عبر Groq، مع حفظ الحجوزات في Firebase Firestore. يمكن تشغيل Ollama محليًا كخيار بديل.

يدعم استكمال الطلب، اقتراح القاعات، التأكيد الصريح، تقويم الموظف والإلغاء، وتقويم المسؤول والصيانة. يتحقق الخادم من السعة وتعارض القاعة وتداخل حجوزات الموظف نفسه قبل الحفظ. البيانات وهمية؛ اختيار الموظف والمسؤول تجريبي وليس مصادقة فردية.

## استخدام التطبيق

1. افتحي رابط التطبيق واختاري تجربة الموظف وهوية تجريبية.
2. اكتبي طلبك: نوع القاعة، التاريخ، وقت البداية والنهاية، وعدد الحضور. يسأل المساعد عن المعلومات الناقصة.
3. اختاري قاعة وراجعي العرض؛ الاختيار وحده لا يحجز القاعة. أكّدي الحجز صراحةً لحفظه.
4. راجعي الحجز أو ألغيه من تقويم حجوزاتي. تجربة المسؤول تعرض تقويم الحجوزات وحالة القاعات والصيانة.

الحجوزات بتوقيت الرياض. الحجز منفرد وفي اليوم نفسه، ولا يُسمح بتداخل حجوزات القاعة أو حجوزات الموظف نفسه. تغيير القاعة إلى الصيانة يمنع الحجوزات الجديدة دون إلغاء الحجوزات السابقة.

## التقنيات

| الجزء | التقنية |
|---|---|
| الواجهة | React + Vite |
| الخادم والتحقق | Python + FastAPI |
| النموذج في النسخة المستضافة | Qwen3.8 27B عبر Groq |
| قاعدة البيانات | Firebase Firestore عبر Python Admin SDK |
| الاستضافة | Render — الواجهة وAPI على خدمة واحدة |

## وثائق المشروع

- [BRD — متطلبات الأعمال](MeetSpace_BRD.md)
- [SPEC — المواصفات التقنية](MeetSpace_SPEC.md)
- [AGENTS.md — تعليمات وكيل التطوير](AGENTS.md)

الوثائق الأصلية تصف النطاق وقت إعدادها. التغييرات اللاحقة المعتمدة تشمل Groq والاستضافة ومنع تداخل حجوزات الموظف؛ الكود وإعدادات التشغيل أدناه تعكس النسخة الحالية.

## ملفات التشغيل

- `backend/`: API وقواعد الحجز والجلسات والوصول إلى Firestore.
- `backend/prompts/booking_agent.txt`: تعليمات النموذج الفعلية؛ يحتاجها التشات للتشغيل.
- `frontend/`: الواجهة وملفات بنائها.
- `scripts/build_render.py`: بناء المشروع للنشر.
- `.env.example`: أسماء متغيرات الإعداد دون أسرار.
- `.node-version`: يحدد Node22 لبناء الواجهة على Render.

BRD وSPEC وAGENTS.md وREADME موجودة في جذر المستودع. ملفات القياس والأدلة والأرشيف وأدوات التطوير ليست ضمن حزمة أكواد التشغيل الحالية.

## التشغيل المحلي

استخدمي Python 3.11 أو أحدث وNode22:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

أنشئي `.env` في الجذر بالاستعانة بـ`.env.example`، ثم أكملي الإعدادات الخاصة:

| المتغير | الإعداد المحلي |
|---|---|
| `MODEL_PROVIDER` | `groq` |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` |
| `GROQ_API_KEY` | مفتاحك الخاص من Groq |
| `FIREBASE_PROJECT_ID` | معرّف مشروع Firebase الخاص بك |
| `GOOGLE_APPLICATION_CREDENTIALS` | المسار المطلق لملف اعتماد Firebase الخاص بك |

اتركي `APP_ENV` و`FRONTEND_ORIGIN` غير مضبوطين محليًا لاستخدام الإعدادات الافتراضية. الأسرار غير مرفقة في ZIP ويجب إعدادها على جهاز التشغيل؛ لا ترفعيها إلى GitHub.

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

وفي طرفية ثانية:

```powershell
npm --prefix frontend run dev
```

افتحي عنوان Vite الظاهر في الطرفية. لتشغيل النموذج محليًا بدل Groq استخدمي `MODEL_PROVIDER=ollama` مع Ollama ونموذج `qwen2:7b` المثبت.

## النشر على Render

خدمة Python3 واحدة؛ Root Directory فارغ:

| الحقل | القيمة |
|---|---|
| Build Command | `python scripts/build_render.py` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/healthz` |

متغيرات البيئة: `APP_ENV=production`، `MODEL_PROVIDER=groq`، `GROQ_MODEL=qwen/qwen3.8-27b`، `GROQ_API_KEY`، `FIREBASE_PROJECT_ID=smart-room-booking-agent`، و`GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/firebase-service-account.json`.

أضيفي ملف الاعتماد في Secret Files باسم `firebase-service-account.json`. اتركي `FRONTEND_ORIGIN` غير معرف ليستخدم عنوان Render التلقائي. لا ترفعي `.env` أو ملف الاعتماد إلى المستودع.

الدخول العام هو الافتراضي. يمكن تفعيل بوابة مشتركة بضبط `REQUIRE_DEMO_AUTH=true` و`DEMO_USERNAME` و`DEMO_PASSWORD` من 16 حرفًا على الأقل؛ ليست صلاحيات مستقلة لكل موظف. استخدمي عملية خادم واحدة، فمسودات المحادثة مؤقتة في الذاكرة؛ الحجوزات المحفوظة تبقى في Firestore. لا تُهيأ البيانات تلقائيًا عند التشغيل.

## ملاحظات التشغيل

- يحتاج Firestore وGroq اتصالًا بالإنترنت، حتى عند تشغيل الواجهة محليًا.
- قد تتأخر أول زيارة عند استيقاظ خدمة Render المجانية. Groq له حدود استخدام وقد يرفض طلبات مؤقتًا.
- `/healthz` يفحص حياة الخادم فقط؛ فحص الاتصال داخل التطبيق يراجع النموذج وFirestore.
- النسخة تعليمية ببيانات وهمية، ولا توفر مصادقة مستقلة أو صلاحيات مؤسسية بين الموظفين والمسؤول.
