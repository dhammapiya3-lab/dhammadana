"""『붓다의 깨달음 — 맛지마 니까야 선집』(DL-0022, 빅쿠 보디 대장로 편집, 빅쿠 케마짜라 옮김) PDF → content/texts/DL-0022.json
  python3 tools/pdf2text_dl0022.py 책.pdf

PDF 쪽 = 인쇄 쪽 (PDF 12쪽에 '012'). 1쪽 속표지, 2~5쪽 서문, 6~11쪽 차례, 12~312쪽 경 26개, 313쪽 빈 쪽, 314~315쪽 옮긴이의 말, 316쪽 판권지.
이 책의 짜임: 경마다 첫 쪽에 큰 번호(GoudyStd 36) + 제목(20pt) + 빠알리 제목(TimesNewRoman 13).
본문 SM신신명조 10.3pt, 절 번호는 굵은 Univers-Bold, 소제목은 SM견고딕 9.8pt.
각주 번호 '1)'(6pt 위첨자) → [^1], 쪽 아래 각주 '1. …'(6.8pt) → [^1]: …, 번호 없이 이어지는 줄은 앞 각주에 이어 붙임(다음 쪽으로 넘어간 것도).
쪽 번호(Univers-Light 8)·쪽 머리글(SM견고딕 6.8 + Helvetica 7)은 뺌.
글자는 PDF 그대로. 다만 ① 빠알리 제목의 옛 글꼴 표기 'l.'·'t.'·'n.' → ḷ·ṭ·ṇ (인쇄된 모양 그대로, 점이 글자 아래에 찍힘), 'a¯' → ā
② 판권지의 상자 선 '│' → '|' (구분 막대 원칙) ③ 숨은 제어 글자(\\x07) 빼기.
"""
import sys, re, json, fitz, collections

pdf = sys.argv[1]
BK, ED = 'DL-0022', '초판'
src = fitz.open(pdf)
N = src.page_count
INVIS = re.compile('[\x07\xad​]')
REF = re.compile(r'^\d{1,3}\)?$')
DOT = {'l': 'ḷ', 't': 'ṭ', 'n': 'ṇ', 'd': 'ḍ', 'm': 'ṃ', 'L': 'Ḷ', 'T': 'Ṭ', 'N': 'Ṇ', 'D': 'Ḍ'}
MAC = {'a': 'ā', 'i': 'ī', 'ı': 'ī', 'u': 'ū', 'A': 'Ā', 'I': 'Ī', 'U': 'Ū'}
fixes = collections.Counter()


def pali(t):
    o = t
    t = re.sub(r'([ltndmLTND])\.(?=[a-zA-Zāīū¯])', lambda m: DOT[m.group(1)], t)
    t = re.sub(r'([aiıuAIU])¯', lambda m: MAC[m.group(1)], t)
    t = re.sub(r'¯([aiıuAIU])', lambda m: MAC[m.group(1)], t)
    if t != o: fixes[(o.strip(), t.strip())] += 1
    return t


def macron(t):  # 각주 글꼴의 'a⁻vuso'·'a¯' → āvuso (인쇄된 모양 그대로)
    o = t
    t = re.sub(r'([aiıuAIU])[¯⁻]', lambda m: MAC[m.group(1)], t)
    t = re.sub(r'(?<![aiıuAIU])[¯⁻]([aiıuAIU])', lambda m: MAC[m.group(1)], t)
    if t != o: fixes[(o.strip(), t.strip())] += 1
    return t


