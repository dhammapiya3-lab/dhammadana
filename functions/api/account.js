// 회원 (독서 기록 이어 보기): 아이디 + 비밀번호. 비밀번호 찾기 = 복구 코드(모든 회원) 또는 이메일(넣은 회원만)
// 저장: R2 'PAPER' 창고(공개 주소 없음)의 acct/ 아래
//   acct/users/<아이디>.json   { id, pw:{s,h}, rc:{s,h}, email, created, fails, lockUntil }  — 비밀번호·복구 코드는 되돌릴 수 없게 바꾼 값만
//   acct/sessions/<열쇠>.json   { id, exp }      (90일)
//   acct/data/<아이디>.json    { k: { v, t } }  읽던 곳·책갈피·밑줄·내 서재 (키마다 마지막으로 바꾼 시각)
//   acct/resets/<열쇠>.json     { id, exp }      이메일 비밀번호 찾기 (1시간, 한 번)
//   acct/emails/<이메일 해시>.json { ids, lastMail } 아이디 찾기용 색인 (이메일 자체는 적지 않고 되돌릴 수 없게 바꾼 값을 이름으로)
// 이메일은 비밀번호·아이디 찾기 메일을 보낼 때만 쓰고 다른 곳에 보내거나 보여 주지 않는다. 메일은 설정값 PAPER_NOTIFY_URL(운영자 Gmail Apps Script)로.
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
const rnd = n => hex(crypto.getRandomValues(new Uint8Array(n)));
const enc = s => new TextEncoder().encode(s);
async function hashOf(secret, salt) {
  const k = await crypto.subtle.importKey('raw', enc(secret), 'PBKDF2', false, ['deriveBits']);
  return hex(await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: enc(salt), iterations: 100000, hash: 'SHA-256' }, k, 256));
}
const makeHash = async secret => { const s = rnd(16); return { s, h: await hashOf(secret, s) }; };
const same = (a, b) => { if (a.length !== b.length) return false; let x = 0; for (let i = 0; i < a.length; i++) x |= a.charCodeAt(i) ^ b.charCodeAt(i); return x === 0; };
const check = async (secret, rec) => !!rec && same(await hashOf(secret, rec.s), rec.h);
const getJ = async (env, key, def = null) => { const o = await env.PAPER.get(key); if (!o) return def; try { return await o.json(); } catch (e) { return def; } };
const putJ = (env, key, v) => env.PAPER.put(key, JSON.stringify(v), { httpMetadata: { contentType: 'application/json; charset=utf-8' } });

