#!/usr/bin/env python3
"""『붓다의 말씀』(DL-0015) 종이책 PDF → content/texts/DL-0015.json
  python3 tools/pdf2text_dl0015.py 책.pdf 목차.txt

PDF 는 앞표지·앞날개(1~2쪽)와 뒤표지(230쪽)를 뺀 3~229쪽을 씀 → 인쇄된 쪽 번호와 같음 (PDF 3쪽 = 1쪽).
인쇄된 줄의 위치·글꼴로 문단을 나눔 (글자는 PDF 그대로, 화면에 안 보이는 조판 기호만 뺌).
- 들여쓴 줄·줄 사이가 벌어진 줄은 새 문단, 꽉 찬 줄 다음 줄은 이어 붙임, 짧은 줄 다음 줄은 줄 바꿈
- 큰 글씨·고딕 굵은 글씨 줄은 '## ' 소제목, 본문 속 굵은 글꼴(PB)은 **굵게**
- 위첨자 숫자는 [^n], 쪽 아래 각주(가는 줄 아래)는 [^n]: … (다음 쪽으로 넘어간 각주는 이어 붙임)
- 오른쪽 맞춤 출전 줄(《長部》 22 …)은 '>> '
- 그림·표(74쪽 팔정도 묶음, 108쪽 12지 연기 표, 속표지 로고)는 잘라서 public/uploads 에
"""
import fitz, json, re, sys
pdf, tocf = sys.argv[1], sys.argv[2]
bk, ED = 'DL-0015', '개정 4판 4쇄'
src = fitz.open(pdf)
OFF = 2  # PDF 쪽 = 인쇄 쪽 + 2
N = 227
images = []


def crop(n, rect, name, dpi=250):
    pg = src[n - 1 + OFF]
    pix = pg.get_pixmap(clip=fitz.Rect(rect), dpi=dpi)
    path = f'public/uploads/{bk}-{name}.png'
    pix.save(path)
    url = '/' + path.replace('public/', ''); images.append(url)
    return url


INVIS = re.compile('[\x07\U000f0000-\U000fffff]')
SANS_B = re.compile(r'Dotum(PB|PM)$')
BOLD = re.compile(r'(PB|BOTF|Bold\w*)$')


def spans_of(l):
    return [s for s in l['spans'] if s['text'].strip()]


def main_size(l):
    ss = [s for s in spans_of(l) if not re.fullmatch(r'\s*\d+\s*', s['text'])]
    return max((s['size'] for s in ss), default=max(s['size'] for s in spans_of(l)))


def line_text(l, foot=False, head=False):
    mx = main_size(l)
    out = []
    first = True
    for s in l['spans']:
        t = INVIS.sub('', s['text']).replace('\t', ' ')
        if not t: continue
        if foot and first and re.fullmatch(r'\s*\d+\s*', t):
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
    L = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            raw = INVIS.sub('', ''.join(s['text'] for s in l['spans']))
            if not raw.strip(): continue
            x0, y0, x1, y1 = l['bbox']
            if y0 > 535: continue  # 쪽 번호·머리글
            foot = y0 > ry
            rawx = ''.join(s['text'] for s in l['spans'])
            L.append(dict(l=l, x0=x0, y0=y0, x1=x1, y1=y1, sz=main_size(l), raw=raw, foot=foot,
                          para=re.match(r'[\s＊*]*\x07', rawx) is not None,
                          head=(not foot) and is_head(l)))
    L.sort(key=lambda a: (round(a['y0']), a['x0']))
    M = []  # 같은 높이의 조각은 하나로
    for a in L:
        if M and abs(a['y0'] - M[-1]['y0']) < 2 and a['foot'] == M[-1]['foot']:
            M[-1]['parts'].append(a); M[-1]['x1'] = a['x1']; M[-1]['raw'] += a['raw']; continue
        a['parts'] = [a]; M.append(a)
    for a in M:
        a['t'] = ''.join(line_text(p['l'], foot=a['foot'], head=a['head']) for p in a['parts'])
    return M


def geom(n):
    return (87.8, 362.8) if n % 2 else (56.7, 331.7)


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
        m = re.match(r'\s*(\d+) +(.*)', a['t'])
        first_digit = a['parts'][0]['l']['spans'] and re.fullmatch(r'\s*\d+\s*', INVIS.sub('', a['parts'][0]['l']['spans'][0]['text']).replace('\t', ' ') or 'x')
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
# 속표지 (1·3·4쪽), 2쪽은 빈 쪽
logo = crop(3, (166, 502, 254, 530), 'calmvoice-logo')
P[1][1] = ['^^ 붓다의 말씀\nBuddhavacanam']
P[2][1] = []
P[3][1] = ['^^ 붓다의 말씀\nBuddhavacanam', ':: 냐나틸로카 스님 엮음 ㅣ 김재성 옮김', f'![#고요한소리]({logo})']
P[4][1] = ['**The Word of the Buddha**', 'An Outline of the Teaching of the Buddha\nin the Words of the Pāli Canon',
           'Compiled, translated and explained by\nNYANATILOKA\n16th ed. 1981', 'Buddhist Publication Society\nKandy‧Sri Lanka']
