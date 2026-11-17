#!/usr/bin/env python3
"""『위빠사나 명상』(DL-0012): 쪽을 넘어간 각주 글이 다음 쪽 본문 문단으로 들어가 있던 것을 그 각주 끝으로 되돌림
(운영자 요청, 2026-11-18). 글자는 그대로, 자리만 옮김. dl0012_bullet_join.py 다음에 돌린다.
  python3 tools/dl0012_fn_overflow.py [--write]
M: (각주가 시작한 쪽, 각주 번호, 넘어간 글의 첫머리들(다음 쪽 문단), 각주와 이을 때 빈칸) — 넘어간 문단끼리는 줄 바꿈"""
import json, re, sys
M = [
 (26, '4', ['크리트의 kṛṭṣna', '다른 명상법도 마찬가지이지만', '사마타 명상에 대해서 설명하는'], ''),
 (42, '6', ['기하는 이도 있습니다.'], ''),
 (66, '11', ['(共相; sāmañña-lakkhaṇa)라고'], ''),
 (76, '12', ['④경안(passaddhi)', '⑤행복(sukha)', '⑥확신(adhimokkha)', '⑦정진(paggaha)', '⑧확고한 마음챙김', '⑨평온(upekkhā)', '⑩애착(nikanti)'], '\n'),
 (137, '20', ['다께 비구계를 허락받은'], ''),
 (143, '22', ['입니다. 하지만 이 졸음을'], ''),
 (176, '27', ['시나’를 의식에 가득하게'], ''),
 (185, '28', ['고 생각하고는 침대에'], ''),
]
p = 'content/texts/DL-0012.json'; T = json.load(open(p))
parts = re.split(r'(\n?=== [^\n]*===\n?)', T['body'])
def pidx(n):
    return next(i for i in range(1, len(parts), 2) if re.match(rf'\n?=== {n}쪽 ===', parts[i]))
for pn, fn, heads, sp in M:
    i = pidx(pn); j = i + 2
    paras = re.split(r'(\n\s*\n)', parts[j + 1])
    moved = []
    for h in heads:
        k = [x for x in range(0, len(paras), 2) if paras[x] is not None and paras[x].strip().startswith(h)]
        if len(k) != 1: sys.exit(f'{pn + 1}쪽 {h!r}: {len(k)}곳')
        moved.append(paras[k[0]].strip()); paras[k[0]] = None
        if k[0] + 1 < len(paras): paras[k[0] + 1] = None
        elif k[0] - 1 >= 0: paras[k[0] - 1] = None
    parts[j + 1] = ''.join(x for x in paras if x is not None)
    t = parts[i + 1]
    m = re.search(rf'^\[\^{fn}\]:.*?(?=\n\s*\n|\n\[\^|\Z)', t, flags=re.M | re.S)
    if not m: sys.exit(f'{pn}쪽 각주 {fn} 없음')
    end = m.start() + len(m.group(0).rstrip())
    parts[i + 1] = t[:end] + sp + '\n'.join(moved) + t[end:]
    print(f'{pn}쪽 각주 {fn} ← {pn + 1}쪽 문단 {len(moved)}개')
new = ''.join(parts)
st = lambda s: sorted(re.sub(r'\s', '', s))
assert st(new) == st(T['body']), '글자가 달라짐'
if '--write' in sys.argv:
    T['body'] = new; open(p, 'w').write(json.dumps(T, ensure_ascii=False, indent=2) + '\n'); print('→', p)
