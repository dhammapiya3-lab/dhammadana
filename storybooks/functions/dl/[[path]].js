// 내려받기: /dl/<책>/<이야기>/NN.jpg (그림 한 장), /dl/<책>/<이야기>.pdf|.zip, /dl/<책>/_book.pdf|_book_s.pdf|_book.zip
// ?n= 로 받을 파일 이름(한글)을 정함. R2 'dhammadana-files' 의 storybooks/ 아래만 꺼냄.
const TYPES = { jpg: 'image/jpeg', pdf: 'application/pdf', zip: 'application/zip' };
export async function onRequestGet({ request, env, params }) {
  const p = (params.path || []).join('/');
  let key;
  if (/^[\w.-]+\/[\w.-]+\/\d{2}\.jpg$/.test(p)) { const [b, s, f] = p.split('/'); key = `storybooks/${b}/${s}/big/${f}`; }
  else if (/^[\w.-]+\/[\w.-]+\.(pdf|zip)$/.test(p)) key = `storybooks/dl/${p}`;
  else return new Response('찾는 파일이 없습니다.', { status: 404 });
  const obj = await env.FILES.get(key);
  if (!obj) return new Response('아직 준비되지 않은 파일입니다. 잠시 뒤에 다시 해 주세요.', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
  const ext = key.split('.').pop();
  let name = (new URL(request.url).searchParams.get('n') || p.split('/').pop()).replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').slice(0, 150);
  if (!name.toLowerCase().endsWith('.' + ext)) name += '.' + ext;
  const ascii = name.replace(/[^\x20-\x7e]/g, '_');
  return new Response(obj.body, { headers: {
    'content-type': TYPES[ext], 'content-length': String(obj.size),
    'content-disposition': `attachment; filename="${ascii}"; filename*=UTF-8''${encodeURIComponent(name)}`,
    'cache-control': 'public, max-age=600', etag: obj.httpEtag } });
}
