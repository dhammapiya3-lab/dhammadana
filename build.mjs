// 테라와다불교 법보시 도서관 — 정적 사이트 만들기
// content/ 의 자료를 읽어 dist/ 에 사이트를 만듭니다. (Cloudflare Pages: 빌드 명령 `npm run build`, 출력 폴더 `dist`)
import fs from 'node:fs';
import path from 'node:path';
import { marked } from 'marked';

const ROOT = path.dirname(new URL(import.meta.url).pathname);
const C = p => path.join(ROOT, 'content', p);
const OUT = path.join(ROOT, 'dist');
const readJSON = p => JSON.parse(fs.readFileSync(C(p), 'utf8'));
import crypto from 'node:crypto';
const ver = f => crypto.createHash('md5').update(fs.readFileSync(path.join(ROOT, 'public', f))).digest('hex').slice(0, 8);
const V = { css: ver('assets/site.css'), js: ver('assets/app.js') };

/* ---------- 자료 읽기 ---------- */
function readMd(file) {
  const raw = fs.readFileSync(file, 'utf8');
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  const meta = {};
  let body = raw;
  if (m) {
    body = m[2];
    for (const line of m[1].split('\n')) {
      const i = line.indexOf(':');
      if (i < 1) continue;
      let v = line.slice(i + 1).trim();
      if (/^".*"$/.test(v) || /^'.*'$/.test(v)) v = v.slice(1, -1);
      meta[line.slice(0, i).trim()] = v;
    }
  }
  return { meta, body, html: marked.parse(body) };
}
const S = readJSON('settings.json');
const TRADS = readJSON('traditions.json').items;
const TEACHERS = readJSON('teachers.json').items;
const TOPICS_RAW = readJSON('topics.json');
const TOPICS = { main: TOPICS_RAW.main.map(x => x.label), groups: [] };
for (const it of TOPICS_RAW.items) { let g = TOPICS.groups.find(x => x.name === it.group); if (!g) TOPICS.groups.push(g = { name: it.group, labels: [] }); g.labels.push(it.label); }
const PROVIDERS = readJSON('providers.json').items;
const PERMS = readJSON('permissions.json').items;
const LINKS = readJSON('links.json').groups;
const PLAYLISTS = readJSON('playlists.json').items;
const VARIANTS = readJSON('variants.json').items.map(v => v.words);
const BOOKS = fs.readdirSync(C('books')).filter(f => f.endsWith('.json'))
  .map(f => JSON.parse(fs.readFileSync(C('books/' + f), 'utf8')))
  .filter(b => !b.hidden)
  .sort((a, b) => (b.added || '').localeCompare(a.added || '') || (b.order || 0) - (a.order || 0) || b.id.localeCompare(a.id));
// 글로 읽기 본문 (관리자 화면에서 고치는 글): content/texts/<자료번호>.json
const TEXTS = {};
if (fs.existsSync(C('texts'))) for (const f of fs.readdirSync(C('texts')).filter(f => f.endsWith('.json'))) {
  const t = JSON.parse(fs.readFileSync(C('texts/' + f), 'utf8'));
  if (!t.book || !t.body) continue;
  const pages = []; const re = /^===\s*(.*?)\s*===\s*$/gm; let m, last = null;
  const body = t.body.replace(/\r\n/g, '\n');
  while ((m = re.exec(body))) { if (last) last.text = body.slice(last.start, m.index).trim(); last = { label: m[1].replace(/\s*쪽$/, ''), start: re.lastIndex }; pages.push(last); }
  if (last) last.text = body.slice(last.start).trim();
  if (!pages.length) pages.push({ label: '', text: body.trim() });
  TEXTS[t.book] = { edition: t.edition || '', pages: pages.map(p => ({ label: p.label, text: p.text })), toc: (t.toc || []).filter(x => x && x.title && x.page).map(x => ({ title: (x.sub ? '  ' : '') + x.title, page: +x.page })) };
}
const NEWS = fs.readdirSync(C('news')).filter(f => f.endsWith('.md')).map(f => {
  const d = readMd(C('news/' + f));
  return { slug: f.replace(/\.md$/, ''), ...d.meta, html: d.html, text: d.body };
}).sort((a, b) => (b.date || '').localeCompare(a.date || ''));
const PAGES = Object.fromEntries(fs.readdirSync(C('pages')).filter(f => f.endsWith('.md')).map(f => [f.replace(/\.md$/, ''), readMd(C('pages/' + f))]));

