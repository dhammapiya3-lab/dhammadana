#!/usr/bin/env python3
"""PDF를 도서관 '온라인 읽기' 자료로 바꿉니다.

쓰는 법 (dhammadana 폴더에서):
  python3 tools/pdf2reader.py 책.pdf DL-0007 초판
  python3 tools/pdf2reader.py 책.pdf DL-0007 초판 --offset 4     # PDF 5번째 쪽이 인쇄된 1쪽일 때
  python3 tools/pdf2reader.py 책.pdf DL-0007 초판 --toc toc.txt  # 목차를 직접 줄 때 (한 줄에 "제목<TAB>PDF쪽번호")

만들어지는 것 (tools/out/ 아래, 그대로 R2에 올리면 됩니다):
  reader/DL-0007/초판/manifest.json   쪽 목록·목차·본문 글
  reader/DL-0007/초판/p/0001.webp     보통 크기 쪽 그림 (가로 1000px)
  reader/DL-0007/초판/big/0001.webp   확대용 쪽 그림 (가로 1800px)
  pdf/DL-0007/DL-0007_초판.pdf         내려받기용 PDF 사본

필요한 것: pip install pypdfium2 pypdf pillow
"""
import argparse, json, os, re, shutil, sys, unicodedata

import pypdfium2 as pdfium
from pypdf import PdfReader

ap = argparse.ArgumentParser(description='PDF → 온라인 읽기 자료')
ap.add_argument('pdf'); ap.add_argument('book_id'); ap.add_argument('edition', nargs='?', default='초판')
ap.add_argument('--offset', type=int, default=None, help='인쇄된 1쪽 앞에 있는 PDF 쪽 수')
ap.add_argument('--toc', help='목차 파일 (제목<TAB>PDF쪽번호)')
ap.add_argument('--out', default=os.path.join(os.path.dirname(__file__), 'out'))
ap.add_argument('--width', type=int, default=1000); ap.add_argument('--big', type=int, default=1800)
ap.add_argument('--quality', type=int, default=80)
ap.add_argument('--visible-only', action='store_true', help='화면에 보이지 않는 숨은 글(InDesign 에 남은 옛 글 등)은 빼고 읽기')
ap.add_argument('--footnotes', action='store_true', help='작은 글씨 위첨자 숫자는 [^번호], 각주 줄은 [^번호]: 로 표시')
ap.add_argument('--headings', action='store_true', help='본문보다 큰 글씨 줄은 소제목(## )으로 표시')
ap.add_argument('--visual-order', action='store_true', help='줄을 쪽에 인쇄된 위치(위→아래) 순서로 다시 놓기 (PDF 안의 저장 순서가 인쇄 순서와 다를 때)')
ap.add_argument('--line-breaks', action='store_true', help='짧은 줄(게송 등)은 인쇄된 대로 줄을 바꿈')
ap.add_argument('--no-text', action='store_true', help='본문 글을 넣지 않음 (그림만)')
a = ap.parse_args()
LINEBREAKS = a.line_breaks

if not re.fullmatch(r'DL-\d{4}', a.book_id):
    sys.exit('자료번호는 DL-0001 처럼 써 주세요.')
base = os.path.join(a.out, 'reader', a.book_id, a.edition)
for d in ('p', 'big'):
    os.makedirs(os.path.join(base, d), exist_ok=True)

doc = pdfium.PdfDocument(a.pdf)
rd = PdfReader(a.pdf)
N = len(doc)
print(f'『{a.pdf}』 {N}쪽을 바꿉니다…')

# 인쇄 쪽 번호
labels = [''] * N
try:
    pl = list(rd.page_labels)
    if any(l and l != str(i + 1) for i, l in enumerate(pl)):
        labels = [str(l or '') for l in pl]
except Exception:
    pass
if a.offset is not None:
    labels = [str(i + 1 - a.offset) if i + 1 - a.offset > 0 else '' for i in range(N)]

