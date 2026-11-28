# 교정 의견(워드 파일)을 번역 교정 자료 줄마다 붙이는 파일 만들기 (운영자 요청, 2026-11-28)
#   python3 cm_extract.py  (교정안.docx 를 in.docx 로 둔 폴더에서) → cm.json
#   python3 cm_match.py    → m2.json (의견마다 붙일 줄: '현재 표현'을 우리 처음 번역 t0 에서 찾음 —
#                             교정안이 본 원고는 메따·계발·위빠사나로 바뀐 판이라 멧따·개발·위빳사나로 맞춰 찾고,
#                             못 찾으면 둘레 의견들의 자리로 짐작한 곳 ±2500자에서 가장 비슷한 곳)
#   python3 cm_fixen.py   → 정확히 맞지 않은 의견은 영어 원문 인용('원문:')으로 원서 줄을 찾아 자리를 바로잡음
#   python3 cm_make.py <교정안 docx> m2.json → <ID>.cm.json  (번역 교정 '새 자료 넣기'로 올림)
import json, sys, docx, re
src, m2 = sys.argv[1], sys.argv[2]
D = docx.Document(src)
P = [p for p in D.paragraphs]
title = P[0].text.strip()
intro = [P[1].text.strip(), P[2].text.strip(), P[3].text.strip()]
pol = []
on = False
for p in P:
    if p.style.name == 'Heading 1' and p.text.startswith('3부'): on = True; continue
    if on and p.text.strip():
        t = p.text.strip(); m = re.match(r'(.+?)\s{2,}(.+)', t)
        pol.append([m.group(1), m.group(2)] if m else ['', t])
rows = json.load(open('out.trans.json'))['rows']
R = json.load(open(m2))
out = {}
for n, x in enumerate(R, 1):
    it = dict(n=n, g=x['part'], sec=x['sec'], p=x['p'], tag=x['tag'], a=x['a'], b=x['b'], why=x['why'], k=x['k'])
    if x['star']: it['star'] = 1
    if x['en']: it['en'] = x['en']
    if x['r1'] is not None and x['r1'] != x['r0']: it['to'] = rows[x['r1']]['id']
    out.setdefault(rows[x['r0']]['id'], []).append(it)
d = dict(kind='cm', id='how-to-develop-metta', title=title, info=title + ' (워드 파일, 538건)', intro=intro, policy=pol, rows=out)
json.dump(d, open('how-to-develop-metta.cm.json', 'w'), ensure_ascii=False)
print(len(out), 'rows', sum(len(v) for v in out.values()), 'items', len(pol), 'policy')
