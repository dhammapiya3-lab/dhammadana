import { canWriteToken as canWrite } from './_auth.js';
// 관리자용 책 파일 올리기: 브라우저에서 보낸 PDF·EPUB을 R2(dhammadana-files)에 넣습니다.
// 허락 확인: 관리자 화면에서 쓰는 GitHub 열쇠로 이 사이트 저장소에 '쓰기' 권한이 있는지 GitHub에 물어봅니다.
const KEY_RE = /^(pdf|epub|hwp)\/DL-\d{4}\/[^/\\]{1,120}\.(pdf|epub|hwpx?)$/i;
const READER_RE = /^reader\/DL-\d{4}\/[^/\\]{1,40}\/(manifest\.json|(p|big)\/\d{4}\.webp)$/;
const AUDIO_RE = /^audio\/DL-\d{4}\/\d{2}\.mp3$/;  // 오디오북 장 소리 파일
const okKey = k => KEY_RE.test(k) || READER_RE.test(k) || AUDIO_RE.test(k);
const TYPES = { mp3: 'audio/mpeg', pdf: 'application/pdf', epub: 'application/epub+zip', hwp: 'application/x-hwp', hwpx: 'application/hwp+zip', webp: 'image/webp', json: 'application/json; charset=utf-8' };
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });

export async function onRequestPost({ request, env }) {
  if (!env.FILES) return json({ error: 'R2 저장소가 연결되어 있지 않습니다 (FILES).' }, 500);
  const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!(await canWrite(token))) return json({ error: '허락되지 않았습니다. 관리자 열쇠(GitHub 토큰)를 확인해 주세요.' }, 401);
  let key = '';
  try { key = decodeURIComponent(request.headers.get('x-key') || ''); } catch (e) {}
  if (!okKey(key)) return json({ error: '파일 위치가 올바르지 않습니다: ' + key }, 400);
  const ext = key.split('.').pop().toLowerCase();
  const cache = ext === 'webp' ? 'public, max-age=31536000' : ext === 'json' ? 'public, max-age=300' : 'public, max-age=86400';
  const meta = { httpMetadata: { contentType: TYPES[ext] || 'application/octet-stream', cacheControl: cache } };
  // 큰 파일(100MB 넘음)은 여러 조각으로 나눠 올림: create → part(1,2,…) → complete
  const mp = request.headers.get('x-mp');
  if (mp) {
    try {
      if (mp === 'create') { const u = await env.FILES.createMultipartUpload(key, meta); return json({ ok: true, uploadId: u.uploadId }); }
      const u = env.FILES.resumeMultipartUpload(key, request.headers.get('x-upload-id') || '');
      if (mp === 'part') { const n = parseInt(request.headers.get('x-part')); const p = await u.uploadPart(n, await request.arrayBuffer()); return json({ ok: true, partNumber: p.partNumber, etag: p.etag }); }
      if (mp === 'complete') { const parts = await request.json(); const obj = await u.complete(parts); return json({ ok: true, key, size: obj ? obj.size : null }); }
      if (mp === 'abort') { await u.abort(); return json({ ok: true }); }
    } catch (e) { return json({ error: '나눠 올리기 오류: ' + (e && e.message || e) }, 500); }
    return json({ error: '알 수 없는 요청' }, 400);
  }
  const obj = await env.FILES.put(key, request.body, meta);
  return json({ ok: true, key, size: obj ? obj.size : null });
}

export async function onRequestGet({ request, env }) {
  // 같은 이름 파일이 이미 있는지 확인
  const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!(await canWrite(token))) return json({ error: '허락되지 않았습니다.' }, 401);
  const key = new URL(request.url).searchParams.get('key') || '';
  if (!okKey(key)) return json({ error: '위치 오류' }, 400);
  const h = env.FILES ? await env.FILES.head(key) : null;
  return json({ exists: !!h, size: h ? h.size : 0 });
}
