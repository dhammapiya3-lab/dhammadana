#!/usr/bin/env python3
"""『가르침을 배우다』 개정판(DL-0018) 종이책 PDF → content/texts/DL-0018.json
  python3 tools/pdf2text_dl0018.py 책.pdf && python3 tools/split_chapters.py --write

PDF는 펼침면(두 쪽이 한 장)이라 쪽마다 반으로 나눔: PDF 1장 = 1쪽, PDF k장(2~228) = 왼쪽 2k-2쪽·오른쪽 2k-1쪽, PDF 229장 = 456쪽.
PDF 파일은 사이트에 올리지 않고 글로 읽기만 씀 (운영자 요청, 2026-11-09).
글자는 PDF 그대로 (조판 기호 \\x07·\\x03 만 빼고, 차례·찾아보기의 \\x08 이음 표시는 점선으로).
- 한글 빨리어 위의 발음 부호(〬 〭 ᷇ ˑ 등, 따로 놓인 글자)는 인쇄된 자리의 바로 앞 글자 뒤에 붙임 (PDF 글 순서와 같음)
- 들여 쓴 줄은 새 문단, 꽉 찬 줄 다음은 이어 붙임, 짧은 줄이 이어지면(게송) 인쇄된 줄 그대로
- 소제목: 고딕 13.6·명조 12.8/11.8 제목, 장 첫 쪽 제목은 '## '. 굵은 글꼴(Bold)은 **굵게**
- 각주: 위첨자 번호 [^n], 쪽 아래 각주 [^n]: … (다음 쪽으로 넘어간 각주는 앞 각주에 이어 붙임)
"""
import collections, fitz, json, re, sys
pdf = sys.argv[1]
bk, ED = 'DL-0018', '개정판 1쇄'
src = fitz.open(pdf)
NP = src.page_count
HALF = 425.0
FOOTY = 570
fixes = []
EXCL = {12: (0, 999), 436: (280, 548)}  # 그림으로 넣는 곳 (쪽: 위아래 범위)
MARKS = set('〭᷇〬ˑ̫͌″᷾᷃˔˕')


def vpages():
    """(쪽 번호, PDF 장 번호(0부터), 반쪽: None/'L'/'R')"""
    out = [(1, 0, None)]
    for k in range(2, NP):
        out += [(2 * k - 2, k - 1, 'L'), (2 * k - 1, k - 1, 'R')]
    out.append((2 * NP - 2, NP - 1, None))
    return out


VP = vpages()
PN = {n: (k, h) for n, k, h in VP}


def geom(n):
    return (62.0, 360.0) if n % 2 == 0 else (68.0, 366.0)


def ntext(t):
    t = t.replace('\n', '\ue0ff')  # 조판 줄바꿈(InDesign) 자리 표시 — 마지막에 SOFTBR 규칙으로 처리
    return t.replace('\x07', '').replace('\x03', '').replace('\xad', '').replace('\t', ' ').replace('\r', '')


def is_bold(s):
    return 'Bold' in s['font'] and 'Helvetica' not in s['font']


def head_span(s):
    f, z = s['font'], s['size']
    if 'YDVYGO34' in f and z >= 13: return True
    if 'YDVYMjO34' in f and z >= 11.5: return True
    if 'TTYeossi' in f: return True
    if 'SDIyagi' in f and z >= 11.5: return True
    if 'NanumGothicBold' in f: return True
    return False


def raw_lines(n):
    k, h = PN[n]
    pg = src[k]
    lines = []
    for b in pg.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                for c in s['chars']:
                    x0, y0, x1, y1 = c['bbox']
                    if h == 'L' and x0 >= HALF - 2: continue
                    if h == 'R' and x0 < HALF - 2: continue
                    off = HALF if h == 'R' else 0
                    lines.append(dict(c=c['c'], x0=x0 - off, x1=x1 - off, y0=y0, y1=y1, font=s['font'], size=s['size'], color=s['color'],
                                      base=l['bbox'][3], line=id(l)))
    return lines


