// 인터넷 없이 읽기: 한 번 연 페이지와 책 본문을 이 기기에 저장해 둡니다.
// 인터넷이 되면 늘 새 내용을 먼저 받고(그리고 저장), 안 되면 저장해 둔 것을 보여 줍니다.
const CACHE = 'dd-offline-v2';
const CORE = ['/', '/library/', '/mynotes/', '/offline.html', '/assets/site.css', '/assets/app.js', '/images/icon.svg', '/images/logo.png', '/data/site.json'];
const SKIP = /^\/(admin|api|download|members|study|cdn-cgi)(\/|$)/;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('dd-offline-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// /read/DL-0007/30 처럼 쪽 번호가 붙은 주소는 같은 읽기 화면(/read/DL-0007/)으로 저장
const keyOf = url => {
  const m = url.pathname.match(/^\/read\/(DL-\d{4})\/\d+$/);
  if (m) return new URL(`/read/${m[1]}/`, url.origin).href;
  return url.origin + url.pathname + (url.pathname.startsWith('/assets/') ? url.search : '');
};
const FONT = /^https:\/\/fonts\.(googleapis|gstatic)\.com$/;

self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (FONT.test(url.origin)) { // 글꼴: 저장해 둔 것을 먼저
    e.respondWith(caches.open(CACHE).then(async c => (await c.match(req)) || fetch(req).then(r => { c.put(req, r.clone()); return r; })));
    return;
  }
  if (url.origin !== location.origin || SKIP.test(url.pathname)) return;
  if (url.pathname.startsWith('/assets/') && url.search) { // 버전이 붙은 디자인·동작 파일: 저장해 둔 것을 먼저
    e.respondWith(caches.open(CACHE).then(async c => (await c.match(keyOf(url))) || fetch(req).then(r => { if (r.ok) c.put(keyOf(url), r.clone()); return r; })));
    return;
  }
  e.respondWith((async () => {
    const c = await caches.open(CACHE), key = keyOf(url);
    try {
      const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 6000);
      const r = await fetch(req, { signal: ctl.signal }); clearTimeout(to);
      if (r.ok && (r.type === 'basic' || r.type === 'default')) c.put(key, r.clone());
      return r;
    } catch (err) {
      const hit = await c.match(key) || await c.match(key, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === 'navigate') return (await c.match(location.origin + '/offline.html')) || Response.error();
      return Response.error();
    }
  })());
});
