/* Optional end-to-end check. Install Playwright separately; see docs/TESTING.md. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const output=process.env.QA_OUTPUT || path.join(root,'test-results');
fs.mkdirSync(output,{recursive:true});
const port=18123;
const server=spawn(process.env.QA_PYTHON || 'python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(port),'--no-access-log'],{cwd:root,stdio:['ignore','pipe','pipe']});
let browser;
const errors=[];
async function ready(){for(let i=0;i<60;i++){try{if((await fetch(`http://127.0.0.1:${port}/api/status`)).ok)return;}catch{}await new Promise(r=>setTimeout(r,200));}throw new Error('Test server did not start');}
(async()=>{
  try {
    await ready();
    const options={headless:true};
    if(process.env.QA_CHROMIUM)options.executablePath=process.env.QA_CHROMIUM;
    if(process.env.QA_CHROMIUM_ARGS)options.args=JSON.parse(process.env.QA_CHROMIUM_ARGS);
    browser=await chromium.launch(options);
    const page=await browser.newPage({viewport:{width:1440,height:1160}});
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`http://127.0.0.1:${port}/app`);
    await page.waitForFunction(()=>document.getElementById('coverage').textContent.includes('v1.3.0'));
    assert.match(await page.locator('#coverage').innerText(),/v1.3.0.*online species & health/);
    assert.equal(await page.locator('#mode-identify').getAttribute('aria-pressed'),'true');
    await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
    await page.locator('[data-view="guide"]').click();
    assert.equal(await page.locator('.guide-card').count(),15);
    await page.locator('#guide-search').fill('Late blight');assert.equal(await page.locator('.guide-card').count(),2);
    await page.locator('.guide-card').first().click();assert.equal(await page.locator('#detail-dialog').isVisible(),true);
    await page.keyboard.press('Escape');
    await page.locator('#language').selectOption('gu');assert.equal(await page.locator('html').getAttribute('lang'),'gu');
    await page.locator('#language').selectOption('en');await page.locator('[data-view="scan"]').click();
    if(process.env.QA_PHOTO){
      await page.locator('#mode-disease').click();await page.locator('#health-engine').selectOption('starter');
      await page.locator('#crop').selectOption('Tomato');
      await page.locator('#photos').setInputFiles(process.env.QA_PHOTO);
      await page.locator('#verification').selectOption('local');
      await page.locator('#crop-confirmed').check();
      assert.equal(await page.locator('.photo-tile').count(),1);
      await page.locator('#analyze').click();await page.locator('#result').waitFor({state:'visible'});
      assert.match(await page.locator('#result').innerText(),/Model score|model score|relative match/);
      await page.locator('#scan-note').fill('Plot A <script>must remain text</script>');
      await page.locator('#save-result').click();await page.waitForFunction(()=>document.getElementById('journal-count').textContent==='1');
      await page.locator('[data-view="journal"]').click();await page.locator('.journal-card').waitFor();
      assert.match(await page.locator('.journal-card').innerText(),/<script>must remain text<\/script>/);
      await page.reload();await page.locator('.journal-card').waitFor();
      await page.locator('[data-open]').click();await page.locator('#result').waitFor({state:'visible'});
      await page.setViewportSize({width:1440,height:1100});await page.locator('#result').screenshot({path:path.join(output,'result.png')});
      const downloaded=page.waitForEvent('download');await page.locator('#download-result').click();const file=await downloaded;
      await file.saveAs(path.join(output,'downloaded-report.txt'));
      assert.match(fs.readFileSync(path.join(output,'downloaded-report.txt'),'utf8'),/FIELD OBSERVATION/);
      await page.locator('#crop').selectOption('other');assert.equal(await page.locator('#result').isHidden(),true);
      assert.equal(await page.locator('#analyze').isDisabled(),true);
      await page.locator('#mode-identify').click();assert.equal(await page.locator('#analyze').isDisabled(),true);
      assert.match(await page.locator('#provider-state').innerText(),/Add PLANTNET_API_KEY/);
      await page.evaluate(()=>navigator.serviceWorker.ready);
      await page.context().setOffline(true);
      await page.locator('[data-view="journal"]').click();await page.reload();
      await page.locator('.journal-card').waitFor();
      await page.locator('[data-view="guide"]').click();
      await page.waitForFunction(()=>document.querySelectorAll('.guide-card').length===15);
      await page.context().setOffline(false);
    }
    assert.deepEqual(errors,[]);
    console.log('PASS: responsive layouts, guide/search/dialog, language, and available scan/journal/export flows. No page errors.');
  } finally {if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
