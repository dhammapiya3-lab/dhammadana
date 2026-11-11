#!/usr/bin/env python3
"""법륜·열여덟 『팔정도』(DL-0020, 고요한소리) 인쇄용 PDF → content/texts/DL-0020.json
  python3 tools/pdf2text_dl0020.py 책.pdf

PDF 1쪽(앞표지)·250쪽(뒤표지)을 뺀 2~249쪽 = 인쇄 1~248쪽 (PDF 쪽 = 인쇄 쪽 + 1). tools/pdf2text_dl0015.py 와 같은 방식.
인쇄된 줄의 위치·글꼴로 문단을 나눔 (글자는 PDF 그대로, 화면에 안 보이는 조판 기호만 뺌).
- 들여쓴 줄·줄 사이가 벌어진 줄은 새 문단, 꽉 찬 줄 다음 줄은 이어 붙임, 짧은 줄 다음 줄은 줄 바꿈
- 큰 글씨·고딕 굵은 글씨 줄은 '## ' 소제목, 본문 속 굵은 글꼴(PB)은 **굵게**
- 위첨자 숫자는 [^n], 쪽 아래 각주(가는 줄 아래)는 [^n]: … (다음 쪽으로 넘어간 각주는 이어 붙임)
- 오른쪽 맞춤 출전 줄(《長部》 22 …)은 '>> '
- 그림·표(74쪽 팔정도 묶음, 108쪽 12지 연기 표, 속표지 로고)는 잘라서 public/uploads 에
"""
import fitz, json, re, sys
pdf = sys.argv[1]
bk, ED = 'DL-0020', '개정판 18쇄'
src = fitz.open(pdf)
OFF = 1  # PDF 쪽 = 인쇄 쪽 + 1
N = 248
images = []


def crop(n, rect, name, dpi=250):
    pg = src[n - 1 + OFF]
    pix = pg.get_pixmap(clip=fitz.Rect(rect), dpi=dpi)
    path = f'public/uploads/{bk}-{name}.png'
    pix.save(path)
    url = '/' + path.replace('public/', ''); images.append(url)
    return url


INVIS = re.compile('[\x01\x07\U000f0000-\U000fffff]')
SANS_B = re.compile(r'Dotum(PB|PM)$')
BOLD = re.compile(r'(PB|BOTF|Bold\w*)$')


def spans_of(l):
    return [s for s in l['spans'] if s['text'].strip()]


def main_size(l):
    ss = [s for s in spans_of(l) if not re.fullmatch(r'\s*\d+\s*', s['text'])]
    return max((s['size'] for s in ss), default=max(s['size'] for s in spans_of(l)))


def line_text(l, foot=False, head=False):
    mx = main_size(l)
    only = INVIS.sub('', ''.join(s['text'] for s in l['spans'])).strip()
    if not foot and re.fullmatch(r'\d{1,3}', only) and max(s['size'] for s in spans_of(l)) < 8:
        return '[^%s]' % only  # 제목 오른쪽 위의 각주 번호(따로 떨어진 작은 숫자)
    out = []
    first = True
    for s in l['spans']:
        t = INVIS.sub('', s['text']).replace('\t', ' ')
        if not t: continue
        if foot and first and re.fullmatch(r'\s*(\d+|\*)\s*', t):
            out.append((t.strip() + ' ', False)); first = False; continue  # 각주 번호
        if t.strip() and re.fullmatch(r'\s*\d+\s*', t) and s['size'] < mx * 0.8:
            out.append(('[^%s]' % t.strip(), False)); first = False; continue
        if t.strip(): first = False
        b = bool(BOLD.search(s['font'])) and not head and s['size'] >= 7.5
        if not re.search('[가-힣A-Za-z0-9]', t) and out:  # 한자·괄호·문장부호만 있는 조각은 앞 글의 굵기를 따름
            b = out[-1][1]
        out.append((t, b))
    res, cb = '', False
    for t, b in out:
        if b and not cb and t.strip():
            lead = len(t) - len(t.lstrip()); res += t[:lead] + '**'; t = t[lead:]; cb = True
        elif not b and cb and t.strip():
            tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + ' ' * tail; cb = False
        res += t
    if cb:
        tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + ' ' * tail
    return res


