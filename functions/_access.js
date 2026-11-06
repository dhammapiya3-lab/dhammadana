// 회원 자료실 문지기: Cloudflare Access 가 붙여 주는 출입증(JWT)이 진짜인지 확인합니다.
// 설정값(Cloudflare Pages → 설정 → 변수): ACCESS_TEAM (예: dhammadana.cloudflareaccess.com), ACCESS_AUD (애플리케이션 AUD 태그)
const KEYS = { at: 0, team: '', list: [] };
const b64u = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(s.length / 4) * 4, '=')), c => c.charCodeAt(0));
const teamOf = env => String(env.ACCESS_TEAM || '').replace(/^https?:\/\//, '').replace(/\/.*$/, '');

async function certs(team) {
  if (KEYS.team === team && Date.now() - KEYS.at < 60 * 60 * 1000 && KEYS.list.length) return KEYS.list;
  const r = await fetch(`https://${team}/cdn-cgi/access/certs`);
  if (!r.ok) throw new Error('certs ' + r.status);
  const j = await r.json();
  KEYS.list = await Promise.all((j.keys || []).map(async k => ({ kid: k.kid, key: await crypto.subtle.importKey('jwk', k, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']) })));
  KEYS.at = Date.now(); KEYS.team = team;
  return KEYS.list;
}
function tokenOf(request) {
  const h = request.headers.get('cf-access-jwt-assertion'); if (h) return h;
  const m = (request.headers.get('cookie') || '').match(/(?:^|;\s*)CF_Authorization=([^;]+)/); return m ? m[1] : '';
}
// 확인되면 { email } 을, 아니면 null 을 돌려줍니다.
export async function accessUser(request, env) {
  const team = teamOf(env), aud = String(env.ACCESS_AUD || '').trim();
  if (!team || !aud) return null;
  const t = tokenOf(request); const parts = t.split('.');
  if (parts.length !== 3) return null;
  try {
    const head = JSON.parse(new TextDecoder().decode(b64u(parts[0])));
    const body = JSON.parse(new TextDecoder().decode(b64u(parts[1])));
    if (head.alg !== 'RS256') return null;
    const auds = Array.isArray(body.aud) ? body.aud : [body.aud];
    if (!auds.includes(aud)) return null;
    if (body.iss !== `https://${team}`) return null;
    const now = Date.now() / 1000;
    if (!body.exp || body.exp < now || (body.nbf && body.nbf > now + 60)) return null;
    const list = await certs(team);
    const cand = list.filter(k => !head.kid || k.kid === head.kid);
    const data = new TextEncoder().encode(parts[0] + '.' + parts[1]), sig = b64u(parts[2]);
    for (const k of cand) if (await crypto.subtle.verify('RSASSA-PKCS1-v1_5', k.key, sig, data)) return { email: body.email || '' };
  } catch (e) {}
  return null;
}
