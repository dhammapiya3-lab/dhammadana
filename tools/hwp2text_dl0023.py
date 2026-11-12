"""『법구경 이야기 1』(DL-0023, 무념·응진 옮김, 옛길 5판) 한글(HWP) 파일 → content/texts/DL-0023.json
  python3 tools/hwp2text_dl0023.py 책.hwp

한글 파일에는 인쇄 쪽 번호가 없으므로(쪽은 한글 프로그램이 그때그때 나눔) 쪽 표시는 이름 없이(=== ===) 넣는다 —
한글 파일에 저장된 줄 자리(LineSeg y 가 0 으로 돌아가는 곳)로 쪽이 바뀌는 곳을 찾아 문단 사이에만 넣음. 인쇄본 쪽 번호와는 맞지 않으므로 번호는 붙이지 않음.
글자는 한글 파일 그대로. 바꾸는 것: 판권지의 '⼁'(부수 글자) → '|' (구분 막대 원칙), 쪽 번호·찾아보기 표시(IndexMarker)는 뺌.
문단 모양: 개요 1(게송)·시들(시) → '++ ' 묶음, 가운데 맞춤 → '::', 오른쪽 맞춤 → '>>', 왼쪽 여백 있는 문단 → '++ ',
개요 2(이야기 제목)·개요 3·개요 5·개요 5-1·개요 5-2 → '## ', 개요 6·7(장 표지) → '^^ '·'::', 목차 쪽 → '%% ' 차례, 표 → | 표 |,
굵은 글자 모양 → **…**, 각주 → [^n] (한글 파일의 각주 번호 1~310 그대로). 그림은 public/uploads/DL-0023-*.
"""
import sys, os, re, json, subprocess, io, struct, collections
import xml.etree.ElementTree as ET

src = sys.argv[1]
BK, ED = 'DL-0023', '5판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = '/tmp/dl0023'
os.makedirs(WORK, exist_ok=True)
xmlp = os.path.join(WORK, 'book.xml')
if not os.path.exists(xmlp) or os.path.getmtime(xmlp) < os.path.getmtime(src):
    with open(xmlp, 'wb') as f: subprocess.run(['hwp5proc', 'xml', src], stdout=f, check=True)
root = ET.parse(xmlp).getroot()
DI = root.find('DocInfo')
STY = {str(i): s.get('local-name') for i, s in enumerate(DI.iter('Style'))}
CS = list(DI.iter('CharShape'))
PSH = list(DI.iter('ParaShape'))
BOLD = {str(i) for i, c in enumerate(CS) if c.get('bold') == '1'}
PL = [p for cs in root.find('BodyText').iter('ColumnSet') for p in cs.findall('Paragraph')]

# ---- 그림: 한글 파일 속 그림 파일 (BinData) ----
UP = os.path.join(REPO, 'public', 'uploads')
def bindata(n):
    import olefile
    ole = olefile.OleFileIO(src)
    for path in ole.listdir():
        if path[0] == 'BinData' and re.match(r'BIN%04X\.' % n, path[1]):
            raw = ole.openstream(path).read()
            try:
                import zlib; raw = zlib.decompress(raw, -15)
            except Exception: pass
            return path[1], raw
    return None, None
IMG = {}   # bindata-id → (주소, 설명)
def save_jpg(n, name):
    from PIL import Image
    fn, raw = bindata(n)
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    out = f'/uploads/{BK}-{name}.jpg'; im.save(os.path.join(REPO, 'public', out.lstrip('/')), quality=88)
    return out
def save_ole(n, name):  # OLE 안의 메타파일 도표 → PNG (LibreOffice 로 PDF → 그림)
    import olefile, fitz
    from PIL import Image, ImageChops
    fn, raw = bindata(n)
    o = olefile.OleFileIO(raw[4:]); pres = o.openstream('\x02OlePres000').read()
    wmf = pres[40:40 + struct.unpack('<I', pres[46:50])[0] * 2]
    d = os.path.join(WORK, 'ole'); os.makedirs(d, exist_ok=True)
    w = os.path.join(d, f'{name}.wmf'); open(w, 'wb').write(wmf)
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', d, w], capture_output=True, timeout=180)
    pix = fitz.open(os.path.join(d, f'{name}.pdf'))[0].get_pixmap(dpi=200)
    im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    bb = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda v: 255 if v > 30 else 0).getbbox()
    im = im.crop((max(0, bb[0] - 25), max(0, bb[1] - 25), min(im.width, bb[2] + 25), min(im.height, bb[3] + 25)))
    out = f'/uploads/{BK}-{name}.png'; im.save(os.path.join(REPO, 'public', out.lstrip('/')))
    return out

