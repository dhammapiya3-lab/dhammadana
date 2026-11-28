"""『위빠사나 수행자의 근기를 돕는 아홉 요인』(DL-0044, 우 쿤달라 비왐사 지음 · 김봉이 옮김 · 묘원 주해, 행복한 숲 2009) → content/texts/DL-0044.json
  python3 tools/hwp2text_dl0044.py 책.hwp 책.pdf
  (다음에 python3 tools/split_chapters.py --write)

글은 한글(HWP) 파일에서, 쪽은 PDF 에서 (운영자 요청, 2026-11-28 — DL-0043 과 같은 방식).
- PDF 는 한글 파일에서 Hancom PDF 로 내보낸 376쪽(책 크기) — 글자층에 낱말 사이 빈칸이 거의 없어 글로는 쓰지 않음.
  PDF 쪽 = 인쇄 쪽(쪽 아래 '…_031').
- 쪽 나눔: 한글 파일의 한글 글자(본문 + 그 자리 각주)를 차례대로 PDF 쪽마다 그 쪽 한글 글자 수(쪽 아래 꼬리말 550pt 아래 뺌)만큼
  나누고 쪽마다 글자 모음이 같은지 확인(다르면 멈춤). 문단은 시작한 쪽에, 각주 풀이는 각주 번호가 있는 쪽 끝에.
- 각주(한글 파일 각주 108개, 장마다 1부터) → [^n] / [^n]: (풀이 첫머리 'n) ' 는 뺌).
- 장: 15pt 제목(서문·차례·장 제목 — 장 제목은 앞 문단의 큰 번호와 '위빠사나 수행자의 근기를 돕는' 줄과 이어 '1 위빠사나 수행' 꼴),
  12pt 굵은 '1. …' → ## (읽기 목차 소제목), 11pt 굵은 '1) …' 와 10pt 굵은 짧은 줄 '(1) …' → ##.
- 빈 문단 없이 이어진 한 줄짜리 줄·쉼표로 끝난 줄 다음 줄·'―' 항목끼리는 한 문단 안 줄 바꿈.
- 한글 파일의 편집 표시('(필름 교체!!!)'·'출판 허락 사인'·'사야도 사진' — 그림 넣을 자리)는 넣지 않음.
- 굵게 **…**. 글자는 한글 파일 그대로 (U+3000·탭은 빈칸, 줄 끝 빈칸은 뺌).
"""
import sys, os, re, json, bisect, collections
import xml.etree.ElementTree as ET, subprocess
import fitz

HWP, PDF = sys.argv[1], sys.argv[2]
BK, ED = 'DL-0044', '초판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = '/tmp/dl0044'
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
            elif e.tag == 'FootNote':
                n = e.get('number'); notes.append((n, [q for q in e.iter('Paragraph')]))
                segs.append(('\x00' + n + '\x00', None))
    return segs, notes

