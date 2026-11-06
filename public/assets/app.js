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
  markEp();
}
function initPlayer() {
  const a = $('#pAudio');
  $('#pRate').value = String(store.get('prate', 1));
  $('#pAuto').checked = store.get('pauto', true);
  $('#pPlay').onclick = () => { if (!PL.pl) { const l = store.get('plast'); if (l) playEp(l.pl, l.i, l.list); return; } a.paused ? a.play() : a.pause(); };
  $('#pNext').onclick = () => { if (PL.pl && PL.i < PL.list.length - 1) playEp(PL.pl, PL.i + 1, PL.list); };
  $('#pPrev').onclick = () => { if (!PL.pl) return; if (a.currentTime > 3) a.currentTime = 0; else if (PL.i > 0) playEp(PL.pl, PL.i - 1, PL.list); };
  $('#pSeek').oninput = e => { if (a.duration) a.currentTime = a.duration * e.target.value / 100; };
  $('#pRate').onchange = e => { a.playbackRate = +e.target.value; store.set('prate', +e.target.value); };
  $('#pAuto').onchange = e => store.set('pauto', e.target.checked);
  $('#pHide').onclick = () => { a.pause(); $('#player').classList.remove('show'); document.body.classList.remove('has-player'); };
  let last = 0;
  a.ontimeupdate = () => {
    $('#pCur').textContent = fmtT(a.currentTime); $('#pDur').textContent = fmtT(a.duration);
    if (a.duration) $('#pSeek').value = a.currentTime / a.duration * 100;
    if (PL.pl && Date.now() - last > 3000) { last = Date.now(); store.set('ppos-' + PL.list[PL.i].audio, a.currentTime); }
  };
  a.onplay = () => { $('#pPlay').textContent = '❚❚'; $('#pPlay').setAttribute('aria-label', '일시정지'); };
  a.onpause = () => { $('#pPlay').textContent = '▶'; $('#pPlay').setAttribute('aria-label', '재생'); };
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
const PRON = { 'mettā': '메따', 'metta': '메따', 'Mettā': '메따', 'Bhāvanā': '바와나', 'bhāvanā': '바와나', 'Dhamma': '담마', 'dhamma': '담마', 'Sutta': '숫따', 'sutta': '숫따', 'Nibbāna': '닙바나', 'nibbāna': '닙바나', 'sati': '사띠', 'vipassanā': '위빳사나', 'samatha': '사마타' };
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
    view: 'text', zoom: store.get('rzoom', 1), fs: store.get('rfs', 1), lh: store.get('rlh', 1.9), font: store.get('rfont', 'serif'),
    hl: hlp ? hlp.split('|').filter(Boolean) : [], speaking: false
  };
  if (!pages.some(p => p.text)) R.view = 'page';
  renderReader();
  if (!want && last > 1) toast(`지난번에 읽던 ${pageName(R.pages[R.i])}을 열었습니다`);
}
const pageName = p => p.label ? `${p.label}쪽` : `${p.n}번째 쪽`;
function closeReader() { stopSpeak(); R = null; const el = $('#reader'); if (el) el.remove(); document.body.style.overflow = ''; }
function exitReader() { const id = R && R.id; closeReader(); location.href = '/book/' + id + '/'; }
const paras = t => String(t || '').split(/\n\s*\n/).map(s => s.replace(/\s*\n\s*/g, ' ').trim()).filter(Boolean);
function markUl(s, n) {
  if (R.hl.length) return hl(s, R.hl);
  const rg = uls().filter(h => h.id === R.id && h.p === n && h.text && s.includes(h.text)).map(h => { const a = s.indexOf(h.text); return [a, a + h.text.length, h.k]; }).sort((x, y) => x[0] - y[0]);
  let out = '', p = 0; rg.forEach(([a, b, k]) => { if (a < p) return; out += esc(s.slice(p, a)) + `<u class="ul" data-hid="${k}" title="밑줄 · 눌러서 메모나 지우기">` + esc(s.slice(a, b)) + '</u>'; p = b; });
  return out + esc(s.slice(p));
}
function pageHtml(p) {
  if (!p.img) return `<div class="reflow ${R.font === 'sans' ? 'sans' : ''}" style="--fs:${R.fs};--lh:${R.lh}">${paras(p.text).map((s, k) => `<p data-pg="${p.n}" data-s="${k}">${markUl(s, p.n)}</p>`).join('') || '<p class="muted">빈 쪽입니다.</p>'}</div>`;
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
    return `<span class="pmark" id="pm-${p.n}">${esc(pageName(p))}</span>${ps.map((s, k) => `<p data-pg="${p.n}" data-s="${k}">${markUl(s, p.n)}</p>`).join('') || ''}`;
  }).join('');
  const nav = `<nav class="ch-nav" aria-label="장 이동">${ci > 0 ? `<button class="tbtn" data-go="${cs[ci - 1].from}">← ${esc(cs[ci - 1].title || '이전 장')}</button>` : '<span></span>'}${ci < cs.length - 1 ? `<button class="tbtn" data-go="${cs[ci + 1].from}">${esc(cs[ci + 1].title || '다음 장')} →</button>` : '<span></span>'}</nav>`;
  return `<div class="reflow ${R.font === 'sans' ? 'sans' : ''}" style="--fs:${R.fs};--lh:${R.lh}">${c.title ? `<div class="ch-head"><span class="small muted">${ci + 1} / ${cs.length}</span><h3>${esc(c.title)}</h3></div>` : ''}${body}${nav}</div>`;
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
      ${R.toc.length ? '<button class="tbtn" data-panel="toc">목차</button>' : ''}
      <button class="tbtn" data-panel="font" aria-label="글씨 크기">가<span style="font-size:16px">가</span></button>
      ${hasText ? `<button class="tbtn ${R.speaking ? 'on' : ''}" id="rSpeak">${R.speaking ? '■ 멈춤' : '▶ 듣기'}</button>` : ''}
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
    <div class="panel" id="p-toc"><h5>목차</h5><ul>${R.toc.map(t => `<li class="${/^\s/.test(t.title) ? 'sub' : ''}"><button class="link" data-go="${t.page}">${esc(t.title.trim())}</button><span class="muted">${esc(t.label || '')}</span></li>`).join('')}</ul></div>
    <div class="panel" id="p-font"><h5>글씨</h5>
      ${R.view === 'page' && hasImg ? `<div class="row">쪽 확대 <span><button class="tbtn" data-zoom="-1">−</button> ${Math.round(R.zoom * 100)}% <button class="tbtn" data-zoom="1">+</button></span></div>${hasText ? '<p class="note">쪽 보기에서는 원본 쪽을 확대합니다. 글자만 크게 보거나 밑줄을 그으려면 ‘글로 보기’로 바꾸세요.</p>' : ''}` :
      `<div class="row">글자 크기 <span class="seg">${[0.85, 1, 1.15, 1.3, 1.5].map((v, i) => `<button data-fs="${v}" class="${R.fs === v ? 'on' : ''}">${i + 1}</button>`).join('')}</span></div>
       <div class="row">줄 간격 <span class="seg">${[[1.6, '좁게'], [1.9, '보통'], [2.2, '넓게']].map(([v, l]) => `<button data-lh="${v}" class="${R.lh === v ? 'on' : ''}">${l}</button>`).join('')}</span></div>
       <div class="row">글꼴 <span class="seg"><button data-font="serif" class="${R.font === 'serif' ? 'on' : ''}">명조</button><button data-font="sans" class="${R.font === 'sans' ? 'on' : ''}">고딕</button></span></div>`}</div>
    <div class="panel" id="p-mode"><h5>화면 모드</h5><div class="seg">${[['day', '기본'], ['mono', '흑백'], ['night', '밤']].map(([k, v]) => `<button data-rmode="${k}" class="${store.get('mode', 'auto') === k ? 'on' : ''}">${v}</button>`).join('')}</div><p class="note">고른 모드는 사이트 전체에 적용되고 다음에 와도 유지됩니다.</p></div>
    <div class="panel" id="p-ul"><h5>이 책의 밑줄</h5><ul>${uls().filter(h => h.id === R.id).sort((a, b) => a.p - b.p).map(h => `<li style="display:block"><button class="link" data-go="${h.p}">${esc(h.pl || h.p)}쪽</button><div class="quote" style="font-size:13.5px">${esc(h.text)}</div>${h.note ? `<div class="small muted">${esc(h.note)}</div>` : ''}</li>`).join('') || '<li class="muted">글을 끌어서 고르면 밑줄을 그을 수 있습니다.</li>'}</ul>
      <div class="row"><a class="tbtn" href="/mynotes/">내 서재에서 모두 보기</a></div></div>
    <div class="panel" id="p-uledit"><h5>밑줄</h5><div class="quote" id="ulText" style="font-size:13.5px"></div>
      <div class="row"><input id="ulNote" placeholder="메모 한 줄" aria-label="밑줄 메모" style="flex:1;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 8px;background:var(--paper)"></div>
      <div class="row"><button class="tbtn" id="ulSave">메모 저장</button><button class="tbtn" id="ulCopy">출처와 함께 복사</button><button class="tbtn" id="ulDel">밑줄 지우기</button></div></div>
    <div class="sel-pop" id="selPop" role="toolbar" aria-label="고른 글"><button id="selUl">밑줄 긋기</button><button id="selNote">밑줄+메모</button><button id="selCopy">복사</button></div>
    <div class="panel" id="p-bm"><h5>내 책갈피</h5><ul>${bms().map((m, k) => `<li><span><a class="link" href="/read/${m.id}/${m.p}">『${esc(m.t)}』 ${esc(m.pl || m.p)}쪽</a>${m.note ? `<br><span class="muted small">${esc(m.note)}</span>` : ''}</span><button class="link" data-bmdel="${k}" aria-label="책갈피 지우기">지우기</button></li>`).join('') || '<li class="muted">아직 책갈피가 없습니다.</li>'}</ul>
      <div class="row" style="margin-top:12px"><input id="bmNote" placeholder="이 쪽에 한 줄 메모" aria-label="책갈피 메모" style="flex:1;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 8px;background:var(--paper)"><button class="tbtn" id="bmSave">저장</button></div>
      <p class="note">회원가입 없이 이 기기의 브라우저에만 저장됩니다. 다른 기기로 옮길 때는 내 서재의 ‘옮기기’를 쓰세요.</p></div>`;
  bindReader();
  if (R.view === 'text') { const c = chapters()[Math.max(0, chapterOf(n))]; const pm = $('#pm-' + n); if (pm && n !== c.from) pm.scrollIntoView({ block: 'start' }); else $('#rBody').scrollTop = 0; }
  // 다음 쪽 그림 미리 받기
  const nx = R.pages[R.i + 1]; if (nx && nx.img && R.view === 'page') { const im = new Image(); im.src = nx.img; }
  store.set('pos-' + R.id, n);
  history.replaceState(history.state, '', `/read/${R.id}/${n}` + location.search);
}
function go(n) { if (!R) return; R.i = Math.max(0, Math.min(R.pages.length - 1, n - 1)); stopSpeak(); renderReader(); if (R.view === 'page') $('#rBody').scrollTop = 0; }
function bindReader() {
  const el = $('#reader');
  const reopen = id => $('#' + id).classList.add('open');
  $('#rClose').onclick = exitReader;
  $('#rPrev').onclick = () => go(R.i); $('#rNext').onclick = () => go(R.i + 2); $('#rRange').onchange = e => go(+e.target.value);
  const ho = $('#hlOff'); if (ho) ho.onclick = () => { R.hl = []; history.replaceState(null, '', location.pathname); renderReader(); };
  
  $$('[data-panel]', el).forEach(b => b.onclick = () => { const p = $('#p-' + b.dataset.panel); const o = p.classList.contains('open'); $$('.panel', el).forEach(x => x.classList.remove('open')); if (!o) p.classList.add('open'); });
  $$('[data-go]', el).forEach(b => b.onclick = () => go(+b.dataset.go));
  $$('[data-zoom]', el).forEach(b => b.onclick = () => { R.zoom = Math.max(.75, Math.min(2.5, +(R.zoom + (+b.dataset.zoom) * .25).toFixed(2))); store.set('rzoom', R.zoom); renderReader(); reopen('p-font'); });
  $$('[data-fs]', el).forEach(b => b.onclick = () => { R.fs = +b.dataset.fs; store.set('rfs', R.fs); renderReader(); reopen('p-font'); });
  $$('[data-lh]', el).forEach(b => b.onclick = () => { R.lh = +b.dataset.lh; store.set('rlh', R.lh); renderReader(); reopen('p-font'); });
  $$('[data-font]', el).forEach(b => b.onclick = () => { R.font = b.dataset.font; store.set('rfont', R.font); renderReader(); reopen('p-font'); });
  $$('[data-rmode]', el).forEach(b => b.onclick = () => { applyMode(b.dataset.rmode); renderReader(); reopen('p-mode'); });
  const cur = () => R.pages[R.i];
  $('#rMark').onclick = () => { const l = bms(), n = cur().n, k = l.findIndex(m => m.id === R.id && m.p === n); if (k > -1) { l.splice(k, 1); toast('책갈피를 지웠습니다'); } else { l.push({ id: R.id, t: R.title, p: n, pl: cur().label, note: '', d: today() }); toast(`${pageName(cur())}에 책갈피를 달았습니다`); } store.set('bm', l); renderReader(); };
  $('#bmSave').onclick = () => { const l = bms(), n = cur().n; let m = l.find(m => m.id === R.id && m.p === n); if (!m) { m = { id: R.id, t: R.title, p: n, pl: cur().label, d: today() }; l.push(m); } m.note = $('#bmNote').value.trim(); store.set('bm', l); renderReader(); reopen('p-bm'); toast('메모를 저장했습니다'); };
  $$('[data-bmdel]', el).forEach(b => b.onclick = () => { const l = bms(); l.splice(+b.dataset.bmdel, 1); store.set('bm', l); renderReader(); reopen('p-bm'); });
  const sp = $('#rSpeak'); if (sp) sp.onclick = () => R.speaking ? stopSpeak(true) : speak();
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
function sayable(s) { let t = s; Object.entries(PRON).forEach(([k, v]) => { t = t.split(k).join(v); }); return t; }
function speak() {
  if (!('speechSynthesis' in window)) { toast('이 기기에서는 음성 읽기를 쓸 수 없습니다'); return; }
  const p = R.pages[R.i]; const sentences = paras(p.text);
  if (!sentences.length) { if (R.i < R.pages.length - 1) { R.i++; renderReader(); setTimeout(speak, 200); } return; }
  R.speaking = true; renderReader(); let k = 0;
  const next = () => {
    if (!R || !R.speaking) return;
    $$('.speaking').forEach(x => x.classList.remove('speaking'));
    if (k >= sentences.length) { if (R.i < R.pages.length - 1) { R.i++; renderReader(); speak(); } else stopSpeak(true); return; }
    const el = $(`[data-pg="${p.n}"][data-s="${k}"]`); if (el) { el.classList.add('speaking'); el.scrollIntoView({ block: 'nearest' }); }
    const u = new SpeechSynthesisUtterance(sayable(sentences[k])); u.lang = 'ko-KR'; u.rate = +store.get('rate', 1);
    u.onend = () => { k++; next(); }; u.onerror = () => stopSpeak(true);
    speechSynthesis.speak(u);
  };
  try { speechSynthesis.cancel(); } catch (e) {} next();
}
function stopSpeak(rerender) { try { speechSynthesis.cancel(); } catch (e) {} if (R) { const was = R.speaking; R.speaking = false; if (rerender && was) renderReader(); } }
document.addEventListener('keydown', e => {
  if (!R || e.target.matches('input,select,textarea')) return;
  if (e.key === 'ArrowRight') go(R.i + 2); else if (e.key === 'ArrowLeft') go(R.i);
  else if (e.key === ' ' && $('#rSpeak')) { e.preventDefault(); R.speaking ? stopSpeak(true) : speak(); }
  else if (e.key === 'Escape') { if ($$('#reader .panel.open').length) $$('#reader .panel').forEach(x => x.classList.remove('open')); else exitReader(); }
});

/* ---------- 내 서재 ---------- */
let notesTab = 'ul';
function renderNotes() {
  const root = $('#notesRoot'); if (!root) return;
  const U = uls(), B = bms();
  const groups = {}; U.forEach(h => (groups[h.id] = groups[h.id] || []).push(h));
  const ulHtml = Object.keys(groups).length ? Object.entries(groups).map(([id, l]) => `<div class="book-group"><h3>『${esc(l[0].t)}』</h3><div class="small muted">${esc(l[0].by)} · 밑줄 ${l.length}개</div>
    ${l.sort((a, c) => a.p - c.p).map(h => `<div class="note-item"><div class="meta"><a href="/read/${id}/${h.p}">${esc(h.pl || h.p)}쪽에서 보기 →</a><span>${esc(h.d || '')}</span></div><div class="quote">${esc(h.text)}</div>${h.note ? `<div class="memo">메모: ${esc(h.note)}</div>` : ''}
    <div class="acts"><button data-ncopy="${h.k}">출처와 함께 복사</button><button data-ndel="${h.k}">지우기</button></div></div>`).join('')}</div>`).join('')
    : `<p class="muted">아직 밑줄이 없습니다. 읽기 화면에서 글을 끌어서 고르면 ‘밑줄 긋기’ 단추가 나옵니다.</p>`;
  const bmHtml = B.length ? B.map((m, k) => `<div class="note-item"><div class="meta"><a href="/read/${m.id}/${m.p}">『${esc(m.t)}』 ${esc(m.pl || m.p)}쪽 →</a><span>${esc(m.d || '')}</span></div>${m.note ? `<div class="memo">${esc(m.note)}</div>` : ''}<div class="acts"><button data-bdel="${k}">지우기</button></div></div>`).join('') : '<p class="muted">아직 책갈피가 없습니다.</p>';
  root.innerHTML = `<div class="tabs" role="tablist"><button role="tab" data-ntb="ul" class="${notesTab === 'ul' ? 'on' : ''}">밑줄 ${U.length}</button><button role="tab" data-ntb="bm" class="${notesTab === 'bm' ? 'on' : ''}">책갈피 ${B.length}</button><button role="tab" data-ntb="io" class="${notesTab === 'io' ? 'on' : ''}">옮기기</button></div>
   <div style="max-width:760px">${notesTab === 'ul' ? (U.length ? `<div style="margin:12px 0"><button class="btn sm ghost" id="copyAll">밑줄 모두 복사 (출처 포함)</button></div>` : '') + ulHtml : notesTab === 'bm' ? bmHtml :
    `<p>다른 기기로 옮길 때: 아래 ‘내보내기’로 복사한 글을 다른 기기의 이 칸에 붙여넣고 ‘가져오기’를 누르세요. 가져오면 이미 있는 것과 합쳐집니다.</p>
    <div style="display:flex;gap:8px;margin:10px 0"><button class="btn sm ghost" id="ioExport">내보내기 (복사)</button><button class="btn sm" id="ioImport">가져오기</button></div>
    <label for="ioText" class="small muted">붙여넣을 곳</label><textarea class="io" id="ioText"></textarea>`}</div>`;
  $$('[data-ntb]', root).forEach(b => b.onclick = () => { notesTab = b.dataset.ntb; renderNotes(); });
  $$('[data-ndel]', root).forEach(b => b.onclick = () => { store.set('ul', uls().filter(x => x.k !== +b.dataset.ndel)); renderNotes(); toast('밑줄을 지웠습니다'); });
  $$('[data-ncopy]', root).forEach(b => b.onclick = () => { const h = uls().find(x => x.k === +b.dataset.ncopy); copy(`“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽 (${SITE})`, '출처와 함께 복사했습니다'); });
  $$('[data-bdel]', root).forEach(b => b.onclick = () => { const l = bms(); l.splice(+b.dataset.bdel, 1); store.set('bm', l); renderNotes(); });
  const ca = $('#copyAll'); if (ca) ca.onclick = () => copy(uls().map(h => `“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽${h.note ? `\n  메모: ${h.note}` : ''}`).join('\n\n') + `\n\n(${SITE})`, '밑줄을 모두 복사했습니다');
  const ex = $('#ioExport'); if (ex) ex.onclick = () => copy(JSON.stringify({ ul: uls(), bm: bms() }), '복사했습니다. 다른 기기의 가져오기 칸에 붙여넣으세요');
  const im = $('#ioImport'); if (im) im.onclick = () => {
    try {
      const d = JSON.parse($('#ioText').value);
      const u = uls(), b = bms();
      (d.ul || []).forEach(h => { if (!u.some(x => x.k === h.k)) u.push(h); });
      (d.bm || (Array.isArray(d) ? d : [])).forEach(m => { if (!b.some(x => x.id === m.id && x.p === m.p)) b.push(m); });
      store.set('ul', u); store.set('bm', b); toast('가져왔습니다'); notesTab = 'ul'; renderNotes();
    } catch (e) { toast('붙여넣은 글을 읽을 수 없습니다. 내보내기로 복사한 글 전체를 넣어 주세요'); }
  };
}

/* ---------- 시작 ---------- */
initHeader();
initPlayer();
initPage();
})();
