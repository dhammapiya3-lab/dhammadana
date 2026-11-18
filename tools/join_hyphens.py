#!/usr/bin/env python3
"""줄 끝 하이픈 뒤 빈칸 바로잡기 — 목록 tools/hyphen_fixes.json (2026-11-18). 본문을 도구로 다시 만들면 다시 돌림.
원서 대조가 있는 책(DL-0006·DL-0012)은 고친 뒤 tools/parallel/shift.py 로 짝 자료 글자 자리를 옮김.
  python3 tools/join_hyphens.py [--write]"""
import json, re, sys, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(R, 'tools/hyphen_fixes.json')))
for bk, fx in L.items():
    if bk.startswith('_'): continue
    p = os.path.join(R, 'content/texts', bk + '.json'); raw = open(p).read(); d = json.loads(raw); b = d['body']; n = 0
    for a, c in fx:
        k = b.count(a); n += k; b = b.replace(a, c)
        if not k and c not in b: print('  못 찾음', bk, a)
    assert re.sub(r'[\s-]', '', b) == re.sub(r'[\s-]', '', d['body'])
    print(bk, n, '곳 · 빈칸·줄표 말고 글자 같음')
    if '--write' in sys.argv and n:
        ind = len(re.match(r'\{\n( +)"', raw).group(1)); d['body'] = b
        open(p, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else ''))
