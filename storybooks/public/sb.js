// 붓다담마 그림책 — 목록 찾기 · 그림책 뷰어
(() => {
  // 첫 화면: 제목·주제로 찾기
  const q = document.getElementById('q');
  if (q) {
    const cards = [...document.querySelectorAll('.bcard')];
    const run = () => {
      const v = q.value.trim().toLowerCase();
      let any = false;
      cards.forEach(c => { const on = !v || c.dataset.q.includes(v); c.hidden = !on; any ||= on; });
      document.querySelectorAll('.cat, .tier').forEach(s => { s.hidden = ![...s.querySelectorAll('.bcard')].some(c => !c.hidden); });
      document.getElementById('noRes').hidden = any;
    };
    q.addEventListener('input', run);
    document.getElementById('qReset').onclick = () => { q.value = ''; run(); q.focus(); };
  }

  // 내 서재 화면 · 책 화면의 '이어 읽기'
  const shelfAll = () => { try { return JSON.parse(localStorage.getItem('sb-shelf') || '{}'); } catch (e) { return {}; } };
  const h = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const shelfEl = document.getElementById('shelf');
  if (shelfEl) {
    const draw = () => {
      const all = shelfAll(), list = Object.entries(all).sort((a, b) => b[1].t - a[1].t);
      document.getElementById('shelfEmpty').hidden = list.length > 0;
      shelfEl.innerHTML = list.map(([slug, r]) => `<div class="sh-item">
        <a class="sh-cover" href="/${h(slug)}/"><img src="${h(r.cover)}" alt="" loading="lazy" onerror="this.remove()"></a>
        <div class="sh-meta"><h2><a href="/${h(slug)}/">${h(r.book)}</a></h2>
        <p>읽던 이야기: <b>${h(r.story)}</b> · ${r.page} / ${r.n}쪽</p>
        <p class="muted">${new Date(r.t).toLocaleDateString('ko-KR')}에 읽음</p>
        <p class="sh-act"><a class="btn" href="${h(r.url)}">▶ 이어 읽기</a> <button type="button" data-del="${h(slug)}">목록에서 빼기</button></p></div></div>`).join('');
      shelfEl.querySelectorAll('[data-del]').forEach(b => b.onclick = () => {
        const a = shelfAll(); delete a[b.dataset.del];
        try { localStorage.setItem('sb-shelf', JSON.stringify(a)); } catch (e) {}
        draw();
      });
    };
    draw();
  }
  const resume = document.getElementById('resume');
  if (resume) {
    const r = shelfAll()[resume.dataset.slug];
    if (r) { resume.hidden = false; resume.className = 'resume'; resume.innerHTML = `<span>읽던 곳: <b>${h(r.story)}</b> · ${r.page} / ${r.n}쪽</span><a class="btn" href="${h(r.url)}">▶ 이어 읽기</a>`; }
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
      for (const sel of ['.story h1', '.sv-thumbs', '.story .prose', '.story .pn', '.story .orig']) {
        const a = document.querySelector(sel), b = doc.querySelector(sel);
        if (a && b) a.replaceWith(document.importNode(b, true));
      }
      document.title = doc.title;
      history.pushState({}, '', url);
      setup();
      if (saveBtn.getAttribute('aria-pressed') === 'true') setSave(true);
      cur = -1;
      if (back) requestAnimationFrame(() => go(pages.length - 1, false)); else { track.scrollTo({ left: 0 }); show(0); }
    } catch (e) { location.href = url; }
    sv.classList.remove('loading');
  };
  addEventListener('popstate', () => location.reload());

  const go = (i, smooth = true) => {
    if (endCard && i > pages.length && cur >= pages.length) { loadNext(); return; }  // 끝 화면에서 › → 다음 이야기
    if (i < 0 && cur <= 0 && sv.dataset.prev) { loadNext(true); return; }  // 첫 그림에서 ‹ → 이전 이야기의 마지막 그림
    i = Math.max(0, Math.min(last(), i));
    track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? 'smooth' : 'auto' });
  };
  const show = i => {
    if (i !== cur) zReset();
    cur = i;
    count.textContent = i >= pages.length ? '다음 이야기' : `${i + 1} / ${pages.length}`;
    thumbs.forEach((t, j) => t.classList.toggle('on', j === i));
    thumbs[i]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    try { localStorage.setItem(KEY, i); } catch (e) {}
    if (i < pages.length) shelfSave(i);
  };
  // 내 서재: 책마다 마지막으로 읽던 이야기와 쪽 (운영자 요청, 2026-11-14)
  const shelfSave = i => {
    const d = sv.dataset; if (!d.book) return;
    try {
      const all = JSON.parse(localStorage.getItem('sb-shelf') || '{}');
      all[d.book] = { book: d.bookTitle, cover: d.cover, story: d.title, url: '/' + d.key + '/', page: i + 1, n: pages.length, t: Date.now() };
      localStorage.setItem('sb-shelf', JSON.stringify(all));
    } catch (e) {}
  };
  track.addEventListener('scroll', () => {
    const i = Math.round(track.scrollLeft / track.clientWidth);
    if (i !== cur) show(i);
  }, { passive: true });
  sv.querySelector('.prev').onclick = () => go(cur - 1);
  sv.querySelector('.next').onclick = () => go(cur + 1);
  sv.addEventListener('keydown', e => {
    if (['ArrowRight', 'k', ' ', 'PageDown'].includes(e.key)) { go(cur + 1); e.preventDefault(); }
    if (['ArrowLeft', 'j', 'PageUp'].includes(e.key)) { go(cur - 1); e.preventDefault(); }
    if (e.key === 'Home') go(0); if (e.key === 'End') go(pages.length - 1);
    if (e.key === 'Enter' && endCard && cur >= pages.length) loadNext();
  });
  // ── 손가락 두 개로 벌려 확대 (전체 화면), 확대한 채 한 손가락으로 끌어 옮기기, 두 번 톡톡 = 2배/원래대로
  const Z = { s: 1, x: 0, y: 0, img: null, pinch: null, pan: null, tap: 0, moved: false };
  const zApply = () => {
    if (!Z.img) return;
    Z.img.style.transform = Z.s > 1 ? `translate(${Z.x}px,${Z.y}px) scale(${Z.s})` : '';
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
      if (!Z.moved && zoomable() && now - Z.tap < 300) {
        const img = pages[cur]?.querySelector('img');
        if (Z.s > 1) zReset(); else if (img) { zReset(); Z.img = img; Z.s = 2; zApply(); }
        Z.tap = 0; Z.dbl = now;
      } else Z.tap = now;
    }
  }, { passive: true });
  let t0 = null;
  track.addEventListener('touchstart', e => { if (sv.classList.contains('sv-rot') && e.touches.length === 1 && Z.s <= 1) t0 = e.touches[0]; else t0 = null; }, { passive: true });
  track.addEventListener('touchend', e => {
    if (!t0 || !sv.classList.contains('sv-rot') || Z.s > 1 || Z.moved) { t0 = null; return; }
    const t = e.changedTouches[0], dy = t.clientY - t0.clientY, dx = t.clientX - t0.clientX; t0 = null;
    if (Math.abs(dy) > 40 && Math.abs(dy) > Math.abs(dx)) go(cur + (dy < 0 ? 1 : -1));
  }, { passive: true });
  // 화면 좌우를 눌러 넘기기 (손가락 화면)
  track.addEventListener('click', e => {
    if (Z.s > 1 || Date.now() - (Z.dbl || 0) < 400) return;  // 확대 중이거나 두 번 톡톡 직후에는 넘기지 않음
    const r = track.getBoundingClientRect(), x = sv.classList.contains('sv-rot') ? (e.clientY - r.top) / r.height : (e.clientX - r.left) / r.width;
    if (x < 0.25) go(cur - 1); else if (x > 0.75) go(cur + 1);
  });
  autoBtn.onclick = () => {
    if (timer) { clearInterval(timer); timer = null; autoBtn.setAttribute('aria-pressed', 'false'); autoBtn.innerHTML = '▶ 자동<span class="lg"> 넘김</span>'; return; }
    autoBtn.setAttribute('aria-pressed', 'true'); autoBtn.textContent = '❚❚ 멈춤';
    timer = setInterval(() => { if (cur >= pages.length && endCard) loadNext(); else if (cur >= last()) autoBtn.onclick(); else go(cur + 1); }, 6000);
  };
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
  if (start > 0 && start < pages.length) requestAnimationFrame(() => go(start, false));
  show(start < pages.length ? start : 0);
})();
