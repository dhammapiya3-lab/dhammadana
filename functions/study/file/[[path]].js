// 회원 자료실 파일 열기·내려받기
export async function onRequestGet({ env, params, request }) {
  if (!env.MEMBERS) return new Response('준비 중', { status: 503 });
  const key = (params.path || []).map(decodeURIComponent).join('/');
  const obj = await env.MEMBERS.get(key);
  if (!obj) return new Response('파일이 없습니다.', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
  const h = new Headers(); obj.writeHttpMetadata(h);
  const name = key.split('/').pop();
  const dl = new URL(request.url).searchParams.has('dl');
  h.set('content-disposition', `${dl ? 'attachment' : 'inline'}; filename*=UTF-8''${encodeURIComponent(name)}`);
  h.set('cache-control', 'private, no-store');
  if (obj.size != null) h.set('content-length', String(obj.size));
  return new Response(obj.body, { headers: h });
}
