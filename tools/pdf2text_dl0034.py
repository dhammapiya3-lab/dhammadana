"""『업과 윤회의 법칙』(DL-0034, 파아옥 또야 사야도 지음, 정명 스님 옮김, 전자책 개정판) PDF → content/texts/DL-0034.json
  python3 tools/pdf2text_dl0034.py 책.pdf
그 다음 python3 tools/split_chapters.py --write

PDF 720쪽 (한글에서 PDF24 로 내보냄). PDF 쪽 = 인쇄 쪽 + 34 (쪽 아래 숫자가 쪽 이름). PDF 1 앞표지는 넣지 않음.
앞쪽(번호 없음): 2 속표지(사자상 그림 쪽), 3 저작권·속표지설명, 4 법보시, 5~9 한국어 번역 허가서, 10~26 차례(요약·자세한),
27~28 표 차례, 29~30 인용 문헌/경전 약어표, 31 빠알리 주석서 약어표, 32~34 일러두기.
글자는 rawdict 글자 자리로 줄을 다시 세움(dl0034_lib). 굵게: 한글이 테두리를 덧그린 글자(texttrace type 1)·Bold 글꼴 → **…**,
기울임(Times Italic 로마자) → °°…°°, 위첨자 각주 번호 'N)' → [^N], 쪽 아래 각주(구분선 아래) → [^N]: …
표(선·칠한 칸이 있는 곳, 칸 사이가 벌어진 줄, 본문보다 아주 작은 글씨 줄)와 그림·옆으로 누운 쪽은 쪽에서 그대로 잘라 그림으로.
문단: 첫 줄 들여쓰기(+7pt)·줄 사이 26pt 넘음·짧은 줄 다음 → 새 문단, 끝까지 찬 줄은 이어 붙임(한글 파일은 낱말 가운데에서도
줄을 바꾸므로 그대로 붙임 — 줄 끝 빈칸은 PDF 에 글자로 있음), 같은 들여쓰기의 짧은 줄 묶음(게송·목록)은 줄 바꿈.
□·▷ 로 시작하는 줄, 12pt 넘는 줄, 인쇄된 차례 항목과 같은 짧은 줄 → ## 소제목. 장 = 인쇄된 차례[요약]의 큰 항목.
U+3000(전각 빈칸) → 빈칸, 빈칸 여럿 → 하나. 다른 글자는 PDF 그대로.
"""
import sys, re, json, os, collections, io
import fitz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl0034_lib import Page, markup, refy

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK, ED = 'DL-0034', '전자책 개정판'
doc = fitz.open(pdf)
UP = os.path.join(REPO, 'public/uploads')
log = collections.Counter()
HANGUL = re.compile(r'[가-힣]')
images = []


def clean(t):
    t = t.replace('\u3000', ' ').replace('\xa0', ' ')
    t = re.sub(r'\*\*(\s*)\*\*', r'\1', t)
    t = re.sub(r'°°(\s*)°°', r'\1', t)
    t = re.sub(r'(?<=\S) {2,}', ' ', t)
    return t.strip(' ')


def plain(t):
    import unicodedata
    t = unicodedata.normalize('NFKC', t)
    t = re.sub(r'[\u4e00-\u9fff]|\*\*|°°', '', t)
    t = re.sub(r'^(?:## )?[□▷■⃞\s]*(?:\d+(?:[-~∼〜]\d+)?\)\s*)?', '', t)
    return re.sub(r'\[\^[^\]]+\]|\*\*|°°|^## |[\s.,·?!()（）:：\-~‘’“”"\'\[\]□▷■?？]', '', t)


TURN = {'DL-0034-357-1.png'}


def render(n, rect, name, dpi=220):
    from PIL import Image
    pix = doc[n - 1].get_pixmap(dpi=dpi, clip=rect)
    im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('L')
    if name in TURN: im = im.rotate(-90, expand=True); name = name.replace('.png', 'r.png')   # 옆으로 누운 표를 바로 세워 가로로 (운영자 요청 2026-11-17: 표 5d)
    path = os.path.join(UP, name); im.save(path, optimize=True)
    images.append('/uploads/' + name); log['그림(표)'] += 1
    return '/uploads/' + name


