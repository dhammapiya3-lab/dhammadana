"""『쉐우민의 스승들』(DL-0043, 우 꼬살라 사야도 · 우 떼자니아 사야도 지음, 묘원 엮음, 행복한 숲 증보판 2010) → content/texts/DL-0043.json
  python3 tools/hwp2text_dl0043.py 책.hwp 책.pdf
  (다음에 python3 tools/split_chapters.py --write → python3 tools/join_pagewords.py DL-0043 --write)

글은 한글(HWP) 파일에서, 쪽은 PDF 에서 (운영자 요청, 2026-11-28 — DL-0041 과 같은 방식).
- PDF 는 한글 파일을 'Microsoft Print To PDF'로 인쇄한 A4 382쪽. 숫자·문장부호 일부가 글자가 아닌 그림 조각으로 찍혀
  글자층으로는 쓸 수 없음. PDF 쪽 n = 인쇄 쪽 n+2 (쪽 아래 번호 그림, 차례 '증보판을 내면서 6' = PDF 4쪽).
- 쪽 나눔: 한글 파일의 한글 글자를 차례대로 PDF 쪽마다 그 쪽 한글 글자 수(쪽 아래 머리글 735pt 아래는 뺌)만큼 나누고
  쪽마다 한글 글자 모음이 PDF 와 같은지 확인(다르면 멈춤). 문단은 시작한 쪽에.
- 한글 파일 문단(엔터) 하나 = 줄 하나. 빈 문단에서 문단을 나눔. 양쪽 맞춤·들여쓰기 본문은 하나씩 따로 문단,
  한 줄짜리 줄이 빈 문단 없이 이어지면(법어록 시·번호 항목·인용 게송·'∙' 항목 둘째 줄 등)은 한 문단 안 줄 바꿈.
- 장: 14pt 제목(증보판을 내면서·안거를 시작하며·첫 번째 면담 …)과 부 표지(우 꼬살라 사야도 법어록 등, ^^).
  13pt 법어록 번호 → ## N (목차에는 넣지 않음), 12pt '1. 마음가짐' → ## (읽기 목차 소제목).
- '＊ …'·'* …' 7pt 주석 문단 → 각주 [^*k]: (본문의 '*' 표시를 [^*k] 로). 본문에 '*' 가 없는 주석은 그 자리 문단에 남김.
- 한글 파일의 편집 표시 '(교체)'·'사진'·'(사진)'(사진 넣을 자리 — 인쇄본에는 사진)은 넣지 않음.
- 문답의 말하는 이 표시(작은 글씨 '수행자'·'사야도'·'통역'·'수행자 일동')는 §§…§§, 텍스트 JSON spk_small: true 로 화면에서 인쇄본처럼 작은 글씨.
- 굵게 **…**. 글자는 한글 파일 그대로 (U+3000 은 빈칸, 줄 끝 빈칸은 뺌).
"""
import sys, os, re, json, bisect, collections
import xml.etree.ElementTree as ET, subprocess
import fitz

HWP, PDF = sys.argv[1], sys.argv[2]
BK, ED = 'DL-0043', '증보판'
OFF = 2
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = '/tmp/dl0043'
os.makedirs(WORK, exist_ok=True)
xmlp = os.path.join(WORK, 'book.xml')
if not os.path.exists(xmlp) or os.path.getmtime(xmlp) < os.path.getmtime(HWP):
    with open(xmlp, 'wb') as f: subprocess.run(['hwp5proc', 'xml', HWP], stdout=f, check=True)
root = ET.parse(xmlp).getroot()
DI = root.find('DocInfo')
CS = list(DI.iter('CharShape')); PSH = list(DI.iter('ParaShape'))
def csf(i):
    c = CS[int(i)]; return int(c.get('basesize')), c.get('bold') == '1'

