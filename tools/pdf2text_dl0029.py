"""『부처님, 그분 – 생애와 가르침』(DL-0029, 삐야닷시 스님 지음, 정원 김재성 옮김, 고요한소리 법륜·하나 개정판 12쇄) PDF → content/texts/DL-0029.json
  python3 tools/pdf2text_dl0029.py 책.pdf

PDF 160쪽 (InDesign). PDF 쪽 = 인쇄 쪽 + 1 (PDF 1쪽은 앞표지). 쪽 이름은 쪽 아래 인쇄된 번호(서론 7쪽 ~ 저자 소개 145쪽).
앞쪽: PDF 2 속표지, 3 원서 속표지, 4 일러두기, 5~6 차례, 7 예경문 (쪽 번호 없음).
뒤쪽: PDF 147~154 〈고요한소리〉 안내·도서 목록은 넣지 않음(운영자 확인 전), 155 판권지, 156~157 부록 지도(펼친 두 쪽), 158~159 부록 가계도(펼친 두 쪽), 160 뒤표지.
본문 KoPub바탕 Light 10.9 — 첫 줄 들여쓰기(+11.3pt)로 문단 시작, 쪽이 넘어가도 들여쓰지 않은 줄이면 이어 붙임.
인용문(경기바탕 Bold 9.9, 통째로 들여 씀) → `++ **…**` (빈 줄 간격으로 문단 나눔).
장 제목 경기바탕 13.9 → 장, 소제목 KoPub바탕 PB 11.4 → `## `, 작은 굵은 제목(KoPub돋움 PB 10.2: 첫해·2, 3, 4년째 …) → `**…**`.
각주 번호(KoPub바탕 PM 6.4) → [^n], 쪽 아래 각주(번호 PM 7.9 + 8.4) → [^n]: …, 다음 쪽으로 넘어간 각주는 이어 붙임.
로마자 기울임(일러두기: 로마자 빠알리어와 영문 책 제목은 이탤릭체) → °°…°°.
글자는 PDF 그대로. 속표지의 'ㅣ'(구분 막대) → '|' (구분 막대 원칙).
"""
import sys, re, json, os, collections
import fitz

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK, ED = 'DL-0029', '개정판 12쇄'
src = fitz.open(pdf)
log = collections.Counter()
UP = os.path.join(REPO, 'public/uploads')


