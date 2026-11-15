"""『빨리어 예경독송집』(DL-0031, 빅쿠 알로까담미까 엮음, 아리야승원 2026) PDF → 글로 읽기 본문
  python3 tools/pdf2text_dl0031.py 책.pdf [--dump 쪽,쪽]   →  content/texts/DL-0031.json

PDF 는 한글(Hwp 2024)에서 내보낸 894쪽(419×637pt). PDF 쪽 = 인쇄 쪽 + 25 (앞 25쪽은 쪽 번호 없음).
- 글자는 텍스트 그리기 기록(get_texttrace)에서 읽음: 칠하기(type 0)만 — 굵게 보이게 덧그린 테두리(type 1)와
  보이지 않는 글자(type 3)는 같은 글자의 겹침이라 뺌. 장식 제목처럼 같은 글을 조금씩 옮겨 여러 번 찍은 것도 한 번만.
- **빈칸 되살리기**: 이 PDF 는 낱말 사이 빈칸을 글자로 넣지 않고 자리만 띄운 곳이 많음(buddhaṃsaraṇaṃ…) →
  글자 사이가 글자 크기의 0.08배보다(낱말 안은 0.03배 이하, 빈칸은 0.11배 이상) 벌어지면 빈칸 하나. 여러 빈칸(소리 줄의 줄 맞춤)은 하나로.
- 특수 글꼴: Wingdings 원 숫자(글리프 4~13 → ①~⑩), Wingdings 'v'(글리프 3) → ❖,
  Haansoft 바탕의 사용자 정의 글자 U+F000 = 원 숫자 두 조각(십의 자리 글리프 6·11·18 + 일의 자리) → ⑯~㊵,
  글리프 48(바탕)·3(돋움) → ”, T7 U+E03E(보이지 않는 이음표) → 빈칸.
- 줄 종류: 소리(굴림체·파란색) / 로마자(T1) / 번역(궁서체) / 제목(휴먼옛체·HY견명조) / 출처(☸) / 알림(❖).
  묶음(소리·로마자·번역)은 한 문단, 줄은 인쇄본 줄 그대로(줄 바꿈) — 한글 파일이 글자 단위로 줄을 바꾼 곳이 있어
  줄을 이어 붙이면 낱말이 붙거나 떨어질 수 있음.
"""
import sys, re, json, os, collections
import pymupdf

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = 25


def circ(n): return chr(0x2460 + n - 1) if n <= 20 else chr(0x3251 + n - 21) if n <= 35 else chr(0x32B1 + n - 36)


TENS = {6: 1, 11: 2, 18: 3}
UNITS = {12: 0, 13: 1, 14: 2, 15: 3, 16: 4, 17: 5, 7: 6, 8: 7, 9: 8, 10: 9}


STROKE = set()


def chars_of(page):
    """[(ch, x0, x1, y_base, size, font, color)] — 겹침 뺌, 특수 글자 바꿈"""
    out = []; pend = None; STROKE.clear()
    for sp in page.get_texttrace():
        if sp['type'] == 1:               # 굵게 보이게 덧그린 테두리 = 같은 글자 (굵은 글자 자리만 기억)
            for (u, g, org, bb) in sp['chars']: STROKE.add((round(bb[0]), round(org[1])))
            continue
        f = sp['font']; sz = sp['size']; col = sp['color']
        col = '%02x%02x%02x' % tuple(int(round(c * 255)) for c in (col if len(col) == 3 else (0, 0, 0)))
        for (u, g, org, bb) in sp['chars']:
            c = chr(u)
            if 'Wingdings' in f:
                c = '❖' if g == 3 else (circ(g - 3) if 4 <= g <= 13 else c)
            elif u == 0xF000:
                if g in TENS and pend is None: pend = (TENS[g], bb[0]); continue
                if g in (48, 3): c = '”'
                elif pend is not None and g in UNITS:
                    c = circ(pend[0] * 10 + UNITS[g]); out.append((c, pend[1], bb[2], org[1], sz, f, col)); pend = None; continue
                else: c = '?'
            elif u == 0xE03E: c = ' '
            pend = None
            out.append((c, bb[0], bb[2], org[1], sz, f, col))
    return out


