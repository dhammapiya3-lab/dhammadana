"""『테라와다 불교의 신행생활』(DL-0041, 아짠 빤냐와로 마하테로 법문, (사)한국테라와다불교 초판 2016) → content/texts/DL-0041.json
  python3 tools/hwp2text_dl0041.py 책.hwp 책.pdf
  (다음에 python3 tools/split_chapters.py --write)

글은 한글(HWP) 파일에서, 쪽은 PDF 에서 (운영자 요청, 2026-11-22).
- PDF 는 한글 파일을 'Microsoft Print To PDF'로 인쇄한 A4 165쪽 — 글자층 순서가 뒤섞여 있어 글로는 쓰지 않음.
  쪽 아래 '- N -' = PDF 쪽 = 쪽 이름 (1~4쪽은 번호 없음, 165쪽도 번호가 인쇄되지 않았지만 본문이 이어지는 쪽이라 165).
- 쪽 나눔: 한글 파일 글자(빈칸 뺌)를 차례대로 PDF 쪽마다 그 쪽 글자 수만큼 나눔 — 쪽마다 글자 모음이 PDF 와 한 자도
  다르지 않은지 확인하고(다르면 멈춤), 문단은 시작한 쪽에 둠. 1쪽(속표지)은 PDF 글자층이 비어 있어 '삼 귀 의' 앞까지를 1쪽으로.
  2쪽은 빈 쪽이라 넣지 않음.
- 한글 파일의 문단(엔터) 하나 = 줄 하나. 빈 문단에서 문단을 나누고, 보통 본문 모양(양쪽 맞춤·왼쪽 여백 0·첫 줄 들여쓰기)
  문단은 하나씩 따로 문단, 그 밖의 모양(들여 쓴 묶음·왼쪽 맞춤 독송문 등)은 같은 모양끼리 이어 한 문단 안 줄 바꿈.
  왼쪽 여백 2000 넘게 들여 쓴 묶음은 ++ . 묶음이 쪽을 넘으면 쪽마다 새 문단.
  본문 모양 문단이라도 앞 문단이 문장 끝(. ? ! 」 등)이 아니고 빈 문단 없이 바로 이어지면(인쇄본 줄 끝에서 엔터로 나눈 줄)
  같은 문단 안 줄 바꿈으로 이어 붙임 (check_breaks ② 49곳).
- 장: 가운데 12pt 굵은 'N. 제목' 줄 (## , 읽기 목차의 장). 소제목: 굵은 한 줄 '(N) …'·'※ 참고 …'·'‣ …' → ## (읽기 목차 소제목).
  다른 가운데 줄은 :: , 오른쪽 맞춤은 >> .
- 굵게 **…**, 밑줄 __…__ (인쇄본에서 '혼자일 때'·'여러 명' 등 바꿔 읽는 곳에 친 밑줄 — 운영자 요청 2026-11-22).
- 글자는 한글 파일 그대로 (U+3000·U+F0A0 은 빈칸, 줄 끝 빈칸은 뺌). 글자·띄어쓰기가 한글 파일과 같은지 따로 대조함.
- 그림: PDF 쪽에서 잘라 냄 — 1쪽 로고, 109쪽 불교기, 126쪽 가사 도표, 155쪽 세 가지 가사. 108쪽 끝 작은 장식 조각은 넣지 않음.
- 차례(4쪽, 한글 파일의 표) → %% 차례 '제목 | 쪽'.
"""
import sys, os, re, json, bisect, collections
import xml.etree.ElementTree as ET, subprocess
import fitz

HWP, PDF = sys.argv[1], sys.argv[2]
BK, ED = 'DL-0041', '초판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = '/tmp/dl0041'
os.makedirs(WORK, exist_ok=True)
xmlp = os.path.join(WORK, 'book.xml')
if not os.path.exists(xmlp) or os.path.getmtime(xmlp) < os.path.getmtime(HWP):
    with open(xmlp, 'wb') as f: subprocess.run(['hwp5proc', 'xml', HWP], stdout=f, check=True)
root = ET.parse(xmlp).getroot()
DI = root.find('DocInfo')
CS = list(DI.iter('CharShape')); PSH = list(DI.iter('ParaShape'))
def csf(i):
    c = CS[int(i)]; return int(c.get('basesize')), c.get('bold') == '1', c.get('underline') != 'none'

