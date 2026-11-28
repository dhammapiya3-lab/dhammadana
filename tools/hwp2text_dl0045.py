"""『큰 스승의 가르침』(DL-0045, 아신 자띨라 사야도 지음 · 오원탁 옮김 · 묘원 주해, 행복한 숲) → content/texts/DL-0045.json
  python3 tools/hwp2text_dl0045.py 책.hwp 책.pdf
  (다음에 python3 tools/split_chapters.py --write)

글은 한글(HWP) 파일에서, 쪽은 PDF 에서 (운영자 요청, 2026-11-28 — DL-0043·0044 와 같은 방식).
- 운영자가 준 한글 파일·PDF(Hancom PDF, A4 183쪽)는 인쇄본(360쪽)을 A4 에 다시 짠 것 — PDF 쪽 번호는 인쇄본 쪽과 다름.
  쪽 이름은 장 첫 쪽에만 차례에 인쇄된 쪽 번호(운영자 결정 2026-11-28 '장 첫 쪽만'), 다른 쪽은 이름 없음(=== ===).
- 쪽 나눔: 한글 파일의 한글 글자(본문 → 미주 차례)를 PDF 쪽마다 그 쪽 한글 글자 수(쪽 아래 꼬리말 780pt 아래 뺌)만큼
  나누고 쪽마다 글자 모음이 같은지 확인(다르면 멈춤). 문단은 시작한 쪽에, 미주 풀이는 그 글이 시작하는 쪽에.
- 미주(한글 파일 미주 80개, 책 끝에 모여 인쇄) → 본문 [^n], 책 끝 '미주' 장에 [^n]: (PDF 의 '39) ' 번호는 한글이 붙이는 것).
- 나눔 표시: 한글 파일에 카페 등에 나눠 올리려고 넣은 '****'·'####' 표시와 그 뒤 글('세 가지 종류의 사람들 -2 . 142쪽 - 145쪽.',
  '출처 : 큰 스승의 가르침 271쪽 - 273쪽.')이 있음 → 기호(* #)는 빼고 남은 글은 문단 뒤에 따로 연한 글씨 {{…}} (운영자 요청, 2026-11-28).
  기호만 있던 곳은 아무것도 남기지 않음. 1177 문단 '네 가지 요소 -3. 195쪽 - 196쪽' 은 앞에 기호가 없어 따로 찾음.
- 장: 16pt 제목(두 줄 '원인과 결과를 … 사람은' + '작은 수다원' 은 이어 하나로), 13pt '나쁜 길' 등 → ## (읽기 목차 소제목).
  앞쪽: 속표지(3쪽)·원서 정보(4쪽)·일대기(6쪽)·차례(7~8쪽 → %% '제목 | 쪽', 아랫단계 -)·'위빠사나를 처음 접하는 독자들에게'(11쪽).
  1쪽 반표제(제목만)는 속표지와 겹쳐 넣지 않음.
- 빈 문단 없이 이어진 한 줄짜리 줄은 한 문단 안 줄 바꿈. 굵게 **…**. 글자는 한글 파일 그대로 (U+3000·탭은 빈칸).
"""
import sys, os, re, json, bisect, collections
import xml.etree.ElementTree as ET, subprocess
import fitz

HWP, PDF = sys.argv[1], sys.argv[2]
BK, ED = 'DL-0045', '1판 2쇄'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = '/tmp/dl0045'
os.makedirs(WORK, exist_ok=True)
xmlp = os.path.join(WORK, 'book.xml')
if not os.path.exists(xmlp) or os.path.getmtime(xmlp) < os.path.getmtime(HWP):
    with open(xmlp, 'wb') as f: subprocess.run(['hwp5proc', 'xml', HWP], stdout=f, check=True)
root = ET.parse(xmlp).getroot()
DI = root.find('DocInfo')
CS = list(DI.iter('CharShape')); PSH = list(DI.iter('ParaShape'))
def csf(i):
    c = CS[int(i)]; return int(c.get('basesize')), c.get('bold') == '1'

def segs_of(p):
    segs, notes = [], []
    for l in p.findall('LineSeg'):
        for e in l:
            if e.tag == 'Text': segs.append((e.text or '', e.get('charshape-id')))
            elif e.tag == 'ControlChar' and e.get('name') == 'LINE_BREAK': segs.append(('\n', e.get('charshape-id')))
            elif e.tag == 'ControlChar' and e.get('name') == 'TAB': segs.append(('\t', e.get('charshape-id')))
            elif e.tag == 'EndNote':
                n = e.get('number'); notes.append((n, [q for q in e.iter('Paragraph')]))
                segs.append(('\x00' + n + '\x00', None))
    return segs, notes

