// /study/ 아래는 Cloudflare Access 로 허락받은 사람만 볼 수 있습니다.
import { accessUser } from '../_access.js';
const page = (title, msg, status) => new Response(`<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${title}</title><link rel="stylesheet" href="/assets/site.css"></head><body><div class="wrap prose" style="padding:60px 20px"><h1>${title}</h1>${msg}<p><a href="/">← 법보시 도서관으로</a></p></div></body></html>`, { status, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });

export async function onRequest(ctx) {
  const { request, env, next, data } = ctx;
  const url = new URL(request.url);
  // 문지기는 dhammadana.kr 에만 있으므로, 다른 주소(…pages.dev)로 오면 dhammadana.kr 로 보냅니다.
  if (url.hostname.endsWith('.pages.dev') || url.hostname === 'www.dhammadana.kr') return Response.redirect('https://dhammadana.kr' + url.pathname + url.search, 302);
  if (!env.ACCESS_TEAM || !env.ACCESS_AUD) return page('학습 자료실 준비 중', '<p>학습 자료실은 아직 설정 중입니다.</p>', 503);
  const u = await accessUser(request, env);
  if (!u) return page('들어갈 수 없습니다', '<p>학습 자료실은 허락받은 분만 들어갈 수 있습니다. 허락받은 이메일로 다시 로그인해 주세요.</p><p><a href="/cdn-cgi/access/logout">다시 로그인하기</a></p>', 403);
  data.email = u.email;
  const res = await next();
  const r = new Response(res.body, res);
  r.headers.set('cache-control', 'private, no-store');
  r.headers.set('x-robots-tag', 'noindex');
  return r;
}
