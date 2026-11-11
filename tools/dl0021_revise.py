"""『법구경 : 하루를 살더라도』(DL-0021) — 개정판 원고의 장 제목·이야기 제목·게송을 글로 읽기 본문에 넣는다.
  python3 tools/pdf2text_dl0021.py 책.pdf   (인쇄본 PDF → content/texts/DL-0021.json)
  python3 tools/dl0021_revise.py            (그 위에 개정판 원고 tools/dl0021_rev.json 을 덮어씀)
- 게송: 같은 게송 번호의 줄을 원고의 줄로 바꿈(줄 나눔도 원고대로). 쪽을 넘어간 게송은 쪽이 갈리는 자리를 원고 글에서 같은 곳으로 맞춤.
- 이야기 제목: 번호는 그대로, 제목·각주 번호는 원고대로. 235~238 은 한 이야기로, 277~279 는 세 이야기로 (원고 짜임).
- 장 제목: 장 표지의 큰 제목을 원고대로.
- 목차(6~19쪽)·장 표지의 이야기 목록·읽기 목차도 바뀐 제목으로.
"""
import json, re, difflib

T = 'content/texts/DL-0021.json'
doc = json.load(open(T))
REV = json.load(open('tools/dl0021_rev.json'))
plain = lambda s: re.sub(r'\[\^[^\]]+\]', '', s.replace('**', ''))
log = []

pages = re.split(r'(=== \d+쪽 ===)\n', doc['body'])
assert pages[0] == ''
P = []  # [표시, [문단…]]
for i in range(1, len(pages), 2):
    P.append([pages[i], [p for p in pages[i + 1].split('\n\n') if p.strip()]])
pno = lambda mark: int(re.search(r'\d+', mark).group())

# ---- 1. 구조: 235~238 한 이야기, 277~279 세 이야기 ----
for pg in P:
    ps = pg[1]
    for j, p in enumerate(ps):
        if p.startswith('## 235-236 '): ps[j] = '## 235-238 ' + p[len('## 235-236 '):]
        if p.startswith('## 237-238 '): ps[j] = None; log.append('237-238 제목 줄을 뺌(235-238 한 이야기)')
        if p.strip() == '## 277-279 무상 고 무아': ps[j] = None; log.append('277-279 묶음 제목을 뺌(277·278·279 세 이야기)')
    subs = {'## 무상[': '## 277 무상[', '## 고(苦)[': '## 278 고(苦)[', '## 무아 [': '## 279 무아 ['}
    for j, p in enumerate(ps):
        if p is None: continue
        for a, b in subs.items():
            if p.startswith(a) and pno(pg[0]) == 325: ps[j] = b + p[len(a):]
    pg[1] = [p for p in ps if p is not None]

# ---- 2. 이야기 제목 ----
nh = 0
for pg in P:
    if not 21 <= pno(pg[0]) < 459: continue
    for j, p in enumerate(pg[1]):
        m = re.match(r'## (\d+)((?:-\d+)?) (.*)$', p, re.S)
        if not m: continue
        v = m.group(1); new = REV['head'][v]
        if v == '237': continue
        if m.group(3) != new: pg[1][j] = f'## {v}{m.group(2)} {new}'; nh += 1

# ---- 3. 게송: 게송 번호별로 (쪽, 문단, 줄) 모으기 ----
segs = {}  # 게송 키 → [(쪽 i, 문단 j, 번호 머리, [줄])]
cur = None
for i, pg in enumerate(P):
    n = pno(pg[0])
    if not 21 <= n < 459: continue
    for j, p in enumerate(pg[1]):
        mh = re.match(r'## (\d+)', p)
        if mh: cur = mh.group(1); continue
        if not p.startswith('++ '): continue
        lines = p[3:].split('\n')
        m = re.match(r'\*\*(\d+(?:-\d+)?) ', lines[0])
        head = ''
        if m: cur = m.group(1); head = m.group(1) + ' '; lines[0] = '**' + lines[0][len(m.group(0)):]
        segs.setdefault(cur, []).append([i, j, head, lines])

