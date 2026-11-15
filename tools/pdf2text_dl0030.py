"""『붓다의 일생』(DL-0030, 빠알리 경전에 의거하여 엮은, 비구 냐아나몰리 편역 | 부희령 옮김, 고요한소리 초판 3쇄 2024) PDF → content/texts/DL-0030.json
  python3 tools/pdf2text_dl0030.py 책.pdf

PDF 718쪽 (InDesign, A5 보다 작은 419.5×595.3pt). PDF 쪽 = 인쇄 쪽 + 1 (PDF 1쪽은 앞표지).
쪽 이름은 쪽 아래 인쇄된 번호. 번호가 인쇄되지 않은 쪽(지도·장 표지·12장 차례 쪽·뒤쪽 표지)도 앞뒤 번호 사이가 비므로 번호를 넣음.
앞쪽: PDF 2 반표제, 3 원서 속표지, 4 속표지, 5 일러두기, 6 예경문, 7~8 차례 — 쪽 번호 없음.
본문: 9 편집자 서문(8쪽) ~ 696(695쪽). 장마다 앞에 장 표지(모든 장 이름 목록, 지금 장만 진하게)가 있는데 그 글은 다음 쪽 장 제목과 겹치므로 넣지 않음(빈 쪽).
뒤쪽: 698 표지, 699~705 경전 출처 목록(표), 707~713 찾아보기, 714 주요 연표(표), 715 저자 소개, 716 저자 저서목록, 717 판권지. 718 뒤표지는 넣지 않음.

글 모양:
- 본문 KoPub바탕 Light 10.9 — 첫 줄 들여쓰기(+11.4pt)·말하는 이 표시·앞 줄이 짧으면 새 문단, 쪽이 넘어가도 이어 붙임.
- 말하는 이 표시(해설자 1·첫 번째 목소리·낭송자 …, 경기바탕 금색) → §§…§§ (화면에서 금색 굵은 글씨).
- 게송·인용 시(경기바탕 Bold 10.3·10.4, 들여 씀) → `++ **…**` 줄마다, 연 사이가 벌어지면 새 문단.
- 경전 출처(오른쪽 맞춤 작은 글씨, 예 '《중부》 26') → `>> `.
- 장 제목(경기바탕 13.9) → 장, 앞쪽 제목(KoPub바탕 PB 12, 금색) → 장, 경 제목(KoPub돋움 PB 10.9)·12장 소제목(KoPub바탕 PB 11.9) → `## `, 12장 팔정도 항목(KoPub바탕 PM 10.9 '1) 바른 견해') → `**…**`.
- 로마자 기울임(Times Italic) → °°…°°. 각주 번호(위첨자, KoPub돋움 6.9) → [^n], 쪽 아래 각주 → [^n]: …(다음 쪽으로 넘어간 각주는 이어 붙임).
  각주 번호는 머리말(1·2)과 본문(1~)에서 따로 셈 — 읽기 화면은 같은 쪽의 각주를 먼저 찾음.
- 311쪽 각주 112 의 3계 26천 표는 그림으로.
글자는 PDF 그대로 (줄 사이 빈칸 없음 — PDF 글자층 그대로 이어 붙임).
"""
import sys, re, json, os, collections
import fitz

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK, ED = 'DL-0030', '초판 3쇄'
src = fitz.open(pdf)
log = collections.Counter()
UP = os.path.join(REPO, 'public/uploads')
GOLD = 0x947139


def Lm(n): return 87.8 if n % 2 == 0 else 56.7


def clean(t): return re.sub('[\x07\x01\r\n]', '', t).replace('\t', ' ')


def is_ref(s): return s['font'].startswith('KoPubDotum') and s['size'] < 7.5 and s['text'].strip().isdigit()
def is_ital(s): return 'Italic' in s['font'] and s['text'].strip() != ''
def is_spk(s): return s['font'].startswith('GyeonggiBatangB') and 8.5 < s['size'] < 9.5 and s['color'] == GOLD