def lines_of(page, bold=False):
    cs = chars_of(page)
    # 같은 글자·같은 자리(1pt 안)는 한 번만
    seen = collections.defaultdict(list); C = []
    for c in cs:
        if c[0].strip() and any(abs(x - c[1]) < 1.2 and abs(y - c[3]) < 1.2 for x, y in seen[c[0]]): continue   # 덧찍기(굵게 보이게)
        seen[c[0]].append((c[1], c[3])); C.append(c)
    C.sort(key=lambda c: (round(c[3], 0), c[1]))
    rows = []
    for c in sorted(C, key=lambda c: c[3]):
        for r in rows:
            if abs(r['y'] - c[3]) < 2.2: r['c'].append(c); break
        else: rows.append({'y': c[3], 'c': [c]})
    L = []
    for r in rows:
        cc = sorted(r['c'], key=lambda c: c[1])
        # 왼쪽·오른쪽이 멀리 떨어진 조각(차례의 쪽 번호 등)은 따로
        segs = [[cc[0]]]
        for a, b in zip(cc, cc[1:]):
            if b[1] - a[2] > 40: segs.append([b])
            else: segs[-1].append(b)
        for sg in segs:
            t = ''; prev = None; inb = False
            for c in sg:
                if prev is not None and c[0] != ' ' and not t.endswith(' ') and c[1] - prev[2] > 0.08 * min(prev[4], c[4]): t += ' '
                if bold and c[0].strip():
                    b = (round(c[1]), round(c[3])) in STROKE
                    if b != inb:
                        if inb and t.endswith(' '): t = t[:-1] + '** '
                        else: t += '**'
                        inb = b
                t += c[0]; prev = c
            if inb: t += '**'
            t = t.replace('****', '')
            trail = t.endswith(' ')
            t = re.sub(r' {2,}', ' ', t).strip()
            if not t: continue
            fonts = collections.Counter()
            for c in sg:
                if c[0].strip(): fonts[(c[5], round(c[4], 1), c[6])] += 1
            (f, sz, col), _ = fonts.most_common(1)[0]
            hf = sum(v for (ff, _, _), v in fonts.items() if ff.startswith(('ÈÞ', 'HYcys')))
            big = [k for k, v in fonts.items() if k[0].startswith(('ÈÞ', 'HYcys')) and k[1] >= 12.5 and v >= 3]
            if (hf >= 0.4 * sum(fonts.values()) or big) and not f.startswith(('ÈÞ', 'HYcys')):     # 제목 글꼴이 섞인 줄(로마자는 다른 글꼴)
                f, sz, col = max(((k, v) for k, v in fonts.items() if k[0].startswith(('ÈÞ', 'HYcys'))), key=lambda kv: kv[1])[0]
            L.append({'t': t, 'trail': trail, 'x0': sg[0][1], 'x1': max(c[2] for c in sg if c[0].strip()), 'y': r['y'], 'font': f, 'size': sz, 'color': col,
                      'fonts': fonts, 'maxsz': max(c[4] for c in sg if c[0].strip())})
    # 장식: 같은 글이 겹쳐 찍힌 줄(그림자) — 같은 글, 가까운 자리
    out = []
    for l in L:
        if any(o['t'] == l['t'] and abs(o['y'] - l['y']) < 6 and abs(o['x0'] - l['x0']) < 6 for o in out): continue
        out.append(l)
    out.sort(key=lambda l: (round(l['y']), l['x0']))
    return out


LAT = re.compile(r'[A-Za-zāīūṃṅñṭḍṇḷĀĪŪṂ]')
HAN = re.compile(r'[가-힣]')


def kind(l):
    f, sz, col, t = l['font'], l['size'], l['color'], l['t']
    if t.startswith('☸'): return 'src'
    if t.startswith('❖'): return 'note'
    if f.startswith(('ÈÞ', 'HYcys')) or sz >= 13: return 'head'
    if col not in ('000000', '171776') and sz >= 10.4 and HAN.search(t) and len(t) < 90 and not t.startswith('('): return 'head'   # 색 제목(T1 글꼴로 든 휴먼옛체)
    nl = len(LAT.findall(t)); nh = len(HAN.findall(t))
    if nl > nh * 2 and nl > 2: return 'roman'
    if 'Gungsuh' in f: return 'tr'
    if col in ('171776',) and ('Gulim' in f or 'Batang' in f): return 'pron'
    return 'text'


