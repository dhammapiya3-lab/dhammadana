// 종이책 보시 신청 게시판 (비밀글) — 서버: /api/paper
(() => {
  const root = document.getElementById('pqRoot'); if (!root) return;
  const BOOKS = JSON.parse(root.dataset.books || '[]');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ST = { received: '접수', sent: '발송 완료' };
  const api = async (body) => {
    const r = await fetch('/api/paper', body ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) } : {});
    let j = {}; try { j = await r.json(); } catch (e) { j = { error: '잠시 연결이 고르지 않습니다. 다시 해 주세요.' }; }
    if (!r.ok && !j.error) j.error = '처리하지 못했습니다. 잠시 뒤 다시 해 주세요.';
    return j;
  };
  let want = new URLSearchParams(location.search).get('book') || '';
  let items = [], openId = '', mine = null, pwKeep = '';

  const privacy = `<details class="pq-priv"><summary>개인정보 수집·이용 안내 (눌러서 보기)</summary>
    <ul><li><b>모으는 것</b>: 받는 분 이름, 연락처, 주소, 남길 말</li>
    <li><b>쓰는 곳</b>: 종이책 발송과 발송에 필요한 연락</li>
    <li><b>보관 기간</b>: 발송 완료 후 90일이 지나면 지웁니다. 발송 전에 취소하면 바로 지웁니다.</li>
    <li>신청 글은 비밀글이며, 신청하신 분(비밀번호)과 我無말들 출판사만 볼 수 있습니다.</li>
    <li>동의하지 않으실 수 있지만, 동의하지 않으면 신청할 수 없습니다.</li></ul></details>`;

  function formHtml(v = {}, edit = false) {
    const cur = booksOf(v), pick = new Map(cur.map(x => [x.id, x.qty]));
    if (!cur.length && want && BOOKS.some(b => b.id === want)) pick.set(want, 1);
    const all = [...BOOKS, ...cur.filter(x => !BOOKS.some(b => b.id === x.id))];
    return `<form class="pq-form" id="pqForm" autocomplete="on">
      <div class="pq-row"><label for="fTitle">글 제목 <span class="muted small">(선택 · 비워 두면 '『자애 수행』(예시) 신청합니다'로 보입니다)</span></label><input id="fTitle" name="title" maxlength="60" value="${esc(v.title)}"></div>
      <fieldset class="pq-row pq-bk"><legend>신청할 책 <span class="muted small">(여러 권을 함께 고를 수 있습니다)</span></legend>
        ${all.map(b => { const on = pick.has(b.id); return `<div class="pq-bi${on ? ' on' : ''}"><label><input type="checkbox" data-bk="${esc(b.id)}" data-title="${esc(b.title)}"${on ? ' checked' : ''}> 『${esc(b.title)}』</label><span class="pq-q"><input type="number" min="1" inputmode="numeric" data-q="${esc(b.id)}" value="${on ? pick.get(b.id) : 1}" aria-label="『${esc(b.title)}』 권수"${on ? '' : ' disabled'}> 권</span></div>`; }).join('')}
      </fieldset>
      <div class="pq-row"><label for="fName">받는 분 이름</label><input id="fName" name="name" maxlength="40" value="${esc(v.name)}" autocomplete="name" required></div>
      <div class="pq-row"><label for="fPhone">연락처 (전화번호)</label><input id="fPhone" name="phone" maxlength="30" inputmode="tel" value="${esc(v.phone)}" autocomplete="tel" placeholder="010-0000-0000" required></div>
      <div class="pq-row"><label for="fAddr">받을 주소</label><textarea id="fAddr" name="address" maxlength="200" rows="2" autocomplete="street-address" required>${esc(v.address)}</textarea></div>
      <div class="pq-row"><label for="fMemo">남길 말 (선택)</label><textarea id="fMemo" name="memo" maxlength="1000" rows="3">${esc(v.memo)}</textarea></div>
      ${edit ? '' : `<div class="pq-row"><label for="fPw">비밀번호 (내 신청 글을 다시 보거나 고칠 때 씁니다, 4자 이상)</label><input id="fPw" name="password" type="password" minlength="4" maxlength="64" autocomplete="new-password" required></div>
      <div class="pq-hp" aria-hidden="true"><label>웹사이트<input name="website" tabindex="-1" autocomplete="off"></label></div>
      ${privacy}
      <label class="pq-agree"><input type="checkbox" name="agree" required> 개인정보 수집·이용에 동의합니다.</label>`}
      <div class="pq-msg" id="pqMsg" role="status"></div>
      <div class="pq-btns"><button class="btn" type="submit">${edit ? '고친 내용 저장' : '신청하기'}</button>${edit ? '<button class="btn ghost" type="button" id="pqEditCancel">그만두기</button>' : ''}</div>
    </form>`;
  }
  const booksOf = v => v && v.books && v.books.length ? v.books : (v && v.book ? [{ id: v.book, title: v.bookTitle, qty: v.qty }] : []);
  const summary = v => booksOf(v).map(x => `『${x.title}』 ${x.qty}권`).join(', ');
  const pickedBooks = f => [...f.querySelectorAll('[data-bk]:checked')].map(c => ({ id: c.dataset.bk, qty: +(f.querySelector(`[data-q="${c.dataset.bk}"]`).value || 1) }));
  const bindBooks = f => f.querySelectorAll('[data-bk]').forEach(c => c.onchange = () => { const q = f.querySelector(`[data-q="${c.dataset.bk}"]`); q.disabled = !c.checked; c.closest('.pq-bi').classList.toggle('on', c.checked); if (c.checked) q.focus(); });
  const formData = f => ({ ...Object.fromEntries(new FormData(f).entries()), books: pickedBooks(f) });

  function listHtml() {
    if (!items.length) return '<p class="muted pq-empty">아직 신청 글이 없습니다.</p>';
    return `<ul class="pq-list">${items.map((x, i) => `<li class="${x.id === openId ? 'open' : ''}">
      <button class="pq-item" data-id="${x.id}" aria-expanded="${x.id === openId}">
        <span class="pq-no">${items.length - i}</span>
        <span class="pq-t">🔒 비밀글 · ${x.title ? esc(x.title) : esc(x.book) + ' 신청합니다'}${x.edited ? ' <span class="muted small">(고침)</span>' : ''}${x.replies ? ` <span class="pq-rc">💬 댓글 ${x.replies}</span>` : ''}</span>
        <span class="pq-w">${esc(x.who)}</span><span class="pq-d">${esc(x.date.slice(5).replace('-', '.'))}</span>
        <span class="pq-s ${x.status}">${ST[x.status] || ''}</span></button>
      ${x.id === openId ? `<div class="pq-open">${openBody(x)}</div>` : ''}</li>`).join('')}</ul>`;
  }
  function openBody(x) {
    if (!mine || mine.id !== x.id) return `<form class="pq-pw" id="pqPw"><label for="pPw">비밀글입니다. 신청할 때 정한 비밀번호를 넣어 주세요.</label><div class="row"><input id="pPw" type="password" autocomplete="current-password" required><button class="btn sm" type="submit">보기</button></div><div class="pq-msg" id="pwMsg" role="status"></div></form>`;
    if (mine._edit) return formHtml(mine, true);
    const m = mine;
    return `<dl class="pq-dl"><dt>신청 번호</dt><dd>${esc(m.id)}</dd>${m.title ? `<dt>글 제목</dt><dd>${esc(m.title)}</dd>` : ''}<dt>책</dt><dd>${esc(summary(m))}</dd><dt>받는 분</dt><dd>${esc(m.name)}</dd><dt>연락처</dt><dd>${esc(m.phone)}</dd><dt>주소</dt><dd>${esc(m.address)}</dd><dt>남길 말</dt><dd>${esc(m.memo) || '—'}</dd><dt>상태</dt><dd>${ST[m.status]}</dd></dl>
      <div class="pq-replies"><h3>댓글</h3>${(m.replies || []).map(x => `<div class="pq-reply ${x.by === 'user' ? 'me' : ''}"><div class="pq-ra">${x.by === 'user' ? '신청한 분' : '담마삐야'} · ${esc(x.at.slice(5, 16).replace('T', ' ').replace('-', '.'))}</div><div class="pq-rt">${esc(x.text)}</div></div>`).join('') || '<p class="muted small">아직 댓글이 없습니다.</p>'}
        <form class="pq-cm" id="pqCm"><textarea id="cmText" rows="2" maxlength="1000" placeholder="출판사에 남길 댓글" required></textarea><button class="btn sm" type="submit">댓글 달기</button></form></div>
      ${m.status === 'sent' ? '<p class="muted small">발송한 신청은 고치거나 취소할 수 없습니다.</p>' : '<div class="pq-btns"><button class="btn sm" id="pqEdit">고치기</button><button class="btn sm ghost" id="pqCancel">신청 취소</button></div>'}
      <div class="pq-msg" id="pqMsg2" role="status"></div>`;
  }

  function render(note = '') {
    root.innerHTML = `<div class="pq-top"><button class="btn" id="pqWriteBtn" aria-expanded="false">✍ 신청 글 쓰기</button></div>
      <section class="pq-write" id="write" hidden><h2>신청 글 쓰기</h2>${formHtml()}</section>
      ${note}
      <h2 class="pq-h">신청 목록</h2>${listHtml()}`;
    bind();
    if (want || location.hash === '#write') openWrite(!note);
  }
  function openWrite(scroll) {
    const w = document.getElementById('write'); if (!w) return; w.hidden = false;
    document.getElementById('pqWriteBtn').setAttribute('aria-expanded', 'true');
    if (scroll) w.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function bind() {
    document.getElementById('pqWriteBtn').onclick = () => { const w = document.getElementById('write'); if (w.hidden) openWrite(true); else { w.hidden = true; document.getElementById('pqWriteBtn').setAttribute('aria-expanded', 'false'); } };
    const t0 = Date.now();
    const f = document.querySelector('#write #pqForm');
    if (f) bindBooks(f);
    if (f) f.onsubmit = async e => {
      e.preventDefault(); const msg = f.querySelector('#pqMsg'); const btn = f.querySelector('[type=submit]');
      if (!pickedBooks(f).length) { msg.className = 'pq-msg err'; msg.textContent = '신청할 책을 하나 이상 골라 주세요.'; return; }
      btn.disabled = true; msg.className = 'pq-msg'; msg.textContent = '보내는 중…';
      const j = await api({ action: 'create', t: t0, ...formData(f), agree: f.agree.checked });
      btn.disabled = false;
      if (j.error) { msg.className = 'pq-msg err'; msg.textContent = j.error; return; }
      history.replaceState(null, '', location.pathname); want = '';
      await load(`<div class="pq-done" role="status"><b>신청을 받았습니다. 고맙습니다.</b><br>목록에서 내 글을 누르고 정한 비밀번호를 넣으면 신청 내용을 보거나 고칠 수 있습니다. 비밀번호를 꼭 기억해 주세요.</div>`);
    };
    root.querySelectorAll('.pq-item').forEach(b => b.onclick = () => { const id = b.dataset.id; openId = openId === id ? '' : id; if (!mine || mine.id !== openId) mine = null; redrawList(); });
    bindOpen();
  }
  function redrawList() {
    const l = root.querySelector('.pq-list'); if (!l) return; l.outerHTML = listHtml();
    root.querySelectorAll('.pq-item').forEach(b => b.onclick = () => { const id = b.dataset.id; openId = openId === id ? '' : id; if (!mine || mine.id !== openId) mine = null; redrawList(); });
    bindOpen();
    const pw = document.getElementById('pPw'); if (pw) pw.focus();
  }
  function bindOpen() {
    const pf = document.getElementById('pqPw');
    if (pf) pf.onsubmit = async e => {
      e.preventDefault(); const pw = document.getElementById('pPw').value; const m = document.getElementById('pwMsg'); m.className = 'pq-msg'; m.textContent = '확인 중…';
      const j = await api({ action: 'view', id: openId, password: pw });
      if (j.error) { m.className = 'pq-msg err'; m.textContent = j.error; return; }
      mine = j.item; pwKeep = pw; redrawList();
    };
    const cm = document.getElementById('pqCm'); if (cm) cm.onsubmit = async e => {
      e.preventDefault(); const t = document.getElementById('cmText').value.trim(); if (!t) return; cm.querySelector('button').disabled = true;
      const j = await api({ action: 'comment', id: openId, password: pwKeep, text: t });
      if (j.error) { cm.querySelector('button').disabled = false; alert(j.error); return; }
      mine = j.item; const it = items.find(x => x.id === openId); if (it) it.replies = (mine.replies || []).length; redrawList();
    };
    const ed = document.getElementById('pqEdit'); if (ed) ed.onclick = () => { mine._edit = true; redrawList(); };
    const cc = document.getElementById('pqCancel'); if (cc) cc.onclick = async () => {
      if (!confirm('이 신청을 취소할까요? 신청 내용이 바로 지워집니다.')) return;
      const j = await api({ action: 'cancel', id: openId, password: pwKeep });
      if (j.error) { document.getElementById('pqMsg2').className = 'pq-msg err'; document.getElementById('pqMsg2').textContent = j.error; return; }
      openId = ''; mine = null; await load('<div class="pq-done" role="status">신청을 취소했습니다.</div>');
    };
    const ef = root.querySelector('.pq-open #pqForm');
    if (ef) {
      bindBooks(ef);
      ef.querySelector('#pqEditCancel').onclick = () => { mine._edit = false; redrawList(); };
      ef.onsubmit = async e => {
        e.preventDefault(); const msg = ef.querySelector('#pqMsg'); msg.className = 'pq-msg'; msg.textContent = '저장하는 중…';
        const j = await api({ action: 'update', id: openId, password: pwKeep, ...formData(ef) });
        if (j.error) { msg.className = 'pq-msg err'; msg.textContent = j.error; return; }
        mine = j.item; const it = items.find(x => x.id === openId); if (it) { it.book = booksOf(mine).map(x => `『${x.title}』`).join(', '); it.title = mine.title || ''; it.edited = true; }
        redrawList(); const m2 = document.getElementById('pqMsg2'); if (m2) { m2.className = 'pq-msg ok'; m2.textContent = '고친 내용을 저장했습니다.'; }
      };
    }
  }
  async function load(note = '') {
    const j = await api();
    if (!j.ready) { root.innerHTML = '<div class="pq-done">신청 접수를 준비하고 있습니다. 곧 이곳에서 신청하실 수 있습니다.</div>'; return; }
    items = j.items || []; render(note);
  }
  load();
})();
