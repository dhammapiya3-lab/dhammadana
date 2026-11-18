#!/usr/bin/env python3
"""『빠릿따 독송예경문』(DL-0032) 미주 안의 '1) 2) 3)' 항목이 미주 풀이 [^1]: [^2]: 로 잘못 들어간 곳 되돌리기 (2026-11-18 다시 검수).
미주 번호는 차례로 늘어나므로, 미주 구역에서 앞 미주 번호보다 작은 [^N]: 은 그 미주 안의 'N) ' 항목 — 빈 줄을 빼고 줄 바꿈으로 앞 미주에 이음.
(317쪽 미주 15 의 1) 유여닙바나·2) 무여닙바나, 324~325쪽 상카라 미주의 1)~4)·1)~3), 330쪽 미주 56 '1) 일을 잘 처리하고' 등)
글자는 '[^N]: ' → 'N) ' 만 바꿈. 본문을 다시 만들면 dl0032_endnotes.py 다음에 돌림.
  python3 tools/dl0032_subitems.py [--write]"""
import json, re, sys, os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content/texts/DL-0032.json')
raw = open(P).read(); d = json.loads(raw); b = d['body']
st = b.find('[^1]:')          # 미주 구역 시작(첫 미주)
last = 0; out = []; pos = 0; n = 0
for m in re.finditer(r'(?m)^[ \t]*\[\^(\d+)\]:[ \t]*', b):
    if m.start() < st: continue
    k = int(m.group(1))
    if k >= last: last = k; continue
    # 앞 빈 줄들(쪽 표시가 끼어 있으면 그대로 둠)을 줄 바꿈 하나로
    s = m.start(); pre = b[pos:s]
    if re.search(r'\n[ \t]*\n[ \t]*$', pre) and not re.search(r'===[^\n]*===\s*$', pre): pre = re.sub(r'\n[ \t]*\n[ \t]*$', '\n', pre)
    out.append(pre + f'{k}) '); pos = m.end(); n += 1
out.append(b[pos:]); b2 = ''.join(out)
# 쪽 표시 바로 뒤에 온 항목('=== 325쪽 ===' 다음 '4) …')은 앞 미주 끝으로 옮김 — 미주는 쪽이 넘어가도 이어 줌
def mv(m):
    global n2; n2 += 1; return m.group(1) + '\n' + m.group(3) + '\n\n' + m.group(2) + '\n'
n2 = 0
b2 = b2[:st] + re.sub(r'([^\n])\n[ \t]*\n(=== [^\n]*===)[ \t]*\n[\s]*(\d\) [^\n]*(?:\n(?![ \t]*\n)[^\n]*)*)', mv, b2[st:])
print('쪽을 넘어 앞 미주로 옮긴 항목', n2)
strip = lambda t: re.sub(r'\s+|\[\^\d+\]:|\d+\)|=== [^\n]*===', '', t)
assert re.findall(r'=== [^\n]*===', b) == re.findall(r'=== [^\n]*===', b2)
assert strip(b) == strip(b2)
print(f'되돌린 곳 {n} · 글자 대조: 같음')
if '-v' in sys.argv:
    for m in re.finditer(r'(?m)^\d\) [^\n]{0,50}', b2[st:]): print('  ', m.group())
if '--write' in sys.argv:
    ind = len(re.match(r'\{\n( +)"', raw).group(1)); d['body'] = b2
    open(P, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else '')); print('썼습니다')
