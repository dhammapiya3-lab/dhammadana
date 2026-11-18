#!/usr/bin/env python3
"""『빨리어 예불과 의례집』(DL-0027) 빈 각주 2곳을 인쇄본대로 채움 (운영자 요청, 2026-11-18 — 인쇄본 PDF 로 확인).
 · 각주 7(32쪽, PDF 46쪽): 각주 글 '여성(Female): dāsī 다˞시˞'(인쇄본)이 기울임 본문 문단 '°°여성(Female): dāsī다˞시˞°°'으로 들어가 있던 것 → 각주 안으로 옮김(글자는 그대로, 인쇄본처럼 dāsī 뒤 빈칸).
 · 각주 30(188쪽, PDF 212쪽): 각주 글 '* 혼자일 때엔, …'이 본문 문단으로 들어가 있던 것 → 각주 안으로 옮김(글자는 그대로).
  python3 tools/dl0027_fnfix.py [--write]   (pdf2text_dl0027.py 로 본문을 다시 만들면 다시 돌림)"""
import json, re, sys
F = 'content/texts/DL-0027.json'
d = json.load(open(F)); b = d['body']; n = 0
m = re.search(r'\n\n°°여성\(Female\): dāsī다˞시˞°°\n\n\[\^7\]:[ \t]*\n', b)
if m:
    b = b[:m.start()] + '\n\n[^7]: 여성(Female): dāsī 다˞시˞\n' + b[m.end():]; n += 1
m = re.search(r'\n\n(\* 혼자일 때엔, 야차미\(yācāmi\) , 두명 이상일 때 야차마\(yācāma\))\n\n\[\^30\]:[ \t]*(?=\n|$)', b)
if m:
    b = b[:m.start()] + '\n\n[^30]: ' + m.group(1) + b[m.end():]; n += 1
print('고친 곳', n)
if '--write' in sys.argv and n:
    d['body'] = b
    raw = open(F).read(); ind = 2 if raw.startswith('{\n  ') else (1 if raw.startswith('{\n ') else None)
    open(F, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind) + ('\n' if raw.endswith('\n') else ''))
    print('저장함')
