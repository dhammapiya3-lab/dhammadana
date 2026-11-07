#!/usr/bin/env python3
"""글로 읽기 본문 검수: 인쇄 원본(PDF)과 content/texts/<ID>.json 을 쪽마다 대조합니다.

쓰는 법: python3 tools/audit_text.py DL-0005 책.pdf
  1) 순서: 문단 순서가 인쇄된 위→아래 순서와 같은지
  2) 줄 바꿈: 인쇄된 줄과 같은지 (산문 문단은 줄을 이어 붙이므로 달라도 정상 — 게송·잠언·판권지 등은 같아야 함)
  3) 각주: 본문 번호 [n] 과 각주 [n]: 의 짝
보고만 하고 고치지는 않습니다. 결과를 보고 운영자에게 알린 뒤 고칩니다.
"""
import json, re, subprocess, sys, os
bk, pdf = sys.argv[1], sys.argv[2]
d = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'content', 'texts', f'{bk}.json'), encoding='utf-8'))
b = d['body']
pg = re.split(r'\n?=== (\d+)쪽 ===\n', b); P = {int(pg[i]): pg[i + 1] for i in range(1, len(pg), 2)}
N = lambda s: re.sub(r'\s|## |\[\^\d+\]:?', '', s)
lay = lambda n: subprocess.run(['pdftotext', '-f', str(n), '-l', str(n), '-layout', pdf, '-'], capture_output=True, text=True).stdout
order, lines = [], []
for n, t in sorted(P.items()):
    L = lay(n); LN = N(L)
    paras = [q for q in t.split('\n\n') if q.strip() and not q.startswith('![')]
    pos = [(LN.find(N(q)[:12]), q) for q in paras if len(N(q)) >= 4]
    pos = [x for x in pos if x[0] >= 0]
    for (a, qa), (c, qc) in zip(pos, pos[1:]):
        if c < a: order.append((n, qa[:25], qc[:25])); break
    pl = [N(l) for l in L.split('\n') if N(l) and not re.fullmatch(r'\d+', N(l))]
    ol = [N(l) for l in t.split('\n') if N(l) and not l.startswith('![')]
    if pl != ol: lines.append((n, len(pl), len(ol)))
refs = re.findall(r'(?m)(?<!^)\[\^(\d+)\]', b); defs = re.findall(r'(?m)^\[\^(\d+)\]:', b)
print(f'{bk}: {len(P)}쪽')
print(f'1) 순서가 인쇄본과 다를 수 있는 쪽 {len(order)}곳 (같은 글귀가 되풀이되면 잘못 잡힐 수 있음)')
for x in order: print('   ', x)
print(f'2) 줄 바꿈이 인쇄본과 다른 쪽 {len(lines)}곳 (산문 문단은 정상)')
for x in lines: print(f'    {x[0]}쪽: 인쇄 {x[1]}줄 / 사이트 {x[2]}줄')
print(f'3) 각주: 본문 번호 {len(refs)}개, 각주 {len(defs)}개, 짝 안 맞음 {sorted(set(refs) ^ set(defs), key=int)}')
