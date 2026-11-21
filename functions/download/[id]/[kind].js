// 책 파일 내려받기: R2에서 꺼내 '책제목_날짜.pdf' 같은 이름으로 내려줍니다.
export async function onRequestGet({ params, env, request }) {
  const id = String(params.id || ''), kind = String(params.kind || '');
  if (!/^DL-\d{4}$/.test(id) || !['pdf', 'pdf_print', 'pdf_cover', 'epub'].includes(kind)) return new Response('잘못된 주소입니다.', { status: 404 });
  const map = await (await env.ASSETS.fetch(new URL('/data/downloads.json', request.url))).json().catch(() => ({}));
  const d = map[id] && map[id][kind];
  if (!d || !env.FILES) return new Response('파일을 찾을 수 없습니다.', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
  const obj = await env.FILES.get(d.key);
  if (!obj) return new Response('파일을 찾을 수 없습니다.', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
  const ascii = d.name.replace(/[^\x20-\x7e]/g, '_').replace(/"/g, '');
  return new Response(obj.body, {
    headers: {
      'content-type': kind === 'epub' ? 'application/epub+zip' : 'application/pdf',
      'content-length': String(obj.size),
      'content-disposition': `attachment; filename="${ascii}"; filename*=UTF-8''${encodeURIComponent(d.name)}`,
      'cache-control': 'public, max-age=3600'
    }
  });
}
