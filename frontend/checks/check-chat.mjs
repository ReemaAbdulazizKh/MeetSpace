// Real local UI + Ollama + Firestore check. Creates ONE real fictional booking,
// identified in docs/evidence/m2/m2_browser_results.json. Does not delete or cancel anything.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
await mkdir('test-results',{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:5173');
  await page.waitForFunction(()=>!document.querySelector('.connection-bar button').disabled);
  await page.getByRole('button',{name:'تغيير اللغة',exact:true}).click();
  const day=new Date();day.setDate(day.getDate()+63);
  const date=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Riyadh',year:'numeric',month:'2-digit',day:'2-digit'}).format(day);
  const message=`I need a training room on ${date} from 14:00 to 15:00 for 20 people.`;
  const responseFor=path=>page.waitForResponse(response=>response.url().endsWith(`/api/${path}`)&&response.request().method()==='POST',{timeout:260000});
  await page.getByRole('textbox',{name:'Message',exact:true}).fill(message);
  const pending=responseFor('chat');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  assert(await page.getByRole('textbox').isDisabled());
  assert(await page.getByRole('button',{name:'Send',exact:true}).isDisabled());
  await page.getByRole('button',{name:'Toggle theme',exact:true}).click();
  await page.getByRole('button',{name:'Switch language',exact:true}).click();
  assert.equal(await page.locator('html').getAttribute('dir'),'rtl');
  const search=await (await pending).json();
  assert.equal(search.status,'options',JSON.stringify(search));
  assert.equal(search.booking,null);
  assert(search.options.every(room=>room.capacity>=20));
  await page.getByRole('button',{name:'تغيير اللغة',exact:true}).click();
  assert((await page.locator('.chat-stream').innerText()).includes(message));
  const selectionPending=responseFor('chat');
  await page.getByRole('button',{name:'Select room',exact:true}).first().click();
  const selection=await (await selectionPending).json();
  assert.equal(selection.status,'offer',JSON.stringify(selection));
  assert.equal(selection.booking,null);
  await page.screenshot({path:'test-results/m2-pending-offer.png',fullPage:true});
  const confirmationPending=responseFor('bookings/confirm');
  await page.getByRole('button',{name:'Confirm booking',exact:true}).click();
  const confirmed=await (await confirmationPending).json();
  assert.equal(confirmed.status,'confirmed',JSON.stringify(confirmed));
  await page.locator(`[data-booking-id="${confirmed.booking.booking_id}"]`).waitFor();
  await page.screenshot({path:'test-results/m2-confirmed.png',fullPage:true});
  await page.getByRole('combobox').selectOption('noura');
  await page.waitForFunction(()=>!document.querySelector('.chat-card')?.getAttribute('aria-busy')||document.querySelector('.chat-card').getAttribute('aria-busy')==='false');
  assert.equal(await page.locator('[data-booking-id]').count(),0);
  assert(!(await page.locator('.chat-stream').innerText()).includes(message));
  await page.getByRole('combobox').selectOption('sara');
  await page.locator(`[data-booking-id="${confirmed.booking.booking_id}"]`).waitFor();
  for(const width of [390,768,1440]) {
    await page.setViewportSize({width,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow ${width}`);
  }
  assert.deepEqual(errors,[]);
  await writeFile('../docs/evidence/m2/m2_browser_results.json',JSON.stringify({status:'passed',input:message,booking:confirmed.booking,session_id:confirmed.session_id,checks:['real UI request/options/select/confirm','loading prevents repeat submit','theme/language preserve messages','employee conversation isolation','390/768/1440 widths','no page errors']},null,2)+'\n');
  console.log('PASS: actual browser chat → Qwen → room cards → pending offer → verified persisted booking',confirmed.booking.booking_id);
} finally {await browser.close();}