def page_label(lines):
    for l in lines:
        m = re.fullmatch(r'-\s*(\d+)\s*-', l['t'])
        if m and l['y'] > 580: return int(m.group(1))
    return None


if __name__ == '__main__':
    pdf = sys.argv[1]
    d = pymupdf.open(pdf)
    if '--dump' in sys.argv:
        for pn in sys.argv[sys.argv.index('--dump') + 1].split(','):
            print('=== PDF', pn)
            for l in lines_of(d[int(pn) - 1]):
                print(f"{kind(l):5} {round(l['x0']):3} {round(l['y']):3} {l['font'][:10]:10} {l['size']:4} {l['color']} | {l['t']}")
        sys.exit()


# ---------------------------------------------------------------- 본문 만들기
DIVIDERS = {28, 30, 46, 92, 94, 108, 114, 132, 220, 322, 380, 390, 392, 430, 444, 456, 464, 476, 498, 550, 612, 638,
            726, 766, 780, 802, 818, 878}     # 장 표지(배경 그림 + 장 이름·작은 차례) — 글은 넣지 않음(다음 쪽 장 제목과 겹침)
TOC_PAGES = range(5, 26)
NUMSTART = re.compile(r'^(\d+\s*\.|[①-⑳㉑-㉟]|\(\d+\))')


def is_center(l):
    c = (l['x0'] + l['x1']) / 2
    return l['x0'] > 85 and abs(c - 209.5) < 18


def body_paras(L, ys=None):
    out = []; cur = None; prev = None; last_y = 0
    if ys is None: ys = []
    meta = {}                     # 문단 번호 → [(줄, 종류)] — 산문 문단의 줄 이어 붙이기에 씀
    for l in L:
        while len(ys) < len(out): ys.append(last_y)
        last_y = l['y']
        if l['y'] < 55 and l['size'] <= 9.5: continue                        # 쪽 머리글
        if re.fullmatch(r'-\s*\d+\s*-', l['t']) and l['y'] > 580: continue    # 쪽 번호
        k = kind(l); t = l['t']
        box = re.match(r'□\s*(\d+)\s*(.*)', t)
        if box: t = box.group(1) + ' ' + box.group(2); k = 'head'
        if k == 'head':
            small = l['font'].startswith('HYcys') and l['size'] < 13 or re.fullmatch(r'포살\s*․\s*축\s*원|<.*>|\(.*\)', t)
            if ' ☸' in t and not small:
                t, src = t.split(' ☸', 1); out.append('## ' + t.strip()); out.append('☸' + src); cur = None; prev = (l, 'head'); continue
            if small: out.append((':: ' if is_center(l) else '') + t); cur = None
            elif l['maxsz'] >= 19.5: out.append('^^ ' + t); cur = None
            else:
                if out and cur is None and prev is not None and prev[1] == 'head' and l['y'] - prev[0]['y'] < 1.7 * l['size'] and out[-1].startswith('## ') and abs(prev[0]['maxsz'] - l['maxsz']) < 0.8:
                    out[-1] += ' ' + t                                        # 두 줄 제목
                else: out.append('## ' + t)
                cur = None
            prev = (l, 'head'); continue
        if k in ('src', 'note') or (prev is not None and prev[1] == 'note' and k != 'src' and l['x0'] > prev[0]['x0'] + 5 and l['y'] - prev[0]['y'] < 1.9 * l['size']):
            if k == 'note' or cur is None: out.append(t); cur = len(out) - 1; meta[cur] = [(l, k)]
            else: out[cur] += '\n' + t; meta.setdefault(cur, []).append((l, 'note'))
            prev = (l, 'note' if k == 'note' or prev[1] == 'note' else k); continue
        new = cur is None or prev is None
        if not new:
            pl, pk = prev; gap = l['y'] - pl['y']
            if pk == 'tr' and k in ('pron', 'roman'): new = True
            elif pk == 'tr' and k != 'tr' and gap > 1.9 * l['size']: new = True
            elif gap > 2.5 * l['size']: new = True
            elif k == 'pron' and pk not in ('pron',): new = True
            elif k in ('text',) and pk in ('text',) and gap > 1.9 * l['size']: new = True
            elif k == 'tr' and pk == 'tr' and gap > 1.9 * l['size']: new = True
            elif NUMSTART.match(t) and k != 'tr' and pk not in ('pron',) and not (k == 'roman' and pk == 'pron'): new = True
        if new:
            out.append((':: ' if is_center(l) and k not in ('pron', 'roman', 'tr') else '') + t); cur = len(out) - 1; meta[cur] = [(l, k)]
        else: out[cur] += '\n' + t; meta.setdefault(cur, []).append((l, k))
        prev = (l, k)
    while len(ys) < len(out): ys.append(last_y)
    # 산문 문단(소리·로마자 줄이 없는 글)은 인쇄본에서 줄 끝까지 찬 줄을 이어 붙임 — 줄 끝에 빈칸이 찍혀 있으면 빈칸,
    # 없으면(낱말 가운데에서 줄이 바뀐 곳: '뜻|이며', '합|송') 바로 붙임 (운영자 요청, 2026-11-15)
    right = max((l['x1'] for l in L if l['y'] > 55 and l['size'] >= 10), default=360)
    for n, ls in meta.items():
        if len(ls) < 2 or any(k in ('pron', 'roman') for _, k in ls) or out[n].startswith(('## ', '^^ ', ':: ')): continue
        if out[n].count('\n') != len(ls) - 1: continue
        parts = out[n].split('\n'); res = parts[0]
        for (pl, _), part in zip(ls, parts[1:]):
            if pl['x1'] >= right - 22: res += (' ' if pl['trail'] or re.search(r'[.?!,:;]$', pl['t']) or (pl['t'].endswith(')') and not re.match(r'[을를이가은는의에과와도로]', part))
                                                 or (re.search(r'[A-Za-zāīūṃṅñṭḍṇḷ]$', pl['t']) and re.match(r'[가-힣]', part)) else '') + part
            else: res += '\n' + part
        out[n] = res
    return out


