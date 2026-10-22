# دليل وثائق MeetSpace

| المطلوب | الملفات |
|---|---|
| نطاق المنتج والقرارات المعتمدة | [BRD](MeetSpace_BRD.md)، [SPEC](MeetSpace_SPEC.md) |
| تقارير التنفيذ | [M1](Milestone_1.md)، [M2](Milestone_2.md)، [M3](Milestone_3.md)، [M4](Milestone_4.md) |
| القياسات البشرية | [النتائج](Productivity_Results.md)، [البروتوكول](Productivity_Measurement_Protocol.md)، [CSV](m4/productivity_results.csv) |
| تحسينات الأوامر والأداء | [سجل التحسين](Prompt_Engineering_Log.md) |
| الأدلة الخام للاختبارات | [evidence](evidence/README.md) |
| نسخ الأوامر والكود السابقة | [archive](archive/README.md) |
| التسليم الختامي ومطابقة سدايا | [لوحة المشروع](Final_Capstone_Board.md)، [قائمة الأدلة](../MeetSpace_Evidence_Checklist.md)، [PowerPoint](../MeetSpace_Final_Presentation.pptx)، [PDF](../MeetSpace_Final_Presentation.pdf) |
| مصدر العرض وفحص إخراجه | [presentation](presentation/)، [أدلة التسليم](evidence/capstone/) |

تقارير المراحل تاريخية؛ تاريخها يحدد الحالة التي تصفها. نتائج قياسات الإنتاجية البشرية منفصلة عن مقاييس استدلال النموذج والاختبارات الآلية.

تنظيم الملفات: اختبارات Python انتقلت من `backend/test_*` إلى `backend/tests/`، وأدوات الفحص إلى `backend/checks/`، وفحوص المتصفح إلى `frontend/checks/`. نُقلت ملفات JSON من جذر docs ومجلد m4 إلى `evidence/m1` حتى `evidence/m4`. بقي ملف قياسات المستخدم `m4/productivity_results.csv` في مكانه. لم يُغيّر منطق التطبيق أو محتوى الأدلة الخام أو قياسات CSV بهذا التنظيم.

التحقق بعد التنظيم: نجح 37 اختبارًا معزولًا، واستيراد أدوات الفحص العشر دون تشغيل تجاربها، وبناء الواجهة، وفحص التنقل والنمط واللغة والأحجام من Chrome. قُرئت ملفات الأدلة JSON الـ39 بنجاح، وطابقت أربع نسخ prompt مؤرشفة بصمات التجارب الأصلية، وبقيت القياسات البشرية الستة كما هي، ولم تظهر روابط محلية مكسورة في الأدلة المحدّثة. لم تُشغّل اختبارات إنشاء الحجوزات أو تهيئة البيانات أثناء التنظيم.

قد يبقى مجلدا `prompt_versions/` و`m4/speed_before/` القديمان فارغين؛ الملفات نُقلت إلى الأرشيف، لكن حذف المجلدين الفارغين واجه رفض وصول ومنعًا من سياسة التشغيل. لا يقرأهما التطبيق.