PICS = {1: ('title', '#법구경 이야기 1 — 법구경 주석서 Dhammapada Aṭṭakathā'), 5: ('title', '#법구경 이야기 1 — 법구경 주석서 Dhammapada Aṭṭakathā'),
        3: ('yetgil', '#옛길'), 7: ('yetgil', '#옛길'), 11: ('wheel', '#법륜')}
SKIP_BIN = {2, 4, 6, 10, 12, 13, 14}   # 같은 자리의 EPS(인쇄용) 그림 — 같은 그림의 JPG 를 씀
OLES = {8: ('sakya', '#사끼야 족 가계도'), 9: ('koliya', '#꼴리야 족 가계도')}
saved = {}
def pic_md(n):
    if n in SKIP_BIN: return ''
    if n in PICS:
        name, alt = PICS[n]
        if name not in saved: saved[name] = save_jpg(n, name)
        return f'![{alt}]({saved[name]})'
    if n in OLES:
        name, alt = OLES[n]
        if name not in saved: saved[name] = f'/uploads/{BK}-{name}.png'   # 가계도는 tools/dl0023_family.py 로 다시 그린 그림
        return f'![{alt}]({saved[name]})'
    raise SystemExit(f'모르는 그림 {n}')

# ---- 글 ----
FN = {}       # 번호 → 글
def ptext(p, bold_ok=True):
    """문단 글 (각주는 [^n], 굵은 글자는 **)."""
    out = []
    def walk(el):
        for ch in el:
            t = ch.tag
            if t == 'LineSeg': walk(ch); continue
            if t == 'Text':
                s = ch.text or ''
                if bold_ok and ch.get('charshape-id') in BOLD and s.strip(): s = re.sub(r'^(\s*)(.*?)(\s*)$', r'\1**\2**\3', s, flags=re.S)
                out.append(s); continue
            if t == 'FootNote':
                n = int(ch.find('.//AutoNumbering').get('number'))
                paras = ch.find('ListHeader').findall('Paragraph')
                FN[n] = '\n'.join(ptext(q).strip() for q in paras if ptext(q).strip())
                out.append(f'[^{n}]'); continue
            if t == 'ControlChar':
                nm = ch.get('name')
                if nm == 'TAB': out.append('\t')
                elif nm == 'LINE_BREAK': out.append('\n')
                continue
            if t == 'TableControl': out.append('\x00TABLE%d\x00' % id(ch)); TABLES[id(ch)] = ch; continue
            if t == 'GShapeObjectControl':
                ids = [int(e.get('bindata-id')) for e in ch.iter() if e.get('bindata-id')]
                oles = [int(e.get('bindata-id', 0)) for e in ch.iter('ShapeOLE')]
                if not ids and ch.find('.//ShapeOLE') is not None: ids = [8, 9]
                for n in ids:
                    md = pic_md(n)
                    if md: out.append('\x00PIC' + md + '\x00')
                continue
    walk(p)
    s = ''.join(out)
    s = s.replace('****', '')
    s = re.sub(r'\*\*([‘’“”\'".,·]+)\*\*', r'\1', s)   # 따옴표 한 글자만 굵은 글자 모양인 곳은 굵게 표시하지 않음
    return s