def raw(segs): return ''.join(s for s, c in segs if c is not None)
def cut(segs, a, b):   # raw 글자 자리 [a, b) 의 조각 (미주 표시는 자리에 따라)
    out, pos = [], 0
    for s, c in segs:
        if c is None:
            if a <= pos <= b and a < b: out.append((s, c))
            continue
        x0, x1 = max(a, pos), min(b, pos + len(s))
        if x0 < x1: out.append((s[x0 - pos:x1 - pos], c))
        pos += len(s)
    return out

P = []
for cs_ in root.find('BodyText').iter('ColumnSet'):
    for p in cs_.findall('Paragraph'):
        segs, notes = segs_of(p)
        ps = PSH[int(p.get('parashape-id'))]
        q = dict(segs=segs, notes=notes, align=ps.get('align'), ml=int(ps.get('doubled-margin-left')) // 2, ind=int(ps.get('indent')))
        q['t'] = raw(segs)
        q['nl'] = len(p.findall('LineSeg'))
        cnt = collections.Counter()
        for s, c in segs:
            if c: cnt[csf(c)[0]] += len(s.strip())
        q['maxsize'] = max(cnt) if cnt else 0
        P.append(q)

def ptext(p): return ''.join(t.text or '' for t in p.iter('Text'))

# ---- 나눔 표시 떼기 ----
MK = re.compile(r'\*(?:\s*\*)+|#{2,}')
EXTRA = {'네 가지 요소 -3. 195쪽 - 196쪽', '8월 18일'}   # 앞에 기호 없는 표시 글 (8월 18일: 올린 날 적어 둔 것으로 보임)
marks = {}   # 문단 번호 → 연한 글씨로 남길 글
for i, q in enumerate(P):
    t = q['t']; m = MK.search(t)
    lab_at = None
    for e in EXTRA:
        k = t.find(e)
        if k > 0: lab_at = k
    if not m and lab_at is None: continue
    if m and m.start() == 0 and MK.sub('', t).strip() and not re.search(r'\d+쪽|\d+-\d+', t) and len(MK.sub('', t).strip()) > 60:
        q['segs'] = cut(q['segs'], m.end(), 10 ** 9)   # '***만약 여러분이…' — 앞 기호만 뺌
        q['t'] = t = raw(q['segs']); m = MK.search(t)
        if not m: continue
    a = lab_at if lab_at is not None and (not m or lab_at < m.start()) else m.start()
    lab = re.sub(r'\s+', ' ', MK.sub(' ', t[a:])).strip()
    body = t[:a]
    b = len(body.rstrip())
    if re.search(r'\.\s+\.$', body[:b]): b = body[:b].rstrip('.').rstrip().__len__() + 1   # '없습니다. .###' 의 떨어진 ' .'
    q['segs'] = cut(q['segs'], 0, b); q['t'] = raw(q['segs'])
    if lab: marks[i] = lab

# ---- 쪽 나눔 ----
H = re.compile('[가-힣]')
d = fitz.open(PDF)
NPG = d.page_count
def pdfchars(n):
    out = []
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                for c in s['chars']:
                    if c['origin'][1] < 780 and H.match(c['c']): out.append(c['c'])
    return out
bstream, nstream = [], []
ORIG = []   # 표시를 떼기 전 글자로 쪽 나눔 (PDF 에는 표시 글이 그대로 찍혀 있음)
for cs_ in root.find('BodyText').iter('ColumnSet'):
    for p in cs_.findall('Paragraph'): ORIG.append(segs_of(p))
NOPRINT = {i for i, (sg, _) in enumerate(ORIG) if i < 10 and raw(sg).strip() == '아신 자띨라 사야도의 법문'}   # 한글 파일에만 있고 PDF 에는 찍히지 않은 부제
for i, (segs, notes) in enumerate(ORIG):
    if i in NOPRINT: continue
    for s, c in segs:
        if c is None and s.startswith('\x00'):
            n = s.strip('\x00')
            for nn, paras in notes:
                if nn == n:
                    for ch in ''.join(ptext(x) for x in paras):
                        if H.match(ch): nstream.append((('n', n), ch))
        elif c is not None:
            for ch in s:
                if H.match(ch): bstream.append((i, ch))
stream = bstream + nstream
bb, bp = [0], 0
for n in range(1, NPG + 1):
    pc = pdfchars(n)
    seg = stream[bp:bp + len(pc)]
    if collections.Counter(c for _, c in seg) != collections.Counter(pc):
        x, y = collections.Counter(c for _, c in seg), collections.Counter(pc)
        sys.exit(f'PDF {n}쪽 글자가 한글 파일과 다름 {dict((x - y).most_common(5))} {dict((y - x).most_common(5))}')
    bp += len(pc); bb.append(bp)
assert bp == len(stream), (bp, len(stream))
first = {}
for j, (k, ch) in enumerate(stream): first.setdefault(k, j)
pageof = lambda k: min(NPG, bisect.bisect_right(bb, first[k]))
PGOF, cur = [], 1
for i in range(len(P)):
    if i in first: cur = pageof(i)
    PGOF.append(cur)
print('쪽마다 한글 글자 모음이 PDF 와 같음:', NPG, '쪽, 한글', len(stream))

def marked(segs):
    chars = []
    for s_, c in segs:
        if c is None:
            if s_.startswith('\x00'): chars.append(('\x01' + s_.strip('\x00') + '\x02', None)); continue
        b = csf(c)[1] if c else False
        for ch in s_: chars.append((ch, b))
    n = len(chars); fl = [None] * n
    for j, (ch, b) in enumerate(chars):
        if b is not None and ch.strip(): fl[j] = b
    for j in range(n):
        if fl[j] is None:
            L = next((fl[k] for k in range(j - 1, -1, -1) if fl[k] is not None), None)
            R = next((fl[k] for k in range(j + 1, n) if fl[k] is not None), None)
            fl[j] = bool(L and R) if chars[j][1] is not None else bool(L)
    out, B = '', False
    for j, (ch, _) in enumerate(chars):
        b = fl[j] if ch != '\n' else False
        if chars[j][1] is None:
            out += ch; continue
        if B and not b: out += '**'; B = False
        if b and not B: out += '**'; B = True
        out += ch
    if B: out += '**'
    out = out.replace('　', ' ').replace('\t', ' ')
    out = re.sub(r'\x01([^\x02]+)\x02', r'[^\1]', out)
    out = re.sub(r'\*\*(\s+)\*\*', r'\1', out)
    out = re.sub(r'\*\*(\[\^\d+\])\*\*', r'\1', out)
    return '\n'.join(re.sub(r'(?<=\S) {2,}', ' ', x).strip() for x in out.split('\n'))
def plain(s): return re.sub(r'\*\*|\[\^[^\]]+\]|\{\{|\}\}', '', s)

pages = collections.OrderedDict()
chapters, subs = [], []
def add(n, s, kind=None, title=None):
    pages.setdefault(n, []).append(s)
    if kind: (chapters if kind == 'ch' else subs).append((title or plain(re.sub(r'^(## |\^\^ |:: )', '', s)), n, len(pages[n]) - 1, plain(re.sub(r'^(## |\^\^ |:: )', '', s)).strip()[:20]))

toc_rows, skipped = [], []
last = None
notes_out = collections.defaultdict(list)
CHPG = {}   # PDF 쪽 → 인쇄본 쪽 이름
i = 0
while i < len(P):
    q = P[i]; n = PGOF[i]; t = q['t']
    for nn, paras in q['notes']:
        txt = '\n'.join(marked(segs_of(x)[0]) for x in paras).strip()
        notes_out[pageof(('n', nn))].append(f'[^{nn}]: {txt}')
    mk = marks.get(i)
    if not t.strip():
        if mk:
            add(n, '{{' + mk + '}}')
        last = None; i += 1; continue
    s = marked(q['segs']); pt = plain(s).strip()
    def tail():
        if mk: add(n, '{{' + mk + '}}')
    if n == 1 or i in NOPRINT: skipped.append((n, pt)); i += 1; continue
    if n == 3:
        add(n, ('^^ ' if q['maxsize'] >= 1800 else ':: ') + s.replace('**', ''), 'ch' if not any(c[0] == '속표지' for c in chapters) else None, '속표지'); i += 1; continue
    if n == 4:
        if last and last[0] == 4 and last[1] == i - 2 and len(pages[4]) > 1: pages[4][-1] += '\n' + s
        else: add(n, s, 'ch' if not any(c[0] == '원서 정보' for c in chapters) else None, '원서 정보')
        last = (4, i); i += 1; continue
    if re.fullmatch(r'\.{10,}', pt): i += 1; continue   # 11쪽 알림 상자 위 점선
    if n in (7, 8):
        if pt == '차례': add(7, '## 차례', 'ch'); i += 1; continue
        if pt == '큰 스승의 가르침': i += 1; continue   # 차례 쪽 위 작은 머리글
        m = re.match(r'(.+?)∥(\d+)$', pt)
        if m: toc_rows.append(('- ' if q['ml'] > 0 else '') + m.group(1).strip() + ' | ' + m.group(2))
        else: toc_rows.append(pt)
        i += 1; continue
    if toc_rows:
        add(7, '%% ' + '\n'.join(toc_rows)); toc_rows = []
    if re.fullmatch(r'\.{10,}', pt): i += 1; continue   # 11쪽 알림 상자 위 점선
    if n == 6 and pt.startswith('∥'):
        add(n, '## ' + s.replace('**', '').lstrip('∥'), 'ch'); CHPG[n] = '6'; last = None; i += 1; continue
    if n == 11 and pt.startswith('위빠사나를 처음 접하는'):
        add(n, '## ' + s.replace('**', ''), 'ch'); last = None; i += 1; continue
    if q['maxsize'] >= 1600:
        ttl = s.replace('**', '')
        if i + 1 < len(P) and P[i + 1]['maxsize'] >= 1600 and P[i + 1]['t'].strip():
            ttl += ' ' + marked(P[i + 1]['segs']).replace('**', ''); i += 1
        add(n, '## ' + ttl, 'ch'); last = None; i += 1; continue
    if q['maxsize'] >= 1300 and len(pt) <= 20:
        add(n, '## ' + s.replace('**', ''), 'sub'); last = None; i += 1; continue
    if last and last[0] == n and last[1] == i - 1 and P[i - 1]['nl'] == 1 and q['nl'] == 1 and not marks.get(i - 1):
        pages[n][-1] += '\n' + s; last = (n, i); tail(); i += 1; continue
    add(n, s); last = (n, i)
    if mk: tail(); last = None
    i += 1
nfirst = min(notes_out)
pages.setdefault(nfirst, []).insert(0, '## 미주')
chapters.append(('미주', nfirst, 0, ''))
for n, xs in sorted(notes_out.items()): pages.setdefault(n, []).extend(xs)

# 장 첫 쪽 이름: 차례의 쪽 번호
tocnum = {}
for r in '\n'.join(x for x in pages[7] if x.startswith('%% ')).replace('%% ', '').split('\n'):
    m = re.match(r'-?\s*(.+?) \| (\d+)$', r)
    if m: tocnum[m.group(1).replace(' ', '')] = m.group(2)
for t_, n, j, a in chapters:
    k = t_.replace(' ', '')
    if j == 0 and k in tocnum: CHPG[n] = tocnum[k]
    elif k.replace('구별', '식별') in {x.replace('구별', '식별') for x in tocnum}:
        CHPG[n] = next(v for x, v in tocnum.items() if x.replace('구별', '식별') == k.replace('구별', '식별'))
chapters.sort(key=lambda x: (x[1], x[2]))
order = [n for n in sorted(pages) if pages[n]]
idx = {n: k for k, n in enumerate(order)}
toc = []
for t_, n, j, a in chapters: toc.append(dict(title=t_, page=idx[n] + 1, sub=False, **({'at': a} if j > 0 else {})))
for t_, n, j, a in subs: toc.append(dict(title=t_, page=idx[n] + 1, sub=True, **({'at': a} if j > 0 else {})))
posd = {(t_, idx[n] + 1): j for t_, n, j, a in chapters + subs}
toc.sort(key=lambda x: (x['page'], posd.get((x['title'], x['page']), 0), x['sub']))
body = ''
for n in order:
    lab = f'{CHPG[n]}쪽' if n in CHPG else ''
    body += f"=== {lab} ===\n\n" + '\n\n'.join(pages[n]) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print('장', len(chapters), '소제목', len(subs), '쪽', len(order), '쪽 이름', len(CHPG), '미주', sum(len(v) for v in notes_out.values()), '나눔 표시', len(marks), '→', out)
print('넣지 않은 글:', skipped)
print('쪽 이름 없는 장:', [c[0] for c in chapters if c[1] not in CHPG])
