// Real API/browser M3 verification. --read-only checks existing M2 data only.
// Full mode cancels only the NEW fixture explicitly identified by the M3 script.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';

const readOnly=process.argv.includes('--read-only');
const milestone=process.env.MEETSPACE_TEST_MILESTONE || 'm3';
const original=JSON.parse(await readFile('../docs/evidence/m2/m2_persistence_audit.json','utf8')).test_bookings;
const originalSara=original.find(item=>item.label.startsWith('Typical'));
const originalNoura=original.find(item=>item.label.startsWith('Messy'));
const browser=await chromium.launch({channel:'chrome',headless:true});
await mkdir('test-results',{recursive:true});
const context=await browser.newContext({baseURL:'http://127.0.0.1:5173',timezoneId:'America/Los_Angeles',viewport:{width:1440,height:1000}});
const page=await context.newPage();
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const requests=[];page.on('request',request=>{if(request.method()!=='GET')requests.push({url:request.url(),method:request.method()});});
async function loaded(){await page.waitForFunction(()=>document.querySelector('.calendar-layout')?.getAttribute('aria-busy')==='false');}
async function day(value){
  const target=value.slice(0,7),number=value=>Number(value.slice(0,4))*12+Number(value.slice(5,7));
  for(let i=0;i<36;i++){
    const first=await page.locator('.day:not(.other)').first().getAttribute('data-date');
    const difference=number(target)-number(first);
    if(!difference)break;
    await page.locator(`.cal-month-actions button[aria-label="${difference>0?'Next month':'Previous month'}"]`).click();
  }
  await page.locator(`button[data-date="${value}"]`).click();
}
async function admin(){await page.getByRole('button',{name:'Switch role',exact:true}).click();await page.getByRole('button',{name:/Room manager experience/}).click();await loaded();}
const report={status:'running',timezone:'America/Los_Angeles',read_only:readOnly,checks:[]};
let maintenanceEnabled=false;
try {
  await page.goto('http://127.0.0.1:5173');
  await page.waitForFunction(()=>!document.querySelector('.connection-bar button').disabled);
  await page.getByRole('button',{name:'تغيير اللغة',exact:true}).click();
  await page.getByRole('button',{name:'My calendar',exact:true}).click();await loaded();
  await day('2026-11-26');
  await page.locator(`[data-detail-id="${originalSara.booking_id}"]`).waitFor();
  assert((await page.locator(`[data-detail-id="${originalSara.booking_id}"] .booking-meta`).innerText()).includes('10:00 – 12:00'));
  assert.equal(await page.locator(`[data-event-id="${originalNoura.booking_id}"]`).count(),0);
  const own=await page.request.get('/api/bookings?employee_id=sara');
  assert((await own.json()).every(item=>item.employee_id==='sara'));
  await page.getByRole('combobox').selectOption('noura');await loaded();await day('2026-11-27');
  await page.locator(`[data-detail-id="${originalNoura.booking_id}"]`).waitFor();
  assert.equal(await page.locator(`[data-event-id="${originalSara.booking_id}"]`).count(),0);
  report.checks.push('existing M2 employee records and isolation','Riyadh grouping/time despite Los Angeles browser timezone');
  assert.equal(requests.filter(item=>/bookings.*cancel|bookings\/confirm|\/api\/chat/.test(item.url)).length,0);
  await admin();await day('2026-11-26');
  assert((await page.locator(`[data-detail-id="${originalSara.booking_id}"]`).innerText()).includes('Sarah Ahmed'));
  await day('2026-11-27');
  assert((await page.locator(`[data-detail-id="${originalNoura.booking_id}"]`).innerText()).includes('Noura Mohammed'));
  assert.equal(await page.locator('.room-admin').count(),10);
  await page.getByRole('button',{name:'Toggle theme',exact:true}).click();
  await page.getByRole('button',{name:'Switch language',exact:true}).click();
  assert.equal(await page.locator('html').getAttribute('dir'),'rtl');
  await page.locator(`[data-detail-id="${originalNoura.booking_id}"]`).waitFor();
  await page.screenshot({path:'test-results/m3-admin-dark-ar.png',fullPage:true});
  for(const width of [390,768,1440]){
    await page.setViewportSize({width,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Admin overflow ${width}`);
  }
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/m3-admin-mobile-ar.png',fullPage:true});
  await page.getByRole('button',{name:'تغيير اللغة',exact:true}).click();
  report.checks.push('admin across employees','10 actual rooms','theme/language retain selected details','responsive 390/768/1440','calendar clicks never create bookings');
  if(!readOnly){
    const live=JSON.parse(await readFile(`../docs/evidence/${milestone}/${milestone}_live_results.json`,'utf8'));
    assert.equal(live.status,'passed');
    const fixture=live.ui_cancel_fixture;
    const room=page.locator('[data-room-id="M01"] button');
    const enabled=page.waitForResponse(response=>response.url().endsWith('/api/admin/rooms/M01/status')&&response.request().method()==='PATCH');
    await room.click();assert.equal((await enabled).status(),200);maintenanceEnabled=true;
    await page.waitForFunction(()=>document.querySelector('[data-room-id="M01"] button').textContent.includes('Maintenance'));
    const restored=page.waitForResponse(response=>response.url().endsWith('/api/admin/rooms/M01/status')&&response.request().method()==='PATCH');
    await room.click();assert.equal((await restored).status(),200);maintenanceEnabled=false;
    await page.waitForFunction(()=>document.querySelector('[data-room-id="M01"] button').textContent.includes('Available'));
    report.checks.push('real browser maintenance enable and restore');
    await page.getByRole('button',{name:'Switch role',exact:true}).click();
    await page.getByRole('button',{name:/Employee experience/}).click();
    await page.getByRole('combobox').selectOption(fixture.employee_id);
    await page.getByRole('button',{name:'My calendar',exact:true}).click();await loaded();await day(live.fixture_day);
    const detail=page.locator(`[data-detail-id="${fixture.booking_id}"]`);await detail.waitFor();
    page.once('dialog',dialog=>dialog.dismiss());
    await detail.getByRole('button',{name:'Cancel booking',exact:true}).click();
    assert((await detail.innerText()).includes('Confirmed'));
    assert.equal(requests.filter(item=>item.url.endsWith(`/bookings/${fixture.booking_id}/cancel`)).length,0);
    const canceled=page.waitForResponse(response=>response.url().endsWith(`/bookings/${fixture.booking_id}/cancel`));
    page.once('dialog',dialog=>dialog.accept());
    await detail.getByRole('button',{name:'Cancel booking',exact:true}).click();
    const cancellation=await canceled;assert.equal(cancellation.status(),200);assert.equal((await cancellation.json()).status,'canceled');
    await page.waitForFunction(id=>document.querySelector(`[data-detail-id="${id}"] .status`)?.textContent==='Canceled',fixture.booking_id);
    assert.equal(await detail.getByRole('button',{name:'Cancel booking',exact:true}).count(),0);
    await page.screenshot({path:'test-results/m3-employee-canceled-en.png',fullPage:true});
    report.canceled_fixture=fixture.booking_id;
    report.checks.push('dismissed confirmation sends no cancellation','accepted confirmation persists cancellation and updates calendar');
    for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
    // This early local slot starts on the PREVIOUS UTC date. It must appear only
    // on its Riyadh calendar day, even in this Los Angeles browser.
    await page.getByRole('combobox').selectOption('fahad');await loaded();await day(live.fixture_day);
    const local=live.test_bookings.find(item=>item.label==='M3 API cancellation fixture');
    await page.locator(`[data-detail-id="${local.booking_id}"]`).waitFor();
    assert((await page.locator(`[data-detail-id="${local.booking_id}"] .booking-meta`).innerText()).includes('00:30 – 01:30'));
    report.checks.push('previous-UTC-date booking displayed on correct Riyadh day','employee calendar responsive');
  }
  assert.deepEqual(errors,[]);report.status='passed';
  await writeFile(`../docs/evidence/${milestone}/${milestone}_${readOnly?'browser_readonly':'browser_results'}.json`,JSON.stringify(report,null,2)+'\n');
  console.log('PASS',JSON.stringify(report));
} finally {
  if(maintenanceEnabled)await page.request.patch('/api/admin/rooms/M01/status',{data:{status:'available'}});
  await browser.close();
}
