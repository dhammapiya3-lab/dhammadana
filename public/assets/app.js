/* 테라와다불교 법보시 도서관 — 화면 동작
   - 화면 모드, 페이지 사이 부드러운 이동(법문 재생이 끊기지 않도록), 도서관 찾아보기, 검색(표기 사전), 읽기 화면, 내 서재, 법문 재생기 */
(function () {
'use strict';
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  get(k, d) { try { const v = localStorage.getItem('dd-' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('dd-' + k, JSON.stringify(v)); } catch (e) {} }
};
const SITE = 'dhammadana.kr';
function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('show'); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 2800); }
function copy(text, msg) { (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => toast(msg)).catch(() => toast('복사할 수 없는 환경입니다. 길게 눌러 직접 복사해 주세요')); }
const today = () => new Date().toLocaleDateString('sv-SE');

/* ---------- 사이트 자료 (검색·서재) ---------- */
let DATA = null;
function data() { return DATA || (DATA = fetch('/data/site.json').then(r => r.json())); }
const manifests = {};
function manifest(url) { return manifests[url] || (manifests[url] = fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })); }

/* 글자 맞추기: 빨리어 점·막대 없애고 한글은 붙여서 비교 */
const norm = s => String(s || '').normalize('NFD').replace(/[̀-̣̱ͯ̇]/g, '').normalize('NFC').toLowerCase().replace(/\s+/g, ' ').trim();

/* ---------- 화면 모드 ---------- */
function applyMode(m) {
  const r = document.documentElement; r.classList.remove('mode-day', 'mode-mono', 'mode-night');
  if (m !== 'auto') r.classList.add('mode-' + m);
  store.set('mode', m); $$('#modePop button').forEach(b => b.classList.toggle('on', b.dataset.mode === m));
}
function initHeader() {
  const btn = $('#modeBtn'), pop = $('#modePop');
  btn.onclick = e => { e.stopPropagation(); const o = pop.classList.toggle('open'); btn.setAttribute('aria-expanded', o); };
  $$('button', pop).forEach(b => b.onclick = () => { applyMode(b.dataset.mode); pop.classList.remove('open'); btn.setAttribute('aria-expanded', false); });
  document.addEventListener('click', () => pop.classList.remove('open'));
  applyMode(store.get('mode', 'auto'));
}