# ---- 한글 파일 문단 (표 칸 문단은 표가 있는 문단 바로 뒤) ----
P = []
def walk(p, intable=False):
    segs, objs, tables = [], [], []
    for l in p.findall('LineSeg'):
        for e in l:
            if e.tag == 'Text': segs.append((e.text or '', e.get('charshape-id')))
            elif e.tag == 'ControlChar':
                if e.get('name') == 'LINE_BREAK': segs.append(('\n', e.get('charshape-id')))
                elif e.get('name') == 'TAB': segs.append(('\t', e.get('charshape-id')))
            elif e.tag == 'GShapeObjectControl': objs.append(e)
            elif e.tag == 'TableControl': tables.append(e)
    ps = PSH[int(p.get('parashape-id'))]
    q = dict(segs=segs, objs=objs, lines=[(int(l.get('chpos')), int(l.get('y'))) for l in p.findall('LineSeg')], align=ps.get('align'), ml=int(ps.get('doubled-margin-left')) // 2,
             ind=int(ps.get('indent')), intable=intable)
    q['t'] = ''.join(s for s, _ in segs)
    sz = [csf(c)[0] for s, c in segs if c and s.strip()]
    q['size'] = max(sz) if sz else 0
    q['allb'] = bool(sz) and all(csf(c)[1] for s, c in segs if c and s.strip())
    P.append(q)
    for t in tables:
        for row in t.iter('TableRow'):
            for cell in row.findall('TableCell'):
                for cp in cell.findall('Paragraph'): walk(cp, True)
for cs_ in root.find('BodyText').iter('ColumnSet'):
    for p in cs_.findall('Paragraph'): walk(p)

# ---- 쪽 나눔: PDF 쪽마다 글자 모음 ----
d = fitz.open(PDF)
NPG = d.page_count
def pdfchars(n):
    out = []
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                for c in s['chars']:
                    if c['c'].strip() and c['origin'][1] < 780: out.append(c['c'])
    return out
stream = [(i, ch) for i, q in enumerate(P) for ch in q['t'] if ch.strip()]
k0 = next(j for j, (i, ch) in enumerate(stream) if P[i]['t'].strip() == '삼 귀 의')
bounds, pos = [0, k0], k0
for n in range(2, NPG + 1):
    pc = pdfchars(n)
    seg = stream[pos:pos + len(pc)]
    if collections.Counter(c for _, c in seg) != collections.Counter(pc):
        sys.exit(f'{n}쪽 글자가 PDF 와 다름')
    pos += len(pc); bounds.append(pos)
assert pos == len(stream), (pos, len(stream))
first = {}
for j, (i, ch) in enumerate(stream): first.setdefault(i, j)
PGOF, cur = [], 1
for i, q in enumerate(P):
    if i in first: cur = bisect.bisect_right(bounds, first[i])
    PGOF.append(cur)
print('쪽마다 글자 모음이 PDF 와 같음:', NPG, '쪽, 글자', len(stream))

# ---- 굵게·밑줄 표시 ----
def marked(q):
    chars = []
    for s, c in q['segs']:
        b, u = (csf(c)[1], csf(c)[2]) if c else (False, False)
        for ch in s: chars.append((ch, b, u))
    # 빈칸은 앞뒤 글자의 모양을 따름 (빈칸만 굵게·밑줄인 것은 무시)
    n = len(chars); fl = [None] * n
    for j, (ch, b, u) in enumerate(chars):
        if ch.strip(): fl[j] = (b, u)
    for j in range(n):
        if fl[j] is None:
            L = next((fl[k] for k in range(j - 1, -1, -1) if fl[k] is not None), None)
            R = next((fl[k] for k in range(j + 1, n) if fl[k] is not None), None)
            fl[j] = (L[0] and R[0], L[1] and R[1]) if L and R else (False, False)
    out, B, U = '', False, False   # 굵게(바깥)·밑줄(안)을 따로 열고 닫음
    for j, (ch, _, _) in enumerate(chars):
        b, u = fl[j] if ch != '\n' else (False, False)
        if U and not (u and b == B): out += '__'; U = False
        if B and not b: out += '**'; B = False
        if b and not B: out += '**'; B = True
        if u and not U: out += '__'; U = True
        out += ch
    if U: out += '__'
    if B: out += '**'
    out = out.replace('　', ' ').replace('\uf0a0', ' ')
    return '\n'.join(x.rstrip() for x in out.split('\n'))
def plain(s): return re.sub(r'\*\*|__', '', s)