ODD = re.compile(r'[\ufffd\ufffe\uffff\ue000-\uf8ff]')
END = re.compile(r'[.?!。…”’"\')」』:]$')
HY = re.compile(r'(.)\ufffe')
def fix_hyphen(t):
    """pdfium 은 줄 끝에 인쇄된 붙임표(-)를 U+FFFE 로 내줍니다. 인쇄된 그대로 '-' 로 되돌립니다.
    한글 음역의 장음 표시(예: 아웨라- 혼뚜)는 뒤에 빈칸이 있으므로 빈칸도 살립니다."""
    return HY.sub(lambda m: m.group(1) + ('- ' if '\uac00' <= m.group(1) <= '\ud7a3' else '-'), t)


FNREF = re.compile(r'\[\^([0-9]+)\]:?')
def unmark(t): return FNREF.sub(lambda m: m.group(1), t)
def mark_footnotes(tp, raw):
    """글자 크기로 각주를 찾아 표시만 붙입니다(글자는 그대로).
    - 본문보다 아주 작은 숫자(위첨자) → [^번호]
    - 본문보다 작은 글씨 줄이 '번호 + 빈칸'으로 시작 → [^번호]: (각주 본문)"""
    import pypdfium2.raw as R2
    n = tp.count_chars()
    def size(i):
        try: l, b, r, t = tp.get_charbox(i, loose=True); return t - b
        except Exception: return 0
    cs = [(tp.get_text_range(i, 1), size(i)) for i in range(n)]
    if ''.join(c for c, _ in cs) != raw: return raw
    from collections import Counter
    sizes = Counter(round(z, 1) for c, z in cs if c.strip() and c not in '0123456789')
    if not sizes: return raw
    tot = sum(sizes.values())
    big = [z for z, k in sizes.items() if k >= max(30, 0.15 * tot)]
    body = max(big) if big else sizes.most_common(1)[0][0]   # 본문 크기 (각주가 더 많은 쪽도 있어서 '많이 쓰인 크기 중 가장 큰 것')
    out, i, line_start = [], 0, True
    while i < n:
        c, z = cs[i]
        if c in '0123456789':
            j = i
            while j < n and cs[j][0] in '0123456789': j += 1
            num = ''.join(x for x, _ in cs[i:j])
            nxt = cs[j][0] if j < n else ''
            if z < body * 0.95 and (nxt == '\u3000' or (line_start and body * 0.75 <= z and nxt in (' ', '\t'))):
                out.append(f'[^{num}]:'); i = j; line_start = False; continue
            prev = out[-1][-1:] if out else ''
            if z < body * 0.75 and prev and not prev.isspace():
                out.append(f'[^{num}]'); i = j; line_start = False; continue
            out.append(num); i = j; line_start = False; continue
        out.append(c)
        if c == '\n': line_start = True
        elif c.strip(): line_start = False
        i += 1
    return ''.join(out)

