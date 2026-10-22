// Actual UI documentation captures: reads + transient chat/selection only.
// No confirmation, cancellation, maintenance change or persisted booking writes.
import {chromium} from 'playwright';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const directory='../docs/evidence/capstone/screenshots';
await mkdir(directory,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({baseURL:'http://127.0.0.1:5173',viewport:{width:1440,height:1000}});
const page=await context.newPage();
const report={purpose:'Current UI documentation, not the original human timed experiments',
  started_at:new Date().toISOString(),screenshots:[],chat_steps:[],mutating_actions:[],errors:[]};
page.on('pageerror',error=>report.errors.push(error.message));
page.on('request',request=>{
  if(request.method()==='PATCH'||request.url().includes('/cancel')||request.url().endsWith('/bookings/confirm'))
    report.mutating_actions.push({method:request.method(),url:request.url()});
});
async function api(path){const r=await page.request.get('/api/'+path);assert.equal(r.status(),200);return r.json();}
async function loaded(){await page.waitForFunction(()=>document.querySelector('.calendar-layout')?.getAttribute('aria-busy')==='false');}
async function day(date){
  const ordinal=value=>Number(value.slice(0,4))*12+Number(value.slice(5,7));
  for(let i=0;i<48;i++){
    const first=await page.locator('.day:not(.other)').first().getAttribute('data-date');
    const difference=ordinal(date)-ordinal(first);
    if(!difference)break;
    await page.locator('.calendar-panel .cal-arrow').nth(difference>0?1:0).click();
  }
  await page.locator('button[data-date="'+date+'"]').click();
}
async function capture(file,caption){
  await page.screenshot({path:directory+'/'+file,fullPage:true});
  report.screenshots.push({file,caption,viewport:page.viewportSize(),captured_at:new Date().toISOString()});
}
async function component(file,selector,caption){
  await page.locator(selector).screenshot({path:directory+'/'+file});
  report.screenshots.push({file,caption,selector,captured_at:new Date().toISOString()});
}
async function send(message){
  const waiting=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().method()==='POST',{timeout:180000});
  await page.getByRole('textbox').fill(message);await page.getByRole('textbox').press('Enter');
  const response=await waiting;assert.equal(response.status(),200);const data=await response.json();
  assert.equal(data.booking,null);report.chat_steps.push({input:message,result:data});
  await page.waitForFunction(()=>document.querySelector('.chat-card')?.getAttribute('aria-busy')==='false');
  return data;
}
try{
  const before=await api('admin/bookings');
  await page.goto('/');
  await page.waitForFunction(()=>document.querySelector('.connection-bar button')?.disabled===false);
  const health=await api('health');assert.equal(health.status,'ok');report.health=health;
  await capture('01-chat-light-ar.png','المحادثة الفعلية، النمط الفاتح، العربية؛ دون أزرار الأمثلة القديمة');
  const missing=await send('أحتاج قاعة اجتماعات يوم 2027-02-15 لعدد 8 أشخاص');
  assert.equal(missing.status,'missing');
  await capture('02-missing-details-ar.png','سؤال حقيقي عن بيانات الموعد الناقصة؛ لقطة توثيقية وليست تجربة الإنتاجية المقاسة');
  const options=await send('من الساعة 10:00 إلى الساعة 12:00');
  assert.equal(options.status,'options');
  await capture('03-room-options-ar.png','خيارات قاعات من قراءة Firestore الفعلية، قبل الاختيار والتأكيد');
  const selectedResponse=page.waitForResponse(r=>r.url().endsWith('/api/chat')&&r.request().postDataJSON()?.action==='select_room');
  await page.locator('.room-option .small-button').first().click();
  const offer=await (await selectedResponse).json();assert.equal(offer.status,'offer');assert.equal(offer.booking,null);
  await page.locator('.confirm-box').waitFor();report.pending_offer=offer.pending_offer;
  await capture('04-pending-offer-ar.png','اختيار منظم مباشر؛ عرض مؤقت للمراجعة ولم يُضغط زر التأكيد');
  await component('09-chat-detail.png','.chat-card','لقطة أصلية لعنصر المحادثة والعرض المعلّق لتكبير القراءة');
  await page.getByRole('button',{name:'تقويم حجوزاتي',exact:true}).click();await loaded();
  const own=before.find(b=>b.employee_id==='sara'&&b.status==='confirmed');assert(own);
  const localDate=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Riyadh',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(own.start_at));
  await day(localDate);await page.locator('[data-detail-id="'+own.booking_id+'"]').waitFor();
  report.displayed_existing_booking=own.booking_id;
  await page.reload();await page.waitForFunction(()=>document.querySelector('.connection-bar button')?.disabled===false);
  await page.getByRole('button',{name:'تقويم حجوزاتي',exact:true}).click();await loaded();await day(localDate);
  await page.locator('[data-detail-id="'+own.booking_id+'"]').waitFor();report.existing_booking_survives_page_reload=true;
  await capture('05-employee-calendar-light.png','حجز سابق محفوظ يظهر بعد إعادة تحميل الصفحة؛ لا يُنسب إلى تجربة توقيت بعينها');
  await component('10-calendar-light-detail.png','.calendar-layout','عنصر تقويم الموظفة وتفاصيل اليوم من التطبيق الفعلي');
  await page.getByRole('button',{name:'تغيير النمط',exact:true}).click();
  await capture('06-employee-calendar-dark.png','تقويم الموظفة بالنمط الداكن مع التفاصيل نفسها');
  await page.getByRole('button',{name:'تبديل الدور',exact:true}).click();
  await page.getByRole('button',{name:/مساحة مسؤول القاعات/}).click();await loaded();await day(localDate);
  await page.waitForFunction(()=>document.querySelectorAll('.room-admin').length===10);
  await capture('07-admin-dark.png','واجهة المسؤول المنفصلة وتقويم جميع الموظفين وحالات القاعات؛ دخول تجريبي لا مصادقة');
  await component('11-admin-calendar-detail.png','.calendar-panel','تقويم جميع الموظفين في واجهة المسؤول الفعلية');
  await component('12-room-status-detail.png','.admin-rooms-section','قاعات مقروءة من Firestore؛ لم تُضغط أزرار الصيانة أثناء الالتقاط');
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await capture('08-mobile-emulation.png','محاكاة عرض هاتف 390 بكسل في Chrome، وليست تجربة هاتف فعلي');
  const after=await api('admin/bookings');
  const canonical=items=>JSON.stringify([...items].sort((a,b)=>a.booking_id.localeCompare(b.booking_id)));
  report.booking_records_unchanged=canonical(before)===canonical(after);
  assert(report.booking_records_unchanged);assert.equal(report.mutating_actions.length,0);assert.equal(report.errors.length,0);
  report.status='passed';report.finished_at=new Date().toISOString();
  console.log(JSON.stringify({status:report.status,screenshots:report.screenshots.length,booking_records_unchanged:true}));
}catch(error){report.status='failed';report.failure=String(error);throw error;}
finally{
  await writeFile('../docs/evidence/capstone/screenshot_manifest.json',JSON.stringify(report,null,2)+'\n');
  await browser.close();
}