TABLES = {}
def table_md(t):
    cells = list(t.iter('TableCell'))
    R = max(int(c.get('row')) + int(c.get('rowspan')) for c in cells); C = max(int(c.get('col')) + int(c.get('colspan')) for c in cells)
    g = [[''] * C for _ in range(R)]
    for c in cells:
        tx = ' '.join(ptext(q).replace('\n', ' ').strip() for q in c.findall('Paragraph') if ptext(q).strip())   # 칸 바로 아래 문단만 (각주 속 문단은 빼고)
        g[int(c.get('row'))][int(c.get('col'))] = re.sub(r'\s+', ' ', tx).replace('|', '｜' if False else '|').strip()
    if g[0][0] == 'A.':   # 약어 표(9쪽): 칸 선 없는 줄 맞춤용 표 → 줄마다 '약어  풀이' 글로, 빈 줄은 묶음 사이
        out, cur = [], []
        for row in g:
            if not ''.join(row).strip():
                if cur: out.append('\n'.join(cur)); cur = []
                continue
            cur.append('  '.join(x for x in row if x))
        if cur: out.append('\n'.join(cur))
        return '\n\n'.join(out)
    return '\n'.join('| ' + ' | '.join(row) + ' |' for row in g)

def pshape(p): return PSH[int(p.get('parashape-id'))]

# 쪽 나눔: 문단 첫 줄의 y 가 앞 줄보다 작아지면 새 쪽
page, lasty, pg = 1, None, []
for p in PL:
    first = None
    if p.get('new-page') == '1' and lasty is not None: page += 1; lasty = None
    for s in p.findall('LineSeg'):
        y = int(s.get('y'))
        if lasty is not None and y <= lasty: page += 1   # 같은 y 도 새 쪽 (각주가 쪽을 거의 다 차지해 본문이 한 줄뿐인 쪽)
        if first is None: first = page
        lasty = y
    pg.append(first if first is not None else page)

blocks = []   # (쪽, 종류, 글)
for i, p in enumerate(PL):
    sty = STY.get(p.get('style-id')); ps = pshape(p); al = ps.get('align'); ml = int(ps.get('doubled-margin-left'))
    head = sty in ('개요 2', '개요 3', '개요 5', '개요 5-1', '개요 5-2', '개요 6', '개요 7', '목차')
    t = ptext(p, bold_ok=not head)
    t = t.replace('\r', '')
    if not t.strip(): continue
    blocks.append({'pg': pg[i], 'sty': sty, 'al': al, 'ml': ml, 'ps': p.get('parashape-id'), 't': t, 'i': i})

LAST = max(b['pg'] for b in blocks)

# ---- 쪽 번호 (한글 파일 꼬리말의 쪽 번호) ----
# 한글 파일에 저장된 줄 자리로 센 쪽(pg)은 실제 쪽과 몇 쪽씩 어긋난다(빈 쪽·각주만 있는 쪽 등은 줄 자리로 알 수 없음).
# 그래서 책의 차례(6~8쪽, 한글 파일에 인쇄된 쪽 번호)를 기준점으로 삼아: 차례 항목이 시작하는 쪽 = 차례의 쪽 번호,
# 그 사이 쪽은 하나씩 늘려 셈. 앞쪽(속표지~차례)은 인쇄본 쪽 차례(1 반표제, 2 빈 쪽, 3 속표지, 4 여는 글, 5 예경문, 6~8 차례).
KEY = lambda s: re.sub(r'[^가-힣A-Za-z0-9]', '', re.sub(r'\[\^\d+\]|\*\*', '', s))
anchors = {}
for b in blocks:
    m = re.match(r'^(?:\d+\. )?(.*?)(?: \| [\d, ~]+)?\t\s*(\d+)$', b['t'].strip())
    if b['pg'] <= 8 and m:
        k = KEY(m.group(1))
        hit = next((c['pg'] for c in blocks if c['pg'] > 8 and KEY(c['t']) == k), None)
        if hit: anchors.setdefault(hit, int(m.group(2)))
FRONT = {}
for b in blocks:
    if b['pg'] > 8: break
    FRONT.setdefault(b['pg'], None)
fp = sorted(FRONT)   # 반표제·속표지·여는 글·예경문·차례 3쪽
for k, lab in zip(fp, [1, 3, 4, 5, 6, 7, 8]): FRONT[k] = lab
AK = sorted(anchors)
def LBL(raw):
    if raw in FRONT and FRONT[raw]: return FRONT[raw]
    a = max([k for k in AK if k <= raw] or [AK[0]])
    lab = anchors[a] + (raw - a)
    if 203 < raw <= 250 and raw > 217: lab += 1   # 8번째 이야기: 217쪽 각주가 넘쳐 각주만 있는 쪽이 하나 더 있음 (다음 이야기 시작 256쪽과 맞음)
    nxt = [k for k in AK if k > raw]
    if nxt and lab >= anchors[nxt[0]]: lab = anchors[nxt[0]] - 1
    return lab