nv = 0; changed = []
for key, ss in segs.items():
    a, b = (key.split('-') + [key])[:2]
    rev = [y.strip() for v in range(int(a), int(b) + 1) for x in REV['verse'][str(v)] for y in x.split('\n') if y.strip()]  # 원고 한 칸에 두 줄이 든 곳(310·362·399)은 줄로 나눔
    old = [plain(l) for s in ss for l in s[3]]
    if old == [plain(x) for x in rev] and all(l.startswith('**') and l.endswith('**') for s in ss for l in s[3]) and [l for s in ss for l in s[3]] == ['**' + x + '**' for x in rev]:
        continue
    # 쪽이 갈리는 자리: 지금 글의 글자 위치를 원고 글의 같은 위치로 옮겨, 원고 줄을 나눔
    oldj = '\n'.join(old); revj = '\n'.join(plain(x) for x in rev)
    cuts, k = [], 0
    for s in ss[:-1]:
        k += sum(len(plain(l)) + 1 for l in s[3]); cuts.append(k)
    sm = difflib.SequenceMatcher(None, oldj, revj, autojunk=False)
    def mapp(x):
        for tag, a1, a2, b1, b2 in sm.get_opcodes():
            if a1 <= x <= a2: return b1 + (x - a1 if tag == 'equal' else round((x - a1) * (b2 - b1) / max(1, a2 - a1)))
        return len(revj)
    starts, t = [], 0
    for x in rev: starts.append(t); t += len(plain(x)) + 1
    bounds = [mapp(c) for c in cuts]
    parts = [[] for _ in ss]
    for x, st in zip(rev, starts):
        parts[sum(1 for bd in bounds if st >= bd - 1)].append(x)
    for s, part in zip(ss, parts):
        if not part: raise SystemExit(f'게송 {key}: 쪽 나눔을 맞추지 못함')
        i, j, head, _ = s
        P[i][1][j] = '++ ' + '\n'.join(('**' + head + x + '**') if q == 0 else '**' + x + '**' for q, x in enumerate(part))
    nv += 1; changed.append(key)

# ---- 4. 장 표지의 큰 제목 ----
for pg in P:
    for j, p in enumerate(pg[1]):
        m = re.match(r':: 제(\d+)장$', p)
        if m and j + 1 < len(pg[1]) and pg[1][j + 1].startswith('^^ '):
            new = REV['chap'][m.group(1)]
            if re.sub(r'\(.*?\)', '', pg[1][j + 1][3:]) != re.sub(r'\(.*?\)', '', new):  # 괄호 속 한자는 표지 아랫줄에 따로 있음
                log.append(f"제{m.group(1)}장 표지 제목 '{pg[1][j + 1][3:]}' → '{new}'"); pg[1][j + 1] = '^^ ' + new

# ---- 5. 목차(6~19쪽 %% 줄)와 장 표지의 이야기 목록 ----
H = {v: plain(t).strip() for v, t in REV['head'].items()}
def fixline(ln):
    m = re.match(r'^(-* ?)(\d+)((?:-\d+)?) (.*?)( \| \d+)?$', ln)
    if not m: return [ln]
    v, rng, tail = m.group(2), m.group(3), m.group(5) or ''
    if v == '237' and rng == '-238': return []
    if v not in H: return [ln]
    if v == '235': rng = '-238'
    if v == '277' and rng == '-279':
        return [f'{m.group(1)}{x} {H[x]}{tail}' for x in ('277', '278', '279')]
    return [f'{m.group(1)}{v}{rng} {H[v]}{tail}']
for pg in P:
    for j, p in enumerate(pg[1]):
        if p.startswith('%% '):
            out = []
            for ln in p[3:].split('\n'): out += fixline(ln)
            pg[1][j] = '%% ' + '\n'.join(out)

body = ''.join(f'{mk}\n' + '\n\n'.join(ps) + '\n\n' for mk, ps in P).rstrip() + '\n'

# ---- 6. 읽기 목차: 바뀐 제목으로 다시 ----
order = [mk for mk, _ in P]
toc = [t for t in doc['toc'] if not t['sub']]
subs = []
for i, (mk, ps) in enumerate(P):
    if not 21 <= pno(mk) < 511: continue
    for p in ps:
        if re.match(r'## \d', p): subs.append({'title': re.sub(r'\[\^[^\]]+\]', '', p[3:]).strip(), 'page': i + 1, 'sub': True})
allt = sorted(toc + subs, key=lambda t: (t['page'], t['sub']))
doc['body'], doc['toc'] = body, allt
json.dump(doc, open(T, 'w'), ensure_ascii=False, indent=2); open(T, 'a').write('\n')
print('이야기 제목', nh, '· 게송', nv, changed[:50], '· 읽기 목차 소제목', len(subs)); [print(' -', x) for x in log]
