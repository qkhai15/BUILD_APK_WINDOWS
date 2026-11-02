// Only cache the application shell. Sensitive API responses and student data are NEVER cached.
const CACHE='thd-static-brand-photo-v07';
const STATIC=['/app/','/app/index.html','/app/style.css','/app/app.js','/app/manifest.webmanifest','/app/icons/icon-192.png','/app/icons/icon-512.png'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 if(event.request.method!=='GET'||url.origin!==location.origin||!url.pathname.startsWith('/app/'))return;
 // Network first for HTML/app code, cache fallback for app shell only.
 event.respondWith(fetch(event.request).then(response=>{
   if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}
   return response;
 }).catch(()=>caches.match(event.request)));
});
