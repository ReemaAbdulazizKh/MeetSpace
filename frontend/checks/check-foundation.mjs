// Local QA only: npm install --no-save --package-lock=false playwright
// Uses existing Chrome; no browser download or production dependency.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
await mkdir('test-results', {recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  assert.equal((await page.goto('http://127.0.0.1:5173')).status(),200);
  await page.getByRole('button',{name:'فحص الاتصال',exact:true}).waitFor();
  await page.waitForFunction(()=>!document.querySelector('.connection-bar button').disabled);
  assert.equal(await page.locator('html').getAttribute('dir'),'rtl');
  assert.equal(await page.getByRole('navigation').innerText(),'المساعد الذكي\nتقويم حجوزاتي');
  await page.getByRole('textbox').fill('مسودة لا ترسل');
  await page.getByRole('button',{name:'تغيير النمط',exact:true}).click();
  assert(await page.locator('body').evaluate(el=>el.classList.contains('dark')));
  await page.getByRole('button',{name:'تغيير اللغة',exact:true}).click();
  assert.equal(await page.locator('html').getAttribute('dir'),'ltr');
  assert.equal(await page.getByRole('textbox').inputValue(),'مسودة لا ترسل');
  await page.getByRole('combobox').selectOption('noura');
  assert.equal(await page.getByRole('textbox').inputValue(),'');
  await page.getByRole('combobox').selectOption('sara');
  assert.equal(await page.getByRole('textbox').inputValue(),'مسودة لا ترسل');
  assert(await page.getByRole('button',{name:'Send',exact:true}).isEnabled());
  await page.getByRole('button',{name:'My calendar',exact:true}).click();
  const heading=await page.locator('.cal-header h2').innerText();
  await page.getByRole('button',{name:'Next month',exact:true}).click();
  assert.notEqual(await page.locator('.cal-header h2').innerText(),heading);
  await page.getByRole('button',{name:'Today',exact:true}).click();
  assert.equal(await page.locator('.cal-header h2').innerText(),heading);
  await page.locator('.day:not(.other)').nth(10).click();
  assert.equal(await page.locator('.day[aria-pressed="true"]').count(),1);
  await page.getByRole('button',{name:'New booking',exact:true}).click();
  assert(await page.getByRole('textbox').isVisible());
  await page.screenshot({path:'test-results/chat-dark-en.png',fullPage:true});
  await page.getByRole('button',{name:'Switch role',exact:true}).click();
  await page.getByRole('button',{name:/Room manager experience/}).click();
  assert.equal(await page.getByRole('navigation').innerText(),'Room manager');
  await page.waitForFunction(()=>document.querySelectorAll('.room-admin button:enabled').length===10);
  assert.equal(await page.locator('.room-admin').count(),10);
  await page.getByRole('button',{name:'Switch language',exact:true}).click();
  await page.getByRole('button',{name:'تغيير النمط',exact:true}).click();
  await page.screenshot({path:'test-results/admin-light-ar.png',fullPage:true});
  for (const width of [390,768,1440]) {
    await page.setViewportSize({width,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),`Overflow at ${width}px`);
  }
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/admin-mobile-ar.png',fullPage:true});
  await page.getByRole('button',{name:'تبديل الدور',exact:true}).click();
  await page.getByRole('button',{name:/مساحة الموظف/}).click();
  for (const width of [390,768,1440]) {
    await page.setViewportSize({width,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),`Chat overflow at ${width}px`);
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: real local browser navigation, employee isolation, disabled actions, calendar, themes, RTL/LTR, 390/768/1440 layouts; no page errors.');
} finally {await browser.close();}