SHOWN = {}     # 차례 화면에는 인쇄된 쪽 번호 그대로 보일 것
TMETA = []     # 차례 줄마다 인쇄본의 자리(들여쓰기 x·위 줄과의 간격·제목 글꼴)


def toc_lines(d):
    """차례 쪽(PDF 5~25) → [(단계, 제목, 쪽 번호|None)] — 단계: 0 큰 묶음(예경 Ⅰ 등), 1 묶음, 2 쪽 번호가 있는 항목, 3 □ 항목"""
    R = []; TMETA.clear()
    for pn in TOC_PAGES:
        L = lines_of(d[pn - 1], bold=True)
        rows = []; py = None
        for l in L:
            bt = re.sub(r'(\*\*)?포살\s*(\*\*)?․\s*(\*\*)?축\s*(\*\*)?원(\*\*)?', '', l['t']).strip()
            tt = bt.replace('**', '').strip()
            if rows and abs(rows[-1]['y'] - l['y']) < 8 and re.fullmatch(r'\d*', tt) and not re.search(r'\d$', rows[-1]['t']):
                if tt: rows[-1]['t'] += ' ' + tt
                continue
            l = dict(l); l['t'] = tt; l['bt'] = bt
            rows.append(l)
        for l in rows:
            t = l['t']
            if t in ('차 례', '') or re.fullmatch(r'\(빨 ?리 ?어 ?\)', t): continue
            m = re.match(r'(.*?)\s*-{3,}\s*(\d+)$', t) or re.match(r'(.*?)\s*(\d{1,3})$', t)
            page = None
            if m and not re.fullmatch(r'[□\d\s]*', m.group(1)):
                title, page = m.group(1).strip(), int(m.group(2))
            else: title = t
            box = re.match(r'□\s*(\d+)\s*(.*)', title)
            if box: title = box.group(1) + ' ' + box.group(2)
            if l['font'].startswith('HYcys') and l['size'] >= 12: lev = 0
            elif box and page is None: lev = 3
            elif page is None: lev = 1
            else: lev = 2
            gap = l['y'] - py if py is not None else 0; py = l['y']
            if lev == 0 and R and R[-1][0] == 0 and l['size'] < 14 and R[-1][2] is None: R[-1] = (0, R[-1][1] + ' ' + title, None); continue   # 예 경 + Ⅰ
            R.append((lev, title, page))
            disp = re.sub(r'\s*(\*\*)?\s*(-{3,}\s*)?\d{1,3}\s*(\*\*)?\s*$', '', l['bt']) if page else l['bt']    # 굵게 표시(**)는 그대로, 쪽 번호만 뗌
            disp = re.sub(r'□\s*', '', disp); disp = re.sub(r'\*\*\s*\*\*', ' ', disp).strip()
            if disp.count('**') % 2: disp += '**'
            TMETA.append({'x': l['x0'], 'gap': gap, 'size': l['size'], 'head': l['font'].startswith(('ÈÞ', 'HYcys')), 'disp': disp})
    # 쪽 번호가 앞뒤 순서와 어긋나는 □ 항목(차례의 잘못 찍힌 쪽 번호, 예: '□6 출가자의 오염원 668')은 쪽 없는 소제목으로
    for n, (lev, title, page) in enumerate(R):
        if lev == 2 and re.match(r'\d+ ', title):
            pv = next((p for (lv, tt, p) in reversed(R[:n]) if p), 0); nx = next((p for (lv, tt, p) in R[n + 1:] if p), 10 ** 6)
            if not (pv <= page <= nx): print('  차례 쪽 번호가 순서에 안 맞음 → 소제목으로:', title, page); R[n] = (3, title, None); SHOWN[title] = page
    return R


