"""『법요집』(DL-0036, 빅쿠 알로까담미까 엮음, 아리야승원 이판 2015) PDF → 글로 읽기 본문
  python3 tools/pdf2text_dl0036.py 책.pdf [--dump 쪽,쪽]   →  content/texts/DL-0036.json
  다음에 늘: python3 tools/join_pagewords.py DL-0036 --write  (쪽 경계에서 갈라진 낱말 — tools/pageword_fixes.json)

『빨리어 예경독송집』(DL-0031) 도구를 바탕으로 함. PDF 는 한글(Hwp 2024)에서 내보낸 756쪽, PDF 쪽 = 인쇄 쪽 + 12.
- 빈칸이 글자로 없는 PDF — 줄 안에서는 글자 사이 자리로 빈칸을 되살리고(DL-0031 과 같음),
  끝까지 찬 줄을 이을 때는 ① 이 책 안(줄 가운데)에서 같은 두 조각을 붙여 썼는지 띄어 썼는지 ② 없으면 kiwi 형태소 점수
  ③ 점수 차가 작으면 kiwi 띄어쓰기로 정함(wrap_sep) — 한글 파일이 낱말 사이에서도 낱말 가운데에서도 줄을 바꿈.
- 특수 글자: Wingdings 글리프 번호 → ❖ 📖 ❶~❿ ①~⑩ (WD, 그림으로 하나씩 확인), 한컴 바탕 U+F000 → ㉑~㉚·⑯·‘ ’ (HF),
  '◯' 위에 겹쳐 찍은 숫자 → ⑱ 등.
- 줄 종류(kind): 휴먼옛체·HY견명조·□ 제목 → ## (20pt 넘는 장 제목은 ^^), 대부분 색 글씨인 줄(📖·❖ 항목, 소제목) → **…** 따로 문단,
  ☸ 경전 출처 → 따로 문단, 궁서체(경전 인용)·바탕(설명)은 보통 글. 독송 묶음(소리 줄·로마자 줄·번역 줄)은 한 문단, 줄은 인쇄본대로.
- 문단: 줄 사이 17~18pt 는 같은 문단, 게송·가운데 맞춤 인용 22pt 도 같은 문단(줄 바꿈), 25pt 넘으면 새 문단.
- 편 표지 10쪽(DIVIDERS)은 글을 넣지 않고 편 이름만(^^), 차례 8쪽(PDF 5~12)은 한 화면 %% 차례.
- 원문 대조: 글자(빈칸·표시 빼고)가 PDF 글자와 책 전체에서 같음을 확인함(2026-11-19, 340,814자).
"""
import sys, re, json, os, collections
import pymupdf

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = 12


def circ(n): return chr(0x2460 + n - 1) if n <= 20 else chr(0x3251 + n - 21) if n <= 35 else chr(0x32B1 + n - 36)


TENS = {6: 1, 11: 2, 18: 3}
UNITS = {12: 0, 13: 1, 14: 2, 15: 3, 16: 4, 17: 5, 7: 6, 8: 7, 9: 8, 10: 9}


STROKE = set()
LP = {}           # 줄(id) → 문단 번호 (body_paras 가 적음)
BOXT = set()      # 인쇄본에서 □ 안에 번호가 찍힌 제목 (□ 를 되살려 화면에서 네모 테두리 번호로 — 운영자 요청, 2026-11-16)
GUNG = set()      # 궁서체(굵게 보이는 글꼴) 글자 자리
# 인쇄본에서 굵게(진하게) 보이는 글꼴 — 쪽 그림으로 하나씩 확인 (2026-11-19 다시 검수): 궁서체(경전 인용·번역 줄), 휴먼옛체·HY견명조(제목·용어),
# T2·T25(☸ 출처 줄의 경 이름 — 굵은 고딕). 가는 글꼴: T3·T11·T12·T13·T18·T21(바탕 — 풀이·괄호), 굴림·굴림체(소리 줄·출처), 돋움
HEAVY = ('Gungsuh', 'ÈÞ', 'HYcys', 'T2', 'T25')
def heavy(f): return f.startswith(HEAVY) and f not in ('T21',)


