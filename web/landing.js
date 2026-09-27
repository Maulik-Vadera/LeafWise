import './install.js';
// Preserve bookmarks and previously installed v1.0/v1.1 start URLs.
if (['#scan','#journal','#guide'].includes(location.hash)) location.replace('/app'+location.hash);
const privacy=document.getElementById('privacy');
const revealPrivacy=()=>{if(location.hash==='#privacy')privacy.open=true;};
window.addEventListener('hashchange',revealPrivacy);
document.getElementById('privacy-link').addEventListener('click',()=>{privacy.open=true;});
revealPrivacy();