// 아이디: 한글·영문·숫자·_ . - 로 3~20자. 영문 대소문자는 같은 아이디로 봄
const normId = s => String(s || '').normalize('NFC').trim();
const okId = s => /^[0-9A-Za-z가-힣_.\-]{2,20}$/.test(s) && !/^[._-]|[._-]$/.test(s);
const keyOf = s => encodeURIComponent(normId(s).toLowerCase());
const okPw = s => typeof s === 'string' && s.length >= 8 && s.length <= 200;
const okEmail = s => s === '' || (/^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/.test(s) && s.length <= 254);
// 복구 코드: 헷갈리는 글자(0 O 1 I L) 없이 12자 → 'K7QM-2XPA-9TZD'
const newCode = () => { const A = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'; const r = crypto.getRandomValues(new Uint8Array(12)); const c = [...r].map(x => A[x % A.length]).join(''); return c.slice(0, 4) + '-' + c.slice(4, 8) + '-' + c.slice(8); };
const normCode = s => String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
const maskEmail = e => { if (!e) return ''; const [a, d] = e.split('@'); return a.slice(0, 2) + '***@' + d; };
const SESSION_DAYS = 90, LOCK_AFTER = 10, LOCK_MIN = 15;

async function newSession(env, id) { const t = rnd(24); await putJ(env, `acct/sessions/${t}.json`, { id, exp: Date.now() + SESSION_DAYS * 864e5 }); return t; }
async function who(env, token) {
  if (!/^[0-9a-f]{48}$/.test(String(token || ''))) return null;
  const s = await getJ(env, `acct/sessions/${token}.json`);
  if (!s || s.exp < Date.now()) return null;
  const u = await getJ(env, `acct/users/${keyOf(s.id)}.json`);
  return u ? { u, token } : null;
}
// 틀린 횟수: 10번 틀리면 15분 잠금
const locked = u => u.lockUntil && u.lockUntil > Date.now();
async function fail(env, u) { u.fails = (u.fails || 0) + 1; if (u.fails >= LOCK_AFTER) { u.lockUntil = Date.now() + LOCK_MIN * 60e3; u.fails = 0; } await putJ(env, `acct/users/${keyOf(u.id)}.json`, u); }
async function ok(env, u) { if (u.fails || u.lockUntil) { u.fails = 0; u.lockUntil = 0; await putJ(env, `acct/users/${keyOf(u.id)}.json`, u); } }
const LOCKMSG = `여러 번 틀려서 ${LOCK_MIN}분 동안 잠겼습니다. 잠시 뒤에 다시 해 주세요.`;
// 한 시간에 만들 수 있는 새 계정 수 (사이트 전체)
async function signupBudget(env) {
  const h = new Date().toISOString().slice(0, 13), k = `acct/rl/signup-${h}.json`;
  const c = await getJ(env, k, { n: 0 }); if (c.n >= 30) return false;
  c.n++; await putJ(env, k, c); return true;
}
async function sendMail(env, to, subject, body) {
  if (!env.PAPER_NOTIFY_URL) return false;
  try {
    const r = await fetch(env.PAPER_NOTIFY_URL, { method: 'POST', headers: { 'content-type': 'text/plain; charset=utf-8' }, body: JSON.stringify({ key: env.PAPER_NOTIFY_KEY || '', to, subject, body }) });
    return r.ok;
  } catch (e) { return false; }
}

// ---- 아이디 찾기용 이메일 색인 ----
const emailKey = async e => `acct/emails/${hex(await crypto.subtle.digest('SHA-256', enc('dd-email:' + String(e).trim().toLowerCase())))}.json`;
async function idxAdd(env, email, id) { if (!email) return; const k = await emailKey(email), x = await getJ(env, k, { ids: [] }); if (!x.ids.includes(id)) { x.ids.push(id); await putJ(env, k, x); } }
async function idxDel(env, email, id) { if (!email) return; const k = await emailKey(email), x = await getJ(env, k); if (!x) return; x.ids = x.ids.filter(v => v !== id); if (x.ids.length) await putJ(env, k, x); else await env.PAPER.delete(k); }
async function idxBuild(env) {  // 색인을 처음 쓸 때 한 번만, 이미 있는 회원들로 만듦
  if (await env.PAPER.head('acct/emails/_built.json')) return;
  let cursor; do { const r = await env.PAPER.list({ prefix: 'acct/users/', cursor, limit: 1000 });
    for (const o of r.objects) { const u = await getJ(env, o.key); if (u && u.email) await idxAdd(env, u.email, u.id); }
    cursor = r.truncated ? r.cursor : null; } while (cursor);
  await putJ(env, 'acct/emails/_built.json', { at: new Date().toISOString() });
}
async function findBudget(env) {  // 아이디 찾기 메일: 사이트 전체 한 시간에 30번까지
  const h = new Date().toISOString().slice(0, 13), k = `acct/rl/findid-${h}.json`;
  const c = await getJ(env, k, { n: 0 }); if (c.n >= 30) return false;
  c.n++; await putJ(env, k, c); return true;
}

const DATA_KEY = /^(bm|ul|hist|plast|pl|pos-[\w.-]{1,40}|ppos-[^\s]{1,300}|sub-[\w.-]{1,60}|sb-b-[\w.-]{1,60})$/;  // sb-b-<책>: 그림책 사이트 내 서재

// 그림책 사이트(storybooks.dhammadana.kr)에서도 같은 회원으로 로그인·내 서재 이어 읽기 (운영자 요청, 2026-11-14)
// 그 사이트에서는 로그인·확인·로그아웃·기록 맞추기만 됨 (가입·비밀번호 찾기는 이 사이트에서)
const SB_ORIGIN = 'https://storybooks.dhammadana.kr', SB_OPS = new Set(['login', 'me', 'logout', 'sync']);
const cors = (r, origin) => { if (origin !== SB_ORIGIN) return r; const h = new Headers(r.headers); h.set('access-control-allow-origin', SB_ORIGIN); h.set('vary', 'Origin'); return new Response(r.body, { status: r.status, headers: h }); };
export const onRequestOptions = ({ request }) => request.headers.get('origin') === SB_ORIGIN
  ? new Response(null, { status: 204, headers: { 'access-control-allow-origin': SB_ORIGIN, 'access-control-allow-methods': 'POST', 'access-control-allow-headers': 'content-type', 'access-control-max-age': '86400', vary: 'Origin' } })
  : new Response(null, { status: 403 });

export async function onRequestPost(ctx) {
  const origin = ctx.request.headers.get('origin') || '';
  return cors(await handle(ctx, origin), origin);
}

async function handle({ request, env }, origin) {
  if (!env.PAPER) return json({ error: '회원 저장소가 아직 연결되지 않았습니다.' }, 503);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ error: '잘못된 요청입니다.' }, 400); }
  const op = String(b.op || '');
  if (origin === SB_ORIGIN && !SB_OPS.has(op)) return json({ error: '이 일은 법보시 도서관(dhammadana.kr)에서 해 주세요.' }, 403);

  if (op === 'signup') {
    const id = normId(b.id), email = String(b.email || '').trim();
    if (!okId(id)) return json({ error: '아이디는 한글·영문·숫자(그리고 _ . -)로 2~20자로 정해 주세요.' }, 400);
    if (!okPw(b.pw)) return json({ error: '비밀번호는 8자 이상으로 정해 주세요.' }, 400);
    if (!okEmail(email)) return json({ error: '이메일 주소를 다시 확인해 주세요.' }, 400);
    if (await getJ(env, `acct/users/${keyOf(id)}.json`)) return json({ error: '이미 있는 아이디입니다. 다른 아이디를 정해 주세요.' }, 409);
    if (!(await signupBudget(env))) return json({ error: '지금은 가입이 많아 잠시 뒤에 다시 해 주세요.' }, 429);
    const code = newCode();
    const u = { id, pw: await makeHash(b.pw), rc: await makeHash(normCode(code)), email, created: new Date().toISOString() };
    await putJ(env, `acct/users/${keyOf(id)}.json`, u);
    if (email) { try { await idxBuild(env); await idxAdd(env, email, id); } catch (e) {} }
    return json({ ok: true, id, token: await newSession(env, id), recovery: code, hasEmail: !!email });
  }
  if (op === 'login') {
    const u = await getJ(env, `acct/users/${keyOf(b.id)}.json`);
    if (!u) return json({ error: '아이디 또는 비밀번호가 맞지 않습니다.' }, 401);
    if (locked(u)) return json({ error: LOCKMSG }, 429);
    if (!(await check(String(b.pw || ''), u.pw))) { await fail(env, u); return json({ error: '아이디 또는 비밀번호가 맞지 않습니다.' }, 401); }
    await ok(env, u);
    return json({ ok: true, id: u.id, token: await newSession(env, u.id), hasEmail: !!u.email });
  }
  if (op === 'recover') {  // 아이디 + 복구 코드 → 새 비밀번호
    const u = await getJ(env, `acct/users/${keyOf(b.id)}.json`);
    if (!u) return json({ error: '아이디 또는 복구 코드가 맞지 않습니다.' }, 401);
    if (locked(u)) return json({ error: LOCKMSG }, 429);
    if (!(await check(normCode(b.code), u.rc))) { await fail(env, u); return json({ error: '아이디 또는 복구 코드가 맞지 않습니다.' }, 401); }
    if (!okPw(b.pw)) return json({ error: '새 비밀번호는 8자 이상으로 정해 주세요.' }, 400);
    const code = newCode(); u.pw = await makeHash(b.pw); u.rc = await makeHash(normCode(code)); u.fails = 0; u.lockUntil = 0;
    await putJ(env, `acct/users/${keyOf(u.id)}.json`, u);
    return json({ ok: true, id: u.id, token: await newSession(env, u.id), recovery: code });
  }
  if (op === 'mail_reset') {  // 이메일로 비밀번호 다시 정하기 링크 (있든 없든 같은 대답)
    const u = await getJ(env, `acct/users/${keyOf(b.id)}.json`);
    const done = json({ ok: true, msg: '그 아이디에 이메일이 등록되어 있으면, 비밀번호를 다시 정하는 링크를 보냈습니다. 메일함(스팸함도)을 확인해 주세요.' });
    if (!u || !u.email) return done;
    if (u.lastMail && Date.now() - u.lastMail < 60e3) return done;  // 1분에 한 번
    const rt = rnd(24); await putJ(env, `acct/resets/${rt}.json`, { id: u.id, exp: Date.now() + 3600e3 });
    u.lastMail = Date.now(); await putJ(env, `acct/users/${keyOf(u.id)}.json`, u);
    const link = `https://dhammadana.kr/account/?reset=${rt}`;
    await sendMail(env, u.email, '[붓다담마 법보시 도서관] 비밀번호 다시 정하기',
      `${u.id} 님, 안녕하세요.\n\n아래 링크를 눌러 새 비밀번호를 정해 주세요. 링크는 1시간 동안 한 번만 쓸 수 있습니다.\n\n${link}\n\n비밀번호 찾기를 하지 않으셨다면 이 메일은 지우셔도 됩니다. 비밀번호는 바뀌지 않습니다.\n\n— 붓다담마 법보시 도서관 (dhammadana.kr)에서 보낸 메일입니다.`);
    return done;
  }
  if (op === 'find_id') {  // 이메일로 아이디 알려 주기 (있든 없든 같은 대답)
    const email = String(b.email || '').trim();
    const done = json({ ok: true, msg: '그 이메일로 가입한 아이디가 있으면, 아이디를 메일로 보냈습니다. 메일함(스팸함도)을 확인해 주세요.' });
    if (!email || !okEmail(email)) return json({ error: '이메일 주소를 다시 확인해 주세요.' }, 400);
    await idxBuild(env);
    const k = await emailKey(email), x = await getJ(env, k);
    if (!x || !x.ids.length) return done;
    if (x.lastMail && Date.now() - x.lastMail < 60e3) return done;  // 1분에 한 번
    if (!(await findBudget(env))) return done;
    // 색인과 실제 계정이 맞는 것만 (지운 계정·바꾼 이메일은 뺌)
    const ids = [];
    for (const id of x.ids) { const u = await getJ(env, `acct/users/${keyOf(id)}.json`); if (u && u.email && u.email.trim().toLowerCase() === email.toLowerCase()) ids.push(u.id); }
    if (!ids.length) return done;
    x.lastMail = Date.now(); await putJ(env, k, x);
    await sendMail(env, email, '[붓다담마 법보시 도서관] 아이디 안내',
      `안녕하세요.\n\n이 이메일로 가입한 아이디는 다음과 같습니다.\n\n${ids.map(i => '· ' + i).join('\n')}\n\n비밀번호도 잊으셨다면 사이트의 '비밀번호 찾기'에서 이메일로 다시 정할 수 있습니다.\nhttps://dhammadana.kr/account/\n\n아이디 찾기를 하지 않으셨다면 이 메일은 지우셔도 됩니다.\n\n— 붓다담마 법보시 도서관`);
    return done;
  }
  if (op === 'reset_pw') {
    if (!/^[0-9a-f]{48}$/.test(String(b.rt || ''))) return json({ error: '링크가 올바르지 않습니다.' }, 400);
    const r = await getJ(env, `acct/resets/${b.rt}.json`);
    if (!r || r.exp < Date.now()) return json({ error: '링크가 지났거나 이미 쓴 링크입니다. 비밀번호 찾기를 다시 해 주세요.' }, 400);
    if (!okPw(b.pw)) return json({ error: '새 비밀번호는 8자 이상으로 정해 주세요.' }, 400);
    const u = await getJ(env, `acct/users/${keyOf(r.id)}.json`); if (!u) return json({ error: '계정을 찾을 수 없습니다.' }, 404);
    u.pw = await makeHash(b.pw); u.fails = 0; u.lockUntil = 0;
    await putJ(env, `acct/users/${keyOf(u.id)}.json`, u); await env.PAPER.delete(`acct/resets/${b.rt}.json`);
    return json({ ok: true, id: u.id, token: await newSession(env, u.id) });
  }

  // ---- 여기부터는 로그인한 회원만 ----
  const me = await who(env, b.token);
  if (!me) return json({ error: '로그인이 필요합니다.', relogin: true }, 401);
  const u = me.u, ukey = `acct/users/${keyOf(u.id)}.json`;
  if (op === 'me') return json({ ok: true, id: u.id, email: maskEmail(u.email), hasEmail: !!u.email, created: u.created, mail: !!env.PAPER_NOTIFY_URL });
  if (op === 'logout') { await env.PAPER.delete(`acct/sessions/${me.token}.json`); return json({ ok: true }); }
  if (op === 'sync') {  // 보낸 것과 저장된 것을 키마다 더 나중 것으로 합쳐서 돌려줌
    const dk = `acct/data/${keyOf(u.id)}.json`, cur = await getJ(env, dk, {});
    let changed = false;
    for (const [k, x] of Object.entries(b.data || {})) {
      if (!DATA_KEY.test(k) || !x || typeof x.t !== 'number') continue;
      if (!cur[k] || x.t > cur[k].t) { cur[k] = { v: x.v, t: Math.min(x.t, Date.now() + 60e3) }; changed = true; }
    }
    if (changed) { const s = JSON.stringify(cur); if (s.length > 4e6) return json({ error: '저장할 기록이 너무 많습니다.' }, 413); await putJ(env, dk, cur); }
    if (b.only === 'sb') return json({ ok: true, data: Object.fromEntries(Object.entries(cur).filter(([k]) => k.startsWith('sb-'))) });
    return json({ ok: true, data: cur });
  }
  // 아래는 비밀번호를 한 번 더 확인
  if (locked(u)) return json({ error: LOCKMSG }, 429);
  if (!(await check(String(b.pw || ''), u.pw))) { await fail(env, u); return json({ error: '지금 비밀번호가 맞지 않습니다.' }, 401); }
  await ok(env, u);
  if (op === 'change_pw') {
    if (!okPw(b.newPw)) return json({ error: '새 비밀번호는 8자 이상으로 정해 주세요.' }, 400);
    u.pw = await makeHash(b.newPw); await putJ(env, ukey, u); return json({ ok: true });
  }
  if (op === 'set_email') {
    const email = String(b.email || '').trim(); if (!okEmail(email)) return json({ error: '이메일 주소를 다시 확인해 주세요.' }, 400);
    try { await idxBuild(env); } catch (e) {}
    const before = u.email; u.email = email; await putJ(env, ukey, u);
    try { if (before && before.toLowerCase() !== email.toLowerCase()) await idxDel(env, before, u.id); if (email) await idxAdd(env, email, u.id); } catch (e) {}
    return json({ ok: true, email: maskEmail(email), hasEmail: !!email });
  }
  if (op === 'new_code') { const code = newCode(); u.rc = await makeHash(normCode(code)); await putJ(env, ukey, u); return json({ ok: true, recovery: code }); }
  if (op === 'delete') {
    try { await idxDel(env, u.email, u.id); } catch (e) {}
    await env.PAPER.delete([ukey, `acct/data/${keyOf(u.id)}.json`, `acct/sessions/${me.token}.json`]);
    return json({ ok: true });
  }
  return json({ error: '알 수 없는 요청입니다.' }, 400);
}