PICS = {'fb533702': ('DL-0031-lion.png', '#사자상 그림'), 'a2dd19b2': ('DL-0031-leaf.png', '#보리수 잎 그림'),
        '629f15a4': ('DL-0031-leaf2.png', '#보리수 잎 그림')}


def save_pics(d):
    """쪽마다 따로 놓인 장식 그림(사자상·보리수 잎) — 흰 바탕은 투명하게. 글 뒤에 깔린 바탕 그림·장 표지 그림은 넣지 않음"""
    import hashlib, io
    from PIL import Image
    done = set(); where = {}
    for i, p in enumerate(d):
        if i + 1 in DIVIDERS: continue
        for x in p.get_images(full=True):
            raw = d.extract_image(x[0])['image']; h = hashlib.md5(raw).hexdigest()[:8]
            if h not in PICS: continue
            r = p.get_image_rects(x[0])[0]
            where.setdefault(i + 1, []).append((r.y0, h))
            if h in done: continue
            im = Image.open(io.BytesIO(raw)).convert('RGBA'); px = im.load()
            for yy in range(im.height):
                for xx in range(im.width):
                    rr, gg, bb, aa = px[xx, yy]; m = min(rr, gg, bb)
                    if m > 235: px[xx, yy] = (rr, gg, bb, int(max(0, (255 - m) * 255 / 20)))
            im.save(os.path.join(REPO, 'public/uploads', PICS[h][0])); done.add(h)
    return where


def build(pdf):
    d = pymupdf.open(pdf)
    pages = []        # [(label, [paras])]
    T = toc_lines(d); WH = save_pics(d)
    for i in range(1, d.page_count + 1):
        lab = f'{i - OFF}쪽' if i > OFF else ''
        L = lines_of(d[i - 1])
        if i == 1: continue                                                # 빈 앞표지 쪽
        if i in DIVIDERS: pages.append((lab, [])); continue
        if i == 2:
            pages.append((lab, ['^^ 빨리어 예경독송집'])); continue
        if i in TOC_PAGES:
            if i == TOC_PAGES[0]: pages.append((lab, ['## 차 례', toc_block(T)]))   # 차례 21쪽은 한 화면으로
            continue
        ys = []; ps = body_paras(L, ys)
        for y0, h in sorted(WH.get(i, [])):
            k = next((n for n, y in enumerate(ys) if y > y0), len(ps))
            ps.insert(k, f'![{PICS[h][1]}](/uploads/{PICS[h][0]})'); ys.insert(k, y0)
        pages.append((lab, ps))
    return d, pages, T


