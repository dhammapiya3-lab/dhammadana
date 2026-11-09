// 붓다담마 그림책 (storybooks.dhammadana.kr) — data/ 를 읽어 dist/ 를 만든다.
// 원작: Dharma Storybooks (dharma-storybooks.net, Bhante Ānandajoti, CC BY-SA 4.0)
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.dirname(new URL(import.meta.url).pathname);
const rd = f => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'));
const CAT = rd('catalog.json');      // 원 사이트 구조 (영어 원문)
const KO = rd('ko.json');            // 한국어 번역
const READY = rd('ready.json');      // 한글 그림이 준비된 이야기 { "책/이야기": 그림 수 }
const S = KO.site, U = KO.ui;
const BOTTOM = (KO.bottom?.books || []).filter(s => CAT.books[s]); // 불교와 직접 관련 없는 책 — 맨 아래 따로
const OUT = path.join(ROOT, 'dist');
const V = Date.now().toString(36);

fs.rmSync(OUT, { recursive: true, force: true });
const put = (p, s) => { const f = path.join(OUT, p); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, s); };
const copyDir = (a, b) => fs.existsSync(a) && fs.cpSync(a, b, { recursive: true });
copyDir(path.join(ROOT, 'public'), OUT);

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const paras = s => String(s || '').split(/\n\s*\n/).map(p => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`).join('');
const sid = f => f.replace(/\.html?$/, '');
const wheel = cls => `<svg class="${cls}" viewBox="0 0 40 40" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="20" cy="20" r="15"/><circle cx="20" cy="20" r="3.2"/><path d="M20 5v30M5 20h30M9.4 9.4l21.2 21.2M30.6 9.4L9.4 30.6"/></g></svg>`;

// 책 정보 모으기 (번역이 없으면 영어 원문을 쓰고 표시)
const homeOf = Object.fromEntries(CAT.categories.flatMap(c => c.books.map(b => [b.slug, b])));
function bookInfo(slug) {
  const b = CAT.books[slug], h = homeOf[slug] || {}, k = KO.books[slug] || {}, d = KO.book_detail[slug] || {};
  const stories = Object.values(b.stories);
  const unit = /Chapters/.test((h.lines || []).join(' ')) ? U.chapters : U.stories;
  const nImg = stories.reduce((n, s) => n + s.items.filter(i => i.img).length, 0);
  const ready = stories.filter(s => READY[`${slug}/${sid(s.file)}`]).length;
  return {
    slug, en: b.title, title: k.title || b.title, sub: k.sub ?? '', style: KO.styles[b.style] || b.style,
    intro: d.intro || '', introEn: b.intro, unit, nStory: stories.length, nImg, ready,
    tags: (h.tags || []).map(t => KO.tags[t] || t), cover: `${S.img_base}/covers/${slug}.jpg`, d,
  };
}
const storyTitle = (slug, s) => KO.book_detail[slug]?.stories?.[s.file]?.title || s.title;

function layout({ title, body, desc = '', page = '', image = '' }) {
  const t = title ? `${title} · ${S.title}` : `${S.title} — 법을 담은 그림책`;
  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(t)}</title>
<meta name="description" content="${esc(desc || S.intro)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(S.title)}">
<meta property="og:title" content="${esc(t)}">
<meta property="og:description" content="${esc(desc || S.intro)}">
${image ? `<meta property="og:image" content="${esc(image)}">` : ''}
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<meta name="theme-color" content="#F7F1E5">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/sb.css?v=${V}">
</head>
<body data-page="${page}">
<header class="site"><div class="wrap head-row">
  <a class="brand" href="/">${wheel('brand-mark')}<span><span class="brand-name">${esc(S.title)}</span><span class="brand-sub">${esc(S.sub)}</span></span></a>
  <nav class="head-nav"><a href="/">${U.home}</a><a href="/about/">소개</a><a class="lib" href="${esc(S.library_url)}">법보시 도서관 ↗</a></nav>
</div></header>
<main>${body}</main>
<footer class="site"><div class="wrap">
  <p>${esc(S.credit)}</p>
  <p><a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/deed.ko">CC BY-SA 4.0</a> · <a href="${esc(S.orig_url)}">dharma-storybooks.net</a> · <a href="${esc(S.library_url)}">붓다담마 법보시 도서관</a></p>
  <p class="sadhu">이 법보시의 공덕을 모든 존재와 함께 나눕니다. Sādhu! Sādhu! Sādhu!</p>
</div></footer>
<script src="/sb.js?v=${V}" defer></script>
</body>
</html>`;
}

