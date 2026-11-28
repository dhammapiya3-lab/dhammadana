// 학습 자료실 '번역 교정' (관리자만): 원서 · 대조 번역본 · 우리 번역을 문장마다 나란히 놓고 우리 번역을 고침.
// 자료는 비공개 창고(MEMBERS)의 _trans/ 아래에만 둔다 — GitHub 에도 공개 주소에도 두지 않음. (운영자 요청, 2026-11-28)
//   GET  /api/trans            → 자료 목록
//   GET  /api/trans?id=…       → 자료 하나(모든 줄)
//   PUT  /api/trans?id=…       → 새 자료 넣기 (이미 있으면 &replace=1 일 때만 바꿈)
//   POST /api/trans?id=…       → 줄 하나 고치기 {row, t?, note?} — 고치기 전 글은 그 줄의 기록(hist)에 남김
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
const summary = d => ({ id: d.id, title: d.title, rows: d.rows.length, edited: d.rows.filter(r => r.t !== r.t0).length, notes: d.rows.filter(r => r.note).length, updated: d.updated || d.made || '', cols: d.cols });
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
  d.updated = now;
  await putJSON(env, KEY(id), d); await touchIndex(env, d);
  return json({ ok: true, row: r, updated: now });
}