def is_head(l):
    ss = spans_of(l)
    mx = main_size(l)
    main = [s for s in ss if re.search('[가-힣A-Za-z]', s['text']) and s['size'] >= mx * 0.85] or ss
    if main_size(l) >= 13: return True
    if main_size(l) >= 11.5 and all(BOLD.search(s['font']) or 'Medium' in s['font'] or 'PM' in s['font'] or 'BOTF' in s['font'] for s in main if s['size'] >= 9):
        return True
    return all(SANS_B.search(s['font']) and s['size'] >= 9.5 for s in main)


def lines_of(n):
    pg = src[n - 1 + OFF]
    rule = [dr['rect'] for dr in pg.get_drawings() if dr['rect'].height < 1.5 and 28 < dr['rect'].width < 40]
    ry = min(r.y0 for r in rule) if rule else 9999
    if n >= 233: ry = 9999  # 저자 소개·부록 표·책 뒤 〈고요한소리〉 안내·도서 목록·판권지에는 각주가 없음 (밑줄 장식을 각주 선으로 보지 않게)
    L = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            raw = INVIS.sub('', ''.join(s['text'] for s in l['spans']))
            if not raw.strip(): continue
            x0, y0, x1, y1 = l['bbox']
            if y0 > 470: continue  # 아래쪽 쪽 번호·머리글
            foot = y0 > ry
            rawx = ''.join(s['text'] for s in l['spans'])
            L.append(dict(l=l, x0=x0, y0=y0, x1=x1, y1=y1, sz=main_size(l), raw=raw, foot=foot,
                          para=re.match(r'[\s＊*]*\x07', rawx) is not None,
                          head=(not foot) and is_head(l)))
    # 같은 줄의 조각은 하나로: 줄 아래(y1)가 같거나 위(y0)가 같으면 같은 줄 — 각주 번호가 위로 솟은 조각('른다.¹ 사성제의…')도 한 줄로
    L.sort(key=lambda a: (round(a['y1']), a['x0']))
    M = []
    for a in L:
        if M and (abs(a['y1'] - M[-1]['y1']) < 2.5 or abs(a['y0'] - M[-1]['y0']) < 2) and a['foot'] == M[-1]['foot']:
            M[-1]['parts'].append(a); continue
        a = dict(a); a['parts'] = [a.copy()]; M.append(a)
    for a in M:
        a['parts'].sort(key=lambda p: p['x0'])
        a['x0'] = a['parts'][0]['x0']; a['x1'] = max(p['x1'] for p in a['parts']); a['y0'] = min(p['y0'] for p in a['parts'])
        a['raw'] = ''.join(p['raw'] for p in a['parts']); a['para'] = a['parts'][0]['para']; a['head'] = any(p['head'] for p in a['parts'])
    M.sort(key=lambda a: (a['y0'], a['x0']))
    for a in M:
        a['t'] = ''.join(line_text(p['l'], foot=a['foot'], head=a['head']) for p in a['parts'])
    return M


def geom(n):
    return (62.4, 315.0) if n % 2 else (48.2, 300.8)


MARK = re.compile(r'\s*(＊|\*|[①-⑳]|\(\d+\)|\d+\.\s|\d+\))')