# ---------------- 인쇄된 차례 ----------------
def toc_lines(pages):
    out = []
    for n in pages:
        P = Page(doc, n)
        for l in P.lines():
            if l['zone'] != 'body': continue
            raw = ''.join(c['c'] for c in l['cs']).replace('　', ' ').strip()
            bold = sum(1 for c in l['cs'] if c['bold'] and c['c'].strip()) > len(raw.replace(' ', '')) * 0.6
            m = re.match(r'^(.*?)\s*(?:·{2,}[·\s]*|\s{2,}|\s(?=\d+$))(\d+)$', raw) or re.match(r'^(.*?)[·\s]*()$', raw)
            title = re.sub(r'\s+', ' ', m.group(1)).strip(); pg = m.group(2)
            if not pg:
                m2 = re.match(r'^(.*[가-힣)’])(\d{2,3})$', title)
                if m2: title, pg = m2.group(1), m2.group(2)
            off = l['x0'] - 70.9
            lv = 0 if off < 4 else 1 if off < 24 else 2 if off < 45 else 3
            out.append(dict(n=n, y=l['y'], title=title, pg=pg, lv=lv, size=l['size'], bold=bold))
    return out


TOC_SUM = toc_lines(range(10, 12))
TOC_DET = toc_lines(range(12, 27))
TOC_TAB = toc_lines(range(27, 29))


def toc_block(items, skip=()):
    rows = []; prev = None
    for it in items:
        if it['title'] in skip: continue
        if prev and it['n'] == prev['n'] and it['y'] - prev['y'] > 30: rows.append('~')
        t = it['title']
        if it['bold']: t = '**' + t + '**'
        rows.append('-' * it['lv'] + ('' if not it['lv'] else ' ') + t + (f" | {it['pg']}" if it['pg'] else ''))
        prev = it
    return '%% ' + '\n'.join(rows)


# ---------------- 쪽 → 문단 ----------------
PAGES = []      # {'lab', 'paras': [str], 'fns': [n]}
FN = {}; FN_ORDER = []
last_fn = [None]
open_para = [None]   # (page dict, para index, last line full?, indent)


