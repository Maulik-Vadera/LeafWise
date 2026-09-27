const CACHE='leafwise-shell-v1.3.0';
const SHELL=['/','/index.html','/app','/scanner.html','/landing.css','/landing.js','/styles.css','/app.js','/photos.js','/install.js','/install.css','/journal.js','/i18n.js','/botanical.svg','/icon.svg','/icon-192.png','/icon-512.png','/manifest.webmanifest'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('leafwise-shell-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==self.location.origin)return;
  const path=url.pathname==='/app/'?'/app':url.pathname;
  // No photo, prediction, status, key-check or disease-service response is cached.
  if(!SHELL.includes(path)&&path!=='/api/catalog')return;
  event.respondWith((async()=>{
    try {const response=await fetch(event.request);if(response.ok){const cache=await caches.open(CACHE);await cache.put(path,response.clone());}return response;}
    catch {const cache=await caches.open(CACHE);return await cache.match(path)||new Response('Connect to Leafwise once to prepare offline browsing.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}
  })());
});