P = []
for cs_ in root.find('BodyText').iter('ColumnSet'):
    for p in cs_.findall('Paragraph'):
        segs, notes = segs_of(p)
        tables = [c for c in p.iter('TableControl')]
        ps = PSH[int(p.get('parashape-id'))]
        q = dict(segs=segs, notes=notes, align=ps.get('align'), ml=int(ps.get('doubled-margin-left')) // 2, ind=int(ps.get('indent')), table=tables[0] if tables else None)
        q['t'] = ''.join(s for s, c in segs if c is not None or not s.startswith('\x00'))
        q['nl'] = len(p.findall('LineSeg'))
        cnt = collections.Counter()
        for s, c in segs:
            if c: cnt[csf(c)[0]] += len(s.strip())
        q['size'] = cnt.most_common(1)[0][0] if cnt else 0
        q['maxsize'] = max(cnt) if cnt else 0
        q['allb'] = bool(cnt) and all(csf(c)[1] for s, c in segs if c and s.strip())
        P.append(q)

def ptext(p): return ''.join(t.text or '' for t in p.iter('Text'))

# ---- 쪽 나눔 ----
H = re.compile('[가-힣]')
d = fitz.open(PDF)
NPG = d.page_count
def sepy(n):   # 각주 구분선(왼쪽 59pt, 너비 98pt 가로줄) 높이 — 없으면 None
    ys = [x['rect'].y0 for x in d[n - 1].get_drawings() if 90 < x['rect'].width < 110 and x['rect'].height < 1 and 50 < x['rect'].x0 < 70]
    return min(ys) if ys else None
def pdfchars(n):
    body, note = [], []
    sy = sepy(n)
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                for c in s['chars']:
                    y = c['origin'][1]
                    if y < 550 and H.match(c['c']): (note if sy is not None and y > sy else body).append(c['c'])
    return body, note
bstream, nstream = [], []   # 본문: (문단 번호, 글자) / 각주: ((문단 번호, 각주 번호), 글자)
for i, q in enumerate(P):
    for s, c in q['segs']:
        if c is None and s.startswith('\x00'):
            n = s.strip('\x00')
            for nn, paras in q['notes']:
                if nn == n:
                    for ch in ''.join(ptext(x) for x in paras):
                        if H.match(ch): nstream.append(((i, n), ch))
        else:
            for ch in s:
                if H.match(ch): bstream.append((i, ch))
    if q['table'] is not None:
        for ch in ''.join(t.text or '' for t in q['table'].iter('Text')):
            if H.match(ch): bstream.append((i, ch))
bb, nb, bp, np_ = [0], [0], 0, 0
for n in range(1, NPG + 1):
    pb, pn = pdfchars(n)
    for st, p0, pc, lab in ((bstream, bp, pb, '본문'), (nstream, np_, pn, '각주')):
        seg = st[p0:p0 + len(pc)]
        if collections.Counter(c for _, c in seg) != collections.Counter(pc):
            x, y = collections.Counter(c for _, c in seg), collections.Counter(pc)
            sys.exit(f'PDF {n}쪽 {lab} 글자가 한글 파일과 다름 {dict((x - y).most_common(5))} {dict((y - x).most_common(5))}')
    bp += len(pb); np_ += len(pn); bb.append(bp); nb.append(np_)
assert bp == len(bstream) and np_ == len(nstream), (bp, len(bstream), np_, len(nstream))
first, fnpage = {}, {}
for j, (i, ch) in enumerate(bstream): first.setdefault(i, j)
for j, (k, ch) in enumerate(nstream): fnpage.setdefault(k, min(NPG, bisect.bisect_right(nb, j)))
PGOF, cur = [], 1
for i, q in enumerate(P):
    if i in first: cur = min(NPG, bisect.bisect_right(bb, first[i]))
    PGOF.append(cur)
stream = bstream + nstream
print('쪽마다 한글 글자 모음이 PDF 와 같음:', NPG, '쪽, 한글', len(stream))
EOF_MARK = 1

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
        if chars[j][1] is None:   # 각주 번호는 굵게 표시 안쪽이든 바깥이든 그대로
            out += ch; continue
        if B and not b: out += '**'; B = False
        if b and not B: out += '**'; B = True
        out += ch
    if B: out += '**'
    out = out.replace('\u3000', ' ').replace('\t', ' ')
    out = re.sub(r'\x01([^\x02]+)\x02', r'[^\1]', out)
    out = re.sub(r'\*\*(\s+)\*\*', r'\1', out)
    return '\n'.join(re.sub(r'(?<=\S) {2,}', ' ', x).strip() for x in out.split('\n'))
def plain(s): return re.sub(r'\*\*|\[\^[^\]]+\]', '', s)

pages = collections.OrderedDict()
chapters, subs = [], []
LOC = {}
def add(n, s, kind=None, title=None):
    pages.setdefault(n, []).append(s)
    if kind: (chapters if kind == 'ch' else subs).append((title or plain(re.sub(r'^(## |\^\^ )', '', s)), n, len(pages[n]) - 1, plain(re.sub(r'^(## |\^\^ |:: )', '', s)).strip()[:20]))

SKIPRE = re.compile(r'필름\s*교체|^출판 허락 사인$|^사야도 사진$')
skipped = []
toc_rows = []
last = None
fnotes = collections.defaultdict(list)   # 쪽 → [각주 풀이]
i = 0
while i < len(P):
    q = P[i]; n = PGOF[i]; t = q['t']
    if not t.strip() and q['table'] is None: last = None; i += 1; continue
    for nn, paras in q['notes']:
        txt = '\n'.join(marked(segs_of(x)[0]) for x in paras).strip()
        txt = re.sub(r'^\**\s*' + re.escape(nn) + r'\)\s*', '', txt)
        fnotes[fnpage[(i, nn)]].append(f'[^{nn}]: {txt}')
    s = marked(q['segs']); pt = plain(s).strip()
    if SKIPRE.search(pt): skipped.append((n, pt)); last = None; i += 1; continue
    if n == 1: skipped.append((n, pt)); i += 1; continue   # 1쪽 반표제(제목만) — 3쪽 속표지와 겹쳐 넣지 않음
    if q['table'] is not None:
        rows = []
        for row in q['table'].iter('TableRow'):
            cells = []
            for cell in row.findall('TableCell'):
                parts = [re.sub(r'\s+', ' ', plain(marked(segs_of(x)[0]))).strip() for x in cell.iter('Paragraph')]
                txt = parts[0] if parts else ''
                for x in parts[1:]: txt += ('' if x.startswith('에서 ') else ' ') + x   # '20개의 범천⏎에서' (엔터로 나눈 낱말)
                cells.append(txt.strip())
            rows.append('| ' + ' | '.join(cells) + ' |')
        if len(rows) > 1: rows.insert(1, '|' + '---|' * (rows[0].count('|') - 1))
        add(n, '\n'.join(rows)); last = None; i += 1; continue
    if n == 9:   # 차례
        if pt == '차례': add(n, '## 차례', 'ch'); i += 1; continue
        if pt == '위빠사나 수행자의 근기를 돕는 아홉 요인': i += 1; continue   # 차례 쪽 위 작은 머리글
        m = re.match(r'(.+?)＿(\d+)$', pt)
        if m:
            name = m.group(1).strip()
            if toc_rows and toc_rows[-1][1] is None: name = toc_rows.pop()[0] + ' ' + name
            toc_rows.append((name, m.group(2)))
        else:
            mm = re.match(r'(\d+)(.*)$', pt); toc_rows.append(((mm.group(1) + ' ' + mm.group(2).strip()) if mm else pt, None))
        i += 1; continue
    if toc_rows:
        add(9, '%% ' + '\n'.join(f'{a} | {b}' if b else a for a, b in toc_rows)); toc_rows = []
    if n == 2 and i < 9:
        if pt.startswith('옮긴이 김봉이'): add(n, s, 'ch', '옮긴이·주해자 소개'); last = None; i += 1; continue
        add(n, s); last = None; i += 1; continue
    if n == 2 and not any(c[0] == '판권지' for c in chapters):
        add(n, ':: ' + s, 'ch', '판권지'); i += 1; continue
    if n == 2 or n == 3:
        add(n, ('^^ ' if pt.startswith('아홉 요인') or pt.startswith('위빠사나 수행자의 근기를') and n == 3 else ':: ') + s,
            'ch' if n == 3 and not any(c[0] == '속표지' for c in chapters) else None, '속표지'); i += 1; continue
    if n == 6 and not any(c[0] == '저자 소개' for c in chapters):
        add(n, s, 'ch', '저자 소개'); i += 1; continue
    # 장 제목: 큰 번호 문단('1위빠사나'·'2위빠사나 수행자의 근기를 돕는') + 15pt 제목 → '1 위빠사나 수행'
    j = i + 1
    while j < len(P) and not P[j]['t'].strip(): j += 1
    if re.match(r'\d+\D', pt) and j < len(P) and P[j]['maxsize'] >= 1500 and len(plain(marked(P[j]['segs'])).strip()) <= 30:
        for nn, paras in P[j]['notes']: pass
        m = re.match(r'(\d+)(.*)$', s.replace('**', ''), re.S); t2 = marked(P[j]['segs']).replace('**', '')
        add(n, '## ' + m.group(1) + ' ' + m.group(2).strip() + ' ' + t2, 'ch', m.group(1) + ' ' + plain(m.group(2)).strip() + ' ' + plain(t2).strip())
        last = None; i = j + 1; continue
    if q['maxsize'] >= 1500 and len(pt) <= 30:
        add(n, '## ' + s.replace('**', ''), 'ch'); last = None; i += 1; continue
    if q['align'] == 'center' and pt == '위빠사나 수행자의 근기를 돕는 아홉 요인' and n == 11:
        add(n, '## ' + s.replace('**', ''), 'ch'); last = None; i += 1; continue
    if q['allb'] and q['maxsize'] >= 1200 and re.match(r'\d+\. ', pt):
        add(n, '## ' + s.replace('**', ''), 'sub'); last = None; i += 1; continue
    if q['allb'] and q['maxsize'] >= 1000 and len(pt) <= 45 and re.match(r'(\d+\)|\(\d+(-\d+)?\)) ', pt):
        add(n, '## ' + s.replace('**', '')); last = None; i += 1; continue
    if q['align'] == 'center':
        if last and last[0] == n and last[1] == i - 1 and pages[n][-1].startswith(':: '): pages[n][-1] += '\n' + s
        else: add(n, ':: ' + s)
        last = (n, i); i += 1; continue
    if q['align'] == 'right':
        add(n, '>> ' + s); last = None; i += 1; continue
    pv = plain(pages[n][-1]).rstrip() if last and pages.get(n) else ''
    if last and last[0] == n and last[1] == i - 1 and ((P[i - 1]['nl'] == 1 and (q['nl'] == 1 or q['ml'] > 0)) or pv.endswith(',') or (pv.split('\n')[-1].startswith('―') and pt.startswith('―'))):   # 빈 문단 없이 이어진 목록·게송 줄(쉼표로 끝나는 줄 뒤, '―' 항목끼리)
        pages[n][-1] += '\n' + s; last = (n, i); i += 1; continue
    add(n, s); last = (n, i); i += 1
for n, xs in fnotes.items(): pages.setdefault(n, []).extend(xs)

chapters.sort(key=lambda x: (x[1], x[2]))
order = [n for n in sorted(pages) if pages[n]]
idx = {n: k for k, n in enumerate(order)}
toc = []
for t, n, j, a in chapters: toc.append(dict(title=t, page=idx[n] + 1, sub=False, **({'at': a} if j > 0 else {})))
for t, n, j, a in subs: toc.append(dict(title=t, page=idx[n] + 1, sub=True, **({'at': a} if j > 0 else {})))
posd = {(t, idx[n] + 1): j for t, n, j, a in chapters + subs}
toc.sort(key=lambda x: (x['page'], posd.get((x['title'], x['page']), 0), x['sub']))
body = ''
for n in order:
    lab = '' if n in (2, 3) else f'{n}쪽'
    body += f"=== {lab} ===\n\n" + '\n\n'.join(pages[n]) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print('장', len(chapters), '소제목', len(subs), '쪽', len(order), '각주', sum(len(v) for v in fnotes.values()), '→', out)
print('넣지 않은 글:', skipped)