def build_lines(n, split=None):
    """글자들을 인쇄 줄로 모음. 발음 부호는 왼쪽 글자 바로 뒤에."""
    cs = raw_lines(n)
    marks = [c for c in cs if c['c'] in MARKS and ('Batang' in c['font'] or 'HCR' in c['font'])]
    rest = [c for c in cs if not (c['c'] in MARKS and ('Batang' in c['font'] or 'HCR' in c['font']))]
    # 줄: 같은 PDF 줄(line id) 을 기본으로, 높이가 겹치면 합침
    groups = collections.OrderedDict()
    for c in rest:
        groups.setdefault(c['line'], []).append(c)
    L = []
    for g in groups.values():
        y0 = min(c['y0'] for c in g); y1 = max(c['y1'] for c in g)
        L.append(dict(cs=g, y0=y0, y1=y1, x0=min(c['x0'] for c in g), x1=max(c['x1'] for c in g)))
    L = [a for a in L if ''.join(c['c'] for c in a['cs']).strip()]
    L.sort(key=lambda a: (0 if split is None or a['x0'] < split else 1, round((a['y0'] + a['y1']) / 2), a['x0']))
    M = []
    for a in L:
        mid = (a['y0'] + a['y1']) / 2
        cand = [m for m in M[-3:]]
        hit = None
        for m in reversed(cand):
            mm = (m['y0'] + m['y1']) / 2
            same_col = split is None or ((a['x0'] < split) == (m['x0'] < split))
            if same_col and (abs(mid - mm) < 4.5 or (a['y0'] < m['y1'] - 2 and a['y1'] > m['y0'] + 2 and abs(mid - mm) < 8)): hit = m; break
        if hit is not None:
            m = hit; m['cs'] += a['cs']; m['y0'] = min(m['y0'], a['y0']); m['y1'] = max(m['y1'], a['y1']); m['x0'] = min(m['x0'], a['x0']); m['x1'] = max(m['x1'], a['x1']); continue
        if False:
            m = M[-1]; mm = (m['y0'] + m['y1']) / 2
            same_col = split is None or ((a['x0'] < split) == (m['x0'] < split))
            if same_col and (abs(mid - mm) < 4.5 or (a['y0'] < m['y1'] - 2 and a['y1'] > m['y0'] + 2 and abs(mid - mm) < 8)):
                m['cs'] += a['cs']; m['y0'] = min(m['y0'], a['y0']); m['y1'] = max(m['y1'], a['y1']); m['x0'] = min(m['x0'], a['x0']); m['x1'] = max(m['x1'], a['x1']); continue
        M.append(dict(a))
    for m in M: m['cs'].sort(key=lambda c: (c['x0'] + c['x1']) / 2)
    # 발음 부호 끼우기: 높이가 맞는 줄에서, 부호 왼쪽 끝과 오른쪽 끝이 가장 가까운 글자 뒤
    for mk in marks:
        mmid = (mk['y0'] + mk['y1']) / 2
        cand = [m for m in M if m['x0'] - 3 <= mk['x0'] <= m['x1'] + 3 and abs((m['y0'] + m['y1']) / 2 - mmid) < 16]
        if not cand:  # 홀로 인쇄된 부호(부호 자체를 보여 주는 곳)는 제자리에 그대로
            M.append(dict(cs=[mk], y0=mk['y0'], y1=mk['y1'] + 6, x0=mk['x0'], x1=mk['x1'] + 4)); M.sort(key=lambda m: ((m['y0'] + m['y1']) / 2, m['x0'])); continue
        m = min(cand, key=lambda m: abs((m['y0'] + m['y1']) / 2 - mmid))
        j = min(range(len(m['cs'])), key=lambda i: abs(mk['x0'] - m['cs'][i]['x1']))
        m['cs'].insert(j + 1, dict(mk, x0=m['cs'][j]['x1'] - 0.01))
    return M