def body_paras(n, body):
    left, right = geom(n)
    paras, cur, prev = [], None, None
    first_x, hang_x, nlines = None, None, 0  # 지금 문단의 첫 줄 x, 내어쓰기 x, 줄 수
    for ai, a in enumerate(body):
        nxt = body[ai + 1] if ai + 1 < len(body) else None
        t = a['t']
        allb = all(BOLD.search(sp['font']) for p_ in a['parts'] for sp in spans_of(p_['l']))
        if not a['head'] and prev is not None and prev['head'] and (a['sz'] >= 11.5 or allb) and a['y0'] - prev['y1'] < 14:
            a['head'] = True  # 소제목의 둘째 줄 (예: '- 일곱 번째 덕목')
        if a['head']:
            if cur and cur.startswith('## ') and prev is not None and prev['head'] and a['y0'] - prev['y1'] < 14:
                tt = t.replace('**', '').strip()
                cur = cur + tt if not prev['raw'].endswith(' ') and re.search('[가-힣]$', cur) else cur.rstrip() + ' ' + tt
            else:
                if cur: paras.append(cur)
                cur = '## ' + t.replace('**', '').strip()
            prev = a; continue
        if a['x0'] > left + 40 and a['x1'] > right - 6 and ((a['sz'] < 10.5 and re.match(r'\s*[《〈<(]', a['raw'])) or a['x0'] > left + 120):
            if cur and cur.startswith('>> ') and prev is not None and prev.get('ral') and a['y0'] - prev['y1'] < 14:
                cur = cur.rstrip() + '\n' + t.strip()
            else:
                if cur: paras.append(cur)
                cur = '>> ' + t.strip()
            a['ral'] = True; prev = a; continue
        if cur and cur.startswith('>> '):
            paras.append(cur); cur = None
        start = False
        if cur is None or prev is None or prev['head']:
            start = True
        else:
            gap = a['y0'] - prev['y1']
            lh = max(6.0, prev['y1'] - prev['y0'])
            short = prev['x1'] < right - 14
            marked = MARK.match(cur.split('\n')[-1].replace('**', '')) is not None
            if nlines == 1 and marked and a['x0'] > first_x + 3:
                hang_x = a['x0']  # 내어쓰기 문단의 둘째 줄
            if nlines == 1 and prev['para'] and not short and not a['para'] and a['x0'] > left + 6:
                hang_x = a['x0']  # 들여 짠 묶음(＊ 설명 등) 안의 문단: 첫 줄은 조판 기호로 들여씀, 둘째 줄부터 묶음 왼쪽
            cont_hang = hang_x is not None and abs(a['x0'] - hang_x) < 2
            same_x = abs(a['x0'] - prev['x0']) < 2 and not short
            verse = abs(a['x0'] - prev['x0']) < 2 and prev['x0'] - left > 6 and prev['x1'] < right - 10 and not cont_hang and gap <= lh * 0.85 \
                and not (nxt is not None and not nxt['head'] and nxt['x0'] < a['x0'] - 6 and nxt['y0'] - a['y1'] <= lh * 0.85)  # 다음 줄이 왼쪽으로 나오면 산문 문단의 첫 줄
            indent = a['x0'] - left > 6 and not cont_hang and not same_x
            newmark = MARK.match(a['raw']) is not None and not cont_hang and short
            szjump = abs(a['sz'] - prev['sz']) > .6 and (short or a['sz'] > 11.5)
            if verse and not newmark:
                cur = cur.rstrip() + '\n' + t; nlines += 1  # 게송 등 들여 짠 짧은 줄: 인쇄된 줄 그대로
            elif gap > lh * 0.85 or szjump or indent or newmark or a['para']:
                start = True
            elif short:
                cur = cur.rstrip() + '\n' + t; nlines += 1
            else:
                cur = cur + t
                nlines += 1
        if start:
            if cur: paras.append(cur)
            cur = t; first_x = a['x0']; hang_x = None; nlines = 1
        prev = a
    if cur: paras.append(cur)
    return paras


