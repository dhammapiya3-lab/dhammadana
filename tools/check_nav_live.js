// 실제 사이트(dhammadana.kr)에서 아래 바 › 검사 — 운영자 크롬의 읽기 화면(예: https://dhammadana.kr/read/DL-0017/1)에서 실행
// 실제 사이트에서만 생기는 일(한글 글꼴 조각이 늦게 받아져 글이 밀림 등)은 로컬 check_nav.py 로 잡히지 않으므로 이것으로 확인한다.
// 쓰는 법(Claude in Chrome 의 javascript 실행):
//   1) 시작 전 읽던 쪽 백업: dd-pos-* · dd-hist 를 sessionStorage 'dd-qa-backup' 에 저장 (검사가 끝나면 되돌림)
//   2) 책마다: 읽기 화면을 열고 이 파일의 __qa 를 넣은 뒤  __qa(500, 900).then(r => window.__qaRes = r)  — 한 번 실행이 45초를 넘으면 안 되므로 기다리지 않고 돌려 두고 window.__qaRes 를 나중에 읽음
//   3) bad 목록이 비어 있어야 통과: '멈춘 곳이 소제목 아님'·'같은 소제목 두 번'·'이미 보이던 소제목'
window.__qa = async (n, wait = 900) => {
  const b = document.querySelector('#rBody'), R0 = document.querySelector('#reader'); const bad = []; let prev = null, prevSeen = [], steps = 0;
  const isHead = x => x.tagName === 'P' && (x.classList.contains('sub-h') || (x.children.length === 1 && x.firstElementChild.tagName === 'STRONG' && x.firstElementChild.textContent.trim() === x.textContent.trim()));
  for (let i = 0; i < n; i++) {
    const nx = document.querySelector('#rNext'); if (!nx || nx.disabled) return { done: true, bad, steps };
    const rg = document.querySelector('#rRange'); if (+rg.value >= +rg.max && prev && prev.end) return { done: true, bad, steps };
    R0.classList.remove('chrome-off'); nx.click(); steps++;
    await new Promise(r => setTimeout(r, wait));
    const rt = document.querySelector('.r-top'); const top = b.getBoundingClientRect().top + rt.offsetHeight;
    const ch = (document.querySelector('.r-title small') || {}).textContent || '';
    const pg = document.querySelector('#rRange').value;
    if (b.scrollTop < 4) { prev = { k: 'chapter:' + ch }; prevSeen = []; continue; }
    const end = b.scrollTop >= b.scrollHeight - b.clientHeight - 2;
    const els = [...b.querySelectorAll('p,figure,.pmark,.r-toc')].filter(e => { const r = e.getBoundingClientRect(); return r.height > 0 && r.bottom > top + 12; });
    const e = els.find(x => isHead(x) && x.getBoundingClientRect().top < top + 40) || els[0];
    const t = e ? e.textContent.trim().slice(0, 40) : '';
    const seen = els.filter(x => isHead(x) && x.getBoundingClientRect().top < top + (b.getBoundingClientRect().bottom - top) * 0.3).map(x => x.textContent.trim().slice(0, 40));
    const k = t + '@' + (e && e.dataset.pg);
    if (end) { prev = { k: 'end', end: true }; continue; }
    if (!e || !isHead(e)) bad.push(['멈춘 곳이 소제목 아님', ch.split('·').pop().trim(), pg, (e ? e.className : '') + ': ' + t]);
    else if (prev && prev.k === k) bad.push(['같은 소제목 두 번', ch.split('·').pop().trim(), pg, t]);
    else if (prevSeen.includes(t)) bad.push(['이미 보이던 소제목', ch.split('·').pop().trim(), pg, t]);
    prev = { k }; prevSeen = seen;
  }
  return { done: false, bad, steps };
};