def spans_of(m):
    """같은 글꼴·크기가 이어지는 조각"""
    out = []; pc = None
    for c in m['cs']:
        # 글자 사이가 벌어져 있는데 빈칸 글자가 없으면 빈칸 하나 (인쇄된 띄어쓰기를 살림 — 빈칸만 더함)
        if pc is not None and c['x0'] - pc['x1'] > 2.2 and c['c'] != ' ' and pc['c'] != ' ' and c['c'] not in MARKS:
            if out: out[-1]['text'] += ' '
        pc = c
        if out and out[-1]['font'] == c['font'] and abs(out[-1]['size'] - c['size']) < .05 and out[-1]['color'] == c['color']:
            out[-1]['text'] += c['c']; continue
        out.append(dict(text=c['c'], font=c['font'], size=c['size'], color=c['color'], x0=c['x0']))
    for s in out: s['text'] = ntext(s['text'])
    return [s for s in out if s['text']]


def lines_of(n, cols=None):
    left, right = geom(n)
    M = build_lines(n, split=(left + right) / 2 + 2 if cols else None)
    R = []
    for m in M:
        if m['y0'] > FOOTY: continue
        if n in EXCL and EXCL[n][0] <= m['y0'] <= EXCL[n][1]: continue  # 그림으로 넣는 표·도표 자리
        sp = spans_of(m)
        ss = [s for s in sp if s['text'].strip()]
        if not ss: continue
        cs = [s for s in ss if 'Helvetica' not in s['font']]
        small = sum(len(s['text'].strip()) for s in cs if s['size'] < 8.0); tot = sum(len(s['text'].strip()) for s in cs) or 1
        a = dict(sp=sp, x0=m['x0'], x1=m['x1'], y0=m['y0'], y1=m['y1'])
        a['sz'] = max(s['size'] for s in ss)
        a['foot'] = small * 2 > tot and a['y0'] > 150 and 18 <= n <= 435
        hs = [s for s in ss if re.search('[가-힣ㄱ-ㅎ■]', s['text'])]
        a['head'] = bool(hs) and all(head_span(s) for s in hs)
        a['bold'] = all(is_bold(s) for s in ss if re.search('[가-힣A-Za-z]', s['text'])) and any(is_bold(s) for s in ss)
        a['verse'] = a['x0'] > left + 20 and not a['head']
        a['cverse'] = any('YDVYMjO23' in s['font'] for s in ss) and not a['head']  # 색 글자 게송(가운데 맞춤)
        a['col'] = (1 if a['x0'] > (left + right) / 2 else 0) if cols else 0
        a['raw'] = ''.join(s['text'] for s in sp)
        R.append(a)
    R.sort(key=lambda a: (a['col'], round((a['y0'] + a['y1']) / 2), a['x0']))
    for a in R: a['t'] = line_text(a)
    return R


SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def line_text(a):
    out = []; first = True
    for s in a['sp']:
        t = s['text']
        if 'Helvetica' in s['font'] and re.fullmatch(r'\s*\d+\s*', t):
            if a['foot'] and first: out.append((f'[^{t.strip()}]: ', False)); first = False; continue
            if not a['foot']: out.append((f'[^{t.strip()}]', False)); first = False; continue
        if s['size'] < 6.5 and 'Times' in s['font'] and re.fullmatch(r'\d+', t.strip()):
            out.append((t.translate(SUP), False)); fixes.append(f'위첨자 {t.strip()} → {t.strip().translate(SUP)}'); first = False; continue
        b = is_bold(s) and not a['head']
        if not re.search('[가-힣A-Za-z0-9]', t) and out: b = out[-1][1]
        out.append((t, b)); first = False
    res, cb = '', False
    for t, b in out:
        if b and not cb and t.strip():
            lead = len(t) - len(t.lstrip()); res += t[:lead] + '**'; t = t[lead:]; cb = True
        elif not b and cb and t.strip():
            tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + ' ' * tail; cb = False
        res += t
    if cb:
        tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + ' ' * tail
    if a['foot']: res = re.sub(r'^(\[\^\d+\]: )\s+', r'\1', res)
    return res


