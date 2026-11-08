// 방문 기록 (사이트 통계) — 이름·IP·이메일 같은 개인정보는 저장하지 않는다.
// 저장: R2 'PAPER' 창고(공개 주소 없음)의 stats/raw/<날짜>/<시각>-<무작위>.json — 한 번 볼 때마다 작은 파일 하나
//   { p: 주소, t: 쪽 제목, r: 들어온 곳(사이트 이름만), v: 기기마다 무작위로 만든 번호, d: 휴대폰/컴퓨터, c: 나라 }
// 관리자(이 기기는 통계에서 빼기를 켠 기기)의 방문은 브라우저에서 아예 보내지 않는다.
const BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|kakaotalk-scrap|yeti|daum|python|curl|wget/i;
const day = () => new Date(Date.now() + 9 * 3600e3).toISOString();  // 한국 시간
const cut = (s, n) => String(s ?? '').replace(/[\u0000-\u001f]/g, '').slice(0, n);

export async function onRequestPost({ request, env }) {
  const ok = new Response(null, { status: 204 });
  if (!env.PAPER) return ok;
  const ua = request.headers.get('user-agent') || '';
  if (!ua || BOT.test(ua)) return ok;
  let b = {};
  try { b = JSON.parse(await request.text()); } catch (e) { return ok; }
  const p = cut(b.p, 200);
  if (!p.startsWith('/') || /^\/(admin|api)\b/.test(p)) return ok;
  let r = '';
  try { if (b.r) { const h = new URL(b.r).hostname.replace(/^www\./, ''); if (h && h !== 'dhammadana.kr' && !h.endsWith('.dhammadana.pages.dev')) r = h; } } catch (e) {}
  const v = /^[0-9a-z]{8,24}$/.test(b.v || '') ? b.v : '';
  const rec = { p, t: cut(b.t, 120), r, v, d: /Mobi|Android|iPhone|iPad/i.test(ua) ? 'm' : 'pc', c: (request.cf && request.cf.country) || '' };
  const now = day(), rnd = [...crypto.getRandomValues(new Uint8Array(4))].map(x => x.toString(16).padStart(2, '0')).join('');
  await env.PAPER.put(`stats/raw/${now.slice(0, 10)}/${now.slice(11, 19).replace(/:/g, '')}-${rnd}.json`, JSON.stringify(rec));
  return ok;
}