def foot_items(n, foot):
    left, right = geom(n)
    items, cur, prev = [], None, None
    for a in foot:
        m = re.match(r'\s*(\d+|\*) +(.*)', a['t'])
        first_digit = a['parts'][0]['l']['spans'] and re.fullmatch(r'\s*(\d+|\*)\s*', INVIS.sub('', a['parts'][0]['l']['spans'][0]['text']).replace('\t', ' ') or 'x')
        if m and first_digit and a['x0'] <= left + 2:
            if cur is not None: items.append(cur)
            cur = [m.group(1), m.group(2).lstrip()]; prev = a; continue
        if cur is None:
            cur = [None, a['t'].lstrip()]; prev = a; continue
        short = prev['x1'] < right - 14
        gap = a['y0'] - prev['y1']
        sub = re.match(r'\s*(\(\d+\)|\*\*\(\d+\))', a['t']) or (a['x0'] < prev['x0'] - 4 and not short and False)
        if sub or gap > 6 or short:
            cur[1] = cur[1].rstrip() + '\n' + a['t'].lstrip()
        else:
            cur[1] = cur[1] + a['t'].lstrip()
        prev = a
    if cur is not None: items.append(cur)
    return items


clean = lambda s: re.sub(r'[ \t ]+\n', '\n', re.sub(r'(?<=\S)[ \t ]{2,}', ' ', s)).strip()
pages, carry = [], []
for n in range(1, N + 1):
    L = lines_of(n)
    body = [a for a in L if not a['foot']]
    foot = [a for a in L if a['foot']]
    paras = body_paras(n, body)
    fitems = foot_items(n, foot)
    fns = []
    for num, txt in fitems:
        if num is None:  # 앞 쪽에서 넘어온 각주
            back = next((pp for pp in reversed(pages) if pp[2]), None)
            if back:
                q = back[2][-1]
                back[2][-1] = (q.rstrip() + '\n' + txt.lstrip()) if re.search(r'[.)」』”]\s*$', q) or re.match(r'\s*(\*\*)?\(\d+\)', txt) else q + txt
            else: fns.append(txt)
            continue
        fns.append(f'[^{num}]: ' + txt)
    pages.append([n, paras, fns])

# ---- 쪽마다 손볼 곳 (인쇄된 모양 그대로) ----
P = {p[0]: p for p in pages}


def rows(n, foot=False):
    return [a for a in lines_of(n) if a['foot'] == foot]


def plain(a):
    return re.sub(r'\s+', ' ', a['raw']).strip()


# 1쪽 속표지 (구분 막대 ㅣ → |)
P[1][1] = [':: 법륜・열여덟', '^^ 팔정도', ':: 聖八支道', ':: 비구 보디 지음 | 전병재 옮김']
assert plain(rows(1)[-1]).replace(' ', '') == '비구보디지음ㅣ전병재옮김', plain(rows(1)[-1])
# 4쪽 일러두기 (쪽 아래쪽)
ls = [a for a in rows(4)]
items, cur = [], None
for a in ls[1:]:
    t = a['raw']
    if t.strip().startswith('*'):
        if cur: items.append(cur)
        cur = t.lstrip()
    else:
        cur = cur + (t if cur.endswith(' ') else t.lstrip())
items.append(cur)
P[4][1] = ['## ' + plain(ls[0])] + ['\n'.join(re.sub(r'\s+', ' ', x) for x in items)]
# 3쪽 원서 정보: 인쇄된 줄 그대로
P[3][1] = ['**The Noble Eightfold Path**\nWay to the End of Suffering', 'Bhikkhu Bodhi', 'The Wheel Publication No.308-311 1984\nSecond edition(revised) 1994\nBuddhist Publication Society\nKandy, Sri Lanka']
assert ''.join(plain(a) for a in rows(3)).replace(' ', '') == ''.join(P[3][1]).replace('**', '').replace('\n', '').replace(' ', ''), [plain(a) for a in rows(3)]
# 5쪽 차례: 인쇄된 글 그대로 (점선 없이), 장 줄은 굵게, 묶음 사이는 ~
out, py = [], None
for a in rows(5):
    t = plain(a)
    if t.replace(' ', '') == '차례': continue
    if py is not None and a['y0'] - py > 30: out.append('~')
    py = a['y0']
    m = re.match(r'(.+?)\s*。\s*(\d+)$', t)
    if m: out.append(f'{m.group(1)} 。 {m.group(2)}'); continue
    m = re.match(r'(.+?)\s*(\d+)$', t)
    out.append(f'**{m.group(1)}**  {m.group(2)}')