def build(n, lab=None):
    P = Page(doc, n)
    L = P.lines()
    if lab is None:
        nums = [l['text'].strip() for l in L if l['zone'] == 'foot' and l['text'].strip().isdigit()]
        lab = (nums[-1] + '쪽') if nums else ''
    page = {'lab': lab, 'paras': [], 'fns': [], 'n': n, 'kinds': [], 'y': []}
    body = [l for l in L if l['zone'] == 'body']
    Lx = 70.9 if n < 35 else P.L
    xs = sorted(l['x1'] for l in body if l['size'] >= 9.5 and l['x1'] < Lx + 310)
    Rx = xs[int(len(xs) * 0.9)] if len(xs) >= 5 else Lx + 297.5
    Rx = min(max(Rx, Lx + 285), Lx + 302)
    regs, cols = P.tables(L)
    if P.fy and any(r.y1 > P.fy + 5 for r in regs):   # 표 안의 짧은 가로선을 각주 구분선으로 잘못 본 것
        P.fy = refy(P, regs, L); L = P.lines(); body = [l for l in L if l['zone'] == 'body']
        xs = sorted(l['x1'] for l in body if l['size'] >= 9.5 and l['x1'] < Lx + 310)
        regs, cols = P.tables(L); log['각주 구분선 다시 봄'] += 1
    used = set()
    for r, gl in cols:
        for l in gl: used.add(id(l))
    inreg = lambda l: any(r.x0 - 1 <= l['x0'] and l['x1'] <= r.x1 + 1 and r.y0 - 2 <= l['y'] <= r.y1 + 3 for r in regs)
    body = [l for l in body if id(l) not in used and not inreg(l)]
    items = [('L', l['y'], l) for l in body] + [('R', r.y0, r) for r in regs if r.y0 < (P.fy or 999)] + [('C', r.y0, gl) for r, gl in cols]
    items.sort(key=lambda x: x[1])
    cur = None; prev = None; k = 0
    first = True
    for kind, y, obj in items:
        if kind == 'R':
            r = fitz.Rect(max(obj.x0 - 4, 0), max(obj.y0 - 3, 0), min(obj.x1 + 4, P.p.rect.x1), min(obj.y1 + 1.5, P.p.rect.y1))
            cap = ''
            inside = sorted([c for c in P.chars if r.contains(fitz.Point(c['x'], c['y']))], key=lambda c: (round(c['y']), c['x']))
            if inside:
                y0 = inside[0]['y']; cap = clean(''.join(c['c'] for c in inside if abs(c['y'] - y0) < 2))
            if not re.match(r'표\s*\d', cap): cap = '표'
            k += 1
            name = f"{BK}-{(lab.replace('쪽', '') or 'f' + str(n))}-{k}.png"
            url = render(n, r, name)
            page['paras'].append(f'![#{cap[:40]}]({url})'); page['kinds'].append('img'); page['y'].append(y)
            cur = None; prev = None; first = False; open_para[0] = None
            continue
        if kind == 'C':
            colsx = []
            for l in obj:
                for ci, cc in enumerate(P.mcells(l) or P.cell_chars(l)):
                    while len(colsx) <= ci: colsx.append([])
                    colsx[ci].append(markup(cc).strip())
            txt = '\n'.join(x for col in colsx for x in col if x)
            page['paras'].append(txt); page['kinds'].append('p'); page['y'].append(y); log['단 나눈 목록'] += 1
            cur = None; prev = None; first = False; open_para[0] = None
            continue
        l = obj
        t = markup(l['cs']).replace('\u3000', ' ')
        if not t.strip(): continue
        ind = l['x0'] - Lx
        full = l['x1'] > Rx - 10
        raw = l['text'].replace('　', ' ').strip()
        head = l['size'] >= 11.5 or raw[:1] in '□▷■◆◇⃞'
        if first and open_para[0] and not head and ind < 4:
            pg, pi, pfull, pind = open_para[0]
            letters = [c for c in l['cs'] if c['c'].strip() and not c.get('sup')]
            allbold = letters and sum(c['bold'] for c in letters) >= len(letters) * 0.8
            if pfull and pg['kinds'][pi] == 'p' and not (allbold and not pg['paras'][pi].rstrip().endswith('**')):
                pg['paras'][pi] = pg['paras'][pi] + t; log['쪽을 넘어 이어 붙인 문단'] += 1
                cur = (pg, pi); prev = l; first = False; open_para[0] = (pg, pi, full, ind); continue
        first = False
        new = cur is None or head or (prev is not None and (l['y'] - prev['y'] > max(26, prev['size'] * 2.45)))
        if not new and prev is not None:
            pfull = prev['x1'] > Rx - 10; pind = prev['x0'] - Lx
            if ind >= 4 and not pfull and not abs(ind - pind) < 3: new = True
            if ind >= 4 and pfull and ind - pind > 4: log['내어쓴 줄 이어 붙임'] += 1
            if prev.get('_head'): new = True
            ab = lambda q: (lambda ls: bool(ls) and sum(c['bold'] for c in ls) >= len(ls) * 0.8)([c for c in q['cs'] if c['c'].strip() and not c.get('sup') and HANGUL.match(c['c'])])
            if not pfull and ab(prev) != ab(l): new = True; log['굵기가 바뀌어 새 문단'] += 1
        if new:
            page['paras'].append(t.lstrip(' ')); page['kinds'].append('h' if head else 'p'); page['y'].append(y)
            cur = (page, len(page['paras']) - 1)
        else:
            pg, pi = cur
            pfull = prev['x1'] > Rx - 10
            if pfull and re.match(r'\s*(?:[①-⑳]|\d+\)\s|\d+[~\-]\d+\s)', t): pfull = False   # 번호 항목은 늘 새 줄
            pg['paras'][pi] = pg['paras'][pi] + t if pfull else pg['paras'][pi].rstrip(' ') + '\n' + t
            if not pfull: log['문단 안 줄 바꿈'] += 1
        l['_head'] = head
        prev = l
        open_para[0] = (cur[0], cur[1], full, ind)
    # 각주
    for l in L:
        if l['zone'] != 'fn': continue
        if l['size'] >= 9.6: continue
        txt = markup(l['cs'], refs=False).replace('\u3000', ' ')
        m = re.match(r'^\s*(\d+)\)\s*', txt)
        if m and l['x0'] < Lx + 4:
            f = m.group(1)
            if f in FN:
                log['겹친 각주 번호'] += 1; f = f + '-' + str(sum(1 for x in FN if x.split('-')[0] == f))
            FN[f] = txt[m.end():]; page['fns'].append(f); last_fn[0] = (f, l)
        elif last_fn[0]:
            f, pl = last_fn[0]
            pfull = pl['x1'] > Rx - 12 or pl['_pg'] != n if '_pg' in pl else pl['x1'] > Rx - 12
            FN[f] = FN[f] + ('' if pfull else '\n') + (txt if pfull else txt.lstrip(' ')); last_fn[0] = (f, l)
        l['_pg'] = n
    PAGES.append(page)
    return page