const card = b => `<a class="bcard" href="/${b.slug}/" data-q="${esc([b.title, b.sub, b.en, b.style, ...b.tags].join(' ').toLowerCase())}">
  <div class="bcover"><img src="${esc(b.cover)}" alt="" loading="lazy" onerror="this.parentNode.classList.add('nocover')"><span class="ph">${esc(b.title)}</span></div>
  <div class="bmeta"><h3>${esc(b.title)}</h3>${b.sub ? `<p class="sub">${esc(b.sub)}</p>` : ''}
  <p class="cnt">${esc(b.style)} · ${b.unit} ${b.nStory}편 · ${U.posters} ${b.nImg.toLocaleString()}장</p>
  ${b.ready ? `<span class="badge ko">${U.ko_ready} ${b.ready}편</span>` : `<span class="badge">${U.en_only}</span>`}</div></a>`;

// 첫 화면
put('index.html', layout({ page: 'home', body: `<section class="hero"><div class="wrap">
  <h1>법을 담은 그림책</h1><p>${esc(S.intro)}</p>
  <div class="filter"><input id="q" type="search" placeholder="${U.filter}" aria-label="${U.filter}"><button id="qReset" type="button">${U.reset}</button></div>
</div></section>
<div class="wrap">${CAT.categories.map(c => ({ ...c, books: c.books.filter(b => !BOTTOM.includes(b.slug)) })).filter(c => c.books.length).map(c => `<section class="cat"><h2>${esc(KO.categories[c.name] || c.name)}</h2>
  <div class="grid">${c.books.map(b => card(bookInfo(b.slug))).join('')}</div></section>`).join('')}
${BOTTOM.length ? `<section class="cat bottom"><h2>${esc(KO.bottom.name)}</h2><p class="muted">${esc(KO.bottom.note)}</p>
  <div class="grid">${BOTTOM.map(s => card(bookInfo(s))).join('')}</div></section>` : ''}
<p id="noRes" class="muted" hidden>${U.no_result}</p></div>` }));