P = []
for cs_ in root.find('BodyText').iter('ColumnSet'):
    for p in cs_.findall('Paragraph'):
        segs = []
        for l in p.findall('LineSeg'):
            for e in l:
                if e.tag == 'Text': segs.append((e.text or '', e.get('charshape-id')))
                elif e.tag == 'ControlChar' and e.get('name') == 'LINE_BREAK': segs.append(('\n', e.get('charshape-id')))
                elif e.tag == 'ControlChar' and e.get('name') == 'TAB': segs.append(('\t', e.get('charshape-id')))
        ps = PSH[int(p.get('parashape-id'))]
        q = dict(segs=segs, align=ps.get('align'), ml=int(ps.get('doubled-margin-left')) // 2, ind=int(ps.get('indent')))
        q['t'] = ''.join(s for s, _ in segs)
        q['nl'] = len(p.findall('LineSeg'))
        cnt = collections.Counter()
        for s, c in segs:
            if c: cnt[csf(c)[0]] += len(s.strip())
        q['size'] = cnt.most_common(1)[0][0] if cnt else 0
        q['maxsize'] = max(cnt) if cnt else 0
        q['allb'] = bool(cnt) and all(csf(c)[1] for s, c in segs if c and s.strip())
        P.append(q)

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
                    if c['origin'][1] < 735 and H.match(c['c']): out.append(c['c'])
    return out
stream = [(i, ch) for i, q in enumerate(P) for ch in q['t'] if H.match(ch)]
bounds, pos = [0], 0
for n in range(1, NPG + 1):
    pc = pdfchars(n)
    seg = stream[pos:pos + len(pc)]
    if collections.Counter(c for _, c in seg) != collections.Counter(pc):
        sys.exit(f'PDF {n}쪽 글자가 한글 파일과 다름')
    pos += len(pc); bounds.append(pos)
assert pos == len(stream), (pos, len(stream))
first = {}
for j, (i, ch) in enumerate(stream): first.setdefault(i, j)
PGOF, cur = [], 1
for i, q in enumerate(P):
    if i in first: cur = min(NPG, bisect.bisect_right(bounds, first[i]))
    PGOF.append(cur)
# 한글이 없는 법어록 번호 줄(13pt '1')은 뒤 글이 있는 쪽에 인쇄됨
for i, q in enumerate(P):
    if q['size'] == 1300 and re.fullmatch(r'\s*\d+\s*', q['t']):
        j = next(j for j in range(i + 1, len(P)) if j in first)
        PGOF[i] = PGOF[j]
print('쪽마다 한글 글자 모음이 PDF 와 같음:', NPG, '쪽, 한글', len(stream))

def marked(q):
    chars = []
    for s, c in q['segs']:
        b = csf(c)[1] if c else False
        for ch in s: chars.append((ch, b))
    n = len(chars); fl = [None] * n
    for j, (ch, b) in enumerate(chars):
        if ch.strip(): fl[j] = b
    for j in range(n):
        if fl[j] is None:
            L = next((fl[k] for k in range(j - 1, -1, -1) if fl[k] is not None), None)
            R = next((fl[k] for k in range(j + 1, n) if fl[k] is not None), None)
            fl[j] = bool(L and R)
    out, B = '', False
    for j, (ch, _) in enumerate(chars):
        b = fl[j] if ch != '\n' else False
        if B and not b: out += '**'; B = False
        if b and not B: out += '**'; B = True
        out += ch
    if B: out += '**'
    out = out.replace('　', ' ').replace('\t', ' ')
    return '\n'.join(x.rstrip() for x in out.split('\n'))
def plain(s): return s.replace('**', '')

pages = collections.OrderedDict()
chapters, subs = [], []
LOC = {}
CURI = [0]
def add(n, s, kind=None):
    pages.setdefault(n, []).append(s)
    LOC[CURI[0]] = (n, len(pages[n]) - 1)
    if kind: (chapters if kind == 'ch' else subs).append((plain(re.sub(r'^(## |\^\^ )', '', s)), n, len(pages[n]) - 1))

PARTS = {'우 꼬살라 사야도 법어록', '우 꼬살라 사야도 법문', '우 떼자니아 사야도 법문', '우 떼자니아 사야도의 수행문답'}
SKIP = {'(교체)', '사진', '(사진)'}
SPK = {'수행자', '사야도', '통역', '수행자 일동'}
toc_rows, notes, skipped = [], [], []
fnk = 0
last = None   # (쪽, 문단 번호, 모양) — 바로 앞에 넣은 문단
for i, q in enumerate(P):
    n = PGOF[i]
    CURI[0] = i
    t = q['t']
    if not t.strip(): last = None; continue
    pt = plain(marked(q)).strip()
    if pt in SKIP: skipped.append((n + OFF, pt)); last = None; continue
    s = marked(q)
    # 문답의 말하는 이 표시(인쇄본에서 9.6pt 작은 글씨 '수행자'·'사야도'·'통역'·'수행자 일동') → §§…§§ (운영자 요청, 2026-11-28)
    lead = ''
    for st, cid in q['segs']:
        if cid and csf(cid)[0] < 1000: lead += st
        else: break
    if lead.strip() in SPK and lead.strip() != pt:
        s = re.sub(r'^(\s*)' + re.escape(lead.strip()), lambda m: m.group(1) + '§§' + lead.strip() + '§§', s, count=1)
    key = (q['align'], q['ml'], q['ind'])
    if n == 1:
        add(n, ('^^ ' if pt == '쉐우민의 스승들' else ':: ') + pt); continue
    m = re.match(r'(.+?)\s{2,}(\d+)$', pt)
    if n == 3 and m:
        toc_rows.append(f'{m.group(1)} | {m.group(2)}'); continue
    if pt == '차례' and n == 3:
        add(n, '## 차례', 'ch'); continue
    if toc_rows and n != 3:
        add(3, '%% ' + '\n'.join(toc_rows)); toc_rows = []
    if pt in PARTS:
        add(n, '^^ ' + pt, 'ch'); last = None; continue
    if pt == '쉐우민 우 꼬살라 사야도 기념비문':
        add(n, '^^ ' + pt, 'ch'); last = None; continue
    if q['maxsize'] >= 1400 and len(pt) <= 40:
        add(n, '## ' + pt, 'ch'); last = None; continue
    if q['size'] == 1300 and re.fullmatch(r'\d+', pt):
        add(n, '## ' + pt); last = None; continue
    if q['size'] == 1200 and re.match(r'\d+\. ', pt):
        add(n, '## ' + pt, 'sub'); last = None; continue
    if re.match(r'[＊*] ', pt) and q['size'] <= 800:
        notes.append((n, i, s.strip())); last = None; continue
    if q['align'] == 'center':
        add(n, ':: ' + s.strip()); last = None; continue
    if q['align'] == 'right':
        add(n, '>> ' + s.strip()); last = None; continue
    joinable = q['align'] == 'left' or q['ml'] > 0 or q['ind'] >= 5000   # 기념비문 '∙' 항목 둘째 줄(내어 쓰기 5000)
    if last and last[0] == n and last[1] == i - 1 and P[i - 1]['nl'] == 1 and (q['nl'] == 1 or q['ml'] > 0 or q['ind'] >= 5000):   # 빈 문단 없이 이어진 한 줄짜리 줄은 한 문단 안 줄 바꿈 (게송·문답 묶음) — 여러 줄 문단 다음은 새 문단(기념비문)
        pages[n][-1] += '\n' + s.strip(); LOC[i] = (n, len(pages[n]) - 1); last = (n, i, key); continue
    add(n, s.strip()); last = (n, i, key)

# ---- 주석 → 각주: 한글 파일 차례에서 주석 바로 앞쪽, 아직 쓰지 않은 '*' 가 있는 가장 가까운 문단 ----
STAR = re.compile(r'(?<![*^])\*(?![*\]])')
unmatched = []
for n, i, s in notes:
    body = s[1:].strip()
    done = False
    for j in range(i - 1, max(-1, i - 40), -1):
        if j not in LOC: continue
        pg, k = LOC[j]
        x = pages[pg][k]
        mm = STAR.search(x)
        if mm:
            fnk += 1
            pages[pg][k] = x[:mm.start()] + f'[^*{fnk}]' + x[mm.end():]
            pages[n].append(f'[^*{fnk}]: {body}')
            done = True; break
    if not done:
        unmatched.append((n + OFF, s[:40])); pages.setdefault(n, []).append(s)

chapters.append(('속표지', 1, 0))
chapters.sort(key=lambda x: (x[1], x[2]))
order = [n for n in sorted(pages) if pages[n]]
idx = {n: k for k, n in enumerate(order)}
toc = []
for t, n, j in chapters:
    toc.append(dict(title=t, page=idx[n] + 1, sub=False, **({'at': t[:20]} if j > 0 else {})))
for t, n, j in subs:
    toc.append(dict(title=t, page=idx[n] + 1, sub=True, **({'at': t[:20]} if j > 0 else {})))
posd = {(t, idx[n] + 1): j for t, n, j in chapters + subs}
toc.sort(key=lambda x: (x['page'], posd.get((x['title'], x['page']), 0), x['sub']))

body = ''
for n in order:
    lab = '' if n == 1 else f'{n + OFF}쪽'
    body += f"=== {lab} ===\n\n" + '\n\n'.join(pages[n]) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'spk_small': True, 'toc': toc, 'images': [], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print('장', len(chapters), '소제목', len(subs), '쪽', len(order), '각주', fnk, '→', out)
print('넣지 않은 편집 표시:', skipped)
print('본문 표시를 못 찾은 주석:', unmatched)