MARK = re.compile(r'\s*(\d+\.\s|\(\d+\)|[⑴-⒇①-⑳]|\d+\)|•|\*|☞|-\s|■|●)')
clean = lambda s: re.sub(r'[ \t ]+\n', '\n', re.sub(r'(?<=\S)[ \t ]{2,}', ' ', s)).strip()


def body_paras(n, body, left=None, right=None):
    gl, gr = geom(n)
    left = gl if left is None else left; right = gr if right is None else right
    paras, cur, prev, verse, hang = [], None, None, False, None
    # 들여 짠 묶음 중 양끝 맞춤된 산문(마지막 줄 말고 모든 줄이 같은 오른쪽 끝)은 이어 붙임
    groups, g = [], []
    for i, a in enumerate(body):
        q = body[i - 1] if i else None
        if not a.get('verse'): g = []; continue
        if not g or q is None or not q.get('verse') or a['y0'] - q['y1'] > max(8.0, q['y1'] - q['y0']) * 1.3 or abs(a['x0'] - q['x0']) >= 3:
            g = []; groups.append(g)
        g.append(a)
    for g in groups:
        if len(g) < 2: continue
        edge = max(a['x1'] for a in g)
        if edge - g[0]['x0'] < 200: continue
        full = [abs(a['x1'] - edge) <= 4 for a in g]
        if sum(full[:-1]) < 1: continue
        for i in range(1, len(g)):
            q = g[i - 1]
            if full[i - 1] and not re.search(r'[.!?。]\s*$', q['raw']) and sum(full) >= 2: g[i]['qjoin'] = True
    for a in body:
        t = ('\x01' + a['t']) if a.get('cverse') else a['t']
        if a['head']:
            if cur and cur.startswith('## ') and prev is not None and prev['head'] and a['y0'] - prev['y1'] < 16:
                cur = cur.rstrip() + ' ' + t.replace('**', '').strip()
            else:
                if cur: paras.append(cur)
                cur = '## ' + t.replace('**', '').strip()
            prev = a; continue
        if cur is None or prev is None or prev['head']:
            if cur: paras.append(cur)
            cur = t; verse = False; hang = None; prev = a; continue
        gap = a['y0'] - prev['y1']
        lh = max(8.0, prev['y1'] - prev['y0'])
        pshort = prev['x1'] < right - 14
        short = a['x1'] < right - 14
        mark = MARK.match(a['raw']) is not None
        if hang is None and not pshort and MARK.match(prev['raw']) and a['x0'] > prev['x0'] + 3:
            hang = a['x0']
        if a.get('qjoin') and prev['verse'] and gap <= lh * 1.3:
            cur = cur + t
        elif (a['verse'] and prev['verse'] and gap <= lh * 1.3 and abs(a['x0'] - prev['x0']) < 3) or (a.get('cverse') and prev.get('cverse') and gap <= lh * 1.3):
            cur = cur.rstrip() + '\n' + t; verse = True
        elif hang is not None and abs(a['x0'] - hang) < 2 and not mark and gap <= lh * 1.2:
            cur = (cur.rstrip() + '\n' + t) if pshort else cur + t
        elif 9 <= a['x0'] - left <= 15 and not a['verse']:
            paras.append(cur); cur = t; verse = False; hang = None
        elif not mark and hang is None and prev['x0'] - a['x0'] > 5 and 9 <= prev['x0'] - left <= 15 and '\n' not in cur and gap <= lh * 1.2 and not pshort and abs(a['x0'] - left) < 3:
            cur = cur + t
        elif gap > lh * 1.3 or (abs(a['sz'] - prev['sz']) > .8 and pshort) or mark or a['bold'] != prev['bold'] or abs(a['x0'] - prev['x0']) > 5:
            paras.append(cur); cur = t; verse = False; hang = None
        elif pshort:
            if verse or short or len(cur.split('\n')) == 1 and len(cur) < 60:
                cur = cur.rstrip() + '\n' + t; verse = True
            else:
                paras.append(cur); cur = t; verse = False
        else:
            cur = cur + t
        prev = a
    if cur: paras.append(cur)
    # 색 글자 게송(인쇄본에서 가운데 맞춤)만으로 된 문단은 가운데로
    out = []
    for p in paras:
        ls = p.split('\n')
        out.append((':: ' if all(l.startswith('\x01') for l in ls) else '') + p.replace('\x01', ''))
    return out


