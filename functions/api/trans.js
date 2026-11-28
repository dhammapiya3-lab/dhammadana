// 학습 자료실 '번역 교정' (관리자만): 원서 · 대조 번역본 · 우리 번역을 문장마다 나란히 놓고 우리 번역을 고침.
// 자료는 비공개 창고(MEMBERS)의 _trans/ 아래에만 둔다 — GitHub 에도 공개 주소에도 두지 않음. (운영자 요청, 2026-11-28)
//   GET  /api/trans            → 자료 목록
//   GET  /api/trans?id=…       → 자료 하나(모든 줄)
//   PUT  /api/trans?id=…       → 새 자료 넣기 (이미 있으면 &replace=1 일 때만 바꿈)
//   PUT  /api/trans?id=…&ref=1 → 대조 번역본만 넣기 {kind:'ref', id, title, col, info, rows:{줄id:[대조 글, rc]}} — 우리 번역·고친 기록·메모는 그대로 (2026-11-28)
//   PUT  /api/trans?id=…&cm=1  → 교정 의견만 넣기 {kind:'cm', id, title, info, intro, policy, rows:{줄id:[의견…]}} — 우리 번역·고친 기록·메모·넣음 표시(cmDone)는 그대로 (2026-11-28)
//   POST /api/trans?id=…       → 줄 하나 고치기 {row, t?, note?, cmDone?} — 고치기 전 글은 그 줄의 기록(hist)에 남김
import { canWriteToken } from './_auth.js';
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const tokenOf = r => (r.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
const okId = id => typeof id === 'string' && /^[a-z0-9][a-z0-9-]{0,80}$/.test(id);
const KEY = id => `_trans/${id}.json`, INDEX = '_trans/_index.json';
const HIST_MAX = 30;

async function guard(request, env) {
  if (!env.MEMBERS) return json({ error: '학습 자료실 창고가 연결되지 않았습니다 (MEMBERS).' }, 503);
  if (!(await canWriteToken(tokenOf(request)))) return json({ error: '관리자만 쓸 수 있습니다. 관리자 열쇠를 확인해 주세요.' }, 401);
  return null;
}
async function getJSON(env, key, dflt) { try { const o = await env.MEMBERS.get(key); return o ? await o.json() : dflt; } catch (e) { return dflt; } }
const putJSON = (env, key, v) => env.MEMBERS.put(key, JSON.stringify(v), { httpMetadata: { contentType: 'application/json; charset=utf-8' } });
const summary = d => ({ id: d.id, title: d.title, rows: d.rows.length, edited: d.rows.filter(r => r.t !== r.t0).length, notes: d.rows.filter(r => r.note).length, cm: d.rows.reduce((n, r) => n + (r.cm ? r.cm.length : 0), 0), cmDone: d.rows.reduce((n, r) => n + (r.cm && r.cmDone ? r.cmDone.filter(x => r.cm.some(c => c.n === x)).length : 0), 0), updated: d.updated || d.made || '', cols: d.cols });
async function touchIndex(env, d) {
  const idx = await getJSON(env, INDEX, { items: [] });
  idx.items = (idx.items || []).filter(x => x.id !== d.id); idx.items.push(summary(d));
  idx.items.sort((a, b) => String(b.updated).localeCompare(String(a.updated)));
  await putJSON(env, INDEX, idx);
}

export async function onRequestGet({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const id = new URL(request.url).searchParams.get('id');
  if (!id) return json(await getJSON(env, INDEX, { items: [] }));
  if (!okId(id)) return json({ error: '자료 이름이 올바르지 않습니다.' }, 400);
  const d = await getJSON(env, KEY(id), null);
  return d ? json(d) : json({ error: '자료를 찾지 못했습니다.' }, 404);
}

export async function onRequestPut({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const u = new URL(request.url), id = u.searchParams.get('id');
  if (!okId(id)) return json({ error: '자료 이름이 올바르지 않습니다.' }, 400);
  const txt = await request.text();
  if (txt.length > 20000000) return json({ error: '자료가 너무 큽니다.' }, 400);
  let d; try { d = JSON.parse(txt); } catch (e) { return json({ error: '자료 파일 형식이 올바르지 않습니다.' }, 400); }
  if (u.searchParams.get('ref') === '1') {
    if (!d || d.kind !== 'ref' || d.id !== id || !d.rows || typeof d.rows !== 'object') return json({ error: '대조 번역본 파일 형식이 올바르지 않습니다.' }, 400);
    const cur = await getJSON(env, KEY(id), null); if (!cur) return json({ error: '이 대조 번역본을 넣을 자료가 아직 없습니다. 자료부터 넣어 주세요.' }, 404);
    if (cur.rows.some(r => r.r) && u.searchParams.get('replace') !== '1') return json({ error: '이미 대조 번역본이 있습니다.', exists: true }, 409);
    let n = 0, miss = 0; const ids = new Set(cur.rows.map(r => r.id));
    for (const k of Object.keys(d.rows)) if (!ids.has(k)) miss++;
    cur.rows.forEach(r => { const v = d.rows[r.id]; r.r = v && typeof v[0] === 'string' ? v[0] : ''; if (v && v[1]) r.rc = 1; else delete r.rc; if (r.r) n++; });
    cur.cols = { ...(cur.cols || {}), r: d.col || (cur.cols && cur.cols.r) || '대조 번역본' };
    if (d.info) cur.info = { ...(cur.info || {}), r: d.info };
    cur.updated = new Date().toISOString();
    await putJSON(env, KEY(id), cur); await touchIndex(env, cur);
    return json({ ok: true, ref: n, miss, ...summary(cur) });
  }
  if (u.searchParams.get('cm') === '1') {
    if (!d || d.kind !== 'cm' || d.id !== id || !d.rows || typeof d.rows !== 'object') return json({ error: '교정 의견 파일 형식이 올바르지 않습니다.' }, 400);
    const cur = await getJSON(env, KEY(id), null); if (!cur) return json({ error: '이 교정 의견을 넣을 자료가 아직 없습니다. 자료부터 넣어 주세요.' }, 404);
    if (cur.rows.some(r => r.cm) && u.searchParams.get('replace') !== '1') return json({ error: '이미 교정 의견이 있습니다.', exists: true }, 409);
    let n = 0, miss = 0; const ids = new Set(cur.rows.map(r => r.id));
    for (const k of Object.keys(d.rows)) if (!ids.has(k)) miss += d.rows[k].length;
    cur.rows.forEach(r => { const v = d.rows[r.id]; if (Array.isArray(v) && v.length) { r.cm = v; n += v.length; } else delete r.cm; });
    cur.cmInfo = { title: d.title || '', info: d.info || '', intro: d.intro || [], policy: d.policy || [], at: new Date().toISOString() };
    cur.updated = new Date().toISOString();
    await putJSON(env, KEY(id), cur); await touchIndex(env, cur);
    return json({ ok: true, cmAdded: n, miss, ...summary(cur) });
  }
  if (!d || d.id !== id || !Array.isArray(d.rows) || !d.rows.every(r => r && typeof r.id === 'string' && typeof r.t === 'string')) return json({ error: '자료 파일 형식이 올바르지 않습니다.' }, 400);
  const old = await env.MEMBERS.head(KEY(id));
  if (old && u.searchParams.get('replace') !== '1') return json({ error: '같은 이름의 자료가 이미 있습니다.', exists: true }, 409);
  d.rows.forEach(r => { if (typeof r.t0 !== 'string') r.t0 = r.t; });
  d.updated = new Date().toISOString();
  await putJSON(env, KEY(id), d); await touchIndex(env, d);
  return json({ ok: true, ...summary(d) });
}

export async function onRequestPost({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const id = new URL(request.url).searchParams.get('id');
  if (!okId(id)) return json({ error: '자료 이름이 올바르지 않습니다.' }, 400);
  const b = await request.json().catch(() => ({}));
  const d = await getJSON(env, KEY(id), null); if (!d) return json({ error: '자료를 찾지 못했습니다.' }, 404);
  const r = d.rows.find(x => x.id === b.row); if (!r) return json({ error: '고칠 줄을 찾지 못했습니다.' }, 404);
  const now = new Date().toISOString();
  if (typeof b.t === 'string' && b.t !== r.t) {
    if (b.t.length > 20000) return json({ error: '글이 너무 깁니다.' }, 400);
    r.hist = [{ t: r.t, at: r.at || '' }, ...(r.hist || [])].slice(0, HIST_MAX);
    r.t = b.t; r.at = now;
  }
  if (typeof b.note === 'string' && b.note !== (r.note || '')) { if (b.note.length > 5000) return json({ error: '메모가 너무 깁니다.' }, 400); r.note = b.note; r.noteAt = now; }
  if (Array.isArray(b.cmDone)) r.cmDone = b.cmDone.filter(x => Number.isInteger(x)).slice(0, 200);
  d.updated = now;
  await putJSON(env, KEY(id), d); await touchIndex(env, d);
  return json({ ok: true, row: r, updated: now });
}
