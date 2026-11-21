#!/usr/bin/env python3
"""『부처님, 그분』(DL-0029) 98쪽 — 각주 76 글 한 줄이 본문으로 들어간 곳을 바로잡음 (2026-11-21, 원서 대조를 만들다 찾음).
 본문 '…살아갈 따름이니 그것이' / (빈 줄) / '의 어원은 라틴어의 castus 純血와 포르투갈어의 casta 血統라고 함. 인승가°°saṅgha°°이다.'
 각주 '[^76]: … 카스트라는 용어도에서는 베다시대 …'
 → 인쇄본 쪽 아래 각주 줄('…용어 / 의 어원은 … 함. 인 / 도에서는 …')이 본문 줄과 섞인 것: 각주 줄 조각을 각주 자리('용어|도에서는' 사이)로,
   본문은 '그것이 승가°°saṅgha°°이다.'로 이음. 글자는 그대로, 자리만 옮김.
  python3 tools/dl0029_fnfix.py [--write]   (pdf2text_dl0029.py 로 본문을 다시 만들면 다시 돌림)"""
import json, re, sys
F = 'content/texts/DL-0029.json'
d = json.load(open(F)); b = d['body']; n = 0
FRAG = '의 어원은 라틴어의 castus 純血와 포르투갈어의 casta 血統라고 함. 인'
m = re.search(r'살아갈 따름이니 그것이\n\n' + re.escape(FRAG) + r'(승가°°saṅgha°°이다\.)', b)
if m and '카스트라는 용어도에서는' in b:
    old = b
    b = b[:m.start()] + '살아갈 따름이니 그것이 ' + m.group(1) + b[m.end():]
    b = b.replace('카스트라는 용어도에서는', '카스트라는 용어' + FRAG + '도에서는', 1)
    assert re.sub(r'\s', '', old) and sorted(re.sub(r'\s', '', old)) == sorted(re.sub(r'\s', '', b))
    n += 1
print('고친 곳', n)
if '--write' in sys.argv and n:
    d['body'] = b
    raw = open(F).read(); ind = 2 if raw.startswith('{\n  ') else (1 if raw.startswith('{\n ') else None)
    open(F, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else ''))
    print('저장함')