def vlines(n):
    """한 쪽의 줄(같은 높이 조각은 한 줄로). [y아래, x0, x1, spans] — 각주 번호(위첨자)만 있는 조각은 가장 가까운 줄에 붙임"""
    L = []; S = []
    for b in src[n - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text']]
            if not ''.join(s['text'] for s in sp).strip(): continue
            x0, y0, x1, y1 = l['bbox']
            r = [y1, x0, x1, sp, (y0 + y1) / 2]
            (S if all(is_ref(s) or not s['text'].strip() for s in sp) else L).append(r)
    L.sort(key=lambda r: r[4])
    out = []
    for r in L:
        if out and abs(out[-1][4] - r[4]) < 3:
            o = out[-1]; o[3] = o[3] + r[3]; o[1] = min(o[1], r[1]); o[2] = max(o[2], r[2]); o[0] = max(o[0], r[0])
        else: out.append(r)
    for r in S:
        if not out: out.append(r); continue
        o = min(out, key=lambda q: abs(q[4] - r[4]) + (0 if q[1] <= r[1] + 1 else 50))
        o[3] = o[3] + r[3]; o[2] = max(o[2], r[2])
    for o in out:
        o[3].sort(key=lambda s: s['bbox'][0])
    return [o[:4] for o in out]


def is_ref(s): return s['font'] == 'KoPubBatangPM' and s['size'] < 7 and s['text'].strip().isdigit()
def is_ital(s): return bool(s['flags'] & 2) and s['text'].strip() and not is_ref(s)


def text_of(spans, refs=True):
    """조각 → 글. 각주 번호 [^n], 기울임 °°…°°"""
    o = ''; it = ''
    def flush():
        nonlocal o, it
        if it:
            a = it[:len(it) - len(it.lstrip())]; z = it[len(it.rstrip()):]
            o += a + '°°' + it.strip() + '°°' + z; it = ''
    for s in spans:
        t = re.sub('[\x07\n\r]', '', s['text']).replace('\t', ' ')
        if refs and is_ref(s):
            flush(); o = o.rstrip(' ') if False else o; o += f'[^{t.strip()}]'; log['각주 번호'] += 1
        elif is_ital(s): it += t
        else:
            if it and not t.strip(): it += t; continue
            flush(); o += t
    flush()
    return o


def kind(r):
    sp = [s for s in r[3] if s['text'].strip() and not is_ref(s)]
    if not sp: return 'B'
    big = max(sp, key=lambda s: len(s['text'].strip()))
    f, z = big['font'], round(big['size'], 1)
    if f.startswith('GyeonggiBatangB') and z >= 13: return 'H1'
    if f == 'KoPubBatangPB' and z >= 11: return 'H2'
    if f == 'KoPubDotumPB' and 10 <= z < 11: return 'H3'
    mx = max(s['size'] for s in sp)
    if mx < 8.6: return 'F'
    if any(s['font'].startswith('GyeonggiBatangB') for s in sp if len(s['text'].strip()) > 1): return 'Q'
    return 'B'


def render(n, rect, name, dpi=300):
    pix = src[n - 1].get_pixmap(dpi=dpi, clip=rect)
    path = os.path.join(UP, name); pix.save(path); return '/uploads/' + name


def spread(n1, r1, n2, r2, name, dpi=250):
    from PIL import Image
    import io
    a = Image.open(io.BytesIO(src[n1 - 1].get_pixmap(dpi=dpi, clip=r1).tobytes('png')))
    b = Image.open(io.BytesIO(src[n2 - 1].get_pixmap(dpi=dpi, clip=r2).tobytes('png')))
    h = max(a.height, b.height)
    m = Image.new('RGB', (a.width + b.width, h), 'white'); m.paste(a, (0, 0)); m.paste(b, (a.width, 0))
    path = os.path.join(UP, name); m.save(path, quality=88, optimize=True); return '/uploads/' + name


PAGES = []   # {'lab','paras','fns'}
images = []
chapters = []  # (title, page index, para index)
subs = []
FN = {}      # 번호 → 글
last_fn = None


def newpage(lab=''):
    P = {'lab': lab, 'paras': [], 'fns': []}; PAGES.append(P); return P


# ---------- 앞쪽 ----------
P = newpage()
wheel = render(2, fitz.Rect(155, 92, 205, 141), f'{BK}-wheel.png', 400); images.append(wheel)
L = vlines(2)
P['paras'] = ['![#법륜](%s)' % wheel, ':: ' + text_of(L[0][3]).strip(), '^^ ' + text_of(L[1][3]).strip(),
              ':: ' + text_of(L[2][3]).strip(), ':: ' + re.sub(r'\s*ㅣ\s*', ' | ', text_of(L[3][3]).strip())]
chapters.append(('속표지', 0, 0))

P = newpage()
L = vlines(3)
P['paras'] = ['>> ' + ('**%s**' % text_of(r[3]).strip() if 'Bold' in r[3][0]['font'] else text_of(r[3]).strip()) for r in L]
chapters.append(('원서 속표지', 1, 0))

P = newpage()
L = [r for r in vlines(4) if 'Dotum' not in r[3][0]['font']]   # '일러두기' 제목 줄은 장 제목으로
items = []
for r in L:
    t = text_of(r[3])
    if t.startswith('*'): items.append(t)
    else: items[-1] += t
P['paras'] = [re.sub(r'\s+$', '', x) for x in items]
chapters.append(('일러두기', 2, 0))

P = newpage()
toc_lines = []
for n in (5, 6):
    for r in vlines(n):
        t = re.sub(r'\s+', ' ', text_of(r[3], refs=False)).strip()
        if t in ('차 례',): continue
        f = [s for s in r[3] if s['text'].strip()][0]
        if f['font'].startswith('GyeonggiBatang') and f['size'] > 10.5: toc_lines.append('**' + t + '**')
        elif r[1] - (48.2 if n % 2 else 62.4) > 8: toc_lines.append('- ' + t)
        else: toc_lines.append(t)
# 장 묶음 사이 간격
tl = []
for k, t in enumerate(toc_lines):
    if k > 1 and t.startswith('**') or t.startswith('저자 소개'): tl.append('~')
    tl.append(t)
P['paras'] = ['%% ' + '\n'.join(tl)]
chapters.append(('차례', 3, 0))

P = newpage()
L = vlines(7)
P['paras'] = [':: ' + text_of(r[3]).strip() for r in L]
chapters.append(('예경문', 4, 0))

# ---------- 본문 ----------
def add(P, k, t):
    P['paras'].append(t); P.setdefault('kinds', {})[len(P['paras']) - 1] = k
    return len(P['paras']) - 1


prev_last = None  # (kind, x1 of last line, right margin)
for n in range(8, 147):
    L = vlines(n)
    lab = ''
    body = []
    for r in L:
        if r[0] > 470:
            nums = [s['text'].strip() for s in r[3] if s['text'].strip().isdigit()]
            if nums: lab = str(int(nums[-1]))
            continue
        body.append(r)
    if n == 146 and not lab: lab = '145'   # 저자 소개 쪽: 번호는 인쇄되지 않았지만 차례에 145쪽
    P = newpage(lab + '쪽' if lab else '')
    pi = len(PAGES) - 1
    Lm = 62.4 if n % 2 == 0 else 48.2
    R = Lm + 249.4
    cur = None; cur_kind = None; prev = None
    for r in body:
        k = kind(r)
        if n == 146:  # 저자 소개 쪽: 작은 글자가 본문
            t0 = text_of(r[3]).strip()
            if t0 == '저자 소개': chapters.append(('저자 소개', pi, 0)); prev = r; continue
            if t0 == '저서': add(P, 'H2', '## 저서'); cur = None; prev = r; continue
            k = 'A'
        if k == 'F':
            t = text_of(r[3], refs=False)
            m = re.match(r'(\d+)\s+', t)
            if r[3][0]['font'] == 'KoPubBatangPM' and m:
                last_fn = m.group(1); FN[last_fn] = t[m.end():]; P['fns'].append(last_fn)
            else:
                if prev is None or kind(prev) != 'F': log['다음 쪽으로 넘어간 각주'] += 1
                FN[last_fn] += t
            prev = r; continue
        t = text_of(r[3])
        if k == 'H1':
            title = re.sub(r'\s+', ' ', t).strip()
            j = add(P, k, '## ' + title); chapters.append((title, pi, j)); cur = None
        elif k == 'H2':
            title = re.sub(r'\s+', ' ', t).strip()
            j = add(P, k, '## ' + title); subs.append((title, pi, j)); cur = None
        elif k == 'H3':
            add(P, k, '**' + t.strip() + '**'); cur = None
        elif k == 'A':
            if cur is not None and prev is not None and r[0] - prev[0] < 16 and prev[2] > R - 12:
                P['paras'][cur] += t
            else:
                cur = add(P, k, t)
        else:
            gap = r[0] - prev[0] if prev is not None else None
            # 인용문 안의 로마자(기울임)만 있는 줄은 인용문의 한 줄
            if k == 'B' and cur_kind == 'Q' and prev is not None and abs(r[1] - prev[1]) < 2 \
                    and all(is_ital(s) or not s['text'].strip() or is_ref(s) for s in r[3]):
                k = 'Q'
            indent = (r[1] - Lm > 8) if k == 'B' else False
            if cur is not None and cur_kind == k:
                lead = 22 if k == 'B' else 20.5
                if (not indent) and gap is not None and gap < lead + 4:
                    # 앞 줄이 끝까지 찼으면 이어 붙이고, 짧으면 인쇄본처럼 줄을 바꿈(게송·문답)
                    sep = '' if prev[2] > R - (20 if k == 'B' else 14) else '\n'
                    if sep: log['문단 안 줄 바꿈'] += 1
                    if cur == 'prev': PAGES[-2]['paras'][-1] = PAGES[-2]['paras'][-1].rstrip(' ') + sep + t if sep else PAGES[-2]['paras'][-1] + t
                    else: P['paras'][cur] = (P['paras'][cur].rstrip(' ') + sep + t) if sep else P['paras'][cur] + t
                    prev = r; continue
            elif cur is None and prev is None and prev_last and prev_last[0] == k and not indent \
                    and PAGES[-2]['paras'] and prev_last[1] > prev_last[2] - 14:
                PAGES[-2]['paras'][-1] += t; log['쪽을 넘어 이어 붙인 문단'] += 1
                cur = 'prev'; cur_kind = k; prev = r; continue
            cur = add(P, k, t); cur_kind = k
        prev = r
    content = [r for r in body if kind(r) != 'F']
    prev_last = (kind(content[-1]) if n != 146 else 'A', content[-1][2], R) if content else None

# ---------- 판권지 (PDF 155) ----------
P = newpage(); pi = len(PAGES) - 1
chapters.append(('판권지', pi, 0))
rows = vlines(155)
for r in rows:
    t = re.sub(r'[ \t]+', ' ', text_of(r[3])).strip()
    if not t: continue
    big = max(r[3], key=lambda s: s['size'])
    if big['size'] > 12: t = '**' + t + '**'
    add(P, 'C', t)

# ---------- 부록 ----------
P = newpage(); pi = len(PAGES) - 1
chapters.append(('부록 : 부처님 당시 지도', pi, 0))
img = spread(156, fitz.Rect(34, 30, 345.8, 368), 157, fitz.Rect(0, 30, 293, 495), f'{BK}-map.jpg'); images.append(img)
P['paras'].append('![#부처님 당시 지도](%s)' % img)
cap = []
for r in vlines(156):
    if r[0] > 400: cap.append(r)
para = ''; out = []
for k, r in enumerate(cap):
    t = text_of(r[3])
    if k and r[3][0]['size'] < 8.95 and cap[k - 1][3][0]['size'] >= 8.95: out.append(para); para = ''
    para += t
out.append(para)
for t in out: add(P, 'C', t.rstrip())

P = newpage(); pi = len(PAGES) - 1
chapters.append(('부록 : 부처님 가계도', pi, 0))
img = spread(158, fitz.Rect(34, 30, 325.9, 384), 159, fitz.Rect(0, 30, 320, 384), f'{BK}-family.jpg'); images.append(img)
P['paras'].append('![#부처님 가계도](%s)' % img)
for n in (158, 159):
    t = ''.join(text_of(r[3]) for r in vlines(n) if r[0] > 410)
    add(P, 'C', t.rstrip())

# ---------- 마무리 ----------
for P in PAGES:
    kinds = P.get('kinds', {})
    for j, p in enumerate(P['paras']):
        p = re.sub(r'[  ]+$', '', p).replace('­', '')
        if kinds.get(j) == 'Q': p = '++ **' + p.strip() + '**'
        P['paras'][j] = p
    for f in P['fns']:
        P['paras'].append(f'[^{f}]: ' + re.sub(r'[  ]+$', '', FN[f]).strip())

toc = []
for t, pi, j in chapters:
    toc.append(dict(title=t, page=pi + 1, sub=False, **({'at': t[:20]} if j > 0 else {})))
for t, pi, j in subs:
    if t == '저서': continue
    toc.append(dict(title=t, page=pi + 1, sub=True, **({'at': t[:20]} if j > 0 else {})))
toc.sort(key=lambda x: (x['page'], 0 if not x['sub'] else 1))
# 같은 쪽에서는 문단 순서대로
order = {}
for t, pi, j in chapters + subs: order[(t, pi + 1)] = j
toc.sort(key=lambda x: (x['page'], order.get((x['title'], x['page']), 0)))

body = ''
for P in PAGES:
    body += (f"=== {P['lab']} ===" if P['lab'] else '=== ===') + '\n\n' + '\n\n'.join(P['paras']) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print(dict(log), '쪽', len(PAGES), '장', len(chapters), '소제목', len(subs), '각주', len(FN), '→', out)
