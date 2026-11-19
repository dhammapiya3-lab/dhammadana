"""『사아리뿟따 이야기』(DL-0037, 냐나뽀니까 스님 지음, 이준승 옮김, 고요한소리 법륜·열넷 2판 6쇄 2025) PDF → content/texts/DL-0037.json
  python3 tools/pdf2text_dl0037.py 책.pdf

『부처님, 그분』(DL-0029, 같은 고요한소리 법륜 조판) 도구를 바탕으로 함.
PDF 198쪽 (InDesign). PDF 쪽 = 인쇄 쪽 + 1 (PDF 1쪽은 앞표지). 쪽 이름은 쪽 아래 인쇄된 번호(들어가는 말 6쪽 ~ 덧붙이는 말 187쪽).
PDF 12쪽은 빈 쪽 — 번호는 인쇄되지 않았지만 10쪽과 12쪽 사이라 11쪽.
앞쪽: PDF 2 속표지(법륜 그림), 3 원서 속표지, 4 일러두기, 5~6 차례 (쪽 번호 없음).
뒤쪽: PDF 189~196 〈고요한소리〉 안내·도서 목록은 넣지 않음(DL-0029 와 같게), 197 판권지, 198 뒤표지(넣지 않음).
본문 KoPub바탕 Light 10.9 — 첫 줄 들여쓰기(+11.3pt)로 문단 시작, 쪽이 넘어가도 들여쓰지 않은 줄이면 이어 붙임.
인용·게송(경기바탕 Bold 9.9) → `++ **…**` (빈 줄 간격으로 문단 나눔, 짧은 줄은 인쇄본처럼 줄 바꿈).
장 제목 경기바탕 13.9 → 장, 소제목 KoPub돋움 Medium 11.4·KoPub돋움 PB 12.4(중부·증지부·상응부) → `## `(읽기 목차 소제목),
줄 전체가 KoPub바탕 PM 10.9 인 항목 제목(‘3경 〈법의 상속자 경…〉’·‘6. 〈라조와다 전생담〉(151)’·덧붙이는 말의 ‘…사리에 관한 기록’) → `## `(목차에는 넣지 않음).
각주 번호(KoPubBatangPM 6.4) → [^n], 쪽 아래 각주(번호 PM 7.9 + 8.4) → [^n]: …, 다음 쪽으로 넘어간 각주는 이어 붙임,
각주 안에서 짧은 줄(게송)·벌어진 줄 사이([역주])는 줄 바꿈.
로마자 기울임(일러두기: 로마자 빠알리어는 이탤릭체) → °°…°°.
글자는 PDF 그대로. 속표지의 'ㅣ'(구분 막대) → '|' (구분 막대 원칙).
"""
import sys, re, json, os, collections
import fitz

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK, ED = 'DL-0037', '2판 6쇄'
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
            # 높이는 글자 바탕선으로 — 한자 대체 글꼴(NotoSerifCJK)이 섞이면 줄 상자가 커져 줄 사이가 벌어진 것처럼 보임
            base = [s['origin'][1] for s in sp if s['text'].strip() and not is_ref(s)]
            if base:
                b0 = max(base, key=base.count) if len(set(base)) > 1 else base[0]
                y1 = b0 + 3; y0 = b0 - 9
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


def text_of(spans, refs=True, gap=False):
    """조각 → 글. 각주 번호 [^n], 기울임 °°…°°. gap: 떨어져 놓인 조각 사이에 빈칸(판권지 표)"""
    o = ''; it = ''; px = None
    def flush():
        nonlocal o, it
        if it:
            a = it[:len(it) - len(it.lstrip())]; z = it[len(it.rstrip()):]
            o += a + '°°' + it.strip() + '°°' + z; it = ''
    for s in spans:
        # 줄 끝의 강제 줄 바꿈 글자(\n)는 낱말 사이 자리라 빈칸으로 (‘요소들이⏎안으로는’)
        t = re.sub('[\x07\r]', '', s['text']).replace('\n', ' ').replace('\t', ' ')
        if gap and px is not None and s['bbox'][0] - px > 3 and not (o + it).endswith(' ') and not t.startswith(' '):
            t = ' ' + t
        px = s['bbox'][2]
        if refs and is_ref(s):
            flush(); o += f'[^{t.strip()}]'; log['각주 번호'] += 1
        elif is_ital(s): it += t
        else:
            if it and not t.strip(): it += t; continue
            flush(); o += t
    flush()
    return o


