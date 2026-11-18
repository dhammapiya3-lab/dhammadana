#!/usr/bin/env python3
"""『법구경 : 하루를 살더라도』(DL-0021) 부록에서 문단 첫 줄만 소제목(## )이 된 곳 바로잡기 (운영자 요청 '다시 검수해줘', 2026-11-18).
인쇄본 한 줄을 꽉 채운 문단 첫 줄이 큰 글씨로 잘못 읽혀 '## ' 소제목이 되고, 나머지 줄은 다음 문단(또는 다음 쪽 첫 문단)으로 떨어져 있었다.
 · 485쪽 오하분결·오상분결, 493~497쪽 12연기 (3)~(12)·24조건 (1)~(24) 풀이 → '## ' 를 빼고 한 문단으로 이음
   (같은 꼴인 (1) 무명·(2) 형성은 처음부터 보통 문단). 다음 쪽으로 넘어간 나머지 글은 앞 쪽 문단 끝으로 옮김(쪽이 넘어가는 문단은 앞 쪽에).
 · 498쪽 '몸의 선행'·'말의 선행' 두 줄로 나뉜 소제목 → 소제목 한 줄로 (몸·말·마음의 악행 소제목과 같은 모양)
이을 때 인쇄본 줄 끝이 낱말 가운데면 빈칸 없이, 낱말 사이면 빈칸 하나 — 낱말마다 확인한 목록 SPACE.
글자는 바꾸지 않는다('## '·빈 줄·빈칸만) — 고친 뒤 대조.
  python3 tools/dl0021_headjoin.py [--write]   (pdf2text_dl0021.py·dl0021_revise.py 로 본문을 다시 만들면 그 다음에 다시 돌림)"""
import json, re, sys, os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content/texts/DL-0021.json')
raw = open(P).read(); ind = len(re.match(r'\{\n( +)"', raw).group(1)); d = json.loads(raw); b = d['body']
# 줄 끝(소제목 끝 글자열) → 낱말 사이라 빈칸을 넣는 곳
SPACE = ('물질인', '괴롭지도', '세간의', '그 사이에', '조건 따라', '생길', '설득력', '대상을', '들뜸,', '않음,')
HEAD = re.compile(r'^## ((?:\(\d+\) [^:\n]+ : |오[하상]분결\([^)]*\): )[^\n]*)$')
pages = re.split(r'(\n?=== [^\n]*===\n?)', b)
n = 0
for i in range(0, len(pages), 2):
    m = re.match(r'\n?=== (\d+)쪽', pages[i - 1]) if i else None
    if not m or not (485 <= int(m.group(1)) <= 498): continue
    paras = pages[i].split('\n\n')
    k = 0
    while k < len(paras):
        p = paras[k]; h = HEAD.match(p.strip())
        sel = p.strip().startswith(('## 몸의 선행:', '## 말의 선행:'))
        if h or sel:
            nxt_here = k + 1 < len(paras) and paras[k + 1].strip() and not paras[k + 1].lstrip().startswith(('#', '[^', '!['))
            head = p.strip()[3:] if h else p.strip()
            if nxt_here:
                cont = paras[k + 1].strip(); del paras[k + 1]
            elif k == len(paras) - 1 or all(not x.strip() or x.lstrip().startswith('[^') for x in paras[k + 1:]):
                # 나머지 글이 다음 쪽 첫 문단으로 넘어감 → 그 문단을 이 쪽으로 가져옴
                np = pages[i + 2].split('\n\n'); j = next(t for t, x in enumerate(np) if x.strip())
                cont = np[j].strip(); del np[j]; pages[i + 2] = '\n\n'.join(np)
            elif h:
                paras[k] = head; n += 1; k += 1; continue   # 한 줄로 끝난 풀이 '(5) 빈틈없는 조건 : …' 도 보통 문단으로
            else: k += 1; continue
            sep = ' ' if head.rstrip().endswith(SPACE) else ''
            paras[k] = head.rstrip() + sep + cont; n += 1
        k += 1
    pages[i] = '\n\n'.join(paras)
b2 = ''.join(pages)
strip = lambda s: re.sub(r'\s+', '', re.sub(r'=== [^\n]*===', '', re.sub(r'(?m)^## ', '', s)))
assert re.findall(r'=== [^\n]*===', b) == re.findall(r'=== [^\n]*===', b2), '쪽 표시가 달라짐'
if strip(b) != strip(b2):
    import difflib; x,y=strip(b),strip(b2); i=next(t for t in range(min(len(x),len(y))) if x[t]!=y[t]); print(x[i-60:i+60]); print(y[i-60:i+60]); sys.exit(1)
print(f'이은 곳 {n} · 글자 대조: 같음')
if '-v' in sys.argv:
    for m in re.finditer(r'(?m)^(\(\d+\) [^:\n]+ : |오[하상]분결|## [몸말]의 선행)[^\n]*$', b2): print('  ', m.group()[:90])
if '--write' in sys.argv:
    d['body'] = b2; open(P, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else '')); print('썼습니다')
