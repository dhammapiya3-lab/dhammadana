// 붓다담마 그림책 — 목록 찾기 · 그림책 뷰어
(() => {
  // 첫 화면: 책·이야기 제목, 인물, 주제로 찾기 (운영자 요청, 2026-11-14)
  // 띄어쓰기·빠알리 발음 기호(ā=a)·대소문자는 무시, 낱말 여럿이면 모두 들어간 것만. 책 카드와 함께 이야기도 찾아 보여 줌
  const q = document.getElementById('q');
  if (q) {
    const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[\s·.,:;!?'"“”‘’()\[\]『』「」<>~—–-]+/g, '');
    const words = v => String(v).trim().split(/\s+/).map(norm).filter(Boolean);
    const cards = [...document.querySelectorAll('.bcard')].map(c => ({ c, n: norm(c.dataset.q) }));
    const sres = document.getElementById('sres'), sol = sres.querySelector('ol');
    const h = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    let IDX = null;
    const load = () => IDX || (IDX = fetch('/search.json').then(r => r.json()).then(a => a.map(o => ({ ...o, nt: norm(o.t + ' ' + o.e), nb: norm(o.b), nx: norm(o.x) }))).catch(() => []));
    const snip = (x, ws) => { // 줄거리에서 찾은 낱말 둘레
      const raw = String(x || ''); if (!raw) return '';
      const lw = String(q.value).trim().split(/\s+/).filter(Boolean);
      let i = -1; for (const w of lw) { i = raw.toLowerCase().indexOf(w.toLowerCase()); if (i >= 0) break; }
      if (i < 0) return h(raw.slice(0, 70)) + (raw.length > 70 ? '…' : '');
      const a = Math.max(0, i - 30), part = raw.slice(a, i + 60);
      return (a ? '…' : '') + h(part).replace(new RegExp(lw.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'gi'), m => `<mark>${m}</mark>`) + (i + 60 < raw.length ? '…' : '');
    };
    let seq = 0;
    const run = async () => {
      const ws = words(q.value), my = ++seq;
      const hit = n => ws.every(w => n.includes(w));
      let any = false;
      cards.forEach(({ c, n }) => { const on = !ws.length || hit(n); c.hidden = !on; any ||= on; });
      document.querySelectorAll('.cat, .tier').forEach(s => { s.hidden = ![...s.querySelectorAll('.bcard')].some(c => !c.hidden); });
      if (!ws.length) { sres.hidden = true; document.getElementById('noRes').hidden = true; return; }
      const idx = await load(); if (my !== seq) return;
      // 제목에서 찾은 것 먼저, 그다음 줄거리·책 이름
      const scored = idx.map(o => { const all = o.nt + o.nb + o.nx; if (!hit(all)) return null; return { o, s: (hit(o.nt) ? 0 : hit(o.nt + o.nb) ? 1 : 2) + (o.r ? 0 : 0.5) }; }).filter(Boolean).sort((a, b) => a.s - b.s);
      sres.hidden = !scored.length;
      document.getElementById('sresN').textContent = scored.length + '편';
      sol.innerHTML = scored.slice(0, 60).map(({ o }) => `<li><a href="${h(o.u)}"><b>${h(o.t)}</b> <span class="muted">— ${h(o.bt || o.b)}</span></a>${o.x ? `<p>${snip(o.x)}</p>` : ''}</li>`).join('') + (scored.length > 60 ? `<li class="muted">… 그 밖에 ${scored.length - 60}편. 낱말을 더 넣어 좁혀 보세요.</li>` : '');
      document.getElementById('noRes').hidden = any || scored.length > 0;
    };
    let tm; q.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(run, 150); });
    q.addEventListener('focus', load, { once: true });
    // 찾기 단추: 접어 두면 묶음마다 한 줄만(들어가는 만큼, 많이 나오는 순서), 펼치면 전체를 가나다 순 (운영자 요청, 2026-11-21)
    const fitRow = row => {
      const tog = row.querySelector('.qtog'); if (!tog) return;
      const bs = [...row.querySelectorAll('button[data-q]')].sort((a, b) => a.dataset.i - b.dataset.i);
      bs.forEach(b => row.insertBefore(b, tog));
      if (tog.classList.contains('on')) { bs.sort((a, b) => a.textContent.localeCompare(b.textContent, 'ko')).forEach(b => { b.hidden = false; row.insertBefore(b, tog); }); tog.hidden = false; return; }
      bs.forEach(b => b.hidden = false); tog.hidden = true;
      const top = bs[0].offsetTop, over = () => bs.some(b => !b.hidden && b.offsetTop > top + 4);
      if (!over()) return;
      tog.hidden = false;
      for (let k = bs.length - 1; k > 0 && (over() || tog.offsetTop > top + 4); k--) bs[k].hidden = true;
    };
    const rows = [...document.querySelectorAll('.qex .qrow')];
    const fitAll = () => rows.forEach(fitRow);
    fitAll(); document.fonts?.ready.then(fitAll);
    let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(fitAll, 120); });
    rows.forEach(row => { const x = row.querySelector('.qtog'); if (x) x.onclick = () => { const open = x.classList.toggle('on'); x.textContent = open ? '－ 접기' : '＋ 더 보기'; fitRow(row); }; });
    document.querySelectorAll('.qex button:not(.qtog)').forEach(x => x.onclick = () => { q.value = x.dataset.q; run(); document.getElementById('sres').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    document.getElementById('qReset').onclick = () => { q.value = ''; run(); q.focus(); };
  }

  // 내 서재 화면 · 책 화면의 '이어 읽기'
  const shelfAll = () => { try { return JSON.parse(localStorage.getItem('sb-shelf') || '{}'); } catch (e) { return {}; } };
  // 예전에 한 칸에 저장된 영어판 기록은 '<책>.en' 칸으로 옮김 (2026-11-22)
  try { const a0 = shelfAll(); let ch = false;
    for (const [k, r] of Object.entries(a0)) if (!k.endsWith('.en') && r && !r.del && /-en\/$/.test(r.url || '')) { if (!a0[k + '.en'] || (a0[k + '.en'].t || 0) < r.t) a0[k + '.en'] = { ...r, lang: 'en' }; a0[k] = { del: true, t: r.t }; ch = true; }
    if (ch) localStorage.setItem('sb-shelf', JSON.stringify(a0)); } catch (e) {}
  // 그림 책갈피 (운영자 요청, 2026-11-21): 법문·어린이 법회에서 다시 보여 줄 그림을 ☆ 로 표시해 두고 내 서재에서 모아 봄.
  // sb-marks = { '<책>/<이야기>#<쪽>': {book, bookTitle, story, url, page, n, img, t} 또는 {del:true, t} }
  const marksAll = () => { try { return JSON.parse(localStorage.getItem('sb-marks') || '{}'); } catch (e) { return {}; } };
  const marksPut = m => { try { localStorage.setItem('sb-marks', JSON.stringify(m)); localStorage.setItem('sb-marks-t', String(Date.now())); } catch (e) {} };
  const marksMerge = (a, b) => { const o = { ...a }; for (const [k, v] of Object.entries(b || {})) if (!o[k] || (v.t || 0) > (o[k].t || 0)) o[k] = v; return o; };
  // 회원: 법보시 도서관(dhammadana.kr)과 같은 회원. 책마다 'sb-b-<책>' 으로 맞춤 (나중에 읽은 쪽이 이김)
  const API = 'https://dhammadana.kr/api/account';
  const ls = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { return null; } };
  const acct = { get token() { return ls('sb-acct') || ''; }, get id() { return ls('sb-acct-id') || ''; } };
  const api = async (op, o = {}) => {
    const r = await fetch(API, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ op, token: acct.token, ...o }), keepalive: op === 'sync' });
    let j = {}; try { j = await r.json(); } catch (e) {}
    if (j.relogin) { ls('sb-acct', null); ls('sb-acct-id', null); acctBtn(); }
    if (!r.ok || j.error) throw new Error(j.error || '연결이 잘 되지 않습니다. 잠시 뒤에 다시 해 주세요.');
    return j;
  };
  const acctBtn = () => { const b = document.getElementById('acctBtn'); if (b) b.textContent = acct.id ? '👤 ' + acct.id : '로그인'; };
  acctBtn();
  let syncing = false, syncTimer = null;
  window.sbSync = async () => {
    if (!acct.token || syncing) return false; syncing = true;
    try {
      const all = shelfAll(), data = {};
      for (const [slug, r] of Object.entries(all)) data['sb-b-' + slug] = { v: r.del ? null : r, t: r.t || 1 };
      data['sb-b-_marks'] = { v: marksAll(), t: +(ls('sb-marks-t') || 1) };
      const j = await api('sync', { data, only: 'sb' });
      let changed = false; const cur = shelfAll();
      for (const [k, x] of Object.entries(j.data || {})) {
        if (!k.startsWith('sb-b-')) continue;
        if (k === 'sb-b-_marks') {  // 책갈피: 기기마다 더한 것을 모두 살림
          const mine = marksAll(), m = marksMerge(mine, x.v || {});
          if (JSON.stringify(m) !== JSON.stringify(mine)) { ls('sb-marks', JSON.stringify(m)); document.dispatchEvent(new Event('sb-marks')); }
          if (JSON.stringify(m) !== JSON.stringify(x.v || {})) { ls('sb-marks-t', String(Date.now())); window.sbSyncSoon && setTimeout(window.sbSyncSoon, 0); }
          continue;
        }
        const slug = k.slice(5), mine = cur[slug];
        if (mine && (mine.t || 0) >= x.t) continue;
        if (x.v) { cur[slug] = { ...x.v, t: x.t }; const key = String(x.v.url || '').replace(/^\/|\/$/g, ''); if (key) ls('sb-pos-' + key, String((x.v.page || 1) - 1)); }
        else cur[slug] = { del: true, t: x.t };
        changed = true;
      }
      if (changed) { ls('sb-shelf', JSON.stringify(cur)); document.dispatchEvent(new Event('sb-shelf')); }
      return true;
    } catch (e) { return false; } finally { syncing = false; }
  };
  window.sbSyncSoon = () => { if (!acct.token) return; clearTimeout(syncTimer); syncTimer = setTimeout(window.sbSync, 3000); };
  document.addEventListener('visibilitychange', () => { if (!acct.token) return; if (document.visibilityState === 'visible') window.sbSync(); else if (syncTimer) { clearTimeout(syncTimer); syncTimer = null; window.sbSync(); } });
  if (acct.token) window.sbSync();

  // 로그인 화면
  const lf = document.getElementById('loginForm');
  if (lf) {
    const out = document.getElementById('loginOut'), msg = document.getElementById('loginMsg');
    const view = () => { lf.hidden = !!acct.token; out.hidden = !acct.token; document.getElementById('meId').textContent = acct.id; };
    view();
    lf.onsubmit = async e => {
      e.preventDefault(); msg.hidden = true; const btn = lf.querySelector('button'); btn.disabled = true;
      try {
        const j = await api('login', { id: lf.elements.id.value.trim(), pw: lf.elements.pw.value });
        ls('sb-acct', j.token); ls('sb-acct-id', j.id); acctBtn(); lf.reset();
        await window.sbSync(); view();
      } catch (err) { msg.textContent = err.message; msg.hidden = false; }
      btn.disabled = false;
    };
    document.getElementById('logout').onclick = async () => {
      await window.sbSync(); try { await api('logout'); } catch (e) {}
      ls('sb-acct', null); ls('sb-acct-id', null); acctBtn(); view();
    };
  }
  const h = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const shelfEl = document.getElementById('shelf');
  if (shelfEl) {
    const draw = () => {
      const all = shelfAll(), list = Object.entries(all).filter(([, r]) => !r.del).sort((a, b) => b[1].t - a[1].t);
      const lg = document.getElementById('shelfLogin'); if (lg) lg.hidden = !!acct.token;
      document.getElementById('shelfEmpty').hidden = list.length > 0;
      shelfEl.innerHTML = list.map(([id, r]) => { const slug = id.replace(/\.en$/, ''), en = id !== slug; return `<div class="sh-item">
        <a class="sh-cover" href="/${h(slug)}/"><img src="${h(r.cover)}" alt="" loading="lazy" onerror="this.remove()"></a>
        <div class="sh-meta"><h2><a href="/${h(slug)}/">${h(r.book)}</a>${en ? ' <span class="badge en" lang="en">English</span>' : ''}</h2>
        <p>읽던 이야기: <b>${h(r.story)}</b> · ${r.page} / ${r.n}쪽</p>
        <p class="muted">${new Date(r.t).toLocaleDateString('ko-KR')}에 읽음</p>
        <p class="sh-act"><a class="btn" href="${h(r.url)}">▶ 이어 읽기</a> <button type="button" data-del="${h(id)}">목록에서 빼기</button></p></div></div>`; }).join('');
      shelfEl.querySelectorAll('[data-del]').forEach(b => b.onclick = () => {
        const a = shelfAll(); a[b.dataset.del] = { del: true, t: Date.now() };
        ls('sb-shelf', JSON.stringify(a)); window.sbSyncSoon();
        draw();
      });
    };
    draw(); document.addEventListener('sb-shelf', draw);
    const mk = document.getElementById('marks');
    if (mk) {
      const drawM = () => {
        const list = Object.entries(marksAll()).filter(([, r]) => !r.del).sort((a, b) => b[1].t - a[1].t);
        document.getElementById('marksWrap').hidden = !list.length;
        mk.innerHTML = list.map(([id, r]) => `<figure class="mk-item"><a href="${h(r.url)}#p${r.page}"><img src="${h(r.img)}" alt="" loading="lazy"></a>
          <figcaption><b>${h(r.story)}</b> · ${r.page}쪽<br><span class="muted">${h(r.bookTitle)}</span>
          <button type="button" data-mdel="${h(id)}" title="책갈피 지우기">✕ 지우기</button></figcaption></figure>`).join('');
        mk.querySelectorAll('[data-mdel]').forEach(b => b.onclick = () => { const m = marksAll(); m[b.dataset.mdel] = { del: true, t: Date.now() }; marksPut(m); window.sbSyncSoon(); drawM(); });
      };
      drawM(); document.addEventListener('sb-marks', drawM);
    }
  }
  const resume = document.getElementById('resume');
  if (resume) {
    const show = () => { const a = shelfAll(), s0 = resume.dataset.slug;
      const rs = [[a[s0], ''], [a[s0 + '.en'], 'English']].filter(([r]) => r && !r.del);
      resume.hidden = !rs.length; resume.className = 'resume';
      resume.innerHTML = rs.map(([r, l]) => `<div class="resume-row"><span>${l ? `<span class="badge en" lang="en">${l}</span> ` : ''}읽던 곳: <b>${h(r.story)}</b> · ${r.page} / ${r.n}쪽</span><a class="btn" href="${h(r.url)}">▶ 이어 읽기</a></div>`).join(''); };
    show(); document.addEventListener('sb-shelf', show);
  }

  // 그림책 뷰어
  const sv = document.getElementById('sv');
  if (!sv) return;
  const track = sv.querySelector('.sv-track');
  let pages, thumbs, KEY, endCard;
  const count = sv.querySelector('.sv-count');
  const autoBtn = sv.querySelector('.sv-auto');
  let cur = 0, timer = null;
  const last = () => pages.length - (endCard ? 0 : 1);  // 끝 화면(다음 이야기)이 있으면 그것까지
  // 한 화를 다 보면 끝 화면: 전체 화면에서 나가지 않고 다음 이야기를 이 자리에서 이어 봄
  const setup = () => {
    pages = [...sv.querySelectorAll('.sv-page:not(.sv-end)')];
    if ((matchMedia('(pointer:coarse)').matches || /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)) && !(document.fullscreenElement === sv || sv.classList.contains('sv-max')))
      pages.forEach(p => { const im = p.querySelector('img'); if (im && im.dataset.s && !im.complete) im.src = im.dataset.s; });  // 휴대폰 보통 화면은 800px 그림부터 (넘기기 빠르게, 2026-11-24)
    thumbs = [...document.querySelectorAll('.sv-thumbs button')];
    thumbs.forEach(t => t.onclick = () => go(+t.dataset.i));
      KEY = 'sb-pos-' + sv.dataset.key;
    endCard = null;
    if (sv.dataset.next) {
      endCard = document.createElement('figure');
      endCard.className = 'sv-page sv-end';
      endCard.innerHTML = `<div><p class="e1">이야기를 다 보셨습니다</p><button type="button" class="e2">다음 이야기 ▶<b></b></button><p class="e3">화면을 나가지 않고 바로 이어집니다</p></div>`;
      endCard.querySelector('b').textContent = sv.dataset.nextTitle;
      endCard.querySelector('button').onclick = e => { e.stopPropagation(); loadNext(); };
      track.append(endCard);
    }
  };
  const loadNext = (back = false) => loadStory(back ? sv.dataset.prev : sv.dataset.next, back);
  // 다른 이야기를 이 자리에서 불러옴 (전체 화면 그대로). back 이면 그 이야기의 마지막 그림부터
  const loadStory = async (url, back) => {
    if (!url || sv.classList.contains('loading')) return;
    sv.classList.add('loading');
    try {
      const doc = new DOMParser().parseFromString(await (await fetch(url)).text(), 'text/html');
      const nv = doc.getElementById('sv');
      if (!nv) { location.href = url; return; }
      track.innerHTML = nv.querySelector('.sv-track').innerHTML;
      for (const k of ['key', 'next', 'nextTitle', 'prev', 'prevTitle', 'book', 'bookTitle', 'cover', 'title']) { if (nv.dataset[k]) sv.dataset[k] = nv.dataset[k]; else delete sv.dataset[k]; }
      { const a = document.querySelector('.story-dl'), b = doc.querySelector('.story-dl');  // 이 이야기 내려받기 줄
        if (a) a.remove(); if (b) document.querySelector('.sv-thumbs')?.after(document.importNode(b, true));
        const nd = doc.querySelector('.sv-dl'), od = sv.querySelector('.sv-dl'); if (nd && od) od.dataset.name = nd.dataset.name; }
      for (const sel of ['.story h1', '.sv-thumbs', '.story .prose', '.story .pn', '.story .orig']) {
        const a = document.querySelector(sel), b = doc.querySelector(sel);
        if (a && b) a.replaceWith(document.importNode(b, true));
      }
      document.title = doc.title;
      history.pushState({}, '', url);
      setup();
      if (saveBtn.getAttribute('aria-pressed') === 'true') setSave(true);
      cur = -1;
      { const ns = nv.querySelector('.sv-say'); if (sayBtn) sayBtn.hidden = !ns; }
      if (back) requestAnimationFrame(() => go(pages.length - 1, false)); else { track.scrollTo({ left: 0 }); show(0); }
      if (V.on) { V.title = true; V.i = -1; vLoad().then(ok => ok ? vPage(0) : vStop('다음 이야기에는 읽어 줄 글이 아직 없습니다.')); }
    } catch (e) { location.href = url; }
    sv.classList.remove('loading');
  };
  addEventListener('popstate', () => location.reload());

  const go = (i, smooth = true) => {
    if (endCard && i > pages.length && cur >= pages.length) { loadNext(); return; }  // 끝 화면에서 › → 다음 이야기
    if (i < 0 && cur <= 0 && sv.dataset.prev) { loadNext(true); return; }  // 첫 그림에서 ‹ → 이전 이야기의 마지막 그림
    i = Math.max(0, Math.min(last(), i));
    goT = i; goAt = Date.now();
    track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? 'smooth' : 'auto' });
  };
  // 빠르게 잇달아 누르기 (운영자 요청, 2026-11-25 '넘기는 반응이 느림' — 세 번째): 넘어가는 동안(부드럽게 미끄러지는 0.3~0.5초) 또 누르면
  // 아직 바뀌지 않은 cur 기준이라 같은 쪽으로 가서 누른 것이 사라졌음 → 방금 가려던 쪽(goT)을 기준으로 한 장 더
  let goT = -1, goAt = 0;
  const base = () => (Date.now() - goAt < 700 && goT >= 0) ? goT : cur;
  const markBtn = sv.querySelector('.sv-mark');
  const markId = i => `${sv.dataset.key}#${i + 1}`;
  const markShow = () => { if (!markBtn) return; const r = marksAll()[markId(cur)], on = !!(r && !r.del) && cur < pages.length;
    markBtn.setAttribute('aria-pressed', on ? 'true' : 'false'); markBtn.firstChild.textContent = on ? '★' : '☆'; markBtn.hidden = cur >= pages.length; };
  if (markBtn) markBtn.onclick = () => {
    if (cur >= pages.length) return;
    const m = marksAll(), id = markId(cur), r = m[id], d = sv.dataset, im = pages[cur].querySelector('img');
    if (r && !r.del) m[id] = { del: true, t: Date.now() };
    else m[id] = { book: d.book, bookTitle: d.bookTitle, story: d.title, url: '/' + d.key + '/', page: cur + 1, n: pages.length, img: im?.dataset.s || im?.src, t: Date.now() };
    marksPut(m); markShow(); window.sbSyncSoon && window.sbSyncSoon();
    const t = document.createElement('div'); t.className = 'sv-toast'; t.textContent = (r && !r.del) ? '책갈피를 지웠습니다' : '책갈피에 넣었습니다 — 내 서재에서 모아 봅니다';
    sv.append(t); setTimeout(() => t.remove(), 1800);
  };
  document.addEventListener('sb-marks', () => markShow());
  const show = i => {
    if (i !== cur) zReset();
    cur = i;
    count.textContent = i >= pages.length ? '다음 이야기' : `${i + 1} / ${pages.length}`;
    thumbs.forEach((t, j) => t.classList.toggle('on', j === i));
    thumbs[i]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    try { localStorage.setItem(KEY, i); } catch (e) {}
    if (i < pages.length) shelfSave(i);
    markShow();
    if (V.on && !V.self && i < pages.length && i !== V.i) vPage(i);  // 읽는 중에 손으로 넘기면 그 쪽부터 읽음
    warm(i);
  };
  // 넘기기 빠르게 (운영자 요청, 2026-11-24 '핸드폰에서 넘기는 반응이 느려짐' — 두 번째): 지금 그림의 앞뒤(앞 1장·다음 3장)를 미리 받아 풀어 둠.
  // 휴대폰(손가락 화면)에서 전체 화면이 아니고 확대하지 않았을 때는 800px 그림(s, 한 장 약 0.1MB)을 씀 — 원본(big, 약 1MB·2645px)은 화면보다 훨씬 커서
  // 받고 풀고 그리는 데 오래 걸림. 전체 화면·확대하면 원본으로 바꾸고, 멀리 떨어진 그림은 다시 800px 로 돌려 휴대폰 메모리를 덜 씀.
  const coarse = matchMedia('(pointer:coarse)').matches || /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
  const fullNow = () => document.fullscreenElement === sv || sv.classList.contains('sv-max') || sv.classList.contains('sv-rot');
  const wantBig = () => !coarse || fullNow() || Z.s > 1;
  const setSrc = (im, u) => { if (!u || im.getAttribute('src') === u || im.dataset.want === u) return;
    im.dataset.want = u; const n = new Image(); n.src = u;
    (n.decode ? n.decode() : Promise.resolve()).catch(() => {}).then(() => { if (im.dataset.want === u) im.src = u; }); };
  const warm = i => { const big = wantBig();
    pages.forEach((pg, j) => { const im = pg.querySelector('img'); if (!im) return; const d = j - i;
      if (d >= -1 && d <= 3) { im.loading = 'eager'; setSrc(im, big ? im.dataset.big : im.dataset.s); }
      else if (coarse && Math.abs(d) > 5 && im.getAttribute('src') !== im.dataset.s && im.complete) { im.dataset.want = ''; im.src = im.dataset.s; } }); };
  new MutationObserver(() => { clearTimeout(warm.t); warm.t = setTimeout(() => cur >= 0 && warm(cur), 120); }).observe(sv, { attributes: true, attributeFilter: ['class'] });
  document.addEventListener('fullscreenchange', () => setTimeout(() => cur >= 0 && warm(cur), 150));
  // 내 서재: 책마다 마지막으로 읽던 이야기와 쪽 (운영자 요청, 2026-11-14)
  const shelfSave = i => {
    const d = sv.dataset; if (!d.book) return;
    try {
      const all = JSON.parse(localStorage.getItem('sb-shelf') || '{}');
      // 영어판(키 끝 -en)은 한글판과 따로 저장 — 칸 이름 '<책>.en' (운영자 요청, 2026-11-22)
      const en = /-en$/.test(d.key || '');
      all[d.book + (en ? '.en' : '')] = { book: d.bookTitle, lang: en ? 'en' : 'ko', cover: d.cover, story: d.title, url: '/' + d.key + '/', page: i + 1, n: pages.length, t: Date.now() };
      localStorage.setItem('sb-shelf', JSON.stringify(all));
    } catch (e) {}
    window.sbSyncSoon && window.sbSyncSoon();
  };
  // 지금 보는 그림 한 장 내려받기 (원본 크기, 한글 파일 이름)
  const dlBtn = sv.querySelector('.sv-dl');
  if (dlBtn) dlBtn.addEventListener('click', e => {
    const i = Math.min(cur, pages.length - 1), nn = String(i + 1).padStart(2, '0');
    dlBtn.href = `/dl/${sv.dataset.key}/${nn}.jpg?n=${encodeURIComponent((sv.dataset.dlName || dlBtn.dataset.name) + '_' + nn + '.jpg')}`;
  });
  track.addEventListener('scroll', () => {
    const i = Math.round(track.scrollLeft / track.clientWidth);
    if (i !== cur) show(i);
  }, { passive: true });
  sv.querySelector('.prev').onclick = () => go(base() - 1);
  sv.querySelector('.next').onclick = () => go(base() + 1);
  sv.addEventListener('keydown', e => {
    if (['ArrowRight', 'k', ' ', 'PageDown'].includes(e.key)) { go(base() + 1); e.preventDefault(); }
    if (['ArrowLeft', 'j', 'PageUp'].includes(e.key)) { go(base() - 1); e.preventDefault(); }
    if (e.key === 'Home') go(0); if (e.key === 'End') go(pages.length - 1);
    if (e.key === 'Enter' && endCard && cur >= pages.length) loadNext();
  });
  // ── 손가락 두 개로 벌려 확대 (전체 화면), 확대한 채 한 손가락으로 끌어 옮기기, 두 번 톡톡 = 2배/원래대로
  const Z = { s: 1, x: 0, y: 0, img: null, pinch: null, pan: null, tap: 0, moved: false };
  const zApply = () => {
    if (!Z.img) return;
    Z.img.style.transform = Z.s > 1 ? `translate(${Z.x}px,${Z.y}px) scale(${Z.s})` : '';
    if (Z.s > 1 && Z.img.dataset.big) setSrc(Z.img, Z.img.dataset.big);  // 확대할 때는 원본 그림으로
    sv.classList.toggle('sv-zoom', Z.s > 1);
  };
  const zReset = () => { if (Z.img) Z.img.style.transform = ''; Z.s = 1; Z.x = Z.y = 0; Z.img = null; sv.classList.remove('sv-zoom'); };
  const zClamp = () => {
    const w = Z.img.offsetWidth, h = Z.img.offsetHeight, mx = (w * Z.s - w) / 2, my = (h * Z.s - h) / 2;
    Z.x = Math.max(-mx, Math.min(mx, Z.x)); Z.y = Math.max(-my, Math.min(my, Z.y));
  };
  // 돌린 화면(sv-rot)에서는 손가락 움직임을 그림 방향으로 바꿈
  const vec = (dx, dy) => sv.classList.contains('sv-rot') ? [dy, -dx] : [dx, dy];
  const dist = t => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
  const zoomable = () => isMax() || matchMedia('(pointer:coarse)').matches;
  track.addEventListener('touchstart', e => {
    if (!zoomable()) return;
    Z.moved = false;
    if (e.touches.length === 2) {
      const img = pages[cur]?.querySelector('img'); if (!img) return;
      if (Z.img !== img) { zReset(); Z.img = img; }
      Z.pinch = { d: dist(e.touches), s: Z.s }; Z.pan = null;
    } else if (e.touches.length === 1 && Z.s > 1) {
      Z.pan = { x: e.touches[0].clientX, y: e.touches[0].clientY, ox: Z.x, oy: Z.y };
    }
  }, { passive: true });
  track.addEventListener('touchmove', e => {
    if (Z.pinch && e.touches.length === 2) {
      e.preventDefault(); Z.moved = true;
      Z.s = Math.max(1, Math.min(4, Z.pinch.s * dist(e.touches) / Z.pinch.d)); zClamp(); zApply();
    } else if (Z.pan && e.touches.length === 1 && Z.s > 1) {
      e.preventDefault(); Z.moved = true;
      const [dx, dy] = vec(e.touches[0].clientX - Z.pan.x, e.touches[0].clientY - Z.pan.y);
      Z.x = Z.pan.ox + dx; Z.y = Z.pan.oy + dy; zClamp(); zApply();
    }
  }, { passive: false });
  track.addEventListener('touchend', e => {
    if (e.touches.length < 2) Z.pinch = null;
    if (!e.touches.length) {
      Z.pan = null; if (Z.s <= 1.02) zReset();
      // 두 번 톡톡: 2배로 키우거나 원래대로
      const now = Date.now();
      { const t = e.changedTouches[0], r = track.getBoundingClientRect();
        const x = sv.classList.contains('sv-rot') ? (t.clientY - r.top) / r.height : (t.clientX - r.left) / r.width;
        if (Z.s <= 1 && (x < 0.25 || x > 0.75)) { Z.tap = 0; return; } }  // 좌우 넘기기 자리: 두 번 톡톡 확대로 세지 않음 (2026-11-25)
      if (!Z.moved && zoomable() && now - Z.tap < 300) {
        const img = pages[cur]?.querySelector('img');
        if (Z.s > 1) zReset(); else if (img) { zReset(); Z.img = img; Z.s = 2; zApply(); }
        Z.tap = 0; Z.dbl = now;
      } else Z.tap = now;
    }
  }, { passive: true });
  // 마우스(컴퓨터): 그림을 두 번 클릭하면 누른 곳을 2배로 확대 / 원래대로, 확대한 채 끌어 옮기기, 휠로 더 키우거나 줄이기 (운영자 요청, 2026-11-15)
  const mouse = () => !matchMedia('(pointer:coarse)').matches;
  // 한 번 클릭으로 확대·원래대로 (운영자 요청, 2026-11-15). 그림 위에 마우스를 올리면 안내가 뜸
  const zhint = document.createElement('div'); zhint.className = 'sv-zhint'; sv.append(zhint);
  const hintText = () => { zhint.textContent = Z.s > 1 ? '클릭하면 원래 크기로 돌아갑니다 · 끌어서 옮기기' : '클릭하면 확대됩니다'; };
  track.addEventListener('mousemove', e => {
    if (!mouse() || cur >= pages.length || !e.target.closest('.sv-page img')) { zhint.classList.remove('on'); return; }
    hintText(); const r = sv.getBoundingClientRect();
    zhint.style.left = (e.clientX - r.left + 14) + 'px'; zhint.style.top = (e.clientY - r.top + 18) + 'px'; zhint.classList.add('on');
  });
  track.addEventListener('mouseleave', () => zhint.classList.remove('on'));
  track.addEventListener('click', e => {
    if (!mouse() || !e.target.closest('.sv-page img')) return;
    if (Z.dragged) { Z.dragged = false; e.stopImmediatePropagation(); return; }  // 끌어 옮긴 뒤의 클릭은 무시
    e.stopImmediatePropagation();
    const img = pages[cur]?.querySelector('img'); if (!img) return;
    if (Z.s > 1) { zReset(); hintText(); return; }
    zReset(); Z.img = img; Z.s = 2;
    const r = img.getBoundingClientRect(), px = e.clientX - (r.left + r.width / 2), py = e.clientY - (r.top + r.height / 2);
    Z.x = px * (1 - Z.s); Z.y = py * (1 - Z.s); zClamp(); zApply(); hintText();
  }, true);
  let drag = null;
  track.addEventListener('mousedown', e => { if (Z.s > 1 && e.button === 0) { drag = { x: e.clientX, y: e.clientY, ox: Z.x, oy: Z.y, m: false }; e.preventDefault(); } });
  addEventListener('mousemove', e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) drag.m = true; Z.x = drag.ox + dx; Z.y = drag.oy + dy; zClamp(); zApply(); });
  addEventListener('mouseup', () => { if (drag?.m) { Z.dragged = true; setTimeout(() => { Z.dragged = false; }, 0); } drag = null; });
  track.addEventListener('wheel', e => {
    if (e.ctrlKey || e.metaKey || Z.s <= 1 || !Z.img) return;  // Ctrl+휠(브라우저 확대)은 그대로 둠. 확대했을 때만 휠로 크기 조절 (평소 휠은 화면 넘기기 그대로)
    e.preventDefault();
    Z.s = Math.max(1, Math.min(4, Z.s * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    if (Z.s <= 1.02) zReset(); else { zClamp(); zApply(); }
  }, { passive: false });
  sv.addEventListener('keydown', e => { if (e.key === 'Escape' && Z.s > 1) { zReset(); e.stopPropagation(); } }, true);
  let t0 = null;
  track.addEventListener('touchstart', e => { if (sv.classList.contains('sv-rot') && e.touches.length === 1 && Z.s <= 1) t0 = e.touches[0]; else t0 = null; }, { passive: true });
  track.addEventListener('touchend', e => {
    if (!t0 || !sv.classList.contains('sv-rot') || Z.s > 1 || Z.moved) { t0 = null; return; }
    const t = e.changedTouches[0], dy = t.clientY - t0.clientY, dx = t.clientX - t0.clientX; t0 = null;
    if (Math.abs(dy) > 40 && Math.abs(dy) > Math.abs(dx)) go(base() + (dy < 0 ? 1 : -1));
  }, { passive: true });
  // 화면 좌우를 눌러 넘기기 (손가락 화면)
  track.addEventListener('click', e => {
    if (Z.s > 1 || Date.now() - (Z.dbl || 0) < 400) return;  // 확대 중이거나 두 번 톡톡 직후에는 넘기지 않음
    const r = track.getBoundingClientRect(), x = sv.classList.contains('sv-rot') ? (e.clientY - r.top) / r.height : (e.clientX - r.left) / r.width;
    if (x < 0.25) go(base() - 1); else if (x > 0.75) go(base() + 1);
    else if (isFull()) barShow(!sv.classList.contains('bar-on'));  // 전체 화면: 가운데를 누르면 아래 바가 나타나거나 숨음
  });
  // 전체 화면에서는 아래 바를 숨겨 그림이 화면을 꽉 채우게 함 — 마우스를 아래쪽에 가까이 대거나(바 위 포함),
  // 손가락 화면은 그림 가운데를 누르면 나타남. 4초 동안 건드리지 않으면 다시 숨음 (운영자 요청, 2026-11-22)
  const isFull = () => document.fullscreenElement === sv || sv.classList.contains('sv-max') || sv.classList.contains('sv-rot');
  let barT = null;
  const barShow = on => {
    clearTimeout(barT); sv.classList.toggle('bar-on', !!on);
    if (on) barT = setTimeout(() => { if (!sv.querySelector('.sv-bar:hover, .sv-bar :focus-visible')) sv.classList.remove('bar-on'); else barShow(true); }, 4000);
  };
  sv.addEventListener('mousemove', e => {
    if (!isFull() || !mouse()) return;
    const r = sv.getBoundingClientRect(), near = sv.classList.contains('sv-rot') ? r.right - e.clientX < 90 : r.bottom - e.clientY < 90;
    if (near || e.target.closest('.sv-bar')) barShow(true); else if (sv.classList.contains('bar-on')) { clearTimeout(barT); barT = setTimeout(() => sv.classList.remove('bar-on'), 700); }
  });
  sv.addEventListener('mouseleave', () => { if (isFull()) { clearTimeout(barT); sv.classList.remove('bar-on'); } });
  sv.addEventListener('focusin', e => { if (isFull() && e.target.closest('.sv-bar')) barShow(true); });
  document.addEventListener('fullscreenchange', () => { sv.classList.remove('bar-on'); });
  autoBtn.onclick = () => {
    if (!timer && V.on) vStop();
    if (timer) { clearInterval(timer); timer = null; autoBtn.setAttribute('aria-pressed', 'false'); autoBtn.innerHTML = '▶ 자동<span class="lg"> 넘김</span>'; return; }
    autoBtn.setAttribute('aria-pressed', 'true'); autoBtn.textContent = '❚❚ 멈춤';
    timer = setInterval(() => { if (cur >= pages.length && endCard) loadNext(); else if (cur >= last()) autoBtn.onclick(); else go(cur + 1); }, 6000);
  };
  // ── 그림 보기의 '읽어 주기': 쪽마다 글을 소리 내어 읽고 다 읽으면 다음 그림으로 넘어감.
  //    전체 화면에서도 그대로, 이야기 끝에서는 다음 이야기로 이어서 읽음 (운영자 요청, 2026-11-22)
  //    목소리·빠르기 등은 '글과 함께 보기'의 듣기 설정(sb-tts)을 그대로 씀
  const sayBtn = sv.querySelector('.sv-say');
  const V = { on: false, i: -1, q: [], data: null, key: '', self: false, lock: null, title: false };
  const vToast = m => { const t = document.createElement('div'); t.className = 'sv-toast'; t.textContent = m; sv.append(t); setTimeout(() => t.remove(), 4000); };
  const vBtn = () => { if (!sayBtn) return; sayBtn.setAttribute('aria-pressed', V.on ? 'true' : 'false'); sayBtn.innerHTML = V.on ? '❚❚ 멈춤' : '🔊 읽어<span class="lg"> 주기</span>'; };
  const vStop = m => {
    V.on = false; V.q = []; V.i = -1; clearTimeout(V.t); try { speechSynthesis.cancel(); } catch (e) {}
    try { V.lock?.release(); } catch (e) {} V.lock = null; vBtn(); if (m) vToast(m);
  };
  const vLoad = async () => {
    if (V.key === sv.dataset.key && V.data) return true;
    try { V.data = await (await fetch('/t/' + sv.dataset.key + '.json')).json(); V.key = sv.dataset.key; return true; } catch (e) { V.data = null; return false; }
  };
  const vEn = () => /-en$/.test(sv.dataset.key || '');
  const vPage = i => {
    if (!V.on) return;
    clearTimeout(V.t); try { speechSynthesis.cancel(); } catch (e) {}
    if (i >= pages.length) {
      if (endCard && sv.dataset.next) { V.self = true; go(pages.length); V.self = false; V.t = setTimeout(() => V.on && loadNext(), 1500); }
      else vStop('이야기를 다 읽었습니다.');
      return;
    }
    V.i = i;
    if (cur !== i) { V.self = true; go(i); V.self = false; }
    const raw = (V.data?.[i] || []).flatMap(t => String(t).split(/\n\s*\n/));
    V.q = (vEn() ? raw.map(t => t.replace(/\s+/g, ' ').trim()) : raw.map(sayable)).filter(Boolean)
      .flatMap(t => t.match(/[^.!?。]+[.!?。]*\s*/g) || [t]).map(x => x.trim()).filter(Boolean);
    // 이야기 처음부터 읽을 때는 제목을 먼저 읽음 — 앞 번호는 '제N화', '—'는 쉼 (운영자 요청, 2026-11-22)
    if (i === 0 && V.title) {
      V.title = false;
      const t0 = String(sv.dataset.title || '').replace(/^0*(\d+)\s+/, vEn() ? 'Story $1. ' : '제$1화. ').replace(/\s*[—–]\s*/g, '. ');
      const say0 = vEn() ? t0 : sayable(t0);
      if (say0) V.q.unshift(say0);
    }
    if (!V.q.length) { V.t = setTimeout(() => V.on && vPage(i + 1), 3000); return; }  // 글 없는 그림은 3초 보여 주고 넘어감
    vNext(i);
  };
  const vNext = i => {
    if (!V.on || V.i !== i) return;
    if (!V.q.length) { V.t = setTimeout(() => V.on && V.i === i && vPage(i + 1), Math.max(0.7, topt().gap) * 1000); return; }
    const u = new SpeechSynthesisUtterance(V.q.shift()), o = topt();
    u.rate = o.rate; u.pitch = o.pitch; u.volume = o.vol;
    if (vEn()) { u.lang = 'en-US'; const ev = speechSynthesis.getVoices().filter(v => /^en/i.test(v.lang)); const v = ev.find(v => /google|natural|neural|online/i.test(v.name)) || ev[0]; if (v) u.voice = v; }
    else { u.lang = 'ko-KR'; const v = koVoice(); if (v) u.voice = v; }
    u.onend = () => vNext(i);
    u.onerror = e => { if (e.error !== 'interrupted' && e.error !== 'canceled') vNext(i); };
    speechSynthesis.speak(u);
  };
  if (sayBtn) sayBtn.onclick = async () => {
    if (V.on) { vStop(); return; }
    if (!('speechSynthesis' in window)) { vToast('이 브라우저에서는 읽어 주기를 쓸 수 없습니다. 크롬·삼성 인터넷·사파리로 열어 주세요.'); return; }
    if (timer) autoBtn.onclick();
    if (!await vLoad()) { vToast('이 이야기에는 읽어 줄 글이 없습니다.'); return; }
    V.on = true; vBtn();
    try { navigator.wakeLock?.request('screen').then(l => { V.lock = l; }).catch(() => {}); } catch (e) {}
    const s0 = cur >= pages.length ? 0 : Math.max(0, cur); V.title = s0 === 0; vPage(s0);
    setTimeout(() => { if (V.on && !vEn() && !speechSynthesis.speaking && !speechSynthesis.pending && !koVoice()) vToast('이 기기에 한국어 음성이 없어 소리가 나지 않을 수 있습니다. 기기 설정의 ‘텍스트 음성 변환(TTS)’에서 한국어 음성을 받아 주세요.'); }, 2500);
  };
  addEventListener('pagehide', () => vStop());
  // ── 글로 보기: 그림 아래에 그 그림의 글을 큰 글씨로, 세로로 넘겨 읽기 (운영자 요청, 2026-11-15)
  //    글자 크기 5단계(가− 가+)와 보기 방식은 이 기기에 기억함
  const SIZES = [16, 18, 21, 24, 28];
  const txtBtn = sv.querySelector('.sv-txt');
  let tbox = null, tobs = null;
  const tsize = () => { const v = +ls('sb-tsize'); return SIZES.includes(v) ? v : 21; };
  const textOff = () => {
    sayStop(); tmsg('');
    document.body.classList.remove('sb-text'); ls('sb-textmode', null);
    if (tobs) tobs.disconnect(); if (tbox) tbox.remove(); tbox = null;
    const i = cur; requestAnimationFrame(() => { go(i, false); sv.scrollIntoView({ block: 'start' }); });
  };
  // 그림 속 줄 바꿈은 상자 너비에 맞춘 것이라, 글로 볼 때는 이어 붙임 (제목·목록·게송 줄은 그대로)
  const tjoin = t => {
    const L = String(t).split('\n'); let out = '';
    L.forEach((l, i) => {
      if (!i) { out = h(l); return; }
      const prev = L[i - 1].trim(), cur = l.trim();
      const keep = !prev || !cur || /[:：]$/.test(prev) || /^([0-9]+[.)]|[•·①-⑩\-–]|\()/.test(cur) || /^“/.test(cur) && /[.!?”]$/.test(prev)
        || (i === 1 && prev.length <= 22 && !/[.!?,”]$/.test(prev)) || /^[A-Za-zĀ-ỿ ,;'’.!?-]+$/.test(prev);
      out += (keep ? '<br>' : ' ') + h(l);
    });
    return out;
  };

  // ── 글과 함께 보기의 '듣기': 쪽마다 글을 소리 내어 읽고 다음 쪽으로 넘어감 (운영자 요청, 2026-11-15)
  //    로마자 빠알리어는 도서관 '듣기'와 같은 음역 규칙으로 한글 소리로 읽음 (한글 뒤 괄호 속 원어는 건너뜀)
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
  const PMARK = /[āīūṭḍṇṅñṃṁḷĀĪŪṬḌṆṄÑṂṀḶ]/;
  const sayWord = w => { const parts = w.split('-').map(x => PALI(x.replace(/[^A-Za-zĀ-ỿ]/g, ''))); return parts.every(Boolean) ? parts.join(' ') : ''; };
  const sayable = t => String(t)
    .replace(/([가-힣])\s*\(([^()가-힣]*[A-Za-zĀ-ỿ][^()가-힣]*)\)/g, '$1')        // 한글(원어) → 한글만
    .replace(/[A-Za-zĀ-ỿ][A-Za-zĀ-ỿ'’-]*/g, w => (PMARK.test(w) || /^[a-z]/.test(w) || /^[A-Z][a-zā-ṁ]+$/.test(w)) ? sayWord(w.replace(/[’']/g, '')) : '')  // 로마자 빠알리 → 한글 소리, 읽을 수 없는 말은 건너뜀
    .replace(/[→➔•·~*]/g, ' ').replace(/[“”‘’"']/g, '').replace(/\(\s*\)/g, '').replace(/\s+/g, ' ').trim();
  // 듣기 설정 (목소리·빠르기·높낮이·소리 크기·쪽 사이 쉬기·따라가기) — 이 기기에 기억 (운영자 요청, 2026-11-15)
  const TDEF = { voice: '', rate: 1, pitch: 1, vol: 1, gap: 0.7, follow: true };
  const topt = () => { let o = {}; try { o = JSON.parse(ls('sb-tts') || '{}') || {}; } catch (e) {} const sp = +ls('sb-tspeed'); if (o.rate == null && sp) o.rate = sp; return { ...TDEF, ...o }; };
  const tset = o => ls('sb-tts', JSON.stringify(o));
  const T = { on: false, i: 0, q: [], lock: null };
  const koVoices = () => ('speechSynthesis' in window ? speechSynthesis.getVoices() : []).filter(v => /^ko/i.test(v.lang));
  const koVoice = () => { const vs = koVoices(), want = topt().voice; return vs.find(v => v.voiceURI === want) || vs.find(v => /google|natural|neural|online/i.test(v.name)) || vs[0] || null; };
  const tmsg = m => { const e = tbox?.querySelector('.st-msg'); if (e) { e.textContent = m || ''; e.hidden = !m; } };
  const tbtn = () => { const b = tbox?.querySelector('.st-say'); if (b) { b.textContent = T.on ? '❚❚ 멈춤' : '🔊 듣기'; b.setAttribute('aria-pressed', T.on ? 'true' : 'false'); } };
  const tmark = i => tbox?.querySelectorAll('.st-page').forEach(f => f.classList.toggle('st-now', T.on && +f.dataset.i === i));
  const sayStop = () => {
    T.on = false; T.q = []; try { speechSynthesis.cancel(); } catch (e) {}
    try { T.lock?.release(); } catch (e) {} T.lock = null; tbtn(); tmark(-1);
  };
  const sayPage = i => {
    if (!T.on || !tbox) return;
    if (i >= pages.length) { sayStop(); tmsg(sv.dataset.next ? '이 이야기를 다 들었습니다. 아래의 ‘다음 이야기’를 누르면 이어서 볼 수 있습니다.' : '이 이야기를 다 들었습니다.'); return; }
    T.i = i; tmark(i); show(i);
    const f = tbox.querySelector(`.st-page[data-i="${i}"]`); if (topt().follow) f?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    // 긴 글은 문장마다 나눠 읽음 (긴 글 하나로 읽으면 크롬이 중간에 멈추는 일이 있음)
    T.q = (T.data[i] || []).flatMap(t => String(t).split(/\n\s*\n/)).map(sayable).filter(Boolean).flatMap(t => t.match(/[^.!?。]+[.!?。]*\s*/g) || [t]).map(x => x.trim()).filter(Boolean);
    sayNext();
  };
  const sayNext = () => {
    if (!T.on) return;
    if (!T.q.length) { setTimeout(() => T.on && sayPage(T.i + 1), topt().gap * 1000); return; }
    const u = new SpeechSynthesisUtterance(T.q.shift());
    const o = topt(); u.lang = 'ko-KR'; u.rate = o.rate; u.pitch = o.pitch; u.volume = o.vol; const v = koVoice(); if (v) u.voice = v;
    u.onend = () => sayNext();
    u.onerror = e => { if (e.error !== 'interrupted' && e.error !== 'canceled') sayNext(); };
    speechSynthesis.speak(u);
  };
  const sayStart = i => {
    if (!('speechSynthesis' in window)) { tmsg('이 브라우저에서는 듣기를 쓸 수 없습니다. 카카오톡 등 앱 안에서 여셨다면 크롬·삼성 인터넷·사파리로 열어 주세요.'); return; }
    sayStop(); tmsg(''); T.on = true; tbtn();
    try { navigator.wakeLock?.request('screen').then(l => { T.lock = l; }).catch(() => {}); } catch (e) {}
    sayPage(Math.max(0, Math.min(pages.length - 1, i)));
    setTimeout(() => { if (T.on && !speechSynthesis.speaking && !speechSynthesis.pending && !koVoice()) tmsg('이 기기에 한국어 음성이 없어 소리가 나지 않을 수 있습니다. 기기 설정의 ‘텍스트 음성 변환(TTS)’에서 한국어 음성을 받아 주세요.'); }, 2500);
  };
  addEventListener('pagehide', sayStop);
  const textOn = async () => {
    let data;
    try { data = await (await fetch('/t/' + sv.dataset.key + '.json')).json(); } catch (e) { return; }
    if (timer) autoBtn.onclick();
    if (V.on) vStop();
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    sv.classList.remove('sv-max', 'sv-rot');
    sayStop();
    tbox?.remove();
    tbox = document.createElement('section'); tbox.className = 'sv-text'; tbox.style.setProperty('--tsz', tsize() + 'px');
    const imgs = pages.map(p => p.querySelector('img'));
    tbox.innerHTML = `<div class="st-bar"><button type="button" class="st-pic">🖼 그림으로<span class="lg"> 보기</span></button><span class="st-say-w"><button type="button" class="st-say" aria-pressed="false" title="글을 소리 내어 읽어 줍니다">🔊 듣기</button><button type="button" class="st-set" aria-expanded="false" title="목소리·빠르기·높낮이 등">⚙<span class="lg"> 듣기</span> 설정</button></span><span class="st-sz"><button type="button" class="st-m" aria-label="글자 작게">가−</button><button type="button" class="st-p" aria-label="글자 크게">가+</button></span><div class="st-panel" hidden></div></div><p class="st-msg" hidden></p>` +
      pages.map((p, i) => `<figure class="st-page" data-i="${i}"><img src="${h(imgs[i]?.dataset.s || imgs[i]?.src)}" data-big="${h(imgs[i]?.dataset.big || '')}" alt="${i + 1}쪽" loading="lazy"><figcaption><span class="st-n">${i + 1} / ${pages.length}<button type="button" class="st-here" data-i="${i}" title="이 쪽부터 듣기">🔊 여기부터 듣기</button></span>${(data[i] || []).map(t => `<p>${tjoin(t)}</p>`).join('')}</figcaption></figure>`).join('') +
      (sv.dataset.next ? `<p class="st-next"><a class="btn" href="${h(sv.dataset.next)}">다음 이야기 ▶ ${h(sv.dataset.nextTitle || '')}</a></p>` : '');
    sv.after(tbox);
    document.body.classList.add('sb-text'); ls('sb-textmode', '1');
    tbox.querySelector('.st-pic').onclick = textOff;
    T.data = data;
    tbox.querySelector('.st-say').onclick = () => {
      if (T.on) return sayStop();
      // 화면에 글이 보이는 첫 쪽부터 (맨 위로 올려 둔 경우 1쪽부터)
      const top = (tbox.querySelector('.st-bar')?.getBoundingClientRect().bottom || 0) + 40;
      const f = [...tbox.querySelectorAll('.st-page')].find(x => x.querySelector('figcaption').getBoundingClientRect().bottom > top);
      sayStart(f ? +f.dataset.i : 0);
    };
    const panel = tbox.querySelector('.st-panel'), setBtn = tbox.querySelector('.st-set');
    setBtn.onclick = () => { const open = panel.hidden; panel.hidden = !open; setBtn.setAttribute('aria-expanded', open); if (open) drawPanel(); };
    const drawPanel = () => {
      const o = topt(), vs = koVoices();
      const rng = (k, label, min, max, step, fmt) => `<label class="sp-row"><span>${label}</span><input type="range" data-k="${k}" min="${min}" max="${max}" step="${step}" value="${o[k]}"><b data-v="${k}">${fmt(o[k])}</b></label>`;
      const F = { rate: v => (+v).toFixed(1) + '배', pitch: v => +v === 1 ? '보통' : (+v < 1 ? '낮게 ' : '높게 ') + (+v).toFixed(1), vol: v => Math.round(v * 100) + '%', gap: v => (+v).toFixed(1) + '초' };
      panel.innerHTML = `<label class="sp-row"><span>목소리</span><select data-k="voice">${vs.length ? `<option value="">자동으로 고르기</option>` + vs.map(v => `<option value="${h(v.voiceURI)}"${v.voiceURI === o.voice ? ' selected' : ''}>${h(v.name.replace(/^(Microsoft|Google)\s*/, '$1 '))}${v.localService ? '' : ' (인터넷)'}</option>`).join('') : '<option value="">이 기기에 한국어 음성이 없습니다</option>'}</select></label>` +
        rng('rate', '빠르기', 0.5, 2, 0.1, F.rate) + rng('pitch', '높낮이', 0.5, 1.5, 0.1, F.pitch) + rng('vol', '소리 크기', 0.1, 1, 0.1, F.vol) + rng('gap', '쪽 사이 쉬기', 0, 3, 0.5, F.gap) +
        `<label class="sp-row sp-chk"><input type="checkbox" data-k="follow"${o.follow ? ' checked' : ''}><span>읽는 쪽으로 화면 따라가기</span></label>` +
        `<div class="sp-btns"><button type="button" class="sp-try">▶ 미리 듣기</button><button type="button" class="sp-reset">처음 설정으로</button><button type="button" class="sp-close">닫기</button></div>` +
        `<p class="sp-note">목소리는 이 기기(휴대폰·컴퓨터)에 들어 있는 한국어 음성 가운데서 고릅니다. 기기마다 고를 수 있는 목소리가 다릅니다. 설정은 이 기기에 기억됩니다.</p>`;
      panel.querySelectorAll('[data-k]').forEach(el => el.oninput = el.onchange = () => {
        const o = topt(), k = el.dataset.k; o[k] = el.type === 'checkbox' ? el.checked : el.tagName === 'SELECT' ? el.value : +el.value; tset(o);
        const b = panel.querySelector(`[data-v="${k}"]`); if (b) b.textContent = F[k](o[k]);
      });
      panel.querySelector('.sp-try').onclick = () => {
        if (!('speechSynthesis' in window)) return tmsg('이 브라우저에서는 듣기를 쓸 수 없습니다.');
        const was = T.on; if (was) sayStop();
        speechSynthesis.cancel(); const o = topt(), u = new SpeechSynthesisUtterance('안녕하세요. 붓다담마 그림책을 읽어 드리겠습니다.');
        u.lang = 'ko-KR'; u.rate = o.rate; u.pitch = o.pitch; u.volume = o.vol; const v = koVoice(); if (v) u.voice = v; speechSynthesis.speak(u);
      };
      panel.querySelector('.sp-reset').onclick = () => { tset({ ...TDEF }); drawPanel(); };
      panel.querySelector('.sp-close').onclick = () => setBtn.onclick();
    };
    document.addEventListener('click', e => { if (!panel.hidden && !e.target.closest('.st-panel, .st-set')) setBtn.onclick(); });  // 바깥을 누르면 닫힘
    if ('speechSynthesis' in window) speechSynthesis.addEventListener?.('voiceschanged', () => { if (!panel.hidden) drawPanel(); });
    tbox.querySelectorAll('.st-here').forEach(b => b.onclick = () => sayStart(+b.dataset.i));
    const setSz = d => { const i = Math.max(0, Math.min(SIZES.length - 1, SIZES.indexOf(tsize()) + d)); ls('sb-tsize', String(SIZES[i])); tbox.style.setProperty('--tsz', SIZES[i] + 'px'); };
    tbox.querySelector('.st-m').onclick = () => setSz(-1); tbox.querySelector('.st-p').onclick = () => setSz(1);
    tbox.querySelectorAll('.st-page img').forEach(im => im.onclick = () => { if (im.dataset.big && im.src !== im.dataset.big) im.src = im.dataset.big; im.classList.toggle('big'); });
    // 읽는 자리 기억 (내 서재·이어 읽기)
    tobs = new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting) show(+e.target.dataset.i); }, { rootMargin: '-40% 0px -55% 0px' });
    tbox.querySelectorAll('.st-page').forEach(f => tobs.observe(f));
    const start = Math.max(0, Math.min(Math.max(cur, +(ls(KEY) || 0)), pages.length - 1));
    (start ? tbox.querySelector(`.st-page[data-i="${start}"]`) : tbox).scrollIntoView({ block: 'start' });
  };
  if (txtBtn) {
    txtBtn.onclick = e => { e.stopPropagation(); textOn(); };
    if (ls('sb-textmode') === '1') requestAnimationFrame(textOn);
  }
  // 전체 화면: 휴대폰은 가로로 돌려 크게 (안드로이드는 화면을 가로로 고정, 아이폰은 화면을 꽉 채우고 돌려 달라고 안내)
  const fullBtn = sv.querySelector('.sv-full');
  // 휴대폰: 삼성 인터넷은 hover 를 다르게 알려 주는 일이 있어 기기 이름·손가락 화면으로도 봄
  const phone = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) || matchMedia('(pointer:coarse)').matches;
  if (phone) document.documentElement.classList.add('is-phone');
  const isMax = () => document.fullscreenElement === sv || sv.classList.contains('sv-max');
  let rotating = false;
  const within = (p, ms) => Promise.race([Promise.resolve(p).catch(() => {}), new Promise(r => setTimeout(r, ms))]);  // 브라우저가 대답을 안 해도 멈추지 않게
  const lockLand = async () => {
    try { if (screen.orientation?.lock) { await within(screen.orientation.lock('landscape'), 700); return true; } } catch (e) {}
    try { const l = screen.lockOrientation || screen.webkitLockOrientation; if (l) return l.call(screen, 'landscape'); } catch (e) {}
    return false;
  };
  const enter = async () => {
    // 크롬·삼성 인터넷 등: 전체 화면 + 가로 고정 (옛 삼성 인터넷은 webkit 이름으로)
    const req = sv.requestFullscreen || sv.webkitRequestFullscreen;
    if (req && (document.fullscreenEnabled || document.webkitFullscreenEnabled)) {
      try { await within(req.call(sv, { navigationUI: 'hide' }), 800); } catch (e) {}
      if (phone && document.fullscreenElement) await lockLand();
    }
    if (document.fullscreenElement !== sv) { sv.classList.add('sv-max'); document.documentElement.classList.add('sv-lock'); }
    sv.focus();
    // 휴대폰 자동 회전이 꺼져 있거나 가로 고정이 안 되는 브라우저(아이폰 등): 그림을 90도 돌려 가로로 보여 줌
    // (진짜 전체 화면 안에서는 돌릴 수 없어서, 전체 화면을 풀고 화면 채우기로 돌림)
    if (phone) setTimeout(async () => {
      if (innerHeight > innerWidth && isMax()) {
        if (document.fullscreenElement) { rotating = true; try { await within(document.exitFullscreen(), 600); } catch (e) {} setTimeout(() => rotating = false, 400); }
        sv.classList.add('sv-max', 'sv-rot'); document.documentElement.classList.add('sv-lock');
      }
      go(cur, false);
    }, 450);
    setTimeout(() => go(cur, false), 50);
  };
  const leave = () => {
    if (document.fullscreenElement) document.exitFullscreen();
    sv.classList.remove('sv-max', 'sv-rot'); document.documentElement.classList.remove('sv-lock'); setTimeout(() => go(cur, false), 50);
  };
  fullBtn.onclick = () => isMax() ? leave() : enter();
  document.addEventListener('fullscreenchange', () => { if (document.fullscreenElement === sv && phone && !sv.classList.contains('sv-max')) lockLand().then(() => setTimeout(() => { if (innerHeight <= innerWidth) sv.classList.remove('sv-rot'); go(cur, false); }, 300)); if (!document.fullscreenElement && !rotating && !sv.classList.contains('sv-max')) sv.classList.remove('sv-rot'); if (!document.fullscreenElement && screen.orientation?.unlock) try { screen.orientation.unlock(); } catch (e) {} setTimeout(() => go(cur, false), 50); });
  sv.addEventListener('keydown', e => { if (e.key === 'Escape' && sv.classList.contains('sv-max')) leave(); });
  if (phone) {
    // 세로로 들고 볼 때: 위에 '가로로 크게 보기' 안내 / 휴대폰을 가로로 돌리면 저절로 화면을 꽉 채움
    const tip = document.createElement('button');
    tip.type = 'button'; tip.className = 'sv-tip';
    tip.innerHTML = '📱 휴대폰을 <b>가로로</b> 돌리면 그림과 글이 크게 보입니다 <span>가로로 크게 보기 ›</span>';
    tip.onclick = enter;
    sv.before(tip);
    const land = matchMedia('(orientation: landscape)');
    const onRot = () => { if (land.matches) sv.classList.remove('sv-rot'); else if (isMax() && !sv.classList.contains('sv-rot') && !rotating) leave();
      if (land.matches && !isMax()) { sv.classList.add('sv-max'); document.documentElement.classList.add('sv-lock'); }  setTimeout(() => go(cur, false), 80); };
    land.addEventListener('change', onRot); onRot();
  }
  window.addEventListener('resize', () => go(cur, false));
  // 데이터 절약: 원본 화질 대신 800px 그림
  const saveBtn = sv.querySelector('.sv-save');
  const setSave = on => {
    saveBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    sv.querySelectorAll('.sv-page img').forEach(im => { const u = on ? im.dataset.s : im.dataset.big; if (im.getAttribute('src') !== u) im.src = u; });
    try { localStorage.setItem('sb-save', on ? '1' : ''); } catch (e) {}
  };
  saveBtn.onclick = () => setSave(saveBtn.getAttribute('aria-pressed') !== 'true');
  try { if (localStorage.getItem('sb-save')) setSave(true); } catch (e) {}
  setup();
  let start = 0;
  try { start = +localStorage.getItem(KEY) || 0; } catch (e) {}
  { const m = location.hash.match(/^#p(\d+)$/); if (m) { start = +m[1] - 1; history.replaceState(null, '', location.pathname + location.search); } }
  if (start > 0 && start < pages.length) requestAnimationFrame(() => go(start, false));
  show(start < pages.length ? start : 0);
})();