def foot_items(n, foot):
    _, right = geom(n)
    items, cur, prev = [], None, None
    for a in foot:
        m = re.match(r'\[\^(\d+)\]: ', a['t'])
        if m:
            if cur: items.append(cur)
            cur = [int(m.group(1)), a['t'][m.end():]]
        elif cur is None:
            cur = [None, a['t']]
        elif prev['x1'] < right - 14:
            cur[1] = cur[1].rstrip() + '\n' + a['t'].lstrip()
        else:
            cur[1] = cur[1] + a['t'].lstrip()
        prev = a
    if cur: items.append(cur)
    return items


if __name__ == '__main__' and '--lines' in sys.argv:
    for n in [int(x) for x in sys.argv[sys.argv.index('--lines') + 1].split(',')]:
        print(f'=== {n}쪽 ===')
        for a in lines_of(n, cols=('--cols' in sys.argv)):
            print(a['col'], round(a['x0']), round(a['y0']), round(a['x1']), 'F' if a['foot'] else ' ', 'H' if a['head'] else ' ', [(s['font'][:10], round(s['size'], 1)) for s in a['sp'] if s['text'].strip()][:2], repr(a['raw'][:60]))
    sys.exit()


plain = lambda a: re.sub(r'\s+', ' ', a['t']).strip()
N = VP[-1][0]
pages = []
for n in range(1, N + 1):
    L = lines_of(n)
    body = [a for a in L if not a['foot']]
    foot = [a for a in L if a['foot']]
    paras = body_paras(n, body)
    fns = []
    for num, txt in foot_items(n, foot):
        if num is None:
            back = next((pp for pp in reversed(pages) if pp[2]), None)
            if back is None: fns.append(txt); continue
            q = back[2][-1]
            back[2][-1] = (q.rstrip() + '\n' + txt.lstrip()) if re.search(r'[.)」』”]\s*$', q) else q + txt
            fixes.append(f'{n}쪽: 앞 쪽에서 넘어온 각주를 앞 각주에 이어 붙임')
            continue
        fns.append(f'[^{num}]: ' + txt)
    pages.append([n, paras, fns])
P = {p[0]: p for p in pages}

if __name__ == '__main__' and '--dump' in sys.argv:
    for n in [int(x) for x in sys.argv[sys.argv.index('--dump') + 1].split(',')]:
        print(f'=== {n}쪽 ===')
        print('\n\n'.join(clean(x) for x in P[n][1] + P[n][2]))
    sys.exit()

# ---- 쪽마다 손볼 곳 (인쇄된 모양 그대로) ----
from PIL import Image
images = []


def crop(n, box, name, dpi=200):
    """n쪽(반쪽 좌표)의 box 부분을 그림으로"""
    k, h = PN[n]; off = HALF if h == 'R' else 0
    x0, y0, x1, y1 = box
    pix = src[k].get_pixmap(dpi=dpi, clip=fitz.Rect(x0 + off, y0, x1 + off, y1))
    path = f'public/uploads/{bk}-{name}.png'; pix.save(path)
    im = Image.open(path).convert('RGB'); im.save(path.replace('.png', '.jpg'), quality=85); import os; os.remove(path)
    url = '/uploads/' + os.path.basename(path.replace('.png', '.jpg')); images.append(url); return url


