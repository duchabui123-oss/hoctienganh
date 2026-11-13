/* Tiếng Anh không khó – offline support and fast start.
   The page opens at once from the saved copy; the newest index.html is fetched in the background and,
   when it is a new release, the page shows a "new version" bar. Lesson edits come from Google Sheets,
   so index.html itself only changes when the site gets new features. */
const CACHE = "tanm-app-v3";
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
    const cacheP = caches.open(CACHE), hitP = cacheP.then(c => c.match("index.html"));
    const net = fetch(r.url.split("#")[0], {cache: "no-store"});
    const update = Promise.all([cacheP, hitP, net]).then(async ([c, hit, res]) => {
      if(!res.ok) return;
      const rel = t => (t.match(/"release":\s*\{"v":\s*"([^"]+)"/) || [])[1] || "";
      const [text, old] = await Promise.all([res.clone().text(), hit ? hit.clone().text() : ""]);
      await c.put("index.html", res.clone());
      if(hit && rel(text) && rel(text) !== rel(old)){                  // a new release was uploaded: tell the open page
        const tell = async () => (await self.clients.matchAll({type: "window", includeUncontrolled: true})).forEach(x => x.postMessage({type: "new-version", v: rel(text)}));
        await tell(); await new Promise(ok => setTimeout(ok, 3000)); await tell();
      }
    }).catch(() => {});
    e.waitUntil(update);
    e.respondWith(hitP.then(hit => hit ? hit.clone() : net.then(res => res.clone()).catch(() => caches.match("./"))));   // instant start from the saved copy
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
