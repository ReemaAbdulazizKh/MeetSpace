// UI feedback checks: real reads, plus explicitly injected HTTP failures.
// No Firestore records are created or modified by this script.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
  const page=await browser.newPage();
  await page.goto('http://127.0.0.1:5173');
  await page.waitForFunction(()=>!document.querySelector('.connection-bar button').disabled);
  await page.getByRole('button',{name:'تغيير اللغة',exact:true}).click();
  let release;
  const gate=new Promise(resolve=>{release=resolve;});
  const route='**/api/bookings?employee_id=*';
  await page.route(route,async request=>{await gate;await request.continue();});
  await page.getByRole('button',{name:'My calendar',exact:true}).click();
  assert.equal(await page.locator('.calendar-layout').getAttribute('aria-busy'),'true');
  assert(await page.getByRole('button',{name:'Refresh bookings',exact:true}).isDisabled());
  assert.equal(await page.locator('.empty').count(),0);
  release();
  await page.waitForFunction(()=>document.querySelector('.calendar-layout').getAttribute('aria-busy')==='false');
  assert((await page.locator('.empty').innerText()).includes('No bookings on this day'));
  await page.unroute(route);
  await page.route(route,request=>request.fulfill({status:503,contentType:'application/json',body:'{"detail":"Injected read failure for UI verification"}'}));
  await page.getByRole('button',{name:'Refresh bookings',exact:true}).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.locator('.empty').count(),0);
  assert.equal(await page.locator('.booking-item').count(),0);
  await page.unroute(route);
  await page.getByRole('button',{name:'Reload',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.calendar-layout').getAttribute('aria-busy')==='false');
  assert.equal(await page.getByRole('alert').count(),0);
  await page.getByRole('button',{name:'Switch role',exact:true}).click();
  await page.getByRole('button',{name:/Room manager experience/}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.room-admin button:enabled').length===10);
  await page.route('**/api/admin/bookings',request=>request.fulfill({status:503,contentType:'application/json',body:'{"detail":"Injected admin read failure for UI verification"}'}));
  await page.getByRole('button',{name:'Refresh data',exact:true}).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.locator('.room-admin').count(),0);
  assert((await page.locator('.admin-stats').innerText()).includes('—'));
  await page.unroute('**/api/admin/bookings');
  await page.getByRole('button',{name:'Reload',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.room-admin button:enabled').length===10);
  assert.equal(await page.getByRole('alert').count(),0);
  const report={status:'passed',checks:['real reads after controlled loading delay','no false empty state during loading','actual empty selected day','explicit injected employee/admin HTTP 503 feedback','no fake inventory or success on read failure','reload recovery using actual API'],database_writes:0};
  await writeFile(`../docs/evidence/${process.env.MEETSPACE_TEST_MILESTONE || 'm3'}/${process.env.MEETSPACE_TEST_MILESTONE || 'm3'}_ui_state_checks.json`,JSON.stringify(report,null,2)+'\n');
  console.log('PASS',JSON.stringify(report));
} finally {await browser.close();}