def mkhead(pg, j, title=None):
    ls = pg['paras'][j].split('\n')
    h = '## ' + (title or re.sub(r'\*\*', '', ls[0]).strip())
    pg['paras'][j:j + 1] = [h] + (['\n'.join(ls[1:])] if len(ls) > 1 else [])
    pg['kinds'][j:j + 1] = ['h'] + (['p'] if len(ls) > 1 else [])


# ---------------- 앞쪽 ----------------
chapters = []   # (title, page index, para index)

# PDF 2 속표지: 사자상 그림
pg = {'lab': '', 'paras': [], 'fns': [], 'n': 2, 'kinds': [], 'y': []}
P2 = doc[1]
info = [i for i in P2.get_image_info()]
# 속표지 쪽은 원본 그대로 한 장의 그림으로 (제목 상자 + 사자상 — 운영자 요청, 2026-11-17)
pix = P2.get_pixmap(dpi=150, clip=P2.rect)
from PIL import Image
Image.open(io.BytesIO(pix.tobytes('png'))).convert('L').save(os.path.join(UP, f'{BK}-title.jpg'), quality=85, optimize=True)
images.append(f'/uploads/{BK}-title.jpg'); log['그림(표)'] += 1
pg['paras'].append(f'![#The Workings of Kammas](/uploads/{BK}-title.jpg)'); pg['kinds'] += ['img']
PAGES.append(pg); chapters.append(('속표지', 0, 0))

pg = build(3, '')
pg['paras'][0] = pg['paras'][0].replace('\n', ' ')   # 저작권 글: 가운데 맞춘 첫 줄도 한 문단으로 (운영자 요청, 2026-11-17)
# '속표지설명' 앞(저작권 글)과 뒤를 나눔
ix = next(i for i, p in enumerate(pg['paras']) if plain(p).startswith('속표지설명'))
rest = pg['paras'][ix].split('\n', 1)
pg['paras'][ix:ix + 1] = ['## 속표지 설명'] + ([rest[1]] if len(rest) > 1 else []); pg['kinds'][ix:ix + 1] = ['h'] + (['p'] if len(rest) > 1 else [])
chapters.append(('저작권', len(PAGES) - 1, 0)); chapters.append(('속표지 설명', len(PAGES) - 1, ix))
build(4, ''); chapters.append(('법보시', len(PAGES) - 1, 0))
for n in range(5, 10):
    pg = build(n, '')
    if n == 5:
        mkhead(pg, 0, '한국어 번역 허가서'); chapters.append(('한국어 번역 허가서', len(PAGES) - 1, 0))
open_para[0] = None

# 차례 (10~26) — 인쇄된 차례 그대로 %% 로
pg = {'lab': '', 'paras': [], 'fns': [], 'n': 10, 'kinds': [], 'y': []}
pg['paras'] = ['## 제목 차례[요약]', toc_block(TOC_SUM, skip=('제목 차례[요약]',)),
               '## 제목 차례[자세한]', toc_block(TOC_DET, skip=('제목 차례[자세한]',))]