def vlines(n, split_x=None):
    """한 쪽의 줄(같은 높이 조각은 한 줄로): [y아래, x0, x1, spans, y가운데]"""
    L = []; S = []
    for b in src[n - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text']]
            if not clean(''.join(s['text'] for s in sp)).strip(): continue
            x0, y0, x1, y1 = l['bbox']
            r = [y1, x0, x1, sp, (y0 + y1) / 2]
            (S if all(is_ref(s) or not clean(s['text']).strip() for s in sp) else L).append(r)
    L.sort(key=lambda r: r[4])
    out = []
    for r in L:
        same = [q for q in out[-3:] if abs(q[4] - r[4]) < 3 and (split_x is None or (q[1] < split_x) == (r[1] < split_x))]
        if same:
            o = same[-1]; o[3] = o[3] + r[3]; o[1] = min(o[1], r[1]); o[2] = max(o[2], r[2]); o[0] = max(o[0], r[0])
        else: out.append(r)
    for r in S:
        if not out: out.append(r); continue
        o = min(out, key=lambda q: abs(q[4] - r[4]))
        o[3] = o[3] + r[3]; o[2] = max(o[2], r[2])
    for o in out: o[3].sort(key=lambda s: s['bbox'][0])
    return out


def text_of(spans, refs=True, spk=True):
    o = ''; it = ''
    def flush():
        nonlocal o, it
        if it:
            a = it[:len(it) - len(it.lstrip())]; z = it[len(it.rstrip()):]
            o += a + '°°' + it.strip() + '°°' + z; it = ''
    k = 0
    while k < len(spans):
        s = spans[k]; t = clean(s['text'])
        if refs and is_ref(s):
            flush(); o += f'[^{t.strip()}]'; log['각주 번호'] += 1
        elif spk and is_spk(s) and t.strip():
            flush(); lab = t
            while k + 1 < len(spans) and is_spk(spans[k + 1]): k += 1; lab += clean(spans[k]['text'])
            o += '§§' + lab.strip() + '§§' + (' ' if lab != lab.rstrip() else '')
        elif is_ital(s): it += t
        else:
            if it and not t.strip(): it += t; k += 1; continue
            flush(); o += t
        k += 1
    flush()
    return o


def main_span(r):
    sp = [s for s in r[3] if clean(s['text']).strip() and not is_ref(s) and not is_spk(s)]
    return max(sp, key=lambda s: len(clean(s['text']).strip())) if sp else None


def kind(r, n):
    sp = [s for s in r[3] if clean(s['text']).strip() and not is_ref(s)]
    if not sp: return 'B'
    if all(is_spk(s) for s in sp): return 'SPK'
    m = main_span(r)
    f, z, c = m['font'], round(m['size'], 1), m['color']
    if f.startswith('GyeonggiBatangB') and z >= 13: return 'H1'
    if f == 'KoPubBatangPB' and 11.5 < z < 12.5 and c == GOLD: return 'FT'
    if f == 'KoPubDotumPB' and 10.5 < z < 11.5 and c == 0x404041: return 'H2'
    if f == 'KoPubBatangPB' and 11.5 < z < 12.5: return 'H2'
    if f == 'KoPubBatangPM' and 10.5 < z < 11.5: return 'H3'
    if f.startswith('GyeonggiBatangB') and 10 < z < 10.6 and c == 0x404041: return 'Q'
    mx = max(s['size'] for s in sp)
    if mx < 8.6: return 'F'
    if mx < 9.5 and r[1] > Lm(n) + 60 and r[2] > Lm(n) + 260: return 'SRC'
    return 'B'


def render(n, rect, name, dpi=300):
    pix = src[n - 1].get_pixmap(dpi=dpi, clip=rect)
    path = os.path.join(UP, name); pix.save(path); return '/uploads/' + name


PAGES = []
images = []
chapters = []   # (title, page index, para index)
subs = []
FN = {}         # (구역, 번호) → 글
last_fn = None


def newpage(lab=''):
    P = {'lab': lab, 'paras': [], 'fns': [], 'kinds': {}}; PAGES.append(P); return P


def add(P, k, t):
    P['paras'].append(t); P['kinds'][len(P['paras']) - 1] = k; return len(P['paras']) - 1


def label(n):
    for r in vlines(n):
        if r[0] > 540:
            nums = re.findall(r'\d+', ''.join(s['text'] for s in r[3]))
            if nums: return nums[0] if n % 2 else nums[-1]   # 짝수 PDF 쪽 아래: '1. 탄생 그리고 어린 시절  29' — 장 번호 뒤의 쪽 번호
    return str(n - 1) if 9 <= n <= 716 else ''


# ---------- 앞쪽 ----------
P = newpage()
wheel = render(4, fitz.Rect(195, 60, 225, 95), f'{BK}-wheel.png', 400); images.append(wheel)
chapters.append(('속표지', 0, 0))
P['paras'] = [':: ' + text_of(r[3]).strip() for r in vlines(2)]
P = newpage()
L = vlines(4)
P['paras'] = ['![#법륜](%s)' % wheel, ':: ' + text_of(L[0][3]).strip(), '^^ ' + re.sub(r'\s+', ' ', text_of(L[1][3])).strip(), ':: ' + text_of(L[2][3]).strip()]

P = newpage(); chapters.append(('원서 속표지', len(PAGES) - 1, 0))
for r in vlines(3):
    t = re.sub(r'\s+', ' ', text_of(r[3])).strip()
    if 'Bol' in r[3][0]['font']: t = '**' + t + '**'
    P['paras'].append(':: ' + t)
# 'THE LIFE' + 'OF THE BUDDHA' 는 한 제목
P['paras'][0:2] = [':: **THE LIFE OF THE BUDDHA**'] if P['paras'][0].startswith(':: **THE LIFE') else P['paras'][0:2]

P = newpage(); chapters.append(('일러두기', len(PAGES) - 1, 0))
items = []
for r in vlines(5):
    t = text_of(r[3])
    if t.strip() == '일러두기': continue
    if t.startswith('*'): items.append(t)
    else: items[-1] += t
P['paras'] = [x.rstrip() for x in items]

P = newpage(); chapters.append(('예경문', len(PAGES) - 1, 0))
L = vlines(6)
grp = []; cur = []
for k, r in enumerate(L):
    if cur and r[0] - L[k - 1][0] > 22: grp.append(cur); cur = []
    cur.append(r)
grp.append(cur)
for g in grp:
    rows = []
    for r in g:
        t = text_of(r[3]).rstrip()
        if r[3][0]['font'].startswith('TimesNewRomanPS-Bold'): t = '**' + t + '**'
        rows.append(t)
    if g[0][1] > 150: P['paras'].append('>> ' + '\n'.join(rows))
    else: P['paras'].append('\n'.join(rows))
# 'Namo Tassa …' 두 줄은 굵게 한 줄씩
P['paras'] = [re.sub(r'\*\*\n\*\*', '\n', x) for x in P['paras']]

P = newpage(); chapters.append(('차례', len(PAGES) - 1, 0))
toc_lines = []
for n in (7, 8):
    L = [r for r in vlines(n) if text_of(r[3]).strip() != '차 례']
    nums = [r for r in L if re.fullmatch(r'\s*\d{3}\s*', text_of(r[3]))]
    for r in L:
        if r in nums: continue
        t = text_of(r[3], refs=False)
        if '│' in t:   # 앞뒤쪽 항목: '편집자 서문 008 │ 3판에 붙여 010 │ …'
            for part in t.split('│'):
                m = re.match(r'\s*(.*?)\s+(\d{3})\s*$', part)
                if m: toc_lines.append((r[4], m.group(1) + ' | ' + m.group(2)))
        else:   # 장 제목과 오른쪽 쪽 번호가 한 줄로 합쳐짐
            m = re.match(r'\s*(.*?)\s*(\d{3})\s*$', t)
            toc_lines.append((r[4] + 1000 * (n - 7), '**' + re.sub(r'\s+', ' ', m.group(1)).strip() + '** | ' + m.group(2)))
fr = [t for y, t in toc_lines if not t.startswith('**')]
ch = [t for y, t in sorted(toc_lines) if t.startswith('**')]
P['paras'] = ['%% ' + '\n'.join(fr[:5] + ['~'] + ch + ['~'] + fr[5:])]

# ---------- 본문 (PDF 9 ~ 696) ----------
DIVIDERS = {27, 45, 83, 119, 161, 194, 222, 236, 258, 322, 381, 425, 525, 556, 581, 668, 697, 698}
sect = 'pre'
prev_last = None   # (kind, x1, R) of last content line on previous page
pending_q = False
for n in range(9, 697):
    lab = label(n)
    P = newpage(lab + '쪽' if lab else '')
    pi = len(PAGES) - 1
    if n in DIVIDERS: prev_last = None; continue
    if n in (23, 24):   # 인도의 중부, 동부 지도
        if n == 23: chapters.append(('인도의 중부, 동부 지도', pi, 0))
        img = render(n, fitz.Rect(Lm(n) - 2, 75, Lm(n) + 277, 512), f'{BK}-map{n - 22}.jpg', 220); images.append(img)
        add(P, 'IMG', '![#인도의 중부, 동부 지도 %d](%s)' % (n - 22, img)); prev_last = None; continue
    L = [r for r in vlines(n) if r[0] < 540]
    lm = Lm(n); R = lm + 275.2
    cur = None; cur_kind = None; prev = None
    # 각주 구역: 각주 번호(KoPub돋움 PB 7.9)로 시작하는 첫 줄부터 아래는 모두 각주 (각주 속 ':' 등이 큰 글씨여도)
    fstarts = [r[4] for r in L if r[3] and r[3][0]['font'].startswith('KoPubDotum') and 7.5 < r[3][0]['size'] < 8.2
               and clean(r[3][0]['text']).strip().isdigit() and r[1] < lm + 3 and r[4] > 150]
    fy = min(fstarts) if fstarts else 9999
    for r in L:
        k = kind(r, n)
        if r[4] >= fy - 1: k = 'F'
        if n in (25, 26):   # 목소리들: 이름표와 설명
            t = text_of(r[3]).strip()
            if k == 'FT': chapters.append((t, pi, len(P['paras']))); prev = r; continue
            if all(s['color'] == 0xffffff for s in r[3] if clean(s['text']).strip()):
                add(P, 'SPKL', '§§' + t + '§§'); cur = None; prev = r; continue
            if cur is not None and prev is not None and r[0] - prev[0] < 22: P['paras'][cur] += text_of(r[3])
            else: cur = add(P, 'B', text_of(r[3]))
            prev = r; continue
        if n == 311 and 197 < r[4] < 500: continue   # 각주 112 의 3계 26천 표 (그림으로)
        if n == 426 and r[4] > 160:   # 12장 차례 쪽
            t = re.sub(r'\s+', ' ', text_of(r[3], refs=False)).strip()
            if t == '차 례': add(P, 'TOCH', '**차 례**'); prev = r; continue
            m = re.match(r'(.*?) ?(\d{3})$', t)
            if r[1] - lm > 8: line = '- ' + t      # '1) 바른 견해 ° 462' 인쇄된 그대로
            else: line = m.group(1) + ' | ' + m.group(2)
            if P['paras'] and P['paras'][-1].startswith('%% '): P['paras'][-1] += '\n' + line
            else: add(P, 'TOC', '%% ' + line)
            prev = r; continue
        if k == 'F':
            t = text_of(r[3], refs=False, spk=False)
            m = re.match(r'\s*(\d+)\s+', t)
            if m and r[3][0]['font'].startswith('KoPubDotum') and r[1] < lm + 3:
                last_fn = (sect, m.group(1)); FN[last_fn] = t[m.end():]; P['fns'].append(last_fn)
            else:
                if last_fn is None: log['각주 아닌 작은 글'] += 1; add(P, 'B', t); continue
                if prev is None or kind(prev, n) != 'F': log['다음 쪽으로 넘어간 각주'] += 1
                FN[last_fn] += t
            prev = r; continue
        t = text_of(r[3])
        if k in ('H1', 'FT'):
            title = re.sub(r'\s+', ' ', t).strip()
            if n == 427 and title == '12. 교리':   # 12장 차례 쪽 다음 쪽에 장 제목이 한 번 더 인쇄됨 → 가운데 줄로 남김(글자 그대로)
                add(P, 'C', ':: ' + title); cur = None; prev = r; continue
            if title in ('머리말',): sect = 'pre'
            elif re.match(r'1\. ', title): sect = 'body'
            j = add(P, k, '## ' + title); chapters.append((title, pi, j)); cur = None; prev = r; cur_kind = k
            continue
        if k == 'H2':
            title = re.sub(r'\s+', ' ', t).strip()
            j = add(P, k, '## ' + title); subs.append((re.sub(r'\[\^\d+\]', '', title), pi, j)); cur = None; prev = r; cur_kind = k; continue
        if k == 'H3':
            add(P, k, '**' + t.strip() + '**'); cur = None; prev = r; cur_kind = k; continue
        if k == 'SPK':
            add(P, k, t.strip()); cur = None; prev = r; cur_kind = k; continue
        if k == 'SRC':
            add(P, k, '>> ' + t.strip()); cur = None; prev = r; cur_kind = k; continue
        # 본문(B)·게송(Q)
        gap = r[0] - prev[0] if prev is not None else None
        indent = r[1] - lm > 8
        spk_start = t.startswith('§§')
        if cur == 'prev' and cur_kind == 'B' and k == 'B' and not indent and not spk_start and gap is not None and gap < 25 and prev[2] > R - 16:
            PAGES[-2]['paras'][-1] += t; prev = r; continue
        if cur == 'prevq' and k == 'Q' and gap is not None and gap < 26:
            PAGES[-2]['paras'][-1] = PAGES[-2]['paras'][-1].rstrip(' ') + '\n' + t; prev = r; continue
        if cur in ('prev', 'prevq'): cur = None
        if cur is not None and cur_kind == k and not spk_start:
            if k == 'Q':
                if gap is not None and gap < 26:
                    P['paras'][cur] = P['paras'][cur].rstrip(' ') + '\n' + t; prev = r; continue
            elif (not indent) and gap is not None and gap < 25 and prev[2] > R - 16:
                P['paras'][cur] += t; prev = r; continue
            elif (not indent) and gap is not None and gap < 25:
                log['짧은 줄 다음 새 문단'] += 1
        elif cur is None and prev is None and prev_last and prev_last[0] == k and not indent and not spk_start \
                and k == 'B' and PAGES[-2]['paras'] and prev_last[1] > prev_last[2] - 16:
            PAGES[-2]['paras'][-1] += t; log['쪽을 넘어 이어 붙인 문단'] += 1
            cur = 'prev'; cur_kind = k; prev = r; continue
        elif cur is None and prev is None and prev_last and prev_last[0] == 'Q' and k == 'Q' and PAGES[-2]['paras']:
            # 게송이 쪽을 넘어감: 앞 쪽 마지막 게송 문단에 이어 줄 바꿈
            PAGES[-2]['paras'][-1] = PAGES[-2]['paras'][-1].rstrip(' ') + '\n' + t; log['쪽을 넘어 이어진 게송'] += 1
            cur = 'prevq'; cur_kind = k; prev = r; continue
        cur = add(P, k, t); cur_kind = k; prev = r
    content = [r for r in L if kind(r, n) not in ('F',)]
    prev_last = (kind(content[-1], n), content[-1][2], R) if content else None
    if n == 311:   # 각주 112 의 표
        img = render(311, fitz.Rect(Lm(311) - 2, 198, Lm(311) + 277, 500), f'{BK}-p310-table.png', 260); images.append(img)
        P['after_fn'] = {('body', '112'): ['![#3계 26천 표](%s)' % img]}

# ---------- 뒤쪽 ----------
P = newpage(label(697) + '쪽')
P = newpage(label(698) + '쪽')


def table_rows(n, cols):
    """표 쪽: 줄마다 칸 x 경계로 나눔"""
    rows = []
    for r in vlines(n):
        if r[0] > 540: continue
        cells = [''] * len(cols)
        for s in r[3]:
            t = clean(s['text'])
            if not t.strip(): continue
            x = s['bbox'][0] - Lm(n)
            c = max(i for i, b in enumerate(cols) if x >= b - 2)
            cells[c] += t
        rows.append((r, [c.strip() for c in cells]))
    return rows


P = PAGES[-1]   # 698 은 뒤쪽 표지(빈 쪽)
first = True
for n in range(699, 707):
    P = newpage(label(n) + '쪽'); pi = len(PAGES) - 1
    if first: chapters.append(('경전 출처 목록', pi, 0)); first = False
    rows = table_rows(n, [0, 50, 67, 104, 232])
    tab = []
    for r, c in rows:
        if r[4] < 70: continue     # 제목 '경전 출처 목록'
        if any(s['color'] == 0xffffff for s in r[3]):
            tab.append('| ' + ' | '.join('**' + x + '**' if x else '' for x in c) + ' |'); continue
        if any(s['color'] == GOLD for s in r[3]) and not c[4]:
            tab.append('| **' + ''.join(c).strip() + '** |  |  |  |  |'); continue
        tab.append('| ' + ' | '.join(c) + ' |')
    # 첫 쪽은 머리 줄 + 구분 줄, 이어지는 쪽은 구분 줄로 시작(머리 줄 없음 — app.js tableHtml)
    sep = '|' + '---|' * 5
    if n == 699: tab.insert(1, sep)
    else: tab.insert(0, sep)
    add(P, 'T', '\n'.join(tab))


first = True
for n in range(707, 714):
    P = newpage(label(n) + '쪽'); pi = len(PAGES) - 1
    if first: chapters.append(('찾아보기', pi, 0)); first = False
    L = [r for r in vlines(n, split_x=Lm(n) + 140) if r[0] < 540 and r[4] > 55 and text_of(r[3]).strip() != '찾아보기']
    # 두 단: 왼쪽 단 → 오른쪽 단
    mid = Lm(n) + 140
    cols = [[r for r in L if r[1] < mid], [r for r in L if r[1] >= mid]]
    for col in cols:
        base = min((r[1] for r in col), default=0)
        cur = None
        for r in col:
            t = text_of(r[3], refs=False, spk=False)
            if any(s['size'] > 10 for s in r[3]):
                add(P, 'H2', '## ' + t.strip()); subs.append((t.strip(), pi, len(P['paras']) - 1)); cur = None; continue
            if r[1] - base > 4 and cur is not None:   # 이어지는 줄(들여 씀)
                P['paras'][cur] = P['paras'][cur].rstrip(' ') + ('' if P['paras'][cur].endswith(',') else ' ') + t.strip() if False else P['paras'][cur] + t
                continue
            if cur is None or P['kinds'].get(cur) != 'IDX': cur = add(P, 'IDX', t)
            else: P['paras'][cur] += '\n' + t
            if r[1] - base <= 4: pass
    # 줄 끝 빈칸 정리
    P['paras'] = [re.sub(r'[  ]+(?=\n|$)', '', p) for p in P['paras']]

n = 714
P = newpage(label(n) + '쪽'); pi = len(PAGES) - 1
chapters.append(('주요 연표', pi, 0))
L = [r for r in vlines(n) if r[0] < 540 and r[4] > 75]
intro = [r for r in L if r[4] < 140]
add(P, 'B', ''.join(text_of(r[3]) for r in intro).strip())
tab = []
for r in L:
    if r in intro or r[4] > 450: continue
    left = ''.join(clean(s['text']) for s in r[3] if s['bbox'][0] < 300).strip()
    right = ''.join(clean(s['text']) for s in r[3] if s['bbox'][0] >= 300).strip()
    if any(s['color'] == GOLD for s in r[3]): tab.append(f'| **{left}** | **{right}** |')
    else: tab.append(f'| {left} | {right} |')
add(P, 'T', '\n'.join(tab))
notes = [r for r in L if r[4] > 450]
add(P, 'B', ''.join(text_of(r[3]) for r in notes).strip())

n = 715
P = newpage(label(n) + '쪽'); pi = len(PAGES) - 1
chapters.append(('저자 소개', pi, 0))
L = [r for r in vlines(n) if r[0] < 540 and r[4] > 75]
add(P, 'H3', '**' + re.sub(r'\s+', ' ', text_of(L[0][3])).strip() + '**')
cur = None; prev = None
for r in L[1:]:
    t = text_of(r[3])
    if cur is not None and r[1] - Lm(n) < 8 and r[0] - prev[0] < 24: P['paras'][cur] += t
    else: cur = add(P, 'B', t)
    prev = r

n = 716
P = newpage(label(n) + '쪽'); pi = len(PAGES) - 1
chapters.append(('저자 저서목록', pi, 0))
L = [r for r in vlines(n) if r[0] < 540 and r[4] > 75]
cur = None
for r in L:
    t = text_of(r[3])
    if any(s['color'] == GOLD for s in r[3]): add(P, 'H3', '**' + t.strip() + '**'); cur = None; continue
    if r[1] - 87.9 > 8 and cur is not None: P['paras'][cur] += t
    else: cur = add(P, 'B', t)

n = 717
P = newpage(); pi = len(PAGES) - 1
chapters.append(('판권지', pi, 0))
L = vlines(n)
eng = [r for r in L if r[4] < 110]
add(P, 'C', '\n'.join(text_of(r[3]).rstrip() for r in eng))
grp = []
for r in L:
    if r in eng: continue
    t = re.sub(r'[  ]{2,}', ' ', text_of(r[3])).strip()
    if not t: continue
    grp.append((r[4], r[1], t))
lines = []
for y, x, t in sorted(grp):
    if lines and abs(lines[-1][0] - y) < 3: lines[-1][1] += ' ' + t
    else: lines.append([y, t])
add(P, 'C', '\n'.join(t for y, t in lines))

# ---------- 마무리 ----------
for P in PAGES:
    kinds = P.get('kinds', {})
    for j, p in enumerate(P['paras']):
        p = re.sub(r'[  ]+$', '', p).replace('­', '')
        p = re.sub(r'[  ]+\n', '\n', p)
        p = re.sub(r'°°(\s*)°°', r'\1', p)   # 줄이 바뀌며 나뉜 기울임 조각을 하나로
        if kinds.get(j) == 'Q': p = '++ ' + '\n'.join('**' + x.strip() + '**' for x in p.split('\n'))
        P['paras'][j] = p
    for f in P['fns']:
        ft = re.sub(r'°°(\s*)°°', r'\1', re.sub(r'[  ]+$', '', FN[f]).strip()); tail = ''
        if f in P.get('after_fn', {}) and '《중부》 41경' in ft:   # 인쇄본 순서: 각주 머리 → 표 → 출처 줄
            k = ft.index('《중부》 41경'); ft, tail = ft[:k].rstrip(), ft[k:]
        P['paras'].append(f'[^{f[1]}]: ' + ft)
        for extra in P.get('after_fn', {}).get(f, []): P['paras'].append(extra)
        if tail: P['paras'].append(tail)

toc = []
order = {}
for t, pi, j in chapters: toc.append(dict(title=t, page=pi + 1, sub=False)); order[(t, pi + 1)] = j
for t, pi, j in subs: toc.append(dict(title=t, page=pi + 1, sub=True)); order[(t, pi + 1)] = j
toc.sort(key=lambda x: (x['page'], order.get((x['title'], x['page']), 0)))
for x in toc:
    if order.get((x['title'], x['page']), 0) > 0: x['at'] = x['title'][:20]

body = ''
for P in PAGES:
    body += (f"=== {P['lab']} ===" if P['lab'] else '=== ===') + '\n\n' + '\n\n'.join(P['paras']) + '\n\n'
body = re.sub(r'\n{3,}', '\n\n', body).rstrip() + '\n'
# 줄 끝에서 나뉜 로마자 낱말: 108쪽 각주 37 'Dhammacak-' + 'kappavattana' 만 붙임 (102쪽 'saddhā-bhājanam' 은 낱말 경계라 책의 합성어 표기처럼 줄표 그대로)
body = body.replace('Dhammacak°°-°°kappavattana', 'Dhammacakkappavattana')
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': images, 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print(dict(log), '쪽', len(PAGES), '장', len(chapters), '소제목', len(subs), '각주', len(FN), '→', out)
