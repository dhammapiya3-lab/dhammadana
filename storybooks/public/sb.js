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
  const loadNext = async () => {
    const url = sv.dataset.next;
    if (!url || sv.classList.contains('loading')) return;
    sv.classList.add('loading');
    try {
      const doc = new DOMParser().parseFromString(await (await fetch(url)).text(), 'text/html');
      const nv = doc.getElementById('sv');
      if (!nv) { location.href = url; return; }
      track.innerHTML = nv.querySelector('.sv-track').innerHTML;
      for (const k of ['key', 'next', 'nextTitle']) { if (nv.dataset[k]) sv.dataset[k] = nv.dataset[k]; else delete sv.dataset[k]; }
      for (const sel of ['.story h1', '.sv-thumbs', '.story .prose', '.story .pn', '.story .orig']) {
        const a = document.querySelector(sel), b = doc.querySelector(sel);
        if (a && b) a.replaceWith(document.importNode(b, true));
      }
      document.title = doc.title;
      history.pushState({}, '', url);
      setup();
      if (saveBtn.getAttribute('aria-pressed') === 'true') setSave(true);
      track.scrollTo({ left: 0 }); cur = -1; show(0);
    } catch (e) { location.href = url; }
    sv.classList.remove('loading');
  };
  addEventListener('popstate', () => location.reload());

  const go = (i, smooth = true) => {
    i = Math.max(0, Math.min(last(), i));
    track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? 'smooth' : 'auto' });
  };
  const show = i => {
    cur = i;
    count.textContent = i >= pages.length ? '다음 이야기' : `${i + 1} / ${pages.length}`;
    thumbs.forEach((t, j) => t.classList.toggle('on', j === i));
    thumbs[i]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    try { localStorage.setItem(KEY, i); } catch (e) {}
  };
  track.addEventListener('scroll', () => {
    const i = Math.round(track.scrollLeft / track.clientWidth);
    if (i !== cur) show(i);
  }, { passive: true });
  sv.querySelector('.prev').onclick = () => go(cur - 1);
  sv.querySelector('.next').onclick = () => go(cur + 1);
  thumbs.forEach(t => t.onclick = () => go(+t.dataset.i));
  sv.addEventListener('keydown', e => {
    if (['ArrowRight', 'k', ' ', 'PageDown'].includes(e.key)) { go(cur + 1); e.preventDefault(); }
    if (['ArrowLeft', 'j', 'PageUp'].includes(e.key)) { go(cur - 1); e.preventDefault(); }
    if (e.key === 'Home') go(0); if (e.key === 'End') go(pages.length - 1);
    if (e.key === 'Enter' && endCard && cur >= pages.length) loadNext();
  });
  let t0 = null;
  track.addEventListener('touchstart', e => { if (sv.classList.contains('sv-rot')) t0 = e.touches[0]; }, { passive: true });
  track.addEventListener('touchend', e => {
    if (!t0 || !sv.classList.contains('sv-rot')) return;
    const t = e.changedTouches[0], dy = t.clientY - t0.clientY, dx = t.clientX - t0.clientX; t0 = null;
    if (Math.abs(dy) > 40 && Math.abs(dy) > Math.abs(dx)) go(cur + (dy < 0 ? 1 : -1));
  }, { passive: true });
  // 화면 좌우를 눌러 넘기기 (손가락 화면)
  track.addEventListener('click', e => {
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
  const phone = matchMedia('(hover:none) and (pointer:coarse)').matches;
  const isMax = () => document.fullscreenElement === sv || sv.classList.contains('sv-max');
  const lockLand = async () => {
    try { if (screen.orientation?.lock) { await screen.orientation.lock('landscape'); return true; } } catch (e) {}
    try { const l = screen.lockOrientation || screen.webkitLockOrientation; if (l) return l.call(screen, 'landscape'); } catch (e) {}
    return false;
  };
  const enter = async () => {
    // 크롬·삼성 인터넷 등: 전체 화면 + 가로 고정 (옛 삼성 인터넷은 webkit 이름으로)
    const req = sv.requestFullscreen || sv.webkitRequestFullscreen;
    if (req && (document.fullscreenEnabled || document.webkitFullscreenEnabled)) {
      try { await req.call(sv, { navigationUI: 'hide' }); } catch (e) {}
      if (phone) await lockLand();
    }
    if (document.fullscreenElement !== sv) { sv.classList.add('sv-max'); document.documentElement.classList.add('sv-lock'); }
    sv.focus();
    // 휴대폰 자동 회전이 꺼져 있거나 가로 고정이 안 되는 브라우저(아이폰 등): 그림을 90도 돌려 가로로 보여 줌
    if (phone) setTimeout(() => { if (innerHeight > innerWidth && isMax()) sv.classList.add('sv-rot'); go(cur, false); }, 450);
    setTimeout(() => go(cur, false), 50);
  };
  const leave = () => {
    if (document.fullscreenElement) document.exitFullscreen();
    sv.classList.remove('sv-max', 'sv-rot'); document.documentElement.classList.remove('sv-lock'); setTimeout(() => go(cur, false), 50);
  };
  fullBtn.onclick = () => isMax() ? leave() : enter();
  document.addEventListener('fullscreenchange', () => { if (document.fullscreenElement === sv && phone) lockLand().then(() => setTimeout(() => { if (innerHeight <= innerWidth) sv.classList.remove('sv-rot'); go(cur, false); }, 300)); if (!document.fullscreenElement) sv.classList.remove('sv-rot'); if (!document.fullscreenElement && screen.orientation?.unlock) try { screen.orientation.unlock(); } catch (e) {} setTimeout(() => go(cur, false), 50); });
  sv.addEventListener('keydown', e => { if (e.key === 'Escape' && sv.classList.contains('sv-max')) leave(); });
  if (phone) {
    // 세로로 들고 볼 때: 위에 '가로로 크게 보기' 안내 / 휴대폰을 가로로 돌리면 저절로 화면을 꽉 채움
    const tip = document.createElement('button');
    tip.type = 'button'; tip.className = 'sv-tip';
    tip.innerHTML = '📱 휴대폰을 <b>가로로</b> 돌리면 그림과 글이 크게 보입니다 <span>가로로 크게 보기 ›</span>';
    tip.onclick = enter;
    sv.before(tip);
    const land = matchMedia('(orientation: landscape)');
    const onRot = () => { if (land.matches) sv.classList.remove('sv-rot'); else if (isMax() && !sv.classList.contains('sv-rot')) sv.classList.add('sv-rot');
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
