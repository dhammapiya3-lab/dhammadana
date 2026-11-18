#!/usr/bin/env python3
"""『빨리어 예경독송집』(DL-0031) 소제목으로 잘못 잡힌 줄 바로잡기 (운영자 요청 '다시 검수해줘', 2026-11-18).
① 독송 묶음(한글 소리 줄 / 로마자 줄 / 번역 줄)의 첫 소리 줄이 T1 색 글씨라 '## ' 소제목이 되어 로마자 줄과 떨어진 19곳
   → '## ' 를 빼고 다음 로마자 줄과 한 묶음(한 문단)으로.
③ 독송 묶음의 마지막 번역 줄이 소제목이 된 12곳 → '## ' 를 빼고 앞 로마자 줄에 이음 (2회차 검수).
② 635쪽 '❖ 포살에는 …(포살 팔계)’에 / ## 대해 숙고한다. (…)' — 문장 중간에서 끊겨 뒷줄이 소제목이 된 곳 → 앞 문단에 이어 붙임.
글자는 바꾸지 않고 '## ' 표시와 빈 줄만 고친다(고친 뒤 빈칸·표시를 뺀 글자가 같은지 대조).
  python3 tools/dl0031_headfix.py [--write]     (pdf2text_dl0031.py 로 본문을 다시 만들면 다시 돌림)"""
import json, re, sys, os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content/texts/DL-0031.json')
raw = open(P).read(); ind = len(re.match(r'\{\n( +)"', raw).group(1)); d = json.loads(raw); b = d['body']
n1 = len(re.findall(r'(?m)^## [^\n]+\n\n(?=[“‘"\']?[a-zāīūṃṁṅñṭḍṇḷ])', b))
b2 = re.sub(r'(?m)^## ([^\n]+)\n\n(?=[“‘"\']?[a-zāīūṃṁṅñṭḍṇḷ])', r'\1\n', b)
# ③ 묶음의 마지막 번역 줄이 소제목이 되어 로마자 줄 뒤에 떨어진 12곳('## 세존 아라한 정등각 부처님께 예경드립니다. (3번)', 대념처경 반복부 '## 이와 같이 안으로... 몸에서 몸을 관찰하며 머문다.' 등)
R3 = r'(?m)^((?:[^\n]*\n)?[“‘(]?[a-zāīūṃṁṅñṭḍṇḷ][^\n]*[a-zāīūṃṁṅñṭḍṇḷ][.,;!?’”]*)\n\n## ([가-힣][^\n]*)$'
n3 = len(re.findall(R3, b2)); b2 = re.sub(R3, r'\1\n\2', b2)
OLD = '‘아라한의 덕성(포살 팔계)’에\n\n## 대해 숙고한다.'
n2 = b2.count(OLD); b2 = b2.replace(OLD, '‘아라한의 덕성(포살 팔계)’에 대해 숙고한다.')
strip = lambda s: re.sub(r'\s+|^#+ ', '', re.sub(r'(?m)^## ', '', s))
assert strip(b) == strip(b2), '글자가 달라짐'
print(f'① 독송 소리 줄 소제목 → 묶음 {n1}곳, ② 끊긴 문장 {n2}곳, ③ 번역 줄 소제목 → 묶음 {n3}곳 · 글자 대조: 같음')
if '--write' in sys.argv:
    d['body'] = b2; open(P, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else ''))
    print('썼습니다:', P)