// 책 화면 · 이야기 화면
for (const slug of Object.keys(CAT.books)) {
  const B = CAT.books[slug], b = bookInfo(slug), d = b.d;
  const list = Object.values(B.stories);
  const toc = B.toc.filter(t => t.h || t.story).map(t => t.h
    ? `<li class="sec">${esc(d.sections?.[t.h] || t.h)}</li>`
    : (() => { const s = B.stories[t.story]; const r = READY[`${slug}/${sid(s.file)}`];
      return `<li><a href="/${slug}/${sid(s.file)}/">${esc(storyTitle(slug, s))}</a>${r ? `<span class="badge ko">${U.ko_ready}</span>` : ''}</li>`; })()).join('');
  put(`${slug}/index.html`, layout({ title: b.title, page: 'book', desc: b.sub || b.title, body: `<div class="wrap book">
  <nav class="crumb"><a href="/">${U.home}</a></nav>
  <div class="book-head"><div class="bcover big"><img src="${esc(b.cover)}" alt="" onerror="this.parentNode.classList.add('nocover')"><span class="ph">${esc(b.title)}</span></div>
  <div><h1>${esc(b.title)}</h1>${b.sub ? `<p class="sub">${esc(b.sub)}</p>` : ''}<p class="en">${esc(b.en)}</p>
  <p class="cnt">${esc(b.style)} · ${b.unit} ${b.nStory}편 · ${U.posters} ${b.nImg.toLocaleString()}장</p>
  <p class="tags">${b.tags.map(t => `<span>${esc(t)}</span>`).join('')}</p></div></div>
  <div class="prose">${b.intro ? paras(b.intro) : `<p class="muted">책 소개를 우리말로 옮기는 중입니다. 아래는 영어 원문입니다.</p><p lang="en">${esc(b.introEn)}</p>`}</div>
  <h2>차례</h2><ol class="toc">${toc}</ol>
  <p class="orig"><a href="${S.orig_url}${slug}/index.htm">${U.en_link} ↗</a></p></div>` }));

  list.forEach((s, i) => {
    const key = `${slug}/${sid(s.file)}`, n = READY[key];
    const k = d.stories?.[s.file] || {};
    const prev = list[i - 1], next = list[i + 1];
    const imgs = n ? Array.from({ length: n }, (_, j) => String(j + 1).padStart(2, '0')) : [];
    const viewer = n ? `<div class="sv" id="sv" data-key="${esc(key)}" tabindex="0" aria-label="그림책 보기 (← → 키로 넘기기)">
  <div class="sv-track">${imgs.map((x, j) => `<figure class="sv-page"><img src="${S.img_base}/${key}/big/${x}.jpg" data-big="${S.img_base}/${key}/big/${x}.jpg" data-s="${S.img_base}/${key}/s/${x}.jpg" alt="${j + 1}쪽" ${j > 1 ? 'loading="lazy"' : ''}></figure>`).join('')}</div>
  <button class="sv-btn prev" aria-label="앞 그림">‹</button><button class="sv-btn next" aria-label="다음 그림">›</button>
  <div class="sv-bar"><span class="sv-count">1 / ${n}</span><button class="sv-auto" aria-pressed="false">▶ 자동<span class="lg"> 넘김</span></button><button class="sv-save" aria-pressed="false" title="작은 그림으로 보아 휴대폰 데이터를 아낍니다"><span class="lg">데이터 </span>절약</button><button class="sv-full">⛶ 전체<span class="lg"> 화면</span></button></div></div>
  <div class="sv-thumbs">${imgs.map((x, j) => `<button data-i="${j}"><img src="${S.img_base}/${key}/s/${x}.jpg" alt="${j + 1}쪽" loading="lazy"></button>`).join('')}</div>`
      : `<div class="notyet"><p>이 이야기의 그림은 아직 우리말로 옮기는 중입니다.</p><p><a class="btn" href="${S.orig_url}${slug}/${s.file}">${U.en_link} ↗</a></p></div>`;
    put(`${key}/index.html`, layout({ title: `${storyTitle(slug, s)} — ${b.title}`, page: 'story', desc: k.intro || s.intro, body: `<div class="wrap story">
  <nav class="crumb"><a href="/">${U.home}</a> › <a href="/${slug}/">${esc(b.title)}</a></nav>
  <h1>${esc(storyTitle(slug, s))}</h1>
  ${viewer}
  <div class="prose">${k.intro ? paras(k.intro) : (s.intro ? `<p lang="en" class="muted">${esc(s.intro)}</p>` : '')}</div>
  <nav class="pn">${prev ? `<a href="/${slug}/${sid(prev.file)}/">← ${esc(storyTitle(slug, prev))}</a>` : '<span></span>'}${next ? `<a href="/${slug}/${sid(next.file)}/">${esc(storyTitle(slug, next))} →</a>` : '<span></span>'}</nav>
  <p class="orig"><a href="${S.orig_url}${slug}/${s.file}">${U.en_link} ↗</a></p></div>` }));
  });
}

// 소개
put('about/index.html', layout({ title: '소개', page: 'about', body: `<div class="wrap"><article class="prose">
<h1>붓다담마 그림책 소개</h1>
<p>${esc(S.intro)}</p>
<h2>원작</h2><p>이 그림책들은 아난다조띠 스님(Bhante Ānandajoti)이 기획하고 이끈 『Dharma Storybooks』(<a href="${S.orig_url}">dharma-storybooks.net</a>)를 우리말로 옮긴 것입니다. 원작의 그림은 스님의 지도로 Gemini Notebook이 만들었습니다. 스님은 1987년부터 아시아에서 지내며 1996년 테라와다 전통에서 비구계를 받았습니다.</p>
<h2>한국어판</h2><p>그림 속 말풍선과 설명 상자의 영어를 지우고 우리말을 넣었습니다. 그림 자체는 원작 그대로입니다. 책 소개와 줄거리도 우리말로 옮겼습니다. 아직 번역하지 않은 이야기는 영어 원본으로 연결됩니다. 번역은 <a href="${S.library_url}">붓다담마 법보시 도서관</a>(我無말들)이 맡았습니다.</p>
<h2>라이선스</h2><p>${esc(S.license)}</p>
</article></div>` }));

put('robots.txt', `User-agent: *\nAllow: /\nSitemap: ${S.url}/sitemap.xml\n`);
const urls = ['/', '/about/', ...Object.keys(CAT.books).flatMap(s => [`/${s}/`, ...Object.values(CAT.books[s].stories).map(x => `/${s}/${sid(x.file)}/`)])];
put('sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.map(u => `<url><loc>${S.url}${u}</loc></url>`).join('')}</urlset>\n`);
console.log('pages', urls.length, 'ready stories', Object.keys(READY).length);
