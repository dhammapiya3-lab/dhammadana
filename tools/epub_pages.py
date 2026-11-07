#!/usr/bin/env python3
"""전자책으로 만든 글(content/texts/<ID>.json)에 종이책 PDF 의 쪽 경계(=== N쪽 ===)를 넣습니다. 글자는 바꾸지 않습니다.

  python3 tools/epub_pages.py DL-0008 종이책.pdf --first 2 [--only-epub "잠언,저자 소개,전자책 판권지"] [--write]

--first: PDF 첫 장의 인쇄 쪽 번호. --only-epub: 종이책에 없는 장(쪽 번호 없이 둠).
"""
import json, re, sys, warnings
warnings.filterwarnings('ignore')
import fitz
sys.path.insert(0, 'tools')
from mark_bold import index_chars, norm

bk, pdf = sys.argv[1], sys.argv[2]
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
first = int(arg('--first', '1'))
only = [x.strip() for x in arg('--only-epub', '').split(',') if x.strip()]
f = f'content/texts/{bk}.json'
d = json.load(open(f)); body = d['body']
old = re.split(r'^===.*?===\n?', body, flags=re.M)[1:]
clean, starts = '', []
for p in old:
    starts.append(len(clean)); clean += p.strip('\n') + '\n\n'
clean = clean.rstrip('\n') + '\n'
n, pos = index_chars(clean)

doc = fitz.open(pdf)
bounds, pending, ptr, miss = [], [], 0, []
for i, pg in enumerate(doc):
    label = f'{i + first}쪽'
    H = pg.rect.height  # 쪽 번호·머리글(맨 위·맨 아래 짧은 줄)은 뺌
    t = norm(''.join(b[4] for b in pg.get_text('blocks') if not re.fullmatch(r'\s*\d{1,3}\s*', b[4]) and not ((b[3] < 60 or b[1] > H - 80) and len(b[4].strip()) < 40 and re.search(r'\d', b[4])) and not (b[3] < 30 and re.search(r'[AP]M +페이지', b[4]))))
    start = None
    if len(t) >= 8:
        cands = [(k, 24) for k in range(0, max(0, min(len(t) - 24, 300)) + 1, 8)] + [(k, 10) for k in range(0, min(len(t) - 10, 300) + 1, 10)]
        def best(key, k):  # 같은 글이 여러 번 나오면 PDF 쪽 글과 더 길게 같은 곳
            occ, j = [], n.find(key, ptr, ptr + 30000)
            while j >= 0 and len(occ) < 20:
                occ.append(j); j = n.find(key, j + 1, ptr + 30000)
            if not occ: return -1
            def agree(j):
                a = 0
                while a < 300 and j + a < len(n) and k + a < len(t) and n[j + a] == t[k + a]: a += 1
                return a
            return max(occ, key=lambda j: (agree(j), -j))
        for k, L in cands:
            q = best(t[k:k + L], k)
            if q >= 0:
                start = max(ptr, q - k)
                # 앞부분 글이 조금 다를 때: PDF 첫 글자 몇 개를 가까운 앞쪽에서 찾아 시작점으로
                for m in ((8, 6, 4, 2) if k else ()):
                    r = n.rfind(t[:m], max(ptr, q - k - 60), q + m)
                    if r >= 0:
                        start = r; break
                break
    if start is None:
        pending.append(label)
        if len(t) >= 8: miss.append((label, t[:30]))
        continue
    p = pos[start]
    ls = clean.rfind('\n', 0, p) + 1
    if re.fullmatch(r'(## |\*\*)*', clean[ls:p]): p = ls
    if pg.get_images() and p == ls:  # 그림이 있는 쪽: 바로 앞의 그림 문단도 이 쪽으로
        while True:
            m = re.search(r'(!\[[^\]]*\]\([^)]*\)\n\n)$', clean[:p])
            if not m: break
            p = m.start(1)
    for e in pending: bounds.append((p, e))
    pending = []
    bounds.append((p, label)); ptr = start + 1
end = len(clean)
if '--keep-tail' in sys.argv:  # 마지막으로 찾은 쪽 뒤의, 전자책에 없는 쪽은 기본으로 넣지 않음
    for e in pending: bounds.append((end, e))
elif pending: print('뒤쪽에 넣지 않은 쪽:', pending)
# 종이책에 없는 장: 쪽 번호 없는 경계
tops = [t for t in d['toc'] if not t.get('sub')]
for t in tops:
    if t['title'] in only:
        bounds.append((starts[t['page'] - 1], ''))
bounds.sort(key=lambda x: x[0])
# 맨 앞 경계가 0 이 아니면 0 에 첫 경계
if not bounds or bounds[0][0] > 0:
    bounds.insert(0, (0, ''))
out, segs = [], []
for k, (p, lab) in enumerate(bounds):
    q = bounds[k + 1][0] if k + 1 < len(bounds) else len(clean)
    seg = clean[p:q]
    segs.append([lab, seg])
# 굵게(**)가 쪽 경계를 넘으면 닫고 다시 엶
for k in range(len(segs) - 1):
    para = segs[k][1].split('\n\n')[-1]
    if para.count('**') % 2:
        segs[k][1] = segs[k][1].rstrip('\n') + '**'
        segs[k + 1][1] = '**' + segs[k + 1][1]
new = ''.join(f'=== {lab} ===\n{seg.strip(chr(10))}\n\n' if lab else f'=== ===\n{seg.strip(chr(10))}\n\n' for lab, seg in segs).rstrip('\n') + '\n'
new = re.sub(r'=== (\S+) ===\n\n\n', r'=== \1 ===\n\n', new)
assert re.sub(r'\s|\*\*', '', re.sub(r'^===.*?===$', '', new, flags=re.M)) == re.sub(r'\s|\*\*', '', re.sub(r'^===.*?===$', '', body, flags=re.M)), '글자가 달라짐'
# 목차 다시 맞추기
bp = [b[0] for b in bounds]
toc = []
for t in d['toc']:
    off = starts[t['page'] - 1]
    j = max(k for k, b in enumerate(bp) if b <= off)
    nt = {'title': t['title'], 'page': j + 1, 'sub': t.get('sub', False)}
    if bp[j] != off and not t.get('sub'):
        para = clean[off:].split('\n\n')[0]
        nt['at'] = re.sub(r'^(## |\*\*)+', '', para).split('\n')[0][:20]
    toc.append(nt)
print('쪽', len(segs), '| 찾지 못한 쪽(빈 쪽으로 둠):', miss)
for t in toc[:12]: print(' ', t)
if '--write' in sys.argv:
    d['body'] = new; d['toc'] = toc
    json.dump(d, open(f, 'w'), ensure_ascii=False, indent=2); open(f, 'a').write('\n')
    print('적용')
