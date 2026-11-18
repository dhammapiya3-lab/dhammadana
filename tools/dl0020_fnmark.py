#!/usr/bin/env python3
"""『팔정도』(DL-0020) — 각주 번호 [^n] 이 따로 한 문단이 되어 문장·낱말을 가른 곳 23곳을
인쇄본 자리로 되돌림 (운영자 요청, 2026-11-18, 인쇄본 PDF 로 확인).
인쇄본에서 각주 번호는 모두 '다음 문단'의 첫 줄 끝(오른쪽)에 찍혀 있음 → 그 줄 끝에 [^n] 을 붙이고,
앞 문단과 다음 문단은 한 문단으로 이음(앞 줄 끝에 빈칸이 있으면 빈칸, 낱말 가운데면 빈칸 없이).
번호 목록(47쪽 13, 115쪽 38)·쪽 첫머리(36쪽 7)는 문단을 잇지 않음. 글자는 그대로.
  python3 tools/dl0020_fnmark.py [--write]   (pdf2text_dl0020.py 로 본문을 다시 만들면 다시 돌림)"""
import json, re, sys, collections
F = 'content/texts/DL-0020.json'
# 각주 번호: (인쇄본에서 번호가 찍힌 줄의 끝 글자, 앞 문단과 이을 때 사이 글자 / None = 잇지 않음)
FIX = {5: ('말씀하셨다.', ' '), 6: ('이끄는 길이다.', ' '), 7: ('발견하게 된다.', None),
       13: ('5. 말전주[兩舌]', None), 15: ('볼 수 있게 된다.', ' '), 22: ('간명하게 요약하신다.', ' '),
       24: ('고통도 없다.', ''), 38: ('고객을 속이는 것.', None), 40: ('루고 있다.', ''),
       41: ('말씀하신다.', ' '), 43: ('따 모은다.', ''), 52: ('하는 것이다.', ''),
       54: ('깨달음의 인자들이다.', ''), 65: ('수행들이 있다.', ''), 66: ('는 것', ''),
       69: ('것일 뿐이다.', ''), 70: ('존재하지 않는다.', ' '), 71: ('기능이 포함된다.', ''),
       74: ('고 있어야 한다.', ''), 77: ('결정해야 한다.', ''), 80: ('기능을 한다.', ''),
       86: ('사라지는지를 안다.', ' '), 89: ('비유된다.', ' ')}
d = json.load(open(F)); body = d['body']
parts = re.split(r'(\n*=== [^=\n]* ===\n*)', body)
done = set()
for k, x in enumerate(parts):
    if x.lstrip('\n').startswith('==='): continue
    pa = x.split('\n\n'); i = 0
    while i < len(pa):
        m = re.fullmatch(r'\s*\[\^(\d+)\]\s*', pa[i])
        if m and int(m.group(1)) in FIX:
            n = int(m.group(1)); end, sep = FIX[n]
            nx = pa[i + 1]; j = nx.find(end)
            assert j >= 0, (n, nx[:40])
            nx = nx[:j + len(end)] + f'[^{n}]' + nx[j + len(end):]
            if sep is None: pa[i:i + 2] = [nx]
            else: pa[i - 1:i + 2] = [pa[i - 1].rstrip() + sep + nx.lstrip()]; i -= 1
            done.add(n)
        i += 1
    parts[k] = '\n\n'.join(pa)
new = ''.join(parts)
assert done == set(FIX), set(FIX) - done
c = lambda s: collections.Counter(re.sub(r'\s', '', s))
assert c(new) == c(body), '글자가 달라짐'
print('고친 곳', len(done))
if '--write' in sys.argv:
    d['body'] = new
    raw = open(F).read(); ind = 2 if raw.startswith('{\n  ') else None
    open(F, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else ''))
    print('저장함')
