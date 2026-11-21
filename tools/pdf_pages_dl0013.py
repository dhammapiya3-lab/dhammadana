#!/usr/bin/env python3
"""『번뇌를 가볍게 여기지 마십시오』(DL-0013): 전자책 글에 종이책 PDF 쪽 번호(=== N쪽 ===)를 넣습니다. 글자는 바꾸지 않습니다.
  python3 tools/pdf_pages_dl0013.py 종이책.pdf [--write]

- 그림이 있는 PDF 쪽(92쪽)과 전자책 그림(92장)은 차례대로 한 짝 → 그 그림 자리에서 쪽이 시작
- 글만 있는 쪽은 쪽 첫 글자들을 전자책 글에서 찾아 시작점으로 (앞 쪽 다음부터 가까운 곳)
- 각주 내용([^n]:)은 각주 번호가 있는 쪽 끝으로 옮김. '전자책 판권지'는 종이책에 없으므로 쪽 번호 없이 둠
"""
import json, re, sys, warnings
warnings.filterwarnings('ignore')
import fitz
sys.path.insert(0, 'tools')
from mark_bold import index_chars, norm

pdf = sys.argv[1]; bk = 'DL-0013'
f = f'content/texts/{bk}.json'
d = json.load(open(f)); body = d['body']
old = re.split(r'^===.*?===\n?', body, flags=re.M)[1:]
# 각주 내용은 따로 빼 두었다가 나중에 쪽 끝에
FN = {}
def takefn(p):
    keep = []
    for para in p.strip('\n').split('\n\n'):
        m = re.match(r'\[\^(\d+)\]: ', para)
        if m: FN[m.group(1)] = para
        else: keep.append(para)
    return '\n\n'.join(keep)
old = [takefn(p) for p in old]
clean, starts = '', []
for p in old:
    starts.append(len(clean)); clean += p.strip('\n') + '\n\n'
clean = clean.rstrip('\n') + '\n'
n, pos = index_chars(clean)
rev = {}  # clean 위치 → n 위치
for i, p in enumerate(pos): rev.setdefault(p, i)
figs = [m.start() for m in re.finditer(r'(?m)^!\[[^\]]*\]\(/uploads/DL-0013-[^)]+\)$', clean)]

doc = fitz.open(pdf)
ptr, fi, miss, S = 0, 0, [], []   # S: 쪽마다 ('img', 그림 위치) 또는 ('txt', 시작 위치 또는 None)
for i, pg in enumerate(doc):
    if pg.get_images():
        S.append(('img', figs[fi])); fi += 1; continue
    H = pg.rect.height
    t = norm(''.join(b[4] for b in pg.get_text('blocks')
                     if not re.fullmatch(r'\s*\d{1,3}\s*', b[4]) and '페이지' not in b[4] and b[1] < H - 30))
    start = None
    if len(t) >= 6:
        for k in list(range(0, min(len(t) - 12, 400) + 1, 6)):
            q = n.find(t[k:k + 12], ptr, ptr + 4000)
            if q >= 0:
                start = max(ptr, q - k)
                if k:  # 앞 글자가 조금 다르면, 가까운 앞쪽에서 첫 글자 몇 개를 찾아 시작점으로
                    for m in (6, 4, 3, 2):
                        r = n.rfind(t[:m], max(ptr, q - k - 40), q)
                        if r >= 0: start = r; break
                break
    if start is None:
        if len(t) >= 6: miss.append((f'{i + 1}쪽', t[:24]))
        S.append(('txt', None)); continue
    p = pos[start]
    ls = clean.rfind('\n', 0, p) + 1
    if re.fullmatch(r'(## |\*\*|:: )*', clean[ls:p]): p = ls
    S.append(('txt', p)); ptr = start + 1
# 그림 쪽: 앞뒤 글 쪽 사이에 그 그림이 있으면 그림 자리에서, 아니면(전자책에서 그림 자리가 다름) 다음 글 쪽 앞에 빈 쪽으로
bounds, pending, last, moved, merge = [], [], 0, [], []
for i, (kind, p) in enumerate(S):
    label = f'{i + 1}쪽'
    if kind == 'img':
        nxt = next((q for kk, q in S[i + 1:] if kk == 'txt' and q is not None), len(clean))
        if not (last <= p <= nxt):  # 이 그림은 다음 쪽 글 사이에 있음 → 다음 쪽과 함께 'N~M쪽'
            moved.append(label); merge.append(i + 1); continue
    if p is None:
        pending.append(label); continue
    if merge:
        label = f'{merge[0]}~{i + 1}쪽'; merge = []
    for e in pending: bounds.append((p, e))
    pending = []; bounds.append((p, label)); last = p
assert fi == len(figs), (fi, len(figs))
tail = pending
print('그림 자리가 종이책과 달라 빈 쪽으로 둔 쪽:', moved)
# 전자책 판권지: 쪽 번호 없이
for t in d['toc']:
    if t['title'] == '전자책 판권지': bounds.append((starts[t['page'] - 1], ''))
bounds.sort(key=lambda x: x[0])
if bounds[0][0] > 0: bounds.insert(0, (0, ''))
segs = []
for k, (p, lab) in enumerate(bounds):
    q = bounds[k + 1][0] if k + 1 < len(bounds) else len(clean)
    segs.append([lab, clean[p:q].strip('\n')])
for k in range(len(segs) - 1):  # 굵게가 쪽을 넘으면 닫고 다시 엶
    para = segs[k][1].split('\n\n')[-1]
    if para.count('**') % 2:
        segs[k][1] += '**'; segs[k + 1][1] = '**' + segs[k + 1][1]
# 각주 내용: 각주 번호가 있는 쪽 끝
for num, para in FN.items():
    k = next(k for k, s in enumerate(segs) if f'[^{num}]' in s[1])
    segs[k][1] = segs[k][1].rstrip('\n') + '\n\n' + para
new = ''.join(f'=== {lab} ===\n{seg}\n\n' if lab else f'=== ===\n{seg}\n\n' for lab, seg in segs).rstrip('\n') + '\n'
strip = lambda s: re.sub(r'\s|\*\*', '', re.sub(r'(?m)^===.*?===$', '', s))
assert sorted(strip(new)) == sorted(strip(body)), '글자가 달라짐'
bp = [b[0] for b in bounds]
toc = []
for t in d['toc']:
    off = starts[t['page'] - 1]
    if t.get('sub'):  # 소제목: 그 소제목이 있는 쪽
        h = clean.find('## ' + t['title'], off)
        j = max(k for k, b in enumerate(bp) if b <= h)
        toc.append({'title': t['title'], 'page': j + 1, 'sub': True, **({'at': t['at']} if bp[j] != h else {})}); continue
    j = max(k for k, b in enumerate(bp) if b <= off)
    nt = {'title': t['title'], 'page': j + 1, 'sub': False}
    if bp[j] != off:
        nt['at'] = re.sub(r'^(## |\*\*|:: )+', '', clean[off:].split('\n\n')[0]).split('\n')[0][:20]
    toc.append(nt)
print('쪽', len(segs), '| 찾지 못한 쪽:', miss, '| 뒤에 남은 쪽:', tail)
for t in toc: print(' ', t)
if '--write' in sys.argv:
    d['body'] = new; d['toc'] = toc
    json.dump(d, open(f, 'w'), ensure_ascii=False, indent=2); open(f, 'a').write('\n')
    print('적용')
