// 관리자 열쇠(GitHub 토큰)에 사이트 저장소 '쓰기' 권한이 있는지 확인 (10분 동안 기억)
const REPO = 'dhammapiya3-lab/dhammadana';
const OK = new Map();
export async function canWriteToken(token) {
  if (!token) return false;
  const t = OK.get(token); if (t && Date.now() - t < 10 * 60 * 1000) return true;
  const r = await fetch(`https://api.github.com/repos/${REPO}`, { headers: { authorization: `Bearer ${token}`, 'user-agent': 'dhammadana-admin', accept: 'application/vnd.github+json' } });
  if (!r.ok) return false;
  const j = await r.json();
  const ok = !!(j.permissions && (j.permissions.push || j.permissions.admin));
  if (ok) OK.set(token, Date.now());
  return ok;
}
