/* Tiếng Anh Nhà Mình – offline support. Lessons open without internet after the first visit;
   when online, the newest index.html on the hosting is always fetched first. */
const CACHE = "tanm-app-v2";
const CORE = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const r = e.request; if(r.method !== "GET") return;
  const url = new URL(r.url);
  if(/\/(api\.php|config\.json)$/.test(url.pathname)) return;          // exercise results always go straight to the hosting
  const page = r.mode === "navigate" || (url.origin === location.origin && /(\/|\.html)$/.test(url.pathname));
  if(page){
    // network first: new content uploaded to the hosting shows up right away
    e.respondWith(fetch(r, {cache: "no-store"}).then(res => {
      if(res.ok){ const cp = res.clone(); caches.open(CACHE).then(c => c.put("index.html", cp)); }
      return res;
    }).catch(() => caches.match("index.html").then(m => m || caches.match("./"))));
    return;
  }
  if(/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname) || url.origin === location.origin){
    // fonts and icons: use the saved copy, refresh it in the background
    e.respondWith(caches.open(CACHE).then(c => c.match(r).then(hit => {
      const net = fetch(r).then(res => { if(res.ok || res.type === "opaque") c.put(r, res.clone()); return res; }).catch(() => hit);
      return hit || net;
    })));
  }
});