LABELS = []
out_pages = []   # [[문단…]]
chapters, subs = [], []
cur_pg = None
def new_page(force=False):
    global cur_pg
    out_pages.append([])
    LABELS.append(LBL(cur_raw))
def add(s): out_pages[-1].append(s)
def flush_fn(page_paras):
    pass

story_no = None
i = 0
cur_raw = blocks[0]['pg']
new_page()
prev_pg = blocks[0]['pg']
pending_fn = []
def end_page():
    # 이 쪽에 나온 각주 내용을 쪽 끝에
    refs = [int(x) for x in re.findall(r'\[\^(\d+)\](?!:)', '\n'.join(out_pages[-1]))]
    for n in refs:
        if n in FN and n not in DONE:
            # 각주 안의 표(각주 197·198)는 각주 글 바로 뒤에 표 문단으로
            txt = ' '.join(x for k, x in expand(FN[n]) if k == 't').strip()
            out_pages[-1].append(f'[^{n}]: {txt}')
            out_pages[-1].extend(x for k, x in expand(FN[n]) if k == 'tbl')
            DONE.add(n)
DONE = set()
def chapter(title, sub=False):
    title = re.sub(r'\[\^\d+\]', '', title).replace('**', '').strip()
    title = re.sub(r'\s+', ' ', title)
    (subs if sub else chapters).append((title, len(out_pages)))

grp = None   # 묶음(게송·가운데 줄)
def close_grp():
    global grp
    if grp: add(grp[0] + ('\n'.join(grp[1]) if grp[0] != '::' else '\n:: '.join(grp[1])).replace(':: ', ':: ', 1) if False else ((grp[0] + ' ' if grp[0] else '') + ('\n' if grp[0] != '::' else '\n:: ').join(grp[1])))
    grp = None
def group(kind, line):
    global grp
    if grp and grp[0] == kind: grp[1].append(line); return
    close_grp(); grp = [kind, [line]]

def expand(t):
    """\x00TABLE…\x00 · \x00PIC…\x00 를 따로 문단으로."""
    parts = re.split(r'\x00(TABLE\d+|PIC[^\x00]*)\x00', t)
    res = []
    for k, x in enumerate(parts):
        if k % 2 == 0:
            if x.strip(): res.append(('t', x))
        elif x.startswith('TABLE'): res.append(('tbl', table_md(TABLES[int(x[5:])])))
        else: res.append(('pic', x[3:]))
    return res

