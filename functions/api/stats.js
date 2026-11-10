import { canWriteToken as canWrite } from './_auth.js';
// 사이트 통계 (관리자만): GET /api/stats?days=30
// 지난 날은 하루치를 묶어 stats/day/<날짜>.json 으로 한 번 정리해 두고, 낱개 기록은 지운다. 오늘 것은 stats/part/<날짜>.json 에 조금씩 모아 둠.
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const addDay = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 864e5).toISOString().slice(0, 10);
const inc = (o, k) => { if (k) o[k] = (o[k] || 0) + 1; };

const empty = () => ({ views: 0, vids: [], pages: {}, titles: {}, refs: {}, dev: {}, ctry: {} });
const getJ = async (env, k) => { const o = await env.PAPER.get(k); if (!o) return null; try { return await o.json(); } catch (e) { return null; } };

// 하루치 낱개 기록을 조금씩(budget 개까지) 읽어 stats/part/<날짜>.json 에 더해 두고 읽은 낱개는 지운다.
// 방문이 많아도 한 번에 너무 많이 읽다가 서버 시간이 넘치지 않게 — 남으면 left>0, 화면이 다시 부름.
async function getDay(env, d, today, B) {
  if (d < today) { const done = await getJ(env, `stats/day/${d}.json`); if (done) return done; }
  const sum = (await getJ(env, `stats/part/${d}.json`)) || empty();
  const vs = new Set(sum.vids), keys = [];
  let cursor, left = false;
  do {
    const l = await env.PAPER.list({ prefix: `stats/raw/${d}/`, cursor, limit: 1000 });
    const take = l.objects.slice(0, Math.max(0, B.n));
    B.n -= take.length;
    for (let i = 0; i < take.length; i += 100) {
      const part = take.slice(i, i + 100);
      const recs = await Promise.all(part.map(async o => { keys.push(o.key); return getJ(env, o.key); }));
      for (const r of recs) {
        if (!r) continue;
        sum.views++; if (r.v) vs.add(r.v);
        inc(sum.pages, r.p); if (r.t && r.p) sum.titles[r.p] = r.t;
        inc(sum.refs, r.r); inc(sum.dev, r.d); inc(sum.ctry, r.c);
      }
    }
    if (take.length < l.objects.length || (l.truncated && B.n <= 0)) { left = true; break; }
    cursor = l.truncated ? l.cursor : null;
  } while (cursor);
  sum.vids = [...vs];
  if (keys.length) {
    await env.PAPER.put(`stats/part/${d}.json`, JSON.stringify(sum));
    for (let i = 0; i < keys.length; i += 1000) await env.PAPER.delete(keys.slice(i, i + 1000));
  }
  if (!left && d < today) {
    await env.PAPER.put(`stats/day/${d}.json`, JSON.stringify(sum));
    await env.PAPER.delete(`stats/part/${d}.json`);
  }
  if (left) B.left = true;
  return sum;
}

export async function onRequestGet({ request, env }) {
  const tok = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!(await canWrite(tok))) return json({ error: '관리자 열쇠가 맞지 않습니다.' }, 401);
  if (!env.PAPER) return json({ ready: false });
  const n = Math.min(Math.max(parseInt(new URL(request.url).searchParams.get('days')) || 30, 1), 366);
  const today = kst(), B = { n: 400, left: false }, days = [], all = new Set(), pages = {}, titles = {}, refs = {}, dev = {}, ctry = {};
  const add = (a, b) => { for (const k in b) a[k] = (a[k] || 0) + b[k]; };
  const ds = []; for (let i = n - 1; i >= 0; i--) ds.push(addDay(today, -i));
  const res = [];
  for (let i = 0; i < ds.length; i += 31) res.push(...await Promise.all(ds.slice(i, i + 31).map(d => getDay(env, d, today, B))));  // 여러 날을 한꺼번에 (1년도 빨리)
  ds.forEach((d, i) => {
    const s = res[i];
    days.push({ date: d, views: s.views, visitors: s.vids.length });
    s.vids.forEach(v => all.add(v)); add(pages, s.pages); add(refs, s.refs); add(dev, s.dev); add(ctry, s.ctry); Object.assign(titles, s.titles);
  });
  const top = (o, k = 30) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, k);
  return json({ ready: true, more: B.left, today, days, visitors: all.size, views: days.reduce((a, b) => a + b.views, 0),
    pages: top(pages).map(([p, c]) => [p, c, titles[p] || '']), refs: top(refs, 20), dev, ctry: top(ctry, 10) });
}
