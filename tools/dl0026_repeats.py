#!/usr/bin/env python3
"""『테라와다 불교의범』(DL-0026): 같은 줄 묶음이 되풀이되는 문단(예: '그 분, 존귀하신 분…' 두 줄을 세 번)을
묶음마다 따로 문단으로 나눠, 되풀이 사이 간격이 고르게 보이게 한다 (운영자 요청, 2026-11-14).
글자는 그대로 — 묶음 사이에 빈 줄만 넣음. 쓰는 법: python3 tools/dl0026_repeats.py [--write]
그 다음 늘 python3 tools/dl0026_lineys.py 인쇄본.pdf 를 다시 돌린다(문단 번호가 바뀌므로)."""
import json, re, sys
TXT = 'content/texts/DL-0026.json'

def cuts_of(L):
    cuts = set(); k = 0
    while k < len(L):
        hit = None
        for m in (2, 3, 4):
            a = L[k:k + m]
            if len(a) == m and a == L[k + m:k + 2 * m] and len(set(a)) == m and all(x.strip() for x in a):
                hit = m; break
        if not hit: k += 1; continue
        m = hit; j = k
        while L[j:j + m] == L[k:k + m]: j += m
        cuts.update(range(k + m, j, m))
        if j < len(L): cuts.add(j)          # 되풀이가 끝난 뒤 이어지는 글도 따로
        k = j
    return sorted(c for c in cuts if 0 < c < len(L))

def main(write):
    d = json.load(open(TXT)); body = d['body']; out = []; n = 0; report = []
    for seg in re.split(r'(^=== *.*? *===$)', body, flags=re.M):
        if seg.startswith('===') : out.append(seg); continue
        blocks = re.split(r'(\n\s*\n)', seg)
        for i, b in enumerate(blocks):
            if i % 2: continue
            L = b.split('\n'); core = [l.strip() for l in L]
            c = cuts_of(core)
            if c and not core[0].startswith('%%'):
                n += len(c); report.append((core, c))
                parts = []; prev = 0
                for x in c + [len(L)]: parts.append('\n'.join(L[prev:x])); prev = x
                blocks[i] = '\n\n'.join(parts)
        out.append(''.join(blocks))
    nb = ''.join(out)
    assert re.sub(r'\s', '', nb) == re.sub(r'\s', '', body)
    for core, c in report:
        print('---'); [print(('|| ' if k in c else '   ') + l[:60]) for k, l in enumerate(core)]
    print(f'나눈 곳 {n}, 문단 {len(report)}')
    if write: d['body'] = nb; json.dump(d, open(TXT, 'w'), ensure_ascii=False, indent=1)

main('--write' in sys.argv)
