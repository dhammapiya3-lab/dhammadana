import os
"""『법구경 : 하루를 살더라도』(DL-0021) — 개정판 원고의 장 제목·이야기 제목·게송을 글로 읽기 본문에 넣는다.
  python3 tools/pdf2text_dl0021.py 책.pdf   (인쇄본 PDF → content/texts/DL-0021.json)
  python3 tools/dl0021_revise.py            (그 위에 개정판 원고 tools/dl0021_rev.json 을 덮어씀)
- 게송: 같은 게송 번호의 줄을 원고의 줄로 바꿈(줄 나눔도 원고대로). 쪽을 넘어간 게송은 쪽이 갈리는 자리를 원고 글에서 같은 곳으로 맞춤.
- 이야기 제목: 번호는 그대로, 제목·각주 번호는 원고대로. 짜임은 인쇄본 그대로(235-236·237-238, 277-279 안의 소제목 — 운영자 요청 2026-11-12).
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

# ---- 1. 짜임은 인쇄본 그대로 (운영자 요청, 2026-11-12): 235-236·237-238 두 이야기, 277-279 한 이야기 안에 소제목 무상·고(苦)·무아 ----
KEEP = {'235', '237', '277'}
SUBT = {'무상': '277', '고(苦)': '278', '무아': '279'}
for pg in P:
    if pno(pg[0]) != 325: continue
    for j, p in enumerate(pg[1]):
        m = re.match(r'## (무상|고\(苦\)|무아) ?(\[\^\d+\])$', p)
        if m:
            new = '## ' + REV['head'][SUBT[m.group(1)]]
            if new != p: pg[1][j] = new; log.append(f'325쪽 소제목 {p[3:]!r} → {new[3:]!r}')

# ---- 2. 이야기 제목 ----
nh = 0
for pg in P:
    if not 21 <= pno(pg[0]) < 459: continue
    for j, p in enumerate(pg[1]):
        m = re.match(r'## (\d+)((?:-\d+)?) (.*)$', p, re.S)
        if not m: continue
        v = m.group(1)
        if v in KEEP: continue
        new = REV['head'][v]
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
    rev = [y.strip() for v in range(int(a), int(b) + 1) for x in REV['verse'][str(v)] for y in x.split('\n') if y.strip()]
    if key == '237': rev = [x.replace('[^305]', '') for x in rev]  # 각주 305 는 인쇄본처럼 237-238 제목에  # 원고 한 칸에 두 줄이 든 곳(310·362·399)은 줄로 나눔
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
    if v not in H or v in KEEP: return [ln]
    return [f'{m.group(1)}{v}{rng} {H[v]}{tail}']
for pg in P:
    for j, p in enumerate(pg[1]):
        if p.startswith('%% '):
            out = []
            for ln in p[3:].split('\n'): out += fixline(ln)
            pg[1][j] = '%% ' + '\n'.join(out)


# ---- 5-2. 각주: 원고의 글자·띄어쓰기(맞춤법)를 넣되, 문단 나눔은 지금 그대로 (운영자 요청, 2026-11-12) ----
def keep_breaks(cur, new):
    cf = cur.replace('\n', ' '); nf = re.sub(r'\s*\n\s*', ' ', new).strip()
    if '\n' not in cur: return nf
    sm = difflib.SequenceMatcher(None, cf, nf, autojunk=False); ops = sm.get_opcodes()
    def mp(x):
        for tag, a1, a2, b1, b2 in ops:
            if a1 <= x < a2 or (x == a2 and tag != 'equal'):
                return b1 + (x - a1 if tag == 'equal' else round((x - a1) * (b2 - b1) / max(1, a2 - a1)))
        return len(nf)
    pos = []
    for i, ch in enumerate(cur):
        if ch != '\n': continue
        j = mp(i)
        k = min(range(max(0, j - 4), min(len(nf), j + 5)), key=lambda q: (nf[q] != ' ', abs(q - j)), default=j)  # 가까운 빈칸 자리
        pos.append(k if k < len(nf) and nf[k] == ' ' else j)
    out = list(nf)
    for k in sorted(set(pos), reverse=True):
        if k < len(out) and out[k] == ' ': out[k] = '\n'
        else: out.insert(k, '\n')
    return '\n'.join(x.strip() for x in ''.join(out).split('\n'))
nf = 0
for pg in P:
    for j, p in enumerate(pg[1]):
        m = re.match(r'\[\^(\d+)\]: (.*)$', p, re.S)
        if not m or m.group(1) not in REV['fn']: continue
        n, cur = m.group(1), m.group(2)
        sub = ''
        ms = re.search(r'\n(\d+-1)\) (.*)$', cur, re.S)   # 225-1)·304-1) 은 인쇄본처럼 앞 각주 끝에
        if ms: sub = ms.group(1); cur = cur[:ms.start()]
        new = keep_breaks(cur, REV['fn'][n])
        if sub: new += f'\n{sub}) ' + REV['fn'][sub].strip()
        if new != m.group(2): pg[1][j] = f'[^{n}]: {new}'; nf += 1
log.append(f'각주 {nf}개 고침')

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
# ---- 판권지: 운영자가 관리자 화면에서 고친 개정판 판권지(tools/dl0021_colophon.txt)로 ----
CK = '=== 511쪽 ===\n**법구경_ 하루를 살더라도**\n\n'
CF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dl0021_colophon.txt')
if os.path.exists(CF) and CK in body:
    col = open(CF, encoding='utf-8').read()
    nb = body[:body.index(CK) + len(CK)] + col
    if nb != body: body = nb; log.append('판권지: 개정판 판권지로')
# ---- 하위 각주(225-1·304-1)는 다른 각주처럼: 게송 끝 '225-1)' → [^225-1], 내용은 따로 [^225-1]: 문단 (운영자 요청, 2026-11-12) ----
for sub in ('225-1', '304-1'):
    nb = body.replace(sub + ')**', '[^' + sub + ']**')
    nb = nb.replace('\n' + sub + ') ', '\n\n[^' + sub + ']: ')
    if nb != body: body = nb; log.append(f'하위 각주 {sub}: 다른 각주와 같은 모양으로')
# ---- 인쇄본 목차의 쪽 번호 잘못: 379-380 이야기는 411쪽에서 시작 (운영자 요청, 2026-11-12) ----
TOCFIX = [('379-380 누더기 옷을 경책으로 삼은 낭갈라꿀라 | 412', '379-380 누더기 옷을 경책으로 삼은 낭갈라꿀라 | 411')]
for a, b in TOCFIX:
    if a in body: body = body.replace(a, b); log.append(f'목차 쪽 번호: {b}')
doc['body'], doc['toc'] = body, allt
json.dump(doc, open(T, 'w'), ensure_ascii=False, indent=2); open(T, 'a').write('\n')
# ---- 7. 책 소개 페이지의 목차(content/books/DL-0021.json contents) ----
B = 'content/books/DL-0021.json'; bk = json.load(open(B)); nc = 0; outl = []
for ln in bk.get('contents', '').split('\n'):
    m = re.match(r'^(\d+)((?:-\d+)?) (.*?) (\d{3})$', ln)
    if m and m.group(1) in H and m.group(1) not in KEEP and m.group(3) != H[m.group(1)]:
        ln = f'{m.group(1)}{m.group(2)} {H[m.group(1)]} {m.group(4)}'; nc += 1
    m = re.match(r'^(제(\d+)장 )(.*?)(\(.*\))$', ln)
    if m and REV['chap'].get(m.group(2)) and re.sub(r'\(.*?\)', '', m.group(3)) != re.sub(r'\(.*?\)', '', REV['chap'][m.group(2)]):
        ln = m.group(1) + re.sub(r'\(.*?\)', '', REV['chap'][m.group(2)]) + m.group(4); nc += 1
    if ln == '379-380 누더기 옷을 경책으로 삼은 낭갈라꿀라 412': ln = ln[:-3] + '411'; nc += 1
    outl.append(ln)
if nc:
    bk['contents'] = '\n'.join(outl); json.dump(bk, open(B, 'w'), ensure_ascii=False, indent=2); open(B, 'a').write('\n')
log.append(f'책 소개 목차 {nc}줄 고침')
print('이야기 제목', nh, '· 게송', nv, changed[:50], '· 읽기 목차 소제목', len(subs)); [print(' -', x) for x in log]
