# MeetSpace — AI-Powered Room Booking Assistant

## 🌐 رابط التطبيق — Live Demo

### [افتحي MeetSpace](https://meetspace-fucc.onrender.com/)

**https://meetspace-fucc.onrender.com/**

مساعد حجز قاعات بالعربية والإنجليزية باستخدام React/Vite وFastAPI وQwen3.8 27B عبر Groq، مع حفظ الحجوزات في Firebase Firestore. يمكن تشغيل Ollama محليًا كخيار بديل.

يدعم استكمال الطلب، اقتراح القاعات، التأكيد الصريح، تقويم الموظف والإلغاء، وتقويم المسؤول والصيانة. يتحقق الخادم من السعة وتعارض القاعة وتداخل حجوزات الموظف نفسه قبل الحفظ. البيانات وهمية؛ اختيار الموظف والمسؤول تجريبي وليس مصادقة فردية.

## وثائق المشروع

- [BRD — متطلبات الأعمال](docs/MeetSpace_BRD.md)
- [SPEC — المواصفات التقنية](docs/MeetSpace_SPEC.md)
- [AGENTS.md — تعليمات وكيل التطوير](AGENTS.md)

الوثائق الأصلية تصف النطاق وقت إعدادها. التغييرات اللاحقة المعتمدة تشمل Groq والاستضافة ومنع تداخل حجوزات الموظف؛ الكود وإعدادات التشغيل أدناه تعكس النسخة الحالية.

## ملفات التشغيل

- `backend/`: API وقواعد الحجز والجلسات والوصول إلى Firestore.
- `backend/prompts/booking_agent.txt`: تعليمات النموذج الفعلية؛ يحتاجها التشات للتشغيل.
- `frontend/`: الواجهة وملفات بنائها.
- `scripts/build_render.py`: بناء المشروع للنشر.
- `.env.example`: أسماء متغيرات الإعداد دون أسرار.

## التشغيل المحلي

استخدمي Python 3.11 أو أحدث وNode22:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

أنشئي `.env` في الجذر. اضبطي `MODEL_PROVIDER=groq` و`GROQ_MODEL=qwen/qwen3.8-27b` و`GROQ_API_KEY` و`FIREBASE_PROJECT_ID` و`GOOGLE_APPLICATION_CREDENTIALS` بمسار ملف اعتماد Firebase الخاص. اتركي `APP_ENV` و`FRONTEND_ORIGIN` غير مضبوطين محليًا لاستخدام الإعدادات الافتراضية. لا ترفعي الأسرار إلى GitHub.

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

الدخول العام هو الافتراضي. يمكن تفعيل بوابة مشتركة بضبط `REQUIRE_DEMO_AUTH=true` و`DEMO_USERNAME` و`DEMO_PASSWORD` من16حرفًا على الأقل؛ ليست صلاحيات مستقلة لكل موظف. استخدمي عملية خادم واحدة، فمسودات المحادثة مؤقتة في الذاكرة؛ الحجوزات المحفوظة تبقى في Firestore. لا تُهيأ البيانات تلقائيًا عند التشغيل.