pg['kinds'] = ['h', 'p', 'h', 'p']
PAGES.append(pg); chapters.append(('차례', len(PAGES) - 1, 0))
pg = {'lab': '', 'paras': [], 'fns': [], 'n': 27, 'kinds': [], 'y': []}
pg['paras'] = ['## <표 차례>', toc_block(TOC_TAB, skip=('<표 차례>',))]; pg['kinds'] = ['h', 'p']
PAGES.append(pg); chapters.append(('표 차례', len(PAGES) - 1, 0))
for n in (29, 30):
    pg = build(n, '')
    if n == 29:
        mkhead(pg, 0); chapters.append(('인용 문헌/경전 약어표', len(PAGES) - 1, 0))
open_para[0] = None
pg = build(31, ''); mkhead(pg, 0); chapters.append(('빠알리 주석서 약어표', len(PAGES) - 1, 0))
open_para[0] = None
for n in (32, 33, 34):
    pg = build(n, '')
    if n == 32: mkhead(pg, 0, '일러두기'); chapters.append(('일러두기', len(PAGES) - 1, 0))
open_para[0] = None

# ---------------- 본문 ----------------
FRONT = len(PAGES)
for n in range(35, 721):
    build(n)

for P in PAGES:
    P['paras'] = ['\n'.join(clean(x) for x in p.split('\n')) for p in P['paras']]
for f in FN: FN[f] = '\n'.join(clean(x) for x in FN[f].split('\n'))

# ---------------- 장·소제목 ----------------
LAB = {p['lab']: i for i, p in enumerate(PAGES) if p['lab']}


def find(title, pgno, span=2, long_ok=False):
    want = plain(title)
    if not want or not pgno: return None
    i0 = LAB.get(f'{pgno}쪽')
    if i0 is None: return None
    for i in range(i0, min(i0 + span, len(PAGES))):
        for j, p in enumerate(PAGES[i]['paras']):
            if p.startswith('![') or p.startswith('[^'): continue
            pp = plain(p.split('\n')[0])
            if pp.startswith(want[:max(6, min(len(want), 14))]) or (len(want) <= 6 and pp == want):
                return (i, j)
    return None


# 차례 항목이 문단 가운데 줄에 있으면 그 줄부터 따로 문단으로
for it in TOC_DET:
    if it['lv'] == 0 or not it['pg']: continue
    want = plain(it['title']); i0 = LAB.get(f"{it['pg']}쪽")
    if i0 is None or not want: continue
    done = False
    for i in range(i0, min(i0 + 2, len(PAGES))):
        P = PAGES[i]
        for j, p in enumerate(P['paras']):
            ls = p.split('\n')
            if len(ls) < 2 or p.startswith('%%') or p.startswith('![') or p.startswith('## '): continue
            for q in range(0, len(ls)):
                pq = plain(ls[q])
                if pq.startswith(want[:max(6, min(len(want), 14))]) and len(pq) <= len(want) + 25:
                    rest = '\n'.join(ls[q + 1:])
                    pre = ['\n'.join(ls[:q])] if q else []
                    P['paras'][j:j + 1] = pre + [ls[q]] + ([rest] if rest else [])
                    P['kinds'][j:j + 1] = ([P['kinds'][j]] if q else []) + ['p'] + (['p'] if rest else [])
                    log['차례 항목 줄을 따로 뗌'] += 1; done = True; break
            if done: break
        if done: break

CH = [('I. 차꼬경', '1'), ('Ⅱ. 두 번째 차꼬경', '45'), ('Ⅲ. 업의 작용', '62'), ('Ⅳ. 짧게 설한 업-분석의 경', None),
      ('Ⅴ. 사람으로 태어나기', '565'), ('Ⅵ. 업의 멈춤', '592'), ('번역후기', '671'), ('부록 1: 40가지 명상주제', '679'),
      ('부록 2: 부처님 계보', '682'), ('편집자 후기', '684'), ('빠알리어 스펠링', '684'), ('Source References', '685')]
KEYS = {'I. 차꼬경': '차꼬경', 'Ⅱ. 두 번째 차꼬경': '두번째차꼬경', 'Ⅲ. 업의 작용': '업의작용', 'Ⅳ. 짧게 설한 업-분석의 경': None,
        'Ⅴ. 사람으로 태어나기': '사람으로태어나기', 'Ⅵ. 업의 멈춤': '업의멈춤'}