const teacherById = id => TEACHERS.find(t => t.id === id);
const tradById = id => TRADS.find(t => t.id === id);
const tradOfTeacher = id => tradById(teacherById(id)?.tradition);
const providerById = id => PROVIDERS.find(p => p.id === id);
const permById = id => PERMS.find(p => p.id === id);
const curEd = b => (b.editions || []).find(e => e.current) || (b.editions || [])[0] || {};
const fileUrl = u => !u ? '' : /^https?:\/\//.test(u) ? u : S.files_base.replace(/\/$/, '') + '/' + u.replace(/^\//, '');
function formats(b) {
  const e = curEd(b), f = [];
  const ok = x => x && x.mode && x.mode !== 'none' && x.url;
  const both = ok(e.pdf) && ok(e.pdf_print);
  const add = (kind, k, name) => {
    const x = e[kind]; if (!ok(x)) return;
    if (x.mode === 'link') { f.push({ k, name, ext: true, url: fileUrl(x.url), site: x.site || '제공처 사이트' }); return; }
    if (/^https?:/.test(x.url)) { f.push({ k, name, ext: false, url: x.url }); return; }
    (DOWNLOADS[b.id] = DOWNLOADS[b.id] || {})[kind] = { key: x.url.replace(/^\//, ''), name: dlName(b, e, kind) };
    f.push({ k, name, ext: false, url: `/download/${b.id}/${kind}` });
  };
  add('pdf', 'PDF', both ? 'PDF (화면용)' : 'PDF');
  add('pdf_print', 'PDF', ok(e.pdf_cover) ? 'PDF (인쇄용 본문)' : 'PDF (인쇄용)');
  add('pdf_cover', 'PDF', 'PDF (인쇄용 표지)');
  add('epub', 'EPUB', 'EPUB');
  if (e.reader) f.push({ k: '온라인 읽기', name: '온라인 읽기' });
  return f;
}
// 판 표시: '개정판 발행 2024년 7월 20일' (발행일 글에 판 이름이 이미 있으면 그대로)
const edText = e => { const l = (e.label || '').trim(), p = (e.published || '').trim(); if (!p) return l; if (!l || p.includes(l)) return p; return `${l} 발행 ${p}`; };
// 목차: 한 줄에 하나. 앞에 공백 2칸 또는 '-' 를 붙이면 아랫단계. 줄 끝 '... 15' 같은 쪽수는 오른쪽에
function contentsHtml(t) {
  const rows = t.split('\n').map(l => l.replace(/\s+$/, '')).filter(l => l.trim()).map(l => {
    const sub = /^(\s{2,}|\t|-\s)/.test(l); let x = l.replace(/^[\s\-]+/, '');
    const m = x.match(/^(.*?)(?:\s*[.·…]{2,}\s*|\s{2,})(\d+)$/); let pg = '';
    if (m) { x = m[1]; pg = m[2]; }
    return `<li class="${sub ? 'sub' : ''}"><span>${esc(x)}</span>${pg ? `<span>${esc(pg)}</span>` : ''}</li>`;
  });
  return `<ol class="toc static">${rows.join('')}</ol>`;
}

// 책 페이지 아래쪽: 책 소개 · 저자 소개 · 옮긴이 소개 · 목차
function bookSections(b, e, t) {
  const has = x => x && String(x).trim();
  const secs = [];
  if (has(b.description)) secs.push({ id: 'intro', name: '책 소개', html: `<div class="desc lead-first">${marked.parse(b.description)}</div>` });
  const person = text => `<div class="person-card"><div class="desc">${marked.parse(text)}</div></div>`;
  if (has(b.author_intro)) secs.push({ id: 'author', name: '저자 소개', html: person(b.author_intro) });
  if (has(b.translator_intro)) secs.push({ id: 'translator', name: '옮긴이 소개', html: person(b.translator_intro) });
  if (e.reader) secs.push({ id: 'toc', name: '목차', html: `<div id="tocMount" data-manifest="${esc(readerManifest(b))}" data-book="${b.id}"></div>` });
  else if (has(b.contents)) secs.push({ id: 'toc', name: '목차', html: contentsHtml(b.contents) });
  if (!secs.length) return '';
  return `${secs.length > 1 ? `<nav class="sec-nav" aria-label="책 정보 바로 가기">${secs.map(x => `<a href="#sec-${x.id}">${x.name}</a>`).join('')}</nav>` : ''}${secs.map(x => `<section class="bsec" id="sec-${x.id}"><h2 class="bsec-h">${wheel('bsec-w')}<span>${x.name}</span></h2>${x.html}</section>`).join('')}`;
}
// 발행일 칸: 앞의 '초판 발행' 같은 판 이름은 빼고 날짜만
const pubDate = x => { let p = (x.published || '').trim(); const l = (x.label || '').trim(); if (l && p.startsWith(l)) p = p.slice(l.length).trim(); return p.replace(/^발행\s*/, '').trim(); };
const edHasFile = x => ['pdf', 'pdf_print', 'pdf_cover', 'epub'].some(k => x[k] && x[k].mode && x[k].mode !== 'none' && x[k].url) || !!x.reader;
const uniqK = f => [...new Map(f.map(x => [x.k, x])).values()];
// 내려받을 때 파일 이름: 책제목_날짜.pdf (날짜 = 파일 만든 날, 없으면 출간일)
function ymd(t) {
  const m = String(t || '').match(/(\d{4})\s*[.\-/년]\s*(\d{1,2})(?:\s*[.\-/월]\s*(\d{1,2}))?/);
  if (!m) { const y = String(t || '').match(/(\d{4})/); return y ? y[1] : ''; }
  return m[1] + '-' + m[2].padStart(2, '0') + (m[3] ? '-' + m[3].padStart(2, '0') : '');
}
const safeName = s => String(s).replace(/[\\/:*?"<>|\u0000-\u001f]+/g, ' ').replace(/\s+/g, ' ').trim();
const DOWNLOADS = {};
function dlName(b, e, kind) {
  const d = ymd(e.file_created) || ymd(e.published);
  const ext = kind === 'epub' ? 'epub' : 'pdf';
  const tag = { pdf_print: e.pdf_cover && e.pdf_cover.url ? '_인쇄용_본문' : '_인쇄용', pdf_cover: '_인쇄용_표지' }[kind] || '';
  return safeName(`${b.title}${tag}${d ? '_' + d : ''}`) + '.' + ext;
}
const hasText = b => { const e = curEd(b), t = TEXTS[b.id]; return !!(t && (!t.edition || t.edition === e.label)); };
const readerManifest = b => { const e = curEd(b); if (hasText(b)) return `/texts/${b.id}.json`; return e.reader ? fileUrl(`reader/${b.id}/${encodeURIComponent(e.label || 'ed')}/manifest.json`) : ''; };

// 창고(R2)에서 지워진 파일은 단추를 숨김: 사이트를 만들 때 파일이 실제로 있는지 확인
// (인터넷이 안 되는 곳에서 만들 때는 확인을 건너뛰고 그대로 둠)
async function exists(url) {
  try {
    const ac = new AbortController(); const to = setTimeout(() => ac.abort(), 10000);
    const r = await fetch(url, { method: 'HEAD', signal: ac.signal }); clearTimeout(to);
    return r.status === 404 ? false : true;
  } catch (e) { return true; }
}
{
  const jobs = [];
  for (const b of BOOKS) for (const e of (b.editions || [])) {
    if (!e.current) continue;
    for (const k of ['pdf', 'pdf_print', 'pdf_cover', 'epub']) {
      const x = e[k];
      if (x && x.mode === 'file' && x.url && !/^https?:/.test(x.url)) jobs.push(exists(fileUrl(x.url)).then(ok => { if (!ok) { console.warn(`[파일 없음] ${b.id} ${k}: ${x.url} → 단추 숨김`); x.mode = 'none'; } }));
    }
    if (TEXTS[b.id] && (!TEXTS[b.id].edition || TEXTS[b.id].edition === e.label)) { e.reader = true; continue; }
    if (e.reader) jobs.push(exists(fileUrl(`reader/${b.id}/${encodeURIComponent(e.label || 'ed')}/manifest.json`)).then(ok => { if (!ok) { console.warn(`[파일 없음] ${b.id} 온라인 읽기 → 숨김`); e.reader = false; } }));
  }
  await Promise.all(jobs);
}

/* ---------- 도구 ---------- */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const slugT = s => encodeURIComponent(s);
const NAV = [['/about/', '소개', 'about'], ['/press/', '我無말들 출판사', 'press'], ['/library/', '법보시 도서관', 'library'], ['/dhammatalk/', '법문 바로 듣기', 'dhammatalk'], ['/links/', '추천·협력 사이트', 'links'], ['/news/', '소식', 'news']];
const wheel = cls => `<svg class="${cls}" viewBox="0 0 40 40" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="20" cy="20" r="15"/><circle cx="20" cy="20" r="3.2"/><path d="M20 5v30M5 20h30M9.4 9.4l21.2 21.2M30.6 9.4L9.4 30.6"/></g></svg>`;

function layout({ title, nav = '', page = '', body, desc = '', image = '' }) {
  const t = title ? `${title} · ${S.site_name}` : S.site_name;
  const P = S.publisher;
  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(t)}</title>
<meta name="description" content="${esc(desc || '부처님과 테라와다 스승들의 가르침을 우리말로 옮긴 법보시 서적을 무료로 찾고, 내려받고, 읽는 곳')}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(S.site_name)}">
<meta property="og:title" content="${esc(t)}">
<meta property="og:description" content="${esc(desc || '부처님과 테라와다 스승들의 가르침을 우리말로 옮긴 법보시 서적을 무료로 찾고, 내려받고, 읽는 곳')}">
<meta property="og:image" content="${esc(S.site_url.replace(/\/$/, '') + (image || '/images/og.jpg'))}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/images/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif:ital,wght@0,400;0,600;1,400&family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans:wght@400;500&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css?v=${V.css}">
<script>try{var m=localStorage.getItem('dd-mode');m=m?JSON.parse(m):'auto';if(m!=='auto')document.documentElement.classList.add('mode-'+m);var f=JSON.parse(localStorage.getItem('dd-sitefs')||'0');if(f>0)document.documentElement.classList.add('sfs-'+f)}catch(e){}</script>
</head>
<body data-page="${page}">
<a class="skip" href="#app">본문으로 건너뛰기</a>
<header class="site"><div class="wrap">
  <div class="head-row">
    <a class="brand" href="/" aria-label="${esc(S.site_name)} 첫 화면">${wheel('brand-mark')}<span><span class="brand-name">${esc(S.site_name)}</span><span class="brand-sub">${esc(S.site_sub)}</span></span></a>
    <div class="head-tools">
      <a class="icon-btn" href="/mynotes/">내 서재</a>
      <a class="icon-btn" href="/search/"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>검색</a>
      <div class="mode-menu"><button class="icon-btn" id="modeBtn" aria-haspopup="true" aria-expanded="false">화면 모드</button>
        <div class="mode-pop" id="modePop" role="menu"><button data-mode="auto">기기 설정 따르기</button><button data-mode="day">기본 (상아빛)</button><button data-mode="mono">흑백</button><button data-mode="night">밤 모드</button><button data-mode="contrast">고대비 (검정 바탕·노란 글씨)</button></div></div>
      <div class="mode-menu"><button class="icon-btn" id="fsBtn" aria-haspopup="true" aria-expanded="false" aria-label="글자 크기">가<span style="font-size:1.25em">가</span></button>
        <div class="mode-pop" id="fsPop" role="menu"><button data-sfs="0">글자 보통</button><button data-sfs="1" style="font-size:16px">글자 크게</button><button data-sfs="2" style="font-size:18px">글자 아주 크게</button></div></div>
    </div>
  </div>
  <nav class="main" aria-label="주 메뉴">${NAV.map(([h, l, k]) => `<a href="${h}" data-nav="${k}"${k === nav ? ' class="on" aria-current="page"' : ''}>${l}</a>`).join('')}</nav>
</div></header>
<main id="app" data-page="${page}" data-nav="${nav}" data-title="${esc(t)}">
${body}
</main>
<footer class="site"><div class="wrap foot">
  <img class="logo-img" src="/images/logo.png" alt="我無말들" width="218" height="84">
  <div>
    <p>${esc(P.name)} · 발행인 ${esc(P.publisher_person)} · 전화 ${esc(P.phone)} · 출판등록 ${esc(P.registration)} · 이메일 ${esc(P.email)}</p>
    <p>${esc(S.footer_license)}</p>
    <p class="sadhu">${esc(S.footer_sadhu)}</p>
  </div>
</div></footer>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<div class="player" id="player" role="region" aria-label="법문 재생기"><div class="in">
  <div class="ctr"><button id="pPrev" aria-label="이전 법문">⏮</button><button class="main" id="pPlay" aria-label="재생">▶</button><button id="pNext" aria-label="다음 법문">⏭</button></div>
  <div class="mid"><div class="pt" id="pTitle">—</div><div class="bar"><span id="pCur">0:00</span><label for="pSeek" class="sr">재생 위치</label><input type="range" id="pSeek" min="0" max="100" value="0" step="0.1"><span id="pDur">0:00</span></div></div>
  <div class="opt"><label for="pRate">빠르기</label><select id="pRate"><option value="0.8">0.8배</option><option value="1" selected>1배</option><option value="1.25">1.25배</option><option value="1.5">1.5배</option></select>
    <label class="inline"><input type="checkbox" id="pAuto" checked>연속 재생</label><button class="tbtn" id="pLock" aria-pressed="false" title="잠그면 실수로 멈추지 않습니다">🔓 잠금</button><button class="tbtn" id="pHide" aria-label="재생기 닫기">✕</button></div>
</div><audio id="pAudio" preload="metadata"></audio></div>
<script src="/assets/app.js?v=${V.js}" defer></script>
</body>
</html>
`;
}

/* ---------- 조각 ---------- */
function coverCard(b) {
  const f = formats(b);
  const tr = b.teacher ? tradOfTeacher(b.teacher) : null;
  return `<a class="book" href="/book/${b.id}/" data-book="${b.id}" data-trad="${tr ? tr.id : ''}" data-teacher="${b.teacher || ''}" data-topics="${esc((b.topics || []).join('|'))}" data-main="${esc((b.main || []).join('|'))}" data-fmts="${esc(uniqK(f).map(x => x.k).join('|'))}" data-lang="${esc(b.original_language || '')}" data-title="${esc(b.title)}" data-added="${esc(b.added || '')}">
  <div class="cover">${!f.length ? '<span class="soon">준비 중</span>' : ''}${b.cover ? `<img class="cover-img" src="${esc(b.cover)}" alt="${esc(b.title)} 표지" loading="lazy">` : `<div class="cover-ph">${esc(b.title)}</div>`}</div>
  <div class="t">${esc(b.title)}</div><div class="a">${esc(b.byline)}${b.translator ? ' | ' + esc(b.translator) : ''}</div>
  ${f.length ? `<div class="fmt">${uniqK(f).map(x => `<span>${x.k}${x.ext ? ' ↗' : ''}</span>`).join('')}</div>` : ''}</a>`;
}
const countTopic = t => BOOKS.filter(b => (b.topics || []).includes(t)).length;
const countMain = t => BOOKS.filter(b => (b.main || []).includes(t)).length;
const countTeacher = id => BOOKS.filter(b => b.teacher === id).length;
const countTrad = id => BOOKS.filter(b => b.teacher && tradOfTeacher(b.teacher)?.id === id).length;

/* ---------- 페이지 ---------- */
const pages = {};
const put = (p, html) => { pages[p] = html; };

// 첫 화면
function updatesList() {
  const rows = [];
  for (const b of BOOKS) for (const e of b.editions || []) {
    if (e.changes && (e.file_created || e.published)) rows.push({ d: e.file_created || e.published, b, c: `${e.label} · ${e.changes}` });
  }
  for (const b of BOOKS) rows.push({ d: b.added || '', b, c: '등록' });
  return rows.sort((a, b) => b.d.localeCompare(a.d)).slice(0, 8);
}
put('index.html', layout({
  page: 'home', body: `<section class="verse wrap">${wheel('wheel')}
  <div class="pali-line">${esc(S.verse_pali)}</div><div class="ko-line">${esc(S.verse_ko)}</div><div class="cite">${esc(S.verse_cite)}</div>
  <form class="hero-search" action="/search/" role="search"><label for="hq" class="sr">자료 검색</label>
    <input id="hq" name="q" placeholder="제목, 스승, 옮긴이, 주제어, 본문으로 찾기" autocomplete="off"><button class="btn" type="submit">찾기</button></form>
  <div class="hint">예: <a href="/search/?q=위빳사나">위빳사나</a> · <a href="/search/?q=난다말라비왐사">난다말라비왐사</a> · <a href="/search/?q=metta">metta</a> · <a href="/search/?q=업과 윤회">업과 윤회</a></div>
</section>
<section class="section wrap two">
  <div><div class="section-head"><h2>최근 업데이트</h2><a class="more" href="/library/">도서관 →</a></div>
    <div class="upd">${updatesList().slice(0, 6).map(u => `<a class="upd-item" href="/book/${u.b.id}/"><span class="upd-cover">${u.b.cover ? `<img src="${esc(u.b.cover)}" alt="" loading="lazy">` : ''}</span><span class="upd-t">${esc(u.b.title)}</span><span class="upd-m">${esc(u.d)} · ${esc(u.c)}</span></a>`).join('')}</div></div>
  <div><div class="section-head"><h2>주제로 둘러보기</h2><a class="more" href="/library/">모든 주제 →</a></div>
    <div class="chips">${TOPICS.groups.flatMap(g => g.labels).filter(t => countTopic(t) > 0).sort((a, b) => countTopic(b) - countTopic(a)).slice(0, 14).map(t => `<a class="chip" href="/library/?topic=${slugT(t)}">${esc(t)}<span class="n">${countTopic(t)}</span></a>`).join('')}</div></div>
</section>
<section class="section wrap"><div class="section-head"><h2>수행전통으로 둘러보기</h2><a class="more" href="/library/">도서관에서 찾아보기 →</a></div>
  <div class="trad-grid">${TRADS.filter(t => t.representatives?.length).sort((a, b) => countTrad(b.id) - countTrad(a.id)).map(t => `<a class="trad${countTrad(t.id) ? '' : ' empty'}" href="/library/?trad=${t.id}"><div class="k">${esc(t.region)}</div><div class="nm">${esc(t.name)}</div><div class="ts">${t.representatives.map(id => esc(teacherById(id)?.name || '')).join(' · ')}</div><div class="ts" style="margin-top:6px">${countTrad(t.id) ? `자료 ${countTrad(t.id)}권` : '준비 중'}</div></a>`).join('')}</div></section>
<section class="section wrap two">
  <div><div class="section-head"><h2>我無말들 출판사</h2><a class="more" href="/press/">출판사 코너 →</a></div>
    <div class="grid three">${BOOKS.filter(b => b.press).slice(0, 3).map(coverCard).join('')}</div></div>
  <div><div class="section-head"><h2>소식</h2><a class="more" href="/news/">전체 소식 →</a></div>
    <ul class="news-list">${NEWS.slice(0, 5).map(n => `<li><div class="dd"><span class="pill ${n.category === 'press' ? 'robe' : ''}">${n.category === 'press' ? '我無말들' : '도서관'}</span> ${esc(n.date || '')}</div><a class="tt" href="/news/${n.slug}/">${esc(n.title)}</a></li>`).join('') || '<li class="muted">아직 소식이 없습니다.</li>'}</ul></div>
</section>`
}));

// 소개
const about = PAGES.about;
put('about/index.html', layout({ title: '소개', nav: 'about', page: 'about', body: `<div class="wrap"><article class="prose"><h1>${esc(about.meta.title)}</h1>${about.meta.homage ? `<p class="homage">${esc(about.meta.homage)}</p>` : ''}${about.html}</article></div>` }));

// 출판사
function pressShell(tab, inner) {
  return `<div class="wrap press"><aside>
  <nav class="press-nav" aria-label="我無말들 출판사 메뉴"><div class="pn-title">我無말들 출판사</div>${[['/press/', '출판도서', 'all'], ['/press/about/', '출판사 소개', 'about'], ['/press/notice/', '공지사항', 'notice'], ['/press/support/', '후원계좌', 'support']].map(([h, l, k]) => `<a href="${h}"${tab === k ? ' class="on" aria-current="page"' : ''}>${l}</a>`).join('')}</nav>
  </aside><section>${inner}</section></div>`;
}
const P = S.publisher;
put('press/index.html', layout({ title: '我無말들 출판사', nav: 'press', page: 'press', body: pressShell('all', `<div class="grid press-grid">${BOOKS.filter(b => b.press).map(coverCard).join('')}</div>`) }));
put('press/about/index.html', layout({ title: '출판사 소개', nav: 'press', page: 'press', body: pressShell('about', `<div class="prose" style="padding-top:0"><h1 class="h-page">${esc(PAGES['press-about'].meta.title)}</h1>${PAGES['press-about'].html}
  <table class="info-tbl"><tr><td>출판사</td><td>${esc(P.name)}</td></tr><tr><td>발행인</td><td>${esc(P.publisher_person)}</td></tr><tr><td>전화</td><td>${esc(P.phone)}</td></tr><tr><td>이메일</td><td>${esc(P.email)}</td></tr><tr><td>출판등록</td><td>${esc(P.registration)}</td></tr>
  <tr><td>라이선스</td><td>CC BY-NC-ND (저작자표시-비영리-변경금지)<br><span class="small muted">출처를 밝히면 누구나 자유롭게 복사하고 나눌 수 있습니다. 다만 판매 등 영리 목적으로 쓰거나 내용을 고쳐 배포할 수는 없습니다.</span> <a class="small" href="https://creativecommons.org/licenses/by-nc-nd/4.0/deed.ko" target="_blank" rel="noopener">자세히 ↗</a></td></tr></table></div>`) }));
const pn = NEWS.filter(n => n.category === 'press');
put('press/notice/index.html', layout({ title: '공지사항', nav: 'press', page: 'press', body: pressShell('notice', `<h1 class="h-page">공지사항</h1><ul class="news-list">${pn.map(n => `<li><div class="dd">${esc(n.date || '')}</div><a class="tt" href="/news/${n.slug}/">${esc(n.title)}</a></li>`).join('') || '<li class="muted">아직 공지가 없습니다.</li>'}</ul>`) }));
const sp = PAGES['press-support'];
put('press/support/index.html', layout({ title: '후원계좌', nav: 'press', page: 'press', body: pressShell('support', `<div class="prose" style="padding-top:0"><h1 class="h-page">${esc(sp.meta.title)}</h1>
  ${sp.body.trim().split('\n').filter(Boolean).map((l, i) => `<p style="margin:${i === 0 ? '0 0 .2em' : '0 0 1em'}">${esc(l)}</p>`).join('')}
  <table class="info-tbl"><tr><td>은행</td><td>${esc(sp.meta.bank)}</td></tr><tr><td>계좌번호</td><td>${esc(sp.meta.account)}</td></tr><tr><td>예금주</td><td>${esc(sp.meta.holder)}</td></tr></table>
  <ul style="list-style:disc;padding-left:1.2em;margin:1.8em 0 0"><li>법보시 출판 전용 계좌입니다.</li><li>개인 계좌이기 때문에 기부금영수증 발행은 어렵습니다.</li></ul></div>`) }));

// 도서관
const LANGS = ['빠알리어', '영어', '미얀마어', '태국어', '싱할라어', '한국어', '기타'].filter(l => BOOKS.some(b => b.original_language === l));
function libraryBody() {
  const chk = (set, val, label, n, extra = '') => `<label class="${n === 0 ? 'zero' : ''}"><input type="checkbox" data-f="${set}" value="${esc(val)}">${label}${extra}<span class="n">${n}</span></label>`;
  let g = '', trad = '';
  for (const t of TRADS) {
    const n = countTrad(t.id);
    if (t.region !== g) { g = t.region; trad += `<div class="group-name trad-region" data-region="${esc(g)}">${esc(g)}</div>`; }
    const ts = [...(t.representatives || []), ...TEACHERS.filter(x => x.tradition === t.id && !(t.representatives || []).includes(x.id)).map(x => x.id)];
    trad += `<div class="trad-block${n === 0 ? ' empty' : ''}" data-trad-block="${t.id}">${chk('trad', t.id, esc(t.name), n)}
      <div class="sub" hidden>${ts.map(id => chk('teacher', id, esc(teacherById(id).name), countTeacher(id), (t.representatives || []).includes(id) ? '<span class="rep">대표</span>' : '')).join('')}</div></div>`;
  }
  const topics = TOPICS.groups.map((gr, i) => `<details class="fgroup"${gr.labels.some(l => countTopic(l)) ? ' open' : ''}><summary class="group-name">${esc(gr.name)} <span class="n">${gr.labels.reduce((a, l) => a + countTopic(l), 0)}</span></summary>` + gr.labels.map(l => chk('topic', l, esc(l), countTopic(l))).join('') + '</details>').join('');
  return `<div class="wrap lib"><details class="filter-toggle" open><summary>찾아보기</summary><div class="filters">
    <h3>주요 자료</h3>${TOPICS.main.map(m => chk('main', m, esc(m), countMain(m))).join('')}
    <h3>수행전통 · 스승</h3>${trad}
    <label class="small muted" style="margin-top:6px"><input type="checkbox" id="showEmpty">준비 중인 전통도 보기</label>
    <h3>주제</h3>${topics}
    ${LANGS.length ? `<h3>원서의 언어</h3>${LANGS.map(l => chk('lang', l, esc(l), BOOKS.filter(b => b.original_language === l).length)).join('')}` : ''}
    <h3>형식</h3>${['PDF', 'EPUB', '온라인 읽기'].map(f => chk('fmt', f, f, BOOKS.filter(b => formats(b).some(x => x.k === f)).length)).join('')}
  </div></details>
  <section><div class="toolbar"><div><h1 class="h-page">법보시 도서관</h1><div class="muted small">자료 <span id="libCount">${BOOKS.length}</span>권</div></div>
    <label class="small">정렬 <select id="sort"><option value="new">최근 등록순</option><option value="title">제목 가나다순</option></select></label></div>
    <div class="active-filters" id="activeFilters"></div>
    <div class="grid" id="libGrid">${BOOKS.map(coverCard).join('')}</div>
    <p class="muted" id="libEmpty" hidden>조건에 맞는 자료가 아직 없습니다. 찾아보기를 줄여 보세요.</p>
  </section></div>`;
}
put('library/index.html', layout({ title: '법보시 도서관', nav: 'library', page: 'library', body: libraryBody() }));

// 책 상세
for (const b of BOOKS) {
  const e = curEd(b), f = formats(b), t = teacherById(b.teacher), tr = b.teacher ? tradOfTeacher(b.teacher) : null;
  const prov = providerById(b.provider);
  const same = BOOKS.filter(x => x !== b && b.teacher && x.teacher === b.teacher);
  const perms = (e.permissions || []).map(permById).filter(Boolean);
  const permLabel = e.permission_status === 'public' ? '공개 배포됨' : e.permission_status === 'confirmed' || perms.length ? '허락 확인됨' : '';
  const pubEds = (b.editions || []);
  const hasPrint = pubEds.some(x => x.isbn || x.publisher_print), hasEbook = pubEds.some(x => x.isbn_ebook || x.publisher_ebook || x.published_ebook);
  const statusCell = x => x.current ? '<span class="pill">최신판</span>' : !edHasFile(x) ? '—' : x.public ? '이전 판 공개' : '보관';
  const edTable = (title, rows, cols) => { const use = cols.filter(c => c.always || rows.some(c.get)); return `<h4 class="ed-h">${title}</h4><div class="tbl-wrap"><table class="tbl"><thead><tr>${use.map(c => `<th>${c.h}</th>`).join('')}</tr></thead><tbody>${rows.map(x => `<tr>${use.map(c => `<td>${c.html ? c.get(x) || '—' : esc(c.get(x) || '—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`; };
  const ebookEds = pubEds.filter(x => x.isbn_ebook || x.publisher_ebook || x.published_ebook);
  const edTables = (hasEbook ? edTable('종이책', pubEds, [
      { h: '판', get: x => x.label, always: 1 }, { h: '발행일', get: x => pubDate(x), always: 1 }, { h: '쪽수', get: x => x.page_count ? x.page_count + '쪽' : '' , always: 1 },
      { h: '출판사', get: x => x.publisher_print }, { h: 'ISBN', get: x => x.isbn }])
    + edTable('전자책', ebookEds, [
      { h: '판', get: x => x.label, always: 1 }, { h: '발행일', get: x => x.published_ebook, always: 1 },
      { h: '출판사', get: x => x.publisher_ebook }, { h: 'ISBN', get: x => x.isbn_ebook }])
    + edTable('이 사이트의 파일', pubEds, [{ h: '판', get: x => x.label, always: 1 }, { h: '공개', get: statusCell, always: 1, html: 1 }])
    : edTable('판', pubEds, [
      { h: '판', get: x => x.label, always: 1 }, { h: '발행일', get: x => pubDate(x), always: 1 }, { h: '쪽수', get: x => x.page_count ? x.page_count + '쪽' : '', always: 1 },
      { h: '출판사', get: x => x.publisher_print }, { h: 'ISBN', get: x => x.isbn }, { h: '공개', get: statusCell, always: 1, html: 1 }]).replace('<h4 class="ed-h">판</h4>', ''));
  const pl = PLAYLISTS.find(p => p.teacher && p.teacher === b.teacher);
  const extF = f.filter(x => x.ext);
  put(`book/${b.id}/index.html`, layout({
    title: b.title, nav: 'library', page: 'book', image: b.cover || '', desc: `${b.title} — ${b.byline}${b.translator ? ', ' + b.translator : ''}`, body: `<div class="wrap detail">
  <div><div class="cover-box">${b.cover ? `<img class="cover-img" src="${esc(b.cover)}" alt="${esc(b.title)} 표지">` : `<div class="cover-ph big">${esc(b.title)}</div>`}</div></div>
  <div class="d-body"><div class="d-head"><div class="crumb"><a href="/library/">법보시 도서관</a>${tr ? ` › <a href="/library/?trad=${tr.id}">${esc(tr.name)}</a> › <a href="/teacher/${t.id}/">${esc(t.name)}</a>` : ''}</div>
    ${b.series ? `<div class="small muted">${esc(b.series)}</div>` : ''}
    <h1>${esc(b.title)}</h1>${b.subtitle ? `<div class="orig" style="font-style:normal">${esc(b.subtitle)}</div>` : ''}${b.original_title || b.original_language ? `<div class="orig">${esc(b.original_title || '')}${b.original_language ? `<span class="lang-tag">${esc(b.original_language)} 원서</span>` : ''}</div>` : ''}
    <div class="people">${esc(b.byline)}${b.translator ? ' | ' + esc(b.translator) : ''}</div>
    ${pl ? `<div style="margin:2px 0 8px"><a class="small" href="/dhammatalk/?pl=${pl.id}">▶ ${esc(t.name)}의 법문 바로 듣기</a></div>` : ''}
    </div><aside class="d-side"><div class="get-box"><div class="gb-title">이 책 읽어보기</div><div class="actions">${e.reader ? `<a class="btn" href="/read/${b.id}/">온라인으로 읽기</a>` : ''}
      ${f.filter(x => x.k !== '온라인 읽기').map(x => x.ext ? `<a class="btn ghost" href="${esc(x.url)}" target="_blank" rel="noopener">${x.name} 내려받기 ↗</a>` : `<a class="btn ghost" href="${esc(x.url)}" download>${x.name} 내려받기</a>`).join('')}
      ${!f.length ? `<div class="soon-box">파일을 준비하고 있습니다.<br><span class="small">소식에서 올라오는 대로 알려 드립니다.</span></div>` : ''}</div>
    ${extF.length ? `<div class="small muted" style="margin-bottom:4px">↗ 표시된 파일은 ${esc(extF[0].site)}로 넘어가서 내려받습니다.</div>` : ''}
    <dl class="gb-kv"><dt>판</dt><dd>${esc(edText(e) || '—')}</dd>${e.page_count ? `<dt>쪽수</dt><dd>${esc(e.page_count)}쪽</dd>` : ''}${e.isbn ? `<dt>ISBN${e.isbn_ebook ? ' (종이책)' : ''}</dt><dd>${esc(e.isbn)}</dd>` : ''}${e.published_ebook ? `<dt>전자책 발행</dt><dd>${esc(e.published_ebook)}</dd>` : ''}${e.isbn_ebook ? `<dt>ISBN (전자책)</dt><dd>${esc(e.isbn_ebook)}</dd>` : ''}${(b.editions || []).filter(x => x !== e && (x.published || x.label)).length ? `<dt>펴낸 이력</dt><dd>${(b.editions || []).map(x => esc(edText(x))).filter(Boolean).join('<br>')}</dd>` : ''}<dt>라이선스</dt><dd>${esc(b.license)}</dd><dt>자료번호</dt><dd>${b.id}</dd></dl></div></aside><div class="d-rest">
    <div class="labels">${(b.main || []).map(m => `<a class="t" href="/library/?main=${slugT(m)}">${esc(m)}</a>`).join('')}${(b.topics || []).map(x => `<a class="t" href="/library/?topic=${slugT(x)}">${esc(x)}</a>`).join('')}${tr ? `<a href="/library/?trad=${tr.id}">${esc(tr.name)}</a>` : ''}${b.press ? `<a href="/press/">我無말들 출간</a>` : ''}</div>
    ${bookSections(b, e, t)}
    <details class="record"><summary>자료 기록 (출처 · 판 · 라이선스)</summary><div class="record-body">
      <dl class="kv"><dt>자료번호</dt><dd>${b.id}</dd>
      <dt>저자·스승</dt><dd>${t ? `<a href="/teacher/${t.id}/">${esc(t.name)}</a>${t.roman ? ` <span class="muted small">(${esc(t.roman)})</span>` : ''}` : esc(b.byline)}</dd>
      <dt>번역·편자</dt><dd>${esc(b.translator || b.byline)}</dd>
      ${b.original_language ? `<dt>원서의 언어</dt><dd>${esc(b.original_language)}</dd>` : ''}
      ${b.original_source ? `<dt>원서 정보</dt><dd>${esc(b.original_source)}</dd>` : ''}
      <dt>자료 제공</dt><dd>${prov ? esc(prov.name) + (prov.urls || []).map(u => ` <a href="${esc(u)}" target="_blank" rel="noopener">↗</a>`).join('') : '—'}</dd>
      <dt>원본 출처</dt><dd>${(e.sources || []).length ? e.sources.map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener">원본 출처 ↗</a>${s.checked ? ` <span class="muted small">(${esc(s.checked)} 확인)</span>` : ''}${s.archive ? ` · <a href="${esc(s.archive)}" target="_blank" rel="noopener">보관본</a>` : ''}`).join('<br>') : '—'}</dd>
      <dt>수집 경로</dt><dd>${esc(e.collection || '—')}${e.collected ? ` <span class="muted small">(${esc(e.collected)})</span>` : ''}</dd>
      <dt>게시 허락</dt><dd>${permLabel || e.permission_note || e.permission_image ? `${permLabel}${perms.filter(p => p.image && p.image_public).map(p => ` · <button class="link-btn" data-permit="${esc(p.image)}" data-title="${esc(b.title)}">허락서 보기</button>`).join('')}${e.permission_image ? `${permLabel ? ' · ' : ''}<button class="link-btn" data-permit="${esc(e.permission_image)}" data-title="${esc(b.title)}">허락서 보기</button>` : ''}${e.permission_note ? `<blockquote class="perm-note">${esc(e.permission_note).replace(/\n/g, '<br>')}</blockquote>` : ''}` : '—'}</dd>
      <dt>라이선스</dt><dd>${esc(b.license)}</dd></dl>
      ${edTables}
      <p class="small muted" style="margin-top:10px">새 판이 올라오면 이전 판은 보관되고, 최신판만 내려받기와 온라인 읽기에 나옵니다.</p>
    </div></details>
    ${same.length ? `<h2 class="h-sub">${esc(t.name)}의 다른 책</h2><div class="grid">${same.map(coverCard).join('')}</div>` : ''}
  </div></div></div>`
  }));
  if (e.reader) put(`read/${b.id}/index.html`, layout({
    title: `${b.title} 읽기`, nav: 'library', page: 'reader', body: `<div id="readerRoot" data-manifest="${esc(readerManifest(b))}" data-book="${b.id}" data-title="${esc(b.title)}" data-byline="${esc(b.byline)}" data-teacher="${esc(t?.name || '')}">
    <div class="wrap prose"><p class="muted">읽기 화면을 불러오는 중입니다…</p><p><a href="/book/${b.id}/">← 책 정보로 돌아가기</a></p></div></div>`
  }));
}

// 스승
for (const t of TEACHERS) {
  const tr = tradById(t.tradition), list = BOOKS.filter(b => b.teacher === t.id), trans = BOOKS.filter(b => b.translator && b.translator.includes(t.name.replace(/ (스님|사야도)$/, '')) && b.teacher !== t.id);
  const pl = PLAYLISTS.find(p => p.teacher === t.id);
  put(`teacher/${t.id}/index.html`, layout({
    title: t.name, nav: 'library', page: 'teacher', body: `<div class="wrap"><div class="teacher-head"><div class="portrait" aria-hidden="true">${t.photo ? `<img src="${esc(t.photo)}" alt="">` : esc(t.name[0])}</div>
    <div><div class="small muted"><a href="/library/?trad=${tr.id}">${esc(tr.region)} · ${esc(tr.name)}</a>${(tr.representatives || []).includes(t.id) ? ' · 대표 스승' : ''}</div>
    <h1 class="h-page">${esc(t.name)}</h1>${t.roman ? `<div class="pali muted">${esc(t.roman)}</div>` : ''}
    ${t.bio ? `<div class="desc small">${marked.parse(t.bio)}</div>` : ''}
    ${pl ? `<p style="margin:8px 0 0"><a class="btn sm ghost" href="/dhammatalk/?pl=${pl.id}">▶ ${esc(t.name)}의 법문 듣기</a></p>` : ''}</div></div>
    <div class="section-head" style="margin-top:20px"><h2>${esc(t.name)}의 가르침을 옮긴 책 ${list.length}권</h2></div>
    ${list.length ? `<div class="grid">${list.map(coverCard).join('')}</div>` : '<p class="muted">아직 등록된 책이 없습니다.</p>'}
    ${trans.length ? `<div class="section-head" style="margin-top:30px"><h2>옮긴 책</h2></div><div class="grid">${trans.map(coverCard).join('')}</div>` : ''}
    <div class="section-head" style="margin-top:36px"><h2>같은 전통의 스승</h2></div>
    <div class="chips">${TEACHERS.filter(x => x.tradition === t.tradition && x.id !== t.id).map(x => `<a class="chip" href="/teacher/${x.id}/">${esc(x.name)}<span class="n">${countTeacher(x.id)}</span></a>`).join('')}</div></div>`
  }));
}

// 검색
put('search/index.html', layout({
  title: '검색', page: 'search', body: `<div class="wrap"><form class="search-top" id="sForm" role="search" action="/search/">
  <label for="sq" class="sr">검색어</label><input id="sq" name="q" placeholder="제목, 스승, 옮긴이, 주제어, 본문" autocomplete="off">
  <label for="scope" class="sr">검색 범위</label><select id="scope" name="scope"><option value="all">전체</option><option value="title">제목</option><option value="author">스승·저자</option><option value="tr">옮긴이·편자</option><option value="topic">주제어</option><option value="body">본문</option></select>
  <button class="btn" type="submit">찾기</button></form>
  <div id="sResult"><p class="muted">찾을 말을 넣어 보세요. 예: <a href="/search/?q=위빳사나">위빳사나</a>, <a href="/search/?q=마음챙김">마음챙김</a>, <a href="/search/?q=난다말라비왐사">난다말라비왐사</a>, <a href="/search/?q=쉐우민">쉐우민</a></p></div></div>`
}));

// 법문 바로 듣기 (팟캐스트 RSS는 빌드 때 가져옴)
async function fetchRss(url) {
  try {
    const ac = new AbortController(); const to = setTimeout(() => ac.abort(), 15000);
    const r = await fetch(url, { signal: ac.signal, headers: { 'user-agent': 'dhammadana-library-build' } }); clearTimeout(to);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const xml = await r.text();
    const un = s => (s || '').replace(/^<!\[CDATA\[|\]\]>$/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();
    const items = [...xml.matchAll(/<item[\s>][\s\S]*?<\/item>/g)].map(m => {
      const it = m[0]; const g = tag => un((it.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`)) || [])[1]);
      const enc = (it.match(/<enclosure[^>]*url="([^"]+)"/) || [])[1];
      return { title: g('title'), date: g('pubDate'), duration: g('itunes:duration'), audio: enc ? un(enc) : '' };
    }).filter(x => x.audio);
    return items;
  } catch (err) { console.warn('[RSS] 가져오기 실패:', url, err.message); return null; }
}
const fmtDate = d => { const t = Date.parse(d); return isNaN(t) ? '' : new Date(t).toISOString().slice(0, 10); };
// 팟빵 채널 번호로 가져오기 (팟빵 앱이 쓰는 공개 목록 주소. 팟빵이 바꾸면 고쳐야 함)
// 팟빵: 팟빵 앱이 쓰는 공개 목록 주소 (offset 은 '몇 번째 묶음'). 팟빵이 바꾸면 고쳐야 함
const PB = 'https://app-api6.podbbang.com';
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function getJSON(url, tries = 3) {
  for (let k = 1; ; k++) {
    const ac = new AbortController(); const to = setTimeout(() => ac.abort(), 20000);
    try {
      const r = await fetch(url, { signal: ac.signal, headers: { accept: 'application/json', 'user-agent': 'Mozilla/5.0 (dhammadana-library-build)' } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      await sleep(150); return await r.json();
    } catch (err) {
      console.warn(`[팟빵] ${k}번째 시도 실패: ${url.replace(PB, '')} — ${err.message}${err.cause ? ' / ' + (err.cause.code || err.cause.message) : ''}`);
      if (k >= tries) throw err; await sleep(1500 * k);
    } finally { clearTimeout(to); }
  }
}
const pbEp = e => ({ id: e.id, title: e.title, date: (e.publishedAt || '').slice(0, 10), t: e.publishedAt || '', duration: e.media?.durationText || '', audio: e.media?.url || '' });
async function pbAll(path) {
  const out = [];
  for (let page = 0, total = Infinity; out.length < total && page < 60; page++) {
    const j = await getJSON(`${PB}${path}${path.includes('?') ? '&' : '?'}offset=${page}&limit=50`);
    const d = j.data || []; if (j.summary?.totalCount != null) total = j.summary.totalCount;
    out.push(...d.map(pbEp)); if (!d.length) break;
  }
  return out.filter(x => x.audio);
}
async function fetchPodbbang(id) {
  try {
    const all = await pbAll(`/channels/${encodeURIComponent(id)}/episodes?sort=desc`);
    const subs = [{ id: 'all', name: '전체 법문', list: all }];
    try {
      const pls = (await getJSON(`${PB}/channels/${encodeURIComponent(id)}/playlists`)).data || [];
      for (const pl of pls) {
        try {
          const l = await pbAll(`/channels/${encodeURIComponent(id)}/playlists/${pl.id}/episodes`);
          l.sort((x, y) => x.t.localeCompare(y.t)); // 재생목록은 1강부터
          if (l.length) subs.push({ id: String(pl.id), name: pl.name, list: l });
        } catch (err) { console.warn('[팟빵] 재생목록 실패:', pl.name, err.message); }
      }
    } catch (err) { console.warn('[팟빵] 재생목록 목록 실패:', err.message); }
    return subs;
  } catch (err) { console.warn('[팟빵] 가져오기 실패:', id, err.message); return null; }
}
for (const p of PLAYLISTS) {
  let subs = null;
  if (p.podbbang) subs = await fetchPodbbang(p.podbbang);
  else if (p.rss) { const l = await fetchRss(p.rss); if (l && l.length) subs = [{ id: 'all', name: '전체 법문', list: l.map(e => ({ ...e, date: fmtDate(e.date) || e.date })) }]; }
  p.fetched = !!(subs && subs[0].list.length);
  if (!p.fetched) subs = [{ id: 'all', name: '전체 법문', list: (p.episodes || []).map(e => ({ title: e.title, date: e.date || '', duration: e.duration || '', audio: e.audio })) }];
  p.subs = subs; p.list = subs[0].list;
}
function talksBody() {
  let g = '';
  const row = (p, s, e, i) => `<div class="ep" role="listitem" tabindex="0" data-ep="${i}" data-epl="${p.id}:${s.id}" data-audio="${esc(e.audio)}" data-title="${esc(e.title)}" data-plname="${esc(p.name + (s.id === 'all' ? '' : ' · ' + s.name))}"${i >= 50 ? ' hidden data-later' : ''}><span class="no">${i + 1}</span><span><span class="et">${esc(e.title)}</span><br><span class="em">${esc(e.date)}</span></span><span class="ed">${esc(e.duration)}</span></div>`;
  return `<div class="wrap"><div class="prose" style="padding-bottom:0"><h1>법문 바로 듣기</h1><p class="muted">재생목록에서 법문을 골라 바로 들을 수 있습니다. 다른 메뉴로 옮겨 가도 아래 재생기는 계속 재생됩니다.</p></div>
  <div class="talks"><nav class="pl-list" aria-label="법문 모음">${PLAYLISTS.map(x => (x.group !== g ? `<div class="pl-group">${esc(g = x.group)}</div>` : '') + `<button class="pl" data-pl="${x.id}" style="--pl-c:${['#9C5A2E', '#6B7F4E', '#4F6B8A', '#8A5A7A', '#A0812F', '#5E7F7A'][PLAYLISTS.indexOf(x) % 6]}"><span class="n">${esc(x.name)}</span><span class="s">${x.list.length}개${x.subs.length > 1 ? ` · 재생목록 ${x.subs.length - 1}개` : ''} · ${esc(x.source || '')}</span></button>`).join('')}</nav>
  <section>${PLAYLISTS.map(p => `<div class="pl-panel" data-panel="${p.id}" hidden>
    <div class="section-head"><h2>${esc(p.name)}</h2>${p.podbbang ? `<a class="btn sm ghost" href="https://www.podbbang.com/channels/${encodeURIComponent(p.podbbang)}" target="_blank" rel="noopener">팟빵 채널로 가기 ↗</a>` : p.link ? `<a class="btn sm ghost" href="${esc(p.link)}" target="_blank" rel="noopener">채널로 가기 ↗</a>` : ''}</div>
    ${p.teacher ? `<div class="small" style="margin-bottom:8px"><a href="/teacher/${p.teacher}/">${esc(teacherById(p.teacher)?.name || '')}의 책 보기 →</a></div>` : ''}
    ${!p.list.length ? `<p class="muted">법문 목록을 불러오지 못했습니다. 잠시 뒤 다시 확인해 주세요.</p>` : ''}
    ${p.subs.length > 1 ? `<div class="chips sub-chips" role="tablist" aria-label="재생목록">${p.subs.map(s => `<button class="chip" role="tab" data-sub="${p.id}:${s.id}">${esc(s.name)}<span class="n">${s.list.length}</span></button>`).join('')}</div>` : ''}
    ${p.subs.map(s => `<div class="sub-panel" data-subpanel="${p.id}:${s.id}" hidden>
      <div class="sub-head"><b>${esc(s.name)}</b> <span class="muted small">${s.list.length}개${s.id === 'all' ? ' · 최근 올린 순' : ' · 1강부터'}</span>${s.list.length ? ` <button class="btn sm" data-playall="${p.id}:${s.id}">▶ 처음부터 모두 듣기</button>` : ''}</div>
      <div role="list">${s.list.map((e, i) => row(p, s, e, i)).join('')}</div>
      ${s.list.length > 50 ? `<div class="more-wrap"><button class="btn sm ghost" data-more>더 보기</button></div>` : ''}
    </div>`).join('')}
  </div>`).join('')}</section></div></div>`;
}
put('dhammatalk/index.html', layout({ title: '법문 바로 듣기', nav: 'dhammatalk', page: 'talks', body: talksBody() }));

// 추천·협력
const partners = PROVIDERS.filter(p => p.partner);
const linkGroups = [{ name: '협력 단체', desc: '도서관과 함께 법보시 자료를 나누는 단체입니다.', items: partners.map(p => ({ name: p.name, url: (p.urls || [])[0] || '#', note: p.note || '' })) }, ...LINKS];
put('links/index.html', layout({
  title: '추천·협력 사이트', nav: 'links', page: 'links', body: `<div class="wrap"><div class="prose" style="padding-bottom:4px"><h1>추천·협력 사이트</h1><p class="muted">함께 법을 나누는 곳들을 종류별로 모았습니다.</p></div>
  ${linkGroups.filter(g => g.items.length).map(g => `<section style="margin-top:30px"><div class="section-head" style="margin-bottom:12px"><h2>${esc(g.name)}</h2><span class="small muted">${g.items.length}곳</span></div>
   <p class="small muted" style="margin:-4px 0 14px">${esc(g.desc || '')}</p>
   <div class="link-grid">${g.items.map(l => `<a class="link-card" href="${esc(l.url)}" target="_blank" rel="noopener"><img class="lc-ico" src="https://www.google.com/s2/favicons?sz=64&domain=${encodeURIComponent((l.url.match(/\/\/([^/]+)/) || [])[1] || '')}" alt="" width="28" height="28" loading="lazy" onerror="this.style.visibility='hidden'"><b class="lc-name">${esc(l.name)} ↗</b><span class="small muted">${esc(l.note || '')}</span></a>`).join('')}</div></section>`).join('')}</div>`
}));

// 소식
function newsList(cat) {
  const l = NEWS.filter(n => !cat || n.category === cat);
  return `<div class="wrap"><div class="prose" style="padding-bottom:0"><h1>소식</h1></div>
  <div class="tabs">${[['/news/', '전체', ''], ['/news/press/', '我無말들 소식', 'press'], ['/news/library/', '도서관 소식', 'library']].map(([h, lb, k]) => `<a href="${h}" class="${(cat || '') === k ? 'on' : ''}">${lb}</a>`).join('')}</div>
  <ul class="news-list" style="max-width:760px">${l.map(n => `<li><div class="dd"><span class="pill ${n.category === 'press' ? 'robe' : ''}">${n.category === 'press' ? '我無말들' : '도서관'}</span> ${esc(n.date || '')}</div><a class="tt" href="/news/${n.slug}/">${esc(n.title)}</a></li>`).join('') || '<li class="muted">아직 소식이 없습니다.</li>'}</ul>
  ${l.length < 6 ? `<div class="more-box"><div class="section-head"><h2>최근 올라온 책</h2><a class="more" href="/library/">도서관 →</a></div><div class="grid">${BOOKS.slice(0, 5).map(coverCard).join('')}</div></div>` : ''}</div>`;
}
put('news/index.html', layout({ title: '소식', nav: 'news', page: 'news', body: newsList('') }));
put('news/press/index.html', layout({ title: '我無말들 소식', nav: 'news', page: 'news', body: newsList('press') }));
put('news/library/index.html', layout({ title: '도서관 소식', nav: 'news', page: 'news', body: newsList('library') }));
for (const n of NEWS) {
  const b = n.book ? BOOKS.find(x => x.id === n.book) : null;
  put(`news/${n.slug}/index.html`, layout({
    title: n.title, nav: 'news', page: 'news', body: `<div class="wrap"><article class="prose"><div class="small muted"><a href="/news/">소식</a> · ${n.category === 'press' ? '我無말들' : '도서관'} · ${esc(n.date || '')}</div><h1>${esc(n.title)}</h1>${n.html}
    ${n.source ? `<p><a href="${esc(n.source)}" target="_blank" rel="noopener">원문 보기 ↗</a></p>` : ''}
    ${b ? `<div class="grid" style="max-width:220px;margin-top:20px">${coverCard(b)}</div>` : ''}</article></div>`
  }));
}

// 내 서재
put('mynotes/index.html', layout({ title: '내 서재', page: 'mynotes', body: `<div class="wrap"><div class="prose" style="padding-bottom:0"><h1>내 서재</h1><p class="muted">밑줄과 책갈피를 책별로 모아 봅니다. 회원가입 없이 이 기기의 브라우저에만 저장됩니다.</p></div><div id="notesRoot"></div></div>` }));

// 인터넷이 없을 때
// 회원 자료실: 빈 틀만 만들고, 내용(파일 목록)은 로그인한 뒤 /members/api/list 에서 받아 옵니다. 자료는 공개 저장소에 두지 않습니다.
put('members/index.html', layout({ title: '회원 자료실', page: 'members', body: `<div class="wrap"><div class="prose" style="padding-bottom:0"><h1>회원 자료실</h1><p class="muted">허락받은 분만 보는 곳입니다. 이 곳의 자료는 다른 분께 넘기지 말아 주세요.</p></div><div id="membersRoot"><p class="muted">불러오는 중…</p></div></div>` }));
put('offline.html', layout({ title: '인터넷 연결 없음', page: 'offline', body: `<div class="wrap prose"><h1>인터넷에 연결되어 있지 않습니다</h1><p>이 페이지는 아직 이 기기에 저장되지 않았습니다. 인터넷이 될 때 한 번 열어 둔 책과 페이지는 인터넷 없이도 읽을 수 있습니다.</p><p><a href="/mynotes/">내 서재에서 읽던 책 보기 →</a></p></div>` }));
// 404
put('404.html', layout({ title: '페이지를 찾을 수 없습니다', page: 'notfound', body: `<div class="wrap prose"><h1>페이지를 찾을 수 없습니다</h1><p>주소가 바뀌었거나 없는 페이지입니다. <a href="/library/">도서관</a>이나 <a href="/search/">검색</a>에서 찾아보세요.</p></div>` }));

/* ---------- 쓰기 ---------- */
fs.rmSync(OUT, { recursive: true, force: true });
fs.cpSync(path.join(ROOT, 'public'), OUT, { recursive: true });
for (const [p, html] of Object.entries(pages)) {
  const f = path.join(OUT, p); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, html);
}
// 검색·내 서재·읽기에 쓰는 자료
const site = {
  files_base: S.files_base,
  variants: VARIANTS,
  books: BOOKS.map(b => {
    const t = teacherById(b.teacher), tr = b.teacher ? tradOfTeacher(b.teacher) : null;
    return { id: b.id, title: b.title, subtitle: b.subtitle || '', orig: b.original_title || '', lang: b.original_language || '', cover: b.cover || '', byline: b.byline, tr: b.translator || '', teacher: t ? t.name : '', teacherRoman: t ? t.roman : '', teacherAliases: t ? t.aliases : [], tradition: tr ? tr.name : '', topics: b.topics || [], main: b.main || [], isbn: (b.editions || []).flatMap(x => [x.isbn, x.isbn_ebook]).filter(Boolean), manifest: readerManifest(b), desc: (b.description || '').slice(0, 300) };
  }),
  aliases: [...TEACHERS.map(t => [t.name, ...(t.aliases || []), t.roman].filter(Boolean)), ...TRADS.map(t => [t.name])]
};
fs.mkdirSync(path.join(OUT, 'data'), { recursive: true });
fs.writeFileSync(path.join(OUT, 'data/site.json'), JSON.stringify(site));
fs.writeFileSync(path.join(OUT, 'data/downloads.json'), JSON.stringify(DOWNLOADS));
fs.mkdirSync(path.join(OUT, 'texts'), { recursive: true });
for (const [id, t] of Object.entries(TEXTS)) fs.writeFileSync(path.join(OUT, 'texts', id + '.json'), JSON.stringify({ book: id, edition: t.edition, pages: t.pages, toc: t.toc }));
// 관리자 화면이 예전 설정(config.yml)을 기억하지 않도록 바뀔 때마다 주소 끝에 표시를 붙입니다.
{ const ai = path.join(OUT, 'admin', 'index.html'); if (fs.existsSync(ai)) fs.writeFileSync(ai, fs.readFileSync(ai, 'utf8').replace('/admin/config.yml"', `/admin/config.yml?v=${ver('admin/config.yml')}"`)); }
fs.writeFileSync(path.join(OUT, '_redirects'), `/read/:id/:page /read/:id/ 200\n`);
console.log(`[팟빵·RSS] ${PLAYLISTS.map(p => p.name + ' ' + p.list.length + '개, 재생목록 ' + (p.subs.length - 1) + '개').join(' / ')}`);
console.log(`만든 페이지 ${Object.keys(pages).length}개, 책 ${BOOKS.length}권, 법문 모음 ${PLAYLISTS.length}개`);
