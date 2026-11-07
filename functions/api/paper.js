import { canWriteToken as canWrite } from './_auth.js';
// 종이책 보시 신청 게시판 (비밀글)
// 저장: R2 'PAPER' 창고 (공개 주소 없음). req/<번호>.json = 신청 한 건, index.json = 목록(가린 이름·책·날짜·상태만)
// 알림: 설정값 PAPER_NOTIFY_URL (구글 Apps Script 주소, Cloudflare 비밀 변수) 로 신청 내용 전체를 보내 담마삐야님 Gmail 로 메일
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const STATUS = { received: '접수', sent: '발송 완료' };
const KEEP_DAYS = 90;  // 발송 완료 뒤 90일이 지나면 지움
const LIM = { name: 40, phone: 30, address: 200, memo: 1000 };

const mask = n => { const s = [...String(n || '').trim()]; return s.length <= 1 ? (s[0] || '') + '○' : s[0] + '○'.repeat(s.length - 1); };
const clean = (s, n) => String(s ?? '').replace(/[\u0000-\u0008\u000b-\u001f]/g, '').trim().slice(0, n);
const rid = () => [...crypto.getRandomValues(new Uint8Array(4))].map(x => x.toString(16).padStart(2, '0')).join('');
const newId = () => { const d = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10).replace(/-/g, ''); const r = crypto.getRandomValues(new Uint8Array(6)); return d + '-' + [...r].map(x => x.toString(16).padStart(2, '0')).join(''); };
const okId = id => /^\d{8}-[0-9a-f]{12}$/.test(String(id || ''));
const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
async function hashPw(pw, salt) {
  const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveBits']);
  return hex(await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: new TextEncoder().encode(salt), iterations: 100000, hash: 'SHA-256' }, k, 256));
}
const sha = async s => hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));

async function getJ(env, key, def) { const o = await env.PAPER.get(key); if (!o) return def; try { return await o.json(); } catch (e) { return def; } }
const putJ = (env, key, v) => env.PAPER.put(key, JSON.stringify(v), { httpMetadata: { contentType: 'application/json; charset=utf-8' } });
// 책 여러 권: r.books = [{ id, title, qty }] (예전 한 권짜리 r.book·bookTitle·qty 도 읽음)
const booksOf = r => r.books && r.books.length ? r.books : (r.book ? [{ id: r.book, title: r.bookTitle, qty: r.qty }] : []);
const summary = r => booksOf(r).map(x => `『${x.title}』 ${x.qty}권`).join(', ');
// 공개 목록: 책 제목만 (권수는 신청한 분·관리자만)
const pub = r => ({ v: 2, id: r.id, who: mask(r.name), book: booksOf(r).map(x => `『${x.title}』`).join(', '), date: r.created.slice(0, 10), status: r.status, edited: !!r.updated, replies: (r.replies || []).length });
async function saveIndex(env, list) { await putJ(env, 'index.json', list.sort((a, b) => b.id.localeCompare(a.id))); }
async function upsertIndex(env, r) { const l = (await getJ(env, 'index.json', [])).filter(x => x.id !== r.id); l.push(pub(r)); await saveIndex(env, l); }
async function dropIndex(env, id) { await saveIndex(env, (await getJ(env, 'index.json', [])).filter(x => x.id !== id)); }

// 같은 곳(IP)에서 너무 자주: 종류별로 시간 안 횟수 제한
async function limited(env, request, kind, max, mins) {
  const ip = request.headers.get('cf-connecting-ip') || 'x';
  const key = `rl/${kind}-${(await sha(ip + '|dhammadana')).slice(0, 24)}.json`;
  const now = Date.now(); const l = (await getJ(env, key, [])).filter(t => now - t < mins * 60e3);
  if (l.length >= max) return true;
  l.push(now); await putJ(env, key, l); return false;
}

function mailText(r, what) {
  return [`[종이책 보시 신청] ${what}`, '',
    `신청 번호: ${r.id}`, `책: ${summary(r)}`, `받는 분: ${r.name}`, `연락처: ${r.phone}`,
    `주소: ${r.address}`, `남길 말: ${r.memo || '(없음)'}`,
    `신청한 때: ${r.created.replace('T', ' ').slice(0, 16)}`, r.updated ? `고친 때: ${r.updated.replace('T', ' ').slice(0, 16)}` : '', '',
    '관리 화면: https://dhammadana.kr/admin/paper/'].filter(x => x !== '').join('\n');
}
async function notify(env, r, what) {
  if (!env.PAPER_NOTIFY_URL) return;
  try {
    await fetch(env.PAPER_NOTIFY_URL, { method: 'POST', headers: { 'content-type': 'text/plain; charset=utf-8' },
      body: JSON.stringify({ key: env.PAPER_NOTIFY_KEY || '', subject: `[종이책 보시 신청] ${what} · ${r.name} · ${summary(r)}`.slice(0, 160), body: mailText(r, what) }) });
  } catch (e) {}
}
const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 19);