P[5][1] = [':: Sabbe sattā bhavantu sukhitattā\n**모든 존재가 행복하기를**\n(숫따니빠아따 Sn 145)']
# 74쪽 팔정도 세 묶음, 108쪽 12지 연기 표 → 그림
url74 = crop(74, (56, 70, 335, 330), 'eightfold-groups')
url108 = crop(108, (68, 225, 335, 392), 'paticca-table')


def rows(n, foot=False):
    """같은 높이의 조각을 이은 인쇄 줄 (위→아래)"""
    return [a for a in lines_of(n) if a['foot'] == foot]


def plain(a):
    return re.sub(r'\s+', ' ', a['raw']).strip()


# 14쪽 일러두기: 따로 한 장
P[14][1] = ['## ' + P[14][1][0].replace('**', '').strip()] + P[14][1][1:]
# 74쪽: 팔정도 세 묶음 그림 (이어지는 본문은 그대로)
i = next(i for i, x in enumerate(P[74][1]) if x.startswith('이것이 여래'))
P[74][1] = [f'![#팔정도의 세 묶음 — 1. 바른 견해(正見)·2. 바른 사유(正思惟): III. 지혜(慧 paññā) / 3. 바른 언어(正語)·4. 바른 행위(正業)·5. 바른 생계(正命): I. 윤리(戒 sīla) / 6. 바른 노력(正精進)·7. 바른 마음챙김(正念)·8. 바른 마음집중(正定): II. 마음집중(定 samādhi)]({url74})'] + P[74][1][i:]
# 108쪽: 12지 연기 표 그림
ps = P[108][1]; h = next(i for i, x in enumerate(ps) if x.startswith('## 12지 연기'))
lines108 = '\n'.join(ps[h + 1:]).split('\n')
tail = next(i for i, x in enumerate(lines108) if x.startswith('8-10과 함께'))
tbl = '![#12지 연기 표 — 과거존재: 1. 무명無明 2. 행行 → 업의 과정 (5원인: 1, 2, 8, 9, 10) / 현재존재: 3. 식識 4. 명색名色 5. 육입六入 6. 촉觸 7. 수受 → 윤회의 과정 (5결과: 3, 4, 5, 6, 7); 8. 애愛 9. 취取 10. 유有 → 업의 과정 (5원인: 1, 2, 8, 9, 10) / 미래존재: 11. 생生 12. 노사老死 → 윤회의 과정 (5결과: 3, 4, 5, 6, 7)](' + url108 + ')'
P[108][1] = ps[:h] + ['**' + ps[h][3:] + '**', tbl] + [x for x in lines108[tail:] if x.strip()]

# 15~16쪽 약어: 약어 하나가 한 줄 (인쇄본에서 줄이 넘어간 것은 이어 붙임)
for n in (15, 16):
    out, cur, intro = [], None, []
    left, _ = geom(n)
    for a in rows(n):
        if a['head']: out.append('## ' + plain(a)); continue
        r = a['raw']
        if re.match(r'(AN|Dhp|DN|MN|Paṭis|SN|Vism) ', r.strip()):
            cur = (cur + '\n' if cur else '') + r.strip(); continue
        if cur is not None and a['x0'] > left + 15 and a['x0'] < left + 22:
            cur = cur.rstrip() + ' ' + r.strip(); continue
        if cur is not None: out.append(cur); cur = None
        out.append(None if False else a)
    if cur: out.append(cur)
    res, para = [], ''
    for o in out:
        if isinstance(o, str):
            if para: res.append(para); para = ''
            res.append(o); continue
        r = o['raw']
        if re.match(r'\s*[①②]', r) or abs(o['x0'] - geom(n)[0] - 11.3) < 1:
            if para: res.append(para)
            para = r.lstrip()
        else:
            para += r if para.endswith(' ') else r.lstrip()
    if para: res.append(para)
    P[n][1] = [re.sub(r' {2,}', ' ', x).strip() for x in res]

# 17~18쪽 차례: 인쇄된 줄 그대로 (항목과 쪽 번호를 한 줄로)
for n in (17, 18):
    out = []
    for a in rows(n):
        if a['head'] and plain(a).replace(' ', '') == '차례': out.append('## 차 례'); continue
        t = plain(a).replace('\t', ' ')
        m = re.match(r'(.*?)\s*(。?\s*\d+)\s*$', t)
        kc = lambda x: len(re.findall('[가-힣A-Za-z]', x))
        bold = sum(kc(sp['text']) for p_ in a['parts'] for sp in p_['l']['spans'] if BOLD.search(sp['font'])) > kc(t) * 0.6
        title, num = (m.group(1), m.group(2)) if m else (t, '')
        title = re.sub(r'\s+', ' ', title).strip()
        out.append(('**' + title + '**' if bold else title) + (' ' + num.strip() if num else ''))
    P[n][1] = ['\n'.join(x for x in out if not x.startswith('## '))] if n == 18 else [out[0], '\n'.join(out[1:])]

