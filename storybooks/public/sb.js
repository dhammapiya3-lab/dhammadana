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
  const pages = [...sv.querySelectorAll('.sv-page')];
  const count = sv.querySelector('.sv-count');
  const thumbs = [...document.querySelectorAll('.sv-thumbs button')];
  const autoBtn = sv.querySelector('.sv-auto');
  const KEY = 'sb-pos-' + sv.dataset.key;
  let cur = 0, timer = null;

  const go = (i, smooth = true) => {
    i = Math.max(0, Math.min(pages.length - 1, i));
    track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? 'smooth' : 'auto' });
  };
  const show = i => {
    cur = i;
    count.textContent = `${i + 1} / ${pages.length}`;
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
  });
  // 화면 좌우를 눌러 넘기기 (손가락 화면)
  track.addEventListener('click', e => {
    const r = track.getBoundingClientRect(), x = (e.clientX - r.left) / r.width;
    if (x < 0.25) go(cur - 1); else if (x > 0.75) go(cur + 1);
  });
  autoBtn.onclick = () => {
    if (timer) { clearInterval(timer); timer = null; autoBtn.setAttribute('aria-pressed', 'false'); autoBtn.innerHTML = '▶ 자동<span class="lg"> 넘김</span>'; return; }
    autoBtn.setAttribute('aria-pressed', 'true'); autoBtn.textContent = '❚❚ 멈춤';
    timer = setInterval(() => { if (cur >= pages.length - 1) autoBtn.onclick(); else go(cur + 1); }, 6000);
  };
  const fullBtn = sv.querySelector('.sv-full');
  if (!document.fullscreenEnabled) fullBtn.hidden = true;
  fullBtn.onclick = () => document.fullscreenElement ? document.exitFullscreen() : sv.requestFullscreen().then(() => sv.focus());
  document.addEventListener('fullscreenchange', () => setTimeout(() => go(cur, false), 50));
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
  let start = 0;
  try { start = +localStorage.getItem(KEY) || 0; } catch (e) {}
  if (start > 0 && start < pages.length) requestAnimationFrame(() => go(start, false));
  show(start < pages.length ? start : 0);
})();
