#!/usr/bin/env python3
"""원서 대조 짝 자료의 한국어 글자 자리 옮기기 (2026-11-18).
한국어 본문에서 문단 안의 글자 몇 개(빈칸·줄 끝 하이픈 등)만 고쳐 쪽·문단 열쇠는 그대로일 때,
짝짓기를 처음부터 다시 돌리지 않고 content/parallel/<ID>.*.json 의 한국어 자리 [열쇠, 시작, 끝] 와 ka 만 새 글에 맞춤.
  python3 tools/parallel/shift.py <ID> <고치기 전 본문 JSON>   (고친 뒤 본문은 content/texts/<ID>.json)
문단 수가 달라졌으면 멈춤 — 그때는 run_<id>.sh 로 다시 짝지음."""
import json, re, sys, os, glob, difflib
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bk, oldp = sys.argv[1], sys.argv[2]

def paras(t): return ['\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]
def plain(s):
    s = re.sub(r'\[\^[^\]]+\]', '', s); s = re.sub(r'^(## |\^\^ |:: |>> |\+\+ |\|\| |%% )', '', s, flags=re.M)
    return re.sub(r'\*\*|==|°°|§§|@@|\{\{|\}\}', '', s)
def keys(body):
    body = body.replace('\r\n', '\n'); pages = []
    for m in re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M): pages.append([m.group(1), m.end()])
    for i, p in enumerate(pages):
        end = pages[i + 1][1] - len(re.search(r'===[^\n]*===\s*$', body[:pages[i + 1][1]]).group(0)) if i + 1 < len(pages) else len(body)
        p.append(body[p[1]:end].strip())
    return {f'{n}:{s}': t for n, (_, _, txt) in enumerate(pages, 1) for s, t in enumerate(paras(txt))}

A = keys(json.load(open(oldp))['body']); B = keys(json.load(open(os.path.join(REPO, 'content/texts', bk + '.json')))['body'])
if set(A) != set(B): sys.exit('문단 열쇠가 달라졌습니다 — run_<id>.sh 로 다시 짝지으세요')
ch = {k for k in A if A[k] != B[k]}
maps = {}
for k in ch:
    m = [None] * (len(A[k]) + 1)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A[k], B[k], autojunk=False).get_opcodes():
        for t in range(i1, i2 + 1): m[t] = j1 + min(t - i1, j2 - j1)
    maps[k] = m
for f in glob.glob(os.path.join(REPO, 'content/parallel', bk + '.*.json')):
    raw = open(f).read(); d = json.loads(raw); n = 0
    for g in d['groups']:
        for s in g.get('s', []):
            for r in s.get('ko', []):
                if isinstance(r, list) and r and r[0] in maps: r[1], r[2] = maps[r[0]][r[1]], maps[r[0]][r[2]]; n += 1
        if g.get('ko') and g['ko'][0] in ch and g.get('ka') not in ('차례', None): g['ka'] = plain(B[g['ko'][0]])[:24]
    ind = re.match(r'\{\n( *)"', raw); ind = len(ind.group(1)) if ind else None
    open(f, 'w').write(json.dumps(d, ensure_ascii=False, indent=ind, separators=None if ind else (',', ':')) + ('\n' if raw.endswith('\n') else ''))
    print(os.path.basename(f), f'고친 문단 {len(ch)}, 옮긴 자리 {n}')
