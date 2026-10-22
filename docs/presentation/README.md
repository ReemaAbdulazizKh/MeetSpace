# مصدر عرض MeetSpace الختامي

هذه أدوات توثيق فقط؛ لا تستدعي Firestore ولا تغير التطبيق أو متطلبات تشغيله.

1. `prepare_content.py`: النص المعتمد والمحتوى والجداول بالأرقام الفعلية؛ يولد `deck_content.json`.
2. `build_presentation.ps1`: ينشئ شرائح PowerPoint أصلية قابلة للتحرير (نصوص وأشكال وجداول ورسم أعمدة) مع صور التطبيق؛ يصدر PDF وصور جميع الشرائح وفحص حدود النص. يحتاج PowerPoint المحلي وWindows COM، ويستخدم نافذة مخفية ولا يغلق جلسة PowerPoint سابقة للمستخدمة.
3. `inspect_output.py`: يتحقق من أعداد الصفحات والنصوص القابلة للتحرير والأرقام، وينشئ صورًا مجمعة للمراجعة من PDF. يستخدم PyMuPDF وPillow المثبتين مؤقتًا في `%TEMP%/meetspace-capstone-tools`، دون إضافتهما لاعتمادات التطبيق.

إعادة توليد مخرجات التوثيق من جذر المشروع:

```powershell
.venv\Scripts\python.exe docs/presentation/prepare_content.py
& docs/presentation/build_presentation.ps1
.venv\Scripts\python.exe docs/presentation/inspect_output.py
```

الصور الأصلية وبيان التقاطها في `docs/evidence/capstone/`. لا تعيد أدوات التوليد التقاط الصور أو تشغيل النموذج أو إنشاء حجوزات. القيم غير المقاسة تبقى غير متاحة؛ لا تخمين لوقت نشط أو أخطاء أو تكرار شهري.

توزيع العرض: 23 شريحة رئيسية و4 ملاحق. لا معلومات أساسية محصورة في Speaker Notes. محتوى اللوحة وقائمة الأدلة يكمل المطابقة الصارمة ويعرض النواقص؛ لا شهادة باجتياز جميع المتطلبات الرسمية.