for title, pgno in CH:
    hit = None
    if pgno is None:
        # Ⅳ: 차례에 쪽 번호가 '(‘Cūḷa…’) 469' 줄에 있음
        pgno = '469'
        i0 = LAB['469쪽']
        for i in range(i0, i0 + 2):
            for j, p in enumerate(PAGES[i]['paras']):
                if 'Ⅳ' in p[:8] or 'IV' in p[:8]: hit = (i, j); break
            if hit: break
    else:
        key = KEYS.get(title) or plain(title)
        i0 = LAB[f'{pgno}쪽']
        for i in range(i0, i0 + 2):
            for j, p in enumerate(PAGES[i]['paras']):
                pp = plain(p.split('\n')[0])
                if key in pp[:len(key) + 6] and len(pp) < len(key) + 60: hit = (i, j); break
            if hit: break
    if not hit:
        print('! 장 제목을 못 찾음:', title, pgno); continue
    i, j = hit
    p = PAGES[i]['paras'][j]
    if not p.startswith('## '):
        PAGES[i]['paras'][j] = '## ' + re.sub(r'\*\*', '', p.split('\n')[0]).strip() + ('\n' + '\n'.join(p.split('\n')[1:]) if '\n' in p else '')
    PAGES[i]['kinds'][j] = 'h'
    head = re.sub(r'\[\^[^\]]+\]|°°|\*\*', '', PAGES[i]['paras'][j].split('\n')[0][3:]).strip()
    chapters.append((head, i, j))   # 장 이름 = 본문에 인쇄된 장 제목 그대로

subs = []
for it in TOC_DET:
    if it['lv'] == 0 or it['title'].startswith('제목 차례') or it['title'].startswith('(‘Cūḷa'): continue
    hit = find(it['title'], it['pg'])
    if not hit:
        log['차례 항목 못 찾음'] += 1; print('  - 차례 항목 못 찾음:', it['pg'], it['title']); continue
    i, j = hit
    p = PAGES[i]['paras'][j]
    one = '\n' not in p and len(plain(p)) <= len(plain(it['title'])) + 25
    if one and not p.startswith('## '):
        PAGES[i]['paras'][j] = '## ' + re.sub(r'\*\*', '', p).strip(); PAGES[i]['kinds'][j] = 'h'
    subs.append((it['title'], i, j))

# 남은 heading 표시(□ ▷ · 큰 글씨)
for P in PAGES:
    for j, p in enumerate(P['paras']):
        if P['kinds'][j] == 'h' and not p.startswith('## ') and not p.startswith('^^'):
            P['paras'][j] = '## ' + re.sub(r'\*\*', '', p.split('\n')[0]).strip() + ('\n' + '\n'.join(p.split('\n')[1:]) if '\n' in p else '')

# ---------------- 마무리 ----------------
for P in PAGES:
    for f in P['fns']:
        P['paras'].append(f'[^{f}]: ' + FN[f].strip())

toc = []
for t, pi, j in chapters:
    toc.append(dict(title=t, page=pi + 1, sub=False, **({'at': re.sub(r'^## ', '', PAGES[pi]['paras'][j]).split('\n')[0][:24]} if j > 0 else {})))
for t, pi, j in subs:   # 소제목은 늘 at (같은 말로 시작하는 본문 문단에 멈추지 않게)
    toc.append(dict(title=t, page=pi + 1, sub=True, at=re.sub(r'^## ', '', PAGES[pi]['paras'][j]).split('\n')[0][:40]))
order = {}
for t, pi, j in chapters + subs: order[(t, pi + 1)] = j
toc.sort(key=lambda x: (x['page'], order.get((x['title'], x['page']), 0), x['sub']))

body = ''
for P in PAGES:
    body += (f"=== {P['lab']} ===" if P['lab'] else '=== ===') + '\n\n' + '\n\n'.join(P['paras']) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print(out, len(PAGES), '쪽', len(FN), '각주', len(images), '그림', dict(log))