def lines(n):
    """쪽의 줄: 같은 높이의 조각은 한 줄로(x 순서). (y, x0, x1, spans)"""
    p = src[n - 1]; L = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if INVIS.sub('', s['text']).strip() or s['text'] == ' ']
            if not any(INVIS.sub('', s['text']).strip() for s in sp): continue
            for s in sp:
                s['text'] = INVIS.sub('', s['text']); s['size'] = round(s['size'], 1)
                if s['font'].startswith('TimesNewRoman') and '@' not in s['text']: s['text'] = pali(s['text'])
                elif re.search('[¯⁻]', s['text']): s['text'] = macron(s['text'])
            x0, y0, x1, y1 = l['bbox']
            L.append([(y0 + y1) / 2, x0, x1, sp])
    L.sort(key=lambda r: (round(r[0]), r[1]))
    sup = [r for r in L if all(s['size'] <= 6.0 and s['flags'] & 1 for s in r[3] if s['text'].strip())]
    for r in sup:
        rest = [q for q in L if q is not r and q not in sup and abs(q[0] - r[0]) < 8]
        if not rest: continue
        q = min(rest, key=lambda q: abs(q[0] - r[0]))
        q[3] = sorted(q[3] + r[3], key=lambda s: s['bbox'][0]); q[1] = min(q[1], r[1]); q[2] = max(q[2], r[2]); L.remove(r)
    out = []
    for r in L:
        if out and abs(out[-1][0] - r[0]) < 4 and not (r[3][0]['font'].startswith('Univers-Cond') or out[-1][3][0]['font'].startswith('Univers-Cond')):
            out[-1][2] = r[2]; out[-1][3] = out[-1][3] + r[3]
        else: out.append(r)
    return out


def drop(r):  # 쪽 번호·머리글
    f, s = r[3][0]['font'], r[3][0]['size']
    return f.startswith('Univers-Light') or (r[0] > 585 and (f.startswith('SMSEGothic') or f.startswith('Helvetica')))


def text_of(sp, refs=True):
    o = ''
    for i, s in enumerate(sp):
        t = s['text']
        if refs and s['size'] <= 6.0 and REF.match(t.strip()) and (t.strip().endswith(')') or s['flags'] & 1): o += f'[^{t.strip().rstrip(")")}]'; continue
        if s['font'].startswith('Univers-Bold') and i == 0 and t.strip().replace('~', '').replace('-', '').isdigit(): o += f'**{t.strip()}**'; continue
        o += t
    return o


def join(a, b):  # 인쇄본 줄바꿈: 줄 끝에 빈칸이 있으면 낱말 사이, 없으면 낱말 중간
    if not a: return b.lstrip()
    if a.endswith(' ') or b.startswith(' '): return a.rstrip() + ' ' + b.lstrip()
    return a + b


def is_foot(r):
    s = r[3][0]
    return s['size'] in (6.8, 6.3) and not (s['flags'] & 1) and r[0] > 150


def is_sub(r):  # 소제목
    return r[3][0]['font'].startswith('SMKGothic') and r[3][0]['size'] >= 9.5


pages = []          # [(쪽 이름, [문단…])]
feet = {}
NEXT = [1]           # 각주 번호 → [쪽 순번, 문단 위치]
lastfoot = None
chapters = []       # (제목, 쪽 순번)
subs = []


