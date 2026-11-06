// 학습 자료실 파일 목록 (학습 자료실 전용 창고 MEMBERS)
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8' } });
export async function onRequestGet({ env, data }) {
  if (!env.MEMBERS) return json({ email: data.email, files: [], notReady: true });
  const files = []; let cursor;
  do { const r = await env.MEMBERS.list({ cursor, limit: 1000 }); files.push(...r.objects.map(o => ({ key: o.key, size: o.size, uploaded: o.uploaded }))); cursor = r.truncated ? r.cursor : null; } while (cursor);
  return json({ email: data.email, files });
}