/* ---------- 부드러운 이동 (재생기 유지) ---------- */
function sameSite(a) {
  if (!a || a.target || a.hasAttribute('download') || a.origin !== location.origin) return false;
  if (/^\/(admin|uploads|data)\b/.test(a.pathname) || /\.[a-z0-9]{2,5}$/i.test(a.pathname)) return false;
  return true;
}
async function softGo(url, push = true) {
  try {
    const r = await fetch(url, { headers: { accept: 'text/html' } });
    const html = await r.text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const nm = doc.querySelector('main#app'); if (!nm) throw new Error('no main');
    closeReader();
    $('#app').replaceWith(document.adoptNode(nm));
    document.title = doc.title;
    const nav = nm.dataset.nav;
    $$('nav.main a').forEach(a => { const on = a.dataset.nav === nav; a.classList.toggle('on', on); on ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'); });
    document.body.dataset.page = nm.dataset.page;
    if (push) history.pushState({}, '', url);
    const u = new URL(url, location.href);
    if (u.hash && $(u.hash)) $(u.hash).scrollIntoView(); else window.scrollTo(0, 0);
    initPage();
  } catch (e) { location.href = url; }
}
document.addEventListener('click', e => {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = e.target.closest('a[href]'); if (!sameSite(a)) return;
  if (a.pathname === location.pathname && a.search === location.search && a.hash) return;
  // 재생 중일 때만 부드럽게 이동 (그 밖에는 보통 이동이 더 단순하고 안전)
  if (!PL.pl || $('#pAudio').paused) return;
  e.preventDefault(); softGo(a.href);
});
window.addEventListener('popstate', () => { if (PL.pl && !$('#pAudio').paused) softGo(location.href, false); else location.reload(); });

/* ---------- 페이지별 시작 ---------- */
function initPage() {
  const p = $('#app').dataset.page;
  if (p === 'library') initLibrary();
  if (p === 'search') initSearch();
  if (p === 'talks') initTalks();
  if (p === 'mynotes') renderNotes();
  if (p === 'reader') initReaderPage();
  if (p === 'book') initBook();
  $$('[data-permit]').forEach(b => b.onclick = () => lightbox(b.dataset.permit, b.dataset.title));
}

/* ---------- 허락서 보기 ---------- */
function zoomView(html, title) {
  const d = document.createElement('div'); d.className = 'lightbox zoomer'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', title);
  d.innerHTML = `<div class="lb-bar"><span>${esc(title)}</span><span class="zm"><button class="tbtn" data-z="-1" aria-label="작게">−</button><button class="tbtn" data-z="1" aria-label="크게">+</button></span><button class="tbtn" id="lbClose">닫기 ✕</button></div><div class="lb-wrap"><div class="zoom-in" style="--z:1">${html}</div></div>`;
  document.body.appendChild(d); let z = 1; const zi = $('.zoom-in', d);
  $$('[data-z]', d).forEach(b => b.onclick = () => { z = Math.max(0.5, Math.min(4, z + (+b.dataset.z) * 0.25)); zi.style.setProperty('--z', z); });
  const close = () => d.remove(); $('#lbClose', d).onclick = close; d.onclick = e => { if (e.target === d || e.target.classList.contains('lb-wrap')) close(); };
  document.addEventListener('keydown', function k(e) { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', k); } });
}
function lightbox(src, title) {
  const d = document.createElement('div'); d.className = 'lightbox'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', '허락서');
  d.innerHTML = `<div class="lb-bar"><span>『${esc(title)}』 게시 허락서</span><a href="${esc(src)}" target="_blank" rel="noopener" style="color:#f3eee3">원본 열기 ↗</a><button class="tbtn" id="lbClose">닫기 ✕</button></div><div class="lb-wrap"><img src="${esc(src)}" alt="게시 허락서"></div>`;
  document.body.appendChild(d);
  const close = () => d.remove();
  $('#lbClose', d).onclick = close; d.onclick = e => { if (e.target === d) close(); };
  $('img', d).onclick = e => e.target.classList.toggle('big');
  document.addEventListener('keydown', function k(e) { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', k); } });
}

/* ---------- 도서관 찾아보기 ---------- */
function initLibrary() {
  const q = new URLSearchParams(location.search);
  const want = { trad: q.getAll('trad'), teacher: q.getAll('teacher'), topic: q.getAll('topic'), main: q.getAll('main'), fmt: q.getAll('fmt'), lang: q.getAll('lang') };
  $$('.filters input[data-f]').forEach(c => { if ((want[c.dataset.f] || []).includes(c.value)) c.checked = true; });
  const showEmpty = $('#showEmpty');
  showEmpty.checked = store.get('showEmpty', false);
  const run = () => {
    const sel = {}; $$('.filters input[data-f]:checked').forEach(c => (sel[c.dataset.f] = sel[c.dataset.f] || []).push(c.value));
    // 전통을 고르면 스승 목록 펼치기
    $$('[data-trad-block]').forEach(bl => {
      const on = $('input[data-f=trad]', bl).checked || $$('input[data-f=teacher]:checked', bl).length > 0;
      $('.sub', bl).hidden = !on;
      bl.hidden = bl.classList.contains('empty') && !showEmpty.checked && !on;
    });
    $$('.trad-region').forEach(g => { let n = g.nextElementSibling, any = false; while (n && n.matches('[data-trad-block]')) { if (!n.hidden) any = true; n = n.nextElementSibling; } g.hidden = !any; });
    const books = $$('#libGrid .book');
    let shown = 0;
    for (const b of books) {
      const has = (k, list) => !list || list.some(v => (b.dataset[k] || '').split('|').includes(v));
      let ok = has('main', sel.main) && has('topics', sel.topic) && has('fmts', sel.fmt) && has('lang', sel.lang);
      // 전통과 스승은 '또는'으로 묶음
      if (ok && (sel.trad || sel.teacher)) ok = (sel.trad || []).includes(b.dataset.trad) || (sel.teacher || []).includes(b.dataset.teacher);
      b.hidden = !ok; if (ok) shown++;
    }
    $('#libCount').textContent = shown; $('#libEmpty').hidden = shown > 0;
    const af = $('#activeFilters');
    const chips = $$('.filters input[data-f]:checked').map(c => `<button data-un="${esc(c.dataset.f)}|${esc(c.value)}">${esc(c.parentElement.firstChild.nextSibling.textContent)} ✕</button>`);
    af.innerHTML = chips.length ? chips.join('') + `<button data-un="*">모두 지우기</button>` : '';
    $$('button', af).forEach(x => x.onclick = () => { const [f, v] = x.dataset.un.split('|'); $$('.filters input[data-f]').forEach(c => { if (x.dataset.un === '*' || (c.dataset.f === f && c.value === v)) c.checked = false; }); run(); sync(); });
  };
  const sync = () => {
    const p = new URLSearchParams(); $$('.filters input[data-f]:checked').forEach(c => p.append(c.dataset.f, c.value));
    history.replaceState(history.state, '', location.pathname + (p.toString() ? '?' + p : ''));
  };
  const sortBy = () => {
    const g = $('#libGrid'), v = $('#sort').value;
    $$('.book', g).sort((a, b) => v === 'title' ? a.dataset.title.localeCompare(b.dataset.title, 'ko') : (b.dataset.added || '').localeCompare(a.dataset.added || '')).forEach(x => g.appendChild(x));
  };
  $$('.filters input[data-f]').forEach(c => c.onchange = () => { run(); sync(); });
  showEmpty.onchange = () => { store.set('showEmpty', showEmpty.checked); run(); };
  $('#sort').onchange = sortBy;
  if (window.innerWidth < 520) $('.filter-toggle').open = false;
  run();
}

/* ---------- 검색 ---------- */
let exact = false;
function expand(q, V) {
  const nq = norm(q); if (!nq) return { terms: [], group: null };
  if (exact) return { terms: [nq], group: null };
  const g = V.find(v => v.some(x => norm(x) === nq)) || V.find(v => v.some(x => norm(x).length >= 2 && nq.includes(norm(x))));
  if (!g) return { terms: [nq], group: null };
  const hit = g.find(x => norm(x) === nq) || g.find(x => nq.includes(norm(x)));
  const terms = new Set([nq]);
  g.forEach(x => terms.add(nq === norm(hit) ? norm(x) : nq.split(norm(hit)).join(norm(x))));
  return { terms: [...terms], group: g };
}
function hl(text, terms) {
  const nt = norm(text);
  // norm 은 글자 수를 바꿀 수 있어 원문과 위치가 같을 때만 정확히 표시
  if (nt.length !== text.length) {
    let out = esc(text);
    terms.forEach(t => { if (t) out = out.replace(new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), m => `<mark>${m}</mark>`); });
    return out;
  }
  const rg = []; terms.forEach(t => { let i = 0; while (t && (i = nt.indexOf(t, i)) > -1) { rg.push([i, i + t.length]); i += t.length; } });
  if (!rg.length) return esc(text);
  rg.sort((a, b) => a[0] - b[0]); let out = '', p = 0;
  rg.forEach(([a, b]) => { if (a < p) return; out += esc(text.slice(p, a)) + '<mark>' + esc(text.slice(a, b)) + '</mark>'; p = b; });
  return out + esc(text.slice(p));
}
function snippet(text, terms) {
  const nt = norm(text); let at = -1;
  for (const t of terms) { const i = nt.indexOf(t); if (i > -1 && (at < 0 || i < at)) at = i; }
  if (at < 0) return '';
  const s = Math.max(0, at - 50), e = Math.min(text.length, at + 90);
  return (s > 0 ? '… ' : '') + text.slice(s, e).trim() + (e < text.length ? ' …' : '');
}
async function initSearch() {
  const q = new URLSearchParams(location.search);
  $('#sq').value = q.get('q') || ''; $('#scope').value = q.get('scope') || 'all';
  exact = q.get('exact') === '1';
  $('#sForm').onsubmit = e => { e.preventDefault(); const p = new URLSearchParams({ q: $('#sq').value.trim(), scope: $('#scope').value }); if (exact) p.set('exact', '1'); history.replaceState(null, '', '/search/?' + p); runSearch(); };
  if ($('#sq').value) runSearch(); else $('#sq').focus();
}
async function runSearch() {
  const box = $('#sResult'), q = $('#sq').value.trim(), scope = $('#scope').value;
  if (!q) return;
  box.innerHTML = '<p class="muted">찾는 중…</p>';
  const D = await data();
  const { terms, group } = expand(q, D.variants);
  const has = s => { const n = norm(s); return terms.some(t => n.includes(t)); };
  const res = [];
  for (const b of D.books) {
    const why = [];
    if ((scope === 'all' || scope === 'title') && [b.title, b.subtitle, b.orig].some(has)) why.push('제목');
    if (scope === 'all' && b.lang && has(b.lang) && !why.length) why.push('원서 언어');
    if ((scope === 'all' || scope === 'author') && [b.byline, b.teacher, b.teacherRoman, b.tradition, ...(b.teacherAliases || [])].some(has)) why.push('스승·저자');
    if ((scope === 'all' || scope === 'tr') && has(b.tr)) why.push('옮긴이');
    if ((scope === 'all' || scope === 'topic') && [...b.topics, ...b.main].some(has)) why.push('주제');
    let body = [];
    if ((scope === 'all' || scope === 'body') && b.manifest) {
      try { const m = await manifest(b.manifest); body = (m.pages || []).map((p, i) => ({ ...p, n: i + 1 })).filter(p => p.text && has(p.text)).slice(0, 5).map(p => ({ n: p.n, label: p.label ? p.label + '쪽' : p.n + '번째 쪽', s: snippet(p.text, terms) })); } catch (e) {}
      if (body.length) why.push('본문');
    }
    if ((scope === 'all') && has(b.desc) && !why.length) why.push('소개');
    if (why.length) res.push({ b, why, body });
  }
  const hq = encodeURIComponent(terms.join('|'));
  box.innerHTML = (group ? `<div class="variant-note"><span>‘${esc(q)}’와 같은 말인 ${group.filter(x => norm(x) !== norm(q)).map(x => `‘${esc(x)}’`).join(', ')}도 함께 찾았습니다.</span><button id="exactBtn">입력한 표기만 찾기</button></div>`
      : exact ? `<div class="variant-note"><span>입력한 표기 ‘${esc(q)}’만 찾았습니다.</span><button id="exactBtn">비슷한 표기도 찾기</button></div>` : '')
    + `<p class="small muted" style="margin:14px 0 4px">${res.length}권을 찾았습니다.</p>`
    + (res.length ? res.map(({ b, why, body }) => `<div class="hit"><a class="h-t" href="/book/${b.id}/">${hl(b.title, terms)}</a>
      <div class="h-m">${hl(b.byline, terms)}${b.tr ? ' | ' + hl(b.tr, terms) : ''} · <span class="pill">${why.join(' · ')}</span></div>
      ${[...b.topics].some(t => terms.some(x => norm(t).includes(x))) ? `<div class="h-m">주제: ${b.topics.map(t => hl(t, terms)).join(', ')}</div>` : ''}
      ${body.map(x => `<div class="h-s"><a href="/read/${b.id}/${x.n}?hl=${hq}">${esc(x.label)}</a> ${hl(x.s, terms)}</div>`).join('')}</div>`).join('')
      : `<p class="muted">찾는 자료가 없습니다. 다른 표기나 더 짧은 말로 찾아보세요. <a href="/library/">도서관에서 둘러보기 →</a></p>`);
  const eb = $('#exactBtn'); if (eb) eb.onclick = () => { exact = !exact; runSearch(); };
}

/* ---------- 화면 켜 두기 (휴대폰에서 소리가 끊기지 않도록) ---------- */
const WAKE = { lock: null, want: new Set() };
async function wake(on, who) {
  on ? WAKE.want.add(who) : WAKE.want.delete(who);
  try {
    if (WAKE.want.size && !WAKE.lock && 'wakeLock' in navigator) { WAKE.lock = await navigator.wakeLock.request('screen'); WAKE.lock.addEventListener('release', () => { WAKE.lock = null; }); }
    if (!WAKE.want.size && WAKE.lock) { await WAKE.lock.release(); WAKE.lock = null; }
  } catch (e) {}
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && WAKE.want.size) wake(true, [...WAKE.want][0]); });

/* ---------- 법문 재생기 ---------- */
const PL = { pl: null, i: 0, list: [] };
const fmtT = s => { if (!isFinite(s)) return '0:00'; s = Math.floor(s); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = String(s % 60).padStart(2, '0'); return h ? `${h}:${String(m).padStart(2, '0')}:${x}` : `${m}:${x}`; };
function epList(plId) { return $$(`[data-epl="${CSS.escape(plId)}"]`).map(e => ({ audio: e.dataset.audio, title: e.dataset.title, plname: e.dataset.plname })); }
function playEp(plId, i, list) {
  list = list || epList(plId); if (!list[i]) return;
  PL.pl = plId; PL.i = i; PL.list = list;
  const e = list[i], a = $('#pAudio');
  a.src = e.audio; a.playbackRate = +$('#pRate').value;
  const pos = store.get('ppos-' + e.audio, 0);
  a.onloadedmetadata = () => { if (pos > 5 && pos < a.duration - 5) a.currentTime = pos; };
  a.play().catch(() => toast('재생 단추를 한 번 더 눌러 주세요'));
  $('#player').classList.add('show'); document.body.classList.add('has-player');
  $('#pTitle').innerHTML = `${esc(e.title)}<small>${esc(e.plname)}</small>`;
  store.set('plast', { pl: plId, i, list });
  markEp(); setMedia(e);
}
// 잠금 화면·이어폰 단추에서 조절 (휴대폰 잠금 화면, 컴퓨터 미디어 키)
function setMedia(e) {
  if (!('mediaSession' in navigator)) return;
  try {
    navigator.mediaSession.metadata = new MediaMetadata({ title: e.title, artist: e.plname, album: '테라와다불교 법보시 도서관 · 법문 바로 듣기', artwork: [{ src: '/images/og.jpg', sizes: '1200x630', type: 'image/jpeg' }] });
  } catch (x) {}
}
function initPlayer() {
  const a = $('#pAudio');
  $('#pRate').value = String(store.get('prate', 1));
  $('#pAuto').checked = store.get('pauto', true);
  $('#pPlay').onclick = () => { if (PL.locked) return; if (!PL.pl) { const l = store.get('plast'); if (l) playEp(l.pl, l.i, l.list); return; } a.paused ? a.play() : a.pause(); };
  $('#pNext').onclick = () => { if (PL.pl && PL.i < PL.list.length - 1) playEp(PL.pl, PL.i + 1, PL.list); };
  $('#pPrev').onclick = () => { if (!PL.pl) return; if (a.currentTime > 3) a.currentTime = 0; else if (PL.i > 0) playEp(PL.pl, PL.i - 1, PL.list); };
  $('#pSeek').oninput = e => { if (a.duration) a.currentTime = a.duration * e.target.value / 100; };
  $('#pRate').onchange = e => { a.playbackRate = +e.target.value; store.set('prate', +e.target.value); };
  $('#pAuto').onchange = e => store.set('pauto', e.target.checked);
  $('#pHide').onclick = () => { if (PL.locked) return lockedMsg(); a.pause(); $('#player').classList.remove('show'); document.body.classList.remove('has-player'); };
  // 잠금: 실수로 멈추거나 넘기지 않도록 (잠그면 화면도 켜 둠)
  const lockedMsg = () => toast('잠겨 있습니다. 🔒 잠금 단추를 눌러 풀어 주세요');
  const setLock = on => {
    PL.locked = on; $('#player').classList.toggle('locked', on);
    $('#pLock').textContent = on ? '🔒 잠김' : '🔓 잠금'; $('#pLock').setAttribute('aria-pressed', on);
    ['#pPrev', '#pPlay', '#pNext', '#pSeek', '#pRate'].forEach(x => { $(x).disabled = on; });
    wake(on && !a.paused, 'player');
  };
  $('#pLock').onclick = () => setLock(!PL.locked);
  if ('mediaSession' in navigator) {
    const ms = navigator.mediaSession, h = (k, f) => { try { ms.setActionHandler(k, f); } catch (e) {} };
    h('play', () => a.play());
    h('pause', () => { if (PL.locked) return; a.pause(); });
    h('previoustrack', () => { if (!PL.locked) $('#pPrev').onclick(); });
    h('nexttrack', () => { if (!PL.locked) $('#pNext').onclick(); });
    h('seekto', d => { if (!PL.locked && d.seekTime != null) a.currentTime = d.seekTime; });
  }
  let last = 0;
  a.ontimeupdate = () => {
    $('#pCur').textContent = fmtT(a.currentTime); $('#pDur').textContent = fmtT(a.duration);
    if (a.duration) $('#pSeek').value = a.currentTime / a.duration * 100;
    if (PL.pl && Date.now() - last > 3000) { last = Date.now(); store.set('ppos-' + PL.list[PL.i].audio, a.currentTime); }
  };
  a.onplay = () => { $('#pPlay').textContent = '❚❚'; $('#pPlay').setAttribute('aria-label', '일시정지'); };
  a.onpause = () => {
    $('#pPlay').textContent = '▶'; $('#pPlay').setAttribute('aria-label', '재생');
    // 잠겨 있는데 저절로 멈추면(이어폰 빠짐 등) 다시 재생
    if (PL.locked && !a.ended && a.src) setTimeout(() => { if (PL.locked && a.paused && !a.ended) a.play().catch(() => {}); }, 400);
    else wake(false, 'player');
  };
  a.addEventListener('play', () => { if (PL.locked) wake(true, 'player'); });
  a.onended = () => { if (PL.pl) store.set('ppos-' + PL.list[PL.i].audio, 0); if ($('#pAuto').checked && PL.pl && PL.i < PL.list.length - 1) playEp(PL.pl, PL.i + 1, PL.list); };
  a.onerror = () => { if (a.src) toast('이 법문을 불러오지 못했습니다. 다음 법문을 골라 주세요'); };
}
function initTalks() {
  const q = new URLSearchParams(location.search);
  const ids = $$('.pl').map(b => b.dataset.pl);
  let cur = q.get('pl') || store.get('pl', ids[0]); if (!ids.includes(cur)) cur = ids[0];
  const showSub = key => {
    const pl = key.split(':')[0];
    $$(`[data-panel="${CSS.escape(pl)}"] [data-sub]`).forEach(c => { const on = c.dataset.sub === key; c.classList.toggle('on', on); c.setAttribute('aria-selected', on); });
    $$(`[data-panel="${CSS.escape(pl)}"] .sub-panel`).forEach(x => x.hidden = x.dataset.subpanel !== key);
    store.set('sub-' + pl, key);
    const u = new URL(location.href); u.searchParams.set('pl', pl); u.searchParams.set('sub', key.split(':')[1]); history.replaceState(history.state, '', u);
  };
  const show = id => {
    cur = id; store.set('pl', id);
    $$('.pl').forEach(b => b.classList.toggle('on', b.dataset.pl === id));
    $$('.pl-panel').forEach(p => p.hidden = p.dataset.panel !== id);
    const want = q.get('pl') === id && q.get('sub') ? `${id}:${q.get('sub')}` : store.get('sub-' + id, `${id}:all`);
    showSub($(`[data-subpanel="${CSS.escape(want)}"]`) ? want : `${id}:all`);
  };
  $$('.pl').forEach(b => b.onclick = () => show(b.dataset.pl));
  $$('[data-sub]').forEach(c => c.onclick = () => showSub(c.dataset.sub));
  $$('.ep').forEach(e => { const go = () => playEp(e.dataset.epl, +e.dataset.ep); e.onclick = go; e.onkeydown = k => { if (k.key === 'Enter' || k.key === ' ') { k.preventDefault(); go(); } }; });
  $$('[data-playall]').forEach(b => b.onclick = () => playEp(b.dataset.playall, 0));
  // 스크롤하면 50개씩 더 보이기
  const more = btn => { const panel = btn.closest('.sub-panel'); $$('[data-later][hidden]', panel).slice(0, 50).forEach(x => x.hidden = false); if (!$('[data-later][hidden]', panel)) btn.parentElement.remove(); };
  $$('[data-more]').forEach(btn => {
    btn.onclick = () => more(btn);
    if ('IntersectionObserver' in window) new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting && btn.isConnected && !btn.closest('[hidden]')) more(btn); }), { rootMargin: '400px' }).observe(btn);
  });
  if (cur) show(cur);
  markEp();
}
function markEp() {
  $$('.ep').forEach(x => {
    const on = x.dataset.epl === PL.pl && +x.dataset.ep === PL.i; x.classList.toggle('on', on);
    if (on && x.hidden) { x.hidden = false; }
  });
}
/* ---------- 책 상세: 목차 ---------- */
async function initBook() {
  const m = $('#tocMount'); if (!m) return;
  try {
    const man = await manifest(m.dataset.manifest);
    if (man.toc && man.toc.length) m.innerHTML = `<ol class="toc">${man.toc.map(t => `<li class="${/^\s/.test(t.title) ? 'sub' : ''}"><a href="/read/${m.dataset.book}/${t.page}?view=text">${esc(t.title.trim())}</a><span>${esc(t.label || t.page)}</span></li>`).join('')}</ol><p class="small muted" style="margin-top:8px">목차를 누르면 그 장을 읽을 수 있습니다.</p>`;
  } catch (e) {}
}