rowsl = lambda n: [a for a in lines_of(n)]
# 1쪽 앞속표지, 3쪽 속표지
P[1][1] = [(':: ' if a['sz'] < 20 else '^^ ') + plain(a) for a in rowsl(1)]
P[3][1] = [(':: ' if a['sz'] < 20 else '^^ ') + plain(a).replace('**', '') for a in rowsl(3)]
# 2쪽 예경문: 세 묶음, 줄 그대로 가운데
P[2][1] = [':: ' + x for x in P[2][1]]
# 12쪽 구성표(도표) → 그림 (도표 안 글자는 그림으로만)
u = crop(12, (40, 50, 380, 570), 'chart')
P[12][1] = [f'![#가르침을 배우다 구성표]({u})']
# 13~17쪽 차례: %% 문단 (x 자리로 단계, \x08 이음 표시는 점선)
TOCROWS = []
for n in range(13, 18):
    left, _ = geom(n); out, head = [], []
    for a in lines_of(n):
        t = plain(a)
        if a['head']: head.append('## ' + t); continue
        m = re.match(r'(.*?)\s*\x08\s*(\d+)$', t)
        title, pg = (m.group(1).strip(), m.group(2)) if m else (t.replace('\x08', '').strip(), '')
        lv = 0 if a['x0'] < left + 5 else (1 if a['x0'] < left + 13 else 2)
        isch = any('YDVYGO33' in s['font'] for s in a['sp'] if s['text'].strip())
        row = ('-' * lv + ' ' if lv else '') + (f'**{title}**' if isch else title) + (f' | {pg}' if pg else '')
        out.append(row); TOCROWS.append((lv, title, int(pg) if pg else None, isch))
    P[n][1] = head + ['%% ' + '\n'.join(out)]
# 436쪽 발음 표 → 그림 (표 부분만), 나머지 글은 그대로
L436 = lines_of(436)
u = crop(436, (55, 280, 368, 548), 'pali-table')
keep = L436
P[436][1] = body_paras(436, keep)
P[436][1].insert(next((i for i, x in enumerate(P[436][1]) if '일반적인 표기' in x), len(P[436][1])) + 1, f'![#빠알리어 모음·자음 표기 표]({u})')
# 446~453쪽 찾아보기: 두 단, 항목마다 한 줄 (넘친 줄은 이어 붙임, \x08 은 빈칸)
for n in range(446, 454):
    left, right = geom(n); out, block = [], []
    for a in lines_of(n, cols=True):
        t = a['t'].replace('\x08', ' ')
        if a['head'] and len(t.strip()) <= 2:
            if block: out.append('\n'.join(block)); block = []
            out.append('## ' + t.strip()); continue
        if a['head']: out.append('## ' + t.strip()); continue
        cl = left if a['col'] == 0 else left + 158
        if not block or a['x0'] <= cl + 4 or re.match(r'\s*\d', t) is None and block[-1].rstrip().endswith(tuple('0123456789')) and a['x0'] <= cl + 4:
            block.append(t)
        else:
            block[-1] = block[-1] + t.lstrip()
    if block: out.append('\n'.join(block))
    P[n][1] = out
# 455쪽 법 보시 명단: 명단은 줄 그대로, 가운데 게송은 가운데
L = lines_of(455); out, blk, cen = [], [], []
for a in L:
    t = plain(a)
    if t.startswith('■'): out.append('## ' + t); continue
    if a['x0'] > 100 and not t.startswith('•'):
        if blk: out.append('\n'.join(blk)); blk = []
        cen.append(t); continue
    if cen: out.append(':: ' + '\n'.join(cen)); cen = []
    if t.startswith('•'):
        if blk: out.append('\n'.join(blk)); blk = []
        out.append(t)
    elif out and out[-1].startswith('•') and not blk: out[-1] = out[-1] + a['t'].strip() if out[-1].endswith(' ') else out[-1] + ' ' + a['t'].strip() if False else out[-1] + a['t']
    else: blk.append(t)