# 222~224쪽 저서·논문: 책 한 권이 한 줄 (인쇄본에서 넘어간 줄은 이어 붙임), 논문은 인쇄된 대로 한 문단
for n in (222, 223, 224):
    out, cur = [], None
    for a in rows(n):
        r = a['raw']
        if a['head']:
            if cur: out.append(cur); cur = None
            out.append('## ' + plain(a)); continue
        if r.lstrip().startswith('《') and not (out and out[-1] == '## 논문') and not (cur and cur.startswith('초기불교 문헌')) or re.match(r'\s*(metta4u|https://band)', r):
            if cur: out.append(cur)
            cur = r.strip() + (' ' if r.endswith(' ') else ''); continue
        if cur is None: cur = r; continue
        cur = cur + (r if cur.endswith(' ') else r.lstrip())
    if cur: out.append(cur)
    P[n][1] = [re.sub(r' {2,}', ' ', x).strip() for x in out]
# 논문 목록은 223쪽부터 224쪽까지 한 문단 → 224쪽 첫 줄들은 이어지는 글
P[224][1] = [' '.join(x for x in P[224][1] if not re.match(r'(metta4u|https://band)', x))] + [x for x in P[224][1] if re.match(r'(metta4u|https://band)', x)]

# 226쪽 판권지: 인쇄된 줄 그대로
P[226][1] = ['This translation was possible\nby the courtesy of the Buddhist Publication Society\n54, Sangharaja Mawatha P.O. BOX61\nKandy, SriLanka',
             '## 붓다의 말씀',
             '초판 1쇄 발행 2002년 2월 20일\n4판 4쇄 발행 2024년 9월 10일',
             '엮은이 냐나틸로카 스님\n옮긴이 김재성\n펴낸이 하주락·변영섭\n펴낸곳 (사)고요한소리',
             '등록번호 제1-879호 1989. 2. 18.\n주소 서울시 종로구 인사동길 47-5 (우 03145)\n연락처 전화 02-739-6328 팩스 02-723-9804\n부산지부 051-513-6650 대구지부 053-755-6035\n대전지부 042-488-1689 광주지부 02-725-3408\n홈페이지 www.calmvoice.org\n이메일 calmvs@hanmail.net\nISBN 978-89-85186-62-9',
             '값 7,000원']
# 227쪽 소리문고: 한 권이 한 줄 (부제는 다음 줄)
ls = [plain(a) for a in rows(227)]
P[227][1] = ['## ' + ls[0], '\n'.join(ls[1:-2]), '\n'.join(ls[-2:])]

# ---- 하나로 ----
body = ''
for n, ps, fns in pages:
    body += f'=== {n}쪽 ===\n' + '\n\n'.join(clean(x) for x in ps + fns if clean(x)) + '\n\n'
body = re.sub(r'\*\*( ?)\*\*', r'\1', body)
body = body.rstrip() + '\n'

# 목차: 제목을 그 쪽(또는 다음 두 쪽)의 소제목에서 찾아 at 정하기
nz = lambda x: re.sub(r'[^0-9A-Za-z가-힣一-龥]', '', re.sub(r'\[\^\d+\]', '', x))
PG = {int(m.group(1)): m.group(2) for m in re.finditer(r'=== (\d+)쪽 ===\n(.*?)(?=\n=== |\Z)', body, re.S)}
toc = []
for l in open(tocf, encoding='utf-8'):
    if not l.strip(): continue
    sub = l.startswith('  '); f = l.strip().split('\t'); title, pg = f[0], f[1]
    e = {'title': title, 'page': int(pg), 'sub': sub}
    if len(f) > 2: e['toc_title'] = f[2]  # 책 소개 목차에는 '차례'에 인쇄된 표기로
    k = None
    for q in range(int(pg), int(pg) + 2):
        ps = [p for p in PG.get(q, '').split('\n\n') if p.strip()]
        k = next((i for i, p in enumerate(ps) if p.startswith('## ') and nz(p.replace('**', ''))[:10] == nz(title)[:10]), None)
        if k is not None:
            if q != int(pg): print('목차 쪽 옮김:', title, pg, '→', q); e['page'] = q
            break
    if k is None: print('  (소제목 없음)', title, pg)
    elif k > 0: e['at'] = ps[k][3:13]
    toc.append(e)
json.dump({'book': bk, 'edition': ED, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '쪽', len(toc), '목차', len(images), '그림')