# ---- 그림 (PDF 쪽에서 잘라 냄) ----
UP = os.path.join(REPO, 'public', 'uploads')
def crop(n, rect, name, dpi=220):
    pm = d[n - 1].get_pixmap(dpi=dpi, clip=fitz.Rect(*rect))
    path = os.path.join(UP, name)
    from PIL import Image
    im = Image.frombytes('RGB', (pm.width, pm.height), pm.samples)
    im.save(path, quality=90)
    return '/uploads/' + name
IMGS = {
    8: (1, (180, 318, 448, 586), 'DL-0041-logo.jpg', '#로고'),
    1744: (109, (88, 96, 326, 308), 'DL-0041-flag.jpg', '#불교기'),
    2001: (126, (80, 212, 377, 460), 'DL-0041-p126-robe.jpg', '#가사 도표 — The pattern of a Five-khanda Cīvara from the inside'),
    2387: (155, (80, 213, 461, 344), 'DL-0041-p155-robes.jpg', '#세 가지 가사 그림'),
}
IMGPG = {1744: 109}   # 불교기 그림은 108쪽 끝 문단에 붙어 있지만 109쪽 맨 위에 인쇄됨

# ---- 문단 만들기 ----
BODY = ('both', 0, 2000)
pages = collections.OrderedDict()   # 쪽 번호 → 문단 목록
chapters, subs = [], []
def add(n, s, kind=None):
    pages.setdefault(n, []).append(s)
    if kind: (chapters if kind == 'ch' else subs).append((s.replace('## ', '').replace('^^ ', ''), n, len(pages[n]) - 1))

i, N = 0, len(P)
grp = None   # (쪽, 모양, [줄])
def flush():
    global grp
    if grp:
        n, key, lines = grp
        txt = '\n'.join(lines)
        if key[1] > 2000 or (key[1] == 2000 and key[0] != 'both'): txt = '++ ' + txt
        elif key[1] == 2000: txt = '++ ' + txt
        add(n, txt)
    grp = None

toc_rows = []
LASTB = None
LISTHEAD = re.compile(r'\s*(?:[①-⑳㉠-㉭Ⓐ-Ⓩ▶※‣「『“]|\(\d+\)|\d+[.)] |[가-하]\) )')
import unicodedata
def lastw(q):   # 한글 파일 문단의 마지막 줄 너비(한글 한 자 = 1)
    st = q['lines'][-1][0] if q.get('lines') else 0
    return sum(1.0 if unicodedata.east_asian_width(c) in 'WF' else 0.5 for c in q['t'][st:].rstrip())
ITEMHEAD = re.compile(r'\s*(?:[①-⑳㉠-㉭Ⓐ-Ⓩ▶※‣]|\(\d+\)|\d+[.)] |[가-하]\) )')
def CONT(prev, nxt, qp):   # 앞 줄이 낱말·쉼표에서 끝나고 다음 줄이 목록·인용 첫머리가 아니면 이어지는 줄
    a = plain(prev).split('\n')[-1].rstrip()
    if re.fullmatch(r'\s*\[[^\]]{1,6}\]', a): return True   # 말하는 이 표시 [대중]·[스님] 다음 줄은 이어서
    if re.search(r'[가-힣A-Za-z\u00c0-\u024f\u1e00-\u1eff,]$', a) is None or LISTHEAD.match(plain(nxt)): return False
    # 목록 항목 줄 다음의 보통 글은 앞 줄이 끝까지 찼을 때만 (⑦ … (오른손과 왼손사이 / 바닥에 …)
    return not ITEMHEAD.match(a) or lastw(qp) >= 25
