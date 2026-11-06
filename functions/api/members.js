// 관리자용 학습 자료실 창고(MEMBERS) 관리: 목록 보기, 올리기, 지우기 (관리자 열쇠 필요)
import { canWriteToken } from './_auth.js';
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });
const tokenOf = r => (r.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
const okKey = k => typeof k === 'string' && k.length > 0 && k.length <= 300 && !k.startsWith('/') && !k.endsWith('/') && !k.split('/').some(p => !p || p === '.' || p === '..') && !/[\\\x00-\x1f]/.test(k);
const TYPES = { pdf: 'application/pdf', epub: 'application/epub+zip', mp3: 'audio/mpeg', m4a: 'audio/mp4', mp4: 'video/mp4', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', txt: 'text/plain; charset=utf-8', md: 'text/plain; charset=utf-8', html: 'text/plain; charset=utf-8', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', hwp: 'application/x-hwp', hwpx: 'application/haansofthwp', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', zip: 'application/zip' };

async function guard(request, env) {
  if (!env.MEMBERS) return json({ error: '학습 자료실 전용 창고가 아직 연결되지 않았습니다 (MEMBERS).' }, 503);
  if (!(await canWriteToken(tokenOf(request)))) return json({ error: '허락되지 않았습니다. 관리자 열쇠를 확인해 주세요.' }, 401);
  return null;
}
export async function onRequestGet({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const files = []; let cursor;
  do { const r = await env.MEMBERS.list({ cursor, limit: 1000 }); files.push(...r.objects.map(o => ({ key: o.key, size: o.size, uploaded: o.uploaded }))); cursor = r.truncated ? r.cursor : null; } while (cursor);
  return json({ files });
}
export async function onRequestPut({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  let key = ''; try { key = decodeURIComponent(request.headers.get('x-key') || ''); } catch (e) {}
  key = key.normalize('NFC').trim();
  if (!okKey(key)) return json({ error: '파일 이름이나 폴더 이름이 올바르지 않습니다: ' + key }, 400);
  const ext = key.split('.').pop().toLowerCase();
  const obj = await env.MEMBERS.put(key, request.body, { httpMetadata: { contentType: TYPES[ext] || 'application/octet-stream' } });
  return json({ ok: true, key, size: obj ? obj.size : null });
}
export async function onRequestPost({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const body = await request.json().catch(() => ({}));
  const list = (Array.isArray(body.delete) ? body.delete : []).filter(okKey);
  for (let i = 0; i < list.length; i += 1000) await env.MEMBERS.delete(list.slice(i, i + 1000));
  return json({ ok: true, deleted: list.length });
}
