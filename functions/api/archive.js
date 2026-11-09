// 아카이빙 자료실 (운영자 요청, 2026-11-10): 관리자만 들어가는 비공개 자료 창고.
// 파일은 공개 주소가 없는 R2 창고(PAPER, dhammadana-paper)의 archive/ 아래에만 둡니다 — 인터넷 주소로는 열리지 않고,
// 관리자 열쇠(사이트 저장소에 쓰기 권한이 있는 GitHub 토큰)를 보낸 요청에만 목록·파일을 돌려줍니다.
import { canWriteToken } from './_auth.js';
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const tokenOf = r => (r.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
const P = 'archive/', CAT = '_catalog.json';
const okKey = k => typeof k === 'string' && k.length > 0 && k.length <= 300 && !k.startsWith('/') && !k.endsWith('/') && !k.split('/').some(p => !p || p === '.' || p === '..') && !/[\\\x00-\x1f]/.test(k);
const TYPES = { pdf: 'application/pdf', epub: 'application/epub+zip', mp3: 'audio/mpeg', m4a: 'audio/mp4', wav: 'audio/wav', mp4: 'video/mp4', mov: 'video/quicktime', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', gif: 'image/gif', webp: 'image/webp', txt: 'text/plain; charset=utf-8', md: 'text/plain; charset=utf-8', csv: 'text/csv; charset=utf-8', json: 'application/json; charset=utf-8', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', hwp: 'application/x-hwp', hwpx: 'application/haansofthwp', xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', zip: 'application/zip' };
const typeOf = k => TYPES[k.split('.').pop().toLowerCase()] || 'application/octet-stream';

async function guard(request, env) {
  if (!env.PAPER) return json({ error: '비공개 창고가 연결되어 있지 않습니다 (PAPER).' }, 503);
  if (!(await canWriteToken(tokenOf(request)))) return json({ error: '허락되지 않았습니다. 관리자 열쇠를 확인해 주세요.' }, 401);
  return null;
}
const keyOf = request => { let k = ''; try { k = decodeURIComponent(request.headers.get('x-key') || ''); } catch (e) {} return k.normalize('NFC').trim(); };

export async function onRequestGet({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const u = new URL(request.url), get = (u.searchParams.get('get') || '').normalize('NFC');
  if (get) {  // 파일 하나 받기 (열기·내려받기)
    if (!okKey(get) || get === CAT) return json({ error: '파일 이름이 올바르지 않습니다.' }, 400);
    const o = await env.PAPER.get(P + get); if (!o) return json({ error: '파일이 없습니다.' }, 404);
    const name = get.split('/').pop();
    return new Response(o.body, { headers: { 'content-type': typeOf(get), 'content-length': String(o.size), 'cache-control': 'no-store', 'x-content-type-options': 'nosniff',
      'content-disposition': `${u.searchParams.get('dl') ? 'attachment' : 'inline'}; filename*=UTF-8''${encodeURIComponent(name)}` } });
  }
  const files = []; let cursor;
  do { const r = await env.PAPER.list({ prefix: P, cursor, limit: 1000 }); files.push(...r.objects.map(o => ({ key: o.key.slice(P.length), size: o.size, uploaded: o.uploaded })).filter(f => f.key !== CAT)); cursor = r.truncated ? r.cursor : null; } while (cursor);
  let catalog = { items: {} };
  try { const o = await env.PAPER.get(P + CAT); if (o) catalog = await o.json(); } catch (e) {}
  return json({ files, catalog });
}

export async function onRequestPut({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const key = keyOf(request);
  if (!okKey(key)) return json({ error: '파일 이름이나 폴더 이름이 올바르지 않습니다: ' + key }, 400);
  if (key === CAT) {
    const txt = await request.text(); let j;
    try { j = JSON.parse(txt); } catch (e) { return json({ error: '자료 정보 형식이 올바르지 않습니다.' }, 400); }
    if (!j || typeof j.items !== 'object' || txt.length > 2000000) return json({ error: '자료 정보 형식이 올바르지 않습니다.' }, 400);
    await env.PAPER.put(P + CAT, txt, { httpMetadata: { contentType: 'application/json; charset=utf-8' } });
    return json({ ok: true });
  }
  const meta = { httpMetadata: { contentType: typeOf(key) } };
  // 큰 파일(90MB 넘음)은 나눠 올림: create → part(1,2,…) → complete
  const mp = request.headers.get('x-mp');
  if (mp) {
    try {
      if (mp === 'create') { const m = await env.PAPER.createMultipartUpload(P + key, meta); return json({ ok: true, uploadId: m.uploadId }); }
      const m = env.PAPER.resumeMultipartUpload(P + key, request.headers.get('x-upload-id') || '');
      if (mp === 'part') { const p = await m.uploadPart(parseInt(request.headers.get('x-part')), await request.arrayBuffer()); return json({ ok: true, partNumber: p.partNumber, etag: p.etag }); }
      if (mp === 'complete') { const o = await m.complete(await request.json()); return json({ ok: true, key, size: o ? o.size : null }); }
      if (mp === 'abort') { await m.abort(); return json({ ok: true }); }
    } catch (e) { return json({ error: '나눠 올리기 오류: ' + (e && e.message || e) }, 500); }
    return json({ error: '알 수 없는 요청' }, 400);
  }
  const o = await env.PAPER.put(P + key, request.body, meta);
  return json({ ok: true, key, size: o ? o.size : null });
}

// 지우기 {delete:[…]} · 옮기기(이름 바꾸기) {move:[[옛 이름, 새 이름], …]}
export async function onRequestPost({ request, env }) {
  const g = await guard(request, env); if (g) return g;
  const body = await request.json().catch(() => ({}));
  if (Array.isArray(body.move)) {
    let n = 0;
    for (const [a, b] of body.move) {
      if (!okKey(a) || !okKey(b) || a === CAT || b === CAT || a === b) continue;
      if (await env.PAPER.head(P + b)) return json({ error: '같은 이름의 파일이 이미 있습니다: ' + b }, 409);
      const o = await env.PAPER.get(P + a); if (!o) continue;
      await env.PAPER.put(P + b, o.body, { httpMetadata: { contentType: typeOf(b) } });
      await env.PAPER.delete(P + a); n++;
    }
    return json({ ok: true, moved: n });
  }
  const list = (Array.isArray(body.delete) ? body.delete : []).filter(okKey).filter(k => k !== CAT).map(k => P + k);
  for (let i = 0; i < list.length; i += 1000) await env.PAPER.delete(list.slice(i, i + 1000));
  return json({ ok: true, deleted: list.length });
}