if blk: out.append('\n'.join(blk))
if cen: out.append(':: ' + '\n'.join(cen))
P[455][1] = [re.sub(r'(?m)^## ', '## ', x) for x in out]
# 456쪽 판권지: 줄 그대로
P[456][1] = ['\n'.join(plain(a) for a in lines_of(456))]
# 454쪽 지은이·감수자: ■■ 제목은 소제목으로
P[454][1] = [('## ' + x) if x.startswith('■■') else x for x in P[454][1]]

body = ''
for n, ps, fns in pages:
    body += f'=== {n}쪽 ===\n' + '\n\n'.join(clean(x) for x in ps + fns if clean(x)) + '\n\n'
body = re.sub(r'\*\*( ?)\*\*', r'\1', body).rstrip() + '\n'
# 조판 줄바꿈 자리: 낱말 중간이 대부분이라 붙이고(왔습|니다, Attadaṇ|ḍa), 한글 뒤에 《 ( “ ‘ [ 〈 가 오면 빈칸
body = re.sub(r'(.)\ue0ff[ \t]*(\n?)[ \t]*(.)', lambda m: m.group(1) + m.group(2) + ((' ' if re.match('[가-힣]', m.group(1)) and m.group(3) in '《(“‘[〈<' else '') if not m.group(2) else '') + m.group(3), body).replace('\ue0ff', '')

# ---- 목차 ----
nz = lambda x: re.sub(r'[^0-9A-Za-z가-힣一-龥]', '', x)
PG = {int(m.group(1)): m.group(2) for m in re.finditer(r'=== (\d+)쪽 ===\n(.*?)(?=\n=== |\Z)', body, re.S)}
toc = [dict(title='예경문', page=2, sub=False), dict(title='속표지', page=3, sub=False), dict(title='일러두기', page=4, sub=False),
       dict(title='약어', page=5, sub=False)]
for lv, title, pg, isch in TOCROWS:
    if pg is None or lv > 1: continue
    t = title.lstrip('• ').strip()
    toc.append(dict(title=t, page=pg, sub=lv == 1))
toc.insert(next(i for i, e in enumerate(toc) if e['title'] == '가르침을 배우다 구성표') + 1, dict(title='차례', page=13, sub=False))
toc += [dict(title='참고문헌', page=442, sub=False), dict(title='찾아보기', page=446, sub=False), dict(title='지은이·감수자', page=454, sub=False),
        dict(title='법 보시 명단', page=455, sub=False), dict(title='판권지', page=456, sub=False)]
for e in toc:
    if not e['sub']: continue
    ps = [p for p in PG.get(e['page'], '').split('\n\n') if p.strip()]
    key = nz(e['title'])
    k = next((i for i, p in enumerate(ps) if p.startswith('## ') and nz(p).startswith(key[:8])), None)
    if k is None:
        for q in (e['page'] + 1, e['page'] - 1):
            ps2 = [p for p in PG.get(q, '').split('\n\n') if p.strip()]
            k2 = next((i for i, p in enumerate(ps2) if p.startswith('## ') and nz(p).startswith(key[:8])), None)
            if k2 is not None: print('목차 쪽 옮김:', e['title'], e['page'], '→', q); e['page'] = q; ps, k = ps2, k2; break
    if k is None: print('  (소제목 없음)', e['title'], e['page']); continue
    if k > 0: e['at'] = re.sub(r'^## ', '', ps[k])[:12]
json.dump({'book': bk, 'edition': ED, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(N, '쪽', len(toc), '목차', len(images), '그림')
for f in dict.fromkeys(fixes): print('  ·', f)