def kind(r):
    sp = [s for s in r[3] if s['text'].strip() and not is_ref(s)]
    if not sp: return 'B'
    big = max([s for s in sp if not s['font'].startswith('TimesNewRoman')] or sp, key=lambda s: len(s['text'].strip()))
    f, z = big['font'], round(big['size'], 1)
    if f.startswith('GyeonggiBatangB') and z >= 13: return 'H1'
    if (f == 'KoPubDotumMedium' and z >= 11) or (f == 'KoPubDotumPB' and z >= 12): return 'H2'
    if sp[0]['font'] == 'KoPubBatangPM' and sp[0]['size'] > 8.8 and \
            all(s['font'] == 'KoPubBatangPM' or is_ital(s) for s in sp): return 'H3'
    # 각주: 한글 글자가 8.6 보다 작은 줄 (각주 속 로마자 책 이름은 Times 9.0 이라 빼고 봄)
    kor = [s['size'] for s in sp if not s['font'].startswith('TimesNewRoman')]
    if max(kor or [s['size'] for s in sp]) < 8.6: return 'F'
    if any(s['font'].startswith('GyeonggiBatangB') for s in sp if len(s['text'].strip()) > 1): return 'Q'
    return 'B'


def render(n, rect, name, dpi=300):
    pix = src[n - 1].get_pixmap(dpi=dpi, clip=rect)
    path = os.path.join(UP, name); pix.save(path); return '/uploads/' + name


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
L = [r for r in vlines(2) if r[0] < 300]
P['paras'] = ['![#법륜](%s)' % wheel, ':: ' + text_of(L[0][3]).strip(), '^^ ' + text_of(L[1][3]).strip(),
              ':: ' + re.sub(r'\s*ㅣ\s*', ' | ', text_of(L[2][3]).strip())]
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
tl = []
for k, t in enumerate(toc_lines):
    if k > 0 and (t.startswith('**') or t.startswith('덧붙이는 말')): tl.append('~')
    tl.append(t)
P['paras'] = ['%% ' + '\n'.join(tl)]
chapters.append(('차례', 3, 0))

# ---------- 본문 ----------
def lastP():
    """지금 쪽 앞에서 글이 있는 가장 가까운 쪽 — 앞 쪽의 글이 모두 그 앞 쪽 문단에 이어 붙어 비었으면 그 앞 쪽(47쪽 → 46쪽)"""
    return next((Q for Q in reversed(PAGES[:-1]) if Q['paras']), None)


def add(P, k, t):
    P['paras'].append(t); P.setdefault('kinds', {})[len(P['paras']) - 1] = k
    return len(P['paras']) - 1


prev_last = None  # (kind, x1 of last line, right margin)
prev_fn_full = False
for n in range(7, 189):
    L = vlines(n)
    lab = ''
    body = []
    for r in L:
        if r[0] > 470:
            nums = [s['text'].strip() for s in r[3] if s['text'].strip().isdigit()]
            if nums: lab = str(int(nums[-1]))
            continue
        body.append(r)
    P = newpage(lab + '쪽' if lab else '')
    pi = len(PAGES) - 1
    Lm = 62.4 if n % 2 == 0 else 48.2
    R = Lm + 249.4
    cur = None; cur_kind = None; prev = None; fprev = None
    for r in body:
        k = kind(r)
        if k == 'F':
            t = text_of(r[3], refs=False)
            m = re.match(r'(\d+)\s+', t)
            if r[3][0]['font'] == 'KoPubBatangPM' and m:
                last_fn = m.group(1); FN[last_fn] = t[m.end():]; P['fns'].append(last_fn)
            else:
                if fprev is None:
                    log['다음 쪽으로 넘어간 각주'] += 1
                    sep = '' if prev_fn_full else '\n'
                else:
                    sep = '' if (fprev[2] > R - 14 and r[0] - fprev[0] < 14) else '\n'
                if sep: log['각주 안 줄 바꿈'] += 1
                FN[last_fn] = (FN[last_fn].rstrip(' ') + sep + t) if sep else FN[last_fn] + t
            fprev = r
            continue
        t = text_of(r[3])
        if k == 'H1':
            title = re.sub(r'\s+', ' ', t).strip()
            j = add(P, k, '## ' + title); chapters.append((title, pi, j)); cur = None
        elif k == 'H2':
            title = re.sub(r'\s+', ' ', t).strip()
            j = add(P, k, '## ' + title); subs.append((re.sub(r'°°', '', title), pi, j)); cur = None
        elif k == 'H3':
            if prev is not None and P.get('kinds', {}).get(len(P['paras']) - 1) == 'H3' and r[0] - prev[0] < 26 \
                    and kind(prev) == 'H3':
                P['paras'][-1] = P['paras'][-1] + re.sub(r'\s+', ' ', t).rstrip(); log['두 줄 항목 제목'] += 1
            else:
                add(P, k, '## ' + re.sub(r'\s+', ' ', t).lstrip()); log['항목 제목(PM)'] += 1
            cur = None
        else:
            gap = r[0] - prev[0] if prev is not None else None
            # 인용문 안의 로마자(기울임)만 있는 줄은 인용문의 한 줄
            if k == 'B' and cur_kind == 'Q' and prev is not None and abs(r[1] - prev[1]) < 2 \
                    and all(is_ital(s) or not s['text'].strip() or is_ref(s) for s in r[3]):
                k = 'Q'
            # 오른쪽에 맞춰 작게 찍힌 경전 출처 줄(‘《증지부》 2법집:12장:1경’) → >>
            if k == 'B' and r[1] - Lm > 60 and r[2] > R - 20 and \
                    max(s['size'] for s in r[3] if s['text'].strip()) < 9.5:
                add(P, 'C', '>> ' + t.strip()); log['경전 출처 줄'] += 1; cur = None; prev = r; continue
            indent = (r[1] - Lm > 8) if k == 'B' else False
            if cur is not None and cur_kind == k:
                lead = 22 if k == 'B' else 20.5
                if (not indent) and gap is not None and gap < lead + 4:
                    # 앞 줄이 끝까지 찼으면 이어 붙이고, 짧으면 인쇄본처럼 줄을 바꿈(게송·문답)
                    sep = '' if prev[2] > R - (20 if k == 'B' else 14) else '\n'
                    if sep: log['문단 안 줄 바꿈'] += 1
                    if cur == 'prev': LP = lastP(); LP['paras'][-1] = LP['paras'][-1].rstrip(' ') + sep + t if sep else LP['paras'][-1] + t
                    else: P['paras'][cur] = (P['paras'][cur].rstrip(' ') + sep + t) if sep else P['paras'][cur] + t
                    prev = r; continue
            elif cur is None and prev is None and prev_last and prev_last[0] == k and not indent \
                    and lastP() and prev_last[1] > prev_last[2] - 14:
                lastP()['paras'][-1] += t; log['쪽을 넘어 이어 붙인 문단'] += 1
                cur = 'prev'; cur_kind = k; prev = r; continue
            cur = add(P, k, t); cur_kind = k
        prev = r
    content = [r for r in body if kind(r) != 'F']
    prev_last = (kind(content[-1]), content[-1][2], R) if content else None
    fl = [r for r in body if kind(r) == 'F']
    prev_fn_full = bool(fl) and fl[-1][2] > R - 14