def body_page(n):
    global lastfoot
    margin = 57 if n % 2 == 0 else 85
    R = [r for r in lines(n) if not drop(r)]
    paras, cur, kind = [], '', None
    fparas = []

    def flush():
        nonlocal cur, kind
        if cur.strip(): paras.append('## ' + cur.strip() if kind == 'h' else '++ ' + cur.strip() if kind == 'v' else cur.strip())
        cur, kind = '', None

    i = 0
    # 경 첫 쪽: 큰 번호 + 제목 + 빠알리 제목
    big = [r for r in R if r[3][0]['font'].startswith('Goudy')]
    if big:
        num = big[0][3][0]['text'].strip()
        t20 = ''.join(text_of(r[3]) for r in R if r[3][0]['size'] == 20.0).strip()
        t13 = ''.join(text_of(r[3]) for r in R if r[3][0]['size'] == 13.0).strip()
        title = f'{num} {t20} {t13}'
        paras.append('## ' + title); chapters.append((title, len(pages) + 1))
        R = [r for r in R if r[3][0]['size'] not in (20.0, 13.0, 36.0)]
    R = [r for r in R if r[3][0]['size'] != 20.0]   # 서문·옮긴이의 말 제목은 따로
    body = [r for r in R if not is_foot(r) and not is_sub(r)]
    ind = {id(r): r[1] >= margin + 6 and not text_of(r[3]).startswith('**') for r in body}
    verse = set()
    right = max([r[2] for r in body] or [0])
    runs, run = [], []
    for k, r in enumerate(body):   # 들여 쓴 줄이 이어진 묶음
        if ind[id(r)] and (not run or r[0] - run[-1][0] < 26): run.append(r)
        else:
            if run: runs.append(run)
            run = [r] if ind[id(r)] else []
    if run: runs.append(run)
    for run in runs:
        last = run[-1]; k = body.index(last)
        nxt = body[k + 1] if k + 1 < len(body) else None
        if nxt is not None and not ind[id(nxt)] and nxt[0] - last[0] < 26: run = run[:-1]   # 다음 줄이 이어지면 산문 문단의 첫 줄
        talk = all(re.match(r'^\s*[“‘].*[”’]\s*(\[\^\d+\])?\s*$', text_of(r[3])) for r in run)   # 주고받는 말(“…”) 줄은 게송이 아님
        if len(run) >= 2 and not talk and all(r[2] < right - 6 for r in run): verse.update(id(r) for r in run)
    prev_y = None
    for r in R:
        t = text_of(r[3])
        if id(r) in verse:
            if kind == 'v' and prev_y is not None and r[0] - prev_y < 26: cur += '\n' + t.strip()
            else: flush(); cur, kind = t.strip(), 'v'
            prev_y = r[0]; continue
        if kind == 'v' and not is_foot(r): flush()
        prev_y = r[0]
        if is_foot(r):
            flush()
            m = re.match(r'^\s*(\d{1,3})[.,]?\s+(.*)$', t)
            if m and int(m.group(1)) == NEXT[0]:
                NEXT[0] += 1
                fparas.append(f'[^{m.group(1)}]: ' + m.group(2)); lastfoot = (len(pages) + 1, len(fparas) - 1, m.group(1))
            elif fparas: fparas[-1] = join(fparas[-1], t)
            else:  # 앞 쪽 각주가 이어짐
                pn, k, num = lastfoot
                if pn == len(pages) + 1: fparas[k] = join(fparas[k], t)
                else: pages[pn - 1][1][len(pages[pn - 1][1]) - pages[pn - 1][2] + k] = join(pages[pn - 1][1][len(pages[pn - 1][1]) - pages[pn - 1][2] + k], t)
            continue
        if is_sub(r):
            if kind == 'h' and cur: cur = join(cur, t); continue
            flush(); cur, kind = t, 'h'; subs.append((re.sub(r'\[\^\d+\]', '', t).strip(), len(pages) + 1)); continue
        if kind == 'h': flush()
        new = t.startswith('**') or r[1] >= margin + 6
        if new: flush()
        cur = join(cur, t)
    flush()
    return paras, fparas


def name(n): return f'{n}쪽'