def toc_block(T):
    """인쇄본 차례처럼: 들여쓰기는 인쇄된 자리(x)로, 굵게는 제목 글꼴(휴먼옛체·HY견명조)일 때만,
    큰 묶음 앞과 인쇄본에서 줄 사이가 벌어진 곳(30pt 넘게)에는 빈 간격 ~ (운영자 요청, 2026-11-15)"""
    out = []
    for (lev, title, page), mt in zip(T, TMETA):
        pg = page or SHOWN.get(title)
        dash = '' if mt['x'] <= 64 or lev == 0 else '- ' if mt['x'] <= 80 else '-- '
        t = mt['disp'] if lev != 0 else title
        if (mt['head'] or lev == 0) and '**' not in t: t = f'**{t}**'
        line = dash + t + (f' | {pg}' if pg else '')
        if out and out[-1] != '~' and (lev in (0, 1) or (lev == 3 and mt['head']) or mt['gap'] > 30): out.append('~')
        out.append(line)
    return '%% ' + '\n'.join(out)


KEY = lambda x: re.sub(r'[^가-힣a-zāīūṃṅñṭḍṇḷ]', '', x.lower())


def find_head(ps, title):
    """쪽 안에서 목차 제목과 가장 비슷한 제목 문단 번호 (요일·날 표시·번호는 빼고 비교)"""
    import difflib
    strip = lambda x: KEY(re.sub(r'^\s*(\d+\s*\.?|[①-⑳])\s*', '', re.sub(r'[월화수목금토일]요일|[가-힣]+\s번째\s날|[가-힣]+째\s날', '', x)))
    tk = strip(title); best = (0, None)
    for k, p in enumerate(ps):
        if not p.startswith(('## ', '^^ ')): continue
        hk = strip(re.sub(r'^(## |\^\^ )', '', p))
        if not hk or not tk: continue
        n = min(len(hk), len(tk), 10)
        r = difflib.SequenceMatcher(None, hk[:n + 2], tk[:n + 2]).ratio()
        if hk[:4] in tk or tk[:4] in hk: r = max(r, 0.8)
        if r >= 0.8: return k                     # 앞에서부터 처음 맞는 제목
        if r > best[0]: best = (r, k)
    return best[1] if best[0] >= 0.55 else None


def find_any(ps, title):
    """제목 문단이 아닌 한 줄 문단(검은 글씨로 찍힌 제목) — 찾으면 ## 를 붙임"""
    tk = KEY(title)
    H = lambda x: re.sub(r'[^가-힣]', '', x)[:3]
    for k, p in enumerate(ps):
        if '\n' in p or p.startswith(('## ', '^^ ', '%% ')): continue
        if H(p) and H(p) == H(title) and re.match(r'\d*', p).group() == re.match(r'\d*', title).group(): ps[k] = '## ' + p; return k
    return None


def find_sub(pages, start, title):
    import difflib
    m = re.match(r'(\d+)\s+(.*)', title); num, rest = m.group(1), KEY(m.group(2))
    first = None
    for i in range(start, min(start + 80, len(pages) + 1)):
        for k, p in enumerate(pages[i - 1][1]):
            mm = re.match(r'## ' + num + r' (.*)', p)
            if not mm: continue
            r = difflib.SequenceMatcher(None, KEY(mm.group(1))[:len(rest) + 4], rest).ratio()
            if r >= 0.45: return i, k
            if first is None: first = (i, k)
    return first


