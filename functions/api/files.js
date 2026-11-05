// 관리자용 창고(R2) 정리: 책별 파일 목록 보기와 지우기
import { canWriteToken } from './_auth.js';
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });
const tokenOf = r => (r.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
const ID_RE = /^DL-\d{4}$/;

async function listAll(env, prefix) {
  const out = []; let cursor;
  do { const r = await env.FILES.list({ prefix, cursor, limit: 1000 }); out.push(...r.objects.map(o => ({ key: o.key, size: o.size }))); cursor = r.truncated ? r.cursor : null; } while (cursor);
  return out;
}

// GET /api/files?book=DL-0007 → 그 책의 파일을 묶음(판 폴더·파일)별로
export async function onRequestGet({ request, env }) {
  if (!(await canWriteToken(tokenOf(request)))) return json({ error: '허락되지 않았습니다.' }, 401);
  const id = new URL(request.url).searchParams.get('book') || '';
  if (!ID_RE.test(id)) return json({ error: '책 번호 오류' }, 400);
  const groups = {};
  for (const top of ['reader', 'pdf', 'epub']) {
    for (const o of await listAll(env, `${top}/${id}/`)) {
      const rest = o.key.slice(top.length + id.length + 2);
      const g = top === 'reader' ? `reader/${id}/${rest.split('/')[0]}/` : o.key;
      (groups[g] = groups[g] || { prefix: g, count: 0, size: 0 }).count++; groups[g].size += o.size;
    }
  }
  return json({ groups: Object.values(groups) });
}

// POST /api/files {delete: [prefix 또는 key]} → 지우기
export async function onRequestPost({ request, env }) {
  if (!(await canWriteToken(tokenOf(request)))) return json({ error: '허락되지 않았습니다.' }, 401);
  const body = await request.json().catch(() => ({}));
  const list = Array.isArray(body.delete) ? body.delete : [];
  let n = 0;
  for (const p of list) {
    if (!/^(reader|pdf|epub)\/DL-\d{4}\/./.test(p)) return json({ error: '지울 수 없는 위치: ' + p }, 400);
    const keys = p.endsWith('/') ? (await listAll(env, p)).map(o => o.key) : [p];
    for (let i = 0; i < keys.length; i += 1000) { await env.FILES.delete(keys.slice(i, i + 1000)); }
    n += keys.length;
  }
  return json({ ok: true, deleted: n });
}