P[5][1] = ['## 차례', '%% ' + '\n'.join(out)]
def raw_rows(n):
    out = []
    for b in src[n - 1 + OFF].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            raw = INVIS.sub('', ''.join(sp['text'] for sp in l['spans']))
            if not raw.strip() or l['bbox'][1] > 470: continue
            x0, y0, x1, y1 = l['bbox']
            out.append(dict(x0=x0, y0=y0, y1=y1, sz=main_size(l), raw=raw))
    return out


# 234~235쪽 부록 1 표: 빠알리어 | 우리말 역어 | 영어 (한 칸에 두 줄이면 띄어 이음)
for n in (234, 235):
    r = sorted(raw_rows(n), key=lambda a: a['y0'])
    head = [a for a in r if a['y0'] < 60 or (a['sz'] < 7 and a['y0'] < 45)]
    cells = [a for a in r if a not in head and a['y0'] < 465 and not (n == 235 and a['y0'] > 345)]
    xs = sorted({round(a['x0']) for a in cells if a['y0'] > 60})
    c2 = min(x for x in xs if x > 140); c3 = min(x for x in xs if x > 220)
    col = lambda a: 0 if a['x0'] < c2 - 5 else (1 if a['x0'] < c3 - 5 else 2)
    # 줄(행)은 가운데 칸(우리말 역어)을 기준으로: 9pt 안쪽으로 이어진 줄은 한 칸, 다른 칸 줄은 가장 가까운 행에
    kor = sorted([a for a in cells if col(a) == 1], key=lambda a: a['y0'])
    anchors = []
    for a in kor:
        if anchors and a['y0'] - anchors[-1][-1]['y0'] < 10: anchors[-1].append(a)
        else: anchors.append([a])
    mid = [(g[0]['y0'] + g[-1]['y1']) / 2 for g in anchors]
    rowsT = [['', '', ''] for _ in anchors]
    for a in sorted(cells, key=lambda a: (a['y0'], a['x0'])):
        k = col(a); c = (a['y0'] + a['y1']) / 2
        i = min(range(len(mid)), key=lambda i: abs(mid[i] - c)) if k != 1 else next(i for i, g in enumerate(anchors) if a in g)
        t = re.sub(r'\s+', ' ', a['raw'].replace('\x07', '')).strip()
        rowsT[i][k] = (rowsT[i][k][:-1] + t if rowsT[i][k].endswith('-') else (rowsT[i][k] + ' ' + t)).strip()
    tbl = ['| ' + ' | '.join(r) + ' |' for r in rowsT]
    title = [plain(a) for a in rows(n) if a['y0'] < 45]
    P[n][1] = (['## 부록 1  팔정도의 요소별 분석[^90]'] if n == 234 else []) + ['\n'.join(tbl)]
    assert n != 234 or re.sub(r'\s', '', ' '.join(title)) == '부록1팔정도의요소별분석90', title
# 236~238쪽 부록 2: 갈래 제목(굵게) + 책마다 한 문단(제목 줄 / 지은이 줄 / 판 정보 줄)
for n in (236, 237, 238):
    out = []
    for a in rows(n):
        t = plain(a)
        if a['y0'] < 45 and '부록' in t: out.append('## ' + re.sub(r'\s+', ' ', t)); continue
        if re.match(r'[ⅠⅡⅢⅣⅤⅥⅦⅧIV]+\.', t): out.append('**' + t + '**'); continue
        if t.startswith('《') or not out or out[-1].startswith(('**', '## ')): out.append(t)
        else: out[-1] += '\n' + t
    P[n][1] = out