def make_toc(pages, T):
    """읽기 목차: 큰 묶음·묶음(장 표지 쪽) + 쪽 번호 항목 = 장, □ 항목 = 소제목"""
    idx = {lab: n for n, (lab, ps) in enumerate(pages, 1) if lab}
    div = {f'{p - OFF}쪽' for p in DIVIDERS}
    used = set(); toc = []
    toc.append({'title': '속표지', 'page': 1, 'sub': False})
    toc.append({'title': '테라와다 불교', 'page': 2, 'sub': False})
    toc.append({'title': '차례', 'page': 4, 'sub': False})
    pend = []        # 쪽 없는 묶음 제목들
    last = 4
    for n, (lev, title, page) in enumerate(T):
        if page is None and lev in (0, 1, 3):
            nxt = next((p for (lv, tt, p) in T[n + 1:] if p), None)
            # 다음 쪽 항목 전에 있는 아직 안 쓴 장 표지 쪽
            cand = [i for lab, i in idx.items() if lab in div and i not in used and i > last and (nxt is None or i < idx.get(f'{nxt}쪽', 10 ** 9))]
            grp = lev in (0, 1) or (lev == 3 and re.search(r'\((저녁예경|포살일|[가-힣]+\s*\d+:\d\d)\)', title))
            if cand and grp:
                i = min(cand); used.add(i); last = i; toc.append({'title': title, 'page': i, 'sub': False}); continue
            if lev == 3:
                # □ 소제목: 앞 장 시작 쪽부터 찾음
                f = find_sub(pages, last, title)
                if f:
                    i, k = f; e = {'title': title, 'page': i, 'sub': True}
                    if k: e['at'] = re.sub(r'^(## |\^\^ )', '', pages[i - 1][1][k])[:24]
                    toc.append(e); last = i
                else: print('  ! 소제목 못 찾음:', title)
            continue
        if page is None: continue
        i = idx.get(f'{page}쪽')
        if i is None: print('  ! 쪽 없음', title, page); continue
        if i - 1 >= 1 and pages[i - 2][0] in div and (i - 1) not in used and not pages[i - 2][1]:
            used.add(i - 1); toc.append({'title': title, 'page': i - 1, 'sub': False}); last = i; continue
        used.add(i)
        e = {'title': title, 'page': i, 'sub': False}
        k = find_head(pages[i - 1][1], title)
        if k is None: k = find_any(pages[i - 1][1], title)
        ps = pages[i - 1][1]
        while k and '\n' not in ps[k - 1] and len(re.sub(r'^## ', '', ps[k - 1])) <= 30 and not ps[k - 1].startswith(('%%', '![')) \
                and (not ps[k - 1].startswith('## ') or re.search(r'니까야|빠타|빠따|법구경', ps[k - 1])
                     or (len(re.sub(r'[^가-힣]', '', ps[k - 1])) <= 5 and not re.search(r'\d', ps[k - 1]))): k -= 1   # 제목 위의 꼬리표(월요일·경전 출처·포살 ․ 축원)도 함께
        if k: e['at'] = re.sub(r'^(## |\^\^ )', '', pages[i - 1][1][k])[:24]
        elif k is None and pages[i - 1][0] not in div: print('  ? 제목 못 맞춤', page, title)
        toc.append(e); last = i
    toc.append({'title': '도서 안내', 'page': idx['868쪽'], 'sub': False})
    toc.append({'title': '판권지', 'page': idx['869쪽'], 'sub': False})
    return toc


if __name__ == '__main__':
    d, pages, T = build(sys.argv[1])
    toc = make_toc(pages, T)
    # 장 표지 쪽: 표지에 크게 인쇄된 장 이름만 넣음(작은 차례·겹쳐 찍은 그림자 글은 뺌) — 듣기가 장 이름부터 읽게
    for t in toc:
        if not t['sub'] and not pages[t['page'] - 1][1]: pages[t['page'] - 1][1].append('^^ ' + t['title'])
    body = '\n\n'.join(f'=== {lab} ===\n' + '\n\n'.join(ps) for lab, ps in pages)
    # 줄 첫머리 번호와 글이 붙은 곳('10.따뽀 …', '14.아침경')은 번호 뒤에 빈칸 (운영자 요청, 2026-11-15 — 교정)
    NUMSP = re.compile(r'(?m)^((?:## |\^\^ |:: |%% |-{1,3} |\*\*)?)(\d{1,3})\.(?=[^\s\d.])')
    body = NUMSP.sub(r'\1\2. ', body)
    for t in toc:
        t['title'] = NUMSP.sub(r'\1\2. ', t['title'])
        if t.get('at'): t['at'] = NUMSP.sub(r'\1\2. ', t['at'])
    imgs = sorted({'/uploads/' + v[0] for v in PICS.values() if '/uploads/' + v[0] in body})
    out = {'book': 'DL-0031', 'edition': '증보판 (초판)', 'toc': toc, 'images': imgs, 'body': body}
    p = os.path.join(REPO, 'content/texts/DL-0031.json')
    json.dump(out, open(p, 'w'), ensure_ascii=False, indent=1)
    print('쪽', len(pages), '목차', len(toc), '장', sum(not t['sub'] for t in toc), '글자', len(body))
