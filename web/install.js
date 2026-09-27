// Shared browser installation flow. Installation is always initiated by a click.
let promptEvent = null;
let prompting = false;
const standalone = matchMedia('(display-mode: standalone)');
let installed = standalone.matches || navigator.standalone === true;
const buttons = [...document.querySelectorAll('[data-install]')];
const originalLabels = new Map(buttons.map(button=>[button,button.innerHTML]));
const statusNodes = [...document.querySelectorAll('[data-install-status]')];
const dialog = document.createElement('dialog');
dialog.id = 'install-dialog';
dialog.className = 'lw-install-dialog';
dialog.setAttribute('aria-labelledby', 'install-dialog-title');
dialog.innerHTML = `<div class="lw-install-heading"><img src="/icon-192.png" width="48" height="48" alt=""><button type="button" class="lw-install-close" aria-label="Close installation help">×</button></div>
<h2 id="install-dialog-title">Keep Leafwise close.</h2><p class="lw-install-intro">Your browser can add Leafwise to your home screen or desktop. If installation isn’t offered, you can keep using the website.</p>
<p id="install-context" class="lw-install-context" role="status"></p>
<ol class="lw-install-methods"><li data-platform="ios"><strong>iPhone or iPad</strong><span>Open the browser’s Share menu, then choose <b>Add to Home Screen</b>. If needed, open this link in Safari. Enable <b>Open as Web App</b> if offered, then tap Add.</span></li><li data-platform="android"><strong>Android</strong><span>In Chrome, open the three-dot menu and choose <b>Install app</b> or <b>Add to home screen</b>.</span></li><li data-platform="desktop"><strong>Windows, Mac or Linux</strong><span>In Chrome or Edge, use the install icon in the address bar, or the browser menu’s install option. On supported Macs, Safari also offers <b>File → Add to Dock</b>.</span></li></ol>
<p class="lw-install-note">Online scans need internet. Your saved journal stays in this browser and does not sync across devices. This release installs from the web; there is no APK download.</p><a class="lw-install-open" href="/app#scan">Open Leafwise →</a>`;
document.body.append(dialog);
dialog.querySelector('.lw-install-close').onclick = () => dialog.close();
dialog.addEventListener('click', event => {if (event.target === dialog) {const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
const ua = navigator.userAgent;
const platform = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) ? 'ios' : /Android/i.test(ua) ? 'android' : 'desktop';
const preferred = dialog.querySelector(`[data-platform="${platform}"]`);
preferred.parentElement.prepend(preferred);
preferred.classList.add('lw-install-preferred');
function announce(message) {statusNodes.forEach(node => {node.textContent=message;});dialog.querySelector('#install-context').textContent=message;}
function update() {buttons.forEach(button => {button.disabled=installed||prompting;if(installed)button.textContent='App installed';else button.innerHTML=originalLabels.get(button);});}
function help() {
  const message = installed ? 'Leafwise is already running as an installed app.' : !window.isSecureContext ? 'Installation needs the secure HTTPS version of this website. Open the published website, then try again.' : 'If your browser shows an install option, follow the steps for your device below.';
  announce(message);if(!dialog.open)dialog.showModal();
}
window.addEventListener('beforeinstallprompt', event => {event.preventDefault();promptEvent=event;update();});
window.addEventListener('appinstalled', () => {installed=true;promptEvent=null;update();announce('Leafwise is installed. Look for its leaf icon on your home screen or in your apps.');if(dialog.open)dialog.close();});
standalone.addEventListener('change', event => {installed=event.matches||navigator.standalone===true;update();});
buttons.forEach(button => button.addEventListener('click', async () => {
  if (!promptEvent) {help();return;}
  const event=promptEvent;promptEvent=null;prompting=true;update();
  try {await event.prompt();const choice=await event.userChoice;announce(choice.outcome==='accepted'?'Installation requested. Your browser will confirm when it finishes.':'Installation dismissed. You can still use Leafwise in your browser.');}
  catch {help();}
  finally {prompting=false;update();}
}));
update();
if(installed)announce('You’re using the installed Leafwise app. Online scans still need internet.');
if ('serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.register('/sw.js', {scope:'/'}).catch(() => {announce('Offline preparation did not finish. You can still use Leafwise online.');});
}