WD = {3: '❖', 4: '📖', 5: '❶', 6: '❷', 7: '①', 8: '②', 9: '③', 10: '④', 11: '⑤', 12: '⑥', 13: '⑦', 14: '⑧', 15: '❸',
      17: '❹', 18: '❺', 19: '❻', 20: '❼', 21: '❽', 22: '❾', 23: '⑨', 24: '⑩', 25: '❿'}
HF = {12: '㉑', 13: '㉑', 14: '㉒', 15: '㉓', 16: '㉔', 17: '㉕', 18: '㉖', 19: '㉗', 20: '㉘', 21: '㉙', 22: '㉚', 23: '㉚', 26: '‘', 27: '’', 28: '⑯'}


def chars_of(page):
    """[(ch, x0, x1, y_base, size, font, color)] — 겹침 뺌, 특수 글자 바꿈 (『법요집』 PDF 의 글리프 번호 — 그림으로 하나씩 확인)"""
    out = []; STROKE.clear(); GUNG.clear()
    for sp in page.get_texttrace():
        if sp['type'] == 1:
            for (u, g, org, bb) in sp['chars']: STROKE.add((round(bb[0]), round(org[1])))
            continue
        f = sp['font']; sz = sp['size']; col = sp['color']
        col = '%02x%02x%02x' % tuple(int(round(c * 255)) for c in (col if len(col) == 3 else (0, 0, 0)))
        for (u, g, org, bb) in sp['chars']:
            c = chr(u)
            if 'Gungsuh' in f: GUNG.add((round(bb[0]), round(org[1])))
            if 'Wingdings' in f:
                if u == 32: c = ' '
                elif g in WD: c = WD[g]
                else: print('  ? Wingdings 글리프', g, u); c = '?'
            elif u == 0xF000:
                if g in HF: c = HF[g]
                else: print('  ? F000 글리프', g); c = '?'
            elif u == 0xE03E: c = ' '
            out.append((c, bb[0], bb[2], org[1], sz, f, col))
    # '◯' 위에 겹쳐 찍은 숫자(◯18 → ⑱)
    res = []; skip = set()
    for n, c in enumerate(out):
        if n in skip: continue
        if c[0] == '\u25ef':
            dg = [(m, o) for m, o in enumerate(out) if m != n and o[0].isdigit() and abs(o[3] - c[3]) < 2 and o[1] >= c[1] - 1 and o[2] <= c[2] + 1]
            if dg:
                num = int(''.join(o[0] for m, o in sorted(dg, key=lambda z: z[1][1])))
                for m, _ in dg: skip.add(m)
                res.append((circ(num),) + c[1:]); continue
        res.append(c)
    return res


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
                    b = (round(c[1]), round(c[3])) in STROKE or (bold == 'all' and (round(c[1]), round(c[3])) in GUNG) or (bold == 'heavy' and heavy(c[5]))
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
            fc = next((c[6] for c in sg if c[0].strip() and c[0] not in '📖❖'), '000000')     # 첫 글자 색(아이콘 뒤)
            fh = next((heavy(c[5]) for c in sg if c[0].strip() and c[0] not in '📖❖'), False)  # 첫 글자(아이콘 뒤)가 굵은 글꼴인지
            L.append({'fc': fc, 'fh': fh, 't': t, 'trail': trail, 'x0': sg[0][1], 'x1': max(c[2] for c in sg if c[0].strip()), 'y': r['y'], 'font': f, 'size': sz, 'color': col,
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
    """『법요집』 줄 종류: head(휴먼옛체·HY견명조·□ 제목) / chead(색 글씨 소제목 줄 — 📖·❖ 항목 등) / src(☸ 경전 출처) /
    note(검은 ❖ 알림) / pron(빠알리 한글 소리 — 굴림체, 장음 '-') / roman / tr(궁서체 — 경전 인용) / text"""
    f, sz, col, t = l['font'], l['size'], l['color'], l['t']
    if t.startswith('☸'): return 'src'
    if f.startswith(('ÈÞ', 'HYcys')) or sz >= 13 or re.match(r'□\s*\d', t): return 'head'
    if t.startswith('❖') and col == '000000': return 'note'
    colored = sum(v for (ff, _, cc), v in l['fonts'].items() if cc != '000000'); allc = sum(l['fonts'].values())
    if 'Gungsuh' not in f and HAN.search(t) and (col != '000000' and colored >= 0.6 * allc or l.get('fc', '000000') != '000000' and colored >= 0.25 * allc): return 'chead'   # 색 글자로 시작하는 줄(뒤에 검은 출처가 붙은 소제목)도
    nl = len(LAT.findall(t)); nh = len(HAN.findall(t))
    if nl > nh * 2 and nl > 2: return 'roman'
    if 'Gungsuh' in f: return 'tr'
    if 'Gulim' in f and len(re.findall(r'[가-힣]-', t)) >= 2: return 'pron'
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
DIVIDERS = {17, 83, 131, 247, 347, 443, 569, 651, 671, 709}     # 편 표지(배경 그림 + 편 이름·장 목록) — 글은 넣지 않음
TOC_PAGES = range(5, 13)
NUMSTART = re.compile(r'^(\d+\s*\.|[①-⑳㉑-㉟]|\(\d+\))')


def is_center(l):
    c = (l['x0'] + l['x1']) / 2
    return l['x0'] > 85 and abs(c - 209.5) < 18


def body_paras(L, ys=None):
    out = []; cur = None; prev = None; last_y = 0
    if ys is None: ys = []
    global RIGHT
    RIGHT = max((l['x1'] for l in L if l['y'] > 55 and l['size'] >= 10), default=360)
    meta = {}                     # 문단 번호 → [(줄, 종류)] — 산문 문단의 줄 이어 붙이기에 씀
    for l in L:
        while len(ys) < len(out): ys.append(last_y)
        last_y = l['y']
        if l['y'] < 55 and l['size'] <= 9.5: continue                        # 쪽 머리글
        if re.fullmatch(r'-\s*\d+\s*-', l['t']) and l['y'] > 580: continue    # 쪽 번호
        k = kind(l); t = l['t']
        box = re.match(r'□\s*(\d+)\s*(.*)', t)
        if box: t = box.group(1) + ' ' + box.group(2); k = 'head'; BOXT.add(t)
        # 소제목 줄 가려내기 (2026-11-19 다시 검수 — 쪽 그림과 대조): 색 글씨·제목 글꼴 줄이라도
        #  ① ❖ 로 시작하는 줄은 알림·항목 문단(굵은 글꼴 부분만 굵게) — '❖ 디가니까야는 23단계…', '❖ 근접삼매 수행(10) : …'
        #  ② 첫 글자가 가는 글꼴인 색 글씨 줄은 보통 문단('세존께서 오온을 … 말씀하셨다.' 같은 남색 이야기 글), 다만
        #     제목 바로 아래 괄호 줄('(위빳사나 냐나, vipassanā-ñāṇa)')은 그 제목에 붙이고, 가운데 맞춤 괄호 줄은 가운데 보통 글
        if k in ('head', 'chead') and l['maxsz'] < 12.5 and not box:
            if t.startswith('❖'): k = 'note'
            elif not l['fh'] and not (t.startswith('(') and out and out[-1].startswith('^^ ')):
                if t.startswith('(') and out and out[-1].startswith('## ') and cur is None and prev is not None and prev[1] in ('head', 'chead') and l['y'] - prev[0]['y'] < 1.9 * l['size'] and not is_center(l):
                    out[-1] += ' ' + t; prev = (l, prev[1]); continue
                k = 'text'
        if k == 'chead' and prev is not None and prev[1] not in ('head', 'chead') and l['y'] - prev[0]['y'] < 1.9 * l['size'] and prev[0]['x1'] >= RIGHT - 22:
            k = 'tr' if 'Gungsuh' in l['font'] else 'text'                          # 끝까지 찬 줄에 이어지는 줄 — 문단 가운데의 색 글자일 뿐
        if k == 'chead':
            # 장 제목(^^) 바로 아래 괄호 풀이 줄은 장 제목에 붙임
            if out and out[-1].startswith('^^ ') and prev is not None and prev[1] == 'head' and t.startswith('('):
                out[-1] += ' ' + t; prev = (l, 'head'); continue
            # 색 소제목 줄(📖·❖ 항목 등)은 휴먼옛체 제목 줄과 같은 인쇄 모양이라 똑같이 ## 소제목으로 (2026-11-19 다시 검수 — 전에는 ## 와 **…** 가 섞여 있었음).
            # 가운데 맞춤 괄호 풀이 줄('(삼마 상깝빠, …)')은 인쇄본에서 가는 글씨라 굵게 하지 않음
            if is_center(l) and t.startswith('('): out.append(':: ' + t)
            elif out and cur is None and prev is not None and prev[1] == 'chead' and l['y'] - prev[0]['y'] < 1.9 * l['size'] and out[-1].startswith('## '):
                out[-1] = out[-1] + (wrap_sep(out[-1], t, prev[0]) if prev[0]['x1'] >= RIGHT - 22 else ' ') + t   # 두 줄로 찍힌 색 소제목
            else: out.append('## ' + t)
            cur = None; prev = (l, 'chead'); continue
        if k == 'head':
            if ' ☸' in t:
                t, src = t.split(' ☸', 1); out.append('## ' + t.strip()); out.append('☸' + src); cur = None; prev = (l, 'head'); continue
            if l['maxsz'] >= 19.5: out.append('^^ ' + t); cur = None
            else:
                if not box and out and cur is None and prev is not None and prev[1] == 'head' and l['y'] - prev[0]['y'] < 1.7 * l['size'] and out[-1].startswith('## ') and abs(prev[0]['maxsz'] - l['maxsz']) < 0.8 and not re.match(r'## □?\d+ ', out[-1]):
                    out[-1] += ' ' + t                                        # 두 줄 제목
                else: out.append('## ' + t)
                cur = None
            prev = (l, 'head'); continue
        if k in ('src', 'note') or (prev is not None and prev[1] == 'note' and k != 'src' and l['x0'] > prev[0]['x0'] + 5 and l['y'] - prev[0]['y'] < 1.9 * l['size']):
            if k in ('note', 'src') or cur is None: out.append((':: ' if k == 'note' and abs((l['x0'] + l['x1']) / 2 - 209.5) < 18 and l['x0'] > 65 else '') + t); cur = len(out) - 1; meta[cur] = [(l, k)]
            else: out[cur] += '\n' + t; meta.setdefault(cur, []).append((l, 'note'))
            prev = (l, 'note' if k == 'note' or (prev is not None and prev[1] == 'note') else k); LP[id(l)] = cur; continue
        new = cur is None or prev is None
        if not new:
            pl, pk = prev; gap = l['y'] - pl['y']
            # 이 책: 보통 줄 사이 17~18pt, 게송·가운데 맞춤 인용 22pt, 문단 사이 30pt 넘음
            if gap > 2.3 * l['size']: new = True
            elif pk == 'note' and pl['t'].startswith('❖') and not (abs((l['x0'] + l['x1']) / 2 - 209.5) < 18 and abs((pl['x0'] + pl['x1']) / 2 - 209.5) < 18 and pl['x0'] > 65): new = True   # 가운데 맞춘 두 줄 ❖ 알림은 한 문단                                          # ❖ 줄 다음의 들여쓰지 않은 줄은 새 문단('❖ 상가의 의미' 다음 본문)
            elif pk == 'tr' and k in ('pron', 'roman') and gap > 1.9 * l['size']: new = True      # 독송 묶음(번역 줄 뒤 다음 소리·로마자 줄)
            elif k == 'pron' and pk not in ('pron',): new = True
            elif NUMSTART.match(t) and k != 'tr' and pk not in ('pron',) and not (k == 'roman' and pk == 'pron') and gap > 1.9 * l['size']: new = True
        if new:
            out.append((':: ' if is_center(l) and k not in ('pron', 'roman') else '') + t); cur = len(out) - 1; meta[cur] = [(l, k)]
        else: out[cur] += '\n' + t; meta.setdefault(cur, []).append((l, k))
        prev = (l, k); LP[id(l)] = cur
    while len(ys) < len(out): ys.append(last_y)
    # 산문 문단(소리·로마자 줄이 없는 글)은 인쇄본에서 줄 끝까지 찬 줄을 이어 붙임 — 줄 끝에 빈칸이 찍혀 있으면 빈칸,
    # 없으면(낱말 가운데에서 줄이 바뀐 곳: '뜻|이며', '합|송') 바로 붙임 (운영자 요청, 2026-11-15)
    right = max((l['x1'] for l in L if l['y'] > 55 and l['size'] >= 10), default=360)
    for n, ls in meta.items():
        if len(ls) < 2 or any(k in ('pron', 'roman') for _, k in ls) or out[n].startswith(('## ', '^^ ', ':: ')): continue
        if out[n].count('\n') != len(ls) - 1: continue
        parts = out[n].split('\n'); res = parts[0]
        for j, part in enumerate(parts[1:]):
            pl = ls[j][0]; cl = ls[j + 1][0]
            item = re.match(r'[①-⑳㉑-㉟❶-❿]|\d+\s*[.)]\s', part) and abs(cl['x0'] - ls[0][0]['x0']) < 2.5   # 번호 항목의 첫 줄(첫 항목과 같은 자리에서 시작)
            if pl['x1'] >= right - 22 and not item: res += wrap_sep(res, part, pl) + part
            else: res += '\n' + part
        out[n] = res
    return out


KIWI = None
RIGHT = 360
WRAPLOG = []
CORPUS = ''


def wrap_sep(a, b, pl):
    """끝까지 찬 줄을 이을 때 빈칸을 넣을지 — 이 PDF 는 줄 끝 빈칸이 글자로 없고, 한글 파일이 낱말 사이에서도 낱말 가운데에서도
    줄을 바꿈('남|방에서는', '성취하신|성인들'). 한글끼리는 형태소 분석(kiwi)으로 붙인 꼴과 띄운 꼴 중 자연스러운 쪽을 고름"""
    global KIWI
    if pl['trail'] or re.search(r'[.?!,:;]$', a): return ' '
    if re.match(r'[‘“]', b) and re.search(r'[가-힣A-Za-z0-9]$', a): return ' '      # 다음 줄이 여는 따옴표·괄호로 시작('빅쿠들은|‘오와다')
    if a.endswith(')') and not re.match(r'[을를이가은는의에과와도로]', b): return ' '
    if re.search(r'[A-Za-zāīūṃṅñṭḍṇḷ]$', a) and re.match(r'[가-힣]', b): return ' '
    if re.search(r'[가-힣]$', a) and re.match(r'[가-힣]', b):
        # ① 이 책 안(줄 가운데 — 빈칸이 자리로 재어져 믿을 만함)에서 같은 두 조각이 붙어 쓰였는지 띄어 쓰였는지
        fa = re.search(r'[가-힣]+$', a).group(); fb = re.match(r'[가-힣]+', b).group()
        if CORPUS:
            jn = len(re.findall(re.escape(fa + fb), CORPUS)); spn = len(re.findall(re.escape(fa + ' ' + fb), CORPUS))
            if jn != spn and max(jn, spn) >= 1:
                WRAPLOG.append((9 if jn > spn else -9, a[-20:], b[:20], 'book', jn, spn))
                return '' if jn > spn else ' '
        if KIWI is None:
            from kiwipiepy import Kiwi
            KIWI = Kiwi()
        sc = lambda s: KIWI.analyze(s)[0][1]
        tail = re.sub(r'\*\*', '', a)[-20:]; head = re.sub(r'\*\*', '', b)[:20]
        d = sc(tail + head) - sc(tail + ' ' + head)
        if abs(d) <= 1:                                                     # 점수로 가리기 어려우면 kiwi 띄어쓰기로
            sp = KIWI.space(tail + head, reset_whitespace=False); n = 0; ia = len(tail.replace(' ', ''))
            for i, ch in enumerate(sp):
                if ch != ' ': n += 1
                if n == ia: d = -1 if (i + 1 < len(sp) and sp[i + 1] == ' ') else 1; break
        WRAPLOG.append((round(d, 2), tail, head))
        return '' if d > 0 else ' '
    return ''


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
            if t in ('차 례', '법 요 집', ''): continue
            m = re.match(r'(.*?)\s*[-\s]{3,}\s*(\d+)$', t) or re.match(r'(.*?)\s*(\d{1,3})$', t)
            page = None
            if m and not re.fullmatch(r'[□\d\s]*', m.group(1)):
                title, page = re.sub(r'[\s-]+$', '', m.group(1)).strip(), int(m.group(2))
            else: title = t
            box = re.match(r'□\s*(\d+)\s*(.*)', title)
            if box: title = box.group(1) + ' ' + box.group(2); BOXT.add(title)
            if l['font'].startswith('ÈÞ') and l['size'] >= 13.5: lev = 0
            elif box and page is None: lev = 3
            elif page is None: lev = 1
            else: lev = 2
            gap = l['y'] - py if py is not None else 0; py = l['y']
            if lev == 0 and R and R[-1][0] == 0 and l['size'] < 14 and R[-1][2] is None: R[-1] = (0, R[-1][1] + ' ' + title, None); continue   # 예 경 + Ⅰ
            R.append((lev, title, page))
            disp = re.sub(r'\s*(\*\*)?\s*([-\s]{3,})?\d{1,3}\s*(\*\*)?\s*$', '', l['bt']) if page else l['bt']    # 굵게 표시(**)는 그대로, 쪽 번호만 뗌
            disp = re.sub(r'□\s*', '□', disp); disp = re.sub(r'\*\*\s*\*\*', ' ', disp).strip()
            if disp.count('**') % 2: disp += '**'
            TMETA.append({'x': l['x0'], 'gap': gap, 'size': l['size'], 'head': l['font'].startswith(('ÈÞ', 'HYcys')), 'disp': disp})
    # 쪽 번호가 앞뒤 순서와 어긋나는 □ 항목(차례의 잘못 찍힌 쪽 번호, 예: '□6 출가자의 오염원 668')은 쪽 없는 소제목으로
    for n, (lev, title, page) in enumerate(R):
        if lev == 2 and re.match(r'\d+ ', title):
            pv = next((p for (lv, tt, p) in reversed(R[:n]) if p), 0); nx = next((p for (lv, tt, p) in R[n + 1:] if p), 10 ** 6)
            if not (pv <= page <= nx): print('  차례 쪽 번호가 순서에 안 맞음 → 소제목으로:', title, page); R[n] = (3, title, None); SHOWN[title] = page
    return R


PICS = {'916aba6f': ('DL-0036-leaf.png', '#보리수 잎 그림'), 'd3a505db': ('DL-0036-lion.png', '#사자상 그림')}


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
    global CORPUS
    CORPUS = '\n'.join(l['t'] for i in range(13, d.page_count + 1) for l in lines_of(d[i - 1]))   # 줄 안의 글(빈칸을 자리로 잼)
    for i in range(1, d.page_count + 1):
        lab = f'{i - OFF}쪽' if i > OFF else ''
        L = lines_of(d[i - 1])
        if i == 1: continue                                                # 빈 앞표지 쪽
        if i == d.page_count: lab = ''                                     # 맨 끝 도서 안내 — 책이 번호를 세지 않은 쪽
        if i in DIVIDERS: pages.append((lab, [])); continue
        if i == 2:
            pages.append((lab, ['^^ 법 요 집', ':: (법 보 시 용)', ':: 이 판', ':: (2015년)', ':: 아리야승원'])); continue
        if i in TOC_PAGES:
            if i == TOC_PAGES[0]: pages.append((lab, ['## 차 례', toc_block(T)]))   # 차례 8쪽은 한 화면으로
            continue
        ys = []; LP.clear(); ps = body_paras(L, ys)
        # 인쇄본에서 굵게 보이는 글꼴(HEAVY)로 찍힌 글자는 모두 굵게, 가는 글꼴은 보통 — 문단 종류와 상관없이 같은 원칙 (2026-11-19 다시 검수:
        # 전에는 바탕 문단 속 궁서체만 굵게 해서 경전 인용 문단은 보통 글이었음 — 운영자 지적 '강조된 곳이 어떤 곳은 굵게, 어떤 곳은 아님')
        Lh = lines_of(d[i - 1], bold='heavy')
        mark_bold(ps, L, Lh, Lh, i)
        for y0, h in sorted(WH.get(i, [])):
            k = next((n for n, y in enumerate(ys) if y > y0), len(ps))
            ps.insert(k, f'![{PICS[h][1]}](/uploads/{PICS[h][0]})'); ys.insert(k, y0)
        pages.append((lab, ps))
    return d, pages, T


BOLDMISS = []


def mark_bold(ps, L, Lb, Lg, pn):
    """인쇄본에서 굵게 보이는 글꼴(HEAVY)로 찍힌 글자를 본문에 **…** 로 — 글자는 그대로, ** 만 더함.
    제목(## ^^ %% 문단)·쪽 번호·머리글은 건드리지 않음. 문장부호·빈칸만 굵은 조각은 뺌. 한 문단 안에서 앞 줄 다음 자리부터 찾음(같은 줄이 되풀이되는 독송)."""
    if not (len(L) == len(Lb)): BOLDMISS.append((pn, '줄 수 다름')); return
    pos = collections.Counter()
    for l, lb in zip(L, Lb):
        k = LP.get(id(l))
        if k is None or ps[k].startswith(('## ', '^^ ', '%% ')): continue
        t = lb['t']
        plain = re.sub(r' {2,}', ' ', t.replace('**', '')).strip()
        if plain != l['t'].strip(): BOLDMISS.append((pn, '글자 다름', plain)); continue
        j = ps[k].find(plain, pos[k])
        if j < 0: BOLDMISS.append((pn, plain)); continue
        if '**' not in t: pos[k] = j + len(plain); continue
        segs = re.split(r'(\*\*.*?\*\*)', t.strip()); out = ''
        for sg in segs:
            if sg.startswith('**') and sg.endswith('**') and len(sg) >= 4:
                inner = sg[2:-2]; core = inner.strip()
                if not core or re.fullmatch(r'[\s.,·:;!?()\-‘’“”\[\]]+', core): out += inner; continue
                lead = inner[:len(inner) - len(inner.lstrip())]; tail = inner[len(inner.rstrip()):]
                out += lead + '**' + core + '**' + tail
            else: out += sg
        out = re.sub(r' {2,}', ' ', out).strip()
        if out.replace('**', '') != plain: BOLDMISS.append((pn, '표시 어긋남', plain)); continue
        ps[k] = ps[k][:j] + out + ps[k][j + len(plain):]
        pos[k] = j + len(out)
    for k in range(len(ps)):
        ps[k] = re.sub(r'\*\*(\s*)\*\*', r'\1', ps[k])     # 줄이 바뀌어도 이어지는 굵게는 하나로


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


def find_sub(pages, start, title, end=None):
    import difflib
    m = re.match(r'(\d+)\s+(.*)', title); num, rest = m.group(1), KEY(m.group(2))
    first = None
    for i in range(start, min(start + 80, len(pages) + 1, end or 10 ** 6)):
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
                nxp = next((p for (lv, tt, p) in T[n + 1:] if p), None)
                f = find_sub(pages, last, title, idx.get(f'{nxp}쪽') if nxp else None)
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
        while k and '\n' not in ps[k - 1] and len(re.sub(r'^## ', '', ps[k - 1])) <= 30 and not ps[k - 1].startswith(('%%', '![', '(')) \
                and (not ps[k - 1].startswith('## ') or re.search(r'니까야|빠타|빠따|법구경', ps[k - 1])
                     or (len(re.sub(r'[^가-힣]', '', ps[k - 1])) <= 5 and not re.search(r'\d', ps[k - 1]))): k -= 1   # 제목 위의 꼬리표(월요일·경전 출처·포살 ․ 축원)도 함께
        if k: e['at'] = re.sub(r'^(## |\^\^ )', '', pages[i - 1][1][k])[:24]
        elif k is None and pages[i - 1][0] not in div: print('  ? 제목 못 맞춤', page, title)
        toc.append(e); last = i
    # 4쪽 예경문(차례에 없음) — 빨리어 한글 표기 다음
    k = next(n for n, t in enumerate(toc) if t['page'] == idx['3쪽'])
    toc.insert(k + 1, {'title': '예경문', 'page': idx['4쪽'], 'sub': False})
    toc.append({'title': '도서 안내', 'page': len(pages), 'sub': False})
    return toc


if __name__ == '__main__':
    d, pages, T = build(sys.argv[1])
    toc = make_toc(pages, T)
    # 장 표지 쪽: 표지에 크게 인쇄된 장 이름만 넣음(작은 차례·겹쳐 찍은 그림자 글은 뺌) — 듣기가 장 이름부터 읽게
    for t in toc:
        if not t['sub'] and not pages[t['page'] - 1][1]: pages[t['page'] - 1][1].append('^^ ' + t['title'])
    # □ 번호 제목: □ 를 되살림 → 화면에서 네모 테두리 번호(app.js boxNum), 듣기는 □ 를 읽지 않음 (운영자 요청, 2026-11-16)
    for lab, ps in pages:
        for k, p in enumerate(ps):
            if p.startswith('## ') and any(p[3:].startswith(b) for b in BOXT) and re.match(r'## \d+ ', p): ps[k] = '## □' + p[3:]
    for t in toc:
        if t['title'] in BOXT: t['title'] = '□' + t['title']
        if t.get('at') and re.match(r'\d+ ', t['at']) and any(b.startswith(t['at']) or t['at'].startswith(b) for b in BOXT): t['at'] = '□' + t['at']
    # 궁서체 굵게 조각이 낱말 가운데에서 시작·끝나면(줄·쪽이 바뀌는 곳에서 글꼴이 바뀐 것) 굵게를 뺌
    PW = {(a.replace('*', ''), b.replace('*', '')) for a, b in [(e[2], e[3]) for e in json.load(open(os.path.join(REPO, 'tools/pageword_fixes.json'))).get('DL-0036', [])]}
    def unmid(t):
        out = ''; pos = 0
        for m in re.finditer(r'\*\*(.+?)\*\*', t):
            a, b = m.start(), m.end()
            bad = (a > 0 and re.match(r'[가-힣]', t[a - 1]) and re.match(r'[가-힣]', m.group(1))) or (b < len(t) and re.match(r'[가-힣]', t[b]) and re.search(r'[가-힣]$', m.group(1)))
            out += t[pos:a] + (m.group(1) if bad else m.group(0)); pos = b
        return out + t[pos:]
    for n, (lab, ps) in enumerate(pages):
        for k, p in enumerate(ps):
            pass   # 2026-11-19: 낱말 가운데에서 바뀌는 굵게도 인쇄본 그대로 둠(궁서체 낱말 + 바탕 괄호 + 궁서체 조사: '**여래**(스승)**를**')
    body = '\n\n'.join(f'=== {lab} ===\n' + '\n\n'.join(ps) for lab, ps in pages)
    # 한글 바로 뒤의 여는 따옴표는 띄어 씀 — 궁서체 ‘ 는 글자 안에 빈 자리가 있어 인쇄본에서는 띄어 보이고, 줄이 바뀌는 곳은 빈칸으로 이었음 (2026-11-19 다시 검수)
    body = re.sub(r'([가-힣])(\*\*)?‘', lambda m: m.group(1) + (m.group(2) or '') + ' ‘', body)
    # 줄 첫머리 번호와 글이 붙은 곳('10.따뽀 …', '14.아침경')은 번호 뒤에 빈칸 (운영자 요청, 2026-11-15 — 교정)
    NUMSP = re.compile(r'(?m)^((?:## |\^\^ |:: |%% |-{1,3} |\*\*)?)(\d{1,3})\.(?=[^\s\d.])')
    body = NUMSP.sub(r'\1\2. ', body)
    for t in toc:
        t['title'] = NUMSP.sub(r'\1\2. ', t['title'])
        if t.get('at'): t['at'] = NUMSP.sub(r'\1\2. ', t['at'])
    imgs = sorted({'/uploads/' + v[0] for v in PICS.values() if '/uploads/' + v[0] in body})
    out = {'book': 'DL-0036', 'edition': '이판', 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in imgs], 'body': body}
    p = os.path.join(REPO, 'content/texts/DL-0036.json')
    json.dump(out, open(p, 'w'), ensure_ascii=False, indent=1)
    json.dump(sorted(WRAPLOG), open('/tmp/dl0036_wraplog.json', 'w'), ensure_ascii=False)
    if BOLDMISS: print('  ! 굵게 자리 못 찾음', len(BOLDMISS), BOLDMISS[:8])
    print('쪽', len(pages), '목차', len(toc), '장', sum(not t['sub'] for t in toc), '글자', len(body))