# 쪽 번호가 인쇄되지 않은 쪽: 앞뒤 쪽 번호 사이가 비면 그 번호
for k, P in enumerate(PAGES):
    if P['lab'] or k == 0: continue
    a = next((int(PAGES[j]['lab'][:-1]) for j in range(k - 1, -1, -1) if PAGES[j]['lab']), None)
    b = next((int(PAGES[j]['lab'][:-1]) for j in range(k + 1, len(PAGES)) if PAGES[j]['lab']), None)
    if a is not None and b is not None and b - a == 2:
        P['lab'] = f'{a + 1}쪽'; log['번호 없는 쪽에 번호'] += 1

# ---------- 판권지 (PDF 197) ----------
P = newpage(); pi = len(PAGES) - 1
chapters.append(('판권지', pi, 0))
rows = vlines(197)
prevy = None
for r in rows:
    t = re.sub(r'[ \t]+', ' ', text_of(r[3], gap=True)).strip()
    if not t: continue
    big = max(r[3], key=lambda s: s['size'])
    if big['size'] > 12: t = '**' + t + '**'
    if r[3][0]['font'].startswith('TimesNewRoman') and prevy is not None and r[0] - prevy < 14 and P['paras']:
        P['paras'][-1] += '\n' + t   # 영어 판권 글 넉 줄은 한 문단
    else:
        add(P, 'C', t)
    prevy = r[0]

# ---------- 마무리 ----------
for P in PAGES:
    kinds = P.get('kinds', {})
    for j, p in enumerate(P['paras']):
        p = re.sub(r'[  ]+$', '', p).replace('­', '')
        p = re.sub(r'[  ]+\n', '\n', p)
        if kinds.get(j) == 'Q': p = '++ **' + p.strip().replace('\n', '**\n**') + '**'
        P['paras'][j] = p
    for f in P['fns']:
        P['paras'].append(f'[^{f}]: ' + re.sub(r'[  ]+(\n|$)', r'\1', FN[f]).strip())

toc = []
for t, pi, j in chapters:
    toc.append(dict(title=t, page=pi + 1, sub=False, **({'at': t[:20]} if j > 0 else {})))
for t, pi, j in subs:
    # at 은 본문 글의 첫머리 — 읽기 화면은 기울임 표시(°°)를 빼지 않고 견주므로 °° 앞까지만 (‘증지부°°Aṅguttara…’ → ‘증지부’)
    at = re.sub(r'^## ', '', PAGES[pi]['paras'][j]).split('°°')[0][:20]
    toc.append(dict(title=t, page=pi + 1, sub=True, **({'at': at} if j > 0 else {})))
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