for i, q in enumerate(P):
    n = IMGPG.get(i, PGOF[i])
    t = q['t']
    if n == 2: continue
    if i in IMGS:
        flush()
        pg, rect, name, alt = IMGS[i]
        url = crop(pg, rect, name)
        if i == 2387:   # 그림 위 설명 글(antaravāsaka …)은 글로 따로
            cap = re.sub(r' {2,}', '  ', marked(q).replace('', '')).strip()
            add(n, ':: ' + cap)
        add(n, f'![{alt}]({url})')
        if i == 1742:
            pass
        continue
    if q['objs'] and i == 1742:   # 108쪽 끝: 글 + 작은 장식 조각 2개(넣지 않음)
        pass
    if not t.strip():
        flush(); continue
    s = marked(q)
    key = (q['align'], q['ml'], q['ind'])
    if q['intable']:   # 4쪽 차례 표
        flush()
        if '…' in t:
            m = re.match(r'(.+?)\s*…\s*(\d+)\s*$', plain(s).strip())
            toc_rows.append(f'**{m.group(1)}** | {m.group(2)}' if q['allb'] else f'{m.group(1)} | {m.group(2)}')
        elif n == 4:
            add(n, ':: ' + s.strip())
        else:
            add(n, ':: ' + s.strip())   # 1쪽 단체 이름
        continue
    if toc_rows and n != 4:
        add(4, '%% ' + '\n'.join(toc_rows)); toc_rows = []
    pt = plain(s).strip()
    if n >= 5 and q['align'] == 'center' and q['size'] == 1200 and q['allb'] and re.match(r'(\d+\.|※) ', pt):
        flush(); add(n, '## ' + pt, 'ch'); continue
    if n >= 5 and q['allb'] and key[0] == 'both' and key[1] == 0 and len(pt) <= 70 and re.match(r'\(\d+\) |※ 참고|‣', pt):
        flush(); add(n, '## ' + pt, 'sub'); continue
    if n == 1:
        flush()
        if q['size'] == 3200: add(n, '^^ ' + pt)
        elif q['align'] == 'right': add(n, '>> ' + (f'**{pt}**' if q['allb'] else pt))
        else: add(n, ':: ' + s.strip())
        continue
    if n == 3 and pt == '삼 귀 의':
        flush(); add(n, '## ' + pt, 'ch'); continue
    if re.match(r' {20,}', t) and n > 1:   # 147쪽 '< 큰절 3번 >' (빈칸으로 가운데에 놓은 줄)
        flush(); add(n, ':: ' + s.strip()); continue
    if q['align'] in ('center', 'right'):
        flush(); add(n, (':: ' if q['align'] == 'center' else '>> ') + s.strip()); continue
    if key == BODY:
        flush()
        # 엔터로 나눈 줄(앞 문단이 문장 끝이 아님 · 빈 문단 없이 바로 이어짐 · 같은 쪽) → 한 문단 안 줄 바꿈
        if LASTB and LASTB[0] == n and LASTB[1] == i - 1 and CONT(pages[n][-1], s, P[i - 1]):
            pages[n][-1] += '\n' + s.rstrip(); LASTB = (n, i); continue
        add(n, s.strip() if not s.startswith(' ') else s.rstrip()); LASTB = (n, i); continue
    if not grp and LASTB and LASTB[0] == n and LASTB[1] == i - 1 and key[1] == 0 and CONT(pages[n][-1], s, P[i - 1]):
        pages[n][-1] += '\n' + s.rstrip(); LASTB = (n, i); continue   # 93쪽: 본문 모양 줄 다음 왼쪽 맞춤 줄
    if grp and grp[1] == key and grp[0] == n: grp[2].append(s)   # 쪽이 바뀌면 새 문단
    else: flush(); grp = (n, key, [s])
flush()

# 차례 장 (4쪽) — '◆ 차 례 ◆' 줄을 장 제목 '차례'로
chapters.append(('차례', 4, 0))
chapters.append(('속표지', 1, 0))
chapters.sort(key=lambda x: (x[1], x[2]))

for n in range(1, NPG + 1):
    if n != 2: pages.setdefault(n, [])
order = sorted(pages)
idx = {n: k for k, n in enumerate(order)}
toc = []
for t, n, j in chapters:
    toc.append(dict(title=t, page=idx[n] + 1, sub=False, **({'at': t[:20]} if j > 0 else {})))
for t, n, j in subs:
    toc.append(dict(title=t, page=idx[n] + 1, sub=True, **({'at': t[:20]} if j > 0 else {})))
pos = {(t, idx[n] + 1): j for t, n, j in chapters + subs}
toc.sort(key=lambda x: (x['page'], pos.get((x['title'], x['page']), 0), x['sub']))
for x in toc:   # 목차 이름만 '삼귀의'로 — 본문의 인쇄된 '삼 귀 의' 줄은 그대로 (운영자 요청, 2026-11-23)
    if x['title'] == '삼 귀 의': x['title'] = '삼귀의'

body = ''
for n in order:
    lab = '' if n <= 4 else f'{n}쪽'
    paras = [re.sub(r'^ +', '', x) if not x.startswith('++') else x for x in pages[n]]
    body += f"=== {lab} ===\n\n" + '\n\n'.join(paras) + '\n\n'
body = body.rstrip() + '\n'
images = [dict(image=f'/uploads/{v[2]}', caption='') for v in IMGS.values()]
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': images, 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print('장', len(chapters), '소제목', len(subs), '쪽', len(order), '→', out)