for bi, b in enumerate(blocks):
    if b['pg'] != prev_pg:
        close_grp(); end_page(); cur_raw = b['pg']; new_page(); prev_pg = b['pg']
    sty, t = b['sty'], b['t']
    tt = t.strip()
    # 장(챕터) 시작
    if b['pg'] == 1 and not chapters: chapter('속표지')
    if b['pg'] == 4 and not any(c[0] == '여는 글' for c in chapters):
        close_grp();
        if out_pages[-1]: end_page(); new_page()
        chapter('여는 글')
    if sty == '개요 1' and b['ps'] == '14' and not any(c[0] == '예경문' for c in chapters):
        close_grp();
        if out_pages[-1]: end_page(); new_page()
        chapter('예경문')
    if b['pg'] == LAST and not any(c[0] == '판권지' for c in chapters):
        close_grp();
        if out_pages[-1]: end_page(); new_page()
        chapter('판권지')
    for kind, x in expand(t):
        if kind == 'pic': close_grp(); add(x); continue
        if kind == 'tbl': close_grp(); add(x); continue
        x = x.strip('\n').rstrip()
        xs = x.strip()
        if b['pg'] == LAST:   # 판권지: 줄마다 그대로, '⼁' → '|'
            xs = x.replace('⼁', '|')
            if sty == '개요 5-1': close_grp(); add('**' + xs.strip() + '**'); continue
            group('', xs.rstrip()); continue
        if sty == '개요 5' and xs in ('제1권 목차', '약어', '법구경 주석서 해제', '일러두기'):
            close_grp()
            if out_pages[-1]: end_page(); new_page()
            chapter(xs); add('## ' + xs); continue
        if sty == '개요 5-1':
            close_grp()
            if out_pages[-1]: end_page(); new_page()
            chapter(xs); add('## ' + xs); continue
        if sty == '개요 6':   # 장 표지
            close_grp()
            if out_pages[-1]: end_page(); new_page()
            nxt = next((c['t'].strip() for c in blocks[bi + 1:bi + 3] if c['sty'] == '개요 7'), '')
            chapter(f'{xs} {nxt}'.strip()); add('^^ ' + xs); continue
        if sty == '개요 7': close_grp(); add(':: ' + xs); continue
        if sty == '개요 2':
            close_grp()
            if re.match(r'^[가-힣 ]+번째 이야기$', xs):
                if out_pages[-1]: end_page(); new_page()
                nxt = next((c['t'].strip() for c in blocks[bi + 1:bi + 2] if c['sty'] == '개요 2'), '')
                chapter(f'{xs} : {nxt}' if nxt else xs)   # '두 번째 이야기 : 제목' (운영자 요청, 2026-11-12)
            add(('## ' if b['pg'] > 3 else ':: ') + xs); continue
        if sty in ('개요 3', '개요 5-2', '개요 5'):
            close_grp(); chapter(xs, sub=(sty != '개요 5')) if sty != '개요 5' else None; add(('## ' if b['pg'] > 3 else ':: ') + xs); continue
        if sty == '목차' or b['ps'] == '18' or (b['pg'] in (6, 7, 8) and sty == '바탕글'):
            line = xs
            m = re.match(r'^(.*?)\t\s*(\d+)$', line)
            if m: line = f'- {m.group(1).strip()} | {m.group(2)}'
            elif sty == '목차': line = ('~\n' if grp and grp[0] == '%%' else '') + f'**{line}**'
            group('%%', line); continue
        if sty == '개요 1' and b['ps'] == '14': group('::', xs); continue
        if sty == '개요 1' or sty == '시들': group('++', xs); continue
        if b['al'] == 'center': group('::', xs); continue
        if b['al'] == 'right': close_grp(); add('>> ' + xs); continue
        close_grp()
        if b['ml'] > 0: add('++ ' + xs); continue
        add(xs)
close_grp(); end_page()

# 각주가 다 들어갔는지
miss = sorted(set(FN) - DONE)
assert not miss, ('쪽 끝에 넣지 못한 각주', miss[:10])

# 인쇄본 맨 앞(반표제 앞)의 지도 두 장 — 한글 파일에는 없어 tools/dl0023_maps.py 로 인쇄본 지도를 다시 그린 그림 (운영자 요청, 2026-11-12)
MAPS = ['/uploads/DL-0023-map-india.png', '/uploads/DL-0023-map-majjhimadesa.png']
body = '=== ===\n![#부처님 당시 인도 B.C 500년경 — 16대국 지도](' + MAPS[0] + ')\n\n=== ===\n![#불교중심지역 majjhimadesa 지도](' + MAPS[1] + ')\n\n'
chapters = [('지도', 1)] + [(t, n + 2) for t, n in chapters]   # 지도 두 쪽 뒤로 밀림
subs = [(t, n + 2) for t, n in subs]
saved['map-india'], saved['map-majjhimadesa'] = MAPS
for lab, ps in zip(LABELS, out_pages):
    body += f'=== {lab}쪽 ===\n' + '\n\n'.join(x for x in ps if x.strip()) + '\n\n'
body = body.rstrip() + '\n'
toc = [{'title': t, 'page': n, 'sub': False} for t, n in chapters] + [{'title': t, 'page': n, 'sub': True} for t, n in subs]
toc.sort(key=lambda x: (x['page'], x['sub']))
images = sorted(set(saved.values()))
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': images, 'body': body}, open(os.path.join(REPO, 'content/texts', BK + '.json'), 'w'), ensure_ascii=False, indent=2)
open(os.path.join(REPO, 'content/texts', BK + '.json'), 'a').write('\n')
print(f'쪽 {len(out_pages)} · 장 {len(chapters)} · 소제목 {len(subs)} · 각주 {len(FN)} · 그림 {images}')