fn90 = [a for a in raw_rows(235) if a['y0'] > 345]
P[235][2] = ['[^90]: ' + re.sub(r'\s+', ' ', ''.join(re.sub(r'^\s*90\s*', '', a['raw']).replace('\x07', '') for a in fn90)).strip()]
# 장 첫머리 지은이 줄(오른쪽 맞춤)의 * 는 각주 표시
for n, ps, fns in pages:
    for i, x in enumerate(ps):
        if x.startswith('>> '):
            ps[i] = re.sub(r'\*\s*(?=\n|$)', '[^*]', x)
        if x.strip() == '- 보시의 완성 -':
            ps[i] = ':: - 보시의 완성 -'
# 124쪽 〈고요한소리〉는: 。 항목마다 한 문단
def bullets(n, mark='。'):
    out, cur = [], None
    for a in rows(n):
        t = a['raw'].replace('\n', '')
        if t.strip().startswith(mark) or t.strip().startswith('-'):
            if cur: out.append(cur)
            cur = t.lstrip()
        else:
            cur = (cur or '') + (t if cur and cur.endswith(' ') else t.lstrip())
    if cur: out.append(cur)
    return [re.sub(r'\s{2,}', ' ', x.replace('\t', ' ')).strip() for x in out]
r124 = rows(240)
hd = [a for a in r124 if a['sz'] > 9.5]
body124 = bullets(240)
head124 = [x for x in body124 if '〈고요한소리〉는' == x.strip()]
P[240][1] = ['## 〈고요한소리〉는'] + [x for x in body124 if x.strip() != '〈고요한소리〉는']
# 홈페이지 안내 두 줄은 앞 항목 아래 줄로
ps = P[240][1]; k = next(i for i, x in enumerate(ps) if '홈페이지 안내' in x)
P[240][1] = ps[:k] + ['\n'.join(ps[k:])]
# 125쪽 회원 안내 + 계좌
r = rows(241)
txt = [a for a in r if a['x0'] < 75]
acct = sorted([a for a in r if a['x0'] >= 75], key=lambda a: (round(a['y0']), a['x0']))

items, cur = [], None
for a in txt:
    t = a['raw'].replace('\t', ' ')
    if t.strip().startswith('。'):
        if cur: items.append(cur)
        cur = t.lstrip()
    elif re.match(r'\s*\(전화', t):
        cur = cur.rstrip() + '\n' + t.strip()
    else:
        cur = cur + (t if cur.endswith(' ') else t.lstrip())
items.append(cur)
lines, prev = [], None
for a in acct:
    if prev is not None and abs(a['y0'] - prev['y0']) < 2: lines[-1] += ' ' + plain(a)
    else: lines.append(plain(a))
    prev = a
P[241][1] = [re.sub(r' {2,}', ' ', x).strip() for x in items] + ['\n'.join(lines)]
# 126~130쪽 도서 목록: 번호(하나·둘 …) + 제목, 한 권이 한 줄
for n in range(242, 248):
    r = raw_rows(n)
    heads = [a for a in r if a['sz'] >= 8.5 and a['x0'] < 80]
    labels = [a for a in r if a['sz'] < 7.5 and a['x0'] < 85 and a not in heads]
    titles = [a for a in r if a['x0'] > 85]
    grp = {}
    for t in titles:
        lb = min(labels, key=lambda l: abs((l['y0'] + l['y1']) / 2 - (t['y0'] + t['y1']) / 2)) if labels else None
        grp.setdefault(id(lb), (lb, []))[1].append(t)
    ev = [(h['y0'], 'h', plain(h)) for h in heads]
    for lb, ts in grp.values():
        ts.sort(key=lambda a: a['y0'])
        ev.append((min(lb['y0'], ts[0]['y0']), 'i', plain(lb) + ' ' + '\n'.join(plain(t) for t in ts)))
    ev.sort()
    out, cur = [], []
    for y, k, t in ev:
        if k == 'h':
            if cur: out.append('\n'.join(cur)); cur = []
            out.append(('## ' if t.startswith('마음을 맑게') else '**') + t + ('' if t.startswith('마음을 맑게') else '**'))
        else: cur.append(t)
    if cur: out.append('\n'.join(cur))
    P[n][1] = out