function readFields(b, books) {
  const seen = new Set(), list = [];
  for (const x of Array.isArray(b.books) ? b.books : []) {
    const bk = books.find(y => y.id === (x && x.id)); if (!bk || seen.has(bk.id)) continue; seen.add(bk.id);
    list.push({ id: bk.id, title: bk.title, qty: Math.max(1, Math.min(99999, parseInt(x.qty, 10) || 1)) });
  }
  const f = { books: list, book: '', bookTitle: '', qty: 0, name: clean(b.name, LIM.name), phone: clean(b.phone, LIM.phone), address: clean(b.address, LIM.address), memo: clean(b.memo, LIM.memo) };
  if (!list.length) return [null, '신청할 책을 하나 이상 골라 주세요.'];
  if (!f.name) return [null, '받는 분 이름을 적어 주세요.'];
  if (!/[0-9]{2,}.*[0-9]{3,}/.test(f.phone)) return [null, '연락처(전화번호)를 적어 주세요.'];
  if (f.address.length < 5) return [null, '받을 주소를 적어 주세요.'];
  return [f, ''];
}
// 신청할 수 있는 책 목록: 사이트가 만들어 둔 /paper-books.json
async function bookList(request) {
  try { const r = await fetch(new URL('/paper-books.json', request.url)); return r.ok ? await r.json() : []; } catch (e) { return []; }
}
async function purge(env) {
  const l = await getJ(env, 'index.json', []); const now = Date.now(); const keep = [];
  for (const x of l) {
    if (x.status === 'sent' && x.sentAt && now - Date.parse(x.sentAt + '+09:00') > KEEP_DAYS * 86400e3) { await env.PAPER.delete(`req/${x.id}.json`); continue; }
    keep.push(x);
  }
  if (keep.length !== l.length) await saveIndex(env, keep);
}

export async function onRequestGet({ request, env }) {
  if (!env.PAPER) return json({ ready: false, items: [] });
  const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (token) {  // 관리자: 신청 내용 전체
    if (!(await canWrite(token))) return json({ error: '허락되지 않았습니다.' }, 401);
    await purge(env);
    const l = await getJ(env, 'index.json', []);
    const items = (await Promise.all(l.map(x => getJ(env, `req/${x.id}.json`, null)))).filter(Boolean).map(({ pw, salt, ...r }) => r);
    return json({ ready: true, notify: !!env.PAPER_NOTIFY_URL, items });
  }
  let l = await getJ(env, 'index.json', []);
  if (l.some(x => x.v !== 2)) {  // 예전 목록 형식이면 신청 글에서 다시 만듦
    const rs = (await Promise.all(l.map(x => getJ(env, `req/${x.id}.json`, null)))).filter(Boolean);
    l = rs.map(r => ({ ...pub(r), sentAt: r.sentAt || '' })); await saveIndex(env, l);
  }
  return json({ ready: true, items: l.map(({ sentAt, v, ...x }) => x) });
}

