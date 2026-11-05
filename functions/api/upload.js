// 관리자용 책 파일 올리기: 브라우저에서 보낸 PDF·EPUB을 R2(dhammadana-files)에 넣습니다.
// 허락 확인: 관리자 화면에서 쓰는 GitHub 열쇠로 이 사이트 저장소에 '쓰기' 권한이 있는지 GitHub에 물어봅니다.
const REPO = 'dhammapiya3-lab/dhammadana';
const KEY_RE = /^(pdf|epub)\/DL-\d{4}\/[^/\\]{1,120}\.(pdf|epub)$/i;
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });

async function canWrite(token) {
  if (!token) return false;
  const r = await fetch(`https://api.github.com/repos/${REPO}`, { headers: { authorization: `Bearer ${token}`, 'user-agent': 'dhammadana-upload', accept: 'application/vnd.github+json' } });
  if (!r.ok) return false;
  const j = await r.json();
  return !!(j.permissions && (j.permissions.push || j.permissions.admin));
}

export async function onRequestPost({ request, env }) {
  if (!env.FILES) return json({ error: 'R2 저장소가 연결되어 있지 않습니다 (FILES).' }, 500);
  const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!(await canWrite(token))) return json({ error: '허락되지 않았습니다. 관리자 열쇠(GitHub 토큰)를 확인해 주세요.' }, 401);
  let key = '';
  try { key = decodeURIComponent(request.headers.get('x-key') || ''); } catch (e) {}
  if (!KEY_RE.test(key)) return json({ error: '파일 위치가 올바르지 않습니다: ' + key }, 400);
  const type = key.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'application/epub+zip';
  const obj = await env.FILES.put(key, request.body, { httpMetadata: { contentType: type, cacheControl: 'public, max-age=86400' } });
  return json({ ok: true, key, size: obj ? obj.size : null });
}

export async function onRequestGet({ request, env }) {
  // 같은 이름 파일이 이미 있는지 확인
  const token = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!(await canWrite(token))) return json({ error: '허락되지 않았습니다.' }, 401);
  const key = new URL(request.url).searchParams.get('key') || '';
  if (!KEY_RE.test(key)) return json({ error: '위치 오류' }, 400);
  const h = env.FILES ? await env.FILES.head(key) : null;
  return json({ exists: !!h, size: h ? h.size : 0 });
}