# 126쪽 '둘' 은 세 줄(초전법륜경 세 가지)의 가운데에 인쇄됨
x = P[242][1][2]
P[242][1][2] = x.replace('하나 염신경念身經\n초전법륜경初轉法輪經\n둘 초전법륜경初轉法輪經 (확대본)', '하나 염신경念身經\n둘 초전법륜경初轉法輪經\n초전법륜경初轉法輪經 (확대본)')
assert P[242][1][2] != x, x
# 132쪽 판권지: 인쇄된 줄 그대로 (이름 칸 + 내용 칸)
r = sorted(rows(248), key=lambda a: (round(a['y0']), a['x0']))
lines, prev = [], None
for a in r:
    t = plain(a)
    if prev is not None and abs(a['y0'] - prev['y0']) < 2: lines[-1] = lines[-1] + ' ' + t
    else: lines.append(t)
    prev = a
lines = [re.sub(r' {2,}', ' ', x.replace('\t', ' ')).strip() for x in lines]
eng = [x for x in lines if re.match(r'(This|by the|54,|Kandy)', x)]
rest = [x for x in lines if x not in eng]
i = next(k for k, x in enumerate(rest) if x.startswith('팔정도'))
P[248][1] = ['\n'.join(eng), rest[i - 1], '## ' + rest[i], '\n'.join(rest[i + 1:i + 3]), '\n'.join(rest[i + 3:i + 7]), '\n'.join(rest[i + 7:-1]), rest[-1]]

# 인쇄본에서 줄 사이를 벌려 짠 굵은 게송(경기바탕 굵은 글꼴): 한 줄씩 떨어진 문단을 한 묶음으로 (한 줄짜리 굵은 문단은 › 가 소제목으로 봄)
for n, ps, fns in pages:
    out = []
    for x in ps:
        one = re.fullmatch(r'\*\*[^*\n]+\*\*', x.strip())
        if one and out and re.fullmatch(r'(\*\*[^*\n]+\*\*\n?)+', out[-1].strip()):
            out[-1] = out[-1].rstrip() + '\n' + x.strip(); continue
        out.append(x)
    ps[:] = out
# ---- 하나로 ----
body = ''
for n, ps, fns in pages:
    body += f'=== {n}쪽 ===\n' + '\n\n'.join(clean(x) for x in ps + fns if clean(x)) + '\n\n'
body = re.sub(r'\*\*( ?)\*\*', r'\1', body)
# 줄 끝에서 나뉜 로마자 낱말(인쇄본 214쪽 saṅkhāra- / kkhandha): 이 책은 빠알리 합성어를 붙여 씀
assert body.count('saṅkhāra-kkhandha') == 1
body = body.replace('saṅkhāra-kkhandha', 'saṅkhārakkhandha')
body = body.rstrip() + '\n'

TOC = [('속표지', 1), ('원서 정보', 3), ('일러두기', 4), ('차례', 5), ('시작하는 말', 6), ('Ⅰ. 고苦가 끝나는 길', 11), ('Ⅱ. 바른 견해', 35),
       ('Ⅲ. 바른 사유', 63), ('Ⅳ. 바른 말, 바른 행위, 바른 생계', 90), ('Ⅴ. 바른 노력', 124), ('Ⅵ. 바른 마음챙김', 149), ('Ⅶ. 바른 집중', 184),
       ('Ⅷ. 지혜의 계발', 207), ('맺는말', 231), ('저자 소개', 233), ('부록 1  팔정도의 요소별 분석', 234), ('부록 2  추천 도서 목록', 236),
       ('〈고요한소리〉는', 240), ('마음을 맑게 하는 〈고요한소리〉 도서', 242), ('판권지', 248)]
toc = [{'title': t, 'page': p, 'sub': False} for t, p in TOC]
json.dump({'book': bk, 'edition': ED, 'toc': toc, 'images': [], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '쪽', len(toc), '목차')
