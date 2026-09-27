import {listScans, saveScan, removeScan} from './journal.js';
import {translate, copy} from './i18n.js';
import {preparePhoto} from './photos.js';
import './install.js';

const $ = id => document.getElementById(id);
const escape = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const pct = n => `${(Math.max(0,Math.min(1,Number(n)||0))*100).toFixed(1)}%`;
const safeUrl = value => { try {const u=new URL(value);return u.protocol==='https:' ? u.href : '#';} catch{return '#';} };
const dateText = value => new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
let lang='en';try {lang=localStorage.getItem('leafwise-language') || 'en';} catch {}
if (!copy[lang]) lang='en';
$('language').value=lang;translate(lang);
let mode=null, photos=[], current=null, currentThumb=null, controller=null, generation=0, catalog=[], status=null, stream=null, checkingProvider=false;
let toastTimer;
const starterMode=()=>mode==='disease'&&$('health-engine').value==='starter';
const remoteMode=()=>mode==='identify'||(mode==='disease'&&!starterMode())||(starterMode()&&$('verification').value==='online');
const actionKey=()=>mode==='identify'?'identify':starterMode()?'analyze':'checkDisease';
function toast(message) {$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').hidden=true;},4500);}
function error(message='') {$('scan-error').textContent=message;$('scan-error').hidden=!message;}
function controls() {
  const pending=!!controller;
  const remote=remoteMode();
  const knownCrop=status?.crops.some(c=>c.id===$('crop').value);
  $('analyze').disabled = pending || !photos.length || (remote&&(!status?.plantnet_available||!$('consent').checked)) || (starterMode()&&(!status?.ready||!knownCrop||!$('crop-confirmed').checked));
  $('starter-fields').hidden=!starterMode();$('online-health-info').hidden=starterMode();
  $('disease-coverage').disabled=!status?.plantnet_available;
  $('analyze').querySelector('span').dataset.i18n=actionKey();
  $('analyze').querySelector('span').textContent=copy[lang][actionKey()];
  $('consent-wrap').hidden=!remote;
  $('provider-panel').hidden=!remote;
  $('check-provider').disabled=checkingProvider||!status?.plantnet_available;
  $('verification-note').textContent=$('verification').value==='online'?'Species is checked first. An unsupported plant or an API error stops the disease scan.':'Plant identity will not be checked. This model can misclassify unfamiliar plants; use this only for a crop you already know.';
  $('privacy-copy').textContent=remote?'Photos go to Pl@ntNet only after you allow it and start the scan. This app’s server does not store them.':'Photos stay on this app’s server for processing and are not stored. Plant identity is not verified in local-only mode.';
  $('consent-wrap').querySelector('label').textContent=mode==='disease'&&!starterMode()?'Send these photos, without embedded location metadata, to Pl@ntNet for disease and pest identification. This uses internet access and the website’s shared identification allowance.':'Send these photos, without embedded location metadata, to Pl@ntNet for plant identification. This uses internet access and the website’s shared identification allowance.';
  $('busy').hidden=!pending;
  $('analyze').hidden=pending;
}
function invalidate() {
  generation++;if(controller)controller.abort();controller=null;current=null;currentThumb=null;$('result').hidden=true;error();controls();
}
function changeMode(next) {
  if(mode===next)return;
  invalidate();mode=next;
  $('health-fields').hidden=mode!=='disease';$('identify-fields').hidden=mode!=='identify';
  $('mode-disease').classList.toggle('selected',mode==='disease');$('mode-identify').classList.toggle('selected',mode==='identify');
  $('mode-disease').setAttribute('aria-pressed',String(mode==='disease'));$('mode-identify').setAttribute('aria-pressed',String(mode==='identify'));
  $('analyze').querySelector('span').dataset.i18n=mode==='identify'?'identify':'analyze';
  $('analyze').querySelector('span').textContent=mode==='identify' ? copy[lang].identify : copy[lang].analyze;
  renderPhotos();controls();
}
function renderPhotos() {
  $('photo-count').textContent=`${photos.length} / 3`;$('dropzone').hidden=photos.length>0;$('add-more').hidden=!photos.length||photos.length>=3;
  $('photo-grid').innerHTML=photos.map((photo,i)=>`<div class="photo-tile"><img src="${photo.url}" alt="Selected plant photo ${i+1}"><button type="button" class="remove-photo" data-remove="${i}" aria-label="Remove photo ${i+1}">×</button><small>${escape(photo.file.name)}</small>${!starterMode()?`<select data-organ="${i}" aria-label="Plant part in photo ${i+1}">${['leaf','flower','fruit','bark','auto'].map(o=>`<option value="${o}" ${o===photo.organ?'selected':''}>${o==='auto'?'Not sure':o[0].toUpperCase()+o.slice(1)}</option>`).join('')}</select>`:''}</div>`).join('');
  controls();
}
async function addFiles(files) {
  invalidate();$('crop-confirmed').checked=false;
  const messages=[];
  for(const file of files) {
    if(photos.length>=3){messages.push('You can add up to three photos of the same plant.');break;}
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)){messages.push('Use JPG, PNG or WebP. For HEIC, export the photo as JPEG first.');continue;}
    if(file.size>6*1024*1024){messages.push('Each photo must be under 6 MB. Export a smaller copy.');continue;}
    if(photos.some(p=>p.file.name===file.name&&p.file.size===file.size&&p.file.lastModified===file.lastModified)){messages.push('That photo is already selected.');continue;}
    photos.push({file,url:URL.createObjectURL(file),organ:'leaf'});
  }
  error(messages.join(' '));renderPhotos();
}
async function thumbnail(file) {
  const bitmap=await createImageBitmap(file);
  const canvas=document.createElement('canvas');const scale=Math.min(1,360/Math.max(bitmap.width,bitmap.height));
  canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
  return new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.8));
}
async function requestJson(url,options) {
  const response=await fetch(url,options);let data;
  try{data=await response.json();}catch{throw new Error(response.status===413?'The upload is too large. Try fewer or smaller photos.':'The server could not finish this request. Wait a moment and try again.');}
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'The request could not be completed.');
  return data;
}
function sourceLinks(sources=[]) {return `<div class="sources">${sources.map(s=>`<a href="${escape(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${escape(s.title)} ↗</a>`).join('')}</div>`;}
function list(items,ordered=false) {const tag=ordered?'ol':'ul';return `<${tag}>${(items||[]).map(x=>`<li>${escape(x)}</li>`).join('')}</${tag}>`;}
function guideHtml(guide) {
  return `<p>${escape(guide.summary)}</p><h3>What to look for</h3>${list(guide.look_for)}<h3>Practical next steps</h3>${list(guide.steps,true)}<h3>Read the sources</h3>${sourceLinks(guide.sources)}`;
}
function titleOf(result) {
  if(result.mode==='disease'&&result.provider){if(result.status==='no_match')return 'No supported condition identified';if(result.status==='uncertain')return 'More evidence needed';return `Possible condition: ${result.candidates?.[0]?.name||'Unknown'}`;}
  if(result.provider){const best=result.candidates?.[0];return best?`Possible ${result.mode==='variety'?'variety':'species'}: ${result.mode==='variety'?best.name:best.common_names?.[0]||best.name}`:'Plant identification · no match';}
  if(result.status==='possible_match')return `${result.candidate.crop} · ${result.candidate.name}`;
  return ({uncertain:'More evidence needed',retake:'A clearer photo will help',unsupported:'Disease screening unavailable',needs_identification:'Identify the plant first',needs_confirmation:'Confirm the crop first'})[result.status] || 'Leaf scan';
}
let resultThumbUrl=null;
function renderResult(result,thumb,note='',fromCurrentPhotos=false) {
  if(resultThumbUrl){URL.revokeObjectURL(resultThumbUrl);resultThumbUrl=null;}
  if(thumb)resultThumbUrl=URL.createObjectURL(thumb);
  const online=!!result.provider;const accepted=result.status==='possible_match';
  const health=online&&result.mode==='disease';
  const badge=health?'Disease & pest scan · Pl@ntNet':online?'Candidates · Pl@ntNet':accepted?(result.candidate.healthy?'No listed disease pattern':'Possible match'):'Needs another look';
  const guide=result.guide || {};
  let content;
  if(health) {
    content=`<div class="result-columns"><div><p>${escape(result.note)}</p>${result.candidates?.length?`<ol class="health-candidates">${result.candidates.map(c=>`<li><strong>${escape(c.name)}</strong><span>${pct(c.score)} provider score</span><small>EPPO code: ${escape(c.code)}</small>${c.reference_url?`<a href="${escape(safeUrl(c.reference_url))}" target="_blank" rel="noopener noreferrer">Read the EPPO reference ↗</a>`:''}</li>`).join('')}</ol>`:''}<p class="score-note">${escape(result.score_note)}</p><h3>What to do next</h3>${list(result.next_steps,true)}</div><aside><div class="inset-note"><h3>About this health check</h3><p>${escape(result.coverage_note)}</p><p>Engine: Pl@ntNet disease identification${result.version?` · ${escape(result.version)}`:''}.</p>${result.remaining_requests!==null&&result.remaining_requests!==undefined?`<p>${escape(result.remaining_requests)} identification requests remaining today.</p>`:''}<p>The offline starter model was not used for this result.</p><a href="https://my.plantnet.org/doc/api/diseases" target="_blank" rel="noopener noreferrer">How this service works ↗</a></div><div class="inset-note"><h3>Get local advice</h3><p>If symptoms spread, share these observations with a crop adviser. A field examination may change the diagnosis.</p><a href="https://www.icar.gov.in/en/krishi-vigyan-kendras-kvks" target="_blank" rel="noopener noreferrer">Find help through ICAR / KVK ↗</a></div></aside></div>`;
  } else if(online) {
    content=`<div class="result-columns"><div><p>${escape(result.note)}</p><ol>${(result.candidates||[]).map(c=>`<li><strong>${escape(c.name)}</strong> · ${pct(c.score)} model score<br>${escape(c.common_names?.join(', '))}<br><em>${escape(c.scientific_name)}</em><br>Genus: ${escape(c.genus||'—')} · Family: ${escape(c.family||'—')}</li>`).join('')}</ol>${!result.candidates?.length?'<p>Try a different view, including a flower or fruit when available.</p>':''}</div><aside><div class="inset-note"><h3>About this identification</h3><p>Provided by Pl@ntNet. Scores rank candidates; they do not certify species, edibility, health or cultivar identity.</p><p>A plant's variety often needs fruit, flowers, provenance or genetic evidence. Unknown is a valid result.</p><a href="https://plantnet.org/en/" target="_blank" rel="noopener noreferrer">About Pl@ntNet ↗</a></div></aside></div>`;
  } else {
    content=`<div class="result-columns"><div>${result.reasons?.length?`<div class="inset-note">${list(result.reasons)}</div>`:''}${guideHtml(guide)}</div><aside>${result.candidate?`<h3>Visual possibilities</h3><ul class="candidate-list">${result.candidates.map(c=>`<li><div>${escape(c.crop)}<br><strong>${escape(c.name)}</strong></div><span>${pct(c.score)}</span></li>`).join('')}</ul><p class="score-note">${escape(result.score_note)}</p><h3>About the crop category</h3><p><em>${escape(result.candidate.scientific_name)}</em><br>${escape(result.candidate.plant_type)} · cultivar not identified</p><p class="score-note">Taxonomy describes the suggested crop category. It is not a separate species-identification result.</p>`:''}${result.quality?.some(q=>q.warnings?.length)?`<h3>Photo notes</h3>${list([...new Set(result.quality.flatMap(q=>q.warnings))])}`:''}<div class="inset-note"><h3>When to ask for help</h3><p>${guide.urgency==='prompt'?'Arrange prompt local assessment if these symptoms are spreading.':'If symptoms spread or growth declines, ask a crop adviser to inspect the plant.'}</p><a href="https://www.icar.gov.in/en/krishi-vigyan-kendras-kvks" target="_blank" rel="noopener noreferrer">Find help through ICAR / KVK ↗</a></div><p class="score-note">${escape(result.scope_note||'Photo screening cannot confirm a disease.')} Field performance has not been validated.</p></aside></div>`;
  }
  const scope=result.health_scope;
  const scopeHtml=scope?`<div class="inset-note"><h3>Offline starter model coverage</h3><p>${escape(scope.message)}</p></div>`:'';
  const identityHtml=result.identity?.candidates?.length?`<div class="inset-note"><h3>Species check · Pl@ntNet</h3><p>Leading candidate: ${escape(result.identity.candidates[0].scientific_name)}. ${escape(result.identity.note)}</p></div>`:'';
  const nextAction=fromCurrentPhotos&&result.mode==='species'?'<button id="result-health" class="button secondary" type="button">Check disease &amp; pests in these photos</button>':['needs_identification','unsupported'].includes(result.status)&&!online?'<button id="result-identify" class="button secondary" type="button">Identify this plant</button>':'';
  $('result').innerHTML=`<div class="result-top">${resultThumbUrl?`<img class="result-thumb" src="${resultThumbUrl}" alt="Photo used for this scan">`:''}<div class="result-title-block"><span class="status-pill ${accepted?'':'amber'}">${badge}</span><h2 id="result-title">${escape(titleOf(result))}</h2><p class="result-subtitle">${escape(dateText(result.created_at))}${result.model?` · ${escape(result.model.name)}`:''}</p></div></div>${lang!=='en'?'<p class="language-note">Detailed crop guidance is currently in English. Navigation is translated.</p>':''}${scopeHtml}${identityHtml}${result.crop_source?`<p class="inset-note">${escape(result.crop_source)}</p>`:''}${nextAction}${content}<div class="result-actions"><label class="sr-only" for="scan-note">Add a field note</label><input id="scan-note" type="text" maxlength="500" placeholder="Add a note: plot, changes, observations…" value="${escape(note)}"><button id="save-result" class="button primary">${icon('book')}Save to journal</button><button id="download-result" class="button secondary">Download report</button><button id="print-result" class="button quiet">Print / PDF</button></div>`;
  if($('result-identify'))$('result-identify').onclick=()=>{changeMode('identify');$('scan-title').scrollIntoView({block:'center'});};
  if($('result-health'))$('result-health').onclick=()=>{$('health-engine').value='plantnet';changeMode('disease');$('scan-title').scrollIntoView({block:'center'});};
  $('result').hidden=false;
  $('save-result').onclick=async()=>{try{const row={id:result.id,created_at:result.created_at,result,thumbnail:thumb,note:$('scan-note').value.trim()};await saveScan(row);toast('Saved in this browser’s journal.');await updateCount();}catch(e){toast(e.message);}};
  $('download-result').onclick=()=>download(`Leafwise-${result.id.slice(0,8)}.txt`,new Blob([reportText(result,$('scan-note').value)],{type:'text/plain;charset=utf-8'}));
  $('print-result').onclick=()=>window.print();
}
function reportText(r,note) {
  let lines=['LEAFWISE · FIELD OBSERVATION',titleOf(r),dateText(r.created_at),'',`Record: ${r.id}`,`Status: ${r.status}`];
  if(r.mode==='disease'&&r.provider){lines.push(`Provider: ${r.provider} disease identification`,r.note,...r.candidates.map(c=>`${c.name} | EPPO ${c.code} | provider score ${pct(c.score)}${c.reference_url?' | '+c.reference_url:''}`),r.score_note||'',r.coverage_note||'','NEXT STEPS',...(r.next_steps||[]));}
  else if(r.provider){lines.push(`Provider: ${r.provider}`,r.note,...r.candidates.map(c=>`${c.name} | ${c.scientific_name} | model score ${pct(c.score)}`));}
  else {lines.push(...(r.reasons||[]),'','POSSIBILITIES',...(r.candidates||[]).map(c=>`${c.crop}: ${c.name} | model score ${pct(c.score)}`),'',r.score_note||'',r.guide?.summary||'','NEXT STEPS',...(r.guide?.steps||[]),'','SOURCES',...(r.guide?.sources||[]).map(s=>`${s.title}: ${s.url}`),'',r.scope_note||'');}
  if(r.health_scope)lines.push('',r.health_scope.message);
  if(r.crop_source)lines.push('',r.crop_source);
  if(r.identity?.candidates?.length)lines.push('Species check: '+r.identity.candidates[0].scientific_name);
  lines.push('','YOUR NOTE',note||'—','','Visual screening, not a confirmed diagnosis. No independently measured field accuracy. Cultivar identity is not guaranteed.');
  return lines.join('\n');
}
function download(name,blob) {const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}

async function analyze() {
  error();current=null;currentThumb=null;$('result').hidden=true;const token=++generation;const owned=new AbortController();controller=owned;controls();
  const timeout=setTimeout(()=>owned.abort('timeout'),55000);
  const snapshot=photos.map(p=>({...p}));const starter=starterMode();
  const endpoint=mode==='identify'?'/api/identify':starter?'/api/analyze':'/api/health';
  const form=new FormData();
  form.append('crop',$('crop').value);form.append('consent',$('consent').checked?'yes':'no');form.append('mode',$('identity-mode').value);
  form.append('crop_confirmed',$('crop-confirmed').checked?'yes':'no');form.append('verification',$('verification').value);
  try {
    for(let i=0;i<snapshot.length;i++) {
      const prepared=await preparePhoto(snapshot[i].file);
      if(token!==generation)return;owned.signal.throwIfAborted();
      form.append('photos',prepared,`plant-${i+1}.jpg`);if(!starter)form.append('organs',snapshot[i].organ);
    }
    const thumb=await thumbnail(snapshot[0].file);
    if(token!==generation)return;owned.signal.throwIfAborted();
    const result=await requestJson(endpoint,{method:'POST',body:form,signal:owned.signal});
    if(token!==generation)return;
    current=result;currentThumb=thumb;renderResult(result,thumb,'',true);$('result').focus({preventScroll:true});$('result').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
  } catch(e) {
    if(token===generation){if(owned.signal.aborted)error(owned.signal.reason==='timeout'?'The request took too long. Check the connection and try again.':'Scan cancelled.');else error(e instanceof TypeError?'Cannot reach Leafwise. Check your connection and try again.':e.message);}
  } finally {clearTimeout(timeout);if(token===generation){controller=null;controls();}}
}
async function loadStatus() {
  try {
    const firstLoad=status===null;
    status=await requestJson('/api/status',{signal:AbortSignal.timeout(20000)});
    $('connection').hidden=status.ready;$('connection').textContent=status.ready?'':'The starter model is unavailable. Online species and disease checks can still run with a working Pl@ntNet connection.';
    $('coverage').textContent=`v${status.version} · online species & health`;
    $('health-coverage').textContent=`Starter model: ${status.crops.map(c=>c.name).join(', ')} only. This is the original small model, with no established field accuracy.`;
    const previous=$('crop').value;
    $('crop').innerHTML='<option value="auto">Choose a known crop</option>'+status.crops.map(c=>`<option value="${escape(c.id)}">${escape(c.name)}</option>`).join('')+'<option value="other">Another crop / tree · disease model unavailable</option>';
    if([...$('crop').options].some(o=>o.value===previous))$('crop').value=previous;
    $('provider-state').textContent=status.plantnet.message;
    $('provider-help').hidden=!!status.hosted;
    if(firstLoad)$('verification').value=status.plantnet_available?'online':'local';
  } catch {
    status=null;$('connection').hidden=false;$('connection').textContent='Leafwise is not reachable. Check your internet connection, or start the server if you run it on your own computer. Saved journal entries and cached guides still work.';$('coverage').textContent='Journal available offline';
  }
  controls();
}
async function checkProvider() {
  checkingProvider=true;controls();$('provider-state').textContent='Checking the Pl@ntNet connection…';
  try {const result=await requestJson('/api/plantnet/check',{method:'POST',signal:AbortSignal.timeout(20000)});$('provider-state').textContent=result.message;}
  catch(e){$('provider-state').textContent=e.name==='TimeoutError'?'Connection check timed out. Try again.':e.message;}
  finally{checkingProvider=false;controls();}
}
function providerHelp() {
  showDetail('<h2>Connect plant identification</h2><ol><li>Open your extracted Leafwise folder.</li><li>Copy <code>.env.example</code> to <code>.env</code>, then open <code>.env</code> in Notepad.</li><li>Paste your private key after <code>PLANTNET_API_KEY=</code> and save. Make sure the filename is <code>.env</code>, not <code>.env.txt</code>.</li><li>Stop Leafwise with Ctrl+C, then double-click <code>Start-Windows.cmd</code>.</li><li>Return here and choose <strong>Check connection</strong>.</li></ol><p>Keep “Expose my API key” unchecked in your Pl@ntNet account for this server app. An error here identifies a key, quota or network problem; the app never substitutes a local species guess.</p><p><a href="https://my.plantnet.org/settings/api-key" target="_blank" rel="noopener noreferrer">Open Pl@ntNet key settings ↗</a></p>');
}
let diseaseCatalogCache=null;
async function showDiseaseCoverage() {
  showDetail('<h2>Supported conditions</h2><p role="status">Loading the current list from Pl@ntNet. No photos are sent.</p>');
  try{
    const data=diseaseCatalogCache||await requestJson('/api/plantnet/diseases',{method:'POST',signal:AbortSignal.timeout(25000)});
    diseaseCatalogCache=data;
    $('detail-content').innerHTML=`<h2>Supported conditions</h2><p>${escape(data.note)}</p><p>${escape(data.count)} conditions returned by Pl@ntNet.</p><label class="field-label" for="condition-search">Search by name or EPPO code</label><input id="condition-search" type="search" placeholder="Search the provider’s list…"><p id="condition-count" class="field-help" role="status"></p><ul id="condition-list" class="condition-list"></ul>`;
    const render=()=>{const q=$('condition-search').value.trim().toLowerCase();const rows=data.entries.filter(c=>`${c.name} ${c.code} ${c.categories.join(' ')}`.toLowerCase().includes(q));$('condition-count').textContent=`${rows.length} matches${rows.length>150?' · showing the first 150; narrow your search':''}`;$('condition-list').innerHTML=rows.slice(0,150).map(c=>`<li><strong>${escape(c.name)}</strong><br><small>${escape(c.code)}${c.categories.length?' · '+escape(c.categories.join(', ')):''}</small>${c.reference_url?` · <a href="${escape(safeUrl(c.reference_url))}" target="_blank" rel="noopener noreferrer">EPPO reference ↗</a>`:''}</li>`).join('')||'<li>No matching conditions in the returned catalog.</li>';};
    $('condition-search').oninput=render;render();
  }catch(e){$('detail-content').innerHTML=`<h2>Coverage could not be checked</h2><p>${escape(e.name==='TimeoutError'?'The request timed out. Try again.':e.message)}</p><p>This does not establish disease support for your plant.</p>`;}
}
async function loadCatalog() {
  try {catalog=(await requestJson('/api/catalog')).entries || [];const crops=[...new Set(catalog.map(c=>c.crop))];$('guide-crop').innerHTML='<option value="all">All crops</option>'+crops.map(c=>`<option>${escape(c)}</option>`).join('');renderGuide();}catch{$('guide-list').innerHTML='<div class="empty-state"><p>Open the guide once while the server is running to make it available offline.</p></div>';}
}
function renderGuide() {
  const q=$('guide-search').value.toLowerCase().trim(),crop=$('guide-crop').value;
  const entries=catalog.filter(c=>(crop==='all'||c.crop===crop)&&`${c.crop} ${c.name}`.toLowerCase().includes(q));
  $('guide-list').innerHTML=entries.map(c=>`<button class="guide-card" data-guide="${escape(c.id)}"><span class="crop-tag">${escape(c.crop)}</span><h3>${escape(c.name)}</h3><small>${c.healthy?'Monitoring & observation':c.urgency==='prompt'?'Prompt review if spreading':'Signs & first steps'} ↗</small></button>`).join('')||'<div class="empty-state"><p>No matches. Try another crop or condition.</p></div>';
}
function showDetail(html) {$('detail-content').innerHTML=html;$('detail-dialog').showModal();}
let journalUrls=[];
async function updateCount() {try{const rows=await listScans();$('journal-count').textContent=rows.length;$('journal-count').hidden=!rows.length;}catch{}}
async function renderJournal() {
  journalUrls.forEach(u=>URL.revokeObjectURL(u));journalUrls=[];
  try {
    const rows=await listScans();
    $('journal-list').innerHTML=rows.map(row=>{let url='';if(row.thumbnail){url=URL.createObjectURL(row.thumbnail);journalUrls.push(url);}return `<article class="journal-card card">${url?`<img src="${url}" alt="Saved scan photo">`:''}<div class="journal-copy"><time>${escape(dateText(row.created_at))}</time><h3>${escape(titleOf(row.result))}</h3><p>${escape(row.note || 'No field note yet.')}</p><p>${escape(row.result.status.replaceAll('_',' '))}</p></div><div class="journal-buttons"><button class="text-button" data-open="${escape(row.id)}">Open report</button><button class="text-button" data-delete="${escape(row.id)}">Delete</button></div></article>`;}).join('')||'<div class="empty-state"><h2>Your growing story starts here.</h2><p>Scan a leaf and choose “Save to journal” to keep the result and your notes.</p><a href="#scan" class="button primary">Start a leaf scan</a></div>';
    $('export-journal').disabled=!rows.length;
    $('journal-list').onclick=async e=>{
      const open=e.target.closest('[data-open]'),remove=e.target.closest('[data-delete]');
      if(open){const row=rows.find(r=>r.id===open.dataset.open);current=row.result;currentThumb=row.thumbnail;location.hash='scan';renderResult(current,currentThumb,row.note);requestAnimationFrame(()=>$('result').scrollIntoView({block:'start'}));}
      if(remove&&confirm('Delete this saved scan from this browser?')){try{await removeScan(remove.dataset.delete);await renderJournal();await updateCount();toast('Scan deleted.');}catch(e){toast(e.message);}}
    };
  } catch(e) {$('journal-list').innerHTML=`<div class="empty-state"><p>${escape(e.message)}</p></div>`;}
}
function route() {const view=['scan','guide','journal'].includes(location.hash.slice(1))?location.hash.slice(1):'scan';document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==`view-${view}`);document.querySelectorAll('[data-view]').forEach(a=>{a.classList.toggle('active',a.dataset.view===view);if(a.dataset.view===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});if(view==='journal')renderJournal();}

function about() {
  const crops=status?.crops.map(c=>c.name).join(', ') || 'See the installed model status';
  showDetail(`<h2>A little help reading your leaves.</h2><p>Leafwise is a student-project field assistant. The included model screens ${escape(status?.class_count||15)} health classes for ${escape(crops)}. It is trained on curated leaf photographs, and has not been independently validated on local farms.</p><h3>Choose the right health service</h3><p><strong>Online disease and pest identification:</strong> the main health option calls Pl@ntNet’s disease API with your existing key and photo consent. It returns possible conditions and reference codes; coverage is limited. No match does not prove health.</p><h3>The optional starter model</h3><p><strong>Crop health:</strong> a model runs on the computer hosting Leafwise. You must choose and confirm a known crop. The model screens visible condition patterns; it does not identify unknown plants. It cannot identify every plant, reject every non-leaf image, measure disease severity or guarantee that a plant is healthy.</p><p><strong>Plant identity:</strong> optional Pl@ntNet integration returns species candidates. Its variety service covers a limited set of crops. An exact cultivar cannot reliably be inferred from every leaf.</p><h3>Privacy, in plain language</h3><p>Crop photos are processed in memory and are not written to the server's storage. If you run this on your own computer, local crop scanning needs no internet after setup. If someone else hosts it, that server receives your photos. The journal is stored in this browser only, including a small thumbnail when you save. Clearing browser data deletes it; export important records first.</p><p>Plant identity, online health checks and online species verification send resized photos to Pl@ntNet only after you tick the sharing box and submit. Local-only health screening sends no photos to Pl@ntNet. Embedded GPS/EXIF metadata is stripped first. Provider terms apply. No analytics, advertising or location tracking are included.</p><h3>For the website owner</h3><p>In hosted deployments, set <code>PLANTNET_API_KEY</code> in the hosting dashboard and redeploy. For a local installation: create a key at <a href="https://my.plantnet.org/" target="_blank" rel="noopener noreferrer">my.plantnet.org</a>, copy <code>.env.example</code> to <code>.env</code>, set <code>PLANTNET_API_KEY</code>, and restart the app. Keep the key on the server. Quotas and terms depend on your provider account.</p><h3>Language & accessibility</h3><p>Core navigation supports English, Hindi and Gujarati. Detailed guidance and errors currently remain in English. Photos, camera permission and saved records are under your control.</p><h3>Where the information comes from</h3><p>Care cards link to university extension guidance. Ask a local adviser to adapt it to the crop, season and region. Source review: 26 September 2026. No pesticide doses or automated chemical prescriptions are provided.</p><p><a href="https://huggingface.co/imaflower/plantvillage-mobilenetv3" target="_blank" rel="noopener noreferrer">Starter model: imaflower / PlantVillage ↗</a></p>`);
}
async function camera() {
  if(!navigator.mediaDevices?.getUserMedia){$('camera-file').click();return;}
  try {stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1600}},audio:false});$('camera-video').srcObject=stream;$('camera-dialog').showModal();await $('camera-video').play();}
  catch{stopCamera();$('camera-dialog').close();toast('Camera access is unavailable. Choose a photo or use your phone’s camera option.');$('camera-file').click();}
}
function stopCamera(){stream?.getTracks().forEach(t=>t.stop());stream=null;$('camera-video').srcObject=null;}
$('capture').onclick=()=>{const video=$('camera-video');if(!video.videoWidth)return;const canvas=document.createElement('canvas');const factor=Math.min(1,1600/Math.max(video.videoWidth,video.videoHeight));canvas.width=Math.round(video.videoWidth*factor);canvas.height=Math.round(video.videoHeight*factor);canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>{if(blob)addFiles([new File([blob],`leaf-${Date.now()}.jpg`,{type:'image/jpeg'})]);},'image/jpeg',.88);$('camera-dialog').close();stopCamera();};
$('camera-dialog').addEventListener('close',stopCamera);$('camera-dialog').addEventListener('cancel',stopCamera);$('close-camera').onclick=()=>{$('camera-dialog').close();};
document.addEventListener('visibilitychange',()=>{if(document.hidden&&stream){$('camera-dialog').close();stopCamera();}});
$('open-camera').onclick=camera;
$('choose-files').onclick=$('add-more').onclick=()=>$('photos').click();
for(const id of ['photos','camera-file'])$(id).onchange=e=>{addFiles([...e.target.files]);e.target.value='';};
$('photo-grid').onclick=e=>{const button=e.target.closest('[data-remove]');if(button){$('crop-confirmed').checked=false;invalidate();const i=Number(button.dataset.remove);URL.revokeObjectURL(photos[i].url);photos.splice(i,1);renderPhotos();}};
$('photo-grid').onchange=e=>{if(e.target.dataset.organ!==undefined){invalidate();photos[Number(e.target.dataset.organ)].organ=e.target.value;}};
for(const type of ['dragenter','dragover'])$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.add('drag');});
for(const type of ['dragleave','drop'])$('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.remove('drag');if(type==='drop')addFiles([...e.dataTransfer.files]);});
window.addEventListener('dragover',e=>e.preventDefault());window.addEventListener('drop',e=>e.preventDefault());
$('mode-disease').onclick=()=>changeMode('disease');$('mode-identify').onclick=()=>changeMode('identify');
$('crop').onchange=()=>{$('crop-confirmed').checked=false;invalidate();};$('identity-mode').onchange=invalidate;$('consent').onchange=()=>{invalidate();controls();};
$('verification').onchange=$('crop-confirmed').onchange=invalidate;
$('health-engine').onchange=()=>{invalidate();renderPhotos();};$('disease-coverage').onclick=showDiseaseCoverage;
$('identify-first').onclick=()=>changeMode('identify');$('check-provider').onclick=checkProvider;$('provider-help').onclick=providerHelp;
$('analyze').onclick=analyze;$('cancel').onclick=()=>{controller?.abort();};
$('guide-search').oninput=$('guide-crop').onchange=renderGuide;
$('guide-list').onclick=e=>{const b=e.target.closest('[data-guide]');if(b){const guide=catalog.find(c=>c.id===b.dataset.guide);showDetail(`<div class="guide-detail"><span class="crop-tag">${escape(guide.crop)}</span><h2>${escape(guide.name)}</h2>${guideHtml(guide)}<p class="score-note">General education. A field examination may change the diagnosis. Reviewed ${escape(guide.reviewed)}.</p></div>`);}};
$('close-detail').onclick=()=>$('detail-dialog').close();for(const id of ['about-open','footer-about','limitations-open'])$(id).onclick=about;
$('language').onchange=()=>{lang=$('language').value;try{localStorage.setItem('leafwise-language',lang);}catch{}translate(lang);controls();toast(lang==='en'?'Language updated.':'Navigation translated. Detailed guidance remains in English.');};
$('export-journal').onclick=async()=>{try{const scans=await listScans();const exportRows=scans.map(({thumbnail,...row})=>row);download('Leafwise-journal.json',new Blob([JSON.stringify({app:'Leafwise',version:1,exported_at:new Date().toISOString(),note:'Photos excluded. Observation records, not confirmed diagnoses.',scans:exportRows},null,2)],{type:'application/json'}));}catch(e){toast(e.message);}};
window.addEventListener('hashchange',route);window.addEventListener('online',loadStatus);
changeMode(new URLSearchParams(location.search).get('mode')==='health'?'disease':'identify');route();await Promise.allSettled([loadStatus(),loadCatalog(),updateCount()]);