for n in range(1, N + 1):
    if n == 1:  # 속표지
        R = lines(n)
        ps = ['^^ 붓다의 깨달음']
        for r in R:
            if r[3][0]['size'] in (19.0,): ps.append(':: ' + text_of(r[3]).strip())
            elif r[3][0]['size'] == 10.0: ps.append(':: ' + re.sub(r'\s+', ' ', text_of(r[3])).strip())
        assert ''.join(c for r in R if r[3][0]['size'] in (43.0, 23.0) for c in r[3][0]['text'].strip()) == '붓다의깨달음'
        pages.append((name(n), ps, 0)); chapters.append(('속표지', 1)); continue
    if 6 <= n <= 11:  # 차례
        R = lines(n); ps = []
        nums = [(r[0], r[3][0]['text'].strip()) for r in R if r[3][0]['font'].startswith('Univers-Cond')]
        out = []
        for r in R:
            f, s = r[3][0]['font'], r[3][0]['size']
            if f.startswith('Univers-Cond') or s in (24.0,) or (s == 15.0 and '선집' in r[3][0]['text']): continue
            if s == 15.0: continue   # '차례' — 장 제목으로
            t = ''.join(x['text'] for x in r[3])
            if f.startswith('TimesNewRomanPS-Bold'):
                no = r[3][0]['text'].strip(); rest = ''.join(x['text'] for x in r[3][1:]).strip()
                pg = min(nums, key=lambda q: abs(q[0] - r[0]))
                assert abs(pg[0] - r[0]) < 6, (n, t)
                out.append(f'**{no}** {rest} | {pg[1]}')
            else: out.append('- ' + t.strip())
        if n == 6: chapters.append(('차례', len(pages) + 1))
        pages.append((name(n), ['%% ' + '\n'.join(out)] if n == 6 else ['%% ' + '\n'.join(out)], 0)); continue
    if n in (2, 314):  # 서문·옮긴이의 말: 20pt 제목
        pass
    if n == 316:  # 판권지
        R = lines(n); ps, cur, py = [], [], None
        for r in R:
            t = text_of(r[3], refs=False).replace('│', '|').rstrip()
            if py is not None and r[0] - py > 16: ps.append('\n'.join(cur)); cur = []
            cur.append(t.strip()); py = r[0]
        ps.append('\n'.join(cur))
        chapters.append(('판권지', len(pages) + 1)); pages.append((name(n), ps, 0)); continue
    R = lines(n)
    # 20pt 장 제목(서문·옮긴이의 말)
    t20 = [r for r in R if r[3][0]['size'] == 20.0 and not any(x['font'].startswith('Goudy') for r2 in R for x in r2[3])]
    paras, fparas = body_page(n)
    if t20 and not any(c[1] == len(pages) + 1 for c in chapters):
        tt = text_of(t20[0][3]).strip()
        paras = ['## ' + tt] + [p for p in paras if p != '## ' + tt and p != tt]
        chapters.append((tt, len(pages) + 1))
    # 오른쪽 맞춤(서명) 줄
    pages.append((name(n), paras + fparas, len(fparas)))

# 서명·오른쪽 맞춤: 5쪽, 315쪽
def rightalign(n, lines_):
    pg = pages[n - 1]
    ps = pg[1]
    for t in lines_:
        for k, p in enumerate(ps):
            if p.endswith(t) and p != t:
                ps[k] = p[: -len(t)].rstrip(); ps.insert(k + 1, '>> ' + t); break
            if p == t: ps[k] = '>> ' + t; break

rightalign(5, ['뉴욕주 카멜 소재 추앙 옌 사원에서', '빅쿠 보디 대장로'])
rightalign(315, ['케마짜라  합장'])

# 글자층에 없이 그림으로만 찍힌 글자 '五' (236쪽·238쪽 소제목, 인쇄본에 보임)
GLYPH = [(236, '(오개-蓋)', '(오개-五蓋)'), (238, '2. 오온蘊', '2. 오온五蘊')]
for n, a, b in GLYPH:
    ps = pages[n - 1][1]; k = [i for i, p in enumerate(ps) if a in p]
    assert k, (n, a); ps[k[0]] = ps[k[0]].replace(a, b)
    for t in subs:
        pass
subs[:] = [(t.replace('(오개-蓋)', '(오개-五蓋)').replace('2. 오온蘊', '2. 오온五蘊'), p) for t, p in subs]

body = ''
for nm, ps, _ in pages:
    body += f'=== {nm} ===\n' + '\n\n'.join(p for p in ps if p.strip()) + '\n\n'
body = body.rstrip() + '\n'
toc = []
for t, p in sorted(chapters, key=lambda x: x[1]): toc.append({'title': t, 'page': p, 'sub': False})
for t, p in subs: toc.append({'title': t, 'page': p, 'sub': True})
toc.sort(key=lambda x: (x['page'], x['sub']))
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [], 'body': body},
          open(f'content/texts/{BK}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{BK}.json', 'a').write('\n')
print(f'{len(pages)} 쪽 · 장 {len(chapters)} · 소제목 {len(subs)}')
print('빠알리 표기 고침:', dict(fixes))
