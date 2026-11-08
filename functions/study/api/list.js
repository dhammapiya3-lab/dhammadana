// 학습 자료실 파일 목록 + 자료 정보(_catalog.json) (학습 자료실 전용 창고 MEMBERS, 허락받은 분만)
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });
const CAT = '_catalog.json';
export async function onRequestGet({ env, data }) {
  if (!env.MEMBERS) return json({ email: data.email, files: [], catalog: { items: [] }, notReady: true });
  const files = []; let cursor;
  do { const r = await env.MEMBERS.list({ cursor, limit: 1000 }); files.push(...r.objects.filter(o => o.key !== CAT).map(o => ({ key: o.key, size: o.size, uploaded: o.uploaded }))); cursor = r.truncated ? r.cursor : null; } while (cursor);
  let catalog = { items: [] };
  try { const o = await env.MEMBERS.get(CAT); if (o) catalog = await o.json(); } catch (e) {}
  return json({ email: data.email, files, catalog });
}
