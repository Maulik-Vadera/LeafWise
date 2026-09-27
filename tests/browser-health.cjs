/* UI regression with simulated provider results; never calls a live API. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),port=18125;
const output=process.env.QA_OUTPUT||path.join(root,'test-results');fs.mkdirSync(output,{recursive:true});
const server=spawn(process.env.QA_PYTHON||'python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(port),'--no-access-log'],{cwd:root,env:{...process.env,PLANTNET_API_KEY:'browser-test-not-a-real-key'},stdio:['ignore','pipe','pipe']});
let browser;
async function ready(){for(let i=0;i<60;i++){try{if((await fetch(`http://127.0.0.1:${port}/api/status`)).ok)return;}catch{}await new Promise(r=>setTimeout(r,200));}throw new Error('Server did not start');}
(async()=>{
 try{
  await ready();const options={headless:true};if(process.env.QA_CHROMIUM)options.executablePath=process.env.QA_CHROMIUM;if(process.env.QA_CHROMIUM_ARGS)options.args=JSON.parse(process.env.QA_CHROMIUM_ARGS);
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1440,height:1120},serviceWorkers:'block'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));let localCalls=0,healthCalls=0,healthState='candidates';
  page.on('request',r=>{if(new URL(r.url()).pathname==='/api/analyze')localCalls++;});
  await page.route('**/api/plantnet/diseases',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({provider:'Pl@ntNet',count:2,note:'Condition list; not a list of supported host plants.',entries:[{code:'APHISP',name:'Aphis sp.',categories:['Insecta'],reference_url:'https://gd.eppo.int/taxon/APHISP'},{code:'ELSIAM',name:'Elsinoe ampelina',categories:[],reference_url:'https://gd.eppo.int/taxon/ELSIAM'}]})}));
  await page.route('**/api/health',r=>{
   healthCalls++;assert.match(r.request().postData(),/name="consent"\r\n\r\nyes/);assert.match(r.request().postData(),/name="organs"/);
   const result={id:'health-fixture-'+healthCalls,created_at:new Date().toISOString(),mode:'disease',provider:'Pl@ntNet',status:healthState,version:'simulated-provider',remaining_requests:9,candidates:healthState==='no_match'?[]:[{name:'Aphis sp.',code:'APHISP',score:healthState==='uncertain'?.3:.91,reference_url:'https://gd.eppo.int/taxon/APHISP'}],note:healthState==='no_match'?'No supported condition was identified. This does not establish that the plant is healthy.':'Possible conditions need confirmation.',coverage_note:'Limited plant and condition coverage.',score_note:'Provider score is not diagnostic accuracy.',next_steps:['Photograph affected areas and record changes.','Confirm the cause with a crop adviser.']};
   return r.fulfill({status:healthState==='error'?502:200,contentType:'application/json',body:JSON.stringify(healthState==='error'?{code:'unauthorized',detail:'Disease identification is not authorized for this key.'}:result)});
  });
  await page.goto(`http://127.0.0.1:${port}/app`);await page.waitForFunction(()=>document.getElementById('coverage').textContent.includes('v1.3.0'));
  await page.locator('#mode-disease').click();assert.equal(await page.locator('#health-engine').inputValue(),'plantnet');assert.equal(await page.locator('#crop').isHidden(),true);
  await page.locator('#disease-coverage').click();await page.locator('#condition-search').waitFor();await page.locator('#condition-search').fill('Aphis');assert.equal(await page.locator('#condition-list li').count(),1);await page.locator('#close-detail').click();
  const pixels=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d');x.fillStyle='#658443';x.fillRect(0,0,256,256);return c.toDataURL('image/png').split(',')[1];});
  await page.locator('#photos').setInputFiles({name:'affected-leaf.png',mimeType:'image/png',buffer:Buffer.from(pixels,'base64')});assert.equal(await page.locator('#analyze').isDisabled(),true);
  await page.locator('#consent').check();assert.match(await page.locator('#analyze').innerText(),/Check disease & pests/);await page.locator('#analyze').click();await page.locator('#result').waitFor({state:'visible'});
  assert.match(await page.locator('#result-title').innerText(),/Possible condition: Aphis sp/);assert.match(await page.locator('#result').innerText(),/EPPO code: APHISP/);assert.doesNotMatch(await page.locator('#result').innerText(),/Genus:|Family:|cultivar/);assert.equal(localCalls,0);assert.equal(healthCalls,1);
  await page.locator('#save-result').click();await page.waitForFunction(()=>document.getElementById('journal-count').textContent==='1');
  const downloaded=page.waitForEvent('download');await page.locator('#download-result').click();const file=await downloaded;await file.saveAs(path.join(output,'disease-report.txt'));const report=fs.readFileSync(path.join(output,'disease-report.txt'),'utf8');assert.match(report,/EPPO APHISP/);assert.doesNotMatch(report,/undefined/);
  await page.screenshot({path:path.join(output,'health-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:path.join(output,'health-mobile.png'),fullPage:true});
  healthState='no_match';await page.locator('#analyze').click();await page.waitForFunction(()=>document.getElementById('result-title')?.textContent==='No supported condition identified');assert.match(await page.locator('#result').innerText(),/does not establish/);
  healthState='uncertain';await page.locator('#analyze').click();await page.waitForFunction(()=>document.getElementById('result-title')?.textContent==='More evidence needed');
  healthState='error';await page.locator('#analyze').click();await page.locator('#scan-error').waitFor({state:'visible'});assert.match(await page.locator('#scan-error').innerText(),/not authorized/);assert.equal(await page.locator('#result').isHidden(),true);assert.equal(localCalls,0);
  await page.locator('#language').selectOption('gu');assert.equal(await page.locator('#analyze span').innerText(),'રોગ અને જીવાત તપાસો');await page.locator('#language').selectOption('en');
  await page.reload();await page.locator('[data-view="journal"]').click();await page.locator('.journal-card').waitFor();assert.match(await page.locator('.journal-card').innerText(),/Aphis/);await page.locator('[data-open]').click();await page.locator('#result').waitFor({state:'visible'});assert.match(await page.locator('#result').innerText(),/EPPO code: APHISP/);
  assert.deepEqual(errors,[]);console.log('PASS: online disease default; catalog search; consent; correct endpoint; condition results/EPPO; report/journal; no-match; uncertainty; errors without fallback; mobile; translations. Simulated provider only.');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
