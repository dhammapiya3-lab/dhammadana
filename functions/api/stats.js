import { canWriteToken as canWrite } from './_auth.js';
// 사이트 통계 (관리자만): GET /api/stats?days=30
// 지난 날은 하루치를 묶어 stats/day/<날짜>.json 으로 한 번 정리해 두고, 낱개 기록은 지운다.
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const addDay = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 864e5).toISOString().slice(0, 10);
const inc = (o, k) => { if (k) o[k] = (o[k] || 0) + 1; };

async function rawDay(env, d) {
  const sum = { views: 0, vids: [], pages: {}, titles: {}, refs: {}, dev: {}, ctry: {} }, vs = new Set(), keys = [];
  let cursor;
  do {
    const l = await env.PAPER.list({ prefix: `stats/raw/${d}/`, cursor, limit: 1000 });
    for (let i = 0; i < l.objects.length; i += 50) {
      const part = l.objects.slice(i, i + 50);
      const recs = await Promise.all(part.map(async o => { keys.push(o.key); const x = await env.PAPER.get(o.key); try { return x ? await x.json() : null; } catch (e) { return null; } }));
      for (const r of recs) {
        if (!r) continue;
        sum.views++; if (r.v) vs.add(r.v);
        inc(sum.pages, r.p); if (r.t && r.p) sum.titles[r.p] = r.t;
        inc(sum.refs, r.r); inc(sum.dev, r.d); inc(sum.ctry, r.c);
      }
    }
    cursor = l.truncated ? l.cursor : null;
  } while (cursor);
  sum.vids = [...vs];
  return { sum, keys };
}

async function getDay(env, d, today) {
  if (d < today) {
    const o = await env.PAPER.get(`stats/day/${d}.json`);
    if (o) { try { return await o.json(); } catch (e) {} }
  }
  const { sum, keys } = await rawDay(env, d);
  if (d < today) {
    await env.PAPER.put(`stats/day/${d}.json`, JSON.stringify(sum));
    for (let i = 0; i < keys.length; i += 1000) await env.PAPER.delete(keys.slice(i, i + 1000));
  }
  return sum;
}

export async function onRequestGet({ request, env }) {
  const tok = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!(await canWrite(tok))) return json({ error: '관리자 열쇠가 맞지 않습니다.' }, 401);
  if (!env.PAPER) return json({ ready: false });
  const n = Math.min(Math.max(parseInt(new URL(request.url).searchParams.get('days')) || 30, 1), 366);
  const today = kst(), days = [], all = new Set(), pages = {}, titles = {}, refs = {}, dev = {}, ctry = {};
  const add = (a, b) => { for (const k in b) a[k] = (a[k] || 0) + b[k]; };
  for (let i = n - 1; i >= 0; i--) {
    const d = addDay(today, -i), s = await getDay(env, d, today);
    days.push({ date: d, views: s.views, visitors: s.vids.length });
    s.vids.forEach(v => all.add(v)); add(pages, s.pages); add(refs, s.refs); add(dev, s.dev); add(ctry, s.ctry); Object.assign(titles, s.titles);
  }
  const top = (o, k = 30) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, k);
  return json({ ready: true, today, days, visitors: all.size, views: days.reduce((a, b) => a + b.views, 0),
    pages: top(pages).map(([p, c]) => [p, c, titles[p] || '']), refs: top(refs, 20), dev, ctry: top(ctry, 10) });
}