HMARK = '\x01'; HSTART = '\x02'
def heading_lines(tp, raw):
    """본문보다 큰 글씨(1.2배 이상)로 된 줄 번호들 (raw 는 pdfium 원래 글, 줄은 \r\n 으로 나뉨)"""
    n = tp.count_chars()
    if ''.join(tp.get_text_range(i, 1) for i in range(n)) != raw: return {}
    def size(i):
        try: l, b, r, t = tp.get_charbox(i, loose=True); return t - b
        except Exception: return 0
    from collections import Counter
    sz = [size(i) if raw[i].strip() else 0 for i in range(n)]
    allsz = Counter(round(z, 1) for i, z in enumerate(sz) if raw[i].strip())
    tot = sum(allsz.values()); big = [z for z, k in allsz.items() if k >= max(30, 0.15 * tot)]
    body = max(big) if big else (allsz.most_common(1)[0][0] if allsz else 0)
    out, pos = {}, 0
    for li, ln in enumerate(raw.split('\r\n')):
        ss = sorted(sz[pos + k] for k, c in enumerate(ln) if c.strip())
        if body and ss and sum(1 for c in ln if c.isalpha()) >= 2 and ss[len(ss) // 2] >= body * 1.2: out[li] = ss[len(ss) // 2]
        pos += len(ln) + 2
    return out
def add_hmarks(t, idx):
    # 크기가 같은 소제목 줄끼리만 한 제목으로 잇고(\x01), 크기가 다르면 새 제목으로 시작(\x02)
    ls = t.split('\r\n'); out = []
    for i, l in enumerate(ls):
        if i not in idx: out.append(l); continue
        cont = (i - 1) in idx and abs(idx[i - 1] - idx[i]) <= idx[i] * 0.1
        out.append((HMARK if cont else HSTART) + l)
    return '\r\n'.join(out)

def visual_order(tp, raw, t, full):
    """줄들을 인쇄된 위치(위→아래, 같은 높이면 왼쪽→오른쪽) 순서로 놓습니다. 줄 안의 글자 순서는 그대로."""
    n = tp.count_chars()
    if ''.join(tp.get_text_range(i, 1) for i in range(n)) != raw: return t, full
    rl = raw.split('\r\n'); tl = t.split('\r\n')
    if len(rl) != len(tl): return t, full
    keys, pos = [], 0
    for li, ln in enumerate(rl):
        bs, xs = [], []
        for k, c in enumerate(ln):
            if c.strip():
                try: l, b, r, tt = tp.get_charbox(pos + k); bs.append(b); xs.append(l)
                except Exception: pass
        keys.append((-(sorted(bs)[len(bs) // 2]) if bs else None, min(xs) if xs else 0))
        pos += len(ln) + 2
    # 빈 줄은 바로 앞 줄 자리에 붙여 둠
    last = (0, 0); ks = []
    for k in keys:
        if k[0] is None: ks.append((last[0], last[1] + 0.001))
        else: ks.append(k); last = k
    # 높이가 2pt 안쪽이면 같은 줄 높이로 보고 왼쪽부터
    order = sorted(range(len(tl)), key=lambda i: (round(ks[i][0] / 2), ks[i][1], i))
    return '\r\n'.join(tl[i] for i in order), [full[i] for i in order] if full and len(full) == len(tl) else full

def clean(t, label='', full=None):
    """원문 글자는 하나도 바꾸지 않고, 줄바꿈만 정리합니다.
    - 줄 끝에 빈칸이 있으면(낱말 사이) 빈칸으로 잇고, 없으면(낱말 중간) 붙여 잇습니다.
    - 줄이 오른쪽 끝까지 차지 않았으면(제목·문단 끝) 줄을 나눕니다.
    - 빈칸 없이 문장부호로 끝난 줄은 문단(게송이면 한 줄) 끝으로 봅니다. 글자로 끝나면 낱말 중간이라 붙입니다.
    - 맨 위 줄이 쪽 번호뿐이면(머리·꼬리 쪽 번호) 뺍니다."""
    t = unicodedata.normalize('NFC', fix_hyphen(t).replace('\r\n', '\n').replace('\r', '\n'))
    lines = t.split('\n')
    full = full or [True] * len(lines)
    if lines and lines[0].strip() and lines[0].strip() == str(label): lines = lines[1:]; full = full[1:]
    while lines and not lines[-1].strip(): lines = lines[:-1]; full = full[:-1]
    if lines and lines[-1].strip() == str(label): lines = lines[:-1]; full = full[:-1]   # 아래쪽 쪽 번호
    paras, buf = [], ''
    for k, raw in enumerate(lines):
        if not raw.strip():
            if buf.strip(): paras.append(buf.strip()); buf = ''
            continue
        if raw[:1] in (HMARK, HSTART):     # 소제목 줄: 앞 문단을 끝내고, 이어지는 같은 크기 소제목 줄끼리만 잇기
            h = raw[1:].replace('\t', ' ')
            if buf.strip() and (raw[0] == HSTART or not buf.startswith('## ')): paras.append(buf.strip()); buf = ''
            buf = ('## ' + h.lstrip()) if not buf else (buf + h)
            nxt = lines[k + 1] if k + 1 < len(lines) else ''
            if not nxt.startswith(HMARK): paras.append(buf.strip()); buf = ''
            continue
        line = raw.replace('\t', ' ')
        if not buf: buf = line.lstrip()
        else: buf += line
        if full and not full[k] and LINEBREAKS:
            # 오른쪽 끝까지 차지 않은 짧은 줄(게송·발원문·문단 끝): 문장부호로 끝나면 문단 끝, 아니면 인쇄된 대로 줄만 바꿈
            if re.search(r'\[\^\d+\]$', line.rstrip()) or re.fullmatch(r'\s*\[\^\d+\]\s*', line):
                buf = buf.rstrip(); continue   # 위첨자 각주 번호 때문에 갈라진 줄: 그대로 이어 붙임
            if re.search(r'[.?!。…”’"\')」』]$', line.rstrip()): paras.append(buf.strip()); buf = ''
            else: buf = buf.rstrip() + '\n'
            continue
        if line.endswith(' '):
            continue                      # 낱말 사이 줄바꿈: 빈칸 그대로 둠
        if re.search(r'\[\^\d+\]$', line.rstrip()) and full[k]:
            continue                      # 각주 번호로 끝난 꽉 찬 줄: 문단 중간
        last = line.rstrip()[-1:]
        if (last and not last.isalnum()) or last.isdigit() or not full[k]:
            paras.append(buf.strip()); buf = ''   # 문장부호로 끝난 줄: 문단(또는 게송 줄) 끝
        # 그 밖에는 낱말 중간 줄바꿈: 다음 줄을 붙여 이음
    if buf.strip(): paras.append(buf.strip())
    return '\n\n'.join(re.sub(r' *\n *', '\n', re.sub(r' {2,}', ' ', p)).strip() for p in paras)

def same_text(raw, out, label=''):
    """빈칸·줄바꿈·쪽번호를 빼고 원문과 글자가 똑같은지 확인"""
    r = unicodedata.normalize('NFC', fix_hyphen(raw))
    rl = r.replace('\r', '').split('\n')
    if rl and rl[0].strip() == str(label): rl = rl[1:]
    strip = lambda x: re.sub(r'\s+', '', x)
    return strip('\n'.join(rl)) == strip(re.sub(r'(^|\n)## ', r'\1', unmark(out)))


# 숨은 글 찾기: 글 덩어리 하나를 지웠을 때 쪽 그림이 전혀 바뀌지 않으면 보이지 않는 글입니다.
import pypdfium2.raw as _R
from PIL import ImageChops as _IC
_DATA = None
def _tobjs(page): return [o for o in page.get_objects(max_depth=1) if o.type == _R.FPDF_PAGEOBJ_TEXT]
def _rend(page): return page.render(scale=2, grayscale=True).to_pil().convert('L')
def _addr(h):
    import ctypes; return ctypes.cast(h, ctypes.c_void_p).value
def _render_without(i, ks):
    d = pdfium.PdfDocument(_DATA); p = d[i]; objs = _tobjs(p)
    for k in sorted(ks, reverse=True): p.remove_obj(objs[k])
    p.gen_content(); return d, p
def hidden_removed_page(i):
    """i번째 쪽에서 보이지 않는 글 덩어리를 뺀 새 쪽과, 뺀 글을 돌려줍니다.
    1) 하나씩 지워 봐서 쪽 그림이 그대로인 덩어리를 고르고,
    2) 고른 것을 한꺼번에 지워도 그림이 그대로인 것만 남깁니다(보이는 글이 같이 사라지지 않게).
    3) 다른 글 바로 위에 똑같이 겹쳐 찍힌 짧은 글(겹친 옛 글)도 뺍니다."""
    base = _rend(pdfium.PdfDocument(_DATA)[i]); n = len(_tobjs(pdfium.PdfDocument(_DATA)[i]))
    def changed(ks):  # 지웠을 때 눈에 띄게 바뀐 점의 수
        df = _IC.difference(base, _rend(_render_without(i, ks)[1]))
        return sum(1 for v in df.getdata() if v > 40) if df.getbbox() else 0
    d0 = pdfium.PdfDocument(_DATA); p0 = d0[i]; t0 = p0.get_textpage(); o0 = _tobjs(p0); lens = []
    for o in o0:
        try: o.textpage = t0; lens.append(len(re.sub(r'\s', '', o.extract())))
        except Exception: lens.append(0)
    # 글자 4개 이상인 덩어리가 지워도 점 몇 개(25개 이하)만 바뀌면 숨은 글로 봅니다(숨은 글이 남기는 작은 점 자국 포함).
    digits_only = []
    for o in o0:
        try: digits_only.append(bool(re.fullmatch(r'\s*[0-9]{1,2}\s*', o.extract())))
        except Exception: digits_only.append(False)
    allow = lambda ks: sum(25 if lens[k] >= 4 else (12 if digits_only[k] else 0) for k in ks)
    cand = [k for k in range(n) if changed([k]) <= allow([k])]
    inv = []
    for k in cand:
        if changed(inv + [k]) <= allow(inv + [k]): inv.append(k)
    # 겹쳐 찍힌 글
    d, p = _render_without(i, inv); objs = _tobjs(p); addr = {_addr(o.raw): j for j, o in enumerate(objs)}
    tp = p.get_textpage(); chars = {}
    for c in range(tp.count_chars()):
        ch = tp.get_text_range(c, 1)
        if not ch.strip(): continue
        j = addr.get(_addr(_R.FPDFText_GetTextObject(tp.raw, c)))
        if j is None: continue
        chars.setdefault(j, []).append((ch, tp.get_charbox(c)))
    def ov(a, b):
        w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
        if w <= 0 or h <= 0: return 0
        return w * h / max(1e-6, min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1])))
    dup = []
    for j, cs in chars.items():
        if len(cs) > 200: continue
        hit = 0; partner = {}
        for ch, bx in cs:
            for j2, cs2 in chars.items():
                if j2 == j or j2 in dup: continue
                if any(c2 == ch and ov(bx, b2) > 0.6 for c2, b2 in cs2): hit += 1; partner[j2] = partner.get(j2, 0) + 1; break
        if cs and hit / len(cs) >= 0.9 and all(len(chars[j2]) >= len(cs) for j2 in partner): dup.append(j)
    tp0 = p.get_textpage(); gone = []
    for k in inv:
        pass
    od = pdfium.PdfDocument(_DATA); op = od[i]; oobjs = _tobjs(op); otp = op.get_textpage()
    for k in inv:
        try: oobjs[k].textpage = otp; gone.append(oobjs[k].extract())
        except Exception: gone.append('')
    for j in dup:
        try: objs[j].textpage = tp0; gone.append('(겹친 글) ' + objs[j].extract())
        except Exception: gone.append('(겹친 글)')
    for j in sorted(dup, reverse=True): p.remove_obj(objs[j])
    if dup: p.gen_content()
    return d, p, gone

if a.visible_only: _DATA = open(a.pdf, 'rb').read()
hidden_log = {}
pages, odd_pages, changed_pages = [], [], []
for i in range(N):
    pg = doc[i]
    w, h = pg.get_size()
    for d, W in (('p', a.width), ('big', a.big)):
        img = pg.render(scale=W / w).to_pil()
        img.save(os.path.join(base, d, f'{i+1:04d}.webp'), 'WEBP', quality=a.quality, method=4)
    text = ''
    if not a.no_text:
        src = pg
        if a.visible_only:
            _keep, src, gone = hidden_removed_page(i)
            if any(g.strip() for g in gone): hidden_log[i + 1] = gone
        tp = src.get_textpage(); raw = tp.get_text_range()
        # 줄마다 오른쪽 끝 위치: 꽉 찬 줄인지(낱말 중간 줄바꿈 가능) 알아보기
        rights, pos = [], 0
        for ln in raw.split('\r\n'):
            st = ln.rstrip(); r = None
            if st:
                try: r = tp.get_charbox(pos + len(st) - 1)[2]
                except Exception: r = None
            rights.append(r); pos += len(ln) + 2
        known = [r for r in rights if r is not None]
        edge = max(known) if known else 0
        full = [r is None or r >= edge - 14 for r in rights]
        tp.close()
        hidx = heading_lines(src.get_textpage(), raw) if a.headings else set()
        raw_m = mark_footnotes(src.get_textpage(), raw) if a.footnotes else raw
        if hidx: raw_m = add_hmarks(raw_m, hidx)
        if a.visual_order: raw_m, full = visual_order(src.get_textpage(), raw, raw_m, full)
        text = clean(raw_m, labels[i] or (i + 1), full)
        if a.footnotes: text = re.sub(r'[ \t]*(?<!^)(?<!\n)(\[\^\d+\]:)', r'\n\n\1', text)  # 문단 중간에 붙은 각주는 따로 떼기
        if a.visual_order:
            from collections import Counter as _C
            _r = unicodedata.normalize('NFC', fix_hyphen(raw)); _rl = _r.replace('\r', '').split('\n')
            if _rl and _rl[0].strip() == str(labels[i] or (i + 1)): _rl = _rl[1:]
            _o = re.sub(r'(^|\n)## ', r'\1', unmark(text))
            if _C(re.sub(r'\s', '', '\n'.join(_rl))) != _C(re.sub(r'\s', '', _o)): changed_pages.append(i + 1)
        elif not same_text(raw, text, labels[i] or (i + 1)): changed_pages.append(i + 1)
        if ODD.search(text): odd_pages.append(i + 1)
    pages.append({'img': f'p/{i+1:04d}.webp', 'big': f'big/{i+1:04d}.webp', 'w': round(w), 'h': round(h), 'label': labels[i], 'text': text})
    print(f'\r  {i+1}/{N}', end='', flush=True)
print()

# 목차
toc = []
if a.toc:
    for line in open(a.toc, encoding='utf-8'):
        if '\t' in line:
            t, p = line.rstrip('\n').rsplit('\t', 1)
            if p.strip().isdigit(): toc.append({'title': t.rstrip(), 'page': int(p)})  # 앞 공백 = 아랫단계
else:
    def walk(items, depth=0):
        for it in items:
            if isinstance(it, list): walk(it, depth + 1); continue
            try:
                n = rd.get_destination_page_number(it) + 1
                toc.append({'title': ('  ' * depth) + it.title.strip(), 'page': n})
            except Exception: pass
    try: walk(rd.outline)
    except Exception: pass
for t in toc:
    t['label'] = labels[t['page'] - 1] if 0 < t['page'] <= N else ''

if a.visible_only:
    with open(os.path.join(base, 'hidden.txt'), 'w', encoding='utf-8') as f:
        for k, v in hidden_log.items(): f.write(f'=== {k}쪽 (뺀 숨은 글) ===\n' + '\n'.join(v) + '\n\n')
man = {'book': a.book_id, 'edition': a.edition, 'pages': pages, 'toc': toc}
with open(os.path.join(base, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(man, f, ensure_ascii=False)

pdf_dir = os.path.join(a.out, 'pdf', a.book_id); os.makedirs(pdf_dir, exist_ok=True)
shutil.copyfile(a.pdf, os.path.join(pdf_dir, f'{a.book_id}_{a.edition}.pdf'))

size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(base) for f in fs)
print(f'완료: {base}  ({size/1e6:.1f} MB)')
print(f'  숨은 글을 뺀 쪽: {len(hidden_log)}쪽 → hidden.txt 에서 확인') if a.visible_only else None
print(f'  목차 {len(toc)}개' + ('' if toc else ' — PDF에 목차(책갈피)가 없습니다. --toc 로 직접 줄 수 있습니다.'))
print('  인쇄 쪽 번호: ' + ('있음' if any(labels) else '없음 — 필요하면 --offset 을 쓰세요.'))
if not a.no_text and not any(p['text'] for p in pages):
    print('  ⚠ 글자를 뽑지 못했습니다. 스캔본이면 쪽 보기만 됩니다(검색·듣기·밑줄 안 됨).')
if changed_pages:
    print(f'  ⚠ 원문과 글자가 달라진 쪽: {changed_pages} — 확인이 필요합니다.')
else:
    print('  ✓ 모든 쪽의 본문 글자가 원문과 똑같습니다 (빈칸·줄바꿈·쪽번호 제외).')
if odd_pages:
    print(f'  ⚠ 깨진 글자가 있는 쪽: {odd_pages[:20]}{" …" if len(odd_pages) > 20 else ""} — 빨리어 점 글자가 깨졌을 수 있으니 확인하세요.')
print(f'다음: 책 자료({a.book_id})의 이 판에서 "온라인 읽기"를 켜고, PDF 주소를 pdf/{a.book_id}/{a.book_id}_{a.edition}.pdf 로 적으세요.')