/* ---------- 읽기 화면 ---------- */
let R = null;
const bms = () => store.get('bm', []);
const uls = () => store.get('ul', []);
async function initReaderPage() {
  const root = $('#readerRoot'); if (!root) return;
  const id = root.dataset.book;
  const seg = location.pathname.split('/').filter(Boolean); const want = +seg[2] || 0;
  const hlp = new URLSearchParams(location.search).get('hl');
  let man;
  try { man = await manifest(root.dataset.manifest); }
  catch (e) { root.innerHTML = `<div class="wrap prose"><h1>${esc(root.dataset.title)}</h1><p>읽기 자료를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.</p><p><a href="/book/${id}/">← 책 정보로 돌아가기</a></p></div>`; return; }
  const base = root.dataset.manifest.replace(/[^/]+$/, '');
  const pages = man.pages.map((p, i) => ({ n: i + 1, label: p.label || '', img: p.img ? base + p.img : '', big: p.big ? base + p.big : '', w: p.w, h: p.h, text: p.text || '' }));
  const last = store.get('pos-' + id, 1);
  R = {
    id, title: root.dataset.title, by: root.dataset.teacher || root.dataset.byline, pages, toc: man.toc || [],
    i: Math.min(Math.max(want || (last > 1 ? last : 0) || firstContent(pages, man.toc || []), 1), pages.length) - 1,
    view: 'text', zoom: store.get('rzoom', 1), fs: store.get('rfs', 1), lh: store.get('rlh', 1.9), font: store.get('rfont', 'serif'), mw: store.get('rmw', 36),
    hl: hlp ? hlp.split('|').filter(Boolean) : [], speaking: false
  };
  if (!pages.some(p => p.text)) R.view = 'page';
  renderReader();
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller && !store.get('off-' + id)) { store.set('off-' + id, 1); setTimeout(() => toast('이 책을 이 기기에 저장했습니다. 이제 인터넷 없이도 읽을 수 있습니다'), 1500); }
  if (!want && last > 1) toast(`지난번에 읽던 ${pageName(R.pages[R.i])}을 열었습니다`);
}
const pageName = p => p.label ? `${p.label}쪽` : `${p.n}번째 쪽`;
function closeReader() { stopSpeak(); R = null; const el = $('#reader'); if (el) el.remove(); document.body.style.overflow = ''; }
function exitReader() { if (R && R.ttsLocked) { toast('듣기가 잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요'); return; } const id = R && R.id; closeReader(); location.href = '/book/' + id + '/'; }
const paras = t => String(t || '').split(/\n\s*\n/).map(s => s.trim().split('\n').every(l => /^\s*\|/.test(l)) ? s.trim() : s.replace(/\s*\n\s*/g, ' ').trim()).filter(Boolean);
function markUl(s, n) {
  if (R.hl.length) return hl(s, R.hl);
  const rg = uls().filter(h => h.id === R.id && h.p === n && h.text && s.includes(h.text)).map(h => { const a = s.indexOf(h.text); return [a, a + h.text.length, h.k]; }).sort((x, y) => x[0] - y[0]);
  let out = '', p = 0; rg.forEach(([a, b, k]) => { if (a < p) return; out += esc(s.slice(p, a)) + `<u class="ul" data-hid="${k}" title="밑줄 · 눌러서 메모나 지우기">` + esc(s.slice(a, b)) + '</u>'; p = b; });
  return out + esc(s.slice(p));
}
function pageHtml(p) {
  if (!p.img) return `<div class="reflow ${R.font === 'sans' ? 'sans' : ''}" style="--fs:${R.fs};--lh:${R.lh};--mw:${R.mw}em">${paras(p.text).map((s, k) => `<p data-pg="${p.n}" data-s="${k}">${markUl(s, p.n)}</p>`).join('') || '<p class="muted">빈 쪽입니다.</p>'}</div>`;
  const src = R.zoom > 1.2 && p.big ? p.big : p.img;
  return `<div class="page-sheet img-sheet" style="width:min(${Math.round(560 * R.zoom)}px,100%);${p.w && p.h ? `aspect-ratio:${p.w}/${p.h}` : ''}"><img src="${esc(src)}" alt="${esc(R.title)} ${esc(pageName(p))}" draggable="false"></div>`;
}
// 글로 보기: 목차의 큰 장(들여쓰지 않은 항목) 단위로 보여 주기
function chapters() {
  const top = R.toc.filter(t => !/^\s/.test(t.title)).sort((a, b) => a.page - b.page);
  if (!top.length) return [{ title: '', from: 1, to: R.pages.length }];
  const out = [];
  // 첫 장 앞쪽에 글이 있을 때만 '앞부분'을 둠 (표지처럼 빈 쪽은 건너뜀)
  if (top[0].page > 1 && R.pages.slice(0, top[0].page - 1).some(p => p.text && p.text.trim())) out.push({ title: '앞부분', from: 1, to: top[0].page - 1 });
  top.forEach((t, i) => out.push({ title: t.title.trim(), from: t.page, to: (top[i + 1] ? top[i + 1].page - 1 : R.pages.length) }));
  return out.filter(c => c.to >= c.from);
}
function chapterOf(n) { const cs = chapters(); const k = cs.findIndex(c => n >= c.from && n <= c.to); return k < 0 ? 0 : k; }
function firstContent(pages, toc) { const t = toc.filter(x => !/^\s/.test(x.title)).map(x => x.page).sort((a, b) => a - b)[0]; const f = pages.findIndex(p => p.text && p.text.trim()) + 1; return Math.min(t || Infinity, f || Infinity) === Infinity ? 1 : Math.min(t || Infinity, f || Infinity); }
function reflowHtml() {
  const cs = chapters(), ci = Math.max(0, chapterOf(R.i + 1)), c = cs[ci];
  const subs = R.toc.filter(t => /^\s/.test(t.title) && t.page >= c.from && t.page <= c.to);
  const body = R.pages.slice(c.from - 1, c.to).map(p => {
    const ps = paras(p.text); const sub = subs.filter(t => t.page === p.n);
    if (!ps.length) return `<span id="pm-${p.n}"></span>`;
    return `<span class="pmark" id="pm-${p.n}">${esc(pageName(p))}</span>${ps.map((s, k) => blockHtml(s, p.n, k) || `<p data-pg="${p.n}" data-s="${k}"${isFootnote(s) ? ' class="fn"' : ''}>${fnMark(markUl(s, p.n))}</p>`).join('') || ''}`;
  }).join('');
  const nav = `<nav class="ch-nav" aria-label="장 이동">${ci > 0 ? `<button class="tbtn" data-go="${cs[ci - 1].from}">← ${esc(cs[ci - 1].title || '이전 장')}</button>` : '<span></span>'}${ci < cs.length - 1 ? `<button class="tbtn" data-go="${cs[ci + 1].from}">${esc(cs[ci + 1].title || '다음 장')} →</button>` : '<span></span>'}</nav>`;
  return `<div class="reflow ${R.font === 'sans' ? 'sans' : ''}" style="--fs:${R.fs};--lh:${R.lh};--mw:${R.mw}em">${c.title ? `<div class="ch-head"><span class="small muted">${ci + 1} / ${cs.length}</span><h3>${esc(c.title)}</h3></div>` : ''}${body}${nav}</div>`;
}
function tocFor(n) { let cur = null; for (const t of R.toc) if (t.page <= n) cur = t; return cur; }
function renderReader() {
  let el = $('#reader');
  if (!el) { el = document.createElement('div'); el.id = 'reader'; el.className = 'reader'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '읽기 화면'); document.body.appendChild(el); document.body.style.overflow = 'hidden'; }
  const p = R.pages[R.i], n = p.n, N = R.pages.length, marked = bms().some(m => m.id === R.id && m.p === n);
  const hasText = R.pages.some(x => x.text), hasImg = R.pages.some(x => x.img);
  const ch = tocFor(n);
  el.innerHTML = `<div class="r-top"><button class="tbtn" id="rClose" aria-label="읽기 닫기">← 닫기</button>
    <div class="r-title">${esc(R.title)}<small>${esc(R.by)}${ch ? ' · ' + esc(ch.title) : ''}</small></div>
    <div class="r-tools">
      ${R.toc.length ? '<button class="tbtn" data-panel="toc">목차</button>' : ''}${hasText ? '<button class="tbtn" data-panel="find" aria-label="본문 검색">🔍 찾기</button>' : ''}
      <button class="tbtn" data-panel="font" aria-label="글씨 크기">가<span style="font-size:16px">가</span></button>
      ${hasText && R.speaking ? `<button class="tbtn ${R.ttsLocked ? 'on' : ''}" id="rLock" aria-pressed="${!!R.ttsLocked}" title="잠그면 실수로 멈추지 않습니다">${R.ttsLocked ? '🔒 잠김' : '🔓 잠금'}</button>` : ''}${hasText ? `<button class="tbtn ${R.speaking ? 'on' : ''}" id="rSpeak" ${R.ttsLocked ? 'disabled' : ''}>${R.speaking ? '■ 멈춤' : '▶ 듣기'}</button><button class="tbtn" data-panel="tts" aria-label="듣기 설정">듣기 설정</button>` : ''}
      <button class="tbtn" data-panel="mode">화면</button>
      <button class="tbtn ${marked ? 'on' : ''}" id="rMark" aria-pressed="${marked}">${marked ? '★ 책갈피' : '☆ 책갈피'}</button>
      <button class="tbtn" data-panel="bm">책갈피 목록</button>
      ${hasText ? '<button class="tbtn" data-panel="ul">밑줄 모음</button>' : ''}
    </div></div>
    ${R.hl.length ? `<div class="variant-note" style="border-radius:0">찾은 말을 표시하고 있습니다. <button id="hlOff">표시 끄기</button></div>` : ''}
    <div class="r-body" id="rBody">${R.view === 'page' ? pageHtml(p) : reflowHtml()}</div>
    <div class="r-bottom"><button class="tbtn" id="rPrev" ${R.i === 0 ? 'disabled' : ''} aria-label="이전 쪽">‹</button>
      <label for="rRange" class="sr">쪽 이동</label><input type="range" id="rRange" min="1" max="${N}" value="${n}">
      <span class="pg">${p.label ? esc(p.label) + '쪽 · ' : ''}${n} / ${N}</span><button class="tbtn" id="rNext" ${R.i === N - 1 ? 'disabled' : ''} aria-label="다음 쪽">›</button></div>
    <div class="panel" id="p-find"><h5>이 책에서 찾기</h5>
      <form id="findForm" class="row" style="gap:6px"><input id="findQ" placeholder="찾을 말" aria-label="찾을 말" value="${esc(R.findQ || '')}" style="flex:1;height:36px;border:1px solid var(--line);border-radius:8px;padding:0 10px;background:var(--paper)"><button class="tbtn" type="submit">찾기</button></form>
      <div id="findRes">${R.findRes || '<p class="note">낱말을 넣으면 이 책의 모든 쪽에서 찾습니다. 위빳사나·vipassanā처럼 다른 표기도 함께 찾습니다.</p>'}</div></div>
    <div class="panel" id="p-toc"><h5>목차</h5><ul>${R.toc.map(t => `<li class="${/^\s/.test(t.title) ? 'sub' : ''}"><button class="link" data-go="${t.page}">${esc(t.title.trim())}</button><span class="muted">${esc(t.label || '')}</span></li>`).join('')}</ul></div>
    <div class="panel" id="p-font"><h5>글씨</h5>
      ${R.view === 'page' && hasImg ? `<div class="row">쪽 확대 <span><button class="tbtn" data-zoom="-1">−</button> ${Math.round(R.zoom * 100)}% <button class="tbtn" data-zoom="1">+</button></span></div>${hasText ? '<p class="note">쪽 보기에서는 원본 쪽을 확대합니다. 글자만 크게 보거나 밑줄을 그으려면 ‘글로 보기’로 바꾸세요.</p>' : ''}` :
      `<div class="row">글자 크기 <span class="seg">${[0.85, 1, 1.15, 1.3, 1.5].map((v, i) => `<button data-fs="${v}" class="${R.fs === v ? 'on' : ''}">${i + 1}</button>`).join('')}</span></div>
       <div class="row">줄 간격 <span class="seg">${[[1.6, '좁게'], [1.9, '보통'], [2.2, '넓게']].map(([v, l]) => `<button data-lh="${v}" class="${R.lh === v ? 'on' : ''}">${l}</button>`).join('')}</span></div>
       <div class="row">글꼴 <span class="seg"><button data-font="serif" class="${R.font === 'serif' ? 'on' : ''}">명조</button><button data-font="sans" class="${R.font === 'sans' ? 'on' : ''}">고딕</button></span></div>
       <div class="row">글 너비 <span class="seg">${[[28, '좁게'], [36, '보통'], [46, '넓게'], [70, '화면 가득']].map(([v, l]) => `<button data-mw="${v}" class="${R.mw === v ? 'on' : ''}">${l}</button>`).join('')}</span></div>`}</div>
    <div class="panel" id="p-tts">${ttsPanel()}</div>
    <div class="panel" id="p-mode"><h5>화면 모드</h5><div class="seg">${[['day', '기본'], ['mono', '흑백'], ['night', '밤']].map(([k, v]) => `<button data-rmode="${k}" class="${store.get('mode', 'auto') === k ? 'on' : ''}">${v}</button>`).join('')}</div><p class="note">고른 모드는 사이트 전체에 적용되고 다음에 와도 유지됩니다.</p></div>
    <div class="panel" id="p-ul"><h5>이 책의 밑줄</h5><ul>${uls().filter(h => h.id === R.id).sort((a, b) => a.p - b.p).map(h => `<li style="display:block"><button class="link" data-go="${h.p}">${esc(h.pl || h.p)}쪽</button><div class="quote" style="font-size:13.5px">${esc(h.text)}</div>${h.note ? `<div class="small muted">${esc(h.note)}</div>` : ''}</li>`).join('') || '<li class="muted">글을 끌어서 고르면 밑줄을 그을 수 있습니다.</li>'}</ul>
      <div class="row"><a class="tbtn" href="/mynotes/">내 서재에서 모두 보기</a></div></div>
    <div class="panel" id="p-uledit"><h5>밑줄</h5><div class="quote" id="ulText" style="font-size:13.5px"></div>
      <div class="row"><input id="ulNote" placeholder="메모 한 줄" aria-label="밑줄 메모" style="flex:1;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 8px;background:var(--paper)"></div>
      <div class="row"><button class="tbtn" id="ulSave">메모 저장</button><button class="tbtn" id="ulCopy">출처와 함께 복사</button><button class="tbtn" id="ulDel">밑줄 지우기</button></div></div>
    <div class="sel-pop" id="selPop" role="toolbar" aria-label="고른 글"><button id="selUl">밑줄 긋기</button><button id="selNote">밑줄+메모</button><button id="selCopy">복사</button>${R.pages.some(x => x.text) ? '<button id="selPlay">▶ 여기부터 듣기</button>' : ''}</div>
    <div class="panel" id="p-bm"><h5>내 책갈피</h5><ul>${bms().map((m, k) => `<li><span><a class="link" href="/read/${m.id}/${m.p}">『${esc(m.t)}』 ${esc(m.pl || m.p)}쪽</a>${m.note ? `<br><span class="muted small">${esc(m.note)}</span>` : ''}</span><button class="link" data-bmdel="${k}" aria-label="책갈피 지우기">지우기</button></li>`).join('') || '<li class="muted">아직 책갈피가 없습니다.</li>'}</ul>
      <div class="row" style="margin-top:12px"><input id="bmNote" placeholder="이 쪽에 한 줄 메모" aria-label="책갈피 메모" style="flex:1;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 8px;background:var(--paper)"><button class="tbtn" id="bmSave">저장</button></div>
      <p class="note">회원가입 없이 이 기기의 브라우저에만 저장됩니다. 다른 기기로 옮길 때는 내 서재의 ‘옮기기’를 쓰세요.</p></div>`;
  bindReader();
  if (R.view === 'text') { const c = chapters()[Math.max(0, chapterOf(n))]; const pm = $('#pm-' + n); if (pm && n !== c.from) pm.scrollIntoView({ block: 'start' }); else $('#rBody').scrollTop = 0; }
  // 다음 쪽 그림 미리 받기
  const nx = R.pages[R.i + 1]; if (nx && nx.img && R.view === 'page') { const im = new Image(); im.src = nx.img; }
  store.set('pos-' + R.id, n);
  saveHistory(n);
  history.replaceState(history.state, '', `/read/${R.id}/${n}` + location.search);
}
function go(n) { if (!R) return; if (R.ttsLocked) { toast('듣기가 잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요'); return; } R.i = Math.max(0, Math.min(R.pages.length - 1, n - 1)); stopSpeak(); renderReader(); if (R.view === 'page') $('#rBody').scrollTop = 0; }
function bindReader() {
  const el = $('#reader');
  const reopen = id => $('#' + id).classList.add('open');
  $('#rClose').onclick = exitReader;
  $('#rPrev').onclick = () => go(R.i); $('#rNext').onclick = () => go(R.i + 2); $('#rRange').onchange = e => go(+e.target.value);
  const ff = $('#findForm'); if (ff) ff.onsubmit = async ev => {
    ev.preventDefault(); const q = $('#findQ').value.trim(); R.findQ = q; if (!q) return;
    let V = []; try { V = (await data()).variants; } catch (e) {}
    const { terms, group } = expand(q, V);
    const hits = [];
    for (const pgx of R.pages) {
      const ps = paras(pgx.text);
      ps.forEach((t, k) => { if (terms.some(x => norm(t).includes(x))) hits.push({ n: pgx.n, k, s: snippet(t, terms) || t.slice(0, 80) }); });
    }
    const ch = n => { const c = chapters()[chapterOf(n)]; return c && c.title ? c.title : ''; };
    R.findTerms = terms;
    R.findRes = `<p class="note">${hits.length ? `${hits.length}곳을 찾았습니다.` : '찾는 말이 없습니다.'}${group ? ` (${group.map(esc).join(', ')} 함께 찾음)` : ''}</p>
      <ul class="find-list">${hits.slice(0, 200).map(h => `<li><button class="link" data-find="${h.n}" data-k="${h.k}"><span class="muted small">${esc(pageName(R.pages[h.n - 1]))}${ch(h.n) ? ' · ' + esc(ch(h.n)) : ''}</span><br>${hl(h.s, terms)}</button></li>`).join('')}</ul>${hits.length > 200 ? '<p class="note">앞의 200곳만 보입니다. 더 자세한 말로 찾아보세요.</p>' : ''}`;
    $('#findRes').innerHTML = R.findRes; bindFind();
  };
  const bindFind = () => $$('[data-find]', el).forEach(b => b.onclick = () => {
    R.hl = R.findTerms || []; const n = +b.dataset.find, k = +b.dataset.k;
    R.i = n - 1; stopSpeak(false); renderReader(); $('#p-find').classList.add('open');
    const t = $(`[data-pg="${n}"][data-s="${k}"]`); if (t) { t.scrollIntoView({ block: 'center' }); t.classList.add('found'); setTimeout(() => t.classList.remove('found'), 1800); }
  });
  bindFind();
  $$('[data-zoom-img]', el).forEach(b => b.onclick = () => zoomView(`<img src="${esc(b.dataset.zoomImg)}" alt="${esc(b.dataset.cap)}">`, b.dataset.cap || '그림'));
  $$('[data-zoom-tbl]', el).forEach(b => b.onclick = () => zoomView(b.parentElement.querySelector('table').outerHTML, '표'));
  const ho = $('#hlOff'); if (ho) ho.onclick = () => { R.hl = []; history.replaceState(null, '', location.pathname); renderReader(); };
  
  $$('[data-panel]', el).forEach(b => b.onclick = () => { const p = $('#p-' + b.dataset.panel); const o = p.classList.contains('open'); $$('.panel', el).forEach(x => x.classList.remove('open')); if (!o) p.classList.add('open'); });
  $$('[data-go]', el).forEach(b => b.onclick = () => go(+b.dataset.go));
  $$('[data-zoom]', el).forEach(b => b.onclick = () => { R.zoom = Math.max(.75, Math.min(2.5, +(R.zoom + (+b.dataset.zoom) * .25).toFixed(2))); store.set('rzoom', R.zoom); renderReader(); reopen('p-font'); });
  $$('[data-fs]', el).forEach(b => b.onclick = () => { R.fs = +b.dataset.fs; store.set('rfs', R.fs); renderReader(); reopen('p-font'); });
  $$('[data-lh]', el).forEach(b => b.onclick = () => { R.lh = +b.dataset.lh; store.set('rlh', R.lh); renderReader(); reopen('p-font'); });
  $$('[data-font]', el).forEach(b => b.onclick = () => { R.font = b.dataset.font; store.set('rfont', R.font); renderReader(); reopen('p-font'); });
  $$('[data-mw]', el).forEach(b => b.onclick = () => { R.mw = +b.dataset.mw; store.set('rmw', R.mw); renderReader(); reopen('p-font'); });
  $$('[data-rmode]', el).forEach(b => b.onclick = () => { applyMode(b.dataset.rmode); renderReader(); reopen('p-mode'); });
  const cur = () => R.pages[R.i];
  $('#rMark').onclick = () => { const l = bms(), n = cur().n, k = l.findIndex(m => m.id === R.id && m.p === n); if (k > -1) { l.splice(k, 1); toast('책갈피를 지웠습니다'); } else { l.push({ id: R.id, t: R.title, p: n, pl: cur().label, note: '', d: today() }); toast(`${pageName(cur())}에 책갈피를 달았습니다`); } store.set('bm', l); renderReader(); };
  $('#bmSave').onclick = () => { const l = bms(), n = cur().n; let m = l.find(m => m.id === R.id && m.p === n); if (!m) { m = { id: R.id, t: R.title, p: n, pl: cur().label, d: today() }; l.push(m); } m.note = $('#bmNote').value.trim(); store.set('bm', l); renderReader(); reopen('p-bm'); toast('메모를 저장했습니다'); };
  $$('[data-bmdel]', el).forEach(b => b.onclick = () => { const l = bms(); l.splice(+b.dataset.bmdel, 1); store.set('bm', l); renderReader(); reopen('p-bm'); });
  const sp = $('#rSpeak'); if (sp) sp.onclick = () => { if (R.ttsLocked) return toast('잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요'); R.speaking ? stopSpeak(true) : speak(); };
  const lk = $('#rLock'); if (lk) lk.onclick = () => { R.ttsLocked = !R.ttsLocked; renderReader(); toast(R.ttsLocked ? '잠갔습니다. 실수로 멈추거나 닫히지 않습니다' : '잠금을 풀었습니다'); };
  $$('[data-tts]', el).forEach(inp => {
    const save = () => {
      const o = store.get('tts', {}), k = inp.dataset.tts;
      o[k] = inp.type === 'checkbox' ? inp.checked : (inp.type === 'range' || k === 'pause' || k === 'sleep') ? +inp.value : inp.value;
      store.set('tts', o);
      if (k === 'rate') $('#ttsRateV').textContent = (+inp.value).toFixed(1) + '배';
      if (k === 'pitch') $('#ttsPitchV').textContent = (+inp.value).toFixed(1);
      if (k === 'sleep' && R.speaking) R.ttsStart = Date.now();
    };
    inp.addEventListener(inp.type === 'range' ? 'input' : 'change', save);
  });
  const tt = $('#ttsTry'); if (tt) tt.onclick = () => {
    if (!('speechSynthesis' in window)) return toast('이 기기에서는 음성 읽기를 쓸 수 없습니다');
    if (!LEX.pali) { loadLex().then(() => tt.onclick()); return; }
    const o = ttsOpt(); const pv = pickVoice(o), v = pv.voice;
    speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(sayable('법의 보시는 모든 보시를 뛰어넘는다. Sabbadānaṃ dhammadānaṃ jināti. (법구경 354게송)', o));
    u.lang = v ? v.lang : 'ko-KR'; if (v) u.voice = v; u.rate = +o.rate; u.pitch = pv.pitch; speechSynthesis.speak(u);
  };
  const trs = $('#ttsReset'); if (trs) trs.onclick = () => { store.set('tts', {}); renderReader(); $('#p-tts').classList.add('open'); toast('처음 설정으로 돌렸습니다'); };
  const body = $('#rBody');
  // 밀어서 넘기기 (쪽 보기)
  let sx = null; body.addEventListener('touchstart', e => { if (R.view === 'page' && R.zoom <= 1) sx = e.touches[0].clientX; }, { passive: true });
  body.addEventListener('touchend', e => { if (sx == null) return; const dx = e.changedTouches[0].clientX - sx; sx = null; if (Math.abs(dx) > 70 && !window.getSelection().toString()) go(R.i + (dx < 0 ? 2 : 0)); });
  // 글 고르기 → 밑줄 단추 (컴퓨터: 마우스, 휴대폰: 길게 눌러 고르기)
  const touch = matchMedia('(pointer: coarse)').matches;
  const onSel = () => {
    const s = window.getSelection(), pop = $('#selPop'); if (!pop) return;
    if (!s || s.isCollapsed || !s.toString().trim()) { if (!pop._hold) pop.classList.remove('show'); return; }
    const node = s.anchorNode && (s.anchorNode.nodeType === 1 ? s.anchorNode : s.anchorNode.parentElement); const para = node && node.closest('[data-pg]');
    if (!para || !body.contains(para)) { pop.classList.remove('show'); return; }
    const r = s.getRangeAt(0).getBoundingClientRect(), pw = pop.offsetWidth || 240, ph = 46;
    pop.style.left = Math.max(8, Math.min(window.innerWidth - pw - 8, r.left + r.width / 2 - pw / 2)) + 'px';
    // 휴대폰은 위쪽에 기기 자체의 복사 메뉴가 뜨므로 아래쪽에 둠
    let top = touch ? r.bottom + 14 : r.top - ph - 4;
    if (top < 8) top = r.bottom + 14;
    if (top > window.innerHeight - ph - 70) top = Math.max(8, r.top - ph - 50);
    pop.style.top = top + 'px';
    pop.classList.add('show'); pop._sel = { text: s.toString().replace(/\s+/g, ' ').trim(), p: +para.dataset.pg };
  };
  let selT; window._ddOnSel = () => { clearTimeout(selT); selT = setTimeout(onSel, touch ? 350 : 30); };
  if (!window._ddSelBound) { document.addEventListener('selectionchange', () => window._ddOnSel && window._ddOnSel()); window._ddSelBound = true; }
  body.addEventListener('mouseup', window._ddOnSel); body.addEventListener('keyup', window._ddOnSel);
  // 단추를 누를 때 고른 글이 풀리지 않도록
  $$('#selPop button').forEach(b => { b.addEventListener('pointerdown', e => e.preventDefault()); b.addEventListener('mousedown', e => e.preventDefault()); });
  const plabel = n => (R.pages[n - 1] || {}).label || '';
  const addUl = withNote => {
    const pop = $('#selPop'), d = pop._sel; if (!d) return; const l = uls(); const k = Date.now();
    l.push({ k, id: R.id, t: R.title, by: R.by, p: d.p, pl: plabel(d.p), text: d.text, note: '', d: today() }); store.set('ul', l);
    window.getSelection().removeAllRanges(); pop.classList.remove('show'); renderReader();
    if (withNote) openUl(k); else toast('밑줄을 그었습니다. ‘밑줄 모음’과 내 서재에서 모아 볼 수 있습니다');
  };
  $('#selUl').onclick = () => addUl(false); $('#selNote').onclick = () => addUl(true);
  const sp2 = $('#selPlay'); if (sp2) sp2.onclick = () => {
    const sel = window.getSelection(); const pop = $('#selPop'); pop.classList.remove('show');
    if (!sel || !sel.rangeCount) return;
    const rg = sel.getRangeAt(0); const node = rg.startContainer.nodeType === 1 ? rg.startContainer : rg.startContainer.parentElement;
    const para = node && node.closest('[data-pg]'); if (!para) return;
    const pre = document.createRange(); pre.setStart(para, 0); pre.setEnd(rg.startContainer, rg.startOffset);
    const rest = para.textContent.slice(pre.toString().length);
    const pg = +para.dataset.pg, k = +para.dataset.s; sel.removeAllRanges();
    stopSpeak(false); R.i = pg - 1; speak(k, rest);
  };
  $('#selCopy').onclick = () => { const d = $('#selPop')._sel; if (d) copy(`“${d.text}” — ${R.by}, 『${R.title}』 ${plabel(d.p) || d.p}쪽 (${SITE})`, '고른 글을 출처와 함께 복사했습니다'); $('#selPop').classList.remove('show'); };
  $$('u.ul', el).forEach(u => u.onclick = e => { e.stopPropagation(); openUl(+u.dataset.hid); });
}
function openUl(k) {
  const h = uls().find(x => x.k === k); if (!h) return; const el = $('#reader');
  $$('.panel', el).forEach(x => x.classList.remove('open'));
  $('#p-uledit').classList.add('open'); $('#ulText').textContent = h.text; $('#ulNote').value = h.note || ''; $('#ulNote').focus();
  $('#ulSave').onclick = () => { const l = uls(); const x = l.find(x => x.k === k); x.note = $('#ulNote').value.trim(); store.set('ul', l); renderReader(); toast('메모를 저장했습니다'); };
  $('#ulDel').onclick = () => { store.set('ul', uls().filter(x => x.k !== k)); renderReader(); toast('밑줄을 지웠습니다'); };
  $('#ulCopy').onclick = () => copy(`“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽 (${SITE})`, '출처와 함께 복사했습니다');
}
// 빨리어 로마자 → 한글 소리 (니까야 번역 용어집 v1.1 음역 규칙)
const PALI = (() => {
  const CHO = { 'ㄱ': 0, 'ㄲ': 1, 'ㄴ': 2, 'ㄷ': 3, 'ㄸ': 4, 'ㄹ': 5, 'ㅁ': 6, 'ㅂ': 7, 'ㅃ': 8, 'ㅅ': 9, 'ㅇ': 11, 'ㅈ': 12, 'ㅉ': 13, 'ㅊ': 14, 'ㅋ': 15, 'ㅌ': 16, 'ㅍ': 17, 'ㅎ': 18 };
  const JONG = { '': 0, 'ㄱ': 1, 'ㄴ': 4, 'ㄹ': 8, 'ㅁ': 16, 'ㅂ': 17, 'ㅅ': 19, 'ㅇ': 21 };
  const V = { a: [0, 2, 9], ā: [0, 2, 9], i: [20, 20, 16], ī: [20, 20, 16], u: [13, 17, 13], ū: [13, 17, 13], e: [5, 7, 15], o: [8, 12, 8] }; // [보통, y붙음, w붙음]
  const ONSET = { k: 'ㄲ', kh: 'ㅋ', g: 'ㄱ', gh: 'ㄱ', c: 'ㅉ', ch: 'ㅊ', j: 'ㅈ', jh: 'ㅈ', 'ṭ': 'ㄸ', 'ṭh': 'ㅌ', 'ḍ': 'ㄷ', 'ḍh': 'ㄷ', t: 'ㄸ', th: 'ㅌ', d: 'ㄷ', dh: 'ㄷ', p: 'ㅃ', ph: 'ㅍ', b: 'ㅂ', bh: 'ㅂ', n: 'ㄴ', 'ṇ': 'ㄴ', 'ñ': 'ㄴ', m: 'ㅁ', y: 'ㅇ', r: 'ㄹ', l: 'ㄹ', 'ḷ': 'ㄹ', s: 'ㅅ', h: 'ㅎ', v: 'ㅇ', 'ṅ': 'ㅇ', 'ṃ': 'ㅇ' };
  const CODA = { k: 'ㄱ', kh: 'ㄱ', g: 'ㄱ', gh: 'ㄱ', c: 'ㅅ', ch: 'ㅅ', j: 'ㅅ', jh: 'ㅅ', 'ṭ': 'ㅅ', 'ṭh': 'ㅅ', 'ḍ': 'ㅅ', 'ḍh': 'ㅅ', t: 'ㅅ', th: 'ㅅ', d: 'ㅅ', dh: 'ㅅ', s: 'ㅅ', p: 'ㅂ', ph: 'ㅂ', b: 'ㅂ', bh: 'ㅂ', n: 'ㄴ', 'ṇ': 'ㄴ', 'ñ': 'ㄴ', m: 'ㅁ', 'ṅ': 'ㅇ', 'ṃ': 'ㅇ', l: 'ㄹ', 'ḷ': 'ㄹ' };
  const NASAL = new Set(['n', 'ṇ', 'ñ', 'm', 'ṅ', 'ṃ']);
  const base = c => c.replace('h', '') || c;
  const syl = (cho, jung, jong = '') => String.fromCharCode(0xAC00 + (CHO[cho] * 21 + jung) * 28 + JONG[jong]);
  function units(w) {
    const out = []; let i = 0;
    while (i < w.length) {
      const two = w.slice(i, i + 2), one = w[i];
      if (V[one]) { out.push({ v: one }); i++; continue; }
      if (two.length === 2 && two[1] === 'h' && ONSET[two]) { out.push({ c: two }); i += 2; continue; }
      if (ONSET[one]) { out.push({ c: one }); i++; continue; }
      return null; // 빨리어가 아닌 글자
    }
    return out;
  }
  function conv(word) {
    const w = word.toLowerCase().normalize('NFC').replace(/ṁ/g, 'ṃ').replace(/vaṃs/g, 'vams'); // 스승 이름 -vaṃsa 는 '왐사' (사이트 결정)
    const u = units(w); if (!u || !u.some(x => x.v)) return null;
    const S = []; // {cho, jung, jong}
    const plain = c => S.push({ cho: ONSET[c] === undefined ? 'ㅇ' : ONSET[c], jung: 18, jong: '' }); // 모음 없는 자음: '으'
    let i = 0;
    while (i < u.length) {
      // 자음 묶음 모으기
      const cl = []; while (i < u.length && u[i].c) cl.push(u[i++].c);
      const vow = i < u.length ? u[i++].v : null;
      let k = 0;
      // 앞 음절 받침
      if (S.length && cl.length) {
        const prev = S[S.length - 1], c0 = cl[0];
        if (cl.length === 1 && (c0 === 'l' || c0 === 'ḷ') && vow) prev.jong = prev.jong || 'ㄹ';           // 모음 사이 l: ㄹ 덧붙임
        else if (c0 === 'ṃ' || c0 === 'ṅ') { prev.jong = 'ㅇ'; k = 1; }
        else if (cl.length >= 2 && (base(c0) === base(cl[1]) || NASAL.has(c0) || c0 === 'l' || c0 === 'ḷ') && CODA[c0] && !(cl[1] === 'y' && !NASAL.has(c0) && base(c0) !== base(cl[1]))) {
          if (base(c0) === 'y' || base(c0) === 'v') k = 1; else { prev.jong = CODA[c0]; k = 1; }
        } else if (!vow && CODA[c0] && cl.length === 1) { prev.jong = CODA[c0]; k = 1; }
      }
      // 남은 자음: 마지막 하나는 첫소리, 그 앞은 '으' (단, 자음+y 는 합침)
      const rest = cl.slice(k);
      if (!vow) { rest.forEach(plain); break; }
      let onset = 'ㅇ', glide = 0;
      if (rest.length) {
        let last = rest[rest.length - 1], before = rest.slice(0, -1);
        if (last === 'y' && before.length) { last = before.pop(); glide = 1; }
        else if (last === 'y') glide = 1;
        else if (last === 'v') { glide = 2; if (before.length) { last = before.pop(); } else last = 'v'; }
        else if (last === 'ñ' && 'aāeo'.includes(vow)) glide = 1;
        before.forEach(plain);
        onset = ONSET[last];
      }
      let jung = V[vow][glide];
      if (glide === 2 && onset !== 'ㅇ') { // 자음+v: 자음에 '으'를 붙이고 와/위…
        S.push({ cho: onset, jung: 18, jong: '' }); onset = 'ㅇ';
      }
      S.push({ cho: onset, jung, jong: '' });
    }
    return S.map(x => syl(x.cho, x.jung, x.jong)).join('');
  }
  return conv;
})();
// 소리 내어 읽을 글 다듬기
const PALI_MARK = /[āīūṭḍṇṅñṃṁḷĀĪŪṬḌṆṄÑṂṀḶ]/;
const PALI_WORDS = new Set(['dhamma', 'sutta', 'metta', 'vipassana', 'samatha', 'sati', 'nibbana', 'buddha', 'sangha', 'sila', 'samadhi', 'panna', 'kamma', 'dana', 'bhikkhu', 'bhikkhuni', 'sadhu', 'jhana', 'arahant', 'dukkha', 'anicca', 'anatta', 'karuna', 'mudita', 'upekkha', 'brahmavihara', 'abhidhamma', 'vinaya', 'tipitaka', 'nikaya', 'paticcasamuppada', 'satipatthana', 'anapanasati', 'kusala', 'akusala', 'citta', 'cetasika', 'rupa', 'nama', 'khandha', 'bhavana', 'parami', 'puñña', 'punna']);
const LATIN = "A-Za-zĀ-žḀ-ỿ";
// 빨리어·영어 낱말 목록 (빨리어: Digital Pāḷi Dictionary, CC BY-NC-SA 4.0 / 영어: SCOWL). 듣기를 처음 쓸 때 한 번 받음
const LEX = { pali: null, en: null, loading: null };
function loadLex() {
  if (LEX.loading) return LEX.loading;
  const set = t => new Set(t.split('\n').filter(x => x && x[0] !== '#'));
  LEX.loading = Promise.all(['/data/pali-words.txt', '/data/en-words.txt'].map(u => fetch(u).then(r => r.ok ? r.text() : ''))).then(([p, e]) => { LEX.pali = set(p); LEX.en = set(e); }).catch(() => { LEX.pali = new Set(); LEX.en = new Set(); });
  return LEX.loading;
}
const plainW = w => w.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
// 낱말 하나: P(빨리어) E(영어) B(둘 다 있음) ?(모름)
function langOf(w) {
  if (PALI_MARK.test(w)) return 'P';
  const x = plainW(w), p = (LEX.pali && LEX.pali.has(x)) || PALI_WORDS.has(x), e = LEX.en && LEX.en.has(x);
  if (p && !e) return 'P'; if (e && !p) return 'E';
  if (!p && !e) return looksPali(w) ? 'P' : '?';
  return 'B';
}
// 점·막대가 없어도 빨리어처럼 생긴 낱말: 빨리어 글자로만 되어 있고, 겹자음이 있고, 모음으로 끝남 (akkhanti, dukkha …)
const looksPali = w => w.length >= 4 && /^[a-z]+$/i.test(w) && !/[fqwxz]/i.test(w) && /(kk|gg|cc|jj|tt|dd|pp|bb|mm|nn|ss|ll)/i.test(w) && /[aeiou]$/i.test(w) && !!PALI(w);
// 한국어 목소리만 (이름으로 남·여를 알 수 있으면 표시)
const MALE_V = /injoon|hyunsu|bongjin|gookmin|minsu|jihoon|male|남성|남자/i, FEMALE_V = /sunhi|heami|yuna|seoyeon|jimin|seohyun|yujin|soonbok|jihyun|female|여성|여자/i;
function koVoices() { return ('speechSynthesis' in window ? speechSynthesis.getVoices() : []).filter(v => /^ko/i.test(v.lang)); }
function voiceOptions(cur) {
  const ko = koVoices();
  const tag = v => MALE_V.test(v.name) ? ' · 남성' : FEMALE_V.test(v.name) ? ' · 여성' : '';
  const opt = v => `<option value="${esc(v.voiceURI)}" ${v.voiceURI === cur ? 'selected' : ''}>${esc(v.name)}${tag(v)}${v.localService ? '' : ' (인터넷)'}</option>`;
  const male = ko.filter(v => MALE_V.test(v.name)), rest = ko.filter(v => !MALE_V.test(v.name));
  return `<option value="">기기 기본 한국어 목소리</option>${male.length ? `<optgroup label="남성 목소리">${male.map(opt).join('')}</optgroup>` : ''}${rest.length ? `<optgroup label="${male.length ? '그 밖의 목소리' : '한국어 목소리'}">${rest.map(opt).join('')}</optgroup>` : ''}
    <option value="__low" ${cur === '__low' ? 'selected' : ''}>낮은 목소리 (기본 목소리를 낮춰서)</option>`;
}
// 고른 목소리와 높낮이 정하기
function pickVoice(o) {
  if (o.voice === '__low') return { voice: koVoices()[0] || null, pitch: Math.max(0.1, +o.pitch * 0.62) };
  const v = o.voice && koVoices().find(x => x.voiceURI === o.voice);
  return { voice: v || null, pitch: +o.pitch };
}
function ttsPanel() {
  const o = ttsOpt();
  const ck = (k, label, hint = '') => `<label class="tts-ck"><input type="checkbox" data-tts="${k}" ${o[k] ? 'checked' : ''}><span>${label}${hint ? `<small>${hint}</small>` : ''}</span></label>`;
  const sel = (k, list) => `<select data-tts="${k}">${list.map(([v, l]) => `<option value="${v}" ${String(o[k]) === String(v) ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  return `<h5>듣기 설정</h5>
    <div class="tts-row"><label for="ttsVoice">목소리</label><select id="ttsVoice" data-tts="voice">${voiceOptions(o.voice)}</select></div>
    <div class="tts-row"><label>빠르기 <b id="ttsRateV">${(+o.rate).toFixed(1)}배</b></label><input type="range" min="0.6" max="1.8" step="0.1" value="${o.rate}" data-tts="rate"></div>
    <div class="tts-row"><label>목소리 높낮이 <b id="ttsPitchV">${(+o.pitch).toFixed(1)}</b></label><input type="range" min="0.6" max="1.4" step="0.1" value="${o.pitch}" data-tts="pitch"></div>
    <div class="tts-sub">읽을 것</div>
    ${ck('pali', '빠알리어', '빠알리어 소리대로 읽음')}${ck('gloss', '한글 옆 원어 풀이도 읽기', '위빳사나Vipassanā, 지도법사(Nāyaka Sayadaw)처럼 한글과 같은 말을 한 번 더 읽음')}${ck('en', '영어')}${ck('hanja', '한자')}${ck('fn', '각주')}${ck('sym', '특수부호', '괄호·따옴표 등을 이름으로 읽음')}
    <div class="tts-sub">읽는 방식</div>
    <div class="tts-row"><label>문단 사이 쉼</label>${sel('pause', [[0, '쉬지 않음'], [0.3, '짧게'], [0.8, '보통'], [1.5, '길게']])}</div>
    <div class="tts-row"><label>꺼짐 예약</label>${sel('sleep', [[0, '끄지 않음'], [15, '15분 뒤'], [30, '30분 뒤'], [60, '1시간 뒤']])}</div>
    ${ck('chapterStop', '한 장이 끝나면 멈추기')}${ck('follow', '읽는 곳을 따라 화면 움직이기')}
    <div class="row"><button class="tbtn" id="ttsTry">▶ 미리 듣기</button><button class="tbtn" id="ttsReset">처음 설정으로</button></div>
    <p class="note">목소리는 이 기기에 깔린 한국어 목소리 가운데서 고릅니다. 남성 목소리가 목록에 없으면 ‘낮은 목소리’를 고르거나, 컴퓨터에서는 마이크로소프트 엣지(Edge) 브라우저로 열면 남성 목소리(InJoon, Hyunsu)를 고를 수 있습니다. 설정은 이 기기의 브라우저에 저장되고, 듣는 중에 바꾸면 다음 문단부터 적용됩니다. 빨리어 낱말 목록: Digital Pāḷi Dictionary (CC BY-NC-SA 4.0).</p>`;
}
// 듣기 설정 (이 브라우저에 저장)
const TTS_DEF = { voice: '', rate: 1, pitch: 1, gloss: false, sym: false, en: true, pali: true, hanja: true, fn: false, pause: 0.3, chapterStop: false, sleep: 0, follow: true };
const ttsOpt = () => Object.assign({}, TTS_DEF, store.get('tts', {}));
const SYM_NAME = { '(': '괄호 열고', ')': '괄호 닫고', '[': '대괄호 열고', ']': '대괄호 닫고', '‘': '작은따옴표', '’': '작은따옴표', '“': '큰따옴표', '”': '큰따옴표', '"': '큰따옴표', "'": '작은따옴표', '「': '낫표', '」': '낫표', '『': '겹낫표', '』': '겹낫표', '《': '겹화살괄호', '》': '겹화살괄호', '〈': '홑화살괄호', '〉': '홑화살괄호', '<': '홑화살괄호', '>': '홑화살괄호', '＜': '홑화살괄호', '＞': '홑화살괄호', '·': '가운뎃점', 'ㆍ': '가운뎃점', '…': '줄임표', '~': '물결표', '*': '별표', '/': '빗금', '|': '세로줄', '—': '줄표', '–': '줄표', '－': '붙임표' };
const SYM_RE = /[()\[\]‘’“”"'「」『』《》〈〉<>＜＞·ㆍ…~*/|—–－]/g;
function sayable(s, o = ttsOpt()) {
  let t = String(s || '');
  t = t.replace(/\[\^[^\]]+\]/g, ''); // 각주 표시
  // 한글 바로 뒤에 붙은 로마자 풀이(예: 위빳사나Vipassanā, 사야도Chanmyay Sayadaw)는 한 번만 읽도록 뺌
  // 한글 바로 뒤에 띄어 쓰지 않고 붙은 로마자는 앞 한글의 원어 풀이로 봄 (위빳사나Vipassanā, 도사dosa, 사야도Chanmyay Sayadaw)
  //  - 풀이 읽기를 끄면 건너뜀, 켜면 빨리어 소리로 한 번 더 읽음
  t = t.replace(new RegExp(`([가-힣])([${LATIN}][${LATIN}\\-]*(?:\\s+[${LATIN}][${LATIN}\\-]*)*)`, 'g'), (m, h, lat) => {
    if (!o.gloss) return h;
    const ws = lat.split(/[\s-]+/).filter(Boolean), pc = ws.filter(w => langOf(w) === 'P').length, ec = ws.filter(w => langOf(w) === 'E').length;
    const pali = PALI_MARK.test(lat) || pc > ec || (pc === ec && /[a-z]/.test(lat[0]));
    return h + ' ' + (pali ? (o.pali ? lat.split(/[\s-]+/).map(w => PALI(w) || w).join(' ') : '') : (o.en ? lat : ''));
  });
  // 한글 뒤 괄호 안이 로마자·숫자뿐이면(원어 풀이) 뺌: 지도법사(Nāyaka Sayadaw)
  if (!o.gloss) t = t.replace(/([가-힣])\s?\(([^()가-힣]*)\)/g, (m, h, inner) => /[A-Za-zĀ-ž]/.test(inner) ? h : m);
  // 로마자 덩어리: 낱말 목록으로 빨리어·영어를 가름. 정하기 어려운 낱말은 덩어리의 다수를 따름
  t = t.replace(new RegExp(`[${LATIN}]+(?:[\\s,;:.!?'’‘\\-]+[${LATIN}]+)*`, 'g'), run => {
    const comps = run.match(new RegExp(`[${LATIN}]+(?:-[${LATIN}]+)*`, 'g')) || [];
    const lab = comps.map(c => { const ls = c.split('-').map(langOf); return ls.includes('P') ? 'P' : ls.includes('E') ? 'E' : ls.includes('B') ? 'B' : '?'; });
    const pc = lab.filter(x => x === 'P').length, ec = lab.filter(x => x === 'E').length;
    const runPali = PALI_MARK.test(run) || pc > ec;
    let k = 0;
    return run.replace(new RegExp(`[${LATIN}]+(?:-[${LATIN}]+)*`, 'g'), comp => {
      const l = lab[k++]; const pali = l === 'P' || ((l === 'B' || l === '?') && runPali && (l === 'B' || pc > 0));
      if (pali) return o.pali ? comp.split('-').map(w => PALI(w) || w).join(' ') : ' ';
      return o.en ? comp : ' ';
    });
  });
  if (!o.hanja) t = t.replace(/[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]+/g, ' ');
  // 한글 음역의 장음 표시(까라니-야, 삿따-)는 읽지 않음
  t = t.replace(/([가-힣])-(?=[가-힣\s,.!?)’”]|$)/g, '$1');
  // 특수부호: 읽기를 켜면 이름으로 읽고, 끄면 소리 내지 않음
  t = o.sym ? t.replace(SYM_RE, c => ` ${SYM_NAME[c] || ''} `) : t.replace(SYM_RE, ' ');
  return t.replace(/\(\s*\)/g, ' ').replace(/\s+([.,!?])/g, '$1').replace(/([.,!?])(?:\s*[.,])+/g, '$1').replace(/\s{2,}/g, ' ').trim();
}
const fnMark = h => h.replace(/^\[\^([^\]]+)\]:\s*/, '<sup class="fn-no">$1</sup> ').replace(/\[\^([^\]]+)\]/g, '<sup class="fn-ref">$1</sup>');
// 본문 속 그림 ![설명](주소) 과 표(| 칸 | 칸 |)
const FIG_RE = /^!\[([^\]]*)\]\(([^)\s]+)\)\s*$/;
const isTable = p => /^\|.*\|\s*$/m.test(p) && p.split('\n').filter(l => l.trim()).every(l => /^\|/.test(l.trim()));
function tableHtml(p) {
  const rows = p.split('\n').map(l => l.trim()).filter(l => l && !/^\|[\s:|-]+\|?$/.test(l)).map(l => l.replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
  if (!rows.length) return '';
  return `<table class="r-table"><thead><tr>${rows[0].map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.slice(1).map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
function blockHtml(s, n, k) {
  const f = s.match(FIG_RE);
  if (f) return `<figure class="r-fig" data-pg="${n}" data-s="${k}" data-skip="1"><button class="fig-btn" data-zoom-img="${esc(f[2])}" data-cap="${esc(f[1])}" aria-label="그림 크게 보기"><img src="${esc(f[2])}" alt="${esc(f[1])}" loading="lazy"></button>${f[1] ? `<figcaption>${esc(f[1])}</figcaption>` : ''}</figure>`;
  if (isTable(s)) return `<div class="r-tbl" data-pg="${n}" data-s="${k}" data-skip="1">${tableHtml(s)}<button class="tbtn sm" data-zoom-tbl>표 크게 보기</button></div>`;
  return null;
}
const isFootnote = p => /^\[\^[^\]]+\]:/.test(p);
// fromK: 그 쪽의 몇 번째 문단부터, firstText: 첫 문단은 이 글부터(고른 곳부터 읽기)
function speak(fromK = 0, firstText = null) {
  if (!('speechSynthesis' in window)) { toast('이 기기에서는 음성 읽기를 쓸 수 없습니다'); return; }
  if (!LEX.pali) { toast('읽기를 준비하는 중입니다…'); loadLex().then(() => speak(fromK, firstText)); return; }
  const o = ttsOpt();
  const p = R.pages[R.i]; const sentences = paras(p.text);
  if (!sentences.length) { if (R.i < R.pages.length - 1) { R.i++; renderReader(); setTimeout(() => speak(), 200); } return; }
  try { speechSynthesis.cancel(); } catch (e) {}
  if (!R.speaking) { R.ttsStart = Date.now(); R.ttsChapter = chapterOf(R.i + 1); }
  wake(true, 'tts');
  R.speaking = true; renderReader(); let k = Math.min(fromK, sentences.length - 1), first = firstText;
  const pv = pickVoice(o), voice = pv.voice;
  const next = () => {
    if (!R || !R.speaking) return;
    $$('.speaking').forEach(x => x.classList.remove('speaking'));
    if (o.sleep && Date.now() - R.ttsStart > o.sleep * 60000) { stopSpeak(true); toast('정한 시간이 되어 듣기를 멈췄습니다'); return; }
    if (k >= sentences.length) {
      if (R.i >= R.pages.length - 1) { stopSpeak(true); return; }
      if (o.chapterStop && chapterOf(R.i + 2) !== R.ttsChapter) { stopSpeak(true); toast('이 장을 다 읽었습니다'); return; }
      R.i++; renderReader(); speak(); return;
    }
    const raw = first && first.trim() ? first : sentences[k]; first = null;
    if ((!o.fn && isFootnote(sentences[k])) || FIG_RE.test(sentences[k]) || isTable(sentences[k])) { k++; next(); return; }
    const el = $(`[data-pg="${p.n}"][data-s="${k}"]`); if (el) { el.classList.add('speaking'); if (o.follow) el.scrollIntoView({ block: 'nearest' }); }
    const text = sayable(raw.replace(/^\[\^[^\]]+\]:\s*/, isFootnote(raw) ? '각주. ' : ''), o);
    if (!text) { k++; next(); return; }
    const u = new SpeechSynthesisUtterance(text); u.lang = voice ? voice.lang : 'ko-KR'; if (voice) u.voice = voice;
    u.rate = +o.rate; u.pitch = pv.pitch;
    u.onend = () => { if (!R || !R.speaking) return; k++; setTimeout(next, Math.max(0, +o.pause * 1000)); };
    u.onerror = e => { if (e.error !== 'interrupted' && e.error !== 'canceled') stopSpeak(true); };
    speechSynthesis.speak(u);
  };
  next();
}
function stopSpeak(rerender) { try { speechSynthesis.cancel(); } catch (e) {} wake(false, 'tts'); if (R) { R.ttsLocked = false; const was = R.speaking; R.speaking = false; if (rerender && was) renderReader(); } }
document.addEventListener('keydown', e => {
  if (!R || e.target.matches('input,select,textarea')) return;
  if (R.ttsLocked && e.key !== 'Tab') { if ([' ', 'ArrowRight', 'ArrowLeft', 'Escape'].includes(e.key)) { e.preventDefault(); toast('듣기가 잠겨 있습니다'); } return; }
  if (e.key === 'ArrowRight') go(R.i + 2); else if (e.key === 'ArrowLeft') go(R.i);
  else if (e.key === ' ' && $('#rSpeak')) { e.preventDefault(); R.speaking ? stopSpeak(true) : speak(); }
  else if (e.key === 'Escape') { if ($$('#reader .panel.open').length) $$('#reader .panel').forEach(x => x.classList.remove('open')); else exitReader(); }
});

/* ---------- 내 서재 ---------- */
// 읽기 기록 (이 기기에만)
function saveHistory(n) {
  if (!R) return; const h = store.get('hist', []).filter(x => x.id !== R.id), c = chapters()[chapterOf(n)];
  h.unshift({ id: R.id, t: R.title, by: R.by, p: n, pl: (R.pages[n - 1] || {}).label || '', ch: c && c.title || '', pct: Math.round(n / R.pages.length * 100), first: (store.get('hist', []).find(x => x.id === R.id) || {}).first || today(), d: today(), ts: Date.now() });
  store.set('hist', h.slice(0, 100));
}
let notesTab = 'read';
function renderNotes() {
  const root = $('#notesRoot'); if (!root) return;
  const U = uls(), B = bms();
  const groups = {}; U.forEach(h => (groups[h.id] = groups[h.id] || []).push(h));
  const ulHtml = Object.keys(groups).length ? Object.entries(groups).map(([id, l]) => `<div class="book-group"><h3>『${esc(l[0].t)}』</h3><div class="small muted">${esc(l[0].by)} · 밑줄 ${l.length}개</div>
    ${l.sort((a, c) => a.p - c.p).map(h => `<div class="note-item"><div class="meta"><a href="/read/${id}/${h.p}">${esc(h.pl || h.p)}쪽에서 보기 →</a><span>${esc(h.d || '')}</span></div><div class="quote">${esc(h.text)}</div>${h.note ? `<div class="memo">메모: ${esc(h.note)}</div>` : ''}
    <div class="acts"><button data-ncopy="${h.k}">출처와 함께 복사</button><button data-ndel="${h.k}">지우기</button></div></div>`).join('')}</div>`).join('')
    : `<p class="muted">아직 밑줄이 없습니다. 읽기 화면에서 글을 끌어서 고르면 ‘밑줄 긋기’ 단추가 나옵니다.</p>`;
  const bmHtml = B.length ? B.map((m, k) => `<div class="note-item"><div class="meta"><a href="/read/${m.id}/${m.p}">『${esc(m.t)}』 ${esc(m.pl || m.p)}쪽 →</a><span>${esc(m.d || '')}</span></div>${m.note ? `<div class="memo">${esc(m.note)}</div>` : ''}<div class="acts"><button data-bdel="${k}">지우기</button></div></div>`).join('') : '<p class="muted">아직 책갈피가 없습니다.</p>';
 const H = store.get('hist', []);
  const histHtml = H.length ? `<div class="hist">${H.map((x, k) => `<div class="hist-item"><a class="hist-cover" href="/book/${x.id}/" data-hc="${x.id}" aria-hidden="true" tabindex="-1"></a><div class="hist-body"><a class="hist-t" href="/book/${x.id}/">『${esc(x.t)}』</a><div class="small muted">${esc(x.by)}</div>
      <div class="hist-bar" aria-label="읽은 만큼 ${x.pct}%"><span style="width:${x.pct}%"></span></div>
      <div class="small">${esc(x.ch ? x.ch + ' · ' : '')}${esc(x.pl || x.p)}쪽 · ${x.pct}%</div>
      <div class="small muted">마지막으로 읽은 날 ${esc(x.d)}${x.first && x.first !== x.d ? ` · 처음 읽은 날 ${esc(x.first)}` : ''}</div>
      <div class="acts"><a class="btn sm" href="/read/${x.id}/${x.p}">이어 읽기</a><button data-hdel="${k}">기록 지우기</button></div></div></div>`).join('')}</div>` : '<p class="muted">아직 읽은 책이 없습니다. 책 페이지에서 ‘온라인으로 읽기’를 누르면 여기에 모입니다.</p>';
  root.innerHTML = `<div class="tabs" role="tablist"><button role="tab" data-ntb="read" class="${notesTab === 'read' ? 'on' : ''}">읽은 책 ${H.length}</button><button role="tab" data-ntb="ul" class="${notesTab === 'ul' ? 'on' : ''}">밑줄 ${U.length}</button><button role="tab" data-ntb="bm" class="${notesTab === 'bm' ? 'on' : ''}">책갈피 ${B.length}</button><button role="tab" data-ntb="io" class="${notesTab === 'io' ? 'on' : ''}">옮기기</button></div>
   <div style="max-width:760px">${notesTab === 'read' ? histHtml : notesTab === 'ul' ? (U.length ? `<div style="margin:12px 0"><button class="btn sm ghost" id="copyAll">밑줄 모두 복사 (출처 포함)</button></div>` : '') + ulHtml : notesTab === 'bm' ? bmHtml :
    `<p>다른 기기로 옮길 때: 아래 ‘내보내기’로 복사한 글을 다른 기기의 이 칸에 붙여넣고 ‘가져오기’를 누르세요. 가져오면 이미 있는 것과 합쳐집니다.</p>
    <div style="display:flex;gap:8px;margin:10px 0"><button class="btn sm ghost" id="ioExport">내보내기 (복사)</button><button class="btn sm" id="ioImport">가져오기</button></div>
    <label for="ioText" class="small muted">붙여넣을 곳</label><textarea class="io" id="ioText"></textarea>`}</div>`;
  $$('[data-ntb]', root).forEach(b => b.onclick = () => { notesTab = b.dataset.ntb; renderNotes(); });
  $$('[data-hdel]', root).forEach(b => b.onclick = () => { const h = store.get('hist', []); h.splice(+b.dataset.hdel, 1); store.set('hist', h); renderNotes(); });
  if ($('[data-hc]', root)) data().then(D => $$('[data-hc]', root).forEach(a => { const bk = D.books.find(x => x.id === a.dataset.hc); if (bk && bk.cover) a.innerHTML = `<img src="${esc(bk.cover)}" alt="">`; })).catch(() => {});
  $$('[data-ndel]', root).forEach(b => b.onclick = () => { store.set('ul', uls().filter(x => x.k !== +b.dataset.ndel)); renderNotes(); toast('밑줄을 지웠습니다'); });
  $$('[data-ncopy]', root).forEach(b => b.onclick = () => { const h = uls().find(x => x.k === +b.dataset.ncopy); copy(`“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽 (${SITE})`, '출처와 함께 복사했습니다'); });
  $$('[data-bdel]', root).forEach(b => b.onclick = () => { const l = bms(); l.splice(+b.dataset.bdel, 1); store.set('bm', l); renderNotes(); });
  const ca = $('#copyAll'); if (ca) ca.onclick = () => copy(uls().map(h => `“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽${h.note ? `\n  메모: ${h.note}` : ''}`).join('\n\n') + `\n\n(${SITE})`, '밑줄을 모두 복사했습니다');
  const ex = $('#ioExport'); if (ex) ex.onclick = () => copy(JSON.stringify({ ul: uls(), bm: bms(), hist: store.get('hist', []) }), '복사했습니다. 다른 기기의 가져오기 칸에 붙여넣으세요');
  const im = $('#ioImport'); if (im) im.onclick = () => {
    try {
      const d = JSON.parse($('#ioText').value);
      const u = uls(), b = bms();
      (d.ul || []).forEach(h => { if (!u.some(x => x.k === h.k)) u.push(h); });
      (d.bm || (Array.isArray(d) ? d : [])).forEach(m => { if (!b.some(x => x.id === m.id && x.p === m.p)) b.push(m); });
      const hh = store.get('hist', []); (d.hist || []).forEach(x => { if (!hh.some(y => y.id === x.id)) hh.push(x); }); hh.sort((a, c) => (c.ts || 0) - (a.ts || 0));
      store.set('ul', u); store.set('bm', b); store.set('hist', hh); toast('가져왔습니다'); notesTab = 'ul'; renderNotes();
    } catch (e) { toast('붙여넣은 글을 읽을 수 없습니다. 내보내기로 복사한 글 전체를 넣어 주세요'); }
  };
}

/* ---------- 시작 ---------- */
// 인터넷 없이 읽기 (서비스 워커)
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) navigator.serviceWorker.register('/sw.js').catch(() => {});
if ('speechSynthesis' in window) speechSynthesis.addEventListener && speechSynthesis.addEventListener('voiceschanged', () => { const v = $('#ttsVoice'); if (v) v.innerHTML = voiceOptions(ttsOpt().voice); });
initHeader();
initPlayer();
initPage();
})();