export async function onRequestPost(ctx) {
  const { request, env } = ctx;
  if (!env.PAPER) return json({ error: '신청 접수를 준비하고 있습니다. 잠시 뒤 다시 와 주세요.' }, 503);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ error: '잘못된 요청입니다.' }, 400); }
  const act = b.action;

  // ── 관리자 ──
  if (act === 'status' || act === 'delete' || act === 'reply' || act === 'unreply') {
    const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
    if (!(await canWrite(token))) return json({ error: '허락되지 않았습니다.' }, 401);
    if (!okId(b.id)) return json({ error: '번호 오류' }, 400);
    if (act === 'delete') { await env.PAPER.delete(`req/${b.id}.json`); await dropIndex(env, b.id); return json({ ok: true }); }
    const r = await getJ(env, `req/${b.id}.json`, null); if (!r) return json({ error: '없는 신청입니다.' }, 404);
    // 댓글(관리자·신청자): 신청한 분이 비밀번호로 글을 열었을 때만 보임 (목록에는 '댓글 n'만)
    if (act === 'reply' || act === 'unreply') {
      r.replies = r.replies || [];
      if (act === 'reply') { const text = clean(b.text, 1000); if (!text) return json({ error: '댓글 내용을 적어 주세요.' }, 400); r.replies.push({ id: rid(), at: kst(), text, by: 'admin' }); }
      else r.replies = r.replies.filter(x => (x.id || x.at) !== (b.rid || b.at));
      await putJ(env, `req/${r.id}.json`, r);
      const l = (await getJ(env, 'index.json', [])).filter(x => x.id !== r.id); l.push({ ...pub(r), sentAt: r.sentAt }); await saveIndex(env, l);
      return json({ ok: true, replies: r.replies });
    }
    if (!STATUS[b.status]) return json({ error: '상태 오류' }, 400);
    r.status = b.status; r.sentAt = b.status === 'sent' ? kst() : '';
    await putJ(env, `req/${r.id}.json`, r);
    const l = (await getJ(env, 'index.json', [])).filter(x => x.id !== r.id); l.push({ ...pub(r), sentAt: r.sentAt }); await saveIndex(env, l);
    return json({ ok: true });
  }

  // ── 신청자 ──
  if (act === 'create') {
    if (b.website) return json({ ok: true, id: '' });  // 사람에게는 보이지 않는 칸: 채워져 있으면 프로그램이 쓴 글
    if (!b.t || Date.now() - Number(b.t) < 4000) return json({ error: '조금 천천히 다시 눌러 주세요.' }, 400);
    if (!b.agree) return json({ error: '개인정보 수집·이용에 동의해 주셔야 신청할 수 있습니다.' }, 400);
    const pw = String(b.password || ''); if (pw.length < 4 || pw.length > 64) return json({ error: '비밀번호를 4자 이상 정해 주세요.' }, 400);
    const [f, err] = readFields(b, await bookList(request)); if (err) return json({ error: err }, 400);
    if (await limited(env, request, 'new', 5, 60)) return json({ error: '짧은 시간에 너무 많이 신청했습니다. 한 시간 뒤 다시 해 주세요.' }, 429);
    const salt = newId(); const r = { id: newId(), created: kst(), updated: '', status: 'received', sentAt: '', ...f, salt, pw: await hashPw(pw, salt) };
    await putJ(env, `req/${r.id}.json`, r); await upsertIndex(env, r);
    ctx.waitUntil(notify(env, r, '새 신청'));
    return json({ ok: true, id: r.id });
  }
  if (act === 'view' || act === 'update' || act === 'cancel' || act === 'comment') {
    if (!okId(b.id)) return json({ error: '번호 오류' }, 400);
    if (await limited(env, request, 'pw', 20, 30)) return json({ error: '비밀번호를 너무 여러 번 넣었습니다. 30분 뒤 다시 해 주세요.' }, 429);
    const r = await getJ(env, `req/${b.id}.json`, null);
    if (!r || (await hashPw(String(b.password || ''), r.salt)) !== r.pw) return json({ error: '비밀번호가 맞지 않습니다.' }, 403);
    const { pw, salt, ...mine } = r;
    if (act === 'view') return json({ ok: true, item: mine });
    if (act === 'comment') {  // 신청자 댓글 (발송 뒤에도 가능)
      const text = clean(b.text, 1000); if (!text) return json({ error: '댓글 내용을 적어 주세요.' }, 400);
      if ((r.replies || []).filter(x => x.by === 'user').length >= 30) return json({ error: '댓글이 너무 많습니다.' }, 400);
      r.replies = r.replies || []; r.replies.push({ id: rid(), at: kst(), text, by: 'user' });
      await putJ(env, `req/${r.id}.json`, r); await upsertIndex(env, r);
      ctx.waitUntil(notify(env, { ...r, memo: `[신청자 댓글] ${text}` }, '신청자 댓글'));
      const { pw: _p, salt: _s, ...out } = r; return json({ ok: true, item: out });
    }
    if (r.status === 'sent') return json({ error: '이미 발송한 신청은 고치거나 취소할 수 없습니다.' }, 400);
    if (act === 'cancel') { await env.PAPER.delete(`req/${r.id}.json`); await dropIndex(env, r.id); ctx.waitUntil(notify(env, r, '신청 취소')); return json({ ok: true }); }
    const bl = await bookList(request); for (const x of booksOf(r)) if (!bl.some(y => y.id === x.id)) bl.push({ id: x.id, title: x.title });
    const [f, err] = readFields(b, bl); if (err) return json({ error: err }, 400);
    Object.assign(r, f, { updated: kst() });
    await putJ(env, `req/${r.id}.json`, r); await upsertIndex(env, r);
    ctx.waitUntil(notify(env, r, '신청 내용 고침'));
    const { pw: _p, salt: _s, ...out } = r; return json({ ok: true, item: out });
  }
  return json({ error: '알 수 없는 요청' }, 400);
}
