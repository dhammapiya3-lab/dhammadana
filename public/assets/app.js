/* 테라와다불교 법보시 도서관 — 화면 동작
   - 화면 모드, 페이지 사이 부드러운 이동(법문 재생이 끊기지 않도록), 도서관 찾아보기, 검색(표기 사전), 읽기 화면, 내 서재, 법문 재생기 */
(function () {
'use strict';
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  get(k, d) { try { const v = localStorage.getItem('dd-' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('dd-' + k, JSON.stringify(v)); } catch (e) {} try { syncMark(k); } catch (e) {} }
};
const SITE = 'dhammadana.kr';
// 카카오톡·네이버·인스타그램 등 앱 안 브라우저는 음성 읽기(speechSynthesis)를 막아 둠 → 크롬·삼성 인터넷·사파리로 열도록 안내
const inApp = () => /KAKAOTALK|NAVER\(inapp|Instagram|FBAN|FBAV|Line\/|everytimeApp|BAND\//i.test(navigator.userAgent);
function openOutside() {
  const u = location.href, ua = navigator.userAgent;
  if (/KAKAOTALK/i.test(ua)) { location.href = 'kakaotalk://web/openExternal?url=' + encodeURIComponent(u); return; }
  if (/Android/i.test(ua)) { location.href = 'intent://' + u.replace(/^https?:\/\//, '') + '#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=' + encodeURIComponent(u) + ';end'; return; }
  copy(u, '주소를 복사했습니다. 사파리를 열고 주소창에 붙여넣어 주세요');
}
function noVoice() {
  if (!inApp()) return toast('이 브라우저에서는 음성 읽기를 쓸 수 없습니다. 크롬·삼성 인터넷·사파리에서 열어 주세요');
  const old = $('#nvBox'); if (old) old.remove();
  const d = document.createElement('div'); d.id = 'nvBox'; d.className = 'nv-box';
  d.innerHTML = `<p><b>이 화면(앱 안 브라우저)에서는 듣기를 쓸 수 없습니다.</b><br>카카오톡·네이버 같은 앱 안에서 연 화면은 음성 읽기가 막혀 있습니다. 휴대폰의 기본 브라우저로 열면 들으실 수 있습니다.</p><div class="nv-b"><button class="btn" id="nvGo">${/iPhone|iPad/i.test(navigator.userAgent) && !/KAKAOTALK/i.test(navigator.userAgent) ? '주소 복사하기' : '다른 브라우저로 열기'}</button><button class="btn ghost" id="nvX">닫기</button></div>`;
  document.body.appendChild(d); $('#nvGo').onclick = openOutside; $('#nvX').onclick = () => d.remove();
}
function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('show'); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 2800); }
function copy(text, msg) { (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => toast(msg)).catch(() => toast('복사할 수 없는 환경입니다. 길게 눌러 직접 복사해 주세요')); }
const today = () => new Date().toLocaleDateString('sv-SE');

/* ---------- 사이트 자료 (검색·서재) ---------- */
let DATA = null;
function data() { return DATA || (DATA = fetch('/data/site.json').then(r => r.json())); }
const manifests = {};
function manifest(url) { return manifests[url] || (manifests[url] = fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })); }

/* 글자 맞추기: 빨리어 점·막대 없애고 한글은 붙여서 비교 */
const norm = s => String(s || '').replace(/[\u302c\u302d\u1dc0-\u1dff\u2033\u02ba\u02d1\u02d4\u02d5\ufe00-\ufe0f\ufe20-\ufe2f\ue900-\ue906]/g, '').replace(/\ue907/g, 'ㄴ').normalize('NFD')  // 빠알리어 한글 표기 부호(〬 〭 ᷇ ̫ ″ ˑ 등)는 찾을 때 무시 — '식카빠당'으로 '식카᷇빠당'을 찾음 (운영자 요청, 2026-11-11)
  .replace(/[̀-̣̱ͯ̇]/g, '').normalize('NFC').toLowerCase().replace(/\s+/g, ' ').trim();

/* ---------- 화면 모드 ---------- */
function applyMode(m) {
  const r = document.documentElement; r.classList.remove('mode-day', 'mode-mono', 'mode-night', 'mode-contrast');
  if (m !== 'auto') r.classList.add('mode-' + m);
  store.set('mode', m); $$('#modePop button').forEach(b => { b.classList.toggle('on', b.dataset.mode === m); b.setAttribute('role', 'menuitemradio'); b.setAttribute('aria-checked', b.dataset.mode === m); });
}
function initHeader() {
  const btn = $('#modeBtn'), pop = $('#modePop');
  btn.onclick = e => { e.stopPropagation(); const o = pop.classList.toggle('open'); btn.setAttribute('aria-expanded', o); };
  $$('button', pop).forEach(b => b.onclick = () => { applyMode(b.dataset.mode); pop.classList.remove('open'); btn.setAttribute('aria-expanded', false); });
  document.addEventListener('click', () => pop.classList.remove('open'));
  applyMode(store.get('mode', 'auto'));
  const fb = $('#fsBtn'), fp = $('#fsPop');
  const setFs = n => { const r = document.documentElement; r.classList.remove('sfs-1', 'sfs-2'); if (n > 0) r.classList.add('sfs-' + n); store.set('sitefs', n); $$('button', fp).forEach(b => { b.classList.toggle('on', +b.dataset.sfs === n); b.setAttribute('aria-checked', +b.dataset.sfs === n); }); };
  if (fb) {
    fb.onclick = e => { e.stopPropagation(); pop.classList.remove('open'); const o = fp.classList.toggle('open'); fb.setAttribute('aria-expanded', o); };
    btn.addEventListener('click', () => fp.classList.remove('open'));
    $$('button', fp).forEach(b => { b.setAttribute('role', 'menuitemradio'); b.onclick = () => { setFs(+b.dataset.sfs); fp.classList.remove('open'); fb.setAttribute('aria-expanded', false); }; });
    document.addEventListener('click', () => fp.classList.remove('open'));
    setFs(+store.get('sitefs', 0) || 0);
  }
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
    lastDoc = location.pathname + location.search;
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
// 같은 페이지 안에서 # 만 바뀐 경우(학습 자료실 자료 소개·읽기 화면 등)는 다시 불러오지 않음
let lastDoc = location.pathname + location.search;
window.addEventListener('popstate', () => {
  if (document.body.classList.contains('simple-ui')) { const hs = history.state || {};
    if (hs.sb) { if (STALK.playing()) { const pr = hs.prev || '/simple/'; sGo(pr, false).then(() => { const up = ($('#sUp') || {}).href || ''; try { if (up && new URL(up).pathname !== new URL(pr, location.href).pathname) { history.replaceState({ sb: 1, prev: up }, '', pr); history.pushState({ sp: 1 }, '', pr); } else history.replaceState({}, '', pr); } catch (e) {} lastDoc = location.pathname + location.search; }); /* 듣는 동안 뒤로 가기를 거듭하면 한 단계씩 위 목록으로 */ } else history.back(); return; }  // 처음 화면의 뒤로 가기
    if ($('#sRead') && location.pathname === lastDoc.split('?')[0]) { lastDoc = location.pathname + location.search; return; }  /* 같은 책 읽기 화면 안의 장 이동은 아래 initSimpleRead 쪽에서 */
    if (STALK.playing() && location.pathname + location.search !== lastDoc) { sGo(location.href, false); return; } } if (AB.locked || AB.skipPop) { AB.skipPop = false; return; } /* 오디오북 잠금 중 — 아래 오디오북 쪽에서 막음 */ const now = location.pathname + location.search; if (now === lastDoc) return; lastDoc = now;
  if (PL.pl && !$('#pAudio').paused) softGo(location.href, false); else location.reload(); });

/* ---------- 페이지별 시작 ---------- */
function initPage() {
  const p = $('#app').dataset.page;
  if (p === 'library') initLibrary();
  if (p === 'search') initSearch();
  if (p === 'talks') initTalks();
  if (p === 'mynotes') renderNotes();
  if (p === 'reader') initReaderPage();
  if (p === 'book') initBook();
  if (p === 'members') initMembers();
  if (p === 'account') initAccount();
  acctBtn();
  $$('[data-permit]').forEach(b => b.onclick = () => lightbox(b.dataset.permit, b.dataset.title));
}

/* ---------- 학습 자료실 ---------- */
// 법보시 도서관과 같은 짜임: 왼쪽 찾아보기(출판사·책 형식·주제) + 표지 카드, 누르면 자료 소개와 파일.
// 자료 정보는 비공개 창고의 _catalog.json (관리자 화면 '학습 자료실 관리'에서 입력). 정보 없는 파일은 아래 '분류하지 않은 자료'.
async function initMembers() {
  const root = $('#membersRoot');
  let cfg = { publishers: [], book_types: [], topics: [] };
  try { cfg = JSON.parse($('#studyCfg').textContent); } catch (e) {}
  const size = n => n > 1048576 ? (n / 1048576).toFixed(1) + 'MB' : Math.max(1, Math.round(n / 1024)) + 'KB';
  const icon = k => /\.(mp3|m4a|wav)$/i.test(k) ? '🎧' : /\.(mp4|mov)$/i.test(k) ? '🎬' : /\.(jpe?g|png|webp|gif)$/i.test(k) ? '🖼' : /\.pdf$/i.test(k) ? '📕' : /\.epub$/i.test(k) ? '📗' : /\.(hwpx?|docx?)$/i.test(k) ? '📘' : '📄';
  const url = k => '/study/file/' + k.split('/').map(encodeURIComponent).join('/');
  const kind = k => (k.split('.').pop() || '').toUpperCase();
  let j;
  try { const r = await fetch('/study/api/list', { cache: 'no-store' }); if (!r.ok) throw 0; j = await r.json(); } catch (e) { root.innerHTML = '<p class="muted">목록을 불러오지 못했습니다. 새로고침해 주세요.</p>'; return; }
  const who = j.email ? `<p class="small muted">${esc(j.email)} 로 들어왔습니다 · <a href="/cdn-cgi/access/logout">나가기</a></p>` : '';
  const head = `<div class="prose" style="padding-bottom:0"><h1>학습 자료실</h1><p class="muted">허락받은 분만 보는 곳입니다. 이 곳의 자료는 다른 분께 넘기지 말아 주세요.</p>${who}</div>`;
  j.files = j.files.filter(f => !/\.gz$/i.test(f.key));
  const fileSet = new Set([...j.files.map(f => f.key), ...((j.catalog || {}).items || []).map(it => it.text).filter(Boolean)]), fileBy = Object.fromEntries(j.files.map(f => [f.key, f]));
  const items = ((j.catalog || {}).items || []).filter(it => it && it.title).map(it => ({ ...it, files: (it.files || []).filter(k => fileSet.has(k)) }));
  const used = new Set(items.flatMap(it => [...it.files, it.cover || '']));
  const loose = j.files.filter(f => !used.has(f.key));
  const fileRow = f => { const n = f.key.split('/').pop(), au = /\.(mp3|m4a|wav)$/i.test(n); return `<li><span class="mb-ic">${icon(n)}</span><div class="mb-b"><a href="${url(f.key)}" target="_blank" rel="noopener">${esc(n)}</a> <span class="small muted">${size(f.size)}</span> · <a class="small" href="${url(f.key)}?dl">내려받기</a>${au ? `<audio controls preload="none" src="${url(f.key)}"></audio>` : ''}</div></li>`; };
  const looseHtml = () => { if (!loose.length) return ''; const g = {}; loose.forEach(f => { const i = f.key.lastIndexOf('/'); const d = i > 0 ? f.key.slice(0, i) : ''; (g[d] = g[d] || []).push(f); });
    return `<section class="study-loose"><h2 class="mb-h" style="margin-top:36px">분류하지 않은 자료</h2>` + Object.keys(g).sort((a, b) => a.localeCompare(b, 'ko')).map(d => `<section class="mb-group"><h3 class="small muted" style="margin:10px 0 0">📁 ${esc(d || '자료')}</h3><ul class="mb-list">${g[d].sort((a, b) => a.key.localeCompare(b.key, 'ko')).map(fileRow).join('')}</ul></section>`).join('') + '</section>'; };
  if (!items.length && !loose.length) { root.innerHTML = head + '<p class="muted">아직 올라온 자료가 없습니다.</p>'; return; }
  const cnt = (f, v) => items.filter(it => f === 'topic' ? (it.topics || []).includes(v) : it[f] === v).length;
  const chk = (f, v) => { const n = cnt(f, v); return `<label class="${n ? '' : 'zero'}"><input type="checkbox" data-sf="${f}" value="${esc(v)}">${esc(v)}<span class="n">${n}</span></label>`; };
  const others = (f, list) => [...new Set(items.map(it => it[f]).filter(v => v && !list.includes(v)))];
  const topics = (cfg.topics || []).map(gr => { const n = gr.labels.reduce((a, l) => a + cnt('topic', l), 0); return `<details class="fgroup"${n ? ' open' : ''}><summary class="group-name">${esc(gr.name)} <span class="n">${n}</span></summary>${gr.labels.map(l => chk('topic', l)).join('')}</details>`; }).join('');
  const card = it => `<a class="book" href="#${esc(it.id)}" data-id="${esc(it.id)}" data-title="${esc(it.title)}" data-added="${esc(it.added || '')}">
    <div class="cover">${it.cover && fileSet.has(it.cover) ? `<img class="cover-img" src="${url(it.cover)}" alt="${esc(it.title)} 표지" loading="lazy">` : `<div class="cover-ph">${esc(it.title)}</div>`}</div>
    <div class="t">${esc(it.title)}</div><div class="a">${esc([it.author, it.translator].filter(Boolean).join(' | '))}</div>
    <div class="fmt">${[it.publisher, it.book_type].filter(Boolean).map(x => `<span>${esc(x)}</span>`).join('')}</div>${it.text ? `<div class="small st-cardread" role="link" tabindex="0" data-read="${esc(it.id)}" style="margin-top:4px;color:var(--robe);text-decoration:underline;cursor:pointer">📖 사이트에서 읽기</div>` : ''}<div class="snip small muted" hidden></div></a>`;
  root.innerHTML = head + (items.length ? `<div class="lib" style="margin-top:18px"><details class="filter-toggle" open><summary>찾아보기</summary><div class="filters">
      <h3>출판사</h3>${[...cfg.publishers, ...others('publisher', cfg.publishers)].map(v => chk('publisher', v)).join('')}
      <h3>책 형식</h3>${[...cfg.book_types, ...others('book_type', cfg.book_types)].map(v => chk('book_type', v)).join('')}
      <h3>주제</h3>${topics}
    </div></details>
    <section><div class="toolbar"><div><div class="muted small">자료 <span id="stCount">${items.length}</span>개</div></div>
      <label class="small"><input id="stQ" type="search" placeholder="제목·지은이·본문으로 찾기" style="height:34px;padding:0 10px;border:1px solid var(--line);border-radius:8px;background:var(--paper);min-width:180px"></label>
      <label class="small">정렬 <select id="stSort"><option value="new">최근 등록순</option><option value="title">제목 가나다순</option></select></label></div>
      <div class="active-filters" id="stActive"></div><p class="small muted" id="stTx" hidden>책 본문에서 찾는 중…</p>
      <div class="grid" id="stGrid">${items.map(card).join('')}</div>
      <p class="muted" id="stEmpty" hidden>조건에 맞는 자료가 없습니다. 찾아보기를 줄여 보세요.</p>
    </section></div>` : '') + looseHtml() + `<div id="stDetail" hidden></div>`;
  const byId = Object.fromEntries(items.map(it => [it.id, it]));
  // 본문 찾기: Claude 가 뽑아 둔 본문 글(_text/…txt)을 찾는 순간에만 받아 옴
  const TX = {}, TXF = {}; let txLoading = false;
  // 빠알리어 발음 기호를 빼고 찾기 (ā→a, ñ→n …): 글자 수가 같게 바꿔 찾은 자리를 원문에 그대로 표시
  const fold = t => { let o = ''; for (const c of t) { const d = c.normalize('NFD'); o += (d.length > 1 && /^[a-zA-Z][\u0300-\u036f]+$/.test(d) ? d[0] : c).toLowerCase().replace(/\s/, ' '); } return o; };
  const loadTexts = async () => { txLoading = true; const st = $('#stTx'); if (st) st.hidden = false;
    const get = async k => { const r = await fetch(url(k)); if (!r.ok) return '';
      if (/\.gz$/i.test(k) && 'DecompressionStream' in window) return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
      return r.text(); };
    await Promise.all(items.filter(it => it.text && TX[it.id] == null).map(it => get(it.text).catch(() => '').then(t => { TX[it.id] = t; TXF[it.id] = fold(t); })));
    txLoading = false; if (st) st.hidden = true; };
  const pageOfHit = (id, q) => { const t = TX[id] || '', i = (TXF[id] || fold(t)).indexOf(fold(q.trim())); return i < 0 ? 1 : (t.slice(0, i).match(/^=== .+? ===$/gm) || []).length + 1; };
  const findSnip = (id, q) => { q = q.trim(); if (!q) return ''; const t = TX[id], f = TXF[id] || fold(t); const i = f.indexOf(fold(q)); if (i < 0) return '';
    let n = 0, j = -1; while ((j = f.indexOf(fold(q), j + 1)) >= 0 && n < 999) n++;
    const pg = (t.slice(0, i).match(/=== [^=\n]+ ===/g) || []).pop(); const a = Math.max(0, i - 50), mk = /=== [^=\n]+ ===|⟦[^⟧]*⟧/g;
    return `${pg ? `<b>${esc(pg.replace(/=/g, '').trim())}${/^\d+$/.test(pg.replace(/[=\s]/g, '')) ? '쪽' : ''}</b> ` : ''}…${esc(t.slice(a, i).replace(mk, ' '))}<mark>${esc(t.slice(i, i + q.length))}</mark>${esc(t.slice(i + q.length, i + q.length + 60).replace(mk, ' '))}…${n > 1 ? ` <span class="small muted">(이 자료에 ${n >= 999 ? '999+' : n}번)</span>` : ''}`; };
  const norm = x => String(x || '').toLowerCase().replace(/\s+/g, '');
  const run = () => {
    const sel = {}; $$('[data-sf]:checked', root).forEach(c => (sel[c.dataset.sf] = sel[c.dataset.sf] || []).push(c.value));
    const q = norm(($('#stQ') || {}).value); let shown = 0;
    $$('#stGrid .book', root).forEach(el => { const it = byId[el.dataset.id];
      let ok = (!sel.publisher || sel.publisher.includes(it.publisher)) && (!sel.book_type || sel.book_type.includes(it.book_type)) && (!sel.topic || sel.topic.some(t => (it.topics || []).includes(t)));
      let snip = '';
      if (ok && q) { ok = norm([it.title, it.author, it.translator, it.publisher, it.description, (it.topics || []).join(' ')].join(' ')).includes(q);
        if (!ok && TX[it.id]) { snip = findSnip(it.id, ($('#stQ') || {}).value || ''); ok = !!snip; } }
      const sn = $('.snip', el); if (sn) { sn.hidden = !snip; sn.innerHTML = snip; }
      el.setAttribute('href', snip ? `#${it.id}/read/${pageOfHit(it.id, ($('#stQ') || {}).value || '')}` : `#${it.id}`);
      el.hidden = !ok; if (ok) shown++; });
    STQ.q = (($('#stQ') || {}).value || '').trim();
    if (q && q.length >= 2 && !txLoading && items.some(it => it.text && TX[it.id] == null)) loadTexts().then(run);
    if ($('#stCount')) { $('#stCount').textContent = shown; $('#stEmpty').hidden = shown > 0; }
    const af = $('#stActive'); if (!af) return;
    const on = $$('[data-sf]:checked', root);
    af.innerHTML = on.length ? on.map(c => `<button data-un="${esc(c.dataset.sf)}|${esc(c.value)}">${esc(c.value)} ✕</button>`).join('') + '<button data-un="*">모두 지우기</button>' : '';
    $$('button', af).forEach(x => x.onclick = () => { $$('[data-sf]', root).forEach(c => { if (x.dataset.un === '*' || x.dataset.un === c.dataset.sf + '|' + c.value) c.checked = false; }); run(); });
  };
  // 카드의 '📖 사이트에서 읽기'는 자료 소개를 거치지 않고 바로 읽기 화면으로
  root.addEventListener('click', e => { const r = e.target.closest('[data-read]'); if (!r) return; e.preventDefault(); e.stopPropagation(); location.hash = '#' + encodeURIComponent(r.dataset.read) + '/read'; });
  root.addEventListener('keydown', e => { const r = e.target.closest && e.target.closest('[data-read]'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); location.hash = '#' + encodeURIComponent(r.dataset.read) + '/read'; } });
  $$('[data-sf]', root).forEach(c => c.onchange = run);
  if ($('#stQ')) $('#stQ').oninput = run;
  if ($('#stSort')) $('#stSort').onchange = () => { const g = $('#stGrid'), v = $('#stSort').value; $$('.book', g).sort((a, b) => v === 'title' ? a.dataset.title.localeCompare(b.dataset.title, 'ko') : v === 'author' ? ((a.dataset.author || '').localeCompare(b.dataset.author || '', 'ko') || (+a.dataset.ord || 0) - (+b.dataset.ord || 0)) : (b.dataset.added || '').localeCompare(a.dataset.added || '')).forEach(x => g.appendChild(x)); };
  if ($('#stSort')) $('#stSort').onchange();
  if (window.innerWidth < 520 && $('.filter-toggle', root)) $('.filter-toggle', root).open = false;
  const detail = () => {
    const hp = decodeURIComponent(location.hash.slice(1)).split('/');
    const it = byId[hp[0]], d = $('#stDetail');
    const parts = [$('.lib', root), $('.study-loose', root)].filter(Boolean);
    if (!it) { d.hidden = true; parts.forEach(x => x.hidden = false); return; }
    parts.forEach(x => x.hidden = true); d.hidden = false;
    if (hp[1] === 'read' && it.text) { studyReader(d, it, hp[2] ? +hp[2] : null, stPairsOf(it, byId)); return; }
    const fl = it.files.map(k => fileBy[k]).filter(Boolean);
    d.innerHTML = `<p style="margin-top:18px"><a href="#" id="stBack">← 학습 자료실 목록</a></p>
      <div class="study-book"><div class="cover">${it.cover && fileSet.has(it.cover) ? `<img src="${url(it.cover)}" alt="${esc(it.title)} 표지">` : `<div class="cover-ph">${esc(it.title)}</div>`}</div>
      <div><h1 style="margin:0 0 6px">${esc(it.title)}</h1>${it.subtitle ? `<p class="muted" style="margin:0 0 8px">${esc(it.subtitle)}</p>` : ''}
        <dl class="kv">${it.author ? `<dt>지은이·스승</dt><dd>${esc(it.author)}</dd>` : ''}${it.translator ? `<dt>옮긴이·편자</dt><dd>${esc(it.translator)}</dd>` : ''}${it.publisher ? `<dt>출판사</dt><dd>${esc(it.publisher)}</dd>` : ''}${it.book_type ? `<dt>책 형식</dt><dd>${esc(it.book_type)}</dd>` : ''}${it.year ? `<dt>펴낸 해</dt><dd>${esc(it.year)}</dd>` : ''}</dl>
        ${(it.topics || []).length ? `<div class="labels">${it.topics.map(t => `<span class="t">${esc(t)}</span>`).join('')}</div>` : ''}
        <div class="study-dl">${it.text ? `<a class="btn st-readbtn" href="#${esc(it.id)}/read">📖 사이트에서 읽기</a>` : ''}${fl.map(f => `${it.text && /\.(txt|md)$/i.test(f.key) ? '' : `<a class="btn${it.text ? ' ghost' : ''}" href="${url(f.key)}" target="_blank" rel="noopener">${icon(f.key)} ${esc(kind(f.key))} 열기</a>`}<a class="btn ghost" href="${url(f.key)}?dl">${it.text && /\.(txt|md)$/i.test(f.key) ? '글 파일 내려받기' : '내려받기'} <span class="small">${size(f.size)}</span></a>`).join('') || (it.text ? '' : '<p class="muted">파일 준비 중</p>')}</div>
      </div></div>
      ${it.description ? `<h2 class="mb-h" style="margin-top:28px">소개</h2><div class="prose" style="padding:0">${esc(it.description).split(/\n{2,}/).map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('')}</div>` : ''}
      ${fl.length > 1 ? `<h2 class="mb-h" style="margin-top:28px">파일</h2><ul class="mb-list">${fl.map(fileRow).join('')}</ul>` : ''}`;
    $('#stBack').onclick = e => { e.preventDefault(); history.pushState(null, '', location.pathname + location.search); detail(); };
    scrollTo(0, 0);
  };
  window.addEventListener('hashchange', detail); detail();
}

/* ---------- 학습 자료실 읽기 화면 ---------- */
// 본문 글(=== 쪽 표시 === 로 나뉜 .txt / .txt.gz)을 쪽마다 보여 줌. 글자는 원문 그대로, 모양만 바꿈.
// 쪽 이름(예: 'Vin I 23')이 쪽의 열쇠라서, 나중에 번역본도 같은 쪽 이름으로 나란히 붙일 수 있음.
const STQ = { q: '' }, STX = {};
const stFold = t => { let o = ''; for (const c of t) { const d = c.normalize('NFD'); o += (d.length > 1 && /^[a-zA-Z][̀-ͯ]+$/.test(d) ? d[0] : c).toLowerCase().replace(/\s/, ' '); } return o; };
async function stLoad(k) {
  if (STX[k]) return STX[k];
  const u = '/study/file/' + k.split('/').map(encodeURIComponent).join('/'), r = await fetch(u); if (!r.ok) throw 0;
  const t = /\.gz$/i.test(k) && 'DecompressionStream' in window ? await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text() : await r.text();
  const parts = t.split(/^=== (.+?) ===$/m), pages = [{ label: '앞부분', text: parts[0] }];
  for (let i = 1; i < parts.length; i += 2) pages.push({ label: parts[i], text: parts[i + 1] || '' });
  pages.forEach(p => { p.f = stFold(p.text); });
  if (!pages[0].text.trim()) pages.shift();
  return (STX[k] = pages);
}
// 대조할 판본들: 자료 정보의 pairs(또는 pair), 없으면 이름 규칙(…-pts-N ↔ …-bjt-N ↔ …-vri-N)
const ED_RE = /-(pts|bjt|vri)-/;
const stEdOf = it => it.edition_label || ({ pts: 'PTS', bjt: 'BJT', vri: 'VRI 6차 결집' }[(String(it.id).match(ED_RE) || [])[1]] || '대조 판본');
function stPairsOf(it, byId) {
  const ids = it.pairs || (it.pair ? [it.pair] : ED_RE.test(it.id) ? ['pts', 'bjt', 'vri'].map(e => it.id.replace(ED_RE, `-${e}-`)).filter(x => x !== it.id) : []);
  return ids.map(x => byId[x]).filter(x => x && x.text);
}
// 문장 나누기: 원문을 한 글자도 바꾸지 않고 자르기만 함 (자른 조각을 이으면 원문 그대로)
function stSents(t) {
  const out = []; let cur = '';
  const re = /(\|\|[\d\s]*\|\||[.?!](?:["'”’]+)?(?=\s)|\n\s*\n)/g; let last = 0, m;
  while ((m = re.exec(t))) { const end = m.index + m[0].length; const ws = /^\s*/.exec(t.slice(end))[0]; out.push(t.slice(last, end + ws.length)); last = end + ws.length; re.lastIndex = last; }
  if (last < t.length) out.push(t.slice(last));
  const merged = []; for (const x of out) { if (merged.length && x.replace(/[^A-Za-zÀ-ɏḀ-ỿ]/g, '').length < 4) merged[merged.length - 1] += x; else merged.push(x); }
  return merged.filter(x => x.length);
}
// 두 판본 문장 짝짓기 (철자·부호 차이는 무시하고 글자 세 개씩 묶어 비슷한 정도로 비교, 순서는 지킴)
function stAlign(A, B) {
  const nf = x => x.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z]/g, '');
  const gr = x => { const s = nf(x), g = new Set(); for (let i = 0; i < s.length - 2; i++) g.add(s.slice(i, i + 3)); return g; };
  const sim = (x, y) => { if (!x.size || !y.size) return 0; let c = 0; for (const g of x) if (y.has(g)) c++; return 2 * c / (x.size + y.size); };
  const GA = A.map(gr), GB = B.map(gr), n = A.length, m = B.length;
  const S = Array.from({ length: n + 1 }, () => new Float64Array(m + 1)), K = Array.from({ length: n + 1 }, () => new Int8Array(m + 1));
  const u = (a, b) => { const g = new Set(a); for (const x of b) g.add(x); return g; };
  for (let i = 0; i <= n; i++) for (let j = 0; j <= m; j++) {
    if (!i && !j) continue; let best = -1, k = 0;
    if (i && S[i - 1][j] > best) { best = S[i - 1][j]; k = 1; }
    if (j && S[i][j - 1] > best) { best = S[i][j - 1]; k = 2; }
    if (i && j) { const v = S[i - 1][j - 1] + Math.max(0, sim(GA[i - 1], GB[j - 1]) - .15); if (v > best) { best = v; k = 3; } }
    if (i > 1 && j) { const v = S[i - 2][j - 1] + Math.max(0, sim(u(GA[i - 2], GA[i - 1]), GB[j - 1]) - .2); if (v > best) { best = v; k = 4; } }
    if (i && j > 1) { const v = S[i - 1][j - 2] + Math.max(0, sim(GA[i - 1], u(GB[j - 2], GB[j - 1])) - .2); if (v > best) { best = v; k = 5; } }
    S[i][j] = best; K[i][j] = k;
  }
  const rows = []; let i = n, j = m;
  while (i || j) { const k = K[i][j];
    if (k === 1) { rows.push([[i - 1], []]); i--; } else if (k === 2) { rows.push([[], [j - 1]]); j--; }
    else if (k === 3) { rows.push([[i - 1], [j - 1]]); i--; j--; } else if (k === 4) { rows.push([[i - 2, i - 1], [j - 1]]); i -= 2; j--; }
    else { rows.push([[i - 1], [j - 2, j - 1]]); i--; j -= 2; } }
  return rows.reverse();
}
async function studyReader(d, it, want, pairs) {
  pairs = pairs || [];
  const id = it.id, base = '#' + encodeURIComponent(id);
  d.innerHTML = `<p style="margin-top:18px"><a href="${base}">← 자료 소개</a></p><p class="muted">본문을 불러오는 중…</p>`;
  // 압축본(.gz)을 풀 수 없는 브라우저(옛 아이폰·일부 앱 안 브라우저)는 같은 자료의 글 파일(.txt)로 읽음
  const plainTxt = (it.files || []).find(k => /\.txt$/i.test(k));
  const key = /\.gz$/i.test(it.text) && !('DecompressionStream' in window) && plainTxt ? plainTxt : it.text;
  let P; try { P = await stLoad(key); } catch (e) { try { if (plainTxt && key !== plainTxt) P = await stLoad(plainTxt); } catch (e2) {} }
  if (!P || !P.length) { d.innerHTML = `<p style="margin-top:18px"><a href="${base}">← 자료 소개</a></p><p>본문을 불러오지 못했습니다. 새로고침해 주세요.</p>`; return; }
  // 대조할 판본: 고른 판본 이름(PTS·BJT·VRI)을 기억해 두고, 이 자료에 그 판본이 있으면 그것으로 (운영자 요청, 2026-11-10: VRI 6차 결집본 더함)
  const want0 = store.get('st-cmp-ed', store.get('st-cmp', false) ? 'BJT' : '');
  let pair = pairs.find(x => stEdOf(x) === want0) || null;
  const S = { fs: store.get('st-fs', 1), lh: store.get('st-lh', 1.9), font: store.get('st-font', 'serif'), cmp: !!pair };
  let P2 = null, P2by = null;
  const loadPair = async () => { if (P2 || !pair) return; try { P2 = await stLoad(pair.text); P2by = new Map(P2.map(p => [p.label, p])); } catch (e) { P2 = []; P2by = new Map(); } };
  if (S.cmp) await loadPair();
  let i = Math.min(Math.max((want || store.get('stpos-' + id, 1)) - 1, 0), P.length - 1);
  const hl = (txt, q) => { const e = esc(txt); if (!q) return e; const f = stFold(txt), fq = stFold(q); if (!fq) return e;
    let out = '', k = 0, j; while ((j = f.indexOf(fq, k)) >= 0) { out += esc(txt.slice(k, j)) + '<mark>' + esc(txt.slice(j, j + q.length)) + '</mark>'; k = j + q.length; } return out + esc(txt.slice(k)); };
  const body = (txt, q) => txt.trim().split(/\n{2,}/).map(b => `<p>${hl(b, q).replace(/⟦([^⟧]*)⟧/g, '<span class="st-tag">$1</span>')}</p>`).join('');
  d.innerHTML = `<div class="st-read">
    <div class="st-bar"><a class="tbtn" href="${base}">← 자료 소개</a><b class="st-title">${esc(it.title)}</b>
      <span class="st-tools"><button class="tbtn" data-fs="-1" aria-label="글자 작게">가−</button><button class="tbtn" data-fs="1" aria-label="글자 크게">가+</button>
      <button class="tbtn" id="stLh">줄 간격</button><button class="tbtn" id="stFont">${S.font === 'serif' ? '고딕체' : '명조체'}</button>
      <select id="stJump" aria-label="쪽으로 가기">${P.map((p, n) => `<option value="${n}">${esc(p.label)}</option>`).join('')}</select>
      <input id="stFind" type="search" placeholder="이 책에서 찾기" value="${esc(STQ.q || '')}">${pairs.length ? `<select id="stCmp" class="${S.cmp ? 'on' : ''}" aria-label="다른 판본과 대조" title="같은 쪽(쪽 이름이 같은 곳)을 문장마다 나란히"><option value="">⇄ 판본 대조 끄기</option>${pairs.map(x => `<option value="${esc(x.id)}" ${pair && pair.id === x.id ? 'selected' : ''}>⇄ ${esc(stEdOf(x))} 판본과 대조</option>`).join('')}</select>` : ''}</span></div>
    <div id="stHits" hidden></div>
    <article class="reflow st-page" id="stPage"></article>
    <div class="st-nav"><button class="btn ghost" id="stPrev">‹ 앞쪽</button><span class="small muted" id="stPos"></span><button class="btn ghost" id="stNext">뒤쪽 ›</button></div></div>`;
  const pg = $('#stPage', d);
  const apply = () => { pg.style.setProperty('--fs', S.fs); pg.style.setProperty('--lh', S.lh); pg.classList.toggle('sans', S.font === 'sans'); };
  const show = (n, keep) => { i = Math.min(Math.max(n, 0), P.length - 1); store.set('stpos-' + id, i + 1);
    const q = ($('#stFind', d).value || '').trim();
    if (S.cmp && P2by) {
      const other = P2by.get(P[i].label);
      const me = stEdOf(it), ot = stEdOf(pair);
      if (!other) pg.innerHTML = `<div class="pmark">${esc(P[i].label)}</div><p class="muted small">${esc(ot)} 판본에는 이 쪽 이름(${esc(P[i].label)})이 없습니다.</p>` + body(P[i].text, q);
      else {
        const A = stSents(P[i].text.trim()), B = stSents(other.text.trim()), rows = stAlign(A, B);
        const cell = (L, ix) => ix.length ? hl(ix.map(k => L[k]).join(''), q).replace(/⟦([^⟧]*)⟧/g, '<span class="st-tag">$1</span>') : '<span class="muted">—</span>';
        pg.innerHTML = `<div class="pmark">${esc(P[i].label)}</div><div class="st-cmp"><div class="st-cmp-h">${esc(me)}</div><div class="st-cmp-h">${esc(ot)}</div>${rows.filter(([a, b]) => (a.map(k => A[k]).join('') + b.map(k => B[k]).join('')).trim()).map(([a, b]) => `<div class="st-c" data-ed="${esc(me)}">${cell(A, a)}</div><div class="st-c" data-ed="${esc(ot)}">${cell(B, b)}</div>`).join('')}</div>`;
      }
    } else
    pg.innerHTML = `<div class="pmark">${esc(P[i].label)}</div>` + body(P[i].text, q);
    $('#stJump', d).value = i; $('#stPos', d).textContent = `${i + 1} / ${P.length}`;
    $('#stPrev', d).disabled = i === 0; $('#stNext', d).disabled = i === P.length - 1;
    history.replaceState(null, '', `${base}/read/${i + 1}`);
    if (!keep) { const m = $('mark', pg); (m || d).scrollIntoView({ block: m ? 'center' : 'start' }); } };
  apply(); show(i);
  $$('[data-fs]', d).forEach(b => b.onclick = () => { S.fs = Math.min(2.2, Math.max(0.7, Math.round((S.fs + b.dataset.fs * 0.1) * 10) / 10)); store.set('st-fs', S.fs); apply(); });
  $('#stLh', d).onclick = () => { S.lh = S.lh >= 2.3 ? 1.5 : Math.round((S.lh + 0.2) * 10) / 10; store.set('st-lh', S.lh); apply(); };
  $('#stFont', d).onclick = e => { S.font = S.font === 'serif' ? 'sans' : 'serif'; store.set('st-font', S.font); e.target.textContent = S.font === 'serif' ? '고딕체' : '명조체'; apply(); };
  $('#stJump', d).onchange = e => show(+e.target.value);
  if ($('#stCmp', d)) $('#stCmp', d).onchange = async e => { const v = e.target.value; pair = pairs.find(x => x.id === v) || null; P2 = P2by = null; S.cmp = !!pair; store.set('st-cmp-ed', pair ? stEdOf(pair) : ''); e.target.classList.toggle('on', S.cmp); if (S.cmp) await loadPair(); pg.classList.toggle('wide', S.cmp); show(i, true); };
  pg.classList.toggle('wide', S.cmp);
  $('#stPrev', d).onclick = () => show(i - 1); $('#stNext', d).onclick = () => show(i + 1);
  const keys = e => { if (!document.contains(pg)) return document.removeEventListener('keydown', keys); if (/INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) return;
    if (e.key === 'ArrowLeft') show(i - 1); if (e.key === 'ArrowRight') show(i + 1); };
  document.addEventListener('keydown', keys);
  const find = () => { const q = ($('#stFind', d).value || '').trim(), box = $('#stHits', d); STQ.q = q;
    if (q.length < 2) { box.hidden = true; show(i, true); return; }
    const fq = stFold(q), hits = []; P.forEach((p, n) => { let j = p.f.indexOf(fq), c = 0; if (j < 0) return; const first = j; while (j >= 0) { c++; j = p.f.indexOf(fq, j + 1); }
      hits.push({ n, c, s: p.text.slice(Math.max(0, first - 40), first + q.length + 50).replace(/⟦[^⟧]*⟧/g, ' ') }); });
    box.hidden = false;
    box.innerHTML = hits.length ? `<p class="small muted">‘${esc(q)}’ — ${hits.length}쪽에서 ${hits.reduce((a, h) => a + h.c, 0)}번</p><ul class="st-hl">${hits.slice(0, 300).map(h => `<li><button data-n="${h.n}"><b>${esc(P[h.n].label)}</b>${h.c > 1 ? ` <span class="small muted">(${h.c}번)</span>` : ''} <span>…${hl(h.s, q)}…</span></button></li>`).join('')}</ul>` : `<p class="small muted">이 책에서 ‘${esc(q)}’ 를 찾지 못했습니다.</p>`;
    $$('[data-n]', box).forEach(b => b.onclick = () => show(+b.dataset.n));
    show(i, true); };
  let ft; $('#stFind', d).oninput = () => { clearTimeout(ft); ft = setTimeout(find, 300); };
  if (STQ.q) find();
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
  const want = { trad: q.getAll('trad'), teacher: q.getAll('teacher'), topic: q.getAll('topic'), main: q.getAll('main'), fmt: q.getAll('fmt'), lang: q.getAll('lang'), btype: q.getAll('btype'), pub: q.getAll('pub'), person: q.getAll('person'), region: q.getAll('region') };
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
    let shown = 0, lastPg = null;
    for (const b of books) {
      const has = (k, list) => !list || list.some(v => (b.dataset[k] || '').split('|').includes(v));
      let ok = has('main', sel.main) && has('topics', sel.topic) && has('fmts', sel.fmt) && has('lang', sel.lang) && has('btype', sel.btype) && has('pub', sel.pub) && has('person', sel.person) && has('region', sel.region);
      // 전통과 스승은 '또는'으로 묶음
      if (ok && (sel.trad || sel.teacher)) ok = (sel.trad || []).some(x => (b.dataset.trad || '').split('|').includes(x)) || (sel.teacher || []).some(x => (b.dataset.teacher || '').split('|').includes(x));
      (b.closest('li') || b).hidden = !ok; if (ok) shown++;  // 목록 항목(li)째 숨김 (2026-11-17)
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
    $$('.book', g).sort((a, b) => v === 'title' ? a.dataset.title.localeCompare(b.dataset.title, 'ko') : v === 'author' ? ((a.dataset.author || '').localeCompare(b.dataset.author || '', 'ko') || (+a.dataset.ord || 0) - (+b.dataset.ord || 0)) : ((+a.dataset.ord || 0) - (+b.dataset.ord || 0)) || (b.dataset.added || '').localeCompare(a.dataset.added || '')).forEach(x => g.appendChild(x.closest('li') || x));  // 최근 등록순: 같은 저자끼리 모아서(data-ord)
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
    const MK = '[\\u302c\\u302d\\u1dc0-\\u1dff\\u2033\\u02ba\\u02d1\\u02d4\\u02d5\\u0300-\\u036f\\ufe00-\\ufe0f\\ufe20-\\ufe2f]*';  // 빠알리어 한글 표기 부호는 건너뛰며 표시
    terms.forEach(t => { if (t) out = out.replace(new RegExp([...t].map(c => c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join(MK) + MK, 'gi'), m => `<mark>${m}</mark>`); });
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
  // 책 본문들을 한꺼번에(동시에) 받아 둠 — 하나씩 차례로 받으면 책이 많아질수록 느려짐
  if (scope === 'all' || scope === 'body') await Promise.all(D.books.filter(b => b.manifest).map(b => manifest(b.manifest).catch(() => null)));
  const res = [];
  const isToc = t => { const ls = String(t || '').split('\n').map(x => x.trim()).filter(Boolean); return /^(차례|목차|contents)$/i.test(ls[0] || '') || (ls.length > 3 && ls.filter(x => /[|·.\s]\s*\d{1,3}$/.test(x)).length / ls.length > 0.5); };
  for (const b of D.books) {
    const why = [];
    if ((scope === 'all' || scope === 'title') && [b.title, b.subtitle, b.orig].some(has)) why.push('제목');
    if (scope === 'all' && b.lang && has(b.lang) && !why.length) why.push('원서 언어');
    if ((scope === 'all' || scope === 'author') && [b.byline, b.teacher, b.teacherRoman, b.tradition, ...(b.teacherAliases || [])].some(has)) why.push('스승·저자');
    if ((scope === 'all' || scope === 'tr') && has(b.tr)) why.push('옮긴이');
    const qd = q.replace(/[^0-9xX]/g, ''); if (scope === 'all' && qd.length >= 10 && (b.isbn || []).some(x => x.replace(/[^0-9xX]/g, '') === qd)) why.push('ISBN');
    if ((scope === 'all' || scope === 'topic') && [...b.topics, ...b.main].some(has)) why.push('주제');
    let body = [];
    if ((scope === 'all' || scope === 'body') && b.manifest) {
      try {
        const m = await manifest(b.manifest);
        const hits = (m.pages || []).map((p, i) => ({ ...p, n: i + 1 })).filter(p => p.text && has(plainT(p.text)));
        if (hits.some(p => isToc(p.text)) && scope === 'all') why.push('목차');
        body = hits.filter(p => !isToc(p.text)).slice(0, 60).map(p => ({ n: p.n, label: p.label ? p.label + '쪽' : p.n + '번째', s: snippet(plainT(p.text).replace(/\s+/g, ' '), terms) }));
        // 색인 표 속 낱말 (제1부 기준, 같은 낱말이 네 부에 되풀이되므로 한 번만)
        if (m.index && m.index.parts && m.index.parts[0]) {
          const ixPage = (m.pages || []).findIndex(p => /\[\[색인\]\]/.test(p.text || '')) + 1;
          const P0 = m.index.parts[0];
          const ixHits = P0.rows.filter(r => r.slice(0, 4).some(c => has(c))).slice(0, 40).map(r => ({ n: ixPage, label: '색인', s: r.slice(0, 4).filter(Boolean).join(' · ').replace(/\s+/g, ' ') }));
          body = [...ixHits, ...body].slice(0, 60);
        }
      } catch (e) {}
    }
    if ((scope === 'all') && has(b.desc) && !why.length) why.push('소개');
    if (why.length || body.length) res.push({ b, why, body });
  }
  const hq = encodeURIComponent(terms.join('|'));
  const info = res.filter(r => r.why.length), inBody = res.filter(r => r.body.length);
  const nBody = inBody.reduce((a, r) => a + r.body.length, 0);
  const thumb = b => `<a class="sr-cov" href="/book/${b.id}/" tabindex="-1" aria-hidden="true">${b.cover ? `<img src="${esc(b.cover)}" alt="" loading="lazy">` : ''}</a>`;
  const infoHtml = info.map(({ b, why }) => `<div class="sr-book">${thumb(b)}<div class="sr-bi">
      <a class="sr-t" href="/book/${b.id}/">${hl(b.title, terms)}</a>
      <div class="sr-m">${hl(b.byline, terms)}${b.tr ? ' | ' + hl(b.tr, terms) : ''}</div>
      ${[...b.topics].some(t => terms.some(x => norm(t).includes(x))) ? `<div class="sr-m">주제: ${b.topics.map(t => hl(t, terms)).join(', ')}</div>` : ''}
      <div class="sr-why">${why.map(w => `<span>${w}에서 찾음</span>`).join('')}</div></div></div>`).join('');
  const bodyHtml = inBody.map(({ b, body }) => `<div class="sr-group">
      <div class="sr-gh">${thumb(b)}<div><a class="sr-t" href="/book/${b.id}/">${esc(b.title)}</a><div class="sr-m">${body.length}${body.length >= 60 ? '곳 이상' : '곳'}</div></div></div>
      <ol class="sr-hits">${body.map((x, i) => `<li${i >= 4 ? ' hidden' : ''}><a href="/read/${b.id}/${x.n}?hl=${hq}"><span class="sr-pg">${esc(x.label)}</span><span class="sr-s">${hl(x.s, terms)}</span></a></li>`).join('')}</ol>
      ${body.length > 4 ? `<button class="sr-more">${body.length - 4}곳 더 보기</button>` : ''}</div>`).join('');
  box.innerHTML = (group ? `<div class="variant-note"><span>‘${esc(q)}’와 같은 말인 ${group.filter(x => norm(x) !== norm(q)).map(x => `‘${esc(x)}’`).join(', ')}도 함께 찾았습니다.</span><button id="exactBtn">입력한 표기만 찾기</button></div>`
      : exact ? `<div class="variant-note"><span>입력한 표기 ‘${esc(q)}’만 찾았습니다.</span><button id="exactBtn">비슷한 표기도 찾기</button></div>` : '')
    + (res.length ? `<div class="sr-sum">${info.length ? `<a href="#srInfo">책 <b>${info.length}</b>권</a>` : ''}${inBody.length ? `<a href="#srBody">본문 <b>${nBody}</b>곳${inBody.some(r => r.body.length >= 60) ? ' 이상' : ''}</a>` : ''}</div>`
      + (info.length ? `<section id="srInfo" class="sr-sec"><h2 class="sr-h">📚 책 정보에서 찾음 <small>제목·저자·옮긴이·주제</small></h2>${infoHtml}</section>` : '')
      + (inBody.length ? `<section id="srBody" class="sr-sec"><h2 class="sr-h">📖 책 본문에서 찾음 <small>누르면 그 쪽을 바로 엽니다</small></h2>${bodyHtml}</section>` : '')
      : `<p class="muted">찾는 자료가 없습니다. 다른 표기나 더 짧은 말로 찾아보세요. <a href="/library/">도서관에서 둘러보기 →</a></p>`);
  $$('.sr-more', box).forEach(btn => btn.onclick = () => { $$('li[hidden]', btn.previousElementSibling).forEach(li => li.hidden = false); btn.remove(); });
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
function epList(plId) { return $$(`[data-epl="${CSS.escape(plId)}"]`).map(e => ({ audio: e.dataset.audio, title: e.dataset.title, plname: e.dataset.plname, sp: e.dataset.sp || '' })); }
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
    navigator.mediaSession.metadata = new MediaMetadata({ title: e.title, artist: e.plname, album: '붓다담마 법보시 도서관 · 법문 바로 듣기', artwork: [{ src: '/images/og.jpg', sizes: '1200x630', type: 'image/jpeg' }] });
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
    $('#pLock').textContent = on ? '🔒 잠김' : '🔓 잠금'; $('#pLock').setAttribute('aria-pressed', on); $('#pLock').setAttribute('aria-label', on ? '잠김, 눌러서 풀기' : '재생기 잠그기');
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
    if (a.duration && document.activeElement !== $('#pSeek')) $('#pSeek').value = a.currentTime / a.duration * 100;  // 커서가 막대에 있으면 움직이지 않음 — 화면 낭독기가 위치를 계속 읽어 소리가 겹치지 않게 (2026-11-17)
    if (PL.pl && Date.now() - last > 3000) { last = Date.now(); const e = PL.list[PL.i]; store.set('ppos-' + e.audio, a.currentTime);
      if (a.currentTime > 3) sHistSave({ a: e.audio, t: e.title, pl: e.plname }, e.sp || '/simple/talks/', a.currentTime, a.duration); }  // 일반 화면에서 듣던 법문도 단순 화면 '이어 듣기'·내 서재에 (운영자 요청, 2026-11-18)
  };
  a.onplay = () => { $('#pPlay').textContent = '❚❚'; $('#pPlay').setAttribute('aria-label', '일시정지'); };
  a.onpause = () => {
    $('#pPlay').textContent = '▶'; $('#pPlay').setAttribute('aria-label', '재생');
    // 잠겨 있는데 저절로 멈추면(이어폰 빠짐 등) 다시 재생
    if (PL.locked && !a.ended && a.src) setTimeout(() => { if (PL.locked && a.paused && !a.ended) a.play().catch(() => {}); }, 400);
    else wake(false, 'player');
  };
  a.addEventListener('play', () => { if (PL.locked) wake(true, 'player'); });
  a.onended = () => { if (PL.pl) { store.set('ppos-' + PL.list[PL.i].audio, 0); sHistDel(PL.list[PL.i].audio); } if ($('#pAuto').checked && PL.pl && PL.i < PL.list.length - 1) playEp(PL.pl, PL.i + 1, PL.list); };
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
    if (man.toc && man.toc.length) m.innerHTML = `<ol class="toc">${man.toc.map(t => `<li class="${/^\s/.test(t.title) ? 'sub' : ''}"><a href="/read/${m.dataset.book}/${t.page}?view=text">${boxNum(esc((t.list || t.title).trim()))}</a><span>${esc(t.label || '')}</span></li>`).join('')}</ol><p class="small muted" style="margin-top:8px">목차를 누르면 그 장을 읽을 수 있습니다.</p>`;
  } catch (e) {}
}

// 책을 열면 인터넷 없이 읽을 수 있게: 글은 열 때 저장되고(sw.js), 본문 그림과 책 소개도 여기서 뒤에서 조용히 받아 둠.
// 이미 저장된 것은 다시 받지 않음.
async function saveBookOffline(id, man) {
  if (!('serviceWorker' in navigator) || !navigator.serviceWorker.controller || !('caches' in window) || !navigator.onLine) return;
  const txt = JSON.stringify(man.pages || []);
  const urls = [`/book/${id}/`, ...new Set(txt.match(/\/uploads\/[^"')\s\\]+/g) || [])];
  for (const u of urls) {
    try { if (await caches.match(new URL(u, location.origin).href)) continue; await fetch(u); } catch (e) {}
  }
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
    id, title: root.dataset.title, by: root.dataset.teacher || root.dataset.byline, cover: root.dataset.cover || '', kakao: root.dataset.kakao || '', noCopy: root.dataset.nocopy === '1', pages, toc: man.toc || [], say: man.say || {}, ph: man.ph || null, tdl: man.table_dl || {}, fnSite: man.fn_site || {}, spreadOk: (man.pages || []).some(p => p.text), spreadPali: !!man.spread, ly: man.ly || null,  // tdl: 표 그림 내려받기 (표 첫 칸 글 → 그림 주소, 운영자 요청 2026-11-12)
     // say: 그림·표를 소리로 읽을 글 (그림 주소 → 글, 운영자 요청 2026-11-10)
   
    i: Math.min(Math.max(want || (last > 1 ? last : 0) || firstContent(pages, man.toc || []), 1), pages.length) - 1,
    view: 'text', zoom: store.get('rzoom', 1), fs: store.get('rfs', 1), bold: store.get('rbold', false), lh: store.get('rlh', 1.9), font: RFONTS.some(f => f[0] === store.get('rfont', 'serif')) ? store.get('rfont', 'serif') : 'serif', mw: store.get('rmw', 36), spread: store.get('rspread2-' + id, !!man.spread), centerHeads: !!man.center_heads,  // 텍스트 JSON center_heads: 본문 소제목(## )을 가운데로 — 『불자수첩』 (운영자 요청, 2026-11-16)
     // 책마다 따로 — 『테라와다 불교의범』처럼 spread 가 있는 책은 처음부터 양쪽으로, 다른 책은 한쪽씩 (운영자 요청, 2026-11-14)
   
    hl: hlp ? hlp.split('|').filter(Boolean) : [], speaking: false,
    par: root.dataset.par ? root.dataset.par.split(',') : [], parMode: root.dataset.par ? store.get('par-' + id, 'off') : 'off', parD: null, parEd: (() => { try { return JSON.parse(root.dataset.parEd || '[]'); } catch (e) { return []; } })(),  // 원서 대조 (운영자 요청, 2026-11-15)
    ix: man.index || null, ixPart: store.get('ixp-' + id, 0), ixQ: hlp ? hlp.split('|')[0] : ''
  };
  if (!pages.some(p => p.text)) R.view = 'page';
  renderReader();
  if (root.dataset.audio) abLoad(root.dataset.audio);  // 오디오북이 있는 책만 🎧 단추
  // 내 서재 'TTS 이어 듣기' 줄: ?listen=1&s=문단 → 그 문단을 보여 주고 '▶ 듣기'에 커서, 누르면 그 문단부터 (운영자 요청, 2026-11-19)
  { const q = new URLSearchParams(location.search); if (q.has('listen')) { R.resumeAt = { i: R.i, k: +q.get('s') || 0 }; history.replaceState(history.state, '', location.pathname);
    setTimeout(() => { const el = $(`#rBody p[data-pg="${R.i + 1}"][data-s="${R.resumeAt ? R.resumeAt.k : 0}"]`); if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('resume-at'); } const rd = $('#reader'); if (rd) rd.classList.remove('chrome-off'); const b = $('#rSpeak'); if (b) b.focus(); toast('▶ 듣기를 누르면 듣던 문단부터 이어서 읽습니다'); }, 400); } }
  saveBookOffline(id, man);
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller && !store.get('off-' + id)) { store.set('off-' + id, 1); setTimeout(() => toast('이 책을 이 기기에 저장했습니다. 이제 인터넷 없이도 읽을 수 있습니다'), 1500); }
  if (!want && last > 1) toast(`지난번에 읽던 ${pageName(R.pages[R.i])}을 열었습니다`);
}
const pageName = p => p.label ? `${p.label}쪽` : `${p.n}번째 쪽`;
document.addEventListener('fullscreenchange', () => { const b = $('#rFull'); if (b) { const on = !!document.fullscreenElement; b.textContent = on ? '⛶ 전체 화면 끄기' : '⛶ 전체 화면'; b.setAttribute('aria-pressed', on); } });
function closeReader() { try { if (R && R.spreadLock) screen.orientation.unlock(); } catch (e) {} try { if (document.fullscreenElement) document.exitFullscreen(); } catch (e) {} stopSpeak(); abStop(); R = null; const el = $('#reader'); if (el) el.remove(); bgInert(false); document.body.style.overflow = ''; }
function exitReader() { if (AB.locked) { abLockedMsg(); return; } if (R && R.ttsLocked) { toast('듣기가 잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요'); return; } const id = R && R.id; closeReader(); location.href = '/book/' + id + '/'; }
// 빈 줄 = 문단 나눔, 문단 안의 한 줄 바꿈 = 줄 바꿈(게송·회향문처럼 인쇄된 대로)
const paras = t => String(t || '').split(/\n\s*\n/).map(s => s.trim().split('\n').map(l => l.trim()).join('\n')).filter(Boolean);
function markUl(s, n) {
  if (R.hl.length) return hl(s, R.hl);
  const rg = uls().filter(h => h.id === R.id && h.p === n && h.text && s.includes(h.text) && !/\*\*/.test(h.text)).map(h => { const a = s.indexOf(h.text); return [a, a + h.text.length, h.k]; }).sort((x, y) => x[0] - y[0]);
  let out = '', p = 0; rg.forEach(([a, b, k]) => { if (a < p) return; out += esc(s.slice(p, a)) + `<u class="ul" data-hid="${k}" title="밑줄 · 눌러서 메모나 지우기">` + esc(s.slice(a, b)) + '</u>'; p = b; });
  return out + esc(s.slice(p));
}
function pageHtml(p) {
  if (!p.img) return `<div class="reflow ${fontCls()}${R.bold ? ' bold' : ''}${R.fs >= 1.75 ? ' big' : ''}" style="--fs:${R.fs};--lh:${R.lh};--mw:${R.mw}em">${paras(p.text).map((s, k) => `<p data-pg="${p.n}" data-s="${k}">${markUl(s, p.n)}</p>`).join('') || '<p class="muted">빈 쪽입니다.</p>'}</div>`;
  const src = R.zoom > 1.2 && p.big ? p.big : p.img;
  return `<div class="page-sheet img-sheet" style="width:min(${Math.round(560 * R.zoom)}px,100%);${p.w && p.h ? `aspect-ratio:${p.w}/${p.h}` : ''}"><img src="${esc(src)}" alt="${esc(R.title)} ${esc(pageName(p))}" draggable="false"></div>`;
}
// 글로 보기: 목차의 큰 장(들여쓰지 않은 항목) 단위로 보여 주기
function chapters() {
  if (R._chs && R._chsToc === R.toc) return R._chs;
  const top = R.toc.filter(t => !/^\s/.test(t.title)).sort((a, b) => a.page - b.page || paraIdx(a) - paraIdx(b));
  let out = [];
  if (!top.length) out = [{ title: '', from: 1, to: R.pages.length, k0: 0, kEnd: null }];
  else {
    // 첫 장 앞쪽에 글이 있을 때만 '앞부분'을 둠 (표지처럼 빈 쪽은 건너뜀)
    if (top[0].page > 1 && R.pages.slice(0, top[0].page - 1).some(p => p.text && p.text.trim())) out.push({ title: '앞부분', from: 1, to: top[0].page - 1, k0: 0, kEnd: null });
    top.forEach((t, i) => {
      const nx = top[i + 1], k0 = paraIdx(t);
      // 다음 장이 같은 쪽 중간에서 시작하면(at) 이 장은 그 쪽의 그 문단 앞까지
      const midNext = nx && paraIdx(nx) > 0;
      out.push({ title: t.title.trim(), from: t.page, k0, to: nx ? (midNext ? nx.page : nx.page - 1) : R.pages.length, kEnd: midNext ? paraIdx(nx) : null });
    });
    out = out.filter(c => c.to >= c.from);
  }
  R._chs = out; R._chsToc = R.toc; return out;
}
// 목차 항목의 at(쪽 중간 시작 글)이 있으면 그 쪽에서 몇 번째 문단인지
function paraIdx(t) {
  if (!t || !t.at) return 0;
  const ps = paras((R.pages[t.page - 1] || {}).text), key = String(t.at).replace(/\s/g, '');
  const k = ps.findIndex(s => s.replace(/^## /, '').replace(/\*\*/g, '').replace(/\s/g, '').startsWith(key.replace(/\*\*/g, '')));
  return k < 0 ? 0 : k;
}
function chapterOf(n) {
  const cs = chapters();
  if (R.chForce != null && cs[R.chForce] && n >= cs[R.chForce].from && n <= cs[R.chForce].to) return R.chForce;
  const k = cs.findIndex(c => n >= c.from && n <= c.to); return k < 0 ? 0 : k;
}
function firstContent(pages, toc) { const t = toc.filter(x => !/^\s/.test(x.title)).map(x => x.page).sort((a, b) => a - b)[0]; const f = pages.findIndex(p => p.text && p.text.trim()) + 1; return Math.min(t || Infinity, f || Infinity) === Infinity ? 1 : Math.min(t || Infinity, f || Infinity); }
// 양쪽으로 읽기 (운영자 요청, 2026-11-14): 글로 읽기가 있는 모든 책 — 넓은 화면에서 짝수 쪽은 왼쪽·홀수 쪽은 오른쪽에 나란히 (텍스트 JSON 의 spread 는 '왼쪽 빠알리·오른쪽 번역' 안내만)
// 휴대폰·태블릿은 가로로 눕혔을 때도 (운영자 요청, 2026-11-14)
const spreadWide = () => window.innerWidth >= 1000 || (window.innerWidth >= 560 && window.innerWidth > window.innerHeight);
const spreadOn = () => !!(R && R.spreadOk && R.spread && spreadWide() && !(R.parMode && R.parMode !== 'off'));  // 원서 대조 중에는 양쪽 보기 대신 원서를 나란히
let spreadWas = null;
// 휴대폰 세로 화면: 전체 화면 + 가로 고정 (안드로이드 크롬 등에서만 됨 — 아이폰은 직접 돌려야 함) (운영자 요청, 2026-11-14)
async function spreadRotate() {
  if (!R) return; let ok = false, why = '';
  const so = screen.orientation;
  if (so && so.lock) {
    // 설치한 앱(홈 화면)·이미 전체 화면이면 전체 화면 없이도 돌릴 수 있음 → 먼저 그대로 한 번
    try { if (document.fullscreenElement || matchMedia('(display-mode: standalone)').matches) { await so.lock('landscape'); ok = true; } } catch (e) { why = e.name; }
    if (!ok) {
      try {
        if (!document.fullscreenElement) { const d = document.documentElement; await (d.requestFullscreen ? d.requestFullscreen({ navigationUI: 'hide' }) : d.webkitRequestFullscreen()); R.spreadFs = true; }
      } catch (e) { why = e.name; }
      // 전체 화면이 실제로 켜지기 전에 돌리면 거절하는 브라우저(삼성 인터넷 등)가 있어 잠깐씩 기다리며 몇 번 더 (운영자 요청, 2026-11-16)
      for (let i = 0; i < 6 && !ok; i++) { try { await so.lock('landscape'); ok = true; } catch (e) { why = e.name; await new Promise(r => setTimeout(r, 250)); } }
    }
    if (ok) R.spreadLock = true;
    else if (R.spreadFs && document.fullscreenElement) { try { await document.exitFullscreen(); } catch (e) {} R.spreadFs = false; }
  }
  if (!ok) setTimeout(() => R && !spreadWide() && toast('이 브라우저는 화면을 저절로 돌릴 수 없습니다 — 휴대폰을 가로로 돌려 주세요 (화면 자동 회전을 켜 두세요)' + (why ? ` · ${why}` : '')), 300);
}
// 양쪽으로 보기가 켜진 책을 휴대폰 세로로 열면 아래쪽에 '가로로 돌려 양쪽으로 보기' 띠 (운영자 요청, 2026-11-14 — 『테라와다 불교의범』)
function sprBar() {
  let b = $('#sprBar'); const want = R && R.spreadOk && R.spread && !spreadWide() && !R.sprBarOff && $('#reader') && R.view !== 'page' && matchMedia('(pointer:coarse)').matches;
  if (!want) { if (b) b.remove(); return; }
  if (b) return;
  b = document.createElement('div'); b.id = 'sprBar'; b.className = 'spr-bar'; b.setAttribute('role', 'region'); b.setAttribute('aria-label', '양쪽으로 보기 안내');
  b.innerHTML = `<p class="spr-msg">${R.spreadPali ? '이 책은 휴대폰을 <b>가로로</b> 눕혀 보시면 좋습니다 — 왼쪽 빠알리 · 오른쪽 번역이 책처럼 나란히 보입니다.' : '휴대폰을 <b>가로로</b> 눕히면 책처럼 두 쪽이 나란히 보입니다.'}</p><div class="spr-btns"><button type="button" class="spr-go">📖 가로로 돌려 양쪽으로 보기</button><button type="button" class="spr-x">닫기</button></div>`;
  $('#reader').appendChild(b);
  b.querySelector('.spr-go').onclick = () => { spreadRotate(); };
  b.querySelector('.spr-x').onclick = () => { R.sprBarOff = true; b.remove(); };
}
window.addEventListener('resize', () => setTimeout(sprBar, 50));
window.addEventListener('resize', () => { if (!R || !R.spreadOk || !$('#reader')) return; const now = spreadOn(); if (spreadWas === null) { spreadWas = now; return; } if (now === spreadWas) return; spreadWas = now;
  const pn = R.i + 1; renderReader(); const m = $('#pm-' + pn); if (m) m.scrollIntoView(); });
// 양쪽으로 보기에서 왼쪽 빠알리 줄과 오른쪽 번역 줄을 인쇄본처럼 같은 높이에 (운영자 요청, 2026-11-14 — 『테라와다 불교의범』)
// 텍스트 JSON 의 ly {쪽 순번: [[문단마다 줄의 인쇄본 높이 pt…]…]} 를 보고, 인쇄본에서 같은 높이에 있는 줄이 화면에서도 같은 높이에 오도록
// 늦게 오는 쪽 문단 위에 빈칸(padding-top)을 더함. 글자는 그대로.
function lineTops(p) {
  const tops = []; let k = 0, want = true;
  const w = document.createTreeWalker(p, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (n.nodeType === 1) { if (n.tagName === 'BR') { k++; want = true; } continue; }
    if (!want || !n.nodeValue.trim()) continue;
    const r = document.createRange(), i = n.nodeValue.search(/\S/); r.setStart(n, i); r.setEnd(n, i + 1);
    const b = r.getClientRects()[0]; if (b) tops[k] = b.top; want = false;
  }
  return tops;
}
function sprAlign() {
  if (!R || !R.ly || !spreadOn()) return;
  const body = $('#rBody'); if (!body) return;
  $$('.spr-pg p[data-s]', body).forEach(p => { p.style.paddingTop = ''; p.style.marginTop = ''; });
  $$('.spr-pg.spr-l', body).forEach(L => {
    const Rt = L.nextElementSibling; if (!Rt || !Rt.classList.contains('spr-r')) return;
    const side = col => {
      const top = col.getBoundingClientRect().top;
      return [...col.querySelectorAll('p[data-s]')].filter(p => p.offsetParent).map(p => {
        const ys = ((R.ly[p.dataset.pg] || [])[+p.dataset.s]) || [];
        const tops = lineTops(p).map(t => t == null ? null : t - top);
        const k0 = ys.findIndex((y, k) => y != null && tops[k] != null);
        return { p, ys, tops, k0, d: 0 };
      }).filter(x => x.k0 > -1);
    };
    const S = [side(L), side(Rt)];
    const eff = (s, i, k) => { let d = 0; for (let j = 0; j <= i; j++) d += S[s][j].d; return S[s][i].tops[k] + d; };
    const anchors = [];
    S.forEach((a, s) => a.forEach((x, i) => anchors.push({ s, i, y: x.ys[x.k0] })));
    anchors.sort((a, b) => a.y - b.y);
    for (const A of anchors) {
      const o = 1 - A.s, x = S[A.s][A.i];
      // 다른 쪽에서 인쇄본 높이가 바로 위·아래인 줄을 찾아 그 사이 자리를 비례로 셈
      let lo = null, hi = null;
      S[o].forEach((q, j) => q.ys.forEach((y, k) => { if (y == null || q.tops[k] == null) return; if (y <= A.y + 2) { if (!lo || y >= lo.y) lo = { j, k, y }; } else if (!hi || y < hi.y) hi = { j, k, y }; }));
      if (!lo) continue;
      const tl = eff(o, lo.j, lo.k);
      let t = tl;
      // 인쇄본에서 9pt 안에 다른 쪽 줄이 있으면 그 줄과 같은 높이로 (한 줄씩 맞춤), 없으면 위·아래 줄 사이를 비례로
      const near = [lo, hi].filter(h => h && Math.abs(h.y - A.y) <= 9).sort((p, q) => Math.abs(p.y - A.y) - Math.abs(q.y - A.y))[0];
      if (near) { t = eff(o, near.j, near.k); x.m = true; }   // 맞은편 줄과 짝지어진 문단 (아래 같은 간격 맞추기에서 건드리지 않음 — 2026-11-15)
      else if (hi && hi.y > lo.y && A.y > lo.y + 2) t = tl + (A.y - lo.y) / (hi.y - lo.y) * (eff(o, hi.j, hi.k) - tl);
      const a = eff(A.s, A.i, x.k0);
      if (a < t - 1) x.d += t - a;
      else if (a > t + 1) {   // 다른 쪽이 늦음: 그쪽 다음 문단이 바로 이 높이에서 시작하면 그 문단을 내림
        const h = near && S[o][near.j].k0 === near.k ? near : null;
        if (h) { const th = eff(o, h.j, h.k); if (th < a - 1) S[o][h.j].d += a - th; }
        else if (near && A.i > 0) {   // 맞은편 줄이 문단 가운데 줄이라 내릴 수 없으면 이 문단을 앞 문단과의 빈 간격 안에서 끌어올림 (2026-11-15)
          const pv = S[A.s][A.i - 1], col = (A.s ? Rt : L).getBoundingClientRect().top;
          let dv = 0; for (let j = 0; j < A.i; j++) dv += S[A.s][j].d;
          const room = (eff(A.s, A.i, x.k0) - x.d) - (pv.p.getBoundingClientRect().bottom - col + dv) - 2;
          const pull = Math.min(a - t, Math.max(0, room)); if (pull > 0.5) x.d -= pull;
        }
      }
    }
    // 인쇄본에서 같은 간격으로 놓인 줄 묶음(예: '부처님을…/담마를…/상가를…')은 화면에서도 같은 간격으로 (운영자 요청, 2026-11-14)
    S.forEach((a, s) => {
      const gaps = [];
      const isH = x => x.p.classList.contains('sub-h') || x.p.getAttribute('role') === 'heading';   // 소제목 앞뒤 간격은 그대로 (양쪽 소제목 높이가 어긋나지 않게)
      for (let k = 0; k + 1 < a.length; k++) if (!isH(a[k]) && !isH(a[k + 1]) && !a[k + 1].m) gaps.push({ k, pg: a[k + 1].ys[a[k + 1].k0] - a[k].ys[a[k].k0], sg: eff(s, k + 1, a[k + 1].k0) - eff(s, k, a[k].k0) });
      // 같은 인쇄 간격끼리 묶음(2개 이상)을 찾고, 그 묶음들의 화면 간격을 인쇄본 간격에 비례하게 맞춤 (묶음 안은 같게, 묶음 사이는 더 넓게)
      const used = new Set(), cl = [];
      gaps.forEach(g => {
        if (used.has(g.k) || g.pg <= 0) return;
        const C = gaps.filter(h => !used.has(h.k) && h.pg > 0 && Math.abs(h.pg - g.pg) <= 1.5);
        C.forEach(h => used.add(h.k));
        if (C.length < 2) return;
        const M = Math.max(...C.map(h => h.sg)), m = Math.min(...C.map(h => h.sg));
        if (m > 0 && M <= m * 2.5) cl.push(C);
      });
      if (!cl.length) return;
      cl.sort((x, y) => x[0].pg - y[0].pg);
      let prev = null;
      cl.forEach(C => {
        let T = Math.max(...C.map(h => h.sg));
        if (prev) T = Math.max(T, prev.T * C[0].pg / prev.pg);   // 인쇄본에서 더 넓은 간격은 화면에서도 더 넓게
        C.forEach(h => { if (T - h.sg > 0.5) a[h.k + 1].d += T - h.sg; });
        prev = { T, pg: C[0].pg };
      });
    });
    S.forEach(a => a.forEach(x => { if (x.d > 0.5) x.p.style.paddingTop = x.d.toFixed(1) + 'px'; else if (x.d < -0.5) x.p.style.marginTop = x.d.toFixed(1) + 'px'; }));
  });
}
let sprAlignT = null;
window.addEventListener('resize', () => { clearTimeout(sprAlignT); sprAlignT = setTimeout(() => { if (R && R.ly && spreadOn()) sprAlign(); }, 150); });
if (document.fonts) document.fonts.addEventListener('loadingdone', () => { if (R && R.ly && spreadOn()) sprAlign(); });
function reflowHtml() {
  const cs = chapters(), ci = Math.max(0, chapterOf(R.i + 1)), c = cs[ci];
  const subs = R.toc.filter(t => /^\s/.test(t.title) && t.page >= c.from && t.page <= c.to);
  const body = R.pages.slice(c.from - 1, c.to).map(p => {
    const ps = paras(p.text); const sub = subs.filter(t => t.page === p.n);
    const keep = k => !(p.n === c.from && k < (c.k0 || 0)) && !(p.n === c.to && c.kEnd != null && k >= c.kEnd);
    const heads = new Set(R.toc.filter(t => t.page === p.n || t.page === p.n - 1).map(t => headKey(t.title)));
    if (!ps.length) return `<span id="pm-${p.n}"></span>`;
    return (spreadOn() ? `<div class="spr-pg ${p.n % 2 ? 'spr-r' : 'spr-l'}">` : '') + `<span class="pmark${p.label ? '' : ' nolabel'}" id="pm-${p.n}">${p.label ? esc(pageName(p)) : ''}</span>${ps.map((s, k) => !keep(k) ? '' : blockHtml(s, p.n, k) || `<p data-pg="${p.n}" data-s="${k}"${isFootnote(s) ? ` class="fn${k === ps.findIndex(isFootnote) ? ' fn-first' : ''}"` : isChDup(s, p.n, c, k) ? ' class="ch-dup"' : /^[❦❧✿❀＊*·•◆◇]+$/.test(s.trim()) ? ' class="orn" aria-hidden="true"' : /^\^\^ /.test(s) ? ' class="r-ctitle"' : /^:: /.test(s) ? ' class="r-center"' : /^>> /.test(s) ? ' class="r-right"' : /^\+\+ /.test(s) ? (/^\+\+ \d+\. /.test(s) ? ' class="r-ind r-num"' : ' class="r-ind"') : /^● /.test(s) ? ' class="r-bul"' : /^\|\| /.test(s) ? ' class="r-bul-c"' : (isHead(s) || heads.has(headKey(s))) && s.length < 120 ? ' class="sub-h" role="heading" aria-level="4"' : ''}>${fnMark(phMark(boldMark(markUl(s.replace(/^## |^\^\^ |^:: |^>> |^\|\| |^\+\+ /, '').replace(/\n(?:\^\^|::|>>) /g, '\n'), p.n)))).replace(/\n/g, '<br>').replace(/<br>● /g, /^● /.test(s) ? '<br><span class="bul-n">●</span> ' : '<br>● ')}</p>`).join('') || ''}` + (spreadOn() ? '</div>' : '');
  }).join('');
  const nav = `<nav class="ch-nav" aria-label="장 이동">${ci > 0 ? `<button class="tbtn" data-go="${cs[ci - 1].from}" data-ci="${ci - 1}">← ${esc(cs[ci - 1].title || '이전 장')}</button>` : '<span></span>'}${ci < cs.length - 1 ? `<button class="tbtn" data-go="${cs[ci + 1].from}" data-ci="${ci + 1}">${esc(cs[ci + 1].title || '다음 장')} →</button>` : '<span></span>'}</nav>`;
  // 장 제목과 같아 숨긴 본문 제목에 각주 번호가 붙어 있으면(예: '보시의 실천⁷') 위의 큰 장 제목에 그 번호를 붙여 보임 (2026-11-11)
  const dupFn = [...body.matchAll(/<p [^>]*class="ch-dup"[^>]*>(.*?)<\/p>/g)].flatMap(m => m[1].match(/<sup class="fn-ref"[^>]*>[^<]*<\/sup>/g) || []).join('');
  return `<div class="reflow ${fontCls()}${R.bold ? ' bold' : ''}${R.fs >= 1.75 ? ' big' : ''}${spreadOn() ? ' spread' : ''}${R.centerHeads ? ' chead' : ''}" style="--fs:${R.fs};--lh:${R.lh};--mw:${R.mw}em">${c.title ? `<div class="ch-head"><span class="small muted">${ci + 1} / ${cs.length}</span><h3>${boxNum(esc(c.title))}${dupFn}</h3></div>` : ''}${spreadOn() ? `<div class="spr">${body}</div>` : body}${nav}</div>`;
}
// 이 장 안의 소제목 자리(화면의 문단) 목록
// 굵은 글씨 한 줄만으로 된 짧은 문단(예: '[1. 사성제]', '수행이란 무엇인가?')도 소제목으로 봄 — 문장(. ! 로 끝남)·따옴표·괄호로 시작하는 강조 글은 빼고
const boldHead = e => { const t = e.textContent.trim(), b = e.firstElementChild; return !e.classList.contains('r-right') && e.children.length === 1 && b && b.tagName === 'STRONG' && b.textContent.trim() === t && t.length >= 2 && t.length <= 40 && !/[.!。…(]$/.test(t) && !/^[‘’'“”"(]/.test(t) && !/[가-힣]-(\s|$)/.test(t); };  // '나모- 땃사…' 같은 빠알리 독송 줄도 뺌
function subTargets(c) {
  if (!c) return [];
  // 소제목 글과 같은 문단(목차 쪽과 다음 쪽에서)을 찾아 그 자리로. 각주 문단에는 멈추지 않음 (운영자 요청, 2026-11-09)
  const nk = x => headKey(x).replace(/[.,:·\-–—!?■□▷◆◇_“”"]/g, '');  // 소제목 앞 □·▷ 표시는 빼고 비교 (DL-0034, 2026-11-17)
  const vis = e => e && e.getClientRects().length && !e.classList.contains('fn');
  // 장 끝의 굵은 한 줄(뒤에 본문 글이 없음 — 머리말 끝 서명 '…합장' 등)은 소제목이 아님: 거기 멈추면 장 끝 각주·사진에 멈춘 것처럼 보임 (운영자 요청, 2026-11-11)
  const hasAfter = e => { for (let x = e.nextElementSibling; x; x = x.nextElementSibling) if (x.matches('p[data-pg]:not(.fn):not(.ch-dup)') && !boldHead(x) && x.textContent.trim()) return true; return false; };
  return R.toc.filter(t => /^\s/.test(t.title) && t.page >= c.from && t.page <= c.to).map(t => {
    const want = nk(t.title).slice(0, 10);
    for (const pg of [t.page, t.page + 1]) {
      const ps = [...$$(`#rBody p[data-pg="${pg}"]`)].filter(vis);
      const tx = e => { const c = e.cloneNode(true); c.querySelectorAll('.fn-ref').forEach(x => x.remove()); return c.textContent; };  // 소제목 가운데 각주 번호는 빼고 비교 ('쌍신변[^231]의 신통…', DL-0024)
      const e = ps.find(e => e.classList.contains('sub-h') && nk(tx(e)).startsWith(want)) || ps.find(e => e.textContent.length < 160 && nk(tx(e)).startsWith(want));
      if (e) return e;
    }
    const e = $(`#rBody p[data-pg="${t.page}"][data-s="${paraIdx(t)}"]`);
    return vis(e) ? e : $('#pm-' + t.page);
  }).concat($$('#rBody .sub-h').filter(vis), $$('#rBody p[data-pg]').filter(boldHead).filter(vis).filter(hasAfter))  // 목차에 없는 본문 소제목(## 줄 등)에도 멈춤 — 모든 책 (운영자 요청, 2026-11-10)
    .filter((e, i, a) => e && a.indexOf(e) === i).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
}
const chHasSubs = n => { const c = chapters()[Math.max(0, chapterOf(n))]; return !!c && (R.toc.some(t => /^\s/.test(t.title) && t.page >= c.from && t.page <= c.to) || R.pages.slice(c.from - 1, c.to).some(p => /^## |^\*\*[^*\n]{2,40}\*\*$/m.test(p.text || ''))); };
function tocFor(n) { let cur = null; for (const t of R.toc) if (t.page <= n) cur = t; return cur; }
// 목차 창에 '책을 이해하는 데 필요한 내용이 담긴' 그림·표를 따로 표시 (운영자 요청, 2026-11-19 — 지도·가계도·도표·표기표·본문 표; 장식·속표지·제목 그림·로고·서명·QR·스승 사진·분위기 삽화는 뺌, 책 소개 페이지 목차에는 넣지 않음)
const FIG_KEEP = /지도|가계도|계보|도표|구성표|표기|운율|기호 보기|연기 표|팔정도|(^|\s)표($|\s|\d)/, FIG_DROP = /표지|상징|서명|초대코드|허가서|사진/;
function figList() {
  if (R._figs) return R._figs;
  const out = [], clean = x => String(x || '').replace(/\[\^[^\]]+\]/g, '').replace(/\*\*|°°|@@|==|§§/g, '').replace(/^#+\s*/, '').replace(/^\*\s*/, '').replace(/[:：]\s*$/, '').trim();
  const cut = x => { x = clean(x); const a = x.split(' — ')[0]; x = a.length >= 4 ? a : x; return x.length > 46 ? x.slice(0, 44) + '…' : x; };
  // 책에 인쇄된 '표 차례'(%% 문단의 '표 2b : … | 83')로 쪽 번호 → 표 이름, 없으면 바로 앞 짧은 글·그 쪽의 소제목
  const TOT = {}; for (const pg of R.pages) for (const q of paras(pg.text)) if (/^%% /.test(q)) for (const l of q.slice(3).split('\n')) { const m = l.replace(/^-+\s*/, '').match(/^(표\s*\S.*?)\s*\|\s*(\d+)\s*$/); if (m && !TOT[m[2]]) TOT[m[2]] = clean(m[1]); }
  const tabOf = lab => TOT[String(lab || '').replace(/\D/g, '')] || '';
  const near = (ps, k, i) => {
    const ok = q => { const c = clean(q); return c && !/^\[\^/.test(q) && !/^[!|=]/.test(q) && (/[:：]\s*(\[\^[^\]]+\]\s*)?$/.test(q.trim()) && c.length <= 60 || c.length <= 50 && !/[.。다]$/.test(c)) ? cut(c) : ''; };
    let pv = k ? ps[k - 1] : null;
    if (k === 0) { const pp = paras((R.pages[i - 1] || {}).text).filter(q => !/^\[\^/.test(q)); pv = pp[pp.length - 1] || ''; }  // 쪽 첫머리 표는 앞 쪽 끝의 안내 글('사대요소의 12가지 특징:')
    const a = pv != null && ok(pv); if (a) return a;
    for (let ii = i, kk = k; ii >= 0 && ii > i - 4; ii--, kk = Infinity) { const q = paras((R.pages[ii] || {}).text); for (let j = Math.min(kk, q.length) - 1; j >= 0; j--) if (/^## /.test(q[j])) return cut(q[j]); }  // 그 쪽·앞 쪽의 가장 가까운 소제목
    return '';
  };
  R.pages.forEach((p, i) => {
    const ps = paras(p.text);
    ps.forEach((q, k) => {
      const m = q.match(/^!\[([^\]]*)\]\(([^)\s]+)\)$/);
      if (m) {
        const alt = m[1].replace(/^#/, '').trim();
        if (FIG_DECO.test(alt) || FIG_DROP.test(alt)) return;
        const said = R.say && R.say[m[2]];
        if (alt === '표') {  // 『업과 윤회의 법칙』처럼 이름이 '표'뿐 — 바로 앞 '표 N : …' 글을 이름으로, 앞 쪽 표가 쪽을 넘어 이어진 것은 뺌
          const cap = k ? clean(ps[k - 1]) : '';
          if (/^표\s*\d/.test(cap)) { out.push({ pg: i + 1, k, kind: '표', label: cut(cap) }); return; }
          const prev = paras((R.pages[i - 1] || {}).text);
          if (k === 0 && /^!\[#?표\]/.test(prev[prev.length - 1] || '')) return;
          out.push({ pg: i + 1, k, kind: '표', label: tabOf(p.label) || near(ps, k, i) || '표' }); return;
        }
        if (!said && !FIG_KEEP.test(alt)) return;
        out.push({ pg: i + 1, k, kind: /지도/.test(alt) ? '지도' : /가계도|계보/.test(alt) ? '가계도' : /표/.test(alt) ? '표' : '그림', label: cut(alt) || '그림' });
        return;
      }
      if (q[0] !== '|' || q.startsWith('||') || /^\|\s*:?-{3}/.test(q)) return;  // '|| ' 는 쪽을 넘어 이어지는 항목 표시라 표가 아님  // 본문 표 (구분 줄로 시작하면 앞 쪽 표가 이어진 것)
      const pv = k ? ps[k - 1] : '', head = q.split('\n')[0].split('|').map(clean).filter(Boolean).slice(0, 3).join(' · ');
      let label = head;
      const fm = pv.match(/^\[\^([^\]]+)\]:\s*(.*)/s);
      if (fm) label = `각주 ${fm[1]} — ` + cut(fm[2].split(/[.。:](\s|$)/)[0]);
      else if (pv && !/^\|/.test(pv) && clean(pv).length <= 50 && !/[.。다]$/.test(clean(pv))) label = cut(pv);
      else if (head.split(' · ').every(c => c.length <= 3)) label = near(ps, k, i) || head;  // 'Ⅰ · Ⅱ · Ⅲ' 처럼 머리 줄로는 뜻을 알 수 없으면 가까운 소제목
      out.push({ pg: i + 1, k, kind: '표', label: label || '표' });
    });
  });
  return (R._figs = out);
}
const figBadge = (kind, label) => { const ic = kind === '표' ? '▦' : kind === '지도' ? '🗺' : kind === '가계도' ? '🌳' : '🖼'; return `<span class="fig-k"><span aria-hidden="true">${ic}</span>${String(label).startsWith(kind) ? '' : String(label).includes(kind) ? `<span class="sr">${kind}: </span>` : ` ${kind}`}</span>`; };
function tocWithFigs() {
  const figs = figList(), pos = R.toc.map(t => [t.page, paraIdx(t)]), after = R.toc.map(() => []), top = [], mark = new Map();
  const nk = x => String(x || '').replace(/[\s.:·,()\-—]/g, '').toLowerCase();
  for (const f of figs) {
    let j = -1; pos.forEach(([pg, k], i) => { if (pg < f.pg || (pg === f.pg && k <= f.k)) j = i; });
    if (j >= 0 && R.toc[j].page === f.pg && nk(R.toc[j].title).includes(nk(f.label).slice(0, 8))) { if (!mark.has(j)) mark.set(j, f.kind); continue; }  // 장 이름이 곧 그 그림(예: '지도 1 : …')이면 따로 줄을 두지 않고 장에 표시만
    (j >= 0 ? after[j] : top).push(f);
  }
  return { figs, top, after, mark };
}
function placePanels(el) {
  el = el || $('#reader'); if (!el) return; const t = $('.r-top', el); if (!t) return;
  el.style.setProperty('--ptop', Math.round(t.offsetTop + t.offsetHeight + 6) + 'px');  // 숨김(밀어 올림) 상태와 관계없이 원래 자리 기준
}
window.addEventListener('resize', () => placePanels());
// 화면 낭독기: 읽기 화면이 열려 있는 동안 뒤에 가려진 사이트(머리·본문·바닥)는 건너뛰게 (운영자 요청, 2026-11-17 — 화면은 그대로)
function bgInert(on) { $$('body > .skip, body > header.site, body > main, body > footer.site').forEach(x => { x.inert = on; if (on) x.setAttribute('aria-hidden', 'true'); else x.removeAttribute('aria-hidden'); }); }
// 읽기 화면을 다시 그리기 전에 커서가 있던 단추를 기억 (id 또는 data-* 값)
function focusKey(el) {
  const a = document.activeElement; if (!a || a === el || !el.contains(a)) return null;
  if (a.id) return '#' + CSS.escape(a.id);
  const d = [...a.attributes].find(x => /^data-(?!tip)/.test(x.name)); return d ? `${a.tagName.toLowerCase()}[${d.name}="${CSS.escape(d.value)}"]` : null;
}
function renderReader() {
  let el = $('#reader');
  if (!el) { el = document.createElement('div'); el.id = 'reader'; el.className = 'reader'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '읽기 화면'); el.setAttribute('aria-modal', 'true'); document.body.appendChild(el); bgInert(true); document.body.style.overflow = 'hidden'; el.classList.add('chrome-off'); }
  el.dataset.book = R.id || '';  // 책마다 다른 모양(site.css #reader[data-book=…])
  const p = R.pages[R.i], n = p.n, N = R.pages.length, marked = bms().some(m => m.id === R.id && m.p === n);
  const hasText = R.pages.some(x => x.text), hasImg = R.pages.some(x => x.img);
  const ch = tocFor(n);
  const fkey = focusKey(el);  // 다시 그려도 키보드·화면 낭독기 커서가 같은 단추에 남게 (운영자 요청, 2026-11-17)
  el.innerHTML = `<button class="r-skip" id="rMenu" aria-keyshortcuts="Alt+Shift+M">메뉴 열기 (듣기·목차·설정·닫기)</button><button class="r-skip" id="rKeys" aria-keyshortcuts="Alt+Shift+H">단축키 안내</button><div class="r-top"><button class="tbtn" id="rClose" aria-label="『${esc(R.title)}』 읽기 끝내기, 책 소개로 돌아가기">← 닫기</button>
    <div class="r-title">${esc(R.title)}<small>${esc(R.by)}${ch ? ' · ' + esc(ch.title) : ''}</small></div>
    <div class="r-tools">
      ${R.toc.length ? '<button class="tbtn" data-panel="toc">목차</button>' : ''}${hasText ? '<button class="tbtn" data-panel="find" aria-label="찾기 (본문 검색)">🔍 찾기</button>' : ''}
      <button class="tbtn" data-panel="font" aria-label="글씨 크기">가<span style="font-size:16px">가</span></button>
      ${hasText && R.speaking ? `<button class="tbtn ${R.ttsLocked ? 'on' : ''}" id="rLock" aria-pressed="${!!R.ttsLocked}" aria-label="${R.ttsLocked ? '듣기 잠김, 눌러서 풀기' : '듣기 잠그기'}" title="잠그면 실수로 멈추지 않습니다">${R.ttsLocked ? '🔒 잠김' : '🔓 잠금'}</button>` : ''}${R.ab ? `<button class="tbtn ${AB.on && !abA().paused ? 'on' : ''}" id="rAb" data-tip="${AB_TIP}" aria-label="오디오북 듣기 (${AB_TIP})">${AB.on && !abA().paused ? '❚❚ 오디오북' : '🎧 오디오북'}</button>` : ''}${hasText ? `<button class="tbtn ${R.speaking ? 'on' : ''}" id="rSpeak" ${R.ttsLocked ? 'disabled' : ''}>${R.speaking ? '■ 멈춤' : '▶ 듣기'}</button><button class="tbtn" data-panel="tts" aria-label="듣기 설정">듣기 설정</button>` : ''}
      <button class="tbtn" data-panel="mode">화면</button>${R.par.length && R.view !== 'page' ? `<button class="tbtn${R.parMode !== 'off' ? ' on' : ''}" data-panel="par" title="번역서와 원서를 나란히 보기">⇄ 원서 대조</button>` : ''}${R.spreadOk && R.view !== 'page' ? `<button class="tbtn${spreadOn() ? ' on' : ''}" id="rSpread" aria-pressed="${spreadOn()}" title="왼쪽·오른쪽 쪽을 책처럼 나란히">${spreadOn() ? '📄 한쪽씩 보기' : '📖 양쪽으로 보기'}</button>` : ''}${document.fullscreenEnabled ? `<button class="tbtn" id="rFull" aria-pressed="${!!document.fullscreenElement}" title="F11 처럼 화면 가득 보기 (Esc 로 나가기)">${document.fullscreenElement ? '⛶ 전체 화면 끄기' : '⛶ 전체 화면'}</button>` : ''}
      <button class="tbtn ${marked ? 'on' : ''}" id="rMark" aria-pressed="${marked}">${marked ? '★ 책갈피' : '☆ 책갈피'}</button>
      <button class="tbtn" data-panel="bm">책갈피 목록</button>
      ${hasText ? '<button class="tbtn" data-panel="ul">밑줄 모음</button>' : ''}
    </div></div>
    ${R.hl.length ? `<div class="variant-note" style="border-radius:0">찾은 말을 표시하고 있습니다. <button id="hlOff">표시 끄기</button></div>` : ''}
    <div class="r-body" id="rBody">${R.view === 'page' ? pageHtml(p) : reflowHtml()}</div>
    <div class="r-bottom"><button class="tbtn" id="rPrev" ${(R.view === 'text' ? chapterOf(n) === 0 && !chHasSubs(n) && stepUnit() !== 'sent' && stepUnit() !== 'para' && stepUnit() !== 'page' : R.i === 0) ? 'disabled' : ''} aria-label="${R.view === 'text' ? stepName(-1) : '이전 쪽'}">‹</button>
      <label for="rRange" class="sr">쪽 이동</label><input type="range" id="rRange" min="1" max="${N}" value="${n}">
      <span class="pg">${p.label ? esc(p.label) + '쪽 · ' : ''}${n} / ${N}</span><button class="tbtn" id="rNext" ${(R.view === 'text' ? chapterOf(n) >= chapters().length - 1 && !chHasSubs(n) && stepUnit() !== 'sent' && stepUnit() !== 'para' && stepUnit() !== 'page' : R.i === N - 1) ? 'disabled' : ''} aria-label="${R.view === 'text' ? stepName(1) : '다음 쪽'}">›</button></div>
    <div class="panel" id="p-find"><h5>이 책에서 찾기</h5>
      <form id="findForm" class="row" style="gap:6px"><input id="findQ" placeholder="찾을 말" aria-label="찾을 말" value="${esc(R.findQ || '')}" style="flex:1;height:36px;border:1px solid var(--line);border-radius:8px;padding:0 10px;background:var(--paper)"><button class="tbtn" type="submit">찾기</button></form>
      <div id="findRes">${R.findRes || '<p class="note">낱말을 넣으면 이 책의 모든 쪽에서 찾습니다. 위빳사나·vipassanā처럼 다른 표기도 함께 찾습니다.</p>'}</div></div>
    <div class="panel" id="p-toc"><h5>목차</h5>${(() => { const W = tocWithFigs(), fli = f => { const pg = R.pages[f.pg - 1] || {}; return `<li class="fig"><button class="link" data-fgo="${f.pg}" data-fk="${f.k}">${figBadge(f.kind, f.label)} ${esc(f.label)}</button><span class="muted">${esc(pg.label || '')}</span></li>`; };
      return (W.figs.length ? `<label class="fig-only"><input type="checkbox" id="figOnly"> 그림·표만 보기 <span class="muted">(${W.figs.length})</span></label>` : '') + `<ul>${W.top.map(fli).join('')}${R.toc.map((t, j) => `<li class="${/^\s/.test(t.title) ? 'sub' : ''}${W.mark.has(j) ? ' has-fig' : ''}"><button class="link" data-go="${t.page}"${!/^\s/.test(t.title) ? ` data-ci="${chapters().findIndex(c => c.title === t.title.trim() && c.from === t.page)}"` : ''}>${W.mark.has(j) ? figBadge(W.mark.get(j), t.title) + ' ' : ''}${boxNum(esc(t.title.trim()))}</button><span class="muted">${esc(t.label || '')}</span></li>` + W.after[j].map(fli).join('')).join('')}</ul>`; })()}</div>
    <div class="panel" id="p-font"><h5>글씨</h5>
      ${R.view === 'page' && hasImg ? `<div class="row">쪽 확대 <span><button class="tbtn" data-zoom="-1" aria-label="쪽 축소">−</button> ${Math.round(R.zoom * 100)}% <button class="tbtn" data-zoom="1" aria-label="쪽 확대">+</button></span></div>${hasText ? '<p class="note">쪽 보기에서는 원본 쪽을 확대합니다. 글자만 크게 보거나 밑줄을 그으려면 ‘글로 보기’로 바꾸세요.</p>' : ''}` :
      `<div class="row">글자 크기 <span class="fs-step"><button class="tbtn" data-fsd="-1" aria-label="글자 작게">가−</button><b aria-live="polite">${Math.round(R.fs * 100)}%</b><button class="tbtn" data-fsd="1" aria-label="글자 크게">가+</button></span></div>
       <div class="row row-col">빨리 고르기 <span class="seg seg-grid">${[1, 1.5, 2, 3, 4].map(v => `<button data-fs="${v}" class="${R.fs === v ? 'on' : ''}" aria-label="글자 ${v * 100}%">${v * 100}%</button>`).join('')}</span></div>
       <div class="row">글자 굵기 <span class="seg"><button data-bold="0" class="${R.bold ? '' : 'on'}">보통</button><button data-bold="1" class="${R.bold ? 'on' : ''}">굵게</button></span></div>
       <div class="row">줄 간격 <span class="seg">${[[1.6, '좁게'], [1.9, '보통'], [2.2, '넓게']].map(([v, l]) => `<button data-lh="${v}" class="${R.lh === v ? 'on' : ''}">${l}</button>`).join('')}</span></div>
       <div class="row row-col">글꼴 <span class="seg seg-grid seg-font">${RFONTS.map(([k, l, ff]) => `<button data-font="${k}" class="${R.font === k ? 'on' : ''}" style="font-family:${ff}">${l}</button>`).join('')}</span></div>
       <div class="row mw-row">글 너비 <span class="seg">${[[28, '좁게'], [36, '보통'], [46, '넓게'], [70, '화면 가득']].map(([v, l]) => `<button data-mw="${v}" class="${R.mw === v ? 'on' : ''}">${l}</button>`).join('')}</span></div>${R.spreadOk && spreadWide() ? `
       <div class="row">쪽 보기 <span class="seg"><button data-spread="0" class="${R.spread ? '' : 'on'}">한쪽씩</button><button data-spread="1" class="${R.spread ? 'on' : ''}">양쪽으로</button></span></div>` : ''}`}</div>
    <div class="panel" id="p-tts">${ttsPanel()}</div>
    ${R.par.length ? `<div class="panel" id="p-par"><h5>⇄ 원서 대조</h5><div class="seg">${[['off', '끄기'], ['para', '문단 나란히'], ['sent', '문장마다']].map(([k, v]) => `<button data-parm="${k}" class="${R.parMode === k ? 'on' : ''}">${v}</button>`).join('')}</div>
      <p class="note">문단 나란히: 한국어 문단 옆(휴대폰은 아래)에 원서 문단. 문장마다: 한국어 문장과 원서 문장을 번갈아. 짝은 자동으로 맞춘 것이라 조금 어긋난 곳이 있을 수 있습니다.</p></div>` : ''}
    <div class="panel" id="p-mode"><h5>화면 모드</h5><div class="seg">${[['day', '기본'], ['mono', '흑백'], ['night', '밤'], ['contrast', '고대비']].map(([k, v]) => `<button data-rmode="${k}" class="${store.get('mode', 'auto') === k ? 'on' : ''}">${v}</button>`).join('')}</div><p class="note">고른 모드는 사이트 전체에 적용되고 다음에 와도 유지됩니다.</p>${R.view === 'text' ? `<h5 class="rstep-h">‹ › 넘기는 단위</h5><div class="seg" role="group" aria-label="‹ › 넘기는 단위">${STEP_UNITS.map(([k, v]) => `<button data-rstep="${k}" class="${stepUnit() === k ? 'on' : ''}">${v}</button>`).join('')}</div><p class="note">아래 바의 ‹ › 단추를 누르면 이 단위로 넘어갑니다. 쪽 막대를 끌어 옮기는 것은 그대로입니다.</p>` : ''}</div>
    <div class="panel" id="p-ul"><h5>이 책의 밑줄</h5><ul>${uls().filter(h => h.id === R.id).sort((a, b) => a.p - b.p).map(h => `<li style="display:block"><button class="link" data-go="${h.p}">${esc(h.pl || h.p)}쪽</button><div class="quote" style="font-size:13.5px">${esc(h.text)}</div>${h.note ? `<div class="small muted">${esc(h.note)}</div>` : ''}</li>`).join('') || '<li class="muted">글을 끌어서 고르면 밑줄을 그을 수 있습니다.</li>'}</ul>
      <div class="row"><a class="tbtn" href="/mynotes/">내 서재에서 모두 보기</a></div></div>
    <div class="panel" id="p-share"><h5>고른 글 공유하기</h5><div class="quote" id="shText" style="font-size:13.5px;white-space:pre-wrap"></div>
      <div class="share-btns">${navigator.share ? '<button class="sh-main" data-sh="app">📱 카카오톡·문자 등 앱으로 보내기</button>' : ''}<button data-sh="kakao">카카오톡</button><button data-sh="band">네이버 밴드</button><button data-sh="x">X(트위터)</button><button data-sh="fb">페이스북</button><button data-sh="mail">이메일</button>${R.noCopy ? '' : '<button data-sh="copy">복사</button>'}</div>
      <p class="note">고른 글 아래에 책 제목·저자·쪽과 이 쪽으로 오는 주소가 함께 붙습니다.</p></div>
    <div class="panel" id="p-uledit"><h5>밑줄</h5><div class="quote" id="ulText" style="font-size:13.5px"></div>
      <div class="row"><input id="ulNote" placeholder="메모 한 줄" aria-label="밑줄 메모" style="flex:1;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 8px;background:var(--paper)"></div>
      <div class="row"><button class="tbtn" id="ulSave">메모 저장</button>${R.noCopy ? '' : '<button class="tbtn" id="ulCopy">출처와 함께 복사</button>'}<button class="tbtn" id="ulDel">밑줄 지우기</button></div></div>
    <div class="sel-pop" id="selPop" role="toolbar" aria-label="고른 글"><button id="selUl">밑줄 긋기</button><button id="selNote">밑줄+메모</button>${R.noCopy ? '' : '<button id="selCopy">복사</button>'}<button id="selShare">공유</button>${R.pages.some(x => x.text) ? '<button id="selPlay">▶ 여기부터 듣기</button>' : ''}${R.ab ? '<button id="selAb">🎧 여기부터 오디오북</button>' : ''}</div>
    <div class="panel" id="p-bm"><h5>내 책갈피</h5><ul>${bms().map((m, k) => `<li><span><a class="link" href="/read/${m.id}/${m.p}">『${esc(m.t)}』 ${esc(m.pl || m.p)}쪽</a>${m.note ? `<br><span class="muted small">${esc(m.note)}</span>` : ''}</span><button class="link" data-bmdel="${k}" aria-label="책갈피 지우기">지우기</button></li>`).join('') || '<li class="muted">아직 책갈피가 없습니다.</li>'}</ul>
      <div class="row" style="margin-top:12px"><input id="bmNote" placeholder="이 쪽에 한 줄 메모" aria-label="책갈피 메모" style="flex:1;height:34px;border:1px solid var(--line);border-radius:8px;padding:0 8px;background:var(--paper)"><button class="tbtn" id="bmSave">저장</button></div>
      <p class="note">회원가입 없이 이 기기의 브라우저에만 저장됩니다. 다른 기기로 옮길 때는 내 서재의 ‘옮기기’를 쓰세요.</p></div>
    <div class="panel" id="p-keys"><h5>단축키 안내</h5><p class="note" tabindex="0">Alt 키와 Shift 키를 함께 누른 채로 아래 글자 키를 누릅니다. (맥은 Option + Shift). 창을 여는 단축키는 한 번 더 누르면 창이 닫히고, 연 단추로 돌아갑니다.</p><ul class="keys">${KEYS.map(([k, d]) => `<li tabindex="0">${k ? `<kbd>Alt+Shift+${k}</kbd> ` : ''}${d}</li>`).join('')}<li tabindex="0"><kbd>Esc</kbd> 열린 창 닫기 (창이 없으면 읽기 끝내기)</li><li tabindex="0"><kbd>→</kbd> <kbd>←</kbd> (오른쪽·왼쪽 화살표 키) 다음 쪽·앞 쪽으로 넘기기 — 눈으로 보며 읽는 분을 위한 키입니다. 화면 낭독기를 쓰실 때는 Alt+Shift+→ ← 를 쓰세요. 듣는 중에는 → ← 가 다음·앞 문장으로 갑니다.</li></ul></div>`;
  bindReader();
  el._fkey = null;
  if (fkey) { const f = $(fkey, el); if (f && f.offsetParent !== null) f.focus({ preventScroll: true }); else el._fkey = fkey; }  // 닫힌 창 안의 단추면 창을 다시 연 뒤(reopen)에 커서를 되돌림
  sprBar(); spreadWas = spreadOn();  // 화면을 돌리면 처음 한 번부터 바로 다시 그리게
  parApply();
  sprAlign(); if (R && R.ly && spreadOn()) $$('#rBody .spr img').forEach(im => { if (!im.complete) im.addEventListener('load', () => { clearTimeout(sprAlignT); sprAlignT = setTimeout(sprAlign, 100); }, { once: true }); });
  if (R.view === 'text') { const c = chapters()[Math.max(0, chapterOf(n))]; const pm = $('#pm-' + n); if (pm && n !== c.from) pm.scrollIntoView({ block: 'start' }); else $('#rBody').scrollTop = 0; }
  // 다음 쪽 그림 미리 받기
  const nx = R.pages[R.i + 1]; if (nx && nx.img && R.view === 'page') { const im = new Image(); im.src = nx.img; }
  if (AB.on) { el.classList.add('ab-on'); abMark(!AB.detached && Date.now() - AB.userAt > 8000); }
  latLater();  // 화면 낭독기: DPD 낱말 목록을 뒤에서 받아 로마자 빠알리어를 한 번 더 가름 (2026-11-17)
  store.set('pos-' + R.id, n);
  saveHistory(n);
  history.replaceState(history.state, '', `/read/${R.id}/${n}` + location.search);
}
function go(n, ci) { if (!R) return; if (R.ttsLocked) { toast('듣기가 잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요'); return; } if (AB.on) AB.detached = true; /* 직접 다른 곳으로 가면 오디오북 따라가기를 멈춤 (📍 로 다시) */ R.chForce = ci == null || isNaN(ci) ? null : ci; R.i = Math.max(0, Math.min(R.pages.length - 1, n - 1)); stopSpeak(); renderReader(); if (R.view === 'page') $('#rBody').scrollTop = 0; }
// 휴대폰·태블릿(손가락 화면)은 가로로 눕혀 넓어져도(양쪽으로 보기 등) 같은 방식으로 메뉴를 숨김 (운영자 요청, 2026-11-14)
const immersive = () => matchMedia('(max-width:700px)').matches || matchMedia('(hover:none) and (pointer:coarse)').matches;
function bindReader() {
  const el = $('#reader');
  const reopen = id => { $('#' + id).classList.add('open'); const k = el._fkey; el._fkey = null; if (k) { const f = $(k, el); if (f) try { f.focus({ preventScroll: true }); } catch (e) {} } };  // 설정 창의 고른 단추(예: 글자 150%)에 커서가 남게 (운영자 요청, 2026-11-18)
  $('#rClose').onclick = exitReader;
  $('#rMenu').onclick = () => { el.classList.remove('chrome-off'); setTimeout(() => { const b = $('#rClose'); if (b) b.focus(); }, 30); };  // 화면 낭독기·키보드용 숨은 단추 (운영자 요청, 2026-11-17)
  // 글로 보기에서는 한 화면이 한 장(章)이므로 ‹ › 는 장 단위로 넘깁니다 (쪽 단위면 같은 화면이 되풀이됨)
  const stepCh = d => { const cs = chapters(), ci = chapterOf(R.i + 1), t = cs[ci + d]; if (!t) { toast(d > 0 ? '책의 끝입니다' : '책의 처음입니다'); return; } if (t) { go(t.from, ci + d); $('#rBody').scrollTop = 0; window.scrollTo(0, 0); } };
  // 장 안에 소제목(목차의 들여쓴 항목)이 있으면 › 는 다음 소제목으로, ‹ 는 앞 소제목으로 내려가고/올라가고, 장 끝·처음에서만 장을 넘김 (운영자 요청, 2026-11-09)
  // 소제목으로 옮긴 뒤 위쪽 그림이 늦게 받아져 글이 밀리면(사진·구분선 자리에 멈춘 것처럼 보임) 몇 초 동안 소제목 자리를 다시 맞춤 (운영자 요청, 2026-11-10)
  // 위 메뉴가 떠 있으면(글 위에 겹쳐 보임) 그 높이만큼 아래에 소제목이 오게 — 메뉴에 가려 사진·구분선에 멈춘 것처럼 보이지 않게
  const navOff = () => { const t = $('.r-top', el); return 8 + (t && !el.classList.contains('chrome-off') ? t.offsetHeight : 0); };
  const pin = e => {
    const body = $('#rBody'); if (!body || !e) return;
    const place = () => { body.scrollTop = Math.max(0, e.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop - navOff()); };
    place(); const until = Date.now() + 6000; R.pinEl = e; R.lastPin = e;
    // 그림이 늦게 받아지거나 글꼴(한글 글꼴은 필요한 글자 묶음을 나중에 받음)이 바뀌어 글 높이가 달라지면 소제목 자리를 다시 맞춤.
    // 읽는 분이 직접 넘기면(휠·터치·스크롤 막대·키보드) 그만 — stop
    const fix = () => { if (R && R.pinEl === e && Date.now() < until) place(); };
    $$('#rBody img').forEach(im => { if (!im.complete) im.addEventListener('load', fix, { once: true }); });
    // 처음 2초는 화면을 그릴 때마다 자리를 다시 확인(글꼴·그림으로 글이 밀리는 것을 바로 따라잡음)
    const t0 = Date.now(); const tick = () => { if (!R || R.pinEl !== e || Date.now() - t0 > 2000) return; const want = Math.max(0, e.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop - navOff()); if (Math.abs(want - body.scrollTop) > 2) body.scrollTop = want; requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    let ro = null; const box = e.closest('.reflow') || body.firstElementChild;
    if (window.ResizeObserver && box) { ro = new ResizeObserver(fix); ro.observe(box); setTimeout(() => ro && ro.disconnect(), 6000); }
    if (document.fonts && document.fonts.addEventListener) { document.fonts.addEventListener('loadingdone', fix); setTimeout(() => document.fonts.removeEventListener('loadingdone', fix), 6000); }
    const stop = () => { if (R && R.pinEl === e) R.pinEl = null; if (ro) { ro.disconnect(); ro = null; } body.removeEventListener('wheel', stop); body.removeEventListener('touchstart', stop); };
    body.addEventListener('wheel', stop, { passive: true }); body.addEventListener('touchstart', stop, { passive: true }); body.addEventListener('mousedown', stop); document.addEventListener('keydown', stop, { once: true });  // 직접 넘기기 시작하면 그만
  };
  const stepSub = d => {
    const body = $('#rBody'), cs = chapters(), ci = chapterOf(R.i + 1), c = cs[Math.max(0, ci)];
    const top0 = body.getBoundingClientRect().top, cur = body.scrollTop;
    // 서로 아주 가까운 자리(40px 안)는 하나로 — 같은 소제목에 두 번 멈추지 않게 (운영자 요청, 2026-11-10)
    const ts = subTargets(c).map(e => ({ e, y: e.getBoundingClientRect().top - top0 + body.scrollTop - navOff() }))
      .filter((v, i, a) => !i || v.y - a[i - 1].y > 40);
    // 방금 멈춘 소제목이 늦게 받아진 그림 때문에 조금 내려가 있어도 다시 멈추지 않음
    const last = R.lastPin, near = v => v.e === last && Math.abs(v.y - cur) < body.clientHeight * 0.6;
    if (d > 0) {
      // 화면 위쪽(30%)에 이미 보이는 소제목은 건너뜀 — 장 처음 화면에 바로 보이는 소제목에서 또 멈추지 않게 (운영자 요청, 2026-11-10)
      const t = ts.find(v => v.y > cur + Math.max(12, body.clientHeight * 0.3) && !near(v));
      if (t && (t.y < body.scrollHeight - body.clientHeight + 4 || cur < body.scrollHeight - body.clientHeight - 12)) { pin(t.e); return; }
      stepCh(1);
    } else {
      const t = ts.filter(v => v.y < cur - 12 && !near(v)).pop();
      if (t) { pin(t.e); return; }
      if (cur > 12) { body.scrollTop = 0; return; }
      stepCh(-1);
    }
  };
  el._stepSub = stepSub;  // Alt+Shift+↓↑ 단축키가 씀
  // ‹ › 넘기는 단위 — 문장·문단·쪽·소제목·장 (운영자 요청, 2026-11-19: '화면' 창에서 고름, 처음 값 소제목, 이 기기에 기억)
  const body0 = () => $('#rBody');
  const yOf = e => { const b = body0(); return e.getBoundingClientRect().top - b.getBoundingClientRect().top + b.scrollTop - navOff(); };
  const paraEls = () => $$('#rBody .reflow [data-pg][data-s]').filter(x => x.matches('p,div.r-toc,div.tbl,table,figure,div') && !x.matches('.fn,.ch-dup,.orn,[data-skip]') && !x.closest('.fn,.ch-dup') && x.getClientRects().length && (x.textContent || '').trim());
  const speakFrom = e => {  // 듣는 중이면 옮긴 자리의 문단부터 이어 읽음
    if (!e) return; const all = paraEls(); const p = e.matches && e.matches('[data-pg][data-s]') ? e : all.find(x => x === e || (e.compareDocumentPosition(x) & 4));
    if (!p) return; stopSpeak(false); R.i = +p.dataset.pg - 1; speak(+p.dataset.s);
  };
  const flash = e => { if (!e || !e.classList) return; e.classList.add('found'); setTimeout(() => e.classList.remove('found'), 1400); };
  const paraStep = d => {
    const b = body0(), cur = b.scrollTop, all = paraEls();
    const sp = R.speaking && $('#rBody .speaking');
    let t = null;
    if (sp) { const i = all.indexOf(sp); t = i < 0 ? null : all[i + d]; if (t) { speakFrom(t); return; } stepCh(d); setTimeout(() => speak(), 60); return; }  // 듣는 중: 앞·다음 문단부터 읽음, 장 끝·처음이면 다음·앞 장 처음부터
    const ys = all.map(e => ({ e, y: yOf(e) }));
    if (d > 0) t = ys.find(v => v.y > cur + 6); else t = ys.filter(v => v.y < cur - 6).pop();
    if (!t) { if (d > 0) stepCh(1); else if (cur > 12) b.scrollTop = 0; else stepCh(-1); return; }
    pin(t.e); flash(t.e); kbFocus(t.e);
  };
  const pageStep = d => {
    const b = body0(), cur = b.scrollTop, ms = $$('#rBody .pmark').map(e => ({ e, y: yOf(e), n: +e.id.slice(3) }));
    const spk = R.speaking && $('#rBody .speaking');
    let t;
    if (spk) { const pg = +spk.dataset.pg, first = paraEls().find(x => +x.dataset.pg === pg) === spk;  // 듣는 중: 쪽 처음에서 ‹ 면 앞 쪽, 쪽 중간이면 이 쪽 처음
      t = d > 0 ? ms.find(v => v.n > pg) : first ? ms.filter(v => v.n < pg).pop() : ms.find(v => v.n === pg); }
    else t = d > 0 ? ms.find(v => v.y > cur + 6) : ms.filter(v => v.y < cur - 6).pop();
    if (t) { pin(t.e); kbFocus(t.e); if (R.speaking) speakFrom(t.e); return; }
    if (d < 0 && cur > 12) { b.scrollTop = 0; return; }
    const n = (ms.length ? (d > 0 ? ms[ms.length - 1].n : ms[0].n) : R.i + 1) + d;
    if (n < 1 || n > R.pages.length) { toast(d > 0 ? '책의 끝입니다' : '책의 처음입니다'); return; }
    const was = R.speaking; go(n);
    setTimeout(() => { const m = $('#pm-' + n); if (m && m.getClientRects().length) { pin(m); kbFocus(m); } if (was) { R.i = n - 1; speak(); } }, 120);
  };
  const chStep = d => {
    const b = body0(); if (d < 0 && b.scrollTop > 12) { b.scrollTop = 0; if (R.speaking) { const c = chapters()[chapterOf(R.i + 1)]; stopSpeak(false); if (c) R.i = c.from - 1; speak(); } return; }
    const was = R.speaking; stepCh(d); if (was) setTimeout(() => speak(), 60);
  };
  // 문장: 문단 글을 '듣기'와 같은 규칙(splitSents)으로 나눠 그 문장에 노란 표시. 듣는 중이면 앞·다음 문장을 읽음
  const sentRanges = p => {
    const tw = document.createTreeWalker(p, NodeFilter.SHOW_TEXT), nodes = []; let n, all = '';
    while ((n = tw.nextNode())) { nodes.push([n, all.length]); all += n.data; }
    const ss = splitSents(all), out = []; let at = 0;
    ss.forEach(x => { const i = all.indexOf(x.trim().slice(0, 4), at); const st = i < 0 ? at : i; const en = st + x.trim().length; at = en; out.push([st, en]); });
    const pos = off => { for (let j = nodes.length - 1; j >= 0; j--) if (nodes[j][1] <= off) return [nodes[j][0], Math.min(off - nodes[j][1], nodes[j][0].data.length)]; return [p, 0]; };
    return out.map(([a, z]) => { const r = document.createRange(); try { r.setStart(...pos(a)); r.setEnd(...pos(Math.max(a, z))); } catch (e) {} return r; });
  };
  const markSent = r => { try { if (window.CSS && CSS.highlights && window.Highlight) { if (r) CSS.highlights.set('rsent', new Highlight(r)); else CSS.highlights.delete('rsent'); } } catch (e) {} };
  const sentStep = d => {
    if (R.speaking && TT.jump) { TT.jump(d); return; }
    const b = body0(), all = paraEls(), bt = b.getBoundingClientRect().top + navOff();
    let st = R.sentAt && document.contains(R.sentAt.p) && all.includes(R.sentAt.p) ? R.sentAt : null;
    if (st) { const r = sentRanges(st.p)[st.i]; const rc = r && r.getBoundingClientRect(); if (!rc || rc.bottom < bt - 4 || rc.top > b.getBoundingClientRect().bottom) st = null; }  // 화면에서 벗어났으면 지금 화면에서 다시
    let p, i;
    if (st) { p = st.p; i = st.i + d; let rs = sentRanges(p);
      while (i < 0 || i >= rs.length) { const k = all.indexOf(p) + (i < 0 ? -1 : 1); if (k < 0 || k >= all.length) { markSent(null); R.sentAt = null; if (d > 0) stepCh(1); else stepCh(-1); return; } p = all[k]; rs = sentRanges(p); i = i < 0 ? rs.length - 1 : 0; }
    } else {
      // 지금 화면 맨 위(메뉴 아래)에 보이는 첫 문장 — › 는 그 문장, ‹ 는 그 앞 문장
      let hit = null;
      for (const e of all) { const rs = sentRanges(e); for (let j = 0; j < rs.length; j++) { const rc = rs[j].getBoundingClientRect(); if (rc.height && rc.top >= bt - 2) { hit = [e, j]; break; } } if (hit) break; }
      if (!hit) { if (d > 0) stepCh(1); else stepCh(-1); return; }
      [p, i] = hit; if (d < 0) { i--; if (i < 0) { const k = all.indexOf(p) - 1; if (k < 0) { if (b.scrollTop > 12) b.scrollTop = 0; else stepCh(-1); return; } p = all[k]; i = sentRanges(p).length - 1; } }
    }
    const r = sentRanges(p)[i]; if (!r) return; R.sentAt = { p, i }; markSent(r);
    const rc = r.getBoundingClientRect(), bb = b.getBoundingClientRect(), bot = $('.r-bottom', el), lim = bb.bottom - (bot && !el.classList.contains('chrome-off') ? bot.offsetHeight : 0) - 8;
    if (rc.top < bt || rc.bottom > lim) b.scrollTop += rc.top - bt - 4;  // 화면 밖이면 그 문장이 위쪽에 오게
    kbFocus(p);
  };
  const stepBy = d => {
    if (R.view !== 'text') { go(R.i + 1 + d); return; }
    const u = stepUnit(); if (u !== 'sent') { markSent(null); R.sentAt = null; }
    if (!R.speaking || u !== 'sent') toast(stepName(d));  // 먼저 알림 — 옮기다 '책의 끝입니다' 등이 뜨면 그 알림이 보이게
    // 듣는 중이면 읽고 있는 문단 자리를 기준으로(화면이 다른 곳에 있어도) — 쪽·소제목이 듣는 곳에서 앞뒤로
    const spk = R.speaking && $('#rBody .speaking'); if (spk && u === 'sub') { body0().scrollTop = Math.max(0, yOf(spk) + 2); R.lastPin = null; }
    if (u === 'sent') sentStep(d);
    else if (u === 'para') paraStep(d);
    else if (u === 'page') pageStep(d);
    else {
      const ci = chapterOf(R.i + 1), was = R.speaking; R.pinEl = null;
      if (u === 'ch') chStep(d); else stepSub(d);
      // 옮긴 소제목·장 제목에 커서 — 화면 낭독기가 거기서부터 읽게(Alt+Shift+↓↑ 와 같음)
      setTimeout(() => { const e = R.pinEl && document.contains(R.pinEl) ? R.pinEl : null, t = e || (chapterOf(R.i + 1) !== ci || u === 'ch' ? $('.ch-head h3') : null); if (!R.speaking) kbFocus(t); if (was && u === 'sub' && e) speakFrom(e); }, 160);
    }
  };
  el._stepBy = stepBy;
  $('#rPrev').onclick = () => stepBy(-1); $('#rNext').onclick = () => stepBy(1);
  $$('[data-rstep]', el).forEach(b => b.onclick = () => { store.set('rstep', b.dataset.rstep); $$('[data-rstep]', el).forEach(x => x.classList.toggle('on', x === b)); const a = $('#rPrev'), z = $('#rNext'); if (a) a.setAttribute('aria-label', stepName(-1)); if (z) z.setAttribute('aria-label', stepName(1)); markSent(null); R.sentAt = null; sayKey(`‹ › 넘기는 단위: ${b.textContent}`); }); $('#rRange').onchange = e => go(+e.target.value);
  const ff = $('#findForm'); if (ff) ff.onsubmit = async ev => {
    ev.preventDefault(); const q = $('#findQ').value.trim(); R.findQ = q; if (!q) return;
    let V = []; try { V = (await data()).variants; } catch (e) {}
    const { terms, group } = expand(q, V);
    const hits = [];
    for (const pgx of R.pages) {
      const ps = paras(pgx.text);
      ps.forEach((t, k) => { if (terms.some(x => norm(plainT(t)).includes(x))) hits.push({ n: pgx.n, k, s: snippet(plainT(t), terms) || plainT(t).slice(0, 80) }); });
    }
    const ch = n => { const c = chapters()[chapterOf(n)]; return c && c.title ? c.title : ''; };
    R.findTerms = terms;
    // 쪽 번호로 찾기: '74', '74쪽', 'p.74', '74페이지' → 그 쪽으로 가는 줄을 맨 위에 (운영자 요청, 2026-11-10)
    const pm = q.replace(/\s+/g, '').match(/^(?:p\.?|pp\.?)?(\d{1,4})(?:쪽|페이지|면|p)?$/i);
    let pgHits = pm ? R.pages.filter(x => String(x.label || '').replace(/쪽$/, '') === pm[1]) : [];
    // 그 쪽 번호의 쪽이 따로 없으면(앞 쪽 문단이 그 쪽까지 이어져 있음) 그 번호를 품은 앞 쪽으로 (운영자 요청, 2026-11-15)
    let pgVia = '';
    if (pm && !pgHits.length) {
      const num = x => { const m = String(x.label || '').match(/^(\d+)쪽?$/); return m ? +m[1] : null; }, N = +pm[1];
      const nums = R.pages.filter(x => num(x) != null);
      const i = nums.findIndex((x, k) => num(x) < N && nums[k + 1] && num(nums[k + 1]) > N);
      if (i >= 0) { pgHits = [nums[i]]; pgVia = `${N}쪽 (${pageName(nums[i])}에 이어짐)`; }
    }
    // 각주 번호로 찾기: '각주 13', '13번 각주', '[13]', '주13' 또는 숫자만 — 본문 자리와 각주 글을 맨 위에 (운영자 요청, 2026-11-11)
    const fm = q.replace(/\s+/g, '').match(/^(?:각주|주|\[\^?|\^)?(\d{1,4})(?:\]|번|번각주|각주)?$/);
    const fnHits = [];
    if (fm) for (const pgx of R.pages) paras(pgx.text).forEach((t, k) => {
      if (t.startsWith('[^' + fm[1] + ']:')) fnHits.push({ n: pgx.n, k, def: true, s: plainT(t).trim().slice(0, 90) });
      else if (t.includes('[^' + fm[1] + ']') && !/^\[\^/.test(t)) { const i = t.indexOf('[^' + fm[1] + ']'), a = plainT(t.slice(Math.max(0, i - 60), i)).trim(); fnHits.push({ n: pgx.n, k, def: false, s: (i > 60 ? '…' : '') + a.slice(-45) }); }
    });
    const fnHtml = fnHits.map(x => `<li><button class="link" data-find="${x.n}" data-k="${x.k}"><span class="muted small">${esc(pageName(R.pages[x.n - 1]))}${ch(x.n) ? ' · ' + esc(ch(x.n)) : ''}</span><br><b>${x.def ? '📝 각주 ' + fm[1] + ' 내용' : '📝 각주 ' + fm[1] + ' 본문 자리'}</b> ${phMark(esc(x.s))}${x.def ? '' : '<sup>' + fm[1] + '</sup>'}</button></li>`).join('');
    const pgHtml = pgHits.map(x => `<li><button class="link" data-find="${x.n}" data-k="-1"><b>📄 ${esc(pgVia || pageName(x))}으로 가기</b>${ch(x.n) ? `<br><span class="muted small">${esc(ch(x.n))}</span>` : ''}</button></li>`).join('');
    R.findRes = `<p class="note">${pgHits.length ? `${esc(pgVia || pageName(pgHits[0]))}이 있습니다. ` : ''}${fnHits.length ? `각주 ${fm[1]}번이 있습니다. ` : ''}${hits.length ? `${hits.length}곳을 찾았습니다.` : pgHits.length || fnHits.length ? '' : '찾는 말이 없습니다.'}${group ? ` (${group.map(esc).join(', ')} 함께 찾음)` : ''}</p>
      <ul class="find-list">${pgHtml}${fnHtml}${hits.slice(0, 200).map(h => `<li><button class="link" data-find="${h.n}" data-k="${h.k}"><span class="muted small">${esc(pageName(R.pages[h.n - 1]))}${ch(h.n) ? ' · ' + esc(ch(h.n)) : ''}</span><br>${phMark(hl(h.s, terms))}</button></li>`).join('')}</ul>${hits.length > 200 ? '<p class="note">앞의 200곳만 보입니다. 더 자세한 말로 찾아보세요.</p>' : ''}`;
    $('#findRes').innerHTML = R.findRes; bindFind();
  };
  const bindFind = () => $$('[data-find]', el).forEach(b => b.onclick = () => {
    const n = +b.dataset.find, k = +b.dataset.k; R.hl = k < 0 ? [] : (R.findTerms || []);
    R.i = n - 1; stopSpeak(false); renderReader(); if (k >= 0) $('#p-find').classList.add('open');  // 쪽으로 가기는 찾기 창을 닫고 그 쪽 첫머리로
    const t = k < 0 ? $('#pm-' + n) : $(`[data-pg="${n}"][data-s="${k}"]`); if (t) { t.scrollIntoView({ block: k < 0 ? 'start' : 'center' }); t.classList.add('found'); setTimeout(() => t.classList.remove('found'), 1800); }
  });
  bindFind();
  $$('[data-zoom-img]', el).forEach(b => b.onclick = () => zoomView(`<img src="${esc(b.dataset.zoomImg)}" alt="${esc(b.dataset.cap)}">`, b.dataset.cap || '그림'));
  $$('[data-zoom-tbl]', el).forEach(b => b.onclick = () => zoomView(b.parentElement.querySelector('table').outerHTML, '표'));
  bindIx();
  const ho = $('#hlOff'); if (ho) ho.onclick = () => { R.hl = []; history.replaceState(null, '', location.pathname); renderReader(); };
  
  // 휴대폰: 전자책 앱처럼 글을 읽거나 손가락으로 밀어 올리면 위 메뉴·아래 바를 숨기고, 화면을 한 번 누르면 다시 보임 (운영자 요청, 2026-11-09)
  if (!el._tapBound) {
    el._tapBound = true;
    const tapOk = t => t.closest('#rBody') && !t.closest('a,button,input,select,textarea,label,sup,u,img,summary,[role=button],[data-go],[data-find],[data-zoom-img],[data-zoom-tbl],.ix-bar');
    // 손가락으로 누른 직후(0.8초)는 휴대폰 방식으로 — 화면이 넓거나 기기가 마우스가 있다고 알려도 (운영자 요청, 2026-11-14: 가로 양쪽 보기에서 눌러도 메뉴가 안 뜨던 것)
    let lastTouch = 0; const touchNow = () => Date.now() - lastTouch < 800;
    el.addEventListener('touchstart', () => { lastTouch = Date.now(); }, { passive: true, capture: true });
    el.addEventListener('click', e => {
      if (!(immersive() || touchNow()) || !tapOk(e.target)) return;
      if (String(window.getSelection() || '').trim() || ($('#selPop') && $('#selPop').classList.contains('show'))) return;
      if (el.classList.toggle('chrome-off')) $$('.panel', el).forEach(x => x.classList.remove('open'));
    });
    let ty = null;
    el.addEventListener('touchstart', e => { ty = e.target.closest('#rBody') ? e.touches[0].clientY : null; }, { passive: true });
    el.addEventListener('touchmove', e => { if (ty == null || !(immersive() || touchNow())) return; if (Math.abs(e.touches[0].clientY - ty) > 12 && !$('.panel.open', el)) { el.classList.add('chrome-off'); ty = null; } }, { passive: true });
    // 컴퓨터(마우스): 화면 맨 위·맨 아래로 마우스를 가져가면 메뉴·바가 보이고, 글 쪽으로 오면 다시 숨음 (운영자 요청, 2026-11-10)
    const hoverPC = () => matchMedia('(hover:hover) and (pointer:fine)').matches && !immersive();
    el.addEventListener('mousemove', e => {
      if (!hoverPC() || touchNow()) return;  // 손가락으로 누를 때 브라우저가 따라 보내는 가짜 마우스 움직임은 무시
      // 맨 위·맨 아래 가장자리(좁게)에서만 나타남, 글 속 단추(장 끝의 ← 앞 장 / 다음 장 → 등) 위에서는 나타나지 않음 — 단추를 가리지 않게 (운영자 요청, 2026-11-10)
      const onBodyBtn = e.target.closest && e.target.closest('#rBody button, #rBody a, #rBody input');
      const nearTop = e.clientY < 40, nearBot = e.clientY > innerHeight - 28 && !onBodyBtn;
      const onChrome = e.target.closest && e.target.closest('.r-top,.r-bottom,.panel,#selPop');
      if (nearTop || nearBot || onChrome) el.classList.remove('chrome-off');
      else if (!$('.panel.open', el)) el.classList.add('chrome-off');
    });
    el.addEventListener('mouseleave', () => { if (hoverPC() && !touchNow() && !$('.panel.open', el)) el.classList.add('chrome-off'); });
    el.addEventListener('focusin', e => { if (e.target.closest('.r-top,.r-bottom')) el.classList.remove('chrome-off'); });  // 키보드(Tab)로 단추에 가면 보임
    if (hoverPC() && !store.get('hover-hint')) { store.set('hover-hint', 1); setTimeout(() => toast('마우스를 화면 맨 위나 맨 아래로 가져가면 메뉴가 나옵니다'), 1200); }
    if (immersive() && !store.get('tap-hint')) { store.set('tap-hint', 1); setTimeout(() => toast('글을 넘기면 메뉴가 숨고, 화면을 한 번 누르면 다시 나옵니다'), 1200); }
  }
  // 휴대폰: 위아래로 넘길 때 오른쪽에 스크롤 막대(지금 위치)를 잠깐 보여 줌 — 손가락으로 끌어 빨리 넘길 수도 있음 (운영자 요청, 2026-11-10)
  if (matchMedia('(pointer:coarse)').matches) {
    const body = $('#rBody'); const sb = document.createElement('div'); sb.className = 'r-sbar'; sb.innerHTML = '<i></i>'; sb.setAttribute('aria-hidden', 'true'); el.appendChild(sb);
    const th = sb.firstChild; let hideT = null;
    const draw = () => { const H = body.scrollHeight, h = body.clientHeight; if (H <= h + 4) { sb.style.display = 'none'; return; } sb.style.display = ''; const tr = sb.clientHeight, tl = Math.max(36, tr * h / H); th.style.height = tl + 'px'; th.style.transform = `translateY(${(tr - tl) * body.scrollTop / (H - h)}px)`; };
    const show = () => { draw(); sb.classList.add('on'); clearTimeout(hideT); hideT = setTimeout(() => sb.classList.remove('on'), 1200); };
    body.addEventListener('scroll', show, { passive: true });
    let drag = null;
    sb.addEventListener('touchstart', e => { const r = sb.getBoundingClientRect(); drag = { y: e.touches[0].clientY, top: body.scrollTop }; e.preventDefault(); show(); }, { passive: false });
    sb.addEventListener('touchmove', e => { if (!drag) return; e.preventDefault(); const tr = sb.clientHeight, H = body.scrollHeight, h = body.clientHeight, tl = Math.max(36, tr * h / H); body.scrollTop = drag.top + (e.touches[0].clientY - drag.y) * (H - h) / Math.max(1, tr - tl); }, { passive: false });
    sb.addEventListener('touchend', () => { drag = null; });
  }
  // 설정·목록 창: 위 단추 줄 바로 아래에 열리게 하고(단추를 가리지 않게), 창마다 ✕ 닫기 단추
  placePanels(el);
  $$('.panel', el).forEach(p => { if (p.querySelector(':scope > .p-close')) return; const x = document.createElement('button'); x.className = 'p-close'; x.type = 'button'; x.setAttribute('aria-label', '닫기'); x.textContent = '✕'; x.onclick = () => p.classList.remove('open'); p.prepend(x); });
  $$('[data-panel]', el).forEach(b => b.onclick = () => openPanel(b.dataset.panel, true));  // 열면 그 창으로 커서를 옮김 (화면 낭독기, 2026-11-17)
  $('#rKeys').onclick = () => openPanel('keys');
  loadReadFont(R.font); loadFontLabels();
  panelA11y(el);
  $$('[data-go]', el).forEach(b => b.onclick = () => go(+b.dataset.go, b.dataset.ci != null ? +b.dataset.ci : null));
  // 목차 창의 그림·표 줄: 그 쪽으로 가서 그림·표에 커서 (2026-11-19)
  $$('[data-fgo]', el).forEach(b => b.onclick = () => { const pg = +b.dataset.fgo, k = +b.dataset.fk; go(pg); const land = () => { const t = $(`#rBody [data-pg="${pg}"][data-s="${k}"]`); if (!t) return; t.scrollIntoView({ block: 'start' }); const nav = $('.r-top'); if (nav && !$('#reader').classList.contains('chrome-off')) $('#rBody').scrollTop -= nav.offsetHeight + 8; t.classList.add('found'); setTimeout(() => t.classList.remove('found'), 1600); const f = $('button, a', t) || t; if (!f.matches('button,a')) f.tabIndex = -1; try { f.focus({ preventScroll: true }); } catch (e) {} }; setTimeout(land, 80); setTimeout(() => { if (!$('#rBody') || !$('#rBody').contains(document.activeElement)) land(); }, 450); });  // 쪽을 그린 뒤 한 번 더(장 바꾸기·자리 맞추기로 다시 그려 커서가 사라지면)
  { const fo = $('#figOnly', el), ul = $('#p-toc ul', el); if (fo && ul) { fo.checked = !!R.figOnly; ul.classList.toggle('figs-only', fo.checked); fo.onchange = () => { R.figOnly = fo.checked; ul.classList.toggle('figs-only', fo.checked); }; } }
  $$('[data-zoom]', el).forEach(b => b.onclick = () => { R.zoom = Math.max(.75, Math.min(2.5, +(R.zoom + (+b.dataset.zoom) * .25).toFixed(2))); store.set('rzoom', R.zoom); renderReader(); reopen('p-font'); });
  $$('[data-fs]', el).forEach(b => b.onclick = () => { R.fs = +b.dataset.fs; store.set('rfs', R.fs); renderReader(); reopen('p-font'); });
  const FS = [0.85, 1, 1.15, 1.3, 1.5, 1.75, 2, 2.25, 2.5, 3, 3.5, 4];
  $$('[data-fsd]', el).forEach(b => b.onclick = () => { const up = +b.dataset.fsd > 0; const v = up ? FS.find(x => x > R.fs + 0.001) : [...FS].reverse().find(x => x < R.fs - 0.001); if (v) { R.fs = v; store.set('rfs', R.fs); renderReader(); reopen('p-font'); } });
  $$('[data-bold]', el).forEach(b => b.onclick = () => { R.bold = b.dataset.bold === '1'; store.set('rbold', R.bold); renderReader(); reopen('p-font'); });
  $$('[data-lh]', el).forEach(b => b.onclick = () => { R.lh = +b.dataset.lh; store.set('rlh', R.lh); renderReader(); reopen('p-font'); });
  $$('[data-font]', el).forEach(b => b.onclick = () => { R.font = b.dataset.font; loadReadFont(R.font); store.set('rfont', R.font); renderReader(); reopen('p-font'); });
  $$('[data-mw]', el).forEach(b => b.onclick = () => { R.mw = +b.dataset.mw; store.set('rmw', R.mw); renderReader(); reopen('p-font'); });
  $$('[data-parm]', el).forEach(b => b.onclick = async () => {
    const m = b.dataset.parm;
    if (m !== 'off' && !R.parD) { try { toast('원서를 불러오는 중입니다…'); R.parD = await (await fetch('/parallel/' + R.id + '.' + R.par[0] + '.json')).json(); } catch (e) { toast('원서를 불러오지 못했습니다'); return; } }
    R.parMode = m; store.set('par-' + R.id, m); renderReader();
  });
  const spB = $('#rSpread', el); if (spB) spB.onclick = async () => { if (R.spread && !spreadWide()) { spreadRotate(); return; }  // 세로 화면에서 이미 켜져 있으면 가로로만 돌림
    R.spread = !R.spread; store.set('rspread2-' + R.id, R.spread);
    // 휴대폰 세로 화면에서 켜면 저절로 가로로 (전체 화면 + 화면 방향 고정 — 안드로이드 크롬 등에서만 됨, 아이폰은 직접 돌려야 함) (운영자 요청, 2026-11-14)
    if (R.spread && !spreadWide() && screen.orientation && screen.orientation.lock) { try { if (!document.fullscreenElement) { await document.documentElement.requestFullscreen(); R.spreadFs = true; } await screen.orientation.lock('landscape'); R.spreadLock = true; } catch (e) {} }
    if (!R.spread && R.spreadLock) { try { screen.orientation.unlock(); } catch (e) {} R.spreadLock = false; if (R.spreadFs && document.fullscreenElement) { try { await document.exitFullscreen(); } catch (e) {} } R.spreadFs = false; } const pn = R.i + 1; renderReader(); const m = $('#pm-' + pn); if (m) m.scrollIntoView(); if (immersive() && $('#reader')) $('#reader').classList.add('chrome-off'); setTimeout(() => R && toast(R.spread && !spreadWide() ? '휴대폰을 가로로 돌려 주세요 — 가로 화면에서 양쪽으로 보입니다' : R.spread ? (R.spreadPali ? '양쪽으로 봅니다 (왼쪽 빠알리 · 오른쪽 번역)' : '양쪽으로 봅니다 (짝수 쪽 왼쪽 · 홀수 쪽 오른쪽)') : '한쪽씩 봅니다'), 700); };
  $$('[data-spread]', el).forEach(b => b.onclick = () => { R.spread = b.dataset.spread === '1'; store.set('rspread2-' + R.id, R.spread); renderReader(); reopen('p-font'); });
  $$('[data-rmode]', el).forEach(b => b.onclick = () => { applyMode(b.dataset.rmode); renderReader(); reopen('p-mode'); });
  const cur = () => R.pages[R.i];
  $('#rMark').onclick = () => { const l = bms(), n = cur().n, k = l.findIndex(m => m.id === R.id && m.p === n); if (k > -1) { l.splice(k, 1); toast('책갈피를 지웠습니다'); } else { l.push({ id: R.id, t: R.title, p: n, pl: cur().label, note: '', d: today() }); toast(`${pageName(cur())}에 책갈피를 달았습니다`); } store.set('bm', l); renderReader(); };
  $('#bmSave').onclick = () => { const l = bms(), n = cur().n; let m = l.find(m => m.id === R.id && m.p === n); if (!m) { m = { id: R.id, t: R.title, p: n, pl: cur().label, d: today() }; l.push(m); } m.note = $('#bmNote').value.trim(); store.set('bm', l); renderReader(); reopen('p-bm'); toast('메모를 저장했습니다'); };
  $$('[data-bmdel]', el).forEach(b => b.onclick = () => { const l = bms(); l.splice(+b.dataset.bmdel, 1); store.set('bm', l); renderReader(); reopen('p-bm'); });
  // 전체 화면으로 보기 (컴퓨터, 운영자 요청 2026-11-10) — 다시 누르거나 Esc 로 나감
  const fb = $('#rFull'); if (fb) fb.onclick = () => { try { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); } catch (e) { toast('이 브라우저에서는 전체 화면을 쓸 수 없습니다'); } };
  const ab = $('#rAb'); if (ab) ab.onclick = () => { if (AB.locked) return abLockedMsg(); AB.on && !abA().paused ? abA().pause() : abStart(); };
  const sp = $('#rSpeak'); if (sp) sp.onclick = () => { if (R.ttsLocked) return toast('잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요'); R.speaking ? stopSpeak(true) : speak(); };
  const lk = $('#rLock'); if (lk) lk.onclick = () => { R.ttsLocked = !R.ttsLocked; renderReader(); toast(R.ttsLocked ? '잠갔습니다. 실수로 멈추거나 닫히지 않습니다' : '잠금을 풀었습니다'); };
  $$('[data-tts]', el).forEach(inp => {
    const save = () => {
      const o = store.get('tts', {}), k = inp.dataset.tts;
      o[k] = inp.type === 'checkbox' ? inp.checked : (inp.type === 'range' || k === 'pause' || k === 'sleep') ? +inp.value : inp.value;
      store.set('tts', o);
      if (['rate', 'pitch', 'enRate'].includes(k)) inp.setAttribute('aria-valuetext', k === 'rate' ? (+inp.value).toFixed(1) + '배' : k === 'enRate' ? Math.round(+inp.value * 100) + '%' : (+inp.value).toFixed(1));  // 화면 낭독기가 '1.2배'처럼 읽게
      if (k === 'rate') $('#ttsRateV').textContent = (+inp.value).toFixed(1) + '배';
      if (k === 'pitch') $('#ttsPitchV').textContent = (+inp.value).toFixed(1);
      if (k === 'enRate') $('#ttsEnRateV').textContent = Math.round(+inp.value * 100) + '%';
      if (k === 'sleep' && R.speaking) R.ttsStart = Date.now();
    };
    inp.addEventListener(inp.type === 'range' ? 'input' : 'change', save);
  });
  const tt = $('#ttsTry'); if (tt) tt.onclick = () => {
    if (!('speechSynthesis' in window)) return noVoice();
    if (!LEX.pali) { loadLex().then(() => tt.onclick()); return; }
    const o = ttsOpt(); const pv = pickVoice(o), v = pv.voice;
    speechSynthesis.cancel(); speakSegs(sayable('법보시는 모든 보시를 능가한다. Sabbadānaṃ dhammadānaṃ jināti. (법구경 354게송) Dhamma is the best gift.', o, true), o, pv, () => {}, () => {});
  };
  const ta = $('#ttsApply'); if (ta) ta.onclick = () => {
    $('#p-tts').classList.remove('open');
    // 듣는 중이면 지금 문단부터 새 설정으로 다시 읽기
    if (R.speaking && R.ttsPos && R.ttsPos.i === R.i) { speak(R.ttsPos.k); toast('설정을 적용했습니다. 지금 문단부터 새 설정으로 읽습니다'); }
    else toast('설정을 적용했습니다');
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
    const head = !para && node && node.closest('.ch-head');   // 장 제목을 골라도 창을 띄움 — 듣기만 (운영자 요청, 2026-11-12)
    if (!(para && body.contains(para)) && !(head && body.contains(head))) { pop.classList.remove('show'); return; }
    pop.classList.toggle('on-head', !!head);
    const z = bodyZoom(), r = s.getRangeAt(0).getBoundingClientRect(), pw = (pop.offsetWidth || 240) * z, ph = 46 * z;
    pop.style.left = Math.max(8, Math.min(window.innerWidth - pw - 8, r.left + r.width / 2 - pw / 2)) / z + 'px';
    // 휴대폰은 위쪽에 기기 자체의 복사 메뉴가 뜨므로 아래쪽에 둠
    let top = touch ? r.bottom + 14 : r.top - ph - 4;
    if (top < 8) top = r.bottom + 14;
    if (top > window.innerHeight - ph - 70) top = Math.max(8, r.top - ph - 50);
    pop.style.top = top / z + 'px';
    pop.classList.add('show'); pop._sel = { text: s.toString().replace(/\s+/g, ' ').trim(), p: para ? +para.dataset.pg : (chapters()[chapterOf(R.i + 1)] || {}).from || R.i + 1 };
  };
  let selT; window._ddOnSel = () => { clearTimeout(selT); selT = setTimeout(onSel, touch ? 350 : 30); };
  if (!window._ddSelBound) { document.addEventListener('selectionchange', () => window._ddOnSel && window._ddOnSel()); window._ddSelBound = true; }
  body.addEventListener('mouseup', window._ddOnSel); body.addEventListener('keyup', window._ddOnSel);
  // 단추를 누를 때 고른 글이 풀리지 않도록
  $$('#selPop button').forEach(b => { b.addEventListener('pointerdown', e => e.preventDefault()); b.addEventListener('mousedown', e => e.preventDefault()); });
  const plabel = n => (R.pages[n - 1] || {}).label || '';
  const addUl = withNote => {
    const pop = $('#selPop'), d = pop._sel; if (!d) return; const l = uls(); const k = Date.now();
    l.push({ k, id: R.id, t: R.title, by: R.by, p: d.p, pl: plabel(d.p), text: d.text, note: '', d: today(), ...(R.noCopy ? { nc: 1 } : {}) }); store.set('ul', l);
    window.getSelection().removeAllRanges(); pop.classList.remove('show'); renderReader();
    if (withNote) openUl(k); else toast('밑줄을 그었습니다. ‘밑줄 모음’과 내 서재에서 모아 볼 수 있습니다');
  };
  $('#selUl').onclick = () => addUl(false); $('#selNote').onclick = () => addUl(true);
  const sp2 = $('#selPlay'); if (sp2) sp2.onclick = () => {
    const sel = window.getSelection(); const pop = $('#selPop'); pop.classList.remove('show');
    if (!sel || !sel.rangeCount) return;
    const rg = sel.getRangeAt(0); const node = rg.startContainer.nodeType === 1 ? rg.startContainer : rg.startContainer.parentElement;
    // 장 제목(.ch-head)을 고르면 그 장 처음부터 — 장 제목부터 읽음 (운영자 요청, 2026-11-12: 장 제목을 골라 '여기부터 듣기'를 누르면 아무 소리가 없던 것)
    if (node && node.closest('.ch-head')) { sel.removeAllRanges(); const c = chapters()[chapterOf(R.i + 1)]; stopSpeak(false); if (c) R.i = c.from - 1; speak(); return; }
    const para = node && node.closest('[data-pg]'); if (!para) return;
    const pre = document.createRange(); pre.setStart(para, 0); pre.setEnd(rg.startContainer, rg.startOffset);
    const pg = +para.dataset.pg, k = +para.dataset.s; sel.removeAllRanges();
    // 화면 글자 위치 → 원래 글(각주 표시 [^1] 등 포함) 위치로 바꿔서, 각주 번호가 '1'이 아니라 '각주 1'로 읽히게
    const src = (paras((R.pages[pg - 1] || {}).text)[k]) || para.textContent;
    const rest = src.slice(domToSrc(src, pre.toString().length));
    stopSpeak(false); R.i = pg - 1; speak(k, rest);
  };
  // 고른 곳부터 오디오북 (운영자 요청, 2026-11-10): 그 문단의 소리 시작점에서, 문단 중간이면 글자 위치만큼 앞으로
  const sa = $('#selAb'); if (sa) sa.onclick = () => {
    const sel = window.getSelection(); $('#selPop').classList.remove('show');
    if (!sel || !sel.rangeCount) return;
    const rg = sel.getRangeAt(0); const node = rg.startContainer.nodeType === 1 ? rg.startContainer : rg.startContainer.parentElement;
    if (node && node.closest('.ch-head')) { sel.removeAllRanges(); const c = chapters()[chapterOf(R.i + 1)]; if (c) abStartAt(c.from, 0, 0); return; }   // 장 제목을 고르면 그 장 처음부터 (2026-11-12)
    const para = node && node.closest('[data-pg]'); if (!para) return;
    const pre = document.createRange(); pre.setStart(para, 0); pre.setEnd(rg.startContainer, rg.startOffset);
    const frac = para.textContent.length ? pre.toString().length / para.textContent.length : 0;
    sel.removeAllRanges(); abStartAt(+para.dataset.pg, +para.dataset.s, frac);
  };
  if ($('#selCopy')) $('#selCopy').onclick = () => { const d = $('#selPop')._sel; if (d) copy(`“${d.text}” — ${R.by}, 『${R.title}』 ${plabel(d.p) || d.p}쪽 (${SITE})`, '고른 글을 출처와 함께 복사했습니다'); $('#selPop').classList.remove('show'); };
  $('#selShare').onclick = () => { const d = $('#selPop')._sel; $('#selPop').classList.remove('show'); if (d) openShare(d, plabel(d.p)); };
  $$('u.ul', el).forEach(u => u.onclick = e => { e.stopPropagation(); openUl(+u.dataset.hid); });
}
// 카카오톡 공유 (카카오 JavaScript SDK, 설정의 kakao_js_key)
let kakaoP = null;
function kakaoReady() {
  if (kakaoP) return kakaoP;
  kakaoP = new Promise(res => {
    if (window.Kakao) { try { if (!Kakao.isInitialized()) Kakao.init(R.kakao); } catch (e) {} return res(); }
    const sc = document.createElement('script');
    sc.src = 'https://t1.kakaocdn.net/kakao_js_sdk/2.8.4/kakao.min.js';
    sc.integrity = 'sha384-BGX7Wb16GmRFagri4bLJV2DgipVZaU2AI812GZtHtHzzDQJnfHasDXN5houxv45w'; sc.crossOrigin = 'anonymous';
    sc.onload = () => { try { Kakao.init(R.kakao); } catch (e) {} res(); }; sc.onerror = () => res();
    document.head.appendChild(sc);
  });
  return kakaoP;
}
// 고른 글을 SNS로 공유: 글 + 출처(저자, 『책』 쪽) + 그 쪽으로 오는 주소
function openShare(d, pl) {
  const el = $('#reader'); $$('.panel', el).forEach(x => x.classList.remove('open'));
  const url = `https://${SITE}/read/${R.id}/${d.p}?view=text`;
  const src = `— ${R.by}, 『${R.title}』${pl ? ' ' + pl + '쪽' : ''}`;
  const q = t => `“${t}”\n\n${src}`;
  const full = `${q(d.text)}\n${url}`;
  const short = n => d.text.length > n ? d.text.slice(0, n - 1) + '…' : d.text;
  $('#shText').textContent = full;
  if (R.kakao) kakaoReady();  // 카카오 공유 프로그램을 미리 불러 둠 (단추를 누르는 즉시 창이 뜨도록)
  $('#p-share').classList.add('open');
  $$('#p-share [data-sh]').forEach(b => b.onclick = async () => {
    const k = b.dataset.sh, open = u => window.open(u, '_blank', 'noopener,width=620,height=640');
    if (k === 'app') { try { await navigator.share({ text: q(d.text), url }); } catch (e) {} return; }
    // 휴대폰: 기기 공유 화면 → 카카오톡을 고르면 고른 글 전체가 일반 메시지로 감 (글자 수 제한 없음)
    if (k === 'kakao' && navigator.share && matchMedia('(pointer: coarse)').matches) { try { await navigator.share({ text: q(d.text), url }); } catch (e) {} return; }
    if (k === 'kakao' && window.Kakao && Kakao.isInitialized && Kakao.isInitialized()) {
      // 텍스트형 메시지: 고른 글이 카톡 말풍선에 글로 그대로 보임 (카카오 제한 200자)
      const tail = `\n\n${src}`, room = 200 - tail.length - 2;
      const body = d.text.length > room ? d.text.slice(0, room - 1) + '…' : d.text;
      try {
        Kakao.Share.sendDefault({ objectType: 'text', text: `“${body}”${tail}`, link: { mobileWebUrl: url, webUrl: url }, buttonTitle: '이 쪽 읽으러 가기' });
        if (d.text.length > room) toast('카카오톡은 200자까지만 보낼 수 있어 앞부분만 보냈습니다. 전체는 ‘복사’로 붙여넣어 주세요');
        return;
      } catch (e) {}
    }
    if (k === 'kakao') { copy(full, '복사했습니다. 카카오톡 대화창에 붙여넣기(Ctrl+V) 하세요'); return; }
    if (k === 'band') return open(`https://band.us/plugin/share?body=${encodeURIComponent(full)}&route=${encodeURIComponent(SITE)}`);
    if (k === 'x') return open(`https://x.com/intent/post?text=${encodeURIComponent(q(short(180)))}&url=${encodeURIComponent(url)}`);
    if (k === 'fb') { copy(q(d.text), '글과 출처를 복사했습니다. 페이스북 글쓰기 칸에 붙여넣기 하세요'); return open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`); }
    if (k === 'mail') { location.href = `mailto:?subject=${encodeURIComponent(`『${R.title}』에서`)}&body=${encodeURIComponent(full)}`; return; }
    if (k === 'copy') copy(full, '고른 글을 출처·주소와 함께 복사했습니다');
  });
}
function domToSrc(src, off) {
  // 화면에는 '## ' 가 없고, [^12]: 는 '12', [^12] 는 '12' 로 보입니다
  let i = 0, d = 0;
  if (src.startsWith('## ') || src.startsWith('^^ ') || src.startsWith(':: ') || src.startsWith('>> ') || src.startsWith('|| ') || src.startsWith('++ ')) i = 3;
  const m0 = src.slice(i).match(/^\[\^([^\]]+)\]:\s*/); if (m0) { if (off < m0[1].length) return i; d += m0[1].length; i += m0[0].length; }
  while (i < src.length && d < off) {
    const m = src.slice(i).match(/^\[\^([^\]]+)\]/);
    if (m) { if (d + m[1].length > off) return i; d += m[1].length; i += m[0].length; continue; }
    if (src[i] === '\n') { i++; continue; }  // 줄 바꿈은 화면 글자에 없음
    if (src.startsWith('**', i) || src.startsWith('==', i)) { i += 2; continue; }  // 굵은 글씨 표시도 화면 글자에 없음
    i++; d++;
  }
  return i;
}
function openUl(k) {
  const h = uls().find(x => x.k === k); if (!h) return; const el = $('#reader');
  $$('.panel', el).forEach(x => x.classList.remove('open'));
  $('#p-uledit').classList.add('open'); $('#ulText').textContent = h.text; $('#ulNote').value = h.note || ''; $('#ulNote').focus();
  $('#ulSave').onclick = () => { const l = uls(); const x = l.find(x => x.k === k); x.note = $('#ulNote').value.trim(); store.set('ul', l); renderReader(); toast('메모를 저장했습니다'); };
  $('#ulDel').onclick = () => { store.set('ul', uls().filter(x => x.k !== k)); renderReader(); toast('밑줄을 지웠습니다'); };
  if ($('#ulCopy')) $('#ulCopy').onclick = () => copy(`“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽 (${SITE})`, '출처와 함께 복사했습니다');
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
const LATIN = "A-Za-zÀ-ÖØ-öø-žḀ-ỿ";
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
  if (!p && !e) return looksPali(w) ? 'P' : notPali(w) ? 'E' : '?';
  return 'B';
}
// 빨리어에는 없는 글자·소리 짜임이 있으면 영어로 봄 (English, Korean, Index …): f q w x z, sh, ck, 모음 두 개 잇달아, ṃ 이외의 자음으로 끝남
// 미얀마 존칭·호칭: 영어 목소리로 읽으면 어색하므로 한국어 소리로
const BUR = { sayadaw: '사야도', sayādaw: '사야도', u: '우', ashin: '아신', daw: '도', bhante: '반떼', sayalay: '사얄레이' };
const notPali = w => /^[A-Za-z]+$/.test(w) && w.length >= 2 && (/[fqwxz]|sh|ck|[aeiou]{2}/i.test(w) || /[bcdfghjklmnpqrstvwxyz]$/i.test(w));
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
function enVoice() {
  const vs = ('speechSynthesis' in window ? speechSynthesis.getVoices() : []).filter(v => /^en/i.test(v.lang));
  const score = v => (/^en[-_]US/i.test(v.lang) ? 4 : /^en[-_]GB/i.test(v.lang) ? 3 : 1) + (/natural|neural|online|google|samantha|aria|jenny|guy/i.test(v.name) ? 2 : 0) + (v.localService ? 0.5 : 0);
  return vs.sort((a, b) => score(b) - score(a))[0] || null;
}
// 한 문단을 한국어·영어 구간으로 나눠 차례로 읽음 (영어는 영어 목소리)
// 듣는 중 ← → 로 앞·다음 문장 (운영자 요청, 2026-11-18 — 시각장애인 이용자): 문단을 문장으로 나눠 한 문장씩 읽고, 건너뛰면 그 문장부터 다시
const TT = { gen: 0, jump: null };
function splitSents(t) {
  const raw = String(t).split(/(?<=[.?!。…][”’"')\]」』]*)\s+(?=\S)/u), out = [];
  raw.forEach(x => { if (out.length && (out[out.length - 1].replace(/[\u0001\u0002\s]/g, '').length < 6)) out[out.length - 1] += ' ' + x; else out.push(x); });  // '1.' 같은 짧은 조각은 다음 문장과 함께
  return out.filter(x => x.replace(/[\u0001\u0002\s]/g, ''));
}
// 문단 사이 쉼: 쉼 동안 → ← 를 누르면 기다리던 일(TT.ntf)을 곧바로 하거나 미룸
function ttsLater(fn, ms) { clearTimeout(TT.nt); TT.ntf = fn; TT.nt = setTimeout(() => { TT.nt = 0; TT.ntf = null; fn(); }, ms); }
// 문장마다 이어 읽기 — ctl.jump(±1) 로 앞·다음 문장, 문단 밖으로 나가면 onOut(±1)
function speakSents(text, o, pv, si, onend, onerror, onOut, el, whole) {
  const ss = whole ? [text] : splitSents(text);  // 장 제목은 나누지 않음 if (!ss.length) { onend(); return; }
  let i = si === 'last' ? ss.length - 1 : Math.max(0, Math.min(ss.length - 1, si || 0));
  // 문단을 다 읽고 다음 문단으로 넘어가기 전 쉼 동안에도 → ← 가 듣게 (운영자 요청, 2026-11-18 '방향키가 동작하지 않는 부분'):
  // → 는 쉼을 건너뛰어 바로 다음 문단, ← 는 이 문단의 마지막 문장을 다시 읽고 이어 감
  let after = null;
  const endJump = () => { TT.jump = d => { const f = after || TT.ntf; clearTimeout(TT.nt); TT.nt = 0; TT.ntf = null;
    if (d > 0) { after = null; TT.gen++; if (f) f(); return; }
    try { speechSynthesis.cancel(); } catch (e) {} after = f; i = ss.length - 1; if (el) ttsFocus(el); run(); }; };
  const run = () => {
    const g = ++TT.gen;
    TT.jump = d => { const j = i + d; try { speechSynthesis.cancel(); } catch (e) {} TT.gen++;
      if (j >= ss.length && after) { const f = after; after = null; f(); return; }  // 다시 읽던 마지막 문장에서 → 면 원래 이어 가던 곳으로
      if (j < 0 || j >= ss.length) { after = null; onOut(d); return; } i = j; if (el) ttsFocus(el); run(); };
    speakSegs(ss[i], o, pv, () => { if (g !== TT.gen) return; if (++i >= ss.length) { endJump(); if (after) { const f = after; after = null; f(); } else onend(); } else run(); }, e => { if (g !== TT.gen) return; onerror(e); });
  };
  run();
}
function speakSegs(text, o, pv, onend, onerror) {
  const ev = o.enVoice !== false ? enVoice() : null;
  let segs = [];
  if (ev) text.split(/(\u0001[^\u0002]*\u0002)/).forEach(x => { if (!x) return; const isEn = x[0] === EN_A; const t = x.replace(/[\u0001\u0002]/g, '').trim(); if (t && /[\p{L}\p{N}]/u.test(t)) segs.push({ t, en: isEn }); });
  else segs = [{ t: text.replace(/[\u0001\u0002]/g, ''), en: false }];
  if (!segs.length) { onend(); return; }
  segs.forEach((g, i) => {
    const u = new SpeechSynthesisUtterance(g.t);
    if (g.en) { u.voice = ev; u.lang = ev.lang; u.pitch = +o.pitch; } else { u.lang = pv.voice ? pv.voice.lang : 'ko-KR'; if (pv.voice) u.voice = pv.voice; u.pitch = pv.pitch; }
    u.rate = g.en ? Math.max(0.3, +o.rate * (+o.enRate || 0.85)) : +o.rate;  // 영어 목소리는 대개 더 빨라서 조금 늦춤
    if (i === segs.length - 1) u.onend = onend;
    u.onerror = onerror;
    speechSynthesis.speak(u);
  });
}
function pickVoice(o) {
  if (o.voice === '__low') return { voice: koVoices()[0] || null, pitch: Math.max(0.1, +o.pitch * 0.62) };
  const v = o.voice && koVoices().find(x => x.voiceURI === o.voice);
  return { voice: v || null, pitch: +o.pitch };
}
function ttsPanel() {
  const o = ttsOpt();
  const ck = (k, label, hint = '') => `<label class="tts-ck"><input type="checkbox" data-tts="${k}" ${o[k] ? 'checked' : ''}><span>${label}${hint ? `<span class="sr"> - </span><small>${hint}</small>` : ''}</span></label>`;  // 낭독기가 '빠알리어 - 빠알리어 소리대로 읽음'처럼 끊어 읽게 (2026-11-18)
  const sel = (k, list, name = '') => `<select data-tts="${k}"${name ? ` aria-label="${name}"` : ''}>${list.map(([v, l]) => `<option value="${v}" ${String(o[k]) === String(v) ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  return `<h5>듣기 설정</h5>
    <div class="tts-row"><label for="ttsVoice">목소리</label><select id="ttsVoice" data-tts="voice">${voiceOptions(o.voice)}</select></div>
    <div class="tts-row"><label>빠르기 <b id="ttsRateV">${(+o.rate).toFixed(1)}배</b></label><input type="range" min="0.6" max="2.5" step="0.1" value="${o.rate}" data-tts="rate" aria-label="빠르기" aria-valuetext="${(+o.rate).toFixed(1)}배"></div>
    <div class="tts-row"><label>영어 빠르기 <b id="ttsEnRateV">${Math.round((+o.enRate || 0.85) * 100)}%</b><small class="muted"> (한국어 빠르기에 비해)</small></label><input type="range" min="0.6" max="1.2" step="0.05" value="${o.enRate || 0.85}" data-tts="enRate" aria-label="영어 빠르기 (한국어 빠르기에 비해)" aria-valuetext="${Math.round((+o.enRate || 0.85) * 100)}%"></div>
    <div class="tts-row"><label>목소리 높낮이 <b id="ttsPitchV">${(+o.pitch).toFixed(1)}</b></label><input type="range" min="0.6" max="1.4" step="0.1" value="${o.pitch}" data-tts="pitch" aria-label="목소리 높낮이" aria-valuetext="${(+o.pitch).toFixed(1)}"></div>
    <div class="tts-sub">읽을 것</div>
    ${ck('pali', '빠알리어', '빠알리어 소리대로 읽음')}${ck('gloss', '한글 옆 원어 풀이도 읽기', '위빳사나Vipassanā, 지도법사(Nāyaka Sayadaw)처럼 한글과 같은 말을 한 번 더 읽음')}${ck('en', '영어')}${ck('enVoice', '영어는 영어 목소리로', '영어 낱말·문장을 기기의 영어 목소리로 읽어 발음이 자연스러움 (영어 목소리가 없는 기기는 한국어 목소리로)')}${ck('hanja', '한자')}${ck('paren', '괄호 ( ) 안', '끄면 ( ) 안의 풀이·원어·참고를 건너뜀')}${ck('brack', '대괄호 [ ] 안', '끄면 옮긴이가 덧붙인 [ ] 안을 건너뜀')}${ck('fn', '각주', '본문 속 번호는 「각주 1」로 읽고, 각주 내용은 쪽 끝에서 읽음')}${ck('table', '표', '켜면 표를 한 줄씩 읽음 (색인 표는 지금 화면에 보이는 줄만)')}${ck('sym', '특수부호', '괄호·따옴표 등을 이름으로 읽음')}
    <div class="tts-sub">읽는 방식</div>
    <div class="tts-row"><label>문단 사이 쉼</label>${sel('pause', [[0, '쉬지 않음'], [0.3, '짧게'], [0.8, '보통'], [1.5, '길게']], '문단 사이 쉼')}</div>
    <div class="tts-row"><label>꺼짐 예약</label>${sel('sleep', [[0, '끄지 않음'], [15, '15분 뒤'], [30, '30분 뒤'], [60, '1시간 뒤']], '꺼짐 예약')}</div>
    ${ck('keySay', '단축키를 누르면 소리로 알려 주기', '화면 바꾸기·쪽 넘기기·지금 위치 등')}${ck('chapterStop', '한 장이 끝나면 멈추기')}${ck('follow', '읽는 곳을 따라 화면 움직이기')}
    <div class="row"><button class="tbtn" id="ttsTry">▶ 미리 듣기</button><button class="tbtn" id="ttsReset">처음 설정으로</button></div>
    <p class="note">목소리는 이 기기에 깔린 한국어 목소리 가운데서 고릅니다. 남성 목소리가 목록에 없으면 ‘낮은 목소리’를 고르거나, 컴퓨터에서는 마이크로소프트 엣지(Edge) 브라우저로 열면 남성 목소리(InJoon, Hyunsu)를 고를 수 있습니다. 설정은 이 기기의 브라우저에 저장되고, 듣는 중에 바꾸면 다음 문단부터 적용됩니다. 빨리어 낱말 목록: Digital Pāḷi Dictionary (CC BY-NC-SA 4.0).</p>
    <div class="tts-apply"><button class="tbtn main" id="ttsApply">✓ 적용하고 닫기</button></div>`;
}
// 듣기 설정 (이 브라우저에 저장)
const TTS_DEF = { voice: '', rate: 1, pitch: 1, gloss: false, sym: false, en: true, pali: true, hanja: true, fn: false, table: false, enVoice: false, enRate: 0.85, paren: true, brack: true, pause: 0.3, chapterStop: false, sleep: 0, follow: true, keySay: true };
const ttsOpt = () => Object.assign({}, TTS_DEF, store.get('tts', {}));
const SYM_NAME = { '(': '괄호 열고', ')': '괄호 닫고', '[': '대괄호 열고', ']': '대괄호 닫고', '‘': '작은따옴표', '’': '작은따옴표', '“': '큰따옴표', '”': '큰따옴표', '"': '큰따옴표', "'": '작은따옴표', '「': '낫표', '」': '낫표', '『': '겹낫표', '』': '겹낫표', '《': '겹화살괄호', '》': '겹화살괄호', '〈': '홑화살괄호', '〉': '홑화살괄호', '<': '홑화살괄호', '>': '홑화살괄호', '＜': '홑화살괄호', '＞': '홑화살괄호', '·': '가운뎃점', 'ㆍ': '가운뎃점', '…': '줄임표', '~': '물결표', '*': '별표', '/': '빗금', '|': '세로줄', '—': '줄표', '–': '줄표', '－': '붙임표' };
const SYM_RE = /[()\[\]‘’“”"'「」『』《》〈〉<>＜＞·ㆍ…~*/|—–－]/g;
const EN_A = '\u0001', EN_B = '\u0002';  // 영어 구간 표시 (영어 목소리로 읽을 부분)
// 경전 출처 'DN II 80'·'MN I 37'·'Sn 145'·'Ⅰ 129' 는 '디엔 투 80'처럼 읽음 — 약어는 영어 글자 이름, 로마 숫자는 영어 (운영자 요청, 2026-11-13: 듣기·오디오북 같게)
const CITE_AB = 'DN|MN|SN|AN|KN|Dhp|Sn|Ud|It|Vin|Vism|Vibh|Dhs|Kv|Pts|Ps|Thag|Thig|Ja|Mil|Nidd|Ap|Bv|Cp|Pv|Vv|Khp|Netti|Peṭ|DA|MA|SA|AA|DhpA|SnA|UdA|ItA|VinA';
const LETTER = { A: '에이', B: '비', C: '씨', D: '디', E: '이', F: '에프', G: '지', H: '에이치', I: '아이', J: '제이', K: '케이', L: '엘', M: '엠', N: '엔', O: '오', P: '피', Q: '큐', R: '알', S: '에스', T: '티', U: '유', V: '브이', W: '더블유', X: '엑스', Y: '와이', Z: '지', Ṭ: '티' };
const ROMAN = { I: '원', II: '투', III: '쓰리', IV: '포', V: '파이브', VI: '식스', VII: '세븐', VIII: '에잇', IX: '나인', X: '텐' };
const CITE_NUM = '(?:(?:I{1,3}|IV|V|VI{1,3}|IX|X)\\s+)?\\d+(?:\\s*[-~–]\\s*\\d+)?';
const CITE_RE = new RegExp(`\\b(${CITE_AB})\\.?[ \\u00a0]+(${CITE_NUM}(?:\\s*[,;]\\s*${CITE_NUM})*)(?![\\w.]*[A-Za-z])`, 'g');
const UROMAN = { 'Ⅰ': '원', 'Ⅱ': '투', 'Ⅲ': '쓰리', 'Ⅳ': '포', 'Ⅴ': '파이브', 'Ⅵ': '식스' };   // 'Ⅰ 129' 처럼 한 글자로 된 로마 숫자
const citeSay = s => s.replace(/[ⅠⅡⅢⅣⅤⅥ](?=\s*\d)/g, r => UROMAN[r]).replace(CITE_RE, (m, ab, rest) => ab.toUpperCase().split('').map(c => LETTER[c] || '').join('') + ' ' +
  rest.replace(/\b(I{1,3}|IV|V|VI{1,3}|IX|X)(?=\s+\d)/g, r => ROMAN[r]).replace(/\s*;\s*/g, ', '));
function sayable(s, o = ttsOpt(), mark = false) {
  const en = w => mark ? EN_A + w + EN_B : w;
  let t = citeSay(unB(s).replace(/^## /, ''));
  t = t.replace(/□\s*(?=\d)/g, '');   // 네모 번호 제목의 □ 는 읽지 않음
  // 숫자 사이의 줄표는 '빼기(마이너스)'로 읽지 않음 (운영자 요청, 2026-11-10)
  //  - 범위(앞 수 < 뒤 수: 8-10, 1-2, 3-7, 1885-1910, 238-242쪽)는 물결(~)처럼 '에서': 8에서 10
  //  - 그 밖(주소 178-19·51-41, 제1-1권, 전화·날짜처럼 줄표가 여러 번)은 '다시': 178 다시 19
  //  - 수학의 뺄셈(같은 줄에 = 가 있는 셈식, 예: 5 - 3 = 2)만 그대로(마이너스)
  t = t.replace(/(\d)\s?[~∼～〜]\s?(?=\d)/g, '$1에서 ');  // 물결(140~142)은 '140에서 142'
  t = t.replace(/[^\n]+/g, line => /[=＝]/.test(line) && /\d\s*[-–−]\s*\d/.test(line) ? line : line
    .replace(/\d+(?:[ ]?[-–][ ]?\d+){2,}/g, m => m.replace(/[ ]?[-–][ ]?/g, ' 다시 '))
    .replace(/(^|[^\d])(\d+)[ ]?[-–][ ]?(\d+)(?!\d)/g, (m, pre, a, b) => pre + a + (+a < +b && !/(제|동|리|길|번지|번길|호)\s*$/.test(pre + '') && !/(제|동|리|길|번지|번길)\s*$/.test(line.slice(0, line.indexOf(m) + pre.length)) ? '에서 ' : ' 다시 ') + b));
  t = t.replace(/(\S)[ \t]+[|｜│ㅣ][ \t]+(?=\S)/g, '$1, ');  // 구분 막대(엮음 | 김재성)는 짧게 쉬기 — '이'로 읽지 않게 (운영자 요청, 2026-11-10)
  if (/^%% /.test(t)) t = tocLines(t).filter(r => !r.sp).map(r => r.t + (r.p ? `, ${r.p}쪽` : '')).join('.\n');
  if (o.paren === false) { let prev; do { prev = t; t = t.replace(/\s?[(（][^()（）]*[)）]/g, ''); } while (t !== prev); }
  if (o.brack === false) t = t.replace(/\s?\[(?!\^)[^\[\]]*\]/g, '');
  t = t.replace(/\[\^([^\]]+)\]/g, (m, n) => o.fn ? ` 각주 ${n}, ` : ''); // 본문 속 각주 번호: '각주 읽기'를 켜면 '각주 1'로, 끄면 읽지 않음
  // 한글 바로 뒤에 붙은 로마자 풀이(예: 위빳사나Vipassanā, 사야도Chanmyay Sayadaw)는 한 번만 읽도록 뺌
  // 한글 바로 뒤에 띄어 쓰지 않고 붙은 로마자는 앞 한글의 원어 풀이로 봄 (위빳사나Vipassanā, 도사dosa, 사야도Chanmyay Sayadaw)
  //  - 풀이 읽기를 끄면 건너뜀, 켜면 빨리어 소리로 한 번 더 읽음
  t = t.replace(new RegExp(`([가-힣])([${LATIN}][${LATIN}\\-]*(?:\\s+[${LATIN}][${LATIN}\\-]*)*)`, 'g'), (m, h, lat) => {
    if (!o.gloss) return h;
    const ws = lat.split(/[\s-]+/).filter(Boolean), pc = ws.filter(w => langOf(w) === 'P').length, ec = ws.filter(w => langOf(w) === 'E').length;
    const pali = PALI_MARK.test(lat) || pc > ec || (pc === ec && /[a-z]/.test(lat[0]));
    return h + ' ' + (pali ? (o.pali ? lat.split(/[\s-]+/).map(w => PALI(w) || w).join(' ') : '') : (o.en ? en(lat) : ''));
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
      if (BUR[comp.toLowerCase()]) return BUR[comp.toLowerCase()];  // 미얀마 존칭은 한국어 소리로
      // 붙임표로 이은 말은 조각마다 가름 (Pāli-Korean-English → 빨리 / 영어 / 영어)
      if (comp.includes('-')) return comp.split('-').map(w => { const lw = langOf(w); const wp = lw === 'P' || ((lw === 'B' || lw === '?') && pali); return wp ? (o.pali ? (PALI(w) || w) : '') : (o.en ? en(w) : ''); }).join(' ');
      if (pali) return o.pali ? comp.split('-').map(w => PALI(w) || w).join(' ') : ' ';
      return o.en ? en(comp) : ' ';
    });
  });
  if (!o.hanja) t = t.replace(/[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]+/g, ' ');
  // 한글 음역의 장음 표시(까라니-야, 삿따-)는 읽지 않음
  t = t.replace(/([가-힣])-(?=[가-힣\s,.!?)’”]|$)/g, '$1');
  // 특수부호: 읽기를 켜면 이름으로 읽고, 끄면 소리 내지 않음
  t = o.sym ? t.replace(SYM_RE, c => ` ${SYM_NAME[c] || ''} `) : t.replace(SYM_RE, ' ');
  if (mark) t = t.replace(/\u0002([\s,;:.!?'’‘\-]*)\u0001/g, '$1');
  return t.replace(/\(\s*\)/g, ' ').replace(/\s+([.,!?])/g, '$1').replace(/([.,!?])(?:\s*[.,])+/g, '$1').replace(/\s{2,}/g, ' ').trim();
}
const fnMark = h => h.replace(/^\[\^([^\]]+)\]:\s*/, '<span class="fn-no" data-fnno="$1" role="button" tabindex="0" aria-label="각주 $1 본문 자리로 가기" title="본문 자리로 가기">$1</span>').replace(/\[\^([^\]]+)\]/g, '<sup class="fn-ref" role="button" tabindex="0" data-fn="$1" aria-label="각주 $1">$1</sup>');
// 본문 속 그림 ![설명](주소) 과 표(| 칸 | 칸 |)
// 소제목 알아보기: 빈칸·괄호 속 풀이를 빼고 목차 제목과 같으면 소제목
const isHead = t => /^## /.test(t);
// **굵은 글씨**: 관리자 화면 본문에서 ** 로 감싼 곳 (화면에서는 굵게, 듣기·찾기·밑줄에서는 ** 를 뺌)
const unB = s => String(s || '').replace(/\*\*|==|\{\{|\}\}|@@|°°|§§/g, '').replace(/^(?:\^\^|::|>>|\|\||\+\+) /gm, '');
// 검색 결과에 보일 글: 그림 주소·## ·각주 표시 같은 내부 부호를 뺌
const plainT = s => unB(s).replace(/!\[[^\]]*\]\([^)]*\)/g, ' ').replace(/^#{1,6} /gm, '').replace(/\[\^\d+\]:?\s?/g, ' ').replace(/\[\[[^\]]*\]\]/g, ' ');
// **굵게**, ==색 강조(인쇄본·전자책의 하늘색 글자)==
// □ 안 번호 제목('□5 대념처경') → 네모 테두리 번호 (운영자 요청, 2026-11-16 — DL-0031)
const boxNum = h => h.replace(/□\s*(\d{1,3})\s*/g, '<span class="boxnum">$1</span>');
const boldMark = h => boxNum(h).replace(/ㆍ/g, '·').replace(/\*\*(?!\s|\*\*)([\s\S]*?[^\s*])\*\*/g, '<strong>$1</strong>').replace(/==(?=\S)([\s\S]*?\S)==/g, '<span class="hl">$1</span>').replace(/\{\{([\s\S]*?)\}\}/g, '<span class="faint" title="생략할 수 있는 부분">$1</span>').replace(/@@([\s\S]*?)@@/g, '<span class="pron">$1</span>').replace(/°°([\s\S]*?)°°/g, '<span class="pli">$1</span>').replace(/§§([\s\S]*?)§§/g, '<span class="spk">$1</span>').replace(/-{8,}(?=\*|\[\^)/g, m => `<span class="dash-rule" style="width:${Math.min(16, m.length * .5)}em" aria-hidden="true"></span>`);  // 각주 번호가 붙은 점선('------------[^19]') → 가운데 가로줄 (운영자 요청, 2026-11-15)  // @@…@@ 빠알리 한글 소리 줄 (DL-0027: 원본처럼 굵은 둥근 글꼴)  // {{…}} 희미한 글자 (DL-0027: 인도자가 없거나 간략히 할 때 생략하는 부분)
// 빠알리어 한글 표기(발음 부호 붙은 한글): 텍스트 JSON 의 ph 사전(tools/pali_hangul.py)대로 바꿔 PaliHangul 글꼴로 — 본문 글자는 그대로, 화면에만
let PH_RE = null, PH_OF = null;
const phMark = h => latMark(phMark0(h));
const phMark0 = h => {
  const ph = R && R.ph; if (!ph) return h;
  if (PH_OF !== ph) { PH_OF = ph; const ks = Object.keys(ph).sort((a, b) => b.length - a.length).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')); PH_RE = ks.length ? new RegExp('(' + ks.join('|') + ')(?![\u0300-\u036f\u1dc0-\u1dff\u302c\u302d\u02d1\u02d4\u02d5\u2033])', 'g') : null; }
  if (!PH_RE) return h;
  // 화면 낭독기: 글꼴 표기(부호 글자)는 읽지 않게 숨기고, 부호를 뺀 한글 소리를 보이지 않는 글(CSS ::before — 복사·밑줄 글자 자리에는 안 들어감)로 알려 줌 (운영자 요청, 2026-11-17)
  return h.replace(/(<[^>]*>)|([^<]+)/g, (m, tag, txt) => tag || txt.replace(PH_RE, w => { const say = phSay(w); return `<span class="ph" aria-hidden="true">${ph[w]}</span><span class="ph-say" data-say="${esc(say)}"></span>`; }));
};
// 화면 낭독기: 로마자 빠알리어(vipassanā, Mahāsi Sayādaw)는 사이트 '듣기'와 같은 음역 규칙의 한글 소리로 알려 줌 (운영자 요청, 2026-11-17)
//  - 화면에는 로마자 그대로(aria-hidden), 뒤의 빈 .ph-say 가 한글 소리('위빳사나')를 낭독기에만 들려줌 — 복사·밑줄 글자 자리는 그대로
//  - 빠알리어·영어 가르기는 sayable 과 같음(langOf·PALI_MARK·다수결), 영어는 건드리지 않음
let LAT_RUN = null, LAT_COMP = null;
function latMark(h) {
  if (!/[A-Za-z]/.test(h)) return h;
  if (!LAT_RUN) { LAT_RUN = new RegExp(`[${LATIN}]+(?:[\\s,;:.!?'’‘\\-]+[${LATIN}]+)*`, 'g'); LAT_COMP = new RegExp(`[${LATIN}]+(?:-[${LATIN}]+)*`, 'g'); }
  const hide = (comp, say) => `<span aria-hidden="true">${comp}</span><span class="ph-say" data-say="${esc(say)}"></span>`;
  return h.replace(/(<[^>]*>)|(&[#a-z0-9]+;)|([^<&]+)/gi, (m, tag, ent, txt) => tag || ent || txt.replace(LAT_RUN, run => {
    const comps = run.match(LAT_COMP) || [];
    const lab = comps.map(c => { const ls = c.split('-').map(langOf); return ls.includes('P') ? 'P' : ls.includes('E') ? 'E' : ls.includes('B') ? 'B' : '?'; });
    const pc = lab.filter(x => x === 'P').length, ec = lab.filter(x => x === 'E').length;
    const runPali = PALI_MARK.test(run) || pc > ec;
    let k = 0;
    return run.replace(LAT_COMP, comp => {
      const l = lab[k++], lc = comp.toLowerCase();
      if (BUR[lc] && (runPali || pc > 0)) return hide(comp, BUR[lc]);
      const pali = l === 'P' || ((l === 'B' || l === '?') && runPali && (l === 'B' || pc > 0));
      if (!pali) return comp;
      const say = comp.split('-').map(w => PALI(w) || '').join(' ').trim();
      return /[가-힣]/.test(say) ? hide(comp, say) : comp;
    });
  }));
}
// 화면 낭독기용 로마자 빠알리어 가르기는 DPD 낱말 목록(/data/pali-words.txt — Digital Pāḷi Dictionary 표제어·낱말 꼴, 경전 법보시 앱과 같은 사전)을 씀.
// 목록은 '듣기'를 누를 때만 받았으므로, 읽기 화면을 열면 본문에 로마자가 있을 때 뒤에서 받아 이미 그린 글에도 다시 적용 (운영자 요청, 2026-11-17 — 'moha' 처럼 기호 없는 낱말)
function latLater() {
  if (LEX.pali) return;
  const body = $('#rBody'); if (!body || !/[A-Za-z]{2}/.test(body.textContent)) return;
  const run = () => loadLex().then(() => {
    const b = $('#rBody'); if (!b || (R && R.speaking) || AB.on) return;  // 듣는 중에는 글을 건드리지 않음(다음에 그릴 때 적용)
    const w = document.createTreeWalker(b, NodeFilter.SHOW_TEXT, { acceptNode: n => /[A-Za-z]{2}/.test(n.nodeValue) && !n.parentElement.closest('[aria-hidden="true"],.ph-say,script,style,input,textarea') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
    const ns = []; while (w.nextNode()) ns.push(w.currentNode);
    ns.forEach(n => { const h = latMark(esc(n.nodeValue)); if (h === esc(n.nodeValue)) return; const t = document.createElement('template'); t.innerHTML = h; n.replaceWith(t.content); });
  });
  ('requestIdleCallback' in window) ? requestIdleCallback(run, { timeout: 4000 }) : setTimeout(run, 1500);
}
const PH_MARKS = /[\u0300-\u036f\u1dc0-\u1dff\u20d0-\u20ff\ufe00-\ufe0f\ufe20-\ufe2f\u302c\u302d\u02b9-\u02ff\u2033\ue000-\uf8ff\u22a4\u22a5]/g;
const phSay = w => w.replace(PH_MARKS, '').normalize('NFC').trim() || '발음 부호';
const headKey = t => unB(t).replace(/^## /, '').replace(/\[\^[^\]]+\]/g, '').replace(/\([^)]*\)/g, '').replace(/[\s‘’'"“”]/g, '').replace(/^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX]+\./, m => m.replace(/[IVX]+/g, x => ({I:'Ⅰ',II:'Ⅱ',III:'Ⅲ',IV:'Ⅳ',V:'Ⅴ',VI:'Ⅵ',VII:'Ⅶ',VIII:'Ⅷ',IX:'Ⅸ',X:'Ⅹ'}[x] || x)));
const FIG_RE = /^!\[([^\]]*)\]\(([^)\s]+)\)\s*$/;
const isTable = p => /^\|.*\|\s*$/m.test(p) && p.split('\n').filter(l => l.trim()).every(l => /^\|/.test(l.trim()));
function tableHtml(p) {
  // 머리 줄: 보통은 첫 줄. 구분 줄(|---|)이 있으면 그 위 줄들이 머리, 구분 줄로 시작하면 머리 없음(쪽을 넘어 이어지는 표 — DL-0030, 2026-11-15)
  const lines = p.split('\n').map(l => l.trim()).filter(Boolean), isSep = l => /^\|[\s:|-]+\|?$/.test(l);
  const si = lines.findIndex(isSep), nh = si < 0 ? 1 : si;
  const rows = lines.filter(l => !isSep(l)).map(l => l.replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
  if (!rows.length) return '';
  const cell = c => fnMark(phMark(boldMark(esc(c))));  // 표 칸의 각주 번호도 누를 수 있게 (2026-11-18 검수: '[^550]' 이 글자로 보이던 것)
  const dl = R.tdl && R.tdl[rows[0][0]];   // 이 표를 그림으로 내려받는 단추 (텍스트 JSON 의 table_dl, 운영자 요청 2026-11-12)
  return `<table class="r-table">${nh ? `<thead>${rows.slice(0, nh).map(r => `<tr>${r.map(c => `<th>${cell(c)}</th>`).join('')}</tr>`).join('')}</thead>` : ''}<tbody>${rows.slice(nh).map(r => `<tr>${r.map(c => `<td>${cell(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`
    + (dl ? `<p class="r-tdl"><a class="tbtn" href="${esc(dl)}" download="${esc(dl.split('/').pop())}">⬇ 그림으로 내려받기</a></p>` : '');
}
// 색인 표: 네 가지 순서(인쇄본 제1~4부)를 버튼으로 바꿔 보고, 낱말로 찾기
const ixNorm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, '');
function ixRows() {
  const p = R.ix.parts[R.ixPart] || R.ix.parts[0], q = ixNorm(R.ixQ);
  return q ? p.rows.filter(r => r.slice(0, 4).some(c => ixNorm(c).includes(q))) : p.rows;
}
function ixMark(c) {
  const q = R.ixQ.trim(); let h = esc(c);
  if (q) { const i = c.toLowerCase().indexOf(q.toLowerCase()); if (i >= 0) h = esc(c.slice(0, i)) + '<mark>' + esc(c.slice(i, i + q.length)) + '</mark>' + esc(c.slice(i + q.length)); }
  return h.replace(/\n/g, '<br>');
}
function ixBody() {
  const p = R.ix.parts[R.ixPart] || R.ix.parts[0], rows = ixRows(), cols = p.cols;
  const side = cols[0] === 'hg' ? 'pali' : 'hg';
  const role = c => c === cols[0] ? 'a-head' : c === side ? 'a-side' : 'a-line';
  const tr = r => {
    const ref = r.slice(1, 4).every(x => !x) && /⇒/.test(r[0]);
    if (ref) return `<tr class="ix-ref"><td colspan="4" class="a-head">${ixMark(r[0])}</td></tr>`;
    return `<tr>${cols.map((c, j) => `<td class="c-${c} ${role(c)}"${c === 'pali' ? ' lang="pi"' : c === 'en' ? ' lang="en"' : ''}>${ixMark(r[j])}</td>`).join('')}</tr>`;
  };
  return `<p class="ix-count small muted" aria-live="polite">${R.ixQ.trim() ? `‘${esc(R.ixQ.trim())}’ ${rows.length}개 찾음` : ''}</p>
  ${rows.length ? `<table class="ix-t"><thead><tr>${cols.map(c => `<th scope="col" class="c-${c}">${esc(R.ix.colnames[c])}</th>`).join('')}</tr></thead><tbody>${rows.map(tr).join('')}</tbody></table>` : '<p class="muted">찾는 낱말이 없습니다. 다른 표기로 찾아보세요.</p>'}`;
}
function ixHtml() {
  const p = R.ix.parts[R.ixPart] || R.ix.parts[0];
  return `<div class="ix-bar"><label class="ix-find"><span class="sr">색인에서 낱말 찾기</span><input type="search" id="ixQ" value="${esc(R.ixQ)}" placeholder="낱말 찾기: 빠알리어·한국어·영어·한글 표기" autocomplete="off"></label>
  <div class="ix-parts" role="group" aria-label="줄 세우는 순서">${R.ix.parts.map((x, i) => `<button class="ix-p${i === R.ixPart ? ' on' : ''}" data-ixp="${i}" aria-pressed="${i === R.ixPart}">${esc(x.label)}</button>`).join('')}</div></div>
  <h4 class="ix-title">${esc(p.part)} : ${esc(p.title)}</h4>${p.note && !R.ixQ.trim() ? `<p class="ix-note">${esc(p.note).replace(/\n/g, '<br>')}</p>` : ''}<div id="ixBody">${ixBody()}</div>`;
}
function bindIx() {
  const box = $('#ix'); if (!box) return;
  const q = $('#ixQ', box); let t;
  if (q) q.oninput = () => { clearTimeout(t); t = setTimeout(() => { R.ixQ = q.value; $('#ixBody', box).innerHTML = ixBody(); const nt = $('.ix-note', box); if (nt) nt.hidden = !!R.ixQ.trim(); }, 150); };
  $$('[data-ixp]', box).forEach(b => b.onclick = () => { R.ixPart = +b.dataset.ixp; store.set('ixp-' + R.id, R.ixPart); box.innerHTML = ixHtml(); bindIx(); const nq = $('#ixQ', box); });
}
/* 본문 그림의 화면 낭독기 이름 — 전에는 모든 그림이 '그림 크게 보기'로만 들렸음 (운영자 요청, 2026-11-18) */
const FIG_DECO = /^(구분 ?장식|구분선|장식|꾸밈|무늬|법륜|사자상 그림|보리수 잎 그림)$/;
function figLabel(alt) {
  const a = String(alt || '').trim();
  if (!a || /^(그림|사진)$/.test(a)) return `${a || '그림'} (설명 없음). 누르면 크게 보기`;
  if (/^표$/.test(a)) return '표 그림 (글로 된 내용 없음). 누르면 크게 보기';
  return `${/(그림|사진|표|지도|가계도|서명|마크)$/.test(a) ? a : '그림: ' + a}. 누르면 크게 보기`;
}
function blockHtml(s, n, k) {
  if (s.trim() === '[[색인]]') return R && R.ix ? `<div class="ix" id="ix" data-pg="${n}" data-s="${k}" data-skip="1">${ixHtml()}</div>` : '';
  const f = s.match(FIG_RE);
  if (f && f[1].startsWith('#')) { const alt = f[1].slice(1).trim();
    if (FIG_DECO.test(alt)) return `<figure class="r-fig deco" data-pg="${n}" data-s="${k}" data-skip="1" aria-hidden="true"><button class="fig-btn" tabindex="-1" data-zoom-img="${esc(f[2])}" data-cap="${esc(alt)}"><img src="${esc(f[2])}" alt="" loading="lazy"></button></figure>`;  // 구분선·장식은 화면 낭독기·Tab 에서 숨김 (운영자 요청, 2026-11-18)
    return `<figure class="r-fig" data-pg="${n}" data-s="${k}" data-skip="1"><button class="fig-btn" data-zoom-img="${esc(f[2])}" data-cap="${esc(alt)}" aria-label="${esc(figLabel(alt))}"><img src="${esc(f[2])}" alt="" loading="lazy"></button></figure>`; }  // ![#설명](주소): 설명은 화면에 안 보이고 읽기 프로그램만 읽음
  if (f) return `<figure class="r-fig" data-pg="${n}" data-s="${k}" data-skip="1"><button class="fig-btn" data-zoom-img="${esc(f[2])}" data-cap="${esc(f[1])}" aria-label="${esc(figLabel(f[1]))}"><img src="${esc(f[2])}" alt="" loading="lazy"></button>${f[1] ? `<figcaption aria-hidden="true">${esc(f[1])}</figcaption>` : ''}</figure>`;
  if (/^%% /.test(s)) return `<div class="r-toc" data-pg="${n}" data-s="${k}" data-skip="1">${tocLines(s).map(r => r.sp ? '<div class="tl-sp" aria-hidden="true"></div>' : `<div class="tl l${Math.min(r.lv, 3)}"><span class="tt">${phMark(boldMark(esc(r.t)))}</span>${r.p ? `<span class="dots" aria-hidden="true"> </span><span class="tp">${esc(r.p)}</span>` : ''}</div>`).join('')}</div>`;  // 차례: 인쇄본처럼 단계별 들여쓰기·점선·쪽 번호
  if (isTable(s)) return `<div class="r-tbl" data-pg="${n}" data-s="${k}" data-skip="1">${tableHtml(s)}<button class="tbtn sm" data-zoom-tbl>표 크게 보기</button></div>`;
  return null;
}
// 차례 문단 '%% ': 줄마다 앞의 - 개수 = 단계(없으면 장), ' | ' 뒤 = 쪽 번호  예) %% 제1장  서원과 수기\n- 서원을 하다 | 36\n-- 수메다 바라문 | 36
const tocLines = s => s.replace(/^%% /, '').split('\n').filter(l => l.trim()).map(l => { if (l.trim() === '~') return { sp: true, lv: 0, t: '', p: '' }; const m = l.match(/^(-*)\s*(.*?)(?:\s+\|\s*(\S+))?\s*$/); return { lv: m[1].length, t: m[2], p: m[3] || '' }; });
const isFootnote = p => /^\[\^[^\]]+\]:/.test(p);
// 장 첫 쪽에서 장 제목과 같은 글(소제목·가운데 제목)은 화면에서 숨기고 소리로도 두 번 읽지 않음 — 장 제목으로 통일
const dupKey = t => headKey(String(t).replace(/^(::|\^\^|##|\+\+)\s*/, '').replace(/^[^┃\n]*┃/, '')).replace(/[.,:·\-–—!?■□●○◆◇◎◉★☆▶▷◀◁※•_]/g, '');  // '책 제목┃부록' 같은 쪽 머리 표시는 뒤쪽 이름만
// 장 첫머리의 문단 몇 개(예: 'Ⅰ' + '껍데기는 버리고…')를 이으면 장 제목과 같아지는지 → 그 문단들의 'n:k' 모음
function chDups(c) {
  if (!c || !c.title) return new Set();
  if (c._dups) return c._dups;
  const want = dupKey(c.title), found = new Set();
  // 장 첫 쪽, 그리고 첫 쪽이 제목뿐이면 다음 쪽 첫머리까지 (부 표지 쪽 + 다음 쪽 제목처럼 되풀이되는 경우)
  for (let n = c.from; n <= Math.min(c.to, c.from + 5); n++) {  // 장 첫머리가 그림·빈 쪽뿐이면 다음 쪽 첫머리까지
    const ps = paras((R.pages[n - 1] || {}).text); let acc = '', out = [], k = n === c.from ? (c.k0 || 0) : 0;
    for (; k < ps.length; k++) {
      const s = ps[k]; if (FIG_RE.test(s)) continue;
      const dk = dupKey(s); if (!dk || isFootnote(s) || s.length > 160 || !want.startsWith(acc + dk)) break;
      acc += dk; out.push(k); if (acc === want) {
        // 장 표지의 '(Yamakavagga)'·'(千)'처럼 제목에 들어 있는 괄호 글만 있는 줄도 같은 제목으로 (DL-0021)
        const tt = c.title.replace(/\s/g, '');
        for (let j = k + 1; j < ps.length; j++) { const m = ps[j].replace(/^(::|\^\^)\s*/, '').trim().match(/^\(([^)]*)\)$/); if (!m || !tt.includes(m[1].replace(/\s/g, ''))) break; out.push(j); }
        out.forEach(x => found.add(n + ':' + x)); break;
      }
    }
    if (ps.some((s, i) => !found.has(n + ':' + i) && !FIG_RE.test(s) && s.trim())) break;  // 첫 쪽에 다른 글이 있으면 다음 쪽은 보지 않음
  }
  return (c._dups = found);
}
const isChDup = (s, n, c, k) => chDups(c).has(n + ':' + k);
// 표를 소리로 읽을 줄들: 한 줄 = 칸들을 쉼표로 이어서
function tableLines(s) {
  if (s.trim() === '[[색인]]') return R && R.ix ? ixRows().map(r => r.slice(0, 4).filter(Boolean).join(', ').replace(/\n/g, ' ')) : [];
  return s.split('\n').map(l => l.trim()).filter(l => l && !/^\|[\s:|-]+\|?$/.test(l)).map(l => l.replace(/^\||\|$/g, '').split('|').map(c => c.trim()).filter(Boolean).join(', ')).filter(Boolean);
}
// fromK: 그 쪽의 몇 번째 문단부터, firstText: 첫 문단은 이 글부터(고른 곳부터 읽기)
// 듣기가 읽는 문단인지 (← 로 앞 문단을 찾을 때)
function readable(s, o) { if (!s || !s.trim()) return false; if (isFootnote(s)) return !!o.fn; const fg = s.match(FIG_RE); if (fg) return !!(R && R.say && R.say[fg[2]]); if (isTable(s) || s.trim() === '[[색인]]') return !!o.table; return !!sayable(s, o, true); }
function speak(fromK = 0, firstText = null) {
  if (!('speechSynthesis' in window)) { noVoice(); return; }
  if (AB.locked) { abLockedMsg(); return; }
  if (AB.on && !abA().paused) abA().pause();  // 오디오북과 기계 음성 듣기는 함께 쓰지 않음
  if (!LEX.pali) { toast('읽기를 준비하는 중입니다…'); loadLex().then(() => speak(fromK, firstText)); return; }
  if (R.resumeAt) { if (fromK === 0 && firstText == null && R.resumeAt.i === R.i) fromK = R.resumeAt.k; R.resumeAt = null; $$('#rBody .resume-at').forEach(x => x.classList.remove('resume-at')); }
  const o = ttsOpt();
  const p = R.pages[R.i]; const sentences = paras(p.text);
  if (!sentences.length) { if (R.i < R.pages.length - 1) { R.i++; renderReader(); setTimeout(() => speak(), 200); } return; }
  try { speechSynthesis.cancel(); } catch (e) {}
  if (!R.speaking) { R.ttsStart = Date.now(); R.ttsChapter = chapterOf(R.i + 1); }
  wake(true, 'tts');
  R.speaking = true; renderReader(); let k = Math.min(fromK, sentences.length - 1), first = firstText;
  const lastBody = (() => { for (let j = sentences.length - 1; j >= 0; j--) if (!isFootnote(sentences[j]) && !FIG_RE.test(sentences[j]) && !isTable(sentences[j])) return j; return -1; })();
  const pv = pickVoice(o), voice = pv.voice;
  let tq = null;  // 표를 읽는 중이면 남은 줄들
  const next = () => {
    if (!R || !R.speaking) return;
    $$('.speaking').forEach(x => x.classList.remove('speaking'));
    if (o.sleep && Date.now() - R.ttsStart > o.sleep * 60000) { stopSpeak(true); toast('정한 시간이 되어 듣기를 멈췄습니다'); return; }
    if (k >= sentences.length) {
      if (R.i >= R.pages.length - 1) { stopSpeak(true); return; }
      if (o.chapterStop && chapterOf(R.i + 2) !== R.ttsChapter) { stopSpeak(true); toast('이 장을 다 읽었습니다'); return; }
      R.i++; renderReader(); speak(); return;
    }
    if (R.ttsSkip && R.ttsSkip.n === p.n && R.ttsSkip.k === k) { R.ttsSkip = null; k++; next(); return; }  // 앞 쪽 끝에서 이미 이어 읽은 문단
    { // 장이 시작하는 곳: 장 제목을 먼저 읽고, 본문의 같은 제목 문단은 건너뜀
      const cs = chapters(), ci = chapterOf(R.i + 1), c = cs[ci];
      const atStart = c && (p.n === c.from ? k === (c.k0 || 0) : k === sentences.findIndex(x => x.trim()) && R.pages.slice(c.from - 1, R.i).every(q => !paras(q.text).some(x => x.trim())));  // 장 첫 쪽이 비어 있으면 다음 쪽 첫 문단이 시작
      if (c && c.title && R.ttsTitled !== ci + ':' + R.id && (atStart || isChDup(sentences[k], p.n, c, k))) {
        R.ttsTitled = ci + ':' + R.id; R.ttsPos = { i: R.i, k };
        const tt = sayable(c.title.trim().replace(/^([IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)\.\s*/, (m, r) => { const v = { I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6, VII: 7, VIII: 8, IX: 9, X: 10, 'Ⅰ': 1, 'Ⅱ': 2, 'Ⅲ': 3, 'Ⅳ': 4, 'Ⅴ': 5, 'Ⅵ': 6, 'Ⅶ': 7, 'Ⅷ': 8, 'Ⅸ': 9, 'Ⅹ': 10 }[r]; return v ? v + '. ' : m; }), o, true);  // 로마 숫자는 소리로 '3.'
        if (tt) { speakSents(tt, o, pv, 0, () => { if (!R || !R.speaking) return; ttsLater(next, Math.max(0, +o.pause * 1000)); }, e => { if (e.error !== 'interrupted' && e.error !== 'canceled') stopSpeak(true); }, d => { if (!R || !R.speaking) return; if (d > 0) next(); else { R.ttsTitled = null; back(true); } }, null, true); return; }
      }
      if (c && isChDup(sentences[k], p.n, c, k)) { k++; next(); return; }
    }
    R.ttsPos = { i: R.i, k };
    let raw = first && first.trim() ? first : sentences[k]; first = null;
    // 쪽 끝에서 문장이 끊긴 문단은 다음 쪽 첫 문단과 이어서 한 번에 읽기 (끊어 읽으면 낱말이 뭉개짐)
    if (k === lastBody && chapterOf(R.i + 1) === chapterOf(R.i + 2) && !isFootnote(raw) && !isHead(raw) && !/[.?!。…”’"')\]」』:]\s*$/.test(raw.replace(/\[\^[^\]]+\]\s*$/, ''))) {
      const np = R.pages[R.i + 1], nps = np ? paras(np.text) : [], nk = nps.findIndex(x => x.trim());
      if (np && nk >= 0 && !isFootnote(nps[nk]) && !isHead(nps[nk]) && !FIG_RE.test(nps[nk])) {
        const a = raw.replace(/\s+$/, ''), b = nps[nk].replace(/^\s+/, '');
        raw = a + (/[가-힣]$/.test(a) && /^[가-힣]/.test(b) ? '' : ' ') + b; R.ttsSkip = { n: np.n || R.i + 2, k: nk };
      }
    }
    const isTbl = isTable(sentences[k]) || sentences[k].trim() === '[[색인]]';
    { const fg = sentences[k].match(FIG_RE); if (fg && R.say && R.say[fg[2]]) raw = R.say[fg[2]]; }  // 그림 내용을 소리로 읽을 글이 있으면 그것을 읽음
    if ((!o.fn && isFootnote(sentences[k])) || (FIG_RE.test(sentences[k]) && !(R.say && R.say[(sentences[k].match(FIG_RE) || [])[2]])) || (isTbl && !o.table)) { k++; next(); return; }
    if (isTbl && !tq) { tq = tableLines(sentences[k]); if (!tq.length) { tq = null; k++; next(); return; } }
    const el = $(`[data-pg="${p.n}"][data-s="${k}"]`); if (el) { el.classList.add('speaking'); if (o.follow && !tq) el.scrollIntoView({ block: 'nearest' }); ttsFocus(el); }
    try { const c0 = chapters()[chapterOf(p.n)]; ttsPosSave(R.id, R.title, p.n, k, p.label, c0 && c0.title); } catch (e) {}
    const text = tq ? sayable(tq.shift(), o, true) : sayable(raw.replace(/^\[\^([^\]]+)\]:\s*/, (m, n) => `각주 ${n}. `), o, true);
    const adv = () => { if (tq && tq.length) return; tq = null; k++; };
    if (!text) { adv(); next(); return; }
    const si = R.ttsSi; R.ttsSi = 0;
    speakSents(text, o, pv, si, () => { if (!R || !R.speaking) return; adv(); ttsLater(next, Math.max(0, +o.pause * 1000)); }, e => { if (e.error !== 'interrupted' && e.error !== 'canceled') stopSpeak(true); },
      d => { if (!R || !R.speaking) return; tq = null;
        if (d > 0) { k++; next(); return; }
        back(); }, el);
  };
  // ← 로 앞 문단의 마지막 문장 (이 쪽 첫 문단이면 앞 쪽의 마지막 문단)
  const back = fromTitle => {
        const c = chapters()[chapterOf(R.i + 1)];
        if (!fromTitle) for (let j = k - 1; j >= 0; j--) if (readable(sentences[j], o) && !(c && isChDup(sentences[j], p.n, c, j))) { k = j; R.ttsSi = 'last'; R.ttsSkip = null; next(); return; }
        // 장의 첫 문단이면 장 제목부터 다시
        if (!fromTitle && c && c.title && p.n === c.from && R.ttsTitled) { R.ttsTitled = null; R.ttsSi = 0; k = sentences.findIndex(x => x.trim()); next(); return; }
        // 이 쪽 첫 문단이면 앞 쪽의 마지막 문단으로
        for (let i = R.i - 1; i >= 0; i--) { const ps = paras(R.pages[i].text); for (let j = ps.length - 1; j >= 0; j--) if (readable(ps[j], o)) { R.i = i; R.ttsSi = 'last'; R.ttsSkip = null; renderReader(); speak(j); return; } }
        R.ttsSi = 0; next();
  };
  next();
}
// 휴대폰에서 화면을 잠그거나 다른 앱으로 가면 브라우저가 읽기를 멈춤 → 돌아오면 멈춘 문단부터 이어 읽기
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState !== 'visible' || !R || !R.speaking || !R.ttsPos) return;
  setTimeout(() => {
    if (!R || !R.speaking || speechSynthesis.speaking || speechSynthesis.pending) return;
    if (R.ttsPos.i !== R.i) { R.i = R.ttsPos.i; renderReader(); }
    toast('멈춘 곳부터 이어서 읽습니다'); speak(R.ttsPos.k);
  }, 600);
});
// ---- 오디오북 (운영자 요청, 2026-11-10) ----
// 미리 만든 소리 파일(장마다 mp3)을 <audio> 로 틀어서 화면을 끄거나 다른 앱을 써도 계속 들림(백그라운드 재생).
// /data/audio/<ID>.json 의 sync [[시작 초, 쪽 순번, 문단 순번], …] 로 지금 읽는 문단을 표시하고 따라감.
const AB_TIP = '미리 만든 오디오북을 듣습니다. 화면을 끄거나 다른 앱을 써도 계속 들립니다 (백그라운드 재생)';
const AB = { a: null, on: false, ci: -1, k: -1, userAt: 0, saved: 0, locked: false, mediaPause: 0 };
// 🔒 잠금 (운영자 요청, 2026-11-10): 화면을 켜 둔 채 들을 때 실수로 멈추거나 읽기 화면을 떠나지 않게
const abLockedMsg = () => toast('오디오북이 잠겨 있습니다. 🔒 잠김 단추를 눌러 풀어 주세요');
function abSetLock(on) {
  AB.locked = on; const b = $('#abBar'), l = $('#abLock');
  if (b) b.classList.toggle('locked', on);
  if (l) { l.textContent = on ? '🔒' : '🔓'; l.dataset.tip = on ? '잠김: 눌러서 풀기' : '잠금: 실수로 멈추거나 닫히지 않게, 화면도 꺼지지 않게'; l.setAttribute('aria-pressed', on); l.setAttribute('aria-label', on ? '잠김, 눌러서 풀기' : '잠그기'); }
  wake(on && AB.a && !AB.a.paused, 'ab');
  if (on) { try { history.pushState({ abLock: 1 }, ''); } catch (e) {} toast('잠갔습니다. 화면이 꺼지지 않고, 실수로 멈추거나 닫히지 않습니다'); }
  else if (history.state && history.state.abLock) { AB.skipPop = true; try { history.back(); } catch (e) {} }  // 잠글 때 넣어 둔 '뒤로 가기' 막이를 거둠
}
// 잠겨 있을 때 휴대폰 '뒤로 가기'로 읽기 화면을 떠나지 않게
window.addEventListener('popstate', () => { if (AB.locked) { try { history.pushState({ abLock: 1 }, ''); } catch (e) {} abLockedMsg(); } });
function abA() {
  if (AB.a) return AB.a;
  const a = AB.a = new Audio(); a.preload = 'auto';
  a.addEventListener('timeupdate', abTick);
  a.addEventListener('play', () => { abUi(); if (AB.locked) wake(true, 'ab'); if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing'; });
  a.addEventListener('pause', () => {
    abSave(); abUi(); if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
    // 잠겨 있는데 저절로 멈추면(이어폰이 빠짐·블루투스 끊김) 다시 재생 — 잠금 화면·이어폰 단추로 멈춘 것은 그대로 둠
    if (AB.locked && !a.ended && Date.now() - AB.mediaPause > 1500) setTimeout(() => { if (AB.locked && a.paused && !a.ended) a.play().catch(() => {}); }, 400);
    else wake(false, 'ab');
  });
  a.addEventListener('ended', abNext);
  a.addEventListener('error', () => { if (a.src) toast('오디오북 파일을 불러오지 못했습니다. 인터넷 연결을 확인해 주세요'); });
  return a;
}
// 장이 끝나면 다음 장으로 (브라우저가 mp3 끝을 늦게 알아차리는 때가 있어 장 길이(dur)를 넘으면 끝난 것으로 봄)
function abNext() {
  if (!R || !R.ab || !AB.on || AB.ending === AB.ci) return; AB.ending = AB.ci;
  if (AB.ci < R.ab.chapters.length - 1) abPlay(AB.ci + 1, 0);
  else { AB.a.pause(); store.set('abpos-' + R.id, null); toast('오디오북을 끝까지 들었습니다'); abUi(); }
}
async function abLoad(url) {
  try { const j = await (await fetch(url)).json(); if (!R || !j.chapters || !j.chapters.length) return; R.ab = j; renderReader(); }
  catch (e) { return; }
  if (new URLSearchParams(location.search).get('audio')) { history.replaceState(history.state, '', location.pathname); abStart(); }
}
// 지금 화면 맨 위에 보이는 문단 → 오디오북 장·시간
function abFromView() {
  const chs = R.ab.chapters, body = $('#rBody'); let pg = R.i + 1, sv = -1;
  if (body && R.view === 'text') {
    const top = body.getBoundingClientRect().top + ($('#reader').classList.contains('chrome-off') ? 0 : ($('.r-top') || { offsetHeight: 0 }).offsetHeight);
    const el = [...$$('#rBody p[data-pg]')].find(e => e.getClientRects().length && e.getBoundingClientRect().bottom > top + 10);
    if (el) { pg = +el.dataset.pg; sv = +el.dataset.s; }
  }
  let ci = chs.findIndex(c => pg >= c.page && pg <= c.to);
  if (ci < 0) { ci = chs.findIndex(c => c.page > pg); if (ci < 0) ci = chs.length - 1; return { ci, t: 0 }; }
  const sy = chs[ci].sync; let k = 0;
  sy.forEach(([t, p, s], i) => { if (p < pg || (p === pg && s <= sv)) k = i; });
  return { ci, t: k ? sy[k][0] : 0, k };
}
function abStart() {
  if (!R || !R.ab) return;
  stopSpeak(true); AB.detached = false; AB.userAt = 0;
  try { const pa = $('#pAudio'); if (pa && !pa.paused) pa.pause(); } catch (e) {}  // 법문 바로 듣기가 나오고 있으면 멈춤
  const a = abA(), v = abFromView(), sv = store.get('abpos-' + R.id, null);
  // 같은 문단에서 멈췄던 곳이면 멈춘 그 초부터
  if (AB.on && a.src && AB.ci === v.ci && Math.abs(a.currentTime - v.t) < 600 && abIdx(R.ab.chapters[v.ci].sync, a.currentTime) === v.k) { a.play().catch(abBlocked); return; }
  if (sv && sv.ci === v.ci && abIdx(R.ab.chapters[v.ci].sync, sv.t) === v.k) v.t = sv.t;
  abPlay(v.ci, v.t);
}
function abStartAt(pg, sv, frac) {
  if (!R || !R.ab) return; if (AB.locked) return abLockedMsg();
  const chs = R.ab.chapters; let ci = chs.findIndex(c => pg >= c.page && pg <= c.to);
  if (ci < 0) { toast('이 부분은 오디오북에 들어 있지 않습니다'); return; }
  const sy = chs[ci].sync; let k = 0; sy.forEach(([t, p, s], i) => { if (p < pg || (p === pg && s <= sv)) k = i; });
  const exact = sy[k][1] === pg && sy[k][2] === sv, t0 = sy[k][0], t1 = k + 1 < sy.length ? sy[k + 1][0] : (chs[ci].dur || t0);
  // 한 문단이 소리 여러 조각이면(그림 글 등) 그대로 문단 처음부터, 한 조각이면 고른 글자 위치만큼 앞으로
  const t = exact && !(k + 1 < sy.length && sy[k + 1][1] === pg && sy[k + 1][2] === sv) ? t0 + Math.max(0, (t1 - t0 - 0.6) * (frac || 0)) : t0;
  stopSpeak(true); AB.detached = false; AB.userAt = 0;
  try { const pa = $('#pAudio'); if (pa && !pa.paused) pa.pause(); } catch (e) {}
  abPlay(ci, Math.max(0, t - (frac > 0.02 ? 1 : 0)));
}
const abBlocked = () => { abUi(); toast('▶ 단추를 누르면 오디오북이 시작됩니다'); };
function abPlay(ci, t) {
  const a = abA(), c = R.ab.chapters[ci];
  AB.on = true; AB.ci = ci; AB.k = -1; AB.ending = -1;
  if (a.dataset.u !== c.url) { a.dataset.u = c.url; a.src = c.url; }
  const seek = () => { try { a.currentTime = t || 0; } catch (e) {} };
  if (a.readyState >= 1) seek(); else a.addEventListener('loadedmetadata', seek, { once: true });
  a.playbackRate = +store.get('abrate', 1) || 1;
  abBar(); abMedia(c);
  a.play().catch(abBlocked);
  const el = $('#reader'); if (el) el.classList.add('ab-on');
}
const abIdx = (sy, t) => { let k = 0; for (let i = 0; i < sy.length && sy[i][0] <= t + 0.05; i++) k = i; return k; };
function abTick() {
  const a = AB.a; if (!AB.on || !R || !R.ab) return;
  const c = R.ab.chapters[AB.ci]; if (!c) return;
  if (c.dur && a.currentTime >= c.dur - 0.2 && !a.paused) { abNext(); return; }
  $('#abCur') && ($('#abCur').textContent = fmtT(a.currentTime));
  const sk = $('#abSeek'); if (sk && !sk._drag && a.duration && document.activeElement !== sk) sk.value = a.currentTime / a.duration * 1000;  // 커서가 막대에 있으면 움직이지 않음 — 화면 낭독기와 소리 겹침 방지 (2026-11-17)
  if (Date.now() - AB.saved > 5000) abSave();
  const k = abIdx(c.sync, a.currentTime), moved = k !== AB.k; AB.k = k;
  const [, p] = c.sync[k];
  // 읽는 분이 직접 넘기지 않았으면 글도 따라감 — 듣는 곳이 다른 장이면 그 장을 열고, 듣는 문단이 화면 밖이면 그리로 (멈췄다가 8초 지나면 다시 따라감)
  const free = Date.now() - AB.userAt > 8000 && !AB.detached;
  if (R.view === 'text' && free && chapterOf(p) !== chapterOf(R.i + 1)) { R.chForce = null; R.i = p - 1; renderReader(); return; }
  if (moved) abMark(free); else if (free) abMark(true, true);
}
// 지금 문단 안에서 얼마나 읽었는지 (0~1) — 긴 문단은 읽는 만큼 글을 올려 줌
function abFrac() { const c = R.ab.chapters[AB.ci], sy = c.sync, k = AB.k, t0 = sy[k][0], t1 = k + 1 < sy.length ? sy[k + 1][0] : (c.dur || t0 + 1); return Math.min(1, Math.max(0, (AB.a.currentTime - t0) / Math.max(1, t1 - t0))); }
function abMark(follow, keep) {
  if (!AB.on || !R || !R.ab || AB.k < 0) return;
  const c = R.ab.chapters[AB.ci]; if (!c || !c.sync[AB.k]) return;
  const [, p, s] = c.sync[AB.k];
  const el = s < 0 ? $('#rBody .ch-head h3') : $(`#rBody [data-pg="${p}"][data-s="${s}"]`);
  if (!keep || !el || !el.classList.contains('ab-now')) { $$('.ab-now').forEach(x => x.classList.remove('ab-now')); if (el) el.classList.add('ab-now'); }
  if (!el) return;
  if (!follow || !el.getClientRects().length) return;
  const body = $('#rBody'), br = body.getBoundingClientRect(), r = el.getBoundingClientRect();
  const topPad = $('#reader').classList.contains('chrome-off') ? 12 : ($('.r-top') || { offsetHeight: 0 }).offsetHeight + 12;
  const bar = $('#abBar'), botPad = (bar ? bar.offsetHeight : 0) + 24;
  const view = br.height - topPad - botPad, top0 = br.top + topPad;
  if (r.height > view * 0.6) {  // 화면보다 긴 문단: 지금 읽는 줄쯤(문단 안 진행 정도)이 화면 위쪽 1/4 에 오게
    const y = r.top + r.height * abFrac();
    if (y < top0 || y > top0 + view * 0.7) body.scrollTo({ top: body.scrollTop + y - top0 - view * 0.25, behavior: 'smooth' });
    return;
  }
  if (keep ? (r.bottom < top0 || r.top > top0 + view - 20) : (r.top < top0 || r.bottom > top0 + view)) body.scrollTo({ top: body.scrollTop + r.top - top0 - Math.max(0, view * 0.15), behavior: 'smooth' });
}
function abSave() { if (!AB.on || !R || !AB.a) return; AB.saved = Date.now(); const c = R.ab && R.ab.chapters[AB.ci]; store.set('abpos-' + R.id, { ci: AB.ci, t: Math.round(AB.a.currentTime), b: R.title, ch: c ? c.title : '', d: new Date().toISOString().slice(0, 10), ts: Date.now() }); }  // b·ch·d 는 단순 화면 내 서재 '이어 듣기' 줄에 씀
function abStop() { if (!AB.a) return; if (AB.locked) abSetLock(false); abSave(); AB.a.pause(); AB.on = false; AB.k = -1; $$('.ab-now').forEach(x => x.classList.remove('ab-now')); const b = $('#abBar'); if (b) b.remove(); const el = $('#reader'); if (el) el.classList.remove('ab-on'); }
function abBar() {
  let b = $('#abBar');
  if (!b) {
    b = document.createElement('div'); b.id = 'abBar'; b.className = 'ab-bar'; b.setAttribute('role', 'region'); b.setAttribute('aria-label', '오디오북 재생기');
    b.innerHTML = `<div class="ab-ctr"><button id="abBack" aria-label="15초 뒤로" data-tip="15초 뒤로">↺15</button><button id="abPlay" class="main" aria-label="재생">▶</button><button id="abFwd" aria-label="15초 앞으로" data-tip="15초 앞으로">15↻</button></div>
      <div class="ab-mid"><div class="ab-t" id="abTitle"></div><div class="ab-row"><span id="abCur">0:00</span><input type="range" id="abSeek" min="0" max="1000" value="0" aria-label="재생 위치"><span id="abDur">0:00</span></div></div>
      <div class="ab-opt"><select id="abRate" aria-label="빠르기" data-tip="듣는 빠르기">${[0.8, 1, 1.2, 1.5, 1.8, 2, 2.2, 2.5].map(v => `<option value="${v}">${v}배</option>`).join('')}</select><button id="abHere" data-tip="듣는 곳으로: 지금 소리로 읽고 있는 문단으로 글을 옮기고, 다시 글이 소리를 따라가게 합니다" aria-label="듣는 곳으로 — 지금 읽고 있는 문단으로 글을 옮김">📍</button><button id="abLock" data-tip="잠금: 실수로 멈추거나 닫히지 않게, 화면도 꺼지지 않게" aria-label="잠그기" aria-pressed="false">🔓</button><button id="abClose" data-tip="오디오북 닫기" aria-label="오디오북 닫기">✕</button></div>`;
    document.body.appendChild(b);
    // 재생 바의 빈 곳(제목·시간 글자 등)을 누르면 글을 누를 때처럼 위 메뉴·아래 바가 나타나거나 숨음 — 휴대폰에서 화면 아래쪽은 재생 바가 덮고 있어서 (운영자 요청, 2026-11-10)
    b.addEventListener('click', e => { if (e.target.closest('button,input,select,label')) return; const el = $('#reader'); if (!el) return; if (el.classList.toggle('chrome-off')) $$('.panel', el).forEach(x => x.classList.remove('open')); });
    const a = abA();
    const L = f => (...x) => AB.locked ? abLockedMsg() : f(...x);
    $('#abLock').onclick = () => abSetLock(!AB.locked);
    $('.ab-row', b).addEventListener('pointerdown', () => { if (AB.locked) abLockedMsg(); });
    $('#abPlay').onclick = () => AB.locked ? abLockedMsg() : a.paused ? (AB.on ? a.play().catch(abBlocked) : abStart()) : a.pause();
    $('#abBack').onclick = L(() => { a.currentTime = Math.max(0, a.currentTime - 15); });
    $('#abFwd').onclick = L(() => { a.currentTime = Math.min((a.duration || 1e9) - 1, a.currentTime + 15); });
    $('#abRate').value = String(store.get('abrate', 1)); $('#abRate').onchange = e => { if (AB.locked) { e.target.value = String(a.playbackRate); return abLockedMsg(); } a.playbackRate = +e.target.value; store.set('abrate', +e.target.value); };
    const sk = $('#abSeek');
    sk.oninput = () => { sk._drag = true; if (a.duration) $('#abCur').textContent = fmtT(a.duration * sk.value / 1000); };
    sk.onchange = () => { sk._drag = false; if (a.duration) a.currentTime = a.duration * sk.value / 1000; AB.userAt = 0; };
    $('#abHere').onclick = () => { AB.userAt = 0; AB.detached = false; AB.k = -1; abTick(); };
    $('#abClose').onclick = L(() => { abStop(); if (R) renderReader(); });
    a.addEventListener('loadedmetadata', () => { const d = $('#abDur'); if (d) d.textContent = fmtT(a.duration); });
  }
  const c = R.ab.chapters[AB.ci];
  $('#abTitle').textContent = `${AB.ci + 1}/${R.ab.chapters.length} · ${c.title}`;
  $('#abDur').textContent = fmtT(c.dur);
  abUi();
}
function abUi() {
  const a = AB.a, pb = $('#abPlay'); if (pb && a) { pb.textContent = a.paused ? '▶' : '❚❚'; pb.setAttribute('aria-label', a.paused ? '재생' : '일시정지'); }
  const rb = $('#rAb'); if (rb && a) { const on = AB.on && !a.paused; rb.classList.toggle('on', on); rb.textContent = on ? '❚❚ 오디오북' : '🎧 오디오북'; }
}
// 잠금 화면·이어폰·블루투스 단추로 조절
function abMedia(c) {
  if (!('mediaSession' in navigator)) return;
  const ms = navigator.mediaSession, a = abA(), h = (k, f) => { try { ms.setActionHandler(k, f); } catch (e) {} };
  try { ms.metadata = new MediaMetadata({ title: c.title, artist: R.title + (R.by ? ' · ' + R.by : ''), album: '붓다담마 법보시 도서관 · 오디오북', artwork: R.cover ? [{ src: R.cover, sizes: '512x512' }] : [{ src: '/images/icon-512.png', sizes: '512x512', type: 'image/png' }] }); } catch (e) {}
  h('play', () => a.play()); h('pause', () => { AB.mediaPause = Date.now(); a.pause(); });
  h('seekbackward', d => { a.currentTime = Math.max(0, a.currentTime - ((d && d.seekOffset) || 15)); });
  h('seekforward', d => { a.currentTime = a.currentTime + ((d && d.seekOffset) || 15); });
  h('seekto', d => { if (d && d.seekTime != null) a.currentTime = d.seekTime; });
  h('previoustrack', () => { if (a.currentTime > 5 || AB.ci === 0) a.currentTime = 0; else abPlay(AB.ci - 1, 0); });
  h('nexttrack', () => { if (R && R.ab && AB.ci < R.ab.chapters.length - 1) abPlay(AB.ci + 1, 0); });
}
// 읽는 분이 직접 글을 넘기면 8초 동안은 따라가지 않음
['wheel', 'touchmove', 'keydown', 'pointerdown'].forEach(t => document.addEventListener(t, e => { if (AB.on && e.target && e.target.closest && e.target.closest('#reader')) AB.userAt = Date.now(); }, { passive: true }));
// 사이트 글자 크기 설정(body zoom 1.2·1.45)이 켜져 있으면 화면 좌표(getBoundingClientRect)와 CSS 좌표가 달라서, 떠 있는 창 자리를 정할 때 나눠 맞춤
function bodyZoom() { return parseFloat(getComputedStyle(document.body).zoom) || 1; }
// 짧은 안내 (data-tip): 마우스를 올리면, 손가락으로는 꾹 누르고 있으면(0.5초) 뜸 — 꾹 눌러 안내를 본 때는 단추가 눌리지 않음 (운영자 요청, 2026-11-10)
(() => {
  let tip = null, hold = null, held = null, hide = null;
  let cur = null, raf = 0;
  const place = () => {  // 단추 바로 위에 (손가락에 가리지 않게) — 화면 안에 다 보이게
    if (!cur || !tip.classList.contains('show')) return;
    if (!document.contains(cur)) { tip.classList.remove('show'); return; }
    tip.style.left = '0px'; tip.style.top = '0px';  // 먼저 왼쪽 위로 옮겨 재야 줄바꿈이 바르게 됨 (오른쪽 끝에서 재면 폭이 좁아져 아주 길어짐)
    // 사이트 글자 크기 설정(body zoom 1.2·1.45)이 켜져 있으면 화면 좌표와 CSS 좌표가 달라서 z 로 나눠 맞춤
    const z = bodyZoom();
    const r = cur.getBoundingClientRect(), tw = tip.offsetWidth * z, th = tip.offsetHeight * z;
    tip.style.left = Math.max(8, Math.min(innerWidth - tw - 8, r.left + r.width / 2 - tw / 2)) / z + 'px';
    tip.style.top = Math.max(4, Math.min(innerHeight - th - 4, r.top - th - 8 < 4 ? r.bottom + 8 : r.top - th - 8)) / z + 'px';
  };
  const loop = () => { place(); if (cur && tip.classList.contains('show')) raf = requestAnimationFrame(loop); };  // 재생 바가 위아래로 움직여도 따라감
  const show = t => {
    if (!tip) { tip = document.createElement('div'); tip.className = 'tipbox'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip); }
    tip.textContent = t.dataset.tip; tip.style.maxWidth = Math.min(280, (innerWidth - 16) / bodyZoom()) + 'px'; tip.classList.add('show');
    cur = t; cancelAnimationFrame(raf); loop();
  };
  document.addEventListener('mouseover', e => {
    const t = e.target.closest && e.target.closest('[data-tip]'); if (!t || !matchMedia('(hover:hover)').matches) return;
    show(t); t.addEventListener('mouseleave', () => tip.classList.remove('show'), { once: true });
  });
  // 아이폰(사파리)은 꾹 누르면 기기 자체 메뉴를 띄우며 touchcancel 을 보내므로, 손가락을 뗄 때(touchend)와 많이 움직일 때만 취소함
  let tx = 0, ty0 = 0;
  document.addEventListener('touchstart', e => {
    const t = e.target.closest && e.target.closest('[data-tip]'); clearTimeout(hold); if (!t) return;
    tx = e.touches[0].clientX; ty0 = e.touches[0].clientY;
    hold = setTimeout(() => { held = t; show(t); clearTimeout(hide); hide = setTimeout(() => tip.classList.remove('show'), 3500); }, 450);
  }, { passive: true });
  document.addEventListener('touchmove', e => { if (Math.abs(e.touches[0].clientX - tx) + Math.abs(e.touches[0].clientY - ty0) > 12) clearTimeout(hold); }, { passive: true });
  document.addEventListener('touchend', () => { clearTimeout(hold); if (held) setTimeout(() => { held = null; }, 700); }, { passive: true });
  document.addEventListener('click', e => { if (held && e.target.closest && e.target.closest('[data-tip]') === held) { e.preventDefault(); e.stopImmediatePropagation(); } held = null; }, true);
  document.addEventListener('contextmenu', e => { if (e.target.closest && e.target.closest('[data-tip]')) e.preventDefault(); });
})();
function stopSpeak(rerender) { TT.gen++; TT.jump = null; if (R) R.ttsSi = 0; try { speechSynthesis.cancel(); } catch (e) {} wake(false, 'tts'); if (R) { R.ttsTitled = null; R.ttsLocked = false; const was = R.speaking; R.speaking = false; if (rerender && was) renderReader(); } }
document.addEventListener('keydown', e => {
  // 열린 창 안에서 Tab 은 창 안에서만 돎 — 단축키 안내처럼 누를 것이 없는 창에서 Tab 을 누르면 커서가 엉뚱한 곳으로 가던 것 (운영자 요청, 2026-11-18)
  if (R && e.key === 'Tab' && !e.altKey && !e.ctrlKey && !e.metaKey) {
    const p = $('#reader .panel.open');
    if (p && p.contains(document.activeElement)) {
      const f = $$('button,a[href],input,select,textarea,summary,[tabindex="0"]', p).filter(x => !x.disabled && x.offsetParent !== null);
      if (f.length) { const i = f.indexOf(document.activeElement); if (e.shiftKey ? i <= 0 : i === -1 || i === f.length - 1) { e.preventDefault(); f[e.shiftKey ? f.length - 1 : 0].focus(); } }
      else { e.preventDefault(); }
      return;
    }
  }
  if (R && e.altKey && e.shiftKey && !e.ctrlKey && !e.metaKey && readerKey(e)) { e.preventDefault(); return; }
  if (!R || e.target.matches('input,select,textarea')) return;
  if (R.ttsLocked && e.key !== 'Tab') { if ([' ', 'ArrowRight', 'ArrowLeft', 'Escape'].includes(e.key)) { e.preventDefault(); toast('듣기가 잠겨 있습니다'); } return; }
  if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && (e.shiftKey || e.ctrlKey || e.altKey || e.metaKey)) return;  // Shift+→ 는 글 고르기
  if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && R.speaking) { e.preventDefault(); if (TT.jump) TT.jump(e.key === 'ArrowRight' ? 1 : -1); return; }  // 듣는 중에는 앞·다음 문장
  if (e.key === 'ArrowRight') go(R.i + 2); else if (e.key === 'ArrowLeft') go(R.i);
  else if (e.key === ' ' && $('#rSpeak') && !e.target.closest('button,a,summary,[role]')) { e.preventDefault(); R.speaking ? stopSpeak(true) : speak(); }
  else if (e.key === 'Escape') { if (document.fullscreenElement) return; if ($$('#reader .panel.open').length) closePanels(); else exitReader(); }
});

/* ---------- 내 서재 ---------- */
// 읽기 기록 (이 기기에만)
function saveHistory(n) {
  if (!R) return; const h = store.get('hist', []).filter(x => x.id !== R.id), c = chapters()[chapterOf(n)];
  h.unshift({ id: R.id, t: R.title, by: R.by, p: n, pl: (R.pages[n - 1] || {}).label || '', ch: c && c.title || '', pct: Math.round(n / R.pages.length * 100), first: (store.get('hist', []).find(x => x.id === R.id) || {}).first || today(), d: today(), ts: Date.now() });
  store.set('hist', h.slice(0, 100));
}
let notesTab = 'read';
const nPicked = new Set();
const pkBar = n => n > 1 ? `<div class="pk-bar"><button class="btn sm ghost" id="pkAll">모두 고르기</button> <button class="btn sm" id="pkDel" disabled>고른 것 지우기 (0개)</button><div id="pkAsk" class="pk-ask" role="alertdialog" aria-labelledby="pkQ" hidden></div></div>` : '';
function renderNotes() {
  const root = $('#notesRoot'); if (!root) return;
  const U = uls(), B = bms();
  const groups = {}; U.forEach(h => (groups[h.id] = groups[h.id] || []).push(h));
  const ulHtml = Object.keys(groups).length ? Object.entries(groups).map(([id, l]) => `<div class="book-group"><h3>『${esc(l[0].t)}』</h3><div class="small muted">${esc(l[0].by)} · 밑줄 ${l.length}개</div>
    ${l.sort((a, c) => a.p - c.p).map(h => `<div class="note-item"><div class="meta"><a href="/read/${id}/${h.p}">${esc(h.pl || h.p)}쪽에서 보기 →</a><span>${esc(h.d || '')}</span></div><div class="quote">${esc(h.text)}</div>${h.note ? `<div class="memo">메모: ${esc(h.note)}</div>` : ''}
    <div class="acts">${h.nc ? '' : `<button data-ncopy="${h.k}">출처와 함께 복사</button>`}<button data-ndel="${h.k}">지우기</button></div></div>`).join('')}</div>`).join('')
    : `<p class="muted">아직 밑줄이 없습니다. 읽기 화면에서 글을 끌어서 고르면 ‘밑줄 긋기’ 단추가 나옵니다.</p>`;
  const bmHtml = B.length ? B.map((m, k) => `<div class="note-item"><div class="meta"><a href="/read/${m.id}/${m.p}">『${esc(m.t)}』 ${esc(m.pl || m.p)}쪽 →</a><span>${esc(m.d || '')}</span></div>${m.note ? `<div class="memo">${esc(m.note)}</div>` : ''}<div class="acts"><button data-bdel="${k}">지우기</button></div></div>`).join('') : '<p class="muted">아직 책갈피가 없습니다.</p>';
 const H = store.get('hist', []);
  // 이어 듣기 (운영자 요청, 2026-11-19): TTS(기기 목소리)·오디오북·법문 듣던 곳 — 하나씩 지울 수 있음
  const LS = [], fmtT = t => { t = Math.floor(t || 0); const h = Math.floor(t / 3600), m = Math.floor(t / 60) % 60; return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(t % 60).padStart(2, '0'); };  // SH·sFmtT 는 이 함수보다 뒤에 있어 처음 그릴 때 쓸 수 없음
  try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i), m = /^dd-(ttspos|abpos)-(.+)$/.exec(k || ''); if (!m) continue; const v = JSON.parse(localStorage.getItem(k) || 'null'); if (!v || !v.b) continue;
    if (m[1] === 'ttspos') { if (v.p) LS.push({ ts: v.ts, d: v.d, del: 'tts:' + m[2], ic: '🔊', kind: 'TTS(기기 목소리)로 듣던 곳', t: `『${v.b}』`, w: `${v.ch || ''}${v.pl ? (v.ch ? ' · ' : '') + v.pl + '쪽' : ''}`, href: `/read/${m[2]}/${v.p}?listen=1&s=${v.s || 0}`, go: '이어 듣기' }); }
    else LS.push({ ts: v.ts, d: v.d, del: 'ab:' + m[2], ic: '🎧', kind: '오디오북', t: `『${v.b}』`, w: `${v.ch || ''}${v.ch ? ' · ' : ''}${fmtT(v.t)}부터`, href: `/read/${m[2]}/?audio=1`, go: '이어 듣기' }); } } catch (e) {}
  store.get('stalk-hist', []).forEach(h => { const pl = /\/simple\/talks\/([^/]+)\//.exec(h.p || ''); LS.push({ ts: h.ts, d: h.d, del: 'ep:' + h.a, ic: '🎙', kind: '법문', t: `「${h.t}」`, w: `${h.pl ? h.pl + ' · ' : ''}${fmtT(h.pos)}${h.dur ? ' / ' + fmtT(h.dur) : ''}`, href: pl ? `/dhammatalk/?pl=${pl[1]}` : '/dhammatalk/', go: '재생목록 열기', play: h.a }); });
  LS.sort((a, c) => (c.ts || Date.parse(c.d || '') || 0) - (a.ts || Date.parse(a.d || '') || 0));
  const lsHtml = LS.length ? LS.map(x => `<div class="note-item"><div class="meta"><span>${x.ic} ${esc(x.kind)}</span><span>${esc(x.d || '')}</span></div><div><b>${esc(x.t)}</b>${x.w ? ` <span class="small muted">${esc(x.w)}</span>` : ''}</div><div class="acts"><label class="pick"><input type="checkbox" data-pk="${esc(x.del)}"${nPicked.has(x.del) ? ' checked' : ''}> 고르기<span class="sr">: ${esc(x.t + ' ' + x.kind)}</span></label>${x.play ? `<a class="btn sm" href="${esc(x.href)}" role="button" data-lplay="${esc(x.play)}">이어 듣기</a> ` : ''}<a class="btn sm${x.play ? ' ghost' : ''}" href="${esc(x.href)}">${x.go}</a><button data-ldel="${esc(x.del)}" aria-label="${esc(x.t + ' ' + x.kind + ' 기록 지우기')}">기록 지우기</button></div></div>`).join('') : '<p class="muted">아직 듣던 책·법문이 없습니다. ‘▶ 듣기’나 오디오북·법문을 들으면 여기에 이어 들을 곳이 남습니다.</p>';
  const histHtml = H.length ? `<div class="hist">${H.map((x, k) => `<div class="hist-item"><a class="hist-cover" href="/book/${x.id}/" data-hc="${x.id}" aria-hidden="true" tabindex="-1"></a><div class="hist-body"><a class="hist-t" href="/book/${x.id}/">『${esc(x.t)}』</a><div class="small muted">${esc(x.by)}</div>
      <div class="hist-bar" aria-label="읽은 만큼 ${x.pct}%"><span style="width:${x.pct}%"></span></div>
      <div class="small">${esc(x.ch ? x.ch + ' · ' : '')}${esc(x.pl || x.p)}쪽 · ${x.pct}%</div>
      <div class="small muted">마지막으로 읽은 날 ${esc(x.d)}${x.first && x.first !== x.d ? ` · 처음 읽은 날 ${esc(x.first)}` : ''}</div>
      <div class="acts"><label class="pick"><input type="checkbox" data-pk="hist:${esc(x.id)}"${nPicked.has('hist:' + x.id) ? ' checked' : ''}> 고르기<span class="sr">: 『${esc(x.t)}』</span></label><a class="btn sm" href="/read/${x.id}/${x.p}">이어 읽기</a><button data-hdel="${k}">기록 지우기</button></div></div></div>`).join('')}</div>` : '<p class="muted">아직 읽은 책이 없습니다. 책 페이지에서 ‘온라인으로 읽기’를 누르면 여기에 모입니다.</p>';
  root.innerHTML = `<div class="tabs" role="tablist"><button role="tab" data-ntb="read" class="${notesTab === 'read' ? 'on' : ''}">읽은 책 ${H.length}</button><button role="tab" data-ntb="listen" class="${notesTab === 'listen' ? 'on' : ''}">이어 듣기 ${LS.length}</button><button role="tab" data-ntb="ul" class="${notesTab === 'ul' ? 'on' : ''}">밑줄 ${U.length}</button><button role="tab" data-ntb="bm" class="${notesTab === 'bm' ? 'on' : ''}">책갈피 ${B.length}</button><button role="tab" data-ntb="io" class="${notesTab === 'io' ? 'on' : ''}">옮기기</button></div>
   <div style="max-width:760px">${notesTab === 'read' ? pkBar(H.length) + histHtml : notesTab === 'listen' ? pkBar(LS.length) + lsHtml : notesTab === 'ul' ? (U.some(h => !h.nc) ? `<div style="margin:12px 0"><button class="btn sm ghost" id="copyAll">밑줄 모두 복사 (출처 포함)</button></div>` : '') + ulHtml : notesTab === 'bm' ? bmHtml :
    `<p>다른 기기로 옮길 때: 아래 ‘내보내기’로 복사한 글을 다른 기기의 이 칸에 붙여넣고 ‘가져오기’를 누르세요. 가져오면 이미 있는 것과 합쳐집니다.</p>
    <div style="display:flex;gap:8px;margin:10px 0"><button class="btn sm ghost" id="ioExport">내보내기 (복사)</button><button class="btn sm" id="ioImport">가져오기</button></div>
    <label for="ioText" class="small muted">붙여넣을 곳</label><textarea class="io" id="ioText"></textarea>`}</div>`;
  $$('[data-ntb]', root).forEach(b => b.onclick = () => { if (notesTab !== b.dataset.ntb) nPicked.clear(); notesTab = b.dataset.ntb; renderNotes(); });
  // 여러 개 골라 지우기 (운영자 요청, 2026-11-19) — 한꺼번에 지울 때는 한 번 더 물음
  const pkSync = () => { const n = nPicked.size, all = $$('[data-pk]', root); const g = $('#pkDel', root), a = $('#pkAll', root); if (g) { g.textContent = `고른 것 지우기 (${n}개)`; g.disabled = !n; } if (a) a.textContent = n && n === all.length ? '모두 풀기' : '모두 고르기'; };
  $$('[data-pk]', root).forEach(c => c.onchange = () => { if (c.checked) nPicked.add(c.dataset.pk); else nPicked.delete(c.dataset.pk); pkSync(); });
  const pa = $('#pkAll', root); if (pa) pa.onclick = () => { const all = $$('[data-pk]', root), clear = nPicked.size && nPicked.size === all.length; all.forEach(c => { c.checked = !clear; if (clear) nPicked.delete(c.dataset.pk); else nPicked.add(c.dataset.pk); }); pkSync(); };
  const pd = $('#pkDel', root); if (pd) pd.onclick = () => {
    const n = nPicked.size; if (!n) return;
    const box = $('#pkAsk', root); box.hidden = false;
    const nms = $$('[data-pk]', root).filter(c => c.checked).map(c => ((c.closest('label') || {}).querySelector('.sr') || {}).textContent || '').map(t => t.replace(/^:\s*/, ''));
    box.innerHTML = `<span id="pkQ">고른 기록 ${n}개를 지울까요? ${esc(nms.slice(0, 6).join(', '))}${nms.length > 6 ? ` 외 ${nms.length - 6}개` : ''}.${ACC.token ? ' 로그인한 다른 기기에서도 지워집니다.' : ''}</span> <button class="btn sm" id="pkYes">지우기</button> <button class="btn sm ghost" id="pkNo">그만두기</button>`;
    $('#pkNo', box).onclick = () => { box.hidden = true; pd.focus(); };
    $('#pkYes', box).onclick = () => { [...nPicked].forEach(sDelDo); nPicked.clear(); renderNotes(); toast(`기록 ${n}개를 지웠습니다`); const t = $(`[data-ntb="${notesTab}"]`, root); if (t) t.focus(); };
    box.onkeydown = e => { if (e.key === 'Escape') { e.preventDefault(); box.hidden = true; pd.focus(); } };
    $('#pkYes', box).focus();
  };
  pkSync();
  // 법문 이어 듣기 — 이 화면 아래 재생기에서 듣던 자리부터, 원래 재생목록의 다음 법문으로 이어짐 (운영자 요청, 2026-11-19)
  $$('[data-lplay]', root).forEach(b => b.onclick = ev => {
    ev.preventDefault();  // 오디오북 '이어 듣기'와 같은 단추 모양(a.btn) — 누르면 재생목록으로 가지 않고 이 화면 재생기에서 바로
    const a = b.dataset.lplay, h = store.get('stalk-hist', []).find(x => x.a === a); if (!h || !$('#pAudio')) return;
    if ((h.pos || 0) > store.get('ppos-' + a, 0)) store.set('ppos-' + a, h.pos);
    const e = { audio: a, title: h.t, plname: h.pl || '', sp: h.p || '' }, key = 'resume:' + a;
    playEp(key, 0, [e]);
    if (h.p) fetch(h.p).then(r => r.ok ? r.text() : '').then(t => {
      if (!t || PL.pl !== key) return;
      const d = new DOMParser().parseFromString(t, 'text/html');
      const list = [...d.querySelectorAll('.s-list > li.k-ep')].map(x => { const l = x.querySelector('a'); return { audio: l ? new URL(l.getAttribute('href'), location.href).href : '', title: x.dataset.t || '', plname: x.dataset.pl || '', sp: h.p }; });
      const i = list.findIndex(x => x.audio === new URL(a, location.href).href); if (i < 0) return;
      list[i] = e; PL.list = list; PL.i = i;
    }).catch(() => {});
  });
  $$('[data-ldel]', root).forEach(b => b.onclick = () => { sDelDo(b.dataset.ldel); renderNotes(); toast('듣던 기록을 지웠습니다'); const t = $('[data-ntb="listen"]', root); if (t) t.focus(); });
  $$('[data-hdel]', root).forEach(b => b.onclick = () => { const h = store.get('hist', []); h.splice(+b.dataset.hdel, 1); store.set('hist', h); renderNotes(); });
  if ($('[data-hc]', root)) data().then(D => $$('[data-hc]', root).forEach(a => { const bk = D.books.find(x => x.id === a.dataset.hc); if (bk && bk.cover) a.innerHTML = `<img src="${esc(bk.cover)}" alt="">`; })).catch(() => {});
  $$('[data-ndel]', root).forEach(b => b.onclick = () => { store.set('ul', uls().filter(x => x.k !== +b.dataset.ndel)); renderNotes(); toast('밑줄을 지웠습니다'); });
  $$('[data-ncopy]', root).forEach(b => b.onclick = () => { const h = uls().find(x => x.k === +b.dataset.ncopy); copy(`“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽 (${SITE})`, '출처와 함께 복사했습니다'); });
  $$('[data-bdel]', root).forEach(b => b.onclick = () => { const l = bms(); l.splice(+b.dataset.bdel, 1); store.set('bm', l); renderNotes(); });
  const ca = $('#copyAll'); if (ca) ca.onclick = () => copy(uls().filter(h => !h.nc).map(h => `“${h.text}” — ${h.by}, 『${h.t}』 ${h.pl || h.p}쪽${h.note ? `\n  메모: ${h.note}` : ''}`).join('\n\n') + `\n\n(${SITE})`, '밑줄을 모두 복사했습니다');
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

/* ---------- 회원 (독서 기록 이어 보기) ---------- */
// 이어 보는 것: 책갈피(bm)·밑줄(ul)·내 서재 기록(hist)·읽던 쪽(pos-)·법문 재생 위치(ppos-·plast·pl·sub-)
const SYNC_RE = /^(bm|ul|hist|plast|pl|pos-.+|ppos-.+|sub-.+|ttspos-.+|abpos-.+|stalk-hist)$/;  // ttspos-·abpos-·stalk-hist: TTS·오디오북·법문 이어 듣기도 (운영자 요청, 2026-11-18)
const ACC = { get token() { try { return localStorage.getItem('dd-acct') || ''; } catch (e) { return ''; } }, get id() { try { return localStorage.getItem('dd-acct-id') || ''; } catch (e) { return ''; } } };
const syncT = () => { try { return JSON.parse(localStorage.getItem('dd-synct') || '{}'); } catch (e) { return {}; } };
let syncTimer = null;
function syncMark(k) {
  if (!SYNC_RE.test(k)) return;
  try { const m = syncT(); m[k] = Date.now(); localStorage.setItem('dd-synct', JSON.stringify(m)); } catch (e) {}
  if (!ACC.token) return;
  // 듣는 자리(문단·초마다 바뀜)는 30초에 한 번만 보냄 — 떠날 때·화면을 끌 때는 바로 보냄(visibilitychange)
  const due = Date.now() + (/^(ttspos-|abpos-|stalk-hist)/.test(k) ? 30000 : 2500);
  if (syncTimer && syncNow._due && syncNow._due <= due) return;
  clearTimeout(syncTimer); syncNow._due = due; syncTimer = setTimeout(() => { syncTimer = null; syncNow._due = 0; syncNow(); }, due - Date.now());
}
async function acctApi(op, o = {}) {
  const r = await fetch('/api/account', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ op, token: ACC.token, ...o }), keepalive: op === 'sync' });
  let j = {}; try { j = await r.json(); } catch (e) {}
  if (j.relogin) acctClear();
  if (!r.ok || j.error) throw new Error(j.error || '연결이 잘 되지 않습니다. 잠시 뒤에 다시 해 주세요.');
  return j;
}
function acctSet(id, token) { try { localStorage.setItem('dd-acct', token); localStorage.setItem('dd-acct-id', id); localStorage.removeItem('dd-synced'); } catch (e) {} acctBtn(); }
function acctClear() { try { localStorage.removeItem('dd-acct'); localStorage.removeItem('dd-acct-id'); } catch (e) {} acctBtn(); }
function acctBtn() { const b = $('#acctBtn'); if (b) b.textContent = ACC.id ? '👤 ' + ACC.id : '로그인'; }
const LISTS = ['bm', 'ul', 'hist'];
let syncing = false;
async function syncNow() {
  if (!ACC.token || syncing) return; syncing = true;
  try {
    const m = syncT(), first = !localStorage.getItem('dd-synced'), data = {};
    for (let i = 0; i < localStorage.length; i++) {
      const lk = localStorage.key(i); if (!lk || !lk.startsWith('dd-')) continue;
      const k = lk.slice(3); if (!SYNC_RE.test(k)) continue;
      let v; try { v = JSON.parse(localStorage.getItem(lk)); } catch (e) { continue; }
      data[k] = { v, t: m[k] || 1 };
    }
    let j = await acctApi('sync', { data: first ? {} : data });
    if (first) {  // 이 기기에서 처음: 목록(책갈피·밑줄·내 서재)은 두 쪽을 합치고, 나머지는 더 나중 것
      const up = {};
      for (const [k, x] of Object.entries(data)) {
        const sv = j.data[k];
        if (LISTS.includes(k) && sv && Array.isArray(sv.v) && Array.isArray(x.v)) {
          const seen = new Set(sv.v.map(y => JSON.stringify(y))), add = x.v.filter(y => !seen.has(JSON.stringify(y)));
          if (add.length) up[k] = { v: sv.v.concat(add), t: Date.now() };
        } else if (!sv || x.t > sv.t) up[k] = x;
      }
      if (Object.keys(up).length) j = await acctApi('sync', { data: up });
      localStorage.setItem('dd-synced', '1');
    }
    // 저장소 쪽이 더 나중이면 이 기기에 씀
    const mm = syncT(); let changed = false;
    for (const [k, x] of Object.entries(j.data || {})) {
      if (!SYNC_RE.test(k)) continue;
      if (!(k in data) || x.t > (mm[k] || 0)) { const cur = localStorage.getItem('dd-' + k), nv = JSON.stringify(x.v); if (cur !== nv) { localStorage.setItem('dd-' + k, nv); changed = true; } mm[k] = x.t; }
    }
    localStorage.setItem('dd-synct', JSON.stringify(mm));
    if (changed && $('#app') && $('#app').dataset.page === 'mynotes') renderNotes();
  } catch (e) {} finally { syncing = false; }
}
// 다른 기기에서 바꾼 것을 가져오기: 페이지를 열 때·다시 볼 때. 떠날 때는 남은 것을 보냄
document.addEventListener('visibilitychange', () => { if (!ACC.token) return; if (document.visibilityState === 'visible') syncNow(); else if (syncTimer) { clearTimeout(syncTimer); syncTimer = null; syncNow(); } });

function initAccount() {
  const root = $('#acctRoot'); if (!root) return;
  const q = new URLSearchParams(location.search), rt = q.get('reset');
  const base = root.dataset.base || '/account/', simple = !!root.dataset.base;  // 단순 화면(/simple/account/)도 같은 화면을 씀 (운영자 요청, 2026-11-18)
  const goFocus = () => { if (!simple) return; setTimeout(() => { const h = $('h2, .acct-msg', root); if (h) { h.setAttribute('tabindex', '-1'); try { h.focus(); } catch (e) {} } }, 60); };  // 로그인·가입·로그아웃 뒤 바뀐 화면의 제목부터 낭독기가 읽게
  const msg = (t, err) => `<div class="acct-msg${err ? ' err' : ''}" role="${err ? 'alert' : 'status'}">${esc(t)}</div>`;  // 화면 낭독기가 안내 글을 바로 읽음 (2026-11-17)
  const codeBox = c => `<div class="acct-code"><b>${esc(c)}</b><button class="tbtn sm" data-copy="${esc(c)}">복사</button></div>
    <div class="acct-warn">⚠ 이 <b>복구 코드</b>는 비밀번호를 잊었을 때 쓰는 열쇠입니다. <b>만들어지는 지금 한 번만 표시</b>되고, 이 화면을 벗어나면 다시 볼 수 없습니다. 운영자도 볼 수 없어 알려 드릴 수 없으니, <b>사진을 찍거나 적어서 잘 보관</b>하세요.</div>`;
  const bindCopy = () => $$('[data-copy]', root).forEach(b => b.onclick = () => copy(b.dataset.copy, '복사했습니다'));
  const form = (id, html, btn) => `<form id="${id}" class="acct-form">${html}<button class="btn" type="submit">${btn}</button><div class="out"></div></form>`;
  const F = (name, label, type = 'text', extra = '') => `<label>${label}<input name="${name}" type="${type}" ${extra}></label>`;
  const on = (id, fn) => { const f = $('#' + id, root); if (!f) return; f.onsubmit = async ev => { ev.preventDefault(); const o = Object.fromEntries(new FormData(f)); const out = $('.out', f), btn = $('button[type=submit]', f); btn.disabled = true; out.innerHTML = ''; try { await fn(o, out); } catch (e) { out.innerHTML = msg(e.message, true); } btn.disabled = false; }; };
  const IDH = 'autocomplete="username" required minlength="2" maxlength="20"', PWH = 'autocomplete="new-password" required minlength="8"';

  if (rt) {  // 이메일 링크로 왔을 때
    root.innerHTML = `<h2>새 비밀번호 정하기</h2>${form('fReset', F('pw', '새 비밀번호 (8자 이상)', 'password', PWH) + F('pw2', '새 비밀번호 한 번 더', 'password', PWH), '비밀번호 바꾸기')}`;
    on('fReset', async (o, out) => { if (o.pw !== o.pw2) throw new Error('두 비밀번호가 같지 않습니다.'); const j = await acctApi('reset_pw', { rt, pw: o.pw }); acctSet(j.id, j.token); history.replaceState(null, '', base); syncNow(); initAccount(); goFocus(); toast('새 비밀번호로 바꾸고 로그인했습니다'); });
    return;
  }
  if (ACC.token) {  // 로그인한 상태
    root.innerHTML = `<p class="muted">불러오는 중…</p>`;
    acctApi('me').then(me => {
      root.innerHTML = `<div class="acct-card"><h2>👤 ${esc(me.id)}</h2><p class="small muted">가입한 날: ${esc(me.created ? new Date(me.created).toLocaleDateString('ko-KR') : '')} · 이메일: ${me.hasEmail ? esc(me.email) : '넣지 않음'}</p>
        <p>이 기기의 책갈피·밑줄·읽던 곳·내 서재가 이 아이디에 저장되고, 다른 기기에서 같은 아이디로 로그인하면 이어집니다.</p>
        <div class="row"><button class="btn" id="aSync">지금 맞추기</button><button class="tbtn" id="aOut">로그아웃</button></div><div id="aSyncOut"></div></div>
        <details class="acct-more"><summary>비밀번호 바꾸기</summary>${form('fPw', F('pw', '지금 비밀번호', 'password', 'autocomplete="current-password" required') + F('newPw', '새 비밀번호 (8자 이상)', 'password', PWH), '바꾸기')}</details>
        <details class="acct-more"><summary>이메일 (아이디·비밀번호 찾기용, 선택)</summary><p class="small">이메일을 넣어 두면 아이디나 비밀번호를 잊었을 때 메일로 찾을 수 있습니다. 아이디·비밀번호 찾기 메일을 보낼 때만 쓰고 다른 곳에 쓰지 않습니다. 비우고 저장하면 지워집니다.</p>${me.mail ? '' : '<p class="small muted">(지금은 메일 보내기가 준비 중이라, 복구 코드로 찾아 주세요.)</p>'}${form('fMail', F('email', '이메일', 'email', 'autocomplete="email"') + F('pw', '지금 비밀번호', 'password', 'autocomplete="current-password" required'), '저장')}</details>
        <details class="acct-more"><summary>복구 코드 새로 받기</summary><p class="small">복구 코드를 잃어버렸으면 새로 받으세요. 예전 코드는 못 쓰게 됩니다. 새 코드도 <b>만들어지는 순간 한 번만 표시</b>되니 잘 보관하세요.</p>${form('fCode', F('pw', '지금 비밀번호', 'password', 'autocomplete="current-password" required'), '새 복구 코드 받기')}</details>
        <details class="acct-more"><summary>회원 탈퇴</summary><p class="small">아이디와 저장소의 기록이 모두 지워집니다(이 기기에 있는 기록은 남습니다). 되돌릴 수 없습니다.</p>${form('fDel', F('pw', '지금 비밀번호', 'password', 'autocomplete="current-password" required'), '탈퇴하기')}</details>`;
      $('#aSync').onclick = async () => { await syncNow(); $('#aSyncOut').innerHTML = msg('맞췄습니다. 다른 기기의 기록도 이 기기에 들어왔습니다.'); };
      $('#aOut').onclick = async () => { try { await acctApi('logout'); } catch (e) {} acctClear(); initAccount(); goFocus(); toast('로그아웃했습니다. 이 기기의 기록은 그대로 남습니다'); };
      on('fPw', async (o, out) => { await acctApi('change_pw', o); out.innerHTML = msg('비밀번호를 바꿨습니다.'); });
      on('fMail', async (o, out) => { const j = await acctApi('set_email', o); out.innerHTML = msg(j.hasEmail ? '이메일을 저장했습니다.' : '이메일을 지웠습니다.'); });
      on('fCode', async (o, out) => { const j = await acctApi('new_code', o); out.innerHTML = codeBox(j.recovery); bindCopy(); });
      on('fDel', async (o) => { if (!confirm('정말 탈퇴할까요? 되돌릴 수 없습니다.')) return; await acctApi('delete', o); acctClear(); initAccount(); toast('탈퇴했습니다'); });
    }).catch(e => { root.innerHTML = msg(e.message, true); if (!ACC.token) initAccount(); });
    return;
  }
  root.innerHTML = `<div class="tabs acct-tabs"><a href="#login" data-t="login" class="on">로그인</a><a href="#signup" data-t="signup">회원 가입</a><a href="#find" data-t="find">아이디·비밀번호 찾기</a></div><div id="acctPane"></div>`;
  const pane = t => {
    $$('[data-t]', root).forEach(a => { a.classList.toggle('on', a.dataset.t === t); if (a.dataset.t === t) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
    const P = $('#acctPane', root);
    if (t === 'login') P.innerHTML = form('fIn', F('id', '아이디', 'text', 'autocomplete="username" required') + F('pw', '비밀번호', 'password', 'autocomplete="current-password" required'), '로그인');
    if (t === 'signup') P.innerHTML = `<p class="small">아이디와 비밀번호만 있으면 됩니다. 이메일은 넣고 싶은 분만 넣으세요(아이디·비밀번호를 메일로 찾을 때만 씀). 가입하면 비밀번호를 잊었을 때 쓰는 <b>복구 코드</b>를 드립니다. 복구 코드는 <b>만들어지는 순간 한 번만 표시</b>되니 꼭 잘 보관하세요.</p>` +
      form('fUp', F('id', '아이디 (한글·영문·숫자 2~20자)', 'text', IDH) + F('pw', '비밀번호 (8자 이상)', 'password', PWH) + F('pw2', '비밀번호 한 번 더', 'password', PWH) + F('email', '이메일 (선택)', 'email', 'autocomplete="email"'), '가입하기');
    if (t === 'find') P.innerHTML = `<h2 class="acct-h">아이디를 잊었을 때</h2><p class="small">가입할 때(또는 나중에) 넣어 둔 이메일을 적으면, 그 이메일로 가입한 아이디를 메일로 알려 드립니다. 이메일을 넣지 않은 분은 아이디를 찾을 수 없습니다.</p>` +
      form('fFid', F('email', '이메일', 'email', 'autocomplete="email" required'), '아이디 메일로 받기') +
      `<h2 class="acct-h" style="margin-top:28px">비밀번호를 잊었을 때</h2><h3>① 복구 코드로 찾기</h3><p class="small">가입할 때 받은 복구 코드(예: K7QM-2XPA-9TZD)를 넣고 새 비밀번호를 정하세요.</p>` +
      form('fRc', F('id', '아이디', 'text', 'autocomplete="username" required') + F('code', '복구 코드', 'text', 'required autocomplete="off"') + F('pw', '새 비밀번호 (8자 이상)', 'password', PWH), '새 비밀번호로 바꾸기') +
      `<h3>② 이메일로 찾기</h3><p class="small">가입할 때(또는 나중에) 이메일을 넣어 둔 분만 쓸 수 있습니다. 새 비밀번호를 정하는 링크를 메일로 보내 드립니다.</p>` +
      form('fMr', F('id', '아이디', 'text', 'autocomplete="username" required'), '메일 보내기') +
      `<p class="small muted">둘 다 안 되면 계정을 되찾을 수 없습니다(운영자도 비밀번호·복구 코드를 볼 수 없습니다). 새로 가입해 주세요.</p>`;
    on('fIn', async o => { const j = await acctApi('login', o); acctSet(j.id, j.token); await syncNow(); toast(j.id + ' 님, 로그인했습니다'); initAccount(); goFocus(); });
    on('fUp', async (o, out) => { if (o.pw !== o.pw2) throw new Error('두 비밀번호가 같지 않습니다.'); const j = await acctApi('signup', { id: o.id, pw: o.pw, email: o.email }); acctSet(j.id, j.token); syncNow();
      root.innerHTML = `<div class="acct-card"><h2>가입했습니다 🙏</h2>${codeBox(j.recovery)}<div class="row"><a class="btn" href="${base}">다 적었습니다</a></div></div>`; bindCopy(); goFocus(); });
    on('fRc', async (o, out) => { const j = await acctApi('recover', o); acctSet(j.id, j.token); syncNow();
      root.innerHTML = `<div class="acct-card"><h2>비밀번호를 바꿨습니다</h2><p>예전 복구 코드는 이제 못 씁니다. 새 복구 코드를 적어 두세요.</p>${codeBox(j.recovery)}<div class="row"><a class="btn" href="${base}">다 적었습니다</a></div></div>`; bindCopy(); goFocus(); });
    on('fMr', async (o, out) => { const j = await acctApi('mail_reset', o); out.innerHTML = msg(j.msg); });
    on('fFid', async (o, out) => { const j = await acctApi('find_id', o); out.innerHTML = msg(j.msg); });
  };
  $$('[data-t]', root).forEach(a => a.onclick = ev => { ev.preventDefault(); pane(a.dataset.t); if (simple) { const f = $('#acctPane input, #acctPane h3', root); if (f) { if (!f.matches('input')) f.setAttribute('tabindex', '-1'); f.focus(); } } });  // 단순 화면: 고른 칸의 첫 입력 칸으로
  pane((location.hash || '#login').slice(1).replace(/[^a-z]/g, '') || 'login');
}

/* ---------- 시작 ---------- */
// 인터넷 없이 읽기 (서비스 워커)
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) navigator.serviceWorker.register('/sw.js').catch(() => {});

/* ---------- 앱으로 설치하기 안내 (운영자 요청, 2026-11-09) ----------
   처음 오신 분에게만 아래쪽에 작게 보이고, '닫기'나 설치를 하면 다시 보이지 않음.
   안드로이드·컴퓨터(크롬·엣지·삼성 인터넷): 누르면 바로 설치 창 / 아이폰·아이패드: '홈 화면에 추가' 방법 안내 */
(() => {
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  const ios = /iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  // 컴퓨터에서만 안내 (운영자 요청, 2026-11-10: 휴대폰·태블릿은 갤럭시 자동 차단 등으로 헷갈려서 안내하지 않음)
  if (ios || /Android|Mobile|Tablet|SamsungBrowser/i.test(navigator.userAgent)) { const bx = $('#installBox'); if (bx) bx.remove(); return; }
  let ev = null;
  const guideText = () => {
    const mob = /Android/i.test(navigator.userAgent), sam = /SamsungBrowser/i.test(navigator.userAgent);
    return sam ? '아래쪽 <b>⋮(또는 ≡) 메뉴 → ‘현재 페이지 추가’ → ‘홈 화면’</b>을 누르세요. 홈 화면에 도서관 아이콘이 생겨요. (갤럭시의 ‘보안 위험 자동 차단’이 켜져 있으면 ‘앱 설치’는 ‘안전하지 않은 앱 설치 차단됨’으로 막히지만, 이 방법은 막히지 않아요.)'
      : ios ? '아래쪽(아이패드는 위쪽)의 <b>공유 단추 □↑</b>를 누르고 → <b>‘홈 화면에 추가’</b>를 고르세요. 그러면 홈 화면에 도서관 아이콘이 생겨요.'
      : mob ? '브라우저 오른쪽 위 <b>⋮ 메뉴</b> → <b>‘앱 설치’</b> 또는 <b>‘홈 화면에 추가’</b>를 누르세요.'
      : '이 컴퓨터에 <b>이미 설치되어 있으면</b> 설치 창이 뜨지 않아요 — 주소창 오른쪽의 <b>‘앱에서 열기’ 아이콘</b>이나 바탕화면·시작 메뉴의 <b>‘법보시 도서관’</b>으로 여세요. 아직 설치하지 않았다면 오른쪽 위 <b>⋮ 메뉴 → ‘전송, 저장, 공유’ → ‘페이지를 앱으로 설치’</b>를 누르세요.';
  };
  // 설치 창을 띄워 보고, 안 뜨거나 취소하면 메뉴로 설치하는 방법을 보여 줌 → true: 설치함
  const tryInstall = async showGuide => {
    if (ev && !/SamsungBrowser/i.test(navigator.userAgent)) { const e0 = ev; ev = null; try { await e0.prompt(); const r = await e0.userChoice; if (r && r.outcome === 'accepted') return true; } catch (e) {} }
    showGuide(guideText()); return false;
  };
  const off = () => { store.set('install-off', true); const b = $('#installBar'); if (b) b.remove(); };
  // 내 서재의 '앱 설치' 칸 (운영자 요청, 2026-11-10): 처음 안내 띠를 닫았어도 여기서 설치.
  // 브라우저가 '설치할 수 있다'고 알려 줄 때(beforeinstallprompt)만 단추가 생김 → 이미 설치한 컴퓨터에는 안 보이고, 앱을 지우면 다시 보임
  const box = $('#installBox');
  const showBox = () => {
    if (!box || standalone || $('#ibBox')) return;
    box.innerHTML = `<div class="install-box"><div><b>📲 앱으로 설치하기</b><p class="small muted ib-t">바탕화면·시작 메뉴에서 바로 열고, 한 번 읽은 책은 인터넷 없이도 볼 수 있어요.</p></div><button class="btn" id="ibBox">앱 설치</button></div>`;
    $('#ibBox').onclick = () => tryInstall(t => { $('.ib-t', box).innerHTML = t; }).then(ok => { if (ok) { box.innerHTML = '<p class="note">설치했습니다. 바탕화면·시작 메뉴의 ‘법보시 도서관’으로 여세요.</p>'; off(); } });
  };
  const barOk = !(standalone || store.get('install-off', false) || inApp() || /^\/(admin|read|study|mynotes)\b/.test(location.pathname));
  const show = () => {
    if (!barOk || $('#installBar')) return;
    const b = document.createElement('div'); b.id = 'installBar'; b.className = 'install-bar'; b.setAttribute('role', 'region'); b.setAttribute('aria-label', '앱으로 설치하기');
    b.innerHTML = `<span class="ib-t">📲 이 도서관을 휴대폰·컴퓨터에 <b>앱처럼 설치</b>하면 홈 화면에서 바로 열고, 읽은 책은 인터넷 없이도 볼 수 있어요.</span><span class="ib-b"><button class="btn" id="ibGo">설치하기</button><button class="tbtn" id="ibNo">닫기</button></span>`;
    document.body.appendChild(b);
    $('#ibNo').onclick = off;
    $('#ibGo').onclick = () => tryInstall(t => { $('.ib-t', b).innerHTML = t + ' 이미 설치하셨다면 이 안내는 닫으셔도 돼요.'; const g = $('#ibGo'); if (g) g.remove(); }).then(ok => ok && off());
  };
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); ev = e; show(); showBox(); });
  window.addEventListener('appinstalled', () => { off(); if (box) box.innerHTML = '<p class="note">설치했습니다. 홈 화면의 도서관 아이콘으로 여세요.</p>'; });
  if (ios && /Safari/i.test(navigator.userAgent) && !/CriOS|FxiOS|EdgiOS/i.test(navigator.userAgent)) setTimeout(show, 1500);
})();
if ('speechSynthesis' in window) speechSynthesis.addEventListener && speechSynthesis.addEventListener('voiceschanged', () => { const v = $('#ttsVoice'); if (v) v.innerHTML = voiceOptions(ttsOpt().voice); });
const SIMPLE_UI = document.body.classList.contains('simple-ui');  // 단순 화면에는 머리·재생기가 없음
if (!SIMPLE_UI) initHeader();
// 화면 낭독기가 페이지를 열면 위쪽 메뉴를 건너뛰고 본문 제목부터 읽게 (운영자 요청, 2026-11-17 — 모바일 카페처럼, 보이는 화면은 그대로)
//  - 보이지 않는 읽기 위치(커서)만 본문의 큰 제목(h1)에 둠. 메뉴는 없어지지 않고 위로 넘기면 들림.
(function focusMain() {
  const pg = document.body.dataset.page;
  if (location.hash || ['reader', 'search', 'members'].includes(pg) || document.body.classList.contains('simple-ui')) return;  // 단순 화면은 initSimple 이 커서를 둠  // 주소에 #자리가 있거나, 스스로 커서를 두는 화면은 그대로
  const h = $('main h1'); if (!h) return;
  // 처음 온 기기: 본문 제목 바로 앞에 '시각장애인용 단순 모드로 보기'를 두고 커서를 거기에 — 낭독기가 맨 먼저 읽고, ↓·Tab 이면 본문 제목으로 (운영자 요청, 2026-11-18). 화면에는 보이지 않음
  const ask = !store.get('ui', '') && !store.get('ui-asked', false) && document.body.dataset.simple;
  const go = () => {
    if (document.activeElement && document.activeElement !== document.body) return;
    if (ask) {
      store.set('ui-asked', true);
      const a = document.createElement('a'); a.className = 'skip quiet'; a.href = document.body.dataset.simple + '?ui=simple'; a.dataset.ui = 'simple';
      a.textContent = '시각장애인용 단순 모드로 보기. Enter 를 누르면 바뀝니다.';
      a.addEventListener('blur', () => a.classList.remove('quiet'), { once: true });
      h.parentNode.insertBefore(a, h); try { a.focus({ preventScroll: true }); return; } catch (e) {}
    }
    // 본문 제목 바로 다음에도 숨은 '단순 모드로 보기' — 제목부터 읽다가 첫 Tab 이 늘 이 링크 (운영자 요청, 2026-11-18)
    if (document.body.dataset.simple && !$('.ui-after')) { const a = document.createElement('a'); a.className = 'skip ui-after'; a.href = document.body.dataset.simple + '?ui=simple'; a.dataset.ui = 'simple'; a.textContent = '시각장애인용 단순 모드로 보기'; h.after(a); }
    h.setAttribute('tabindex', '-1'); h.classList.add('auto-focus'); try { h.focus({ preventScroll: true }); } catch (e) {}
  };
  if (document.readyState === 'complete') go(); else window.addEventListener('load', go, { once: true });
})();
if (!SIMPLE_UI) { initPlayer(); initPage(); }
if (ACC.token) syncNow();
// 방문 통계: 기기마다 무작위 번호만 (개인정보 없음). 관리자 기기(통계에서 빼기)는 보내지 않음
try {
  if (navigator.sendBeacon && location.protocol === 'https:' && !store.get('notrack', false) && !/^\/(admin|api)\b/.test(location.pathname)) {
    let v = store.get('vid', ''); if (!/^[0-9a-z]{8,24}$/.test(v)) { v = Math.random().toString(36).slice(2, 12) + Date.now().toString(36).slice(-4); store.set('vid', v); }
    navigator.sendBeacon('/api/hit', JSON.stringify({ p: location.pathname, t: document.title.replace(/\s*·\s*(?:테라와다불교|붓다담마) 법보시 도서관$/, ''), r: document.referrer, v }));
  }
} catch (e) {}

// 인쇄본에 풀이가 없는 각주 — 텍스트 JSON fn_site {번호: 설명} 의 사이트 안내 글을, 책 글과 헷갈리지 않게 '사이트 안내' 표시를 붙여 보임 (운영자 요청, 2026-11-19)
function fnSiteHtml(RB, n) {
  const t = RB && RB.fnSite && RB.fnSite[n]; if (!t) return '';
  return `<div class="fn-site" role="note"><p><span class="fn-site-tag">ⓘ 사이트 안내 —</span> ${esc(t)}</p></div>`;
}
/* ---------- 각주 번호를 누르면 각주 내용 보여주기 ---------- */
document.addEventListener('click', e => {
  const old = document.getElementById('fnPop');
  const back = e.target.closest && e.target.closest('.reflow .fn-no');
  if (back) {  // 쪽 끝 각주 번호 → 본문의 각주 번호 자리로
    e.preventDefault(); e.stopPropagation(); if (old) old.remove();
    const n = back.dataset.fnno, pgn = back.closest('[data-pg]').dataset.pg;
    const refs = [...document.querySelectorAll(`.reflow .fn-ref[data-fn="${CSS.escape(n)}"]`)];
    const ref = refs.find(r => r.closest('[data-pg]').dataset.pg === pgn) || refs.filter(r => +r.closest('[data-pg]').dataset.pg <= +pgn).pop() || refs[0];
    if (ref) { ref.scrollIntoView({ block: 'center' }); ref.classList.add('fn-here'); ref.focus({ preventScroll: true }); setTimeout(() => ref.classList.remove('fn-here'), 2000); }
    else toast('이 각주의 본문 자리가 다른 장에 있습니다');
    return;
  }
  const sup = e.target.closest && e.target.closest('.fn-ref');
  if (!sup) { if (old && !e.target.closest('#fnPop')) old.remove(); return; }
  e.preventDefault(); e.stopPropagation(); if (old) old.remove();
  const n = sup.dataset.fn, here = sup.closest('[data-pg]');
  const cands = [...document.querySelectorAll(`.fn-no[data-fnno="${CSS.escape(n)}"]`)];
  const tgt = (here && cands.find(x => x.closest('[data-pg]').dataset.pg === here.dataset.pg)) || cands[0];
  const pop = document.createElement('div'); pop.id = 'fnPop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '각주 ' + n);
  if (tgt) { const c = tgt.closest('p').cloneNode(true); c.removeAttribute('data-pg'); c.removeAttribute('data-s'); pop.innerHTML = `<div class="fnpop-h">각주 ${n}<button class="fnpop-x" aria-label="닫기">✕</button></div>`; c.querySelector('.fn-no') && c.querySelector('.fn-no').remove(); pop.appendChild(c);
    // 각주 바로 뒤에 붙은 표·그림·출처 줄(같은 쪽, 다음 각주 전까지)도 각주 창에 함께 — 각주는 끊어 보이지 않게 (운영자 요청, 2026-11-18: DL-0030 각주 112 표, DL-0023 각주 197·198, DL-0024 각주 176)
    const fp = tgt.closest('p'); for (let s = fp.nextElementSibling; s && s.dataset && s.dataset.pg === fp.dataset.pg && !s.classList.contains('fn') && s.matches('figure, .r-tbl, p'); s = s.nextElementSibling) { const x = s.cloneNode(true); x.removeAttribute('data-pg'); x.removeAttribute('data-s'); pop.appendChild(x); }
    const go = document.createElement('button'); go.className = 'link-btn small'; go.textContent = '각주 자리로 가기 ↓'; go.onclick = () => { pop.remove(); tgt.closest('p').scrollIntoView({ block: 'center' }); tgt.closest('p').classList.add('found'); setTimeout(() => tgt.closest('p').classList.remove('found'), 1600); }; pop.appendChild(go); }
  else {  // 각주 글이 지금 장에 없으면(다음 장 첫 쪽 등) 책 전체에서 가장 가까운 쪽의 각주 글을 찾아 보여 줌 (2026-11-11)
    const hp = here ? +here.dataset.pg : 1; let best = null;
    const RB = (R && R.pages) ? R : (document.getElementById('sRead') && typeof SR !== 'undefined' && SR.r) || null;  // 단순 화면은 SR.r (2026-11-18 검수: 미주를 못 찾던 것)
    for (const pgx of (RB && RB.pages) || []) for (const q of paras(pgx.text)) if (q.startsWith('[^' + n + ']:') && (!best || Math.abs(pgx.n - hp) < Math.abs(best.n - hp))) best = { n: pgx.n, q };
    pop.innerHTML = `<div class="fnpop-h">각주 ${n}<button class="fnpop-x" aria-label="닫기">✕</button></div>` + (best ? `<p>${(RB === R ? (f => f()) : withR)(() => phMark(boldMark(esc(best.q.replace(/^\[\^[^\]]+\]:\s*/, '')))))}</p>` : fnSiteHtml(RB, n) || '<p class="muted">이 각주의 풀이를 이 책에서 찾지 못했습니다.</p>');
  }
  parFnAdd(pop, n, null);
  document.body.appendChild(pop);
  const z = bodyZoom(), r = sup.getBoundingClientRect(), W = Math.min(420 * z, innerWidth - 24);
  pop.style.width = W / z + 'px'; pop.style.left = Math.max(12, Math.min(innerWidth - W - 12, r.left - W / 2)) / z + 'px';
  const below = r.bottom + 8, h = pop.offsetHeight * z;
  pop.style.top = (below + h < innerHeight - 8 ? below : Math.max(8, r.top - h - 8)) / z + 'px';
  fnPopOpen(pop, sup);
}, true);
// 각주 창을 열면 화면 낭독기 커서를 각주 내용으로 옮기고, ✕·Esc 로 닫으면 누른 각주 번호로 돌아옴 (운영자 요청, 2026-11-18 — 전에는 커서가 번호에 그대로 있어 낭독기가 각주 내용을 읽지 않았음)
function fnPopOpen(pop, opener) {
  pop._ret = opener; pop.setAttribute('aria-modal', 'false');
  pop.querySelector('.fnpop-x').onclick = () => fnPopClose(pop);
  const f = pop.querySelector('p:not(.muted)') || pop.querySelector('p') || pop;
  f.setAttribute('tabindex', '-1'); try { f.focus({ preventScroll: true }); } catch (e) {}
}
function fnPopClose(pop) {
  if (!pop) return; const r = pop._ret, had = pop.contains(document.activeElement);
  pop.remove(); if (had && r && r.isConnected) try { r.focus({ preventScroll: true }); } catch (e) {}
}
document.addEventListener('keydown', e => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && (e.target.classList.contains('fn-ref') || e.target.classList.contains('fn-no'))) { e.preventDefault(); e.target.click(); }
  const p = document.getElementById('fnPop'); if (!p) return;
  if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); fnPopClose(p); return; }
  if (e.key === 'Tab' && p.contains(document.activeElement)) {  // 창 안에서만 돎(내용 → ✕ → 단추들)
    const f = [...p.querySelectorAll('[tabindex="-1"], button, a[href]')].filter(x => x.offsetParent || x === document.activeElement);
    if (f.length) { const i = f.indexOf(document.activeElement); e.preventDefault(); f[(i + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus(); }
  }
}, true);
// 도서관 왼쪽 찾아보기 상자: 화면에 실제로 보이는 높이만큼만 — 페이지 맨 위에서도(머리글 아래에서 시작) 맨 아래 '형식'까지 상자 안에서 넘겨 볼 수 있게 (운영자 요청, 2026-11-11)
(() => {
  const d = document.querySelector('.lib>details'); if (!d) return;
  const fit = () => {
    if (innerWidth <= 520) { d.style.maxHeight = ''; return; }
    const z = parseFloat(getComputedStyle(document.body).zoom) || 1;
    const top = Math.max(d.getBoundingClientRect().top, 16 * z);
    d.style.maxHeight = Math.max(200, (innerHeight - top - 16 * z) / z) + 'px';
  };
  fit(); addEventListener('scroll', fit, { passive: true }); addEventListener('resize', fit);
})();

/* ---------- 사이트 통계: 실제로 읽은 쪽 수 (운영자 요청, 2026-11-12) ----------
   읽기 화면에서 한 쪽이 화면 가운데에 15초 넘게 머물면 '읽은 쪽' 하나로 셈 (같은 쪽은 한 번만).
   화면이 꺼져 있거나 5분 넘게 아무 손길이 없으면 세지 않음. 모아 두었다가 다른 화면으로 갈 때·1분마다 보냄.
   보내는 것: 책 번호·제목·읽은 쪽 수·기기 무작위 번호뿐 (관리자 기기는 보내지 않음) */
(() => {
  if (!navigator.sendBeacon || location.protocol !== 'https:') return;
  const READ_SEC = 15, IDLE = 300e3;
  let touched = Date.now(); const secs = {}, done = new Set(), pend = {};
  ['scroll', 'wheel', 'touchstart', 'keydown', 'mousemove', 'click'].forEach(t => addEventListener(t, () => { touched = Date.now(); }, { passive: true, capture: true }));
  // 단순 모드(시각장애인용) '온라인으로 읽기' 장 글 화면도 셈 — 화면(창) 위쪽 40% 자리의 쪽, 기록에 s:1 (운영자 요청, 2026-11-18)
  const simple = () => SIMPLE_UI && SR.r && SR.id && $('#sRead [data-pg]');
  const curPage = () => {
    if (simple()) { const y = innerHeight * 0.4; let pg = 0; for (const e of document.querySelectorAll('#sRead [data-pg]')) { const t = e.getBoundingClientRect(); if (!t.height || t.bottom < 0) continue; if (t.top > y) { if (!pg && t.top < innerHeight) pg = +e.dataset.pg; break; } pg = +e.dataset.pg; } return pg; }  // 글이 화면 아래쪽에서 시작하면(장 첫머리) 처음 보이는 쪽
    if (R.view !== 'text') return R.i + 1;
    const b = $('#rBody'); if (!b) return 0; const r = b.getBoundingClientRect();
    const y = r.top + r.height * 0.4; let pg = 0;  // 화면 위쪽 40% 자리에 있는 글의 쪽
    for (const e of b.querySelectorAll('[data-pg]')) { const t = e.getBoundingClientRect(); if (!t.height) continue; if (t.top > y) break; pg = +e.dataset.pg; }
    return pg;
  };
  const flush = () => {
    if (store.get('notrack', false)) { for (const k in pend) delete pend[k]; return; }
    let v = store.get('vid', ''); if (!/^[0-9a-z]{8,24}$/.test(v)) { v = Math.random().toString(36).slice(2, 12) + Date.now().toString(36).slice(-4); store.set('vid', v); }
    for (const id in pend) { const o = pend[id]; if (o.n) navigator.sendBeacon('/api/hit', JSON.stringify({ k: 'read', b: o.id, t: o.t, n: o.n, p: location.pathname, v, s: o.s })); delete pend[id]; }
  };
  setInterval(() => {
    if (document.visibilityState !== 'visible' || Date.now() - touched > IDLE) return;
    const sm = simple(); if (!sm && (!R || $('#reader') == null)) return;
    const id = sm ? SR.id : R.id, title = sm ? SR.title : R.title;
    const n = curPage(); if (!n) return; const k = id + ':' + n;
    if (done.has(k)) return;
    secs[k] = (secs[k] || 0) + 2;
    if (secs[k] >= READ_SEC) { done.add(k); const pk = id + (sm ? ':s' : ''); const o = pend[pk] || (pend[pk] = { id, n: 0, t: title || '', s: sm ? 1 : 0 }); o.n++; }
  }, 2000);
  setInterval(flush, 60e3);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flush(); });
  addEventListener('pagehide', flush);
})();
// '읽기 화면 복사 막기'(책 JSON no_copy)를 켠 책만 복사를 막음 — 글 고르기·밑줄·찾기는 그대로 (운영자 요청, 2026-11-12)
(() => {
  const inBook = () => { if (!R || !R.noCopy) return false; const sel = getSelection(); if (!sel || sel.isCollapsed || !sel.rangeCount) return false;
    const n = sel.getRangeAt(0).commonAncestorContainer, el = n.nodeType === 1 ? n : n.parentElement;
    return !!(el && el.closest('#reader') && !el.closest('input, textarea, [contenteditable="true"]')); };
  const stop = e => { if (e.target && e.target.closest && e.target.closest('input, textarea')) return; if (!inBook()) return; e.preventDefault(); try { e.clipboardData && e.clipboardData.setData('text/plain', ''); } catch (x) {} toast('이 책은 복사할 수 없습니다'); };
  document.addEventListener('copy', stop, true); document.addEventListener('cut', stop, true);
})();

// ---------- 원서 대조 (운영자 요청, 2026-11-15) ----------
// 짝 자료 /parallel/<ID>.<말>.json : groups[].ko = 한국어 문단 열쇠 '쪽 순번:문단 순번', or = 원서 문단 번호, s = 문장 짝(문단 열쇠·번호, 시작·끝 글자)
async function parEnsure() { if (R && R.par.length && R.parMode !== 'off' && !R.parD) { try { R.parD = await (await fetch('/parallel/' + R.id + '.' + R.par[0] + '.json')).json(); renderReader(); } catch (e) { R.parMode = 'off'; } } }
function parApply() {
  const body = $('#rBody'), rf = body && $('.reflow', body);
  if (!rf || !R || !R.par.length || R.parMode === 'off' || R.view === 'page') return;
  if (!R.parD) { parEnsure(); return; }
  const D = R.parD, O = D.orig, wide = innerWidth >= 900, ptx = {};
  const kText = key => { if (!(key in ptx)) { const [n, k] = key.split(':').map(Number); ptx[key] = (paras((R.pages[n - 1] || {}).text)[k]) || ''; } return ptx[key]; };
  const oHtml = (t, h) => boldMark(esc(t)).replace(/\[\^([^\]\s]+)\]/g, (m, n) => `<sup class="par-fn" role="button" tabindex="0" data-ofn="${n}" aria-label="${esc(lang)} 원서 각주 ${n}">${n}</sup>`).replace(/\n/g, '<br>');  // 원서 각주 번호 [^n] → 작은 위첨자, 누르면 원서 각주  // 원서 각주 번호 [^n] → 작은 위첨자
  const kHtml = t => fnMark(phMark(boldMark(esc(t.replace(/^## |^\^\^ |^:: |^>> |^\|\| |^\+\+ /gm, ''))))).replace(/\n/g, '<br>');
  const lang = { en: '영어', my: '미얀마어', pi: '빠알리어', th: '태국어' }[D.lang] || D.lang;
  rf.classList.add('par-on', R.parMode === 'para' && wide ? 'par2' : 'par1');
  if (R.parMode === 'para' && wide) rf.style.maxWidth = `calc(${R.mw}em * 2 + 3em)`;
  let shown = 0, lastPg = null;
  D.groups.forEach((g, gi) => {
    if (g.toc) { if (parToc(g, O, kText, oHtml, wide)) shown++; return; }
    const els = g.ko.map(k => { const [n, s] = k.split(':'); return $(`#rBody [data-pg="${n}"][data-s="${s}"]`); }).filter(Boolean);
    if (!els.length || !g.or.length) return;
    shown++;
    const last = els[els.length - 1];
    if (R.parMode === 'para') {
      const box = document.createElement('div'); box.className = 'par-or'; box.lang = D.lang; box.dataset.g = gi;
      box.innerHTML = g.or.map(i => { const o = O[i]; return `<p class="${o.k === 'h' ? 'par-h' : o.k === 'gl' ? 'par-gl' : o.k === 'cite' ? 'par-cite' : ''}">${oHtml(o.t)}</p>`; }).join('') + (O[g.or[0]].pg !== lastPg && !g.note ? `<span class="par-pg" aria-hidden="true">${esc(lang)} 원서 ${esc(O[g.or[0]].pg ? O[g.or[0]].pg + '쪽' : '')}${O[g.or[0]].pdf && O[g.or[0]].pdf !== O[g.or[0]].pg ? ` (PDF ${esc(O[g.or[0]].pdf)}쪽)` : ''}</span>` : '') + (g.note ? `<p class="par-note" lang="ko">※ ${esc(g.note)}</p>` : '');   // 원서와 순서가 다른 짝 메모 (운영자 요청, 2026-11-17 — DL-0005)
      lastPg = O[g.or[g.or.length - 1]].pg;
      const vis = els.filter(e => e.getClientRects().length);   // 장 제목과 같아 숨긴 글(ch-dup)은 빼고
      if (wide && vis.length) {   // 넓은 화면: 같은 줄 오른쪽 칸 (한국어 문단 수만큼 줄을 차지)
        vis.forEach(e => e.classList.add('par-k')); box.style.gridRow = `span ${vis.length}`;
        const mt = parseFloat(getComputedStyle(vis[0]).marginTop) || 0; if (mt) box.style.marginTop = mt + 'px';   // 소제목처럼 위 여백이 있는 문단과 첫 줄 높이를 맞춤
        vis[0].after(box);
      } else (vis[vis.length - 1] || last).after(box);
    } else {   // 문장마다: 한국어 문장 · 원서 문장을 번갈아 (한국어 문단은 숨기고, 소제목은 그대로)
      const heads = els.filter(e => e.classList.contains('sub-h') || e.classList.contains('ch-dup'));
      const box = document.createElement('div'); box.className = 'par-sent'; box.dataset.g = gi;
      box.innerHTML = g.s.map(p => {
        const ko = p.ko.map(([k, a, b]) => kText(k).slice(a, b)).join(' '), or = p.or.map(([i, a, b]) => O[i].t.slice(a, b)).join(' ');
        const onlyHead = p.ko.length && p.ko.every(([k]) => heads.some(e => `${e.dataset.pg}:${e.dataset.s}` === k));
        return onlyHead ? (or ? `<div class="ps ps-hd"><div class="ps-o" lang="${D.lang}">${oHtml(or)}</div></div>` : '') : `<div class="ps">${ko ? `<div class="ps-k">${kHtml(ko)}</div>` : ''}${or ? `<div class="ps-o" lang="${D.lang}">${oHtml(or)}</div>` : ''}</div>`;
      }).join('') + (g.note ? `<p class="par-note">※ ${esc(g.note)}</p>` : '');
      els.forEach(e => { if (!heads.includes(e)) e.classList.add('par-hide'); });
      last.after(box);
    }
  });
  if (!shown) return;
}

/* ---------- 원서 대조 중 각주: 한국어 각주 창에 원서 각주도, 원서 위첨자 번호를 누르면 원서 각주 (운영자 요청, 2026-11-17) ---------- */
function parFnAdd(pop, koN, origN) {
  if (!R || !R.parD || !R.parMode || R.parMode === 'off') return;
  const D = R.parD, O = D.orig || [];
  const i = origN != null ? O.findIndex(o => o.k === 'fn' && o.t.startsWith('[^' + origN + ']:')) : (D.fn && D.fn[koN] != null ? D.fn[koN] : -1);
  if (i < 0 || !O[i]) return;
  const lang = { en: '영어', my: '미얀마어', pi: '빠알리어', th: '태국어' }[D.lang] || D.lang;
  const m = O[i].t.match(/^\[\^([^\]]+)\]:\s*/), on = m ? m[1] : '';
  const box = document.createElement('div'); box.className = 'fnpop-or'; box.lang = D.lang;
  box.innerHTML = `<div class="fnpop-oh">${esc(lang)} 원서 각주 ${esc(on)}${O[i].pg ? ` · 원서 ${esc(O[i].pg)}쪽` : ''}</div><p>${boldMark(esc(O[i].t.replace(/^\[\^[^\]]+\]:\s*/, '')))}</p>`;
  pop.appendChild(box);
}
document.addEventListener('click', e => {
  const sup = e.target.closest && e.target.closest('.par-fn[data-ofn]');
  if (!sup) return;
  e.preventDefault(); e.stopPropagation();
  const old = document.getElementById('fnPop'); if (old) old.remove();
  const n = sup.dataset.ofn, lang = { en: '영어', my: '미얀마어', pi: '빠알리어', th: '태국어' }[(R && R.parD || {}).lang] || '';
  const pop = document.createElement('div'); pop.id = 'fnPop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', lang + ' 원서 각주 ' + n);
  pop.innerHTML = `<div class="fnpop-h">${esc(lang)} 원서 각주 ${esc(n)}<button class="fnpop-x" aria-label="닫기">✕</button></div>`;
  parFnAdd(pop, null, n);
  const box = pop.querySelector('.fnpop-or'); if (box) box.querySelector('.fnpop-oh').remove(), box.classList.add('only'); else pop.insertAdjacentHTML('beforeend', '<p class="muted">원서 각주를 찾지 못했습니다.</p>');
  // 짝지은 한국어 각주
  const D = R && R.parD; const oi = D ? (D.orig || []).findIndex(o => o.k === 'fn' && o.t.startsWith('[^' + n + ']:')) : -1;
  const kn = D && D.fn ? Object.keys(D.fn).find(k => D.fn[k] === oi) : null;
  if (kn) { const b = document.createElement('button'); b.className = 'link-btn small'; b.textContent = `한국어 각주 ${kn} 보기`; b.onclick = () => { const r = document.querySelector(`.reflow .fn-ref[data-fn="${CSS.escape(kn)}"]`); pop.remove(); if (r) r.click(); else toast('한국어 각주가 다른 장에 있습니다'); }; pop.appendChild(b); }
  document.body.appendChild(pop);
  const z = bodyZoom(), r = sup.getBoundingClientRect(), W = Math.min(420 * z, innerWidth - 24);
  pop.style.width = W / z + 'px'; pop.style.left = Math.max(12, Math.min(innerWidth - W - 12, r.left - W / 2)) / z + 'px';
  const below = r.bottom + 8, h = pop.offsetHeight * z;
  pop.style.top = (below + h < innerHeight - 8 ? below : Math.max(8, r.top - h - 8)) / z + 'px';
  fnPopOpen(pop, sup);
}, true);
document.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('par-fn')) { e.preventDefault(); e.target.click(); } });

// 차례 줄마다 원서 차례 제목(쪽 번호는 뺌) — 넓은 화면 '문단 나란히'는 오른쪽 칸, 그 밖은 줄 아래 (운영자 요청, 2026-11-17)
function parToc(g, O, kText, oHtml, wide) {
  const rowOf = (key, a) => {   // 차례 문단 안 글자 자리 → 그 줄의 .tl (tocLines 와 같은 줄 세기: 빈 줄은 빼고 '~' 는 간격 줄)
    const [n, k] = key.split(':'), el = $(`#rBody .r-toc[data-pg="${n}"][data-s="${k}"]`); if (!el) return null;
    const before = kText(key).slice(0, a).split('\n'); before.pop();
    return [...el.children].filter(c => !c.classList.contains('tl-or'))[before.filter(l => l.trim()).length] || null;   // 앞서 끼운 원서 줄은 빼고 셈
  };
  const two = R.parMode === 'para' && wide; let any = false;
  // 원서 줄을 끼워 넣으면 '.l0 + .l0' 같은 이웃 규칙이 바뀌므로, 먼저 지금 줄 간격을 그대로 굳혀 둠
  g.ko.forEach(key => { const [n, k] = key.split(':'), el = $(`#rBody .r-toc[data-pg="${n}"][data-s="${k}"]`); if (el) [...el.children].forEach(c => { c.style.marginTop = getComputedStyle(c).marginTop; }); });
  const lv = el => (el.className.match(/\bl\d\b/) || ['l0'])[0];
  const mk = (row, o) => { const d = document.createElement('div'); d.className = 'tl-or ' + lv(row) + (row.querySelector('strong,b') ? ' tl-b' : '');   // 한국어 줄이 굵으면 원서 줄도 굵게
    d.lang = 'en'; d.innerHTML = o.map(([i, a, b]) => oHtml(O[i].t.slice(a, b))).join(' / '); return d; };
  const add = (row, d) => { let at = row; while (at.nextElementSibling && at.nextElementSibling.classList.contains('tl-or')) at = at.nextElementSibling; at.after(d); };
  g.s.forEach(s => {
    const anchor = s.ko.length ? s.ko[0] : s.after; if (!anchor) return;
    const row = rowOf(anchor[0], anchor[1]); if (!row || !row.classList.contains('tl')) return;
    row.closest('.r-toc').classList.add('par-tc', two ? 'tc2' : 'tc1');
    const d = mk(row, s.or); if (!s.ko.length) d.classList.add('tl-only'); else if (two) d.style.marginTop = row.style.marginTop; add(row, d); any = true;
  });
  if (two) $$('#rBody .r-toc.tc2').forEach(t => {   // 두 칸: 한국어 줄마다 원서 칸 하나 (짝 없는 줄은 빈 칸, 원서만 있는 줄은 한국어 칸을 비움)
    [...t.children].forEach(c => {
      if (c.classList.contains('tl') && !(c.nextElementSibling && c.nextElementSibling.classList.contains('tl-or') && !c.nextElementSibling.classList.contains('tl-only'))) { const e = document.createElement('div'); e.className = 'tl-or tl-none ' + lv(c); e.style.marginTop = c.style.marginTop; c.after(e); }
      if (c.classList.contains('tl-only')) { const e = document.createElement('div'); e.className = 'tl tl-blank ' + lv(c); e.setAttribute('aria-hidden', 'true'); c.before(e); }
    });
  });
  return any;
}

/* ---------- 화면 낭독기: 고른 단추 알리기 (운영자 요청, 2026-11-17 — 화면은 그대로) ---------- */
(function a11yPressed() {
  const SEL = '.seg button, [data-spread], [data-bold], [data-font], [data-lh], [data-mw], [data-parm], [data-rmode]';
  const sync = root => { if (!root || !root.querySelectorAll) return; (root.matches && root.matches(SEL) ? [root] : []).concat([...root.querySelectorAll(SEL)]).forEach(b => { if (b.tagName !== 'BUTTON' || b.getAttribute('role')) return; const v = String(b.classList.contains('on')); if (b.getAttribute('aria-pressed') !== v) b.setAttribute('aria-pressed', v); }); };
  sync(document.body);
  new MutationObserver(ms => { for (const m of ms) { if (m.type === 'attributes') { if (m.target.matches && m.target.matches(SEL)) sync(m.target); } else m.addedNodes.forEach(n => n.nodeType === 1 && sync(n)); } })
    .observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['class'] });
})();

/* ---------- 읽기 화면 설정 창·단축키 (화면 낭독기, 운영자 요청 2026-11-17) ---------- */
// 창을 열면 커서를 창 제목(찾기는 찾을 말 칸)으로 옮기고, 닫으면 연 단추로 돌려보냄
function openPanel(name, toggle) {
  const el = $('#reader'), p = $('#p-' + name); if (!el || !p) return false;
  const o = p.classList.contains('open');
  $$('.panel', el).forEach(x => x.classList.remove('open'));
  if (o && toggle) return true;
  el.classList.remove('chrome-off'); p.classList.add('open');
  setTimeout(() => { const t = name === 'find' ? $('#findQ') : $('h5', p); if (!t) return; if (t.tagName === 'H5') t.tabIndex = -1; try { t.focus({ preventScroll: true }); } catch (e) {} }, 40);
  return true;
}
function togglePanel(name) { const p = $('#p-' + name); if (!p) return false; if (p.classList.contains('open')) closePanels(); else openPanel(name); return true; }
function closePanels(back = true) {
  const el = $('#reader'); if (!el) return; const p = $('.panel.open', el);
  $$('.panel', el).forEach(x => x.classList.remove('open'));
  if (!back || !p) return;
  const b = $(`[data-panel="${p.id.slice(2)}"]`, el) || $('#rClose');
  if (b) { el.classList.remove('chrome-off'); setTimeout(() => b.focus(), 20); }
}
function panelA11y(el) {
  $$('.panel', el).forEach(p => {
    const h = $('h5', p); if (h) { h.id = p.id + '-h'; h.tabIndex = -1; p.setAttribute('role', 'region'); p.setAttribute('aria-labelledby', h.id); }
    const x = $(':scope > .p-close', p); if (x) { x.setAttribute('aria-label', (h ? h.textContent.trim() + ' ' : '') + '창 닫기'); x.onclick = () => { if (p.classList.contains('open')) closePanels(); }; }  // ✕ 를 누르면 연 단추로 커서를 돌려보냄
  });
  const ex = () => $$('[data-panel]', el).forEach(b => { b.setAttribute('aria-controls', 'p-' + b.dataset.panel); b.setAttribute('aria-expanded', String(!!$('#p-' + b.dataset.panel + '.open'))); });
  ex(); if (el._pmo) el._pmo.disconnect();
  el._pmo = new MutationObserver(ex); $$('.panel', el).forEach(p => el._pmo.observe(p, { attributes: true, attributeFilter: ['class'] }));
  const KS = { toc: 'N', font: 'F', mode: 'V', tts: 'S', bm: 'L' };
  $$('[data-panel]', el).forEach(b => { const k = KS[b.dataset.panel]; if (k) b.setAttribute('aria-keyshortcuts', 'Alt+Shift+' + k); });
  const sp = $('#rSpeak'); if (sp) sp.setAttribute('aria-keyshortcuts', 'Alt+Shift+P');
  const mk = $('#rMark'); if (mk) mk.setAttribute('aria-keyshortcuts', 'Alt+Shift+B');
}
// 단축키: 브라우저·화면 낭독기 키와 겹치지 않게 Alt+Shift+글자 (WCAG 2.1.4 — 한 글자 키는 쓰지 않음)
const KEYS = [['→', '다음 쪽'], ['←', '앞 쪽'], ['↓', '다음 목차 (소제목·장)'], ['↑', '앞 목차 (소제목·장)'], ['M', '메뉴 열기 (닫기 단추로 커서)'], ['P', '토글: 듣기 시작·멈춤 (듣는 동안 커서가 읽는 문단을 따라감)'], ['C', '지금 읽는 문단을 클립보드에 복사'], ['', '듣는 중에 → ← (Alt·Shift 없이): 다음 문장·앞 문장'], ['S', '토글: 듣기 설정 창 열기·닫기'], ['V', '토글: 화면 바꾸기 (누를 때마다 기본 → 흑백 → 밤 → 고대비)'], ['F', '토글: 글씨 창 열기·닫기 (크기·굵기·줄 간격·글꼴)'], ['N', '토글: 목차 창 열기·닫기'], ['B', '토글: 이 쪽에 책갈피 넣기·빼기'], ['L', '토글: 책갈피 목록 열기·닫기'], ['K', '지금 읽는 곳 알리기'], ['U', '아래 바 ‹ › 넘기는 단위 바꾸기 (누를 때마다 문장 → 문단 → 쪽 → 소제목 → 장)'], ['A', '토글: 오디오북 재생기로 가기 (오디오북이 있는 책 — 재생을 시작하고 커서를 재생 단추로, 다시 누르면 본문으로)'], ['H', '토글: 단축키 안내 열기·닫기']];
// 듣는 동안 커서(포커스)가 읽는 문단을 따라감 (운영자 요청, 2026-11-18 — 시각장애인 이용자: 듣던 문장을 바로 Shift+→ 로 골라 복사할 수 있게).
// 커서가 본문·듣기 단추·앞서 읽던 문단에 있을 때만 옮김 — 설정 창 등 다른 곳에서 일하는 중이면 건드리지 않음
// TTS(기기 목소리 '▶ 듣기')로 듣던 자리 — 책마다 하나, 읽던 자리(pos-·hist)·오디오북 자리(abpos-)와 따로 기억 (운영자 요청, 2026-11-18: 한 책이라도 TTS 로 듣던 곳과 오디오북으로 듣던 곳을 각각 이어 듣게)
function ttsPosSave(id, b, n, s, pl, ch) { if (!id || !n) return; store.set('ttspos-' + id, { p: n, s: +s || 0, pl: pl || '', ch: ch || '', b: b || '', d: today(), ts: Date.now() }); }
function ttsFocus(el) {
  if (!el) return; const a = document.activeElement;
  const ok = !a || a === document.body || a === document.documentElement || (a.closest && a.closest('.reflow, .s-text, #rBody, .s-h1, .s-chnav')) || a.id === 'rSpeak' || a.id === 'sSpeak';
  if (a && a.matches && a.matches('.s-chnav button:not(#sSpeak), .s-chnav input')) return;  // 휴대폰 단추(앞뒤 문장·책갈피 등)를 누른 뒤에는 커서를 단추에 둠 — 다시 누를 수 있게 (2026-11-18 다시 검수)
  if (!ok) return;
  if (!el.hasAttribute('tabindex')) el.tabIndex = -1;
  try { el.focus({ preventScroll: true }); } catch (e) {}
  try { const r = document.createRange(); r.setStart(el, 0); r.collapse(true); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r); } catch (e) {}  // 글 맨 앞에 글자 커서 — Shift+→ 로 바로 고름
}
// Alt+Shift+C: 지금 읽는(없으면 커서가 있는·화면 맨 위) 문단을 클립보드로
function copyNow(root) {
  if (R && R.noCopy && !SR.r) { toast('이 책은 복사할 수 없습니다'); return; }
  const box = $(root); if (!box) return;
  const a = document.activeElement;
  const el = $('.speaking', box) || (a && a.closest && box.contains(a) && a.closest('[data-pg]')) || $$('[data-pg][data-s]', box).find(x => x.getBoundingClientRect().bottom > 80);
  if (!el) { toast('복사할 글이 없습니다'); return; }
  const c = el.cloneNode(true); $$('.ph-say, .sr, .par-pg, .dots, .orn', c).forEach(x => x.remove());  // 낭독기용 소리 글·꾸밈은 빼고 화면 글자 그대로
  const t = c.textContent.replace(/\s+\n/g, '\n').trim(); if (!t) { toast('복사할 글이 없습니다'); return; }
  const done = () => sayKey('지금 문단을 복사했습니다'), fail = () => { try { const ta = document.createElement('textarea'); ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); done(); } catch (e) { toast('복사하지 못했습니다'); } };
  try { navigator.clipboard.writeText(t).then(done, fail); } catch (e) { fail(); }
}
// 쪽·목차 넘기기 단축키 (운영자 요청, 2026-11-18 — 시각장애인 이용자: 다음·앞 쪽, 다음·앞 목차)
// 옮긴 뒤 커서를 그 쪽 표시(또는 제목)에 두어 화면 낭독기가 거기서부터 읽게 함
var STEP_UNITS = [['sent', '문장'], ['para', '문단'], ['page', '쪽'], ['sub', '소제목'], ['ch', '장']];
function stepUnit() { const u = store.get('rstep', 'sub'); return STEP_UNITS.some(x => x[0] === u) ? u : 'sub'; }
function stepName(d) { const u = stepUnit(); return d > 0 ? ({ sent: '다음 문장', para: '다음 문단', page: '다음 쪽', sub: '다음 소제목', ch: '다음 장' })[u] : ({ sent: '앞 문장', para: '앞 문단', page: '앞 쪽', sub: '앞 소제목', ch: '앞 장' })[u]; }
function kbFocus(t) { if (!t) return; if (!t.hasAttribute('tabindex')) t.tabIndex = -1; try { t.focus({ preventScroll: true }); } catch (e) {} }
function kbPage(d) {
  const n = R.i + 1 + d; if (n < 1 || n > R.pages.length) { toast(d > 0 ? '책의 끝입니다' : '책의 처음입니다'); return; }
  go(n);
  setTimeout(() => { const m = $('#pm-' + n); if (!m) return; if (m.textContent.trim()) { kbFocus(m); sayKey(m.textContent.trim()); } else { sayKey(`${n}번째 쪽`); kbFocus(m.nextElementSibling || m); } }, 120);
}
function kbToc(d) {
  const el = $('#reader'); if (!el) return;
  if (R.view !== 'text' || !el._stepSub) { kbPage(d); return; }
  const ci = chapterOf(R.i + 1); R.pinEl = null; el._stepSub(d);
  setTimeout(() => { const e = R.pinEl && document.contains(R.pinEl) ? R.pinEl : null, t = e || (chapterOf(R.i + 1) !== ci ? $('.ch-head h3') : null); kbFocus(t); if (t) sayKey(t.textContent.replace(/\s+/g, ' ').trim()); }, 160);
}
const MODES = [['day', '기본'], ['mono', '흑백'], ['night', '밤'], ['contrast', '고대비']];
// 단축키를 누르면 알림 글을 '▶ 듣기' 목소리로 읽어 줌 (운영자 요청, 2026-11-18 — 시각장애인 이용자: 화면 낭독기와 겹쳐도 됨).
// 듣는 중이면 알림을 읽은 뒤 읽던 문장부터 다시. after 가 있으면 다 읽은 뒤(또는 2.5초 뒤) 실행 — 다른 화면으로 갈 때
function sayKey(msg, after) {
  toast(msg); const o = ttsOpt();
  if (o.keySay === false || !('speechSynthesis' in window)) { if (after) after(); return; }
  const go = () => {
    const resume = ((R && R.speaking) || SR.speaking) ? TT.jump : null;
    TT.gen++; try { speechSynthesis.cancel(); } catch (e) {}
    let done = false; const fin = () => { if (done) return; done = true; clearTimeout(t); if (after) after(); else if (resume && ((R && R.speaking) || SR.speaking)) resume(0); };
    const t = setTimeout(fin, after ? 2500 : 6000);
    speakSegs(sayable(msg, o, true) || msg, o, pickVoice(o), fin, fin);
  };
  if (!LEX.pali) loadLex().then(go, go); else go();
}
const panelSay = (name, label) => setTimeout(() => sayKey(label + ($('#p-' + name + '.open') ? '' : ' 닫힘')), 30);
// Alt+Shift+A: 오디오북 재생기로 바로 가기 — 커서를 재생기 단추로 옮겨 화면 낭독기로 확인·조절 (운영자 요청, 2026-11-18)
function abFocus() {
  if (!R || !R.ab) { sayKey('이 책에는 오디오북이 없습니다'); return; }
  const bar = $('#abBar');
  if (bar && bar.contains(document.activeElement)) { const t = $('.ab-now', $('#rBody')) || $('#rBody [data-pg]'); kbFocus(t); sayKey('본문으로'); return; }  // 다시 누르면 본문으로
  if (!AB.on || !bar || bar.offsetParent === null) abStart();
  setTimeout(() => { const b = $('#abPlay'); if (b) { b.focus(); sayKey('오디오북 재생기'); } }, 300);
}
function cycleMode() {
  const c = store.get('mode', 'auto'); const i = MODES.findIndex(m => m[0] === c), n = MODES[(i + 1) % MODES.length];
  applyMode(n[0]); sayKey(`${n[1]} 화면`); return n;
}
function readerKey(e) {
  const k = (e.code || '').replace(/^Key/, ''); const el = $('#reader'); if (!el) return false;
  if (/^Arrow/.test(k)) { if (R.ttsLocked) { say('듣기가 잠겨 있습니다'); return true; } ({ ArrowRight: () => kbPage(1), ArrowLeft: () => kbPage(-1), ArrowDown: () => kbToc(1), ArrowUp: () => kbToc(-1) })[k](); return true; }
  const say = m => sayKey(m);
  switch (k) {
    case 'A': abFocus(); return true;
    case 'U': { if (R.view !== 'text') { say('이 화면에서는 쪽 단위로만 넘어갑니다'); return true; } const i = STEP_UNITS.findIndex(x => x[0] === stepUnit()), u = STEP_UNITS[(i + 1) % STEP_UNITS.length]; store.set('rstep', u[0]); $$('[data-rstep]', el).forEach(x => x.classList.toggle('on', x.dataset.rstep === u[0])); const a = $('#rPrev'), z = $('#rNext'); if (a) a.setAttribute('aria-label', stepName(-1)); if (z) z.setAttribute('aria-label', stepName(1)); say(`‹ › 넘기는 단위: ${u[1]}`); return true; }  // 누를 때마다 문장 → 문단 → 쪽 → 소제목 → 장 (2026-11-19)
    case 'M': sayKey('메뉴'); el.classList.remove('chrome-off'); $$('.panel', el).forEach(x => x.classList.remove('open')); setTimeout(() => { const b = $('#rClose'); if (b) b.focus(); }, 30); return true;
    case 'P': { const b = $('#rSpeak'); if (!b) { say('이 화면에서는 듣기를 쓸 수 없습니다'); return true; } if (R.ttsLocked) { say('듣기가 잠겨 있습니다'); return true; } if (R.speaking) { stopSpeak(true); say('듣기 멈춤'); } else speak(); return true; }
    // 창 단축키는 켜고 끄기: 한 번 더 누르면 창을 닫고 연 단추로 커서가 돌아감 (운영자 요청, 2026-11-18 — Esc 도 그대로)
    case 'S': if (!togglePanel('tts')) say('이 책은 듣기 설정이 없습니다'); else panelSay('tts', '듣기 설정'); return true;
    case 'V': { const o = !!$('#p-mode.open'); cycleMode(); renderReader(); if (o) openPanel('mode'); return true; }  // 누를 때마다 다음 화면 모드 (운영자 요청, 2026-11-18)
    case 'F': togglePanel('font'); panelSay('font', '글씨 설정'); return true;
    case 'N': if (!togglePanel('toc')) say('이 책에는 목차가 없습니다'); else panelSay('toc', '목차'); return true;
    case 'L': togglePanel('bm'); panelSay('bm', '책갈피 목록'); return true;
    case 'H': togglePanel('keys'); panelSay('keys', '단축키 안내'); return true;
    case 'C': copyNow('#rBody'); return true;
    case 'B': { const b = $('#rMark'); if (b) { b.click(); setTimeout(() => sayKey($('#toast').textContent || '책갈피'), 20); } setTimeout(() => { const m = $('#rMark'); if (m && document.activeElement === document.body) m.focus(); }, 60); return true; }
    case 'K': {
      const p = R.pages[R.i] || {}; let ch = null; try { const cs = chapters(); ch = cs[chapterOf(R.i + 1)]; } catch (x) {}
      say(`『${R.title}』${ch && ch.title ? ', ' + ch.title : ''}, ${pageName(p)}, 전체 ${R.pages.length}쪽 가운데 ${R.i + 1}번째${R.speaking ? ', 듣는 중' : ''}`); return true;
    }
  }
  return false;
}

/* ---------- 읽기 글꼴 (저시력, 운영자 요청 2026-11-17): 명조·고딕 + 나눔명조·나눔고딕(구글 글꼴) + KoPub 바탕·돋움(public/fonts/kopub, 한국출판인회의 무료 글꼴 — 원본 그대로, LICENSE.md) ---------- */
// 단추 이름은 그 글꼴로 보임 — 이름 글자만 담은 작은 글꼴(나눔은 구글 text=, KoPub 은 label-*.woff2). 본문 글꼴은 고를 때만 받음
const RFONTS = [['serif', '명조', 'var(--serif)'], ['sans', '고딕', 'var(--sans)'], ['nanum-myeongjo', '나눔명조', "'Nanum Myeongjo',var(--serif)"], ['nanum-gothic', '나눔고딕', "'Nanum Gothic',var(--sans)"], ['kopub-batang', 'KoPub 바탕', "'dd-kpb-label','KoPubWorld Batang',var(--serif)"], ['kopub-dotum', 'KoPub 돋움', "'dd-kpd-label','KoPubWorld Dotum',var(--sans)"]];
function fontCls() { return R.font === 'sans' ? 'sans' : R.font && R.font !== 'serif' ? 'f-' + R.font : ''; }
function addCss(id, href) { if (document.getElementById(id)) return; const l = document.createElement('link'); l.id = id; l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l); }
function loadReadFont(f) {
  if (/^nanum/.test(f || '')) addCss('rf-nanum', 'https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700&family=Nanum+Myeongjo:wght@400;700&display=swap');
}
function loadFontLabels() { addCss('rf-nanum-label', 'https://fonts.googleapis.com/css2?family=Nanum+Gothic&family=Nanum+Myeongjo&display=swap&text=' + encodeURIComponent('나눔명조고딕')); }

/* ---------- 단순 화면 (시각장애인용, 운영자 요청 2026-11-18) ----------
   센스월드 '내 콘텐츠'처럼: 목록에 들어오면 첫 줄(또는 지난번에 고른 줄)이 바로 골라져 있고, ↑↓ 로 움직이면 바로 골라짐.
   Enter 열기 · Backspace 위 목록으로 · Home/End · PageUp/Down(10줄) · 글자 키(ㄱ~ㅎ 포함)로 그 글자로 시작하는 줄로. */
const CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
const choOf = ch => { const c = ch.charCodeAt(0) - 0xAC00; return c >= 0 && c < 11172 ? CHO[Math.floor(c / 588)] : ch.toLowerCase(); };
// 단순 화면 '법문 바로 듣기': 법문 줄에서 Enter → 재생기(#sAudio)로 재생, 다 들으면 다음 법문 (운영자 요청, 2026-11-18)
// 재생기는 한 번만 만들고, 듣는 중에 다른 단순 화면으로 가면 페이지를 새로 열지 않고 본문만 바꿔(sGo) 계속 들림 —
// 법문 목록 화면에서는 위쪽 자리(#sPlayerSlot)에, 다른 화면에서는 아래쪽에 붙어 보임 (운영자 요청, 2026-11-18 '백그라운드 재생')
const STALK = { el: null, au: null, list: [], idx: -1, page: '', play: null, toggle: null, now: null, playing: () => !!(STALK.au && !STALK.au.paused) };
const sFmtT = t => { t = Math.floor(t || 0); const h = Math.floor(t / 3600), m = Math.floor(t / 60) % 60, s2 = t % 60; return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s2).padStart(2, '0'); };
function sPlayerMake() {
  if (STALK.el) return STALK.el;
  // 맨 위(파란 줄 바로 밑)에 고정되는 한 줄짜리 재생기 — 법문과 오디오북을 함께 틂 (운영자 요청, 2026-11-18)
  const el = document.createElement('section'); el.className = 's-player'; el.id = 'sPlayer'; el.setAttribute('aria-label', '재생기 (법문·오디오북)');
  el.innerHTML = `<p id="sNow" class="s-now" role="status" aria-live="polite">목록에서 법문을 골라 Enter 를 누르면 여기서 재생됩니다. 다른 화면으로 옮겨 가도 계속 들립니다.</p>
<audio id="sAudio" preload="none"></audio>
<div class="s-pbtns"><button type="button" class="s-btn" id="sPrev" aria-label="앞 법문" title="앞 법문">⏮</button><button type="button" class="s-btn" id="sBack15" aria-label="15초 뒤로" title="15초 뒤로">⏪</button><button type="button" class="s-btn s-pplay" id="sPlay" aria-label="재생">▶</button><button type="button" class="s-btn" id="sFwd15" aria-label="15초 앞으로" title="15초 앞으로">⏩</button><button type="button" class="s-btn" id="sNext" aria-label="다음 법문" title="다음 법문">⏭</button>
<label class="s-rate"><span class="sr">빠르기</span><select id="sRate" aria-label="빠르기">${[0.8, 1, 1.2, 1.5, 1.8, 2, 2.2, 2.5].map(r => `<option value="${r}">${r}배</option>`).join('')}</select></label>
<span id="sTime" class="s-time" aria-hidden="true"></span><a class="s-btn s-goto" id="sGoList" href="/simple/talks/" hidden>재생 목록으로</a><button type="button" class="s-btn s-close" id="sClose" aria-label="재생기 닫기, 재생 멈춤">✕ 닫기</button></div>`;
  STALK.el = el; const au = STALK.au = $('#sAudio', el), q = x => $(x, el), now = q('#sNow'), bP = q('#sPlay');
  const SK = 'stalk'; let lastSave = 0;
  const rate = store.get('stalk-rate', 1); q('#sRate').value = String(rate); au.playbackRate = rate;
  // '✕ 닫기'는 멈춘 동안에만 보임 — 듣다가 손이 스쳐 꺼지지 않게 (운영자 요청, 2026-11-19)
  const setBtn = () => { const on = !au.paused; bP.textContent = on ? '⏸' : '▶'; bP.setAttribute('aria-label', on ? '멈춤' : '재생'); q('#sClose').hidden = on; };
  au.addEventListener('play', sHistGuard);  // ◀ 뒤로·휴대폰 뒤로 가기에도 끊기지 않게
  const cur = () => STALK.list[STALK.idx];
  const play = (list, i, from = 0, page = location.pathname) => {
    const e = list[i]; if (!e) return;
    if (STALK.closed) { STALK.closed = false; sPlayerPlace(true); }  // 닫아 둔 재생기는 다시 재생할 때 나타남
    if (STALK.list === list && STALK.idx === i && au.src) { au.play().catch(() => {}); return; }
    STALK.list = list; STALK.idx = i; STALK.page = page; au.src = e.a; au.playbackRate = +q('#sRate').value || 1;
    const sv = store.get(SK, null); if (!from && sv && sv.a === e.a && sv.t > 5) from = sv.t;  // 듣다 멈춘 법문이면 그 자리부터
    if (from) au.addEventListener('loadedmetadata', () => { try { au.currentTime = from; } catch (x) {} }, { once: true });
    au.play().catch(() => toast('재생하지 못했습니다. 잠시 뒤 다시 눌러 주세요'));
    const ab = !!e.ab, u = ab ? '장' : '법문';
    [['#sPrev', `앞 ${u}`], ['#sNext', `다음 ${u}`]].forEach(([x, l]) => { q(x).setAttribute('aria-label', l); q(x).title = l; });
    q('#sGoList').textContent = ab ? '읽는 화면으로' : '재생 목록으로';
    now.textContent = `${ab ? `오디오북: ${e.pl} – ` : '재생: '}${e.t} (${i + 1}/${list.length})${from ? `, ${sFmtT(from)}부터 이어 듣기` : ''}`;
    STALK.abk = -1;
    const g = q('#sGoList'); g.href = page; g.hidden = page === location.pathname;
    sTalkMark();
    if ('mediaSession' in navigator) { try { navigator.mediaSession.metadata = new MediaMetadata({ title: e.t, artist: e.pl || '', album: (e.ab ? '오디오북' : '법문 바로 듣기') + ' · 붓다담마 법보시 도서관' }); } catch (x) {} }
  };
  const step = d => { const j = STALK.idx + d; if (!STALK.list.length || j < 0 || j >= STALK.list.length) { sayKey(cur() && cur().ab ? (d > 0 ? '마지막 장입니다' : '첫 장입니다') : (d > 0 ? '마지막 법문입니다' : '첫 법문입니다')); return; } play(STALK.list, j, 0, STALK.page); };
  STALK.play = play;
  const savePos = () => { if (!cur() || !au.src) return; if (cur().ab) sAbSave(cur(), au.currentTime); else { store.set(SK, { a: cur().a, t: au.currentTime, p: STALK.page }); if (au.currentTime > 3) sHistSave(cur(), STALK.page, au.currentTime, au.duration); } };
  q('#sClose').onclick = () => {
    savePos(); au.pause(); STALK.closed = true; el.remove(); document.body.classList.remove('s-docked'); sBarH();
    const old = $('#sReopen'); if (old) old.remove();
    const bar = $('.s-bar'); if (bar) bar.insertAdjacentHTML('afterend', `<div id="sReopen" class="s-reopen" role="status">재생기를 닫았습니다. 듣던 자리는 저장했습니다. <button type="button" class="s-btn">다시 열기</button></div>`);
    const ro = $('#sReopen'); if (ro) { $('button', ro).onclick = () => { ro.remove(); STALK.closed = false; sPlayerPlace(true); const b = $('#sPlay'); if (b) b.focus(); sayKey('재생기를 다시 열었습니다'); }; setTimeout(() => { if (ro.isConnected && !ro.contains(document.activeElement)) ro.remove(); }, 8000); }
    const h = $('.s-h1'); if (h) h.focus({ preventScroll: true }); sayKey('재생기를 닫았습니다');
  };
  STALK.step = step; STALK.seek = d => { if (!cur()) { sayKey('듣는 것이 없습니다'); return; } au.currentTime = Math.max(0, Math.min(au.duration || 1e9, au.currentTime + d)); sayKey(`${d > 0 ? '15초 앞으로' : '15초 뒤로'}, ${sFmtT(au.currentTime)}`); };
  au.addEventListener('play', () => { if (SR.speaking) srStop(true); });  // 책 '▶ 듣기'와 법문이 겹쳐 나오지 않게
  STALK.toggle = () => { if (!cur()) { const pl = sTalkPageList(); if (!pl.length) { sayKey('법문 목록 화면에서 법문을 고르세요'); return; } const sel = $('.s-list > li.k-ep[aria-selected="true"]'); play(pl, sel ? $$('.s-list > li.k-ep').indexOf(sel) : 0); return; } if (au.paused) au.play().catch(() => {}); else au.pause(); };
  STALK.now = () => cur() ? `${au.paused ? '멈춤' : '듣는 중'}: ${cur().ab ? '오디오북 ' + cur().pl + ', ' : ''}${cur().t}, ${sFmtT(au.currentTime)} / ${sFmtT(au.duration)}` : '';
  bP.onclick = STALK.toggle; q('#sPrev').onclick = () => step(-1); q('#sNext').onclick = () => step(1);
  q('#sBack15').onclick = () => { au.currentTime = Math.max(0, au.currentTime - 15); }; q('#sFwd15').onclick = () => { au.currentTime = Math.min(au.duration || 1e9, au.currentTime + 15); };
  q('#sRate').onchange = e => { au.playbackRate = +e.target.value || 1; store.set('stalk-rate', au.playbackRate); };
  au.addEventListener('play', setBtn); au.addEventListener('pause', setBtn);
  au.addEventListener('timeupdate', () => { q('#sTime').textContent = `${sFmtT(au.currentTime)} / ${sFmtT(au.duration)}`; if (cur() && Date.now() - lastSave > 5000) { lastSave = Date.now(); if (cur().ab) sAbSave(cur(), au.currentTime); else { store.set(SK, { a: cur().a, t: au.currentTime, p: STALK.page }); if (au.currentTime > 3) sHistSave(cur(), STALK.page, au.currentTime, au.duration); } } if (cur() && cur().ab) { sAbFollow(cur(), au.currentTime); } });
  au.addEventListener('ended', () => { if (cur() && cur().ab) { if (STALK.idx + 1 >= STALK.list.length) store.set('abpos-' + cur().ab.id, null); } else { store.set(SK, null); if (cur()) sHistDel(cur().a); } if (STALK.idx + 1 < STALK.list.length) play(STALK.list, STALK.idx + 1, 0, STALK.page); else { now.textContent = '목록의 마지막 법문까지 들었습니다'; setBtn(); } });
  if ('mediaSession' in navigator) { const h = (k, f) => { try { navigator.mediaSession.setActionHandler(k, f); } catch (x) {} }; h('play', () => au.play()); h('pause', () => au.pause()); h('previoustrack', () => step(-1)); h('nexttrack', () => step(1)); h('seekbackward', () => q('#sBack15').click()); h('seekforward', () => q('#sFwd15').click()); }
  return el;
}
const sTalkPageList = () => $$('.s-list > li.k-ep').map(li => ({ a: li.dataset.href || ($('a', li) || {}).href, t: li.dataset.t || ($('.s-c1', li) || li).textContent.trim(), pl: li.dataset.pl || '' }));
function sTalkMark() {
  const same = STALK.page === location.pathname;
  $$('.s-list > li.k-ep').forEach((li, i) => { const on = same && i === STALK.idx; li.classList.toggle('playing', on); if (on) li.setAttribute('aria-current', 'true'); else li.removeAttribute('aria-current'); });
  if (STALK.el) { const g = $('#sGoList', STALK.el); g.hidden = same || !STALK.list.length; g.href = STALK.page || '/simple/talks/'; }
}
// 재생기 자리: 법문 목록 화면이면 위쪽 자리, 다른 화면이면 듣는 법문이 있을 때만 아래쪽에 붙임
function sPlayerPlace(force) {
  if (STALK.closed && !force) { if (STALK.el) STALK.el.remove(); return; }  // '✕ 닫기'로 닫았으면 다시 재생할 때까지 숨김
  if (force) STALK.closed = false;
  const slot = $('#sPlayerSlot');
  if (!slot && !force && !(STALK.el && STALK.list.length)) { if (STALK.el) STALK.el.remove(); return; }
  const el = sPlayerMake(), bar = $('.s-bar');
  if (bar && el.previousElementSibling !== bar) bar.after(el); else if (!bar && !el.isConnected) document.body.prepend(el);
  el.classList.add('top'); el.classList.remove('dock'); document.body.classList.remove('s-docked');
  sBarH(); sTalkMark();
}
// 이어 듣기 기록: 듣던 법문을 최근 순으로 20개까지(이 기기에만), 끝까지 들은 법문은 빠짐 (운영자 요청, 2026-11-18)
const SH = 'stalk-hist';
function sHistSave(e, page, pos, dur) {
  const h = store.get(SH, []).filter(x => x.a !== e.a);
  h.unshift({ a: e.a, t: e.t, pl: e.pl || '', p: page, pos: Math.floor(pos), dur: isFinite(dur) ? Math.floor(dur) : 0, d: new Date().toISOString().slice(0, 10), ts: Date.now() });
  store.set(SH, h.slice(0, 20));
}
function sHistDel(a) { store.set(SH, store.get(SH, []).filter(x => x.a !== a)); }
// 법문 바로 듣기 목록의 '이어 듣기' 줄(기록이 없으면 뺌)과 첫 화면 '법문 바로 듣기' 줄에 듣던 법문 수
function sResumeCount() {
  const n = store.get(SH, []).length;
  const r = $('.s-list a[href="/simple/talks/resume/"]'); if (r) { const li = r.closest('li'); if (!n) li.remove(); else { const c = $('.s-c3', li); if (c) c.textContent = `듣던 법문 ${n}개 · 최근 순`; } }
  const t = $('.s-list a[href="/simple/talks/"]'); if (t && n && !t.dataset.rc) { t.dataset.rc = 1; const c = $('.s-c3', t); if (c) c.textContent += ` · 이어 듣기 ${n}개`; }
}
function initSimpleTalk() {
  const rs = $('#sResume');
  if (rs) {
    const H = store.get(SH, []);
    rs.innerHTML = H.length ? '<div class="s-tbl" style="--cols:minmax(0,2.4fr) minmax(0,1.4fr) minmax(0,2fr)">' + sHead(['법문', '이어 듣기', '어디 · 언제']) + `<ul class="s-list" data-label="이어 듣기, 듣던 법문 ${H.length}개">${H.map(h => sRow(h.a, [h.t, `이어 듣기: ${sFmtT(h.pos)}${h.dur ? ' / ' + sFmtT(h.dur) : ''}`, `${h.pl}${h.pl ? ' · ' : ''}${h.d || ''}`], '▶', 'ep')).join('')}</ul></div>` : '<p>아직 이 기기에서 들은 법문이 없습니다. 법문 목록에서 법문을 골라 들으면 여기에 최근 순으로 모입니다.</p>';
    $$('.s-list > li.k-ep', rs).forEach((li, i) => { const h = H[i]; li.dataset.t = h.t; li.dataset.pl = h.pl; li.dataset.src = h.p || ''; li.dataset.pos = h.pos || 0; });
    sStat(`듣던 법문 ${H.length}`);
  }
  sPlayerPlace();
  const list = sTalkPageList();
  // 같은 화면을 다시 열었으면 지금 듣는 목록과 같은 목록으로 이어 감
  STALK.pageList = STALK.page === location.pathname && STALK.list.length === list.length ? STALK.list : list;
  const sv = store.get('stalk', null), i0 = !STALK.list.length && sv && sv.p === location.pathname ? list.findIndex(e => e.a === sv.a) : -1;
  if (i0 > -1) $('#sNow').textContent = `지난번에 ‘${list[i0].t}’을 ${sFmtT(sv.t)}까지 들었습니다. 그 줄을 고르고 Enter 를 누르면 이어 듣습니다.`;
}
// 단순 화면 안에서 옮겨 가기: 법문을 듣는 중이면 페이지를 새로 열지 않고 본문만 바꿈(재생기가 끊기지 않게), 아니면 보통 이동
// 처음 연 화면(새로 불러온 페이지)에서 재생을 시작하면, 그 화면의 뒤로 가기는 브라우저가 페이지를 새로 열어 소리가 멈춤 —
// 재생을 시작할 때 같은 주소의 기록을 하나 더 쌓아 두고(sp), 뒤로 가기로 아래 기록(sb)에 오면 앞 화면을 sGo 로 그림 (운영자 요청, 2026-11-18)
// ---- 오디오북도 단순 화면 재생기에서 (운영자 요청, 2026-11-18) ----
// 장마다 mp3 를 한 목록으로(STALK.list 의 줄에 ab 정보) 틀고, 장 글 화면이면 듣는 문단을 표시하고 글이 따라감(sync [초, 쪽, 문단])
STALK.abj = {};
async function sAbData(id, url) { if (STALK.abj[id]) return STALK.abj[id]; const j = await (await fetch(url || `/data/audio/${id}.json`)).json(); return (STALK.abj[id] = j); }
const sAbList = (id, title, j) => j.chapters.map((c, i) => ({ a: c.url, t: c.title, pl: title, ab: { id, ci: i, page: c.page, to: c.to, sync: c.sync || [] } }));
function sAbSave(e, t) { store.set('abpos-' + e.ab.id, { ci: e.ab.ci, t: Math.round(t), b: e.pl, ch: e.t, d: today(), ts: Date.now() }); }
function sAbFollow(e, t) {
  if (!(SR.r && SR.id === e.ab.id && $('#sRead .s-text'))) return;
  const sy = e.ab.sync; let k = -1; for (let i = 0; i < sy.length && sy[i][0] <= t + 0.05; i++) k = i;
  if (k < 0 || (k === STALK.abk && $('.ab-now'))) return;
  const [, pg, sn] = sy[k];
  let el = sn < 0 ? null : $(`.s-text [data-pg="${pg}"][data-s="${sn}"]`);
  if (sn < 0) el = $(`.s-text [data-pg="${pg}"]`) ? $('.s-h1') : null;
  if (!el) {  // 듣는 곳이 다른 장으로 넘어감 — 읽는 분이 따라 보던 장이면 그 장을 그려 따라감
    if (STALK.abCi === SR.ci && !STALK.abMoving) { const ci = withR(() => chapterOf(pg)); if (ci !== SR.ci) { STALK.abMoving = 1; srChapter(ci, 0, true, () => { STALK.abMoving = 0; STALK.abCi = ci; STALK.abk = -1; scrollTo(0, 0); }); } }
    return;
  }
  STALK.abk = k; STALK.abCi = SR.ci;
  $$('.ab-now').forEach(x => x.classList.remove('ab-now')); el.classList.add('ab-now');
  if (Date.now() - (STALK.userAt || 0) > 8000) { const r = el.getBoundingClientRect(), top = (STALK.el ? STALK.el.getBoundingClientRect().bottom : 0) + 8; if (r.top < top || r.bottom > innerHeight - 20) scrollTo({ top: scrollY + r.top - top - 10 }); }
}
['wheel', 'touchmove'].forEach(ev => addEventListener(ev, () => { STALK.userAt = Date.now(); }, { passive: true }));
// 장 글 화면에서 오디오북 시작: 지금 보는 장을 담은 오디오북 장부터(이어 듣던 장이면 그 자리부터)
async function sAbStart() {
  const root = $('#sRead'); if (!root || !root.dataset.audio) return;
  const id = SR.id; sPlayerPlace(true);
  if (STALK.list[0] && STALK.list[0].ab && STALK.list[0].ab.id === id && STALK.au.src) { STALK.toggle(); return; }
  let j; try { j = await sAbData(id, root.dataset.audio); } catch (e) { toast('오디오북을 불러오지 못했습니다'); return; }
  const list = sAbList(id, SR.title, j), first = $('.s-text [data-pg]'), pg = first ? +first.dataset.pg : 1;
  let ci = list.findIndex(x => pg >= x.ab.page && pg <= (x.ab.to || x.ab.page)); if (ci < 0) ci = list.findIndex(x => x.ab.page >= pg); if (ci < 0) ci = 0;
  const ap = store.get('abpos-' + id, null), from = ap && ap.ci === ci && ap.t > 5 ? ap.t : 0;
  STALK.abCi = SR.ci; STALK.abk = -1;
  STALK.play(list, ci, from, `/simple/book/${id}/read/?p=${list[ci].ab.page}`);
}
function sAbBtn() {
  const root = $('#sRead'); if (!root || !root.dataset.audio) return;
  const nav = $('.s-chnav', root), sp = $('#sSpeak'); if (!nav || $('#sAb')) return;
  const b = document.createElement('button'); b.type = 'button'; b.className = 's-btn'; b.id = 'sAb'; b.textContent = '🎧 오디오북'; b.setAttribute('aria-label', '오디오북 듣기 (녹음된 소리, 맨 위 재생기에서 재생)');
  (sp ? sp.parentNode : nav).insertBefore(b, sp ? sp.nextSibling : null); b.onclick = sAbStart;
}
function sResumePlay(li) {
  const e = { a: li.dataset.href, t: li.dataset.t, pl: li.dataset.pl }, src = li.dataset.src, pos = +li.dataset.pos || 0;
  sPlayerPlace(true);  // 내 서재처럼 재생기 자리가 없는 화면이면 아래쪽에 붙임(재생 전에 — 재생 중 옮기면 이어 듣기 자리를 놓침)
  STALK.play([e], 0, pos > 5 ? pos : 0, src);  // 바로 재생(누른 즉시 소리가 나게)
  fetch(src).then(r => r.ok ? r.text() : '').then(t => {  // 원래 재생목록을 받아 다음 법문으로 이어지게
    if (!t || STALK.list[0] !== e) return;
    const d = new DOMParser().parseFromString(t, 'text/html');
    const list = [...d.querySelectorAll('.s-list > li.k-ep')].map(x => { const a = x.querySelector('a'); return { a: a ? new URL(a.getAttribute('href'), location.href).href : '', t: x.dataset.t || '', pl: x.dataset.pl || '' }; });
    const i = list.findIndex(x => x.a === new URL(e.a, location.href).href); if (i < 0) return;
    list[i] = e; STALK.list = list; STALK.idx = i;
    const nw = $('#sNow'); if (nw) nw.textContent = nw.textContent.replace('(1/1)', `(${i + 1}/${list.length})`);
  }).catch(() => {});
}
let sGuarded = false;
function sHistGuard() {
  if (sGuarded || !document.body.classList.contains('simple-ui')) return; sGuarded = true;
  let prev = ''; try { const r = new URL(document.referrer); if (r.origin === location.origin && r.pathname.startsWith('/simple/') && r.pathname + r.search !== location.pathname + location.search) prev = r.href; } catch (e) {}
  if (!prev) prev = ($('#sUp') || {}).href || '/simple/';
  try { history.replaceState({ sb: 1, prev }, ''); history.pushState({ sp: 1 }, ''); } catch (e) {}
}
async function sGo(url, push = true) {
  const u = new URL(url, location.href);
  if (!STALK.playing() || u.origin !== location.origin || !u.pathname.startsWith('/simple/')) { if (push) location.href = u.href; else location.reload(); return; }
  try {
    const r = await fetch(u.href, { headers: { accept: 'text/html' } }); if (!r.ok) throw 0;
    const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
    if (!doc.body.classList.contains('simple-ui') || !doc.querySelector('main#app')) throw 0;
    if (STALK.el) STALK.el.remove();
    if (SR.speaking) srStop(true);
    $('.s-bar').replaceWith(document.adoptNode(doc.querySelector('.s-bar')));
    $('main#app').replaceWith(document.adoptNode(doc.querySelector('main#app')));
    const of = $('footer.s-stat'), nf = doc.querySelector('footer.s-stat'); if (of) of.remove(); if (nf) $('main#app').after(document.adoptNode(nf));
    document.title = doc.title; document.body.dataset.page = doc.body.dataset.page;
    if (push) history.pushState({}, '', u.href);
    lastDoc = location.pathname + location.search;
    window.scrollTo(0, 0);
    sPageInit();
    try { if (navigator.sendBeacon && location.protocol === 'https:' && !store.get('notrack', false)) { const v = store.get('vid', ''); if (v) navigator.sendBeacon('/api/hit', JSON.stringify({ p: location.pathname, t: document.title.replace(/\s*·\s*(?:테라와다불교|붓다담마) 법보시 도서관$/, ''), r: '', v })); } } catch (x) {}  // 통계에도 화면 연 것을 셈
  } catch (e) { location.href = u.href; }
}
function sListbox(ul) {
  // 첫 화면 말고는 목록 맨 위에 '▲ 위로' 줄 (운영자 요청, 2026-11-18 — 책이 한 권뿐인 목록에서 ↑↓ 를 눌러도
  // 움직일 곳이 없어 낭독기가 아무것도 읽지 않던 것: 위로 줄이 있으면 늘 움직일 곳이 있음)
  const upA = $('#sUp');
  if (upA && !ul.closest('.s-find') && !$(':scope > li.k-up', ul)) {
    const pa = $$('.s-path a'), pn = pa.length ? pa[pa.length - 1].textContent.trim() : '';
    ul.insertAdjacentHTML('afterbegin', sRow(upA.getAttribute('href'), ['▲ 위로', pn ? `한 단계 위: ${pn}` : '한 단계 위 목록'], '', 'up'));
  }
  const items = $$(':scope > li', ul); if (!items.length) return null;
  const hasUp = items[0].classList.contains('k-up');
  ul.setAttribute('role', 'listbox'); if (ul.dataset.label) ul.setAttribute('aria-label', ul.dataset.label);
  const key = 'dd-ssel:' + location.pathname + location.search;
  let sel = hasUp && items.length > 1 ? 1 : 0; try { const v = sessionStorage.getItem(key); if (v != null) sel = Math.min(+v || 0, items.length - 1); } catch (e) {}
  // 줄 안의 링크는 글자 덩어리로 바꾸고(목록 줄 안에 또 누를 것이 있으면 낭독기가 헷갈림) 주소는 줄에 기억
  items.forEach((li, i) => { li.setAttribute('role', 'option'); li.id = li.id || 'so-' + i; const a = $('a', li); if (!a) return;
    li.dataset.href = a.getAttribute('href'); if (a.hasAttribute('download')) li.dataset.dl = '1'; if (a.target === '_blank') li.dataset.ext = '1';
    const sp = document.createElement('span'); sp.className = 's-a'; while (a.firstChild) sp.appendChild(a.firstChild); a.replaceWith(sp); });
  const pick = (i, focus = true) => {
    const want = i; i = Math.max(0, Math.min(items.length - 1, i));
    if (focus && i === sel && want !== i) toast(want < 0 ? '목록의 처음입니다' : '목록의 끝입니다');  // 더 갈 곳이 없을 때도 소리로 알림
    sel = i;
    items.forEach((li, k) => { const on = k === i; li.setAttribute('aria-selected', on ? 'true' : 'false'); li.tabIndex = on ? 0 : -1; li.classList.toggle('sel', on); });
    try { sessionStorage.setItem(key, i); } catch (e) {}
    if (focus) { try { items[i].focus({ preventScroll: true }); } catch (e) {} }
    const r = items[i].getBoundingClientRect(); if (r.top < 70 || r.bottom > innerHeight - 50) items[i].scrollIntoView({ block: 'center' });
  };
  const open = i => { pick(i, false); const li = items[i], h = li.dataset.href; if (ul._delMode && li.dataset.del && ul._pick) { ul._pick(li); return; } if (!h) return;
    if (li.classList.contains('k-ep') && li.dataset.src) { sPlayerMake(); sResumePlay(li); return; }  // 이어 듣기 줄: 듣던 자리부터, 원래 목록에서 이어 감
    if (li.classList.contains('k-ep')) { sPlayerMake(); const l = STALK.pageList || sTalkPageList(); STALK.play(l, $$(':scope > li.k-ep', ul).indexOf(li)); return; }  // 법문 줄: 재생기로 재생
    if (li.dataset.ext) { window.open(h, '_blank', 'noopener'); return; }
    if (li.dataset.dl) { const a = document.createElement('a'); a.href = h; a.download = ''; document.body.appendChild(a); a.click(); a.remove(); toast('파일을 내려받습니다'); return; }
    sGo(h); };
  pick(sel, false);
  ul.addEventListener('keydown', e => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const k = e.key;
    if (k === 'ArrowDown') pick(sel + 1); else if (k === 'ArrowUp') pick(sel - 1);
    else if (k === 'Home') pick(0); else if (k === 'End') pick(items.length - 1);
    else if (k === 'PageDown') pick(sel + 10); else if (k === 'PageUp') pick(sel - 10);
    else if (k === 'Enter' || k === ' ') open(sel);
    else if (k === 'Backspace') { const u = $('#sUp'); if (!u) return; u.click(); }
    else if (k === 'Delete') { if (!items[sel].dataset.del || !ul._del) { toast('이 줄은 지울 수 없습니다'); } else ul._del(items[sel]); }
    else if (k.length === 1 && /\S/.test(k)) {
      const want = choOf(k), name = li => ($('.s-c1', li) || li).textContent.trim();
      for (let s = 1; s <= items.length; s++) { const j = (sel + s) % items.length, t = name(items[j]); if (t && (t[0].toLowerCase() === k.toLowerCase() || choOf(t[0]) === want)) { pick(j); break; } }
    } else return;
    e.preventDefault();
  });
  items.forEach((li, i) => li.addEventListener('click', () => open(i)));
  return { pick, focus: () => pick(sel) };
}
const sRow = (href, cols, ic = '📁', kind = '') => `<li class="s-row${kind ? ' k-' + kind : ''}"><a href="${esc(href)}"><span class="s-ic" aria-hidden="true">${ic}</span>${cols.map((c, i) => `${i && c ? '<span class="sr">, </span>' : ''}<span class="s-c s-c${i + 1}">${sDate(c || '')}</span>`).join('')}</a></li>`;
const sDate = c => /\d{4}-\d{1,2}-\d{1,2}/.test(c) ? `<span aria-hidden="true" class="d-long">${esc(c)}</span><span aria-hidden="true" class="d-short">${esc(c.replace(/^.*?(\d{2})(\d{2})-(\d{1,2})-(\d{1,2}).*$/, (m, a, y, mo, d) => `${y}/${mo.padStart(2, '0')}/${d.padStart(2, '0')}`))}</span><span class="sr">${esc(c.replace(/(\d{4})-(\d{1,2})-(\d{1,2})/g, (m, y, mo, d) => `${y}년 ${+mo}월 ${+d}일`))}</span>` : esc(c);  // 날짜는 '2026년 11월 15일' 로 들려줌
const sHead = h => `<div class="s-head" aria-hidden="true">${h.map((x, i) => `<span class="s-c s-c${i + 1}">${esc(x)}</span>`).join('')}</div>`;
const sStat = t => { const s = $('.s-stat span:last-child'); if (s) s.textContent = t; };
function sFocusFirst() {
  // 목록이 있으면 골라진 줄로, 없으면 제목으로 — 화면 낭독기가 바로 읽음
  const ul = $('.s-list'); const lb = ul && (ul._lb || (ul._lb = sListbox(ul)));
  const go = () => { if (lb) lb.focus(); else { const h = $('.s-h1'); if (h) h.focus({ preventScroll: true }); } };
  if (document.readyState === 'complete') go(); else addEventListener('load', go, { once: true });
}
// 단순 화면 글 읽기: 장을 바꿔도 페이지를 새로 열지 않고 그 자리에서 다시 그림(듣기가 다음 장으로 이어지게)
// 듣기(Alt+Shift+P, '▶ 듣기' 단추)는 일반 읽기 화면과 같은 목소리·설정으로 문단마다 읽음 (운영자 요청, 2026-11-18)
const SR = { r: null, cs: null, ci: 0, id: '', title: '', speaking: false, list: [], k: 0 };
const withR = fn => { const old = R; R = SR.r; try { return fn(); } finally { R = old; } };
const srName = (ch, i) => ch.title || `${i + 1}번째 부분`;
async function initSimpleRead() {
  const root = $('#sRead'); if (!root) return;
  const id = root.dataset.book, title = root.dataset.title;
  let man; try { man = await manifest(root.dataset.manifest); } catch (e) { root.innerHTML = '<p>읽기 자료를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.</p>'; return; }
  const pages = man.pages.map((p, i) => ({ n: i + 1, label: p.label || '', img: '', big: '', text: p.text || '' }));
  SR.r = { id, title, by: root.dataset.by, pages, toc: man.toc || [], say: man.say || {}, ph: man.ph || null, tdl: man.table_dl || {}, fnSite: man.fn_site || {}, spreadOk: false, spread: false, ly: null, i: 0, view: 'text', zoom: 1, fs: 1, bold: false, lh: 1.9, font: 'serif', mw: 40, centerHeads: !!man.center_heads, hl: [], speaking: false, par: [], parMode: 'off', parD: null, parEd: [], ix: man.index || null, ixPart: 0, ixQ: '', simple: true };
  SR.id = id; SR.title = title; SR.cs = withR(() => chapters());
  if (!SR.scrollHook) { SR.scrollHook = 1; let tt = 0; addEventListener('scroll', () => { if (SR.speaking || scrollY <= 40 || !$('#sRead .s-text')) return; clearTimeout(tt); tt = setTimeout(() => { const head = (STALK.el && STALK.el.isConnected ? STALK.el.getBoundingClientRect().bottom : sBarH()) + 4; const el = $$('.s-text [data-pg][data-s]').find(x => x.getBoundingClientRect().bottom > head); if (el) SR.anchor = +el.dataset.pg; }, 250); }, { passive: true }); }  // 마지막으로 보던 쪽
  const q = new URLSearchParams(location.search), c = +q.get('c') || 0, listen = q.has('listen'), audio = q.has('audio') && root.dataset.audio;
  // 책 폴더의 '듣기' 줄(?listen=1): 이 기기에서 읽던 곳(없으면 첫 장)을 열고 커서를 '▶ 듣기' 단추에 — Enter 한 번이면 읽기 시작 (운영자 요청, 2026-11-18)
  let pp = +q.get('p') || 0, ps = q.has('s') ? +q.get('s') : null;
  if (listen && !c && !pp) { const tp = store.get('ttspos-' + SR.id, null); if (tp && tp.p) { pp = tp.p; ps = tp.s; } else { const h = store.get('hist', []).find(x => x.id === SR.id); pp = h && h.p || 1; } }  // TTS 로 듣던 곳이 있으면 거기부터 (없으면 읽던 곳)
  // 오디오북(?audio=1): 이어 듣던 장(없으면 첫 장)을 열고 커서를 '🎧 오디오북' 단추에 — Enter 한 번이면 재생 (운영자 요청, 2026-11-18)
  if (audio && !c && !pp) { const ap = store.get('abpos-' + SR.id, null); pp = 1; if (ap) { try { const j = await sAbData(SR.id, root.dataset.audio); const ch = j.chapters[ap.ci]; if (ch) pp = ch.page; } catch (e) {} } }
  if (!c && !pp) { SR.ci0 = null; srList(root); return; }
  const ci = c ? Math.min(c, SR.cs.length) - 1 : withR(() => chapterOf(Math.min(pp, pages.length)));
  srChapter(ci, pp && !c ? Math.min(pp, pages.length) : 0, false);
  if (pp && !c && ps != null) SR.anchorS = { p: Math.min(pp, pages.length), s: ps };  // ▶ 듣기가 그 문단부터
  if (audio) { const fa = () => { const b = $('#sAb'); if (b) { b.focus(); toast('🎧 오디오북 단추입니다. Enter 를 누르면 맨 위 재생기에서 재생합니다'); } }; if (document.readyState === 'complete') setTimeout(fa, 300); else addEventListener('load', () => setTimeout(fa, 300), { once: true }); }
  if (listen) { const fb = () => { const b = $('#sSpeak'); if (b) { b.focus(); toast(`▶ 듣기 단추입니다. Enter 를 누르면 ${SR.anchorS ? '듣던 곳부터 ' : ''}읽기 시작합니다`); } }; if (document.readyState === 'complete') setTimeout(fb, 300); else addEventListener('load', () => setTimeout(fb, 300), { once: true }); }
  SR.ci0 = c || pp ? ci : null; SR.p0 = pp && !c ? Math.min(pp, pages.length) : 0;
  // 장 사이 뒤로·앞으로 가기는 페이지를 새로 열지 않고 그 자리에서 다시 그림 — 오디오북·법문이 듣는 중이어도 끊기지 않게 (운영자 요청, 2026-11-18)
  if (!SR.popHook) { SR.popHook = 1; window.addEventListener('popstate', () => { if (!$('#sRead') || (history.state || {}).sb) return; const u = new URLSearchParams(location.search), cc = +u.get('c') || 0; if (SR.speaking) srStop(true); if (cc) srChapter(cc - 1, 0, false); else if (SR.ci0 != null) srChapter(SR.ci0, SR.p0, false); else srList($('#sRead')); }); }
}
function srList(root) {
  const cs = SR.cs, id = SR.id, pages = SR.r.pages;
  const rng = ch => { const a = pages[ch.from - 1], b = pages[ch.to - 1]; return a && a.label ? `${a.label}쪽${b && b.label && b.label !== a.label ? '~' + b.label + '쪽' : ''}` : ''; };
  const last = store.get('pos-' + id, 0), lc = last > 1 ? withR(() => chapterOf(last)) : -1;
  const rows = [].concat(lc >= 0 ? [sRow(`?p=${last}`, [`이어 읽기: ${srName(cs[lc], lc)}`, pageName(pages[last - 1] || { n: last }), '지난번에 읽던 곳'], '🔖', 'resume')] : [])
    .concat(cs.map((ch, i) => sRow(`?c=${i + 1}`, [srName(ch, i), rng(ch), `${i + 1} / ${cs.length}`], '📄', 'ch')));
  root.innerHTML = `<div class="s-tbl" style="--cols:minmax(0,3fr) minmax(0,1.3fr) 110px">` + sHead(['장 이름', '쪽', '순서']) + `<ul class="s-list" data-label="${esc(SR.title)} 장 목록, ${cs.length}개">${rows.join('')}</ul></div>`;
  sStat(`장 ${cs.length}`); sFocusFirst();
}
function srChapter(ci, page, push, then) {
  const root = $('#sRead'), cs = SR.cs; ci = Math.max(0, Math.min(ci, cs.length - 1)); SR.ci = ci;
  const ch = cs[ci], R0 = SR.r; R0.i = (page || ch.from) - 1; SR.anchor = page || null;
  const full = withR(() => reflowHtml()), hd = (full.match(/<div class="ch-head">[\s\S]*?<\/div>/) || [''])[0];
  const headFn = (hd.match(/<sup class="fn-ref"[^>]*>[^<]*<\/sup>/g) || []).join('');  // 장 제목에 붙은 각주 번호 — 숨긴 같은 제목 줄에서 옮겨 온 것 (2026-11-18: 단순 화면에서 빠져 그 각주를 열 수 없었음)
  const html = full.replace(/<div class="ch-head">[\s\S]*?<\/div>/, '').replace(/<nav class="ch-nav"[\s\S]*?<\/nav>/, '');
  const nav = where => `<nav class="s-chnav" aria-label="장 이동 (${where})"><a href="./" class="s-btn">▤ 장 목록</a>${ci > 0 ? `<a class="s-btn" href="?c=${ci}" data-c="${ci - 1}">◀ 앞 장: ${esc(srName(cs[ci - 1], ci - 1))}</a>` : ''}${ci < cs.length - 1 ? `<a class="s-btn" href="?c=${ci + 2}" data-c="${ci + 1}">다음 장: ${esc(srName(cs[ci + 1], ci + 1))} ▶</a>` : '<span class="s-sub">책의 끝입니다.</span>'}${where === '위' ? `<button type="button" class="s-btn" id="sSpeak" aria-keyshortcuts="Alt+Shift+P">${SR.speaking ? '■ 듣기 멈춤' : '▶ 듣기'}</button><button type="button" class="s-btn" id="sTtsBtn" aria-keyshortcuts="Alt+Shift+S" aria-expanded="false" aria-controls="sTts">듣기 설정</button><button type="button" class="s-btn s-sent" id="sPrevS" aria-label="앞 문장 듣기"${SR.speaking ? '' : ' hidden'}>◀ 앞 문장</button><button type="button" class="s-btn s-sent" id="sNextS" aria-label="다음 문장 듣기"${SR.speaking ? '' : ' hidden'}>다음 문장 ▶</button><button type="button" class="s-btn" id="sBmBtn" aria-keyshortcuts="Alt+Shift+B" aria-label="지금 쪽에 책갈피 넣기·빼기">🔖 책갈피</button><button type="button" class="s-btn" id="sWhereBtn" aria-keyshortcuts="Alt+Shift+K" aria-label="지금 위치 알리기">📍 지금 위치</button><button type="button" class="s-btn" id="sGoPg" aria-expanded="false" aria-controls="sPgForm">📄 쪽으로 가기</button>` : ''}</nav>`;
  root.innerHTML = nav('위') + `<form id="sPgForm" class="s-pgform" hidden><label for="sPgIn">몇 쪽으로 갈까요? (책에 인쇄된 쪽 번호)</label> <input id="sPgIn" type="text" inputmode="numeric" autocomplete="off" size="6"> <button type="submit" class="s-btn">가기</button> <button type="button" class="s-btn" id="sPgX">닫기</button></form><section id="sTts" class="s-tts" hidden aria-labelledby="sTtsH"></section><div class="s-text">${html}</div>` + nav('아래');
  $$('.s-text [aria-level]', root).forEach(h => h.setAttribute('aria-level', Math.max(2, +h.getAttribute('aria-level') - 2)));  // 단순 화면은 장 제목이 h1 이라 소제목 단계를 맞춤
  $$('.s-chnav a[data-c]', root).forEach(a => a.onclick = e => { e.preventDefault(); const go = +a.dataset.c, was = SR.speaking; srStop(); srChapter(go, 0, true); if (was) srSpeak(); });
  $('#sSpeak').onclick = () => SR.speaking ? srStop() : srSpeak();
  $('#sTtsBtn').onclick = () => srTtsPanel();
  // 휴대폰(키보드 없음)에서도 단축키 기능을 쓸 수 있게 단추로 (운영자 요청, 2026-11-18)
  $('#sPrevS').onclick = () => { if (SR.speaking && TT.jump) TT.jump(-1); };
  $('#sNextS').onclick = () => { if (SR.speaking && TT.jump) TT.jump(1); };
  $('#sBmBtn').onclick = () => sBookmark();
  $('#sWhereBtn').onclick = () => sWhere();
  $('#sGoPg').onclick = () => sPgForm(true);
  $('#sPgX').onclick = () => sPgForm(false);
  $('#sPgForm').onsubmit = e => { e.preventDefault(); sGoPage($('#sPgIn').value); };
  $('#sPgForm').onkeydown = e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); sPgForm(false); } };
  sAbBtn();
  const h1 = $('.s-h1'); h1.textContent = srName(ch, ci); if (headFn) h1.insertAdjacentHTML('beforeend', headFn); document.title = `${srName(ch, ci)} · ${SR.title} · 단순 화면`;
  const cur = $('.s-path [aria-current]'); if (cur) cur.textContent = srName(ch, ci);
  sStat(`${ci + 1} / ${cs.length} 장`);
  if (push) { try { history.pushState({}, '', `?c=${ci + 1}`); } catch (e) {} lastDoc = location.pathname + location.search; }
  srSavePos(R0.i + 1, ch);
  if (then) { then(); return; }
  const go = () => { const t = page && $('#pm-' + page); if (t) t.scrollIntoView(); else scrollTo(0, 0); h1.focus({ preventScroll: true }); };
  if (document.readyState === 'complete') go(); else addEventListener('load', go, { once: true });
}
function srSavePos(n, ch) {
  const id = SR.id; store.set('pos-' + id, n);  // 일반 읽기 화면에서도 이어 읽게
  const old = store.get('hist', []), h = old.filter(x => x.id !== id);  // 내 서재 '이어 읽기'
  h.unshift({ id, t: SR.title, by: SR.r.by, p: n, pl: (SR.r.pages[n - 1] || {}).label || '', ch: (ch && ch.title) || '', pct: Math.round(n / SR.r.pages.length * 100), first: (old.find(x => x.id === id) || {}).first || today(), d: today(), ts: Date.now() });
  store.set('hist', h.slice(0, 100));
}
function srStop(quiet) {
  TT.gen++; TT.jump = null; SR.si = 0; SR.speaking = false; try { speechSynthesis.cancel(); } catch (e) {} wake(false, 'tts');
  $$('.s-text .speaking').forEach(x => x.classList.remove('speaking'));
  const b = $('#sSpeak'); if (b) b.textContent = '▶ 듣기'; $$('.s-sent').forEach(x => x.hidden = true);
  if (!quiet) toast('듣기를 멈췄습니다');
}
// 화면에 보이는 문단(또는 장 처음)부터 읽음 — 장이 끝나면 다음 장을 그 자리에 그리고 이어 읽음
function srSpeak(fromTop, startAt) {
  if (!('speechSynthesis' in window)) { noVoice(); return; }
  if (!LEX.pali) { toast('읽기를 준비하는 중입니다…'); loadLex().then(() => srSpeak(fromTop)); return; }
  const o = ttsOpt(), pv = pickVoice(o), R0 = SR.r, ch = SR.cs[SR.ci];
  const items = [];
  if (ch.title) items.push({ el: $('.s-h1'), text: sayable(ch.title, o, true), whole: true });
  $$('.s-text [data-pg][data-s]').forEach(el => {
    const pg = R0.pages[+el.dataset.pg - 1]; if (!pg) return; const raw0 = paras(pg.text)[+el.dataset.s]; if (raw0 == null) return;
    if (el.offsetParent === null && !el.closest('.fn-list')) return;  // 장 제목과 같아 숨긴 글
    let raw = raw0; const fg = raw.match(FIG_RE);
    if (fg) { if (R0.say && R0.say[fg[2]]) raw = R0.say[fg[2]]; else return; }
    if (!o.fn && isFootnote(raw0)) return;
    if (isTable(raw0)) { if (!o.table) return; tableLines(raw0).forEach(l => items.push({ el, text: sayable(l, o, true) })); return; }
    items.push({ el, text: sayable(raw.replace(/^\[\^([^\]]+)\]:\s*/, (m, n) => `각주 ${n}. `), o, true) });
  });
  let k = startAt === 'last' ? Math.max(0, items.length - 1) : 0;
  const aS = SR.anchorS; SR.anchorS = null; let aK = -1;
  if (aS && aS.p === SR.anchor && !fromTop && startAt == null) aK = items.findIndex(it => it.el && +it.el.dataset.pg === aS.p && +it.el.dataset.s === aS.s);
  if (aK > 0) k = aK;  // TTS 로 듣던 문단 (내 서재 'TTS 이어 듣기'·책 폴더 '듣기')
  else if (!fromTop && startAt == null) {
    const head = (STALK.el && STALK.el.isConnected ? STALK.el.getBoundingClientRect().bottom : sBarH()) + 4;
    const top = items.findIndex((it, i) => i && it.el && it.el.getBoundingClientRect().bottom > head); if (top > 0 && scrollY > 40) k = top;
    // 맨 위 '▶ 듣기' 단추로 가느라 화면이 장 처음으로 올라갔어도, 읽던 쪽(내 서재 이어 읽기·책갈피로 연 쪽, 마지막으로 보던 쪽)부터 (운영자 요청, 2026-11-18 — 내 서재에서 연 책에서 → 가 듣지 않는 것처럼 보이던 것: 장 처음부터 읽고 있었음)
    else if (SR.anchor) { const a = items.findIndex((it, i) => i && it.el && +it.el.dataset.pg >= SR.anchor); if (a > 0) k = a; }
  }
  try { speechSynthesis.cancel(); } catch (e) {}
  if (STALK.playing()) STALK.au.pause();  // 법문이 나오고 있으면 멈추고 책을 읽음
  SR.speaking = true; wake(true, 'tts'); const b = $('#sSpeak'); if (b) b.textContent = '■ 듣기 멈춤'; $$('.s-sent').forEach(x => x.hidden = false);
  const t0 = SR.t0 || (SR.t0 = Date.now());
  const next = () => {
    if (!SR.speaking) return;
    $$('.speaking').forEach(x => x.classList.remove('speaking'));
    if (o.sleep && Date.now() - t0 > o.sleep * 60000) { srStop(true); toast('정한 시간이 되어 듣기를 멈췄습니다'); return; }
    if (k >= items.length) {
      if (SR.ci >= SR.cs.length - 1) { srStop(true); toast('책의 끝입니다'); return; }
      if (o.chapterStop) { srStop(true); toast('이 장을 다 읽었습니다'); return; }
      srChapter(SR.ci + 1, 0, true, () => { scrollTo(0, 0); srSpeak(true); }); return;
    }
    const it = items[k++]; if (!it.text) { next(); return; }
    if (it.el) { it.el.classList.add('speaking'); if (o.follow) it.el.scrollIntoView({ block: 'nearest' }); ttsFocus(it.el); const n = +it.el.dataset.pg; if (n) { srSavePos(n, ch); ttsPosSave(SR.id, SR.title, n, it.el.dataset.s, (R0.pages[n - 1] || {}).label, ch && ch.title); } }
    const si = SR.si; SR.si = 0;
    speakSents(it.text, o, pv, si, () => { if (SR.speaking) ttsLater(next, Math.max(0, +o.pause * 1000)); }, e => { if (e.error !== 'interrupted' && e.error !== 'canceled') srStop(true); },
      d => { if (!SR.speaking) return; if (d > 0) { next(); return; }
        if (k >= 2) { k -= 2; SR.si = 'last'; next(); return; }  // 앞 문단의 마지막 문장
        if (SR.ci > 0) { const ci = SR.ci - 1; srChapter(ci, 0, true, () => { SR.si = 'last'; srSpeak(true, 'last'); }); return; }
        k = Math.max(0, k - 1); SR.si = 0; next(); }, it.el, it.whole);
  };
  next();
}
// 단순 화면의 듣기 설정 (일반 읽기 화면과 같은 설정을 씀)
function srTtsPanel(force) {
  const s = $('#sTts'), b = $('#sTtsBtn'); if (!s) return false;
  const open = force != null ? force : s.hidden;
  if (!open) { s.hidden = true; if (b) { b.setAttribute('aria-expanded', 'false'); b.focus(); } return true; }
  s.innerHTML = ttsPanel().replace('<h5>', '<h2 id="sTtsH" tabindex="-1">').replace('</h5>', '</h2>');
  s.hidden = false; if (b) b.setAttribute('aria-expanded', 'true');
  $$('[data-tts]', s).forEach(inp => inp.addEventListener(inp.type === 'range' ? 'input' : 'change', () => {
    const o = store.get('tts', {}), k = inp.dataset.tts;
    o[k] = inp.type === 'checkbox' ? inp.checked : (inp.type === 'range' || k === 'pause' || k === 'sleep') ? +inp.value : inp.value; store.set('tts', o);
    if (k === 'rate') { const v = (+inp.value).toFixed(1) + '배'; $('#ttsRateV').textContent = v; inp.setAttribute('aria-valuetext', v); }
    if (k === 'pitch') { $('#ttsPitchV').textContent = (+inp.value).toFixed(1); inp.setAttribute('aria-valuetext', (+inp.value).toFixed(1)); }
    if (k === 'enRate') { const v = Math.round(+inp.value * 100) + '%'; $('#ttsEnRateV').textContent = v; inp.setAttribute('aria-valuetext', v); }
  }));
  const tr = $('#ttsTry', s); if (tr) tr.onclick = () => { if (!('speechSynthesis' in window)) return noVoice(); const o = ttsOpt(); try { speechSynthesis.cancel(); } catch (e) {} speakSegs(sayable('이 빠르기와 목소리로 읽습니다.', o, true), o, pickVoice(o), () => {}, () => {}); };
  const rs = $('#ttsReset', s); if (rs) rs.onclick = () => { store.set('tts', {}); srTtsPanel(true); toast('처음 설정으로 돌렸습니다'); };
  const ap = $('#ttsApply', s); if (ap) ap.onclick = () => { srTtsPanel(false); if (SR.speaking) { srStop(true); srSpeak(); } };
  setTimeout(() => $('#sTtsH').focus(), 30); return true;
}
// 단순 화면 첫 화면의 '로그인 · 회원가입' 줄: 로그인했으면 '내 계정: 아이디' 로 (운영자 요청, 2026-11-18)
function sAcctRow() {
  const tb = $('#sAcctTop'); if (tb && ACC.token) { tb.textContent = '👤 ' + ACC.id; tb.setAttribute('aria-label', `${ACC.id} 내 계정 (로그인됨)`); }  // 첫 화면 위쪽 단추 — 로그인했으면 아이디 (운영자 요청, 2026-11-19)
  if (!ACC.token) return; const li = $$('.s-list > li').find(x => (x.dataset.href || '').startsWith('/simple/account/')); if (!li) return;
  const c1 = $('.s-c1', li), c3 = $('.s-c3', li); if (c1 && !li.dataset.acc) { li.dataset.acc = 1; c1.textContent = `내 계정: ${ACC.id} (로그인됨)`; if (c3) c3.textContent = '로그아웃·비밀번호 바꾸기'; }
}
function initSimpleMine() {
  const root = $('#sMine'); if (!root) return;
  // 내 서재는 폴더 셋 (운영자 요청, 2026-11-18): 맨 위 '최근에 하던 것' 한 줄 + 📖 이어 읽기 · 🎧 이어 듣기(오디오북·법문) · 🔖 책갈피 — 폴더 안은 최근 것이 위
  if (sDelF !== (root.dataset.f || '')) { sDelF = root.dataset.f || ''; sDelOn = false; }  // 다른 폴더로 가면 지우기 고르기는 끔
  const f = root.dataset.f || '', when = x => x.ts || Date.parse(x.d || '') || 0, byRecent = (a, b) => when(b) - when(a);
  const H = store.get('hist', []).slice().sort(byRecent), B = bms().slice().sort(byRecent), TL = store.get(SH, []).slice().sort(byRecent);
  const AL = []; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (!/^dd-abpos-/.test(k)) continue; const v = JSON.parse(localStorage.getItem(k) || 'null'); if (v && v.b) AL.push({ id: k.slice(9), ...v }); } } catch (e) {}
  AL.sort(byRecent);
  const TS = []; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (!/^dd-ttspos-/.test(k)) continue; const v = JSON.parse(localStorage.getItem(k) || 'null'); if (v && v.b && v.p) TS.push({ id: k.slice(10), ...v }); } } catch (e) {}
  TS.sort(byRecent);
  const R_ = h => ({ w: when(h), del: 'hist:' + h.id, nm: `『${h.t}』 이어 읽기`, html: sRow(`/simple/book/${h.id}/read/?p=${h.p}`, [h.t, `이어 읽기${h.ch ? ': ' + h.ch : ''}${h.pl ? ', ' + h.pl + '쪽' : ''}`, `${h.pct || 0}% · ${h.d || ''}`], '📖', 'resume') });
  const A_ = a => ({ w: when(a), del: 'ab:' + a.id, nm: `『${a.b}』 오디오북 이어 듣기`, html: sRow(`/simple/book/${a.id}/read/?audio=1`, [a.b, `오디오북 이어 듣기${a.ch ? ': ' + a.ch : ''}, ${sFmtT(a.t)}부터`, a.d || ''], '🎧', 'abres') });
  const S_ = a => ({ w: when(a), del: 'tts:' + a.id, nm: `『${a.b}』 TTS 이어 듣기`, html: sRow(`/simple/book/${a.id}/read/?listen=1&p=${a.p}&s=${a.s || 0}`, [a.b, `TTS 이어 듣기${a.ch ? ': ' + a.ch : ''}${a.pl ? ', ' + a.pl + '쪽' : ''}`, a.d || ''], '🔊', 'ttsres') });
  const T_ = h => ({ w: when(h), ep: h, del: 'ep:' + h.a, nm: `법문 「${h.t}」 이어 듣기`, html: sRow(h.a, [h.t, `법문 이어 듣기: ${sFmtT(h.pos)}${h.dur ? ' / ' + sFmtT(h.dur) : ''}${h.pl ? ' · ' + h.pl : ''}`, h.d || ''], '🎙', 'ep') });
  const M_ = m => ({ w: when(m), del: `bm:${m.id}|${m.p}`, nm: `『${m.t}』 ${m.pl ? m.pl + '쪽' : m.p + '번째 쪽'} 책갈피`, html: sRow(`/simple/book/${m.id}/read/?p=${m.p}`, [m.t, `책갈피: ${m.pl ? m.pl + '쪽' : m.p + '번째 쪽'}${m.note ? ' – ' + m.note : ''}`, m.d || ''], '🔖', 'bm') });
  let items, label, stat;
  if (f === 'read') { items = H.map(R_); label = `이어 읽기, 읽던 책 ${H.length}권`; stat = `읽던 책 ${H.length}`; }
  else if (f === 'tts') { items = TS.map(S_); label = `TTS 이어 듣기, 기기 목소리로 듣던 책 ${TS.length}권`; stat = `TTS로 듣던 책 ${TS.length}`; }
  else if (f === 'listen') { items = AL.map(A_).concat(TL.map(T_)).sort((x, y) => y.w - x.w); label = `음성 녹음 이어 듣기, 오디오북 ${AL.length}개, 법문 ${TL.length}개`; stat = `오디오북 ${AL.length} · 법문 ${TL.length}`; }
  else if (f === 'bm') { items = B.map(M_); label = `책갈피 ${B.length}개`; stat = `책갈피 ${B.length}`; }
  else {
    const last = [H[0] && R_(H[0]), TS[0] && S_(TS[0]), AL[0] && A_(AL[0]), TL[0] && T_(TL[0])].filter(Boolean).sort((x, y) => y.w - x.w)[0];
    items = [];
    if (last) items.push({ ...last, html: last.html.replace(/<span class="s-ic" aria-hidden="true">[^<]*<\/span>/, '<span class="s-ic" aria-hidden="true">⏯</span>').replace(/(<span class="s-c s-c1[^"]*"[^>]*>)/, '$1<span class="sr">최근에 하던 것: </span>') });
    const F = (h, t, n, ic) => ({ html: sRow(h, [t, '폴더', n], ic, 'folder') });
    if (H.length) items.push(F('/simple/mine/read/', '이어 읽기', `읽던 책 ${H.length}권`, '📖'));
    if (TS.length) items.push(F('/simple/mine/tts/', 'TTS 이어 듣기', `기기 목소리로 듣던 책 ${TS.length}권`, '🔊'));
    if (AL.length || TL.length) items.push(F('/simple/mine/listen/', '음성 녹음 이어 듣기', [AL.length && `오디오북 ${AL.length}개`, TL.length && `법문 ${TL.length}개`].filter(Boolean).join(', '), '🎧'));
    if (B.length) items.push(F('/simple/mine/bm/', '책갈피', `${B.length}개`, '🔖'));
    label = '내 서재'; stat = `읽던 책 ${H.length} · TTS ${TS.length} · 음성 녹음 ${AL.length + TL.length} · 책갈피 ${B.length}`;
  }
  const acc = f ? '' : (ACC.token ? `<p class="s-acct-note">👤 ${esc(ACC.id)} 님으로 로그인되어 있습니다 — 다른 기기에서도 같은 아이디로 로그인하면 이 기록이 이어집니다. <a href="/simple/account/">내 계정</a></p>` : `<p class="s-acct-note">로그인하면 다른 기기에서도 이어 읽기·이어 듣기·책갈피가 이어집니다. <a href="/simple/account/">로그인 · 회원가입</a></p>`);  // 운영자 요청, 2026-11-18
  root.innerHTML = acc + (items.length ? `<div class="s-tbl" style="--cols:minmax(0,2fr) minmax(0,2.4fr) minmax(0,1fr)">` + sHead(['이름', '어디', '언제']) + `<ul class="s-list" data-label="${esc(label)}">${items.map(x => x.html).join('')}</ul></div>` : '<p>아직 이 기기에서 읽거나 들은 책·법문이 없습니다. 책을 읽거나 법문·오디오북을 들으면 여기에 이어 읽을 곳·이어 들을 곳이 남습니다.</p>');
  const eps = items.filter(x => x.ep);
  $$('.s-list > li.k-ep', root).forEach((li, i) => { const h = eps[i].ep; li.dataset.t = h.t; li.dataset.pl = h.pl; li.dataset.src = h.p || '/simple/talks/'; li.dataset.pos = h.pos || 0; });
  // 기록 지우기 (운영자 요청, 2026-11-19): 줄에서 Delete 키 → 그 줄 하나. 폴더 안에서는 '🗑 지울 기록 고르기'를 켜고
  // 줄을 누르거나 Space 로 여러 개를 골라(☐ ↔ ☑) '고른 기록 지우기' → 한 번 더 묻고 지움
  const lis = $$('.s-list > li', root); items.forEach((x, i) => { if (x.del && lis[i]) { lis[i].dataset.del = x.del; lis[i].dataset.nm = x.nm; } });
  const ul = $('.s-list', root), dels = $$('.s-list > li[data-del]', root);
  if (ul && dels.length) {
    ul._del = sDelAsk;
    const mode = sDelOn && !!f;
    ul._delMode = mode; ul.classList.toggle('delmode', mode);
    if (mode) {
      for (const k of [...sPicked]) if (!dels.some(li => li.dataset.del === k)) sPicked.delete(k);
      dels.forEach(li => sPickShow(li));
      ul._pick = li => { const k = li.dataset.del, on = !sPicked.has(k); if (on) sPicked.add(k); else sPicked.delete(k); sPickShow(li); sPickBar(); sayKey(`${li.dataset.nm || ''} ${on ? '골라짐' : '고르기 풀림'}. 지금 고른 기록 ${sPicked.size}개`); };
    }
    if (f) {
      root.insertAdjacentHTML('beforeend', `<div class="s-del-row" id="sDelRow"></div>`);
      sPickBar();
    } else root.insertAdjacentHTML('beforeend', `<p class="s-del-row"><span class="s-del-hint">기록을 여러 개 지우려면 폴더를 열고 '🗑 지울 기록 고르기'를 누르세요. 컴퓨터에서는 줄에서 Delete 키로 그 줄을 지울 수 있습니다.</span></p>`);
  }
  sStat(stat); if (!sDelKeep) sFocusFirst();
}
let sDelOn = false, sDelKeep = false, sDelF = null;
const sPicked = new Set();
function sPickShow(li) {
  const on = sPicked.has(li.dataset.del), ic = $('.s-ic', li);
  if (ic) ic.textContent = on ? '☑' : '☐';
  li.classList.toggle('picked', on);  // 낭독기에는 줄 이름 끝의 ', 지우려고 골라짐' 글로 알림(aria-checked 는 낭독기마다 달리 읽고, 커서 표시 aria-selected '선택됨'과 헷갈려 쓰지 않음)
  let sr = $('.s-pk', li); if (!sr) { sr = document.createElement('span'); sr.className = 'sr s-pk'; (li.firstElementChild || li).appendChild(sr); }
  sr.textContent = on ? ', 지우려고 골라짐' : ', 고르지 않음';
}
function sPickBar() {
  const row = $('#sDelRow'); if (!row) return;
  const n = sPicked.size, total = $$('#sMine .s-list > li[data-del]').length, keep = document.activeElement && document.activeElement.id;
  row.innerHTML = sDelOn
    ? `<button type="button" class="s-btn s-delgo" id="sDelGo"${n ? '' : ' aria-disabled="true"'}>🗑 고른 기록 지우기 (${n}개)</button> <button type="button" class="s-btn" id="sDelAll">${n && n === total ? '모두 풀기' : '모두 고르기'}</button> <button type="button" class="s-btn" id="sDelMode" aria-pressed="true">그만두기</button><p class="s-del-hint">줄을 누르면 ☐ 고르기 · ☑ 풀기입니다. 컴퓨터에서는 ↑↓ 로 옮기고 Space 로 고릅니다.</p>`
    : `<button type="button" class="s-btn s-delmode" id="sDelMode" aria-pressed="false">🗑 지울 기록 고르기</button> <span class="s-del-hint">여러 개를 골라 한꺼번에 지울 수 있습니다. 컴퓨터에서는 줄에서 Delete 키로 그 줄만 바로 지울 수도 있습니다.</span>`;
  if (keep && $('#' + keep, row)) $('#' + keep, row).focus();
  $('#sDelMode').onclick = () => {
    sDelOn = !sDelOn; sPicked.clear(); sDelKeep = true; initSimpleMine(); sDelKeep = false;
    if (sDelOn) { const lb = $('#sMine .s-list'); if (lb && lb._lb) lb._lb.focus(); else sFocusFirst(); sayKey('지울 기록 고르기. 줄을 누르거나 Space 로 고르세요'); }
    else { const b = $('#sDelMode'); if (b) b.focus(); sayKey('고르기를 그만두었습니다'); }
  };
  const all = $('#sDelAll'); if (all) all.onclick = () => {
    const lis = $$('#sMine .s-list > li[data-del]'), clear = sPicked.size && sPicked.size === lis.length;
    lis.forEach(li => { if (clear) sPicked.delete(li.dataset.del); else sPicked.add(li.dataset.del); sPickShow(li); });
    sPickBar(); sayKey(clear ? '모두 풀었습니다' : `모두 골랐습니다. ${sPicked.size}개`);
  };
  const go = $('#sDelGo'); if (go) go.onclick = () => {
    if (!sPicked.size) { sayKey('먼저 지울 기록을 고르세요'); return; }
    const ks = [...sPicked], one = ks.length === 1 ? ($$('#sMine .s-list > li[data-del]').find(li => li.dataset.del === ks[0]) || {}).dataset : null;
    const nms = ks.map(k => ($$('#sMine .s-list > li[data-del]').find(li => li.dataset.del === k) || {}).dataset).filter(Boolean).map(d => d.nm);
    sAsk(one ? `${one.nm} 기록을 지울까요?` : `고른 기록 ${ks.length}개를 지울까요? ${nms.slice(0, 6).join(', ')}${nms.length > 6 ? ` 외 ${nms.length - 6}개` : ''}.`, () => {
      ks.forEach(sDelDo); sPicked.clear(); sDelOn = false;
      sDelDone(one ? `${one.nm} 기록을 지웠습니다` : `기록 ${ks.length}개를 지웠습니다`);
    }, go);
  };
}
function sDelDo(d) {
  const i = d.indexOf(':'), t = d.slice(0, i), v = d.slice(i + 1);
  if (t === 'hist') store.set('hist', store.get('hist', []).filter(x => x.id !== v));
  else if (t === 'tts') store.set('ttspos-' + v, null);   // null 로 두어야 로그인한 다른 기기에서도 지워짐(동기화)
  else if (t === 'ab') store.set('abpos-' + v, null);
  else if (t === 'ep') sHistDel(v);
  else if (t === 'bm') { const [id, pg] = v.split('|'); store.set('bm', bms().filter(m => !(m.id === id && String(m.p) === pg))); }
}
function sDelDone(msg) {
  const f = ($('#sMine') || {}).dataset || {}; sDelKeep = true; initSimpleMine(); sDelKeep = false;
  if (f.f && !$('#sMine .s-list > li[data-del]')) { sayKey(`${msg}. 이 폴더가 비어 내 서재로 갑니다`, () => sGo('/simple/mine/')); return; }
  sFocusFirst(); sayKey(msg);
}
// 지우기 전에 한 번 더 묻는 상자 (목록 아래, role=alertdialog — Esc 는 그만두기)
function sAsk(q, yes, back) {
  const old = $('#sDelAsk'); if (old) old.remove();
  const at = $('#sMine .s-tbl') || $('#sMine .s-list'); if (!at) return;
  at.insertAdjacentHTML('afterend', `<div id="sDelAsk" class="s-delask" role="alertdialog" aria-labelledby="sDelQ"><p id="sDelQ">${esc(q)}${ACC.token ? ' 로그인한 다른 기기에서도 지워집니다.' : ''}</p><button type="button" class="s-btn" id="sDelYes">🗑 지우기</button> <button type="button" class="s-btn" id="sDelNo">그만두기</button></div>`);
  const box = $('#sDelAsk'), no = () => { box.remove(); try { back.focus(); } catch (e) {} sayKey('그만두었습니다'); };
  $('#sDelNo').onclick = no;
  $('#sDelYes').onclick = () => { box.remove(); yes(); };
  box.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); no(); } });
  $('#sDelYes').focus(); box.scrollIntoView({ block: 'nearest' });
}
function sDelAsk(li) {
  const nm = li.dataset.nm || '이';
  sAsk(`${nm} 기록을 지울까요?`, () => { sDelDo(li.dataset.del); sPicked.delete(li.dataset.del); sDelDone(`${nm} 기록을 지웠습니다`); }, li);
}
function initSimpleFind() {
  const q = $('#sQ'); if (!q) return;
  let data = []; try { data = JSON.parse($('#sFindData').textContent); } catch (e) {}
  const out = $('#sFindList'), msg = $('#sFindMsg'), nz = s => norm(String(s || '')).toLowerCase().replace(/\s/g, '');
  let t = 0;
  const run = () => {
    const w = nz(q.value); if (!w) { out.innerHTML = ''; msg.textContent = `책 ${data.length}권에서 찾습니다. 찾을 말을 넣으면 아래에 결과가 나오고, ↓ 키로 결과 목록에 들어갑니다.`; sStat(''); return; }
    const hit = data.filter(d => nz(d[1] + d[2] + d[5]).includes(w));
    out.innerHTML = hit.length ? '<div class="s-tbl">' + sHead(['이름', '지은이 · 옮긴이', '등록일', '형식']) + `<ul class="s-list" data-label="찾은 책 ${hit.length}권">${hit.map(d => sRow(`/simple/book/${d[0]}/`, [d[1], d[2], d[3] ? d[3] + ' 등록' : '', d[4]], '📕', 'book')).join('')}</ul></div>` : '';
    const ul = $('.s-list', out); if (ul) ul._lb = sListbox(ul);
    msg.textContent = hit.length ? `${hit.length}권을 찾았습니다. ↓ 키로 목록에 들어갑니다.` : '찾은 책이 없습니다.'; sStat(hit.length ? `찾은 책 ${hit.length}` : '');
  };
  q.addEventListener('input', () => { clearTimeout(t); t = setTimeout(run, 250); });
  q.addEventListener('keydown', e => { if ((e.key === 'ArrowDown' || e.key === 'Enter') && $('.s-list', out)) { e.preventDefault(); $('.s-list', out)._lb.pick(0); } });
  run(); const go = () => q.focus(); if (document.readyState === 'complete') go(); else addEventListener('load', go, { once: true });
}
const S_KEYS = [['→', '다음 쪽 (장 글 화면에서)'], ['←', '앞 쪽'], ['↓', '다음 장 (목차의 다음 항목)'], ['↑', '앞 장'], ['P', '토글: 듣기 시작·멈춤 (책의 장 글 화면에서, 듣는 동안 커서가 읽는 문단을 따라감 · 법문이 나오고 있으면 먼저 법문을 멈춤 · 그 밖의 화면에서는 법문 재생·멈춤)'], ['A', '토글: 맨 위 재생기(법문·오디오북)로 가기·원래 자리로 돌아오기 — 오디오북이 있는 책의 장 글 화면에서는 오디오북 단추로'], ['.', '다음 법문·다음 장 (점)'], [',', '앞 법문·앞 장 (쉼표)'], [']', '15초 앞으로'], ['[', '15초 뒤로'], ['C', '지금 읽는 문단을 클립보드에 복사'], ['', '듣는 중에 → ← (Alt·Shift 없이): 다음 문장·앞 문장'], ['S', '토글: 듣기 설정 열기·닫기 (장 글 화면에서)'], ['V', '토글: 화면 바꾸기 (누를 때마다 기본 → 흑백 → 밤 → 고대비)'], ['N', '장 목록으로 (책을 읽을 때)'], ['B', '토글: 지금 읽는 쪽에 책갈피 넣기·빼기'], ['L', '내 서재 (이어 읽기·책갈피)'], ['M', '첫 화면 (폴더 목록)'], ['K', '지금 위치 알리기'], ['H', '토글: 단축키 안내 열기·닫기']];
function simpleHelp() {
  const old = $('#sKeys'); if (old) { old.remove(); const b = $('.s-list [aria-selected="true"]') || $('.s-h1'); if (b) b.focus(); return; }
  $('.s-h1').insertAdjacentHTML('afterend', `<section id="sKeys" class="s-keys" aria-labelledby="sKeysH"><h2 id="sKeysH" tabindex="-1">단축키 안내</h2><p tabindex="0">Alt 키와 Shift 키를 함께 누른 채로 글자 키를 누릅니다 (맥은 Option + Shift). Tab 키로 한 줄씩 들으실 수 있습니다.</p><ul>${S_KEYS.map(([k, d]) => `<li tabindex="0">${k ? `<kbd>Alt+Shift+${k}</kbd> ` : ''}${d}</li>`).join('')}<li tabindex="0"><kbd>↑</kbd> <kbd>↓</kbd> 목록에서 줄 고르기, <kbd>Enter</kbd> 열기, <kbd>Backspace</kbd> 위 목록으로</li><li tabindex="0"><kbd>Delete</kbd> 내 서재 목록에서 고른 기록 지우기 (지울지 한 번 더 묻습니다)</li></ul><button type="button" class="s-btn" id="sKeysX">단축키 안내 닫기</button></section>`);
  $('#sKeysX').onclick = simpleHelp; $('#sKeysH').focus();
  $('#sKeys').addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); simpleHelp(); return; }
    if (e.key !== 'Tab' || e.altKey || e.ctrlKey || e.metaKey) return;  // 안내 안에서 Tab 은 줄마다, 끝에서 처음으로 돎
    const f = $$('#sKeys [tabindex="0"], #sKeys button'), i = f.indexOf(document.activeElement);
    if (e.shiftKey ? i <= 0 : i === f.length - 1) { e.preventDefault(); f[e.shiftKey ? f.length - 1 : 0].focus(); }
  });
}
// 위쪽 파란 줄(◀ 뒤로·▲ 위로·지금 위치) 높이 — 쪽 표시가 그 뒤로 숨지 않게 그만큼 내려 둠 (운영자 요청, 2026-11-18)
const sBarH = () => { const b = $('.s-bar'); const h = b ? Math.ceil(b.getBoundingClientRect().bottom) : 0; document.documentElement.style.setProperty('--sbar', h + 'px'); return h; };
function sGoMark(m) {
  SR.pm = m.id; sBarH(); m.scrollIntoView({ block: 'start' });  // CSS scroll-margin-top 이 파란 줄 높이만큼 띄움
  if (m.textContent.trim()) { kbFocus(m); sayKey(m.textContent.trim()); } else { sayKey(`${+m.id.slice(3)}번째 쪽`); kbFocus(m.nextElementSibling || m); }
}
function sPage(d) {
  const ms = $$('.s-text [id^="pm-"]'); if (!ms.length) { sChap(d); return; }
  const top = sBarH() + 24;
  let cur = -1; ms.forEach((m, i) => { if (m.getBoundingClientRect().top <= top) cur = i; });
  { const k = ms.findIndex(m => m.id === SR.pm); if (k >= 0) { const r = ms[k].getBoundingClientRect(); if (r.top >= 0 && r.top < innerHeight) cur = k; } }  // 방금 옮겨 간 쪽(장 끝 짧은 쪽처럼 맨 위로 못 올라간 쪽도)
  const j = cur + d;
  if (j >= ms.length) { sChap(1); return; }       // 장의 마지막 쪽 → 다음 장 처음
  if (j < 0) { sChap(-1, true); return; }         // 장의 첫 쪽 → 앞 장의 마지막 쪽
  sGoMark(ms[j]);
}
function sChap(d, toEnd) {
  const go = SR.ci + d; if (go < 0 || go >= SR.cs.length) { toast(d > 0 ? '책의 끝입니다' : '책의 처음입니다'); return; }
  const was = SR.speaking; srStop(true); SR.pm = null;
  srChapter(go, 0, true, () => {
    const ms = $$('.s-text [id^="pm-"]');
    if (toEnd && ms.length > 1) { sGoMark(ms[ms.length - 1]); return; }
    scrollTo(0, 0); $('.s-h1').focus({ preventScroll: true }); if (was) srSpeak(true); else sayKey($('.s-h1').textContent.trim());
  });
}
function simpleKey(e) {
  const k = (e.code || '').replace(/^Key/, ''), reading = !!(SR.r && $('#sSpeak'));
  if (/^Arrow/.test(k)) { if (!reading) { sayKey('쪽·장 넘기기는 책의 장 글 화면에서 쓸 수 있습니다'); return true; } ({ ArrowRight: () => sPage(1), ArrowLeft: () => sPage(-1), ArrowDown: () => sChap(1), ArrowUp: () => sChap(-1) })[k](); return true; }
  switch (k) {
    case 'V': cycleMode(); return true;
    case 'A': {  // 법문 재생기로 바로 가기 — 다시 누르면 원래 있던 곳으로 (운영자 요청, 2026-11-18)
      const pb = STALK.el && STALK.list.length && $('#sPlay', STALK.el);
      if (!pb) { const ab = $('#sAb'); if (ab) { ab.focus(); sayKey('오디오북 단추. Enter 를 누르면 재생합니다'); return true; } sayKey('듣는 것이 없습니다. 법문 목록이나 오디오북이 있는 책에서 고르세요'); return true; }
      if (STALK.el.contains(document.activeElement)) { const r = STALK.ret; STALK.ret = null; if (r && r.isConnected) r.focus(); else { const b = $('.s-list [aria-selected="true"]') || $('.s-h1'); if (b) b.focus(); } sayKey('재생기에서 돌아옴'); return true; }
      STALK.ret = document.activeElement; pb.focus(); sayKey('재생기. ' + (STALK.now() || '')); return true;
    }
    case 'Period': if (!STALK.step || !STALK.list.length) { sayKey('듣는 것이 없습니다'); return true; } STALK.step(1); return true;
    case 'Comma': if (!STALK.step || !STALK.list.length) { sayKey('듣는 것이 없습니다'); return true; } STALK.step(-1); return true;
    case 'BracketRight': if (!STALK.seek) { sayKey('듣는 것이 없습니다'); return true; } STALK.seek(15); return true;
    case 'BracketLeft': if (!STALK.seek) { sayKey('듣는 것이 없습니다'); return true; } STALK.seek(-15); return true;
    case 'H': simpleHelp(); sayKey($('#sKeys') ? '단축키 안내' : '단축키 안내 닫힘'); return true;
    case 'C': if (!SR.r) { sayKey('책의 장 글 화면에서 쓸 수 있습니다'); return true; } copyNow('.s-text'); return true;
    case 'P': if (reading && STALK.playing()) { STALK.toggle(); sayKey('재생 멈춤'); return true; }  // 책 글 화면에서도 법문이 나오고 있으면 먼저 법문을 멈춤
      if (!reading && (STALK.list.length || $('#sPlayerSlot'))) { sPlayerMake(); STALK.toggle(); return true; } if (!reading) { sayKey('듣기는 책의 장 글 화면에서 쓸 수 있습니다. 책 → 온라인으로 읽기 → 장을 고르세요'); return true; } if (SR.speaking) { srStop(true); sayKey('듣기 멈춤'); } else srSpeak(); return true;
    case 'S': if (!reading) { sayKey('듣기 설정은 책의 장 글 화면에서 쓸 수 있습니다'); return true; } srTtsPanel(); sayKey($('#sTts') && !$('#sTts').hidden ? '듣기 설정' : '듣기 설정 닫힘'); return true;
    case 'N': if (!SR.r) { sayKey('책을 읽을 때 쓰는 키입니다'); return true; } sayKey('장 목록', () => sGo('./')); return true;
    case 'L': sayKey('내 서재', () => sGo('/simple/mine/')); return true;
    case 'M': sayKey('첫 화면', () => sGo('/simple/')); return true;
    case 'B': if (!reading) { sayKey('책갈피는 책의 장 글 화면에서 넣을 수 있습니다'); return true; } sBookmark(); return true;
    case 'K': sWhere(); return true;
  }
  return false;
}
// 단순 화면 장 글: 책갈피·지금 위치·쪽으로 가기 — 단축키(B·K)와 단추가 함께 씀
function sCurEl() { const sp = SR.speaking && $('.s-text .speaking'); return sp || $$('.s-text [data-pg]').find(x => x.getBoundingClientRect().bottom > 80) || $('.s-text [data-pg]'); }
function sBookmark() {
  const el = sCurEl(); if (!el || !SR.r) return;
  const n = +el.dataset.pg, pg = SR.r.pages[n - 1] || { n }, l = store.get('bm', []), i = l.findIndex(m => m.id === SR.id && m.p === n);
  let msg; if (i > -1) { l.splice(i, 1); msg = `${pageName(pg)}의 책갈피를 지웠습니다`; } else { l.push({ id: SR.id, t: SR.title, p: n, pl: pg.label || '', note: '', d: today() }); msg = `${pageName(pg)}에 책갈피를 달았습니다`; }
  store.set('bm', l); sayKey(msg);
}
function sWhere() {
  const reading = !!(SR.r && $('#sSpeak'));
  const path = $$('.s-path a, .s-path [aria-current]').map(x => x.textContent.trim()).join(', ');
  const o = $('.s-list [aria-selected="true"] .s-c1');
  let m = `지금 위치: ${path}`;
  if (STALK.now && STALK.now()) m += ', ' + STALK.now();
  if (reading) { const el = sCurEl(); if (el) m += `, ${pageName(SR.r.pages[+el.dataset.pg - 1] || {})}`; if (SR.speaking) m += ', 듣는 중'; }
  else if (o) m += `, 고른 줄: ${o.textContent.trim()}`;
  sayKey(m);
}
function sPgForm(on) {
  const f = $('#sPgForm'), b = $('#sGoPg'); if (!f) return;
  f.hidden = !on; if (b) b.setAttribute('aria-expanded', on);
  if (on) { const i = $('#sPgIn'); i.value = ''; i.focus(); } else if (b) b.focus();
}
// 책에 인쇄된 쪽 번호(쪽 이름)로 가기 — 다른 장이면 그 장을 그림. 쪽 표시가 없는 번호는 그 번호를 품은 앞 쪽으로 (운영자 요청, 2026-11-18)
function sGoPage(v) {
  const q = String(v || '').trim().replace(/^(p\.?|쪽)\s*/i, '').replace(/\s*(쪽|페이지|p)$/i, '').trim(); if (!q || !SR.r) return;
  const pages = SR.r.pages, lab = p => String(p.label || '').trim();
  let idx = pages.findIndex(p => lab(p) === q), via = '';
  if (idx < 0 && /^\d+$/.test(q)) { const num = +q; let best = -1; pages.forEach((p, i) => { const l = lab(p); if (/^\d+$/.test(l) && +l < num) best = i; }); if (best > -1 && pages.some(p => /^\d+$/.test(lab(p)) && +lab(p) > num)) { idx = best; via = ` (${lab(pages[best])}쪽에 이어짐)`; } }
  if (idx < 0) { sayKey(`${q}쪽을 이 책에서 찾지 못했습니다`); return; }
  const n = idx + 1, ci = withR(() => chapterOf(n)), was = SR.speaking;
  if (was) srStop(true);
  const go = () => { const t = $('#pm-' + n); if (t) { SR.pm = t.id; sBarH(); t.scrollIntoView({ block: 'start' });  /* 파란 줄 높이를 먼저 재야 쪽이 그 뒤로 숨지 않음 (2026-11-18 다시 검수) */ t.setAttribute('tabindex', '-1'); t.focus({ preventScroll: true }); } if (!t || document.activeElement !== t) { const f = $$(`.s-text [data-pg="${n}"]`).find(x => x.getClientRects().length) || $('.s-h1'); if (f) { if (!f.hasAttribute('tabindex')) f.setAttribute('tabindex', '-1'); f.focus({ preventScroll: !!t }); } }  /* 숨은 쪽 표시(장 첫 쪽)면 그 쪽 첫 문단·장 제목에 커서 (2026-11-18 전체 검수) */ SR.anchor = n; sayKey(`${q}쪽${via}`, was ? () => srSpeak() : null); };  // 듣는 중이면 쪽 이름을 다 읽은 뒤 이어 읽음(바로 읽으면 알림이 끊김)
  $('#sPgForm').hidden = true; const gb = $('#sGoPg'); if (gb) gb.setAttribute('aria-expanded', 'false');
  if (ci !== SR.ci) { srChapter(ci, n, true, go); } else go();
}
// 단순 화면 한 장을 열 때마다 (처음 열 때·sGo 로 본문만 바꿀 때)
function sPageInit() {
  const back = $('#sBack'); if (back) back.onclick = () => { if (history.length > 1 && (document.referrer.startsWith(location.origin) || STALK.playing())) history.back(); else sGo(($('#sUp') || {}).href || '/simple/'); };
  const pg = document.body.dataset.page;
  STALK.pageList = null;
  sResumeCount();
  if (pg === 'simple-talk') initSimpleTalk(); else sPlayerPlace();
  if (pg === 'simple-read') initSimpleRead(); else if (pg === 'simple-mine') initSimpleMine(); else if (pg === 'simple-find') initSimpleFind(); else if (pg === 'simple-acct') initAccount();
  else if (pg === 'simple-text' || pg === 'simple-acct') { const go = () => $('.s-h1').focus({ preventScroll: true }); if (document.readyState === 'complete') go(); else addEventListener('load', go, { once: true }); }
  else sFocusFirst();
  sAcctRow();
}
(function initSimple() {
  // 어느 화면에서든 '단순 | 일반'을 고르면 기기가 기억
  document.addEventListener('click', e => { const a = e.target.closest('[data-ui]'); if (a) store.set('ui', a.dataset.ui); });
  if (!document.body.classList.contains('simple-ui')) return;
  sPageInit();
  // 법문을 듣는 중에는 단순 화면 안의 링크를 부드럽게 옮겨 감(재생기가 끊기지 않게)
  document.addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || !STALK.playing()) return;
    const a = e.target.closest('a[href]'); if (!a || a.target || a.hasAttribute('download') || a.dataset.ui || a.origin !== location.origin || !a.pathname.startsWith('/simple/')) return;
    e.preventDefault(); sGo(a.href);
  });
  // 단순 화면에서도 Alt+Shift 단축키 (운영자 요청, 2026-11-18)
  document.addEventListener('keydown', e => { if (e.altKey && e.shiftKey && !e.ctrlKey && !e.metaKey && simpleKey(e)) e.preventDefault(); });
  // 듣는 중 ← → 는 앞·다음 문장 (운영자 요청, 2026-11-18)
  document.addEventListener('keydown', e => { if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && !e.shiftKey && !e.altKey && !e.ctrlKey && !e.metaKey && SR.speaking && TT.jump && !e.target.matches('input,textarea,select,[role=option]')) { e.preventDefault(); TT.jump(e.key === 'ArrowRight' ? 1 : -1); } });
  // 목록 밖에서도 Backspace 로 위 목록으로 (입력 칸 밖에서만)
  document.addEventListener('keydown', e => { if (e.key === 'Backspace' && !e.altKey && !e.ctrlKey && !e.target.matches('input,textarea,select,.s-list,.s-list *')) { const u = $('#sUp'); if (u) { e.preventDefault(); u.click(); } } });
})();
})();
