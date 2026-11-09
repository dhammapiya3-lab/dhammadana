#!/usr/bin/env python3
"""『부처님을 만나다』 개정판 2쇄(DL-0017) 종이책 PDF → content/texts/DL-0017.json
  python3 tools/pdf2text_dl0017.py 책.pdf && python3 tools/split_chapters.py --write
  ※ 2026-11-09 이후 운영자가 관리자 화면에서 판권지 줄 묶음 등을 고쳤으므로, 다시 돌리면 그 고침이 덮어써짐 — 다시 돌리기 전 확인할 것

PDF 쪽 = 인쇄된 쪽 (528쪽). PDF 파일은 사이트에 올리지 않고 글로 읽기만 씀 (운영자 요청, 2026-11-09).
글자는 PDF 그대로 (화면에 안 보이는 조판 기호 \\x07 만 뺌). 다르게 한 곳:
- 글꼴에 없는 글자라 그림(선)으로 인쇄된 한자 辟·羯 6곳은 인쇄된 대로 글자로 넣음 (PDF 글자층에는 빠져 있음)
- 판권지의 사용자 정의 기호(U+E20D)는 인쇄된 모양 그대로 ＊ 로
- 참고문헌의 '같은 지은이' 줄(선으로 인쇄)은 ——— 로
- 80쪽 각주의 위첨자 '10의 140제곱'은 ¹⁴⁰ (위첨자 숫자)로
- 장 첫 쪽(1·2·3…8 + 장 제목, 그림으로만 인쇄됨)은 글로 읽기에서 장 제목으로 보이므로 빈 쪽으로 둠
줄·문단: 들여쓴 줄은 새 문단, 꽉 찬 줄 다음은 이어 붙임, 짧은 줄이 이어지면(게송·인용 게송) 인쇄된 줄 그대로.
소제목: 명조 큰 글씨(17.5·19.5)·고딕 제목 줄은 '## '. 굵은 명조는 **굵게**.
각주: 위첨자 번호 [^n], 쪽 아래 각주 [^n]: … (다음 쪽으로 넘어간 각주는 앞 각주에 이어 붙임).
"""
import collections, fitz, json, re, sys
pdf = sys.argv[1]
bk, ED = 'DL-0017', '개정판 2쇄'
src = fitz.open(pdf)
N = src.page_count
OPENERS = (35, 57, 89, 125, 143, 169, 209, 447)
# 글꼴에 글자가 없어 선으로 그려 인쇄된 한자 (쪽, 그림 상자 왼쪽 위 x, y) → 글자
DRAWN = {(59, 302, 253): '辟', (60, 212, 351): '辟', (429, 350, 215): '羯',
         (518, 195, 270): '辟', (518, 132, 354): '辟', (527, 230, 328): '羯'}
SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
HEADF = re.compile(r'YDVYGOStd1[345]|NanumGothic')
fixes = []
JOINLOG = []
# 폭이 우연히 인용 산문과 같은 게송 줄 (눈으로 확인, 2026-11-09): (쪽, 줄 위치)
VERSE_KEEP = {(119, 115), (354, 524)}


def ntext(t):
    t = re.sub(r'(?<=\S)\n', ' ', t).replace('\n', '')  # 글 안의 강제 줄바꿈(InDesign) → 낱말 사이 빈칸
    return t.replace('\x07', '').replace('\xad', '').replace('', '＊').replace('\t', ' ').replace('\r', '')


def is_bold(s):
    return ('Bold' in s['font'] or 'ExtraBol' in s['font']) and 'Helvetica' not in s['font']


def head_span(s):
    f, z = s['font'], s['size']
    if 'NanumMyeongjo' in f and z >= 17: return True
    if HEADF.search(f) and z >= 8.5: return True
    if 'YDVYGOStd12' in f and z >= 9.9: return True
    return False


def lines_of(n, cols=False):
    pg = src[n - 1]
    L = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [dict(text=ntext(s['text']), font=s['font'], size=s['size'], x0=s['bbox'][0], y0=s['bbox'][1]) for s in l['spans']]
            sp = [s for s in sp if s['text']]
            if not ''.join(s['text'] for s in sp).strip(): continue
            x0, y0, x1, y1 = l['bbox']
            if y0 > 600: continue  # 쪽 번호·머리글
            L.append(dict(sp=sp, x0=x0, y0=y0, x1=x1, y1=y1))
    # 그림으로 인쇄된 한자: 같은 높이 줄의 알맞은 자리에 글자 조각으로 끼움
    for (p, dx, dy), ch in DRAWN.items():
        if p != n: continue
        best = min(L, key=lambda a: abs((a['y0'] + a['y1']) / 2 - (dy + 5)) + (0 if a['x0'] - 2 <= dx <= a['x1'] + 12 else 1000))
        best['sp'].append(dict(text=ch, font='(drawn)', size=10, x0=dx, y0=dy)); best['sp'].sort(key=lambda s: s['x0'])
        best['x0'] = min(best['x0'], dx); best['x1'] = max(best['x1'], dx + 9)
        fixes.append(f'{n}쪽: 선으로 인쇄된 한자 {ch} 넣음')
    for a in L:
        ss = [s for s in a['sp'] if s['text'].strip()]
        a['sz'] = max(s['size'] for s in ss)
        cs = [s for s in ss if 'Helvetica' not in s['font']]
        small = sum(len(s['text'].strip()) for s in cs if s['size'] < 8.3); tot = sum(len(s['text'].strip()) for s in cs)
        a['foot'] = 18 <= n <= 507 and small * 2 > tot  # 각주 줄 (글자 대부분이 작은 글씨)
        hs = [s for s in ss if re.search('[가-힣ㄱ-ㅎ■]', s['text'])]
        a['head'] = bool(hs) and all(head_span(s) for s in hs)
        a['bold'] = all(is_bold(s) for s in ss if re.search('[가-힣A-Za-z]', s['text'])) and any(is_bold(s) for s in ss)
        a['col'] = (1 if a['x0'] > 250 else 0) if cols else 0
        a['verse'] = any('Nanum' in s['font'] for s in ss) and 9 < a['sz'] < 11 and a['x0'] > geom(n)[0] + 20  # 들여 짠 인용 게송
    L.sort(key=lambda a: (a['col'], round(a['y0']), a['x0']))
    M = []
    for a in L:
        if M and M[-1]['col'] == a['col'] and abs(a['y0'] - M[-1]['y0']) < 3 and a['foot'] == M[-1]['foot']:
            m = M[-1]; m['sp'] += a['sp']; m['x1'] = max(m['x1'], a['x1']); m['y1'] = max(m['y1'], a['y1'])
            m['sz'] = max(m['sz'], a['sz']); m['head'] = m['head'] and a['head']; continue
        M.append(a)
    for a in M:
        a['sp'].sort(key=lambda s: s['x0'])
        a['t'] = line_text(a)
        a['raw'] = ''.join(s['text'] for s in a['sp'])
    return M


def line_text(a):
    out = []
    first = True
    for s in a['sp']:
        t = s['text']
        if 'Helvetica' in s['font'] and re.fullmatch(r'\s*\d+\s*', t):
            if a['foot'] and first:
                out.append((f'[^{t.strip()}]: ', False)); first = False; continue
            if not a['foot']:
                out.append((f'[^{t.strip()}]', False)); first = False; continue
        if s['size'] < 5 and re.fullmatch(r'\d+', t.strip()):
            out.append((t.translate(SUP), False)); fixes.append('80쪽: 위첨자 ' + t.strip() + ' → ' + t.strip().translate(SUP)); first = False; continue
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


def geom(n):
    return (105.0, 400.0) if n % 2 == 0 else (108.0, 403.0)


MARK = re.compile(r'\s*(\d+\.\s|\(\d+\)|[⑴-⒇①-⑳]|\d+\)|•|\*|☞|-\s|■)')
clean = lambda s: re.sub(r'[ \t ]+\n', '\n', re.sub(r'(?<=\S)[ \t ]{2,}', ' ', s)).strip()


def body_paras(n, body, left=None, right=None):
    gl, gr = geom(n)
    left = gl if left is None else left; right = gr if right is None else right
    paras, cur, prev, verse, hang = [], None, None, False, None
    # 인용 산문 가리기: 들여 짠 명조 글을 묶음(빈 줄·들여쓰기로 나뉨)마다 보고,
    # 마지막 줄 말고 모든 줄이 같은 오른쪽 끝(±4, 거의 꽉 찬 폭)에서 끝나는 줄이 둘 이상이면 양끝 맞춤된 산문 → 이어 붙임
    groups, g = [], []
    for i, a in enumerate(body):
        q = body[i - 1] if i else None
        if not a.get('verse'): g = []; continue
        if not g or q is None or not q.get('verse') or a['y0'] - q['y1'] > max(8.0, q['y1'] - q['y0']) * 1.2 or a['x0'] - q['x0'] >= 6:
            g = []; groups.append(g)
        g.append(a)
    for g in groups:
        base = min(a['x0'] for a in g); inner = g[:-1]
        if len(inner) >= 2:
            edge = max(a['x1'] for a in inner)
            if edge - base >= 225 and all(abs(a['x1'] - edge) <= 4 for a in inner):
                for a in g[1:]: a['qjoin'] = True
        # 묶음 안에서도: 앞 줄이 인용 산문 폭(왼쪽 끝 + 235~241)에서 꽉 차게 끝나면 이어 붙임
        for q, a in zip(g, g[1:]):
            if base + 235 <= q['x1'] <= base + 241 and not a.get('qjoin') and (n, round(q['y0'])) not in VERSE_KEEP:
                a['qjoin'] = True; JOINLOG.append((q['t'][-15:], a['t'][:12]))
    for a in body:
        t = a['t']
        if a['head']:
            if cur and cur.startswith('## ') and prev is not None and prev['head'] and a['y0'] - prev['y1'] < 12 and abs(a['sz'] - prev['sz']) < .8:
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
            hang = a['x0']  # 글머리 문단의 둘째 줄(내어쓰기)
        if a.get('verse') and prev.get('verse') and gap <= lh * 1.2 and a['x0'] - prev['x0'] >= 6:
            paras.append(cur); cur = t; verse = False  # 인용문 안의 들여 쓴 줄 = 새 문단
        elif a.get('verse') and prev.get('verse') and gap <= lh * 1.2 and prev['x0'] - a['x0'] < 12:
            if a.get('qjoin'):
                cur = cur + t  # 양끝 맞춤된 인용 산문: 꽉 찬 줄 다음은 이어 붙임
            else:
                cur = cur.rstrip() + '\n' + t; verse = True  # 게송 줄은 인쇄된 줄 그대로
        elif hang is not None and abs(a['x0'] - hang) < 2 and not mark and gap <= lh * 1.2:
            cur = (cur.rstrip() + '\n' + t) if pshort else cur + t
        elif 6 <= a['x0'] - left <= 10 and not a.get('verse'):
            paras.append(cur); cur = t; verse = False; hang = None  # 들여 쓴 줄 = 새 문단
        elif not mark and hang is None and prev['x0'] - a['x0'] > 5 and 5 <= prev['x0'] - left <= 12 and '\n' not in cur and gap <= lh * 1.2 and not pshort and abs(a['x0'] - left) < 3:
            cur = cur + t  # 들여 쓴 첫 줄 다음 줄
        elif gap > lh * 1.2 or (abs(a['sz'] - prev['sz']) > .8 and pshort) or mark or a['bold'] != prev['bold'] or abs(a['x0'] - prev['x0']) > 5:
            paras.append(cur); cur = t; verse = False; hang = None
        elif pshort:
            if verse or short or len(cur.split('\n')) == 1 and len(cur) < 60:
                cur = cur.rstrip() + '\n' + t; verse = True  # 게송·목록: 인쇄된 줄 그대로
            else:
                paras.append(cur); cur = t; verse = False  # 산문 문단 끝
        else:
            cur = cur + t
        prev = a
    if cur: paras.append(cur)
    return paras


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


def plain(a):
    return re.sub(r'\s+', ' ', a['t']).strip()


pages = []
for n in range(1, N + 1):
    cols = 512 <= n <= 527
    L = lines_of(n, cols)
    body = [a for a in L if not a['foot']]
    foot = [a for a in L if a['foot']]
    paras = body_paras(n, body) if not cols else []
    fns = []
    for num, txt in foot_items(n, foot):
        if num is None:  # 앞 쪽에서 넘어온 각주
            back = next((pp for pp in reversed(pages) if pp[2]), None)
            if back is None: print('?? 번호 없는 작은 글', n, txt[:40]); fns.append(txt); continue
            q = back[2][-1]
            back[2][-1] = (q.rstrip() + '\n' + txt.lstrip()) if re.search(r'[.)」』”]\s*$', q) else q + txt
            fixes.append(f'{n}쪽: 앞 쪽에서 넘어온 각주를 앞 각주에 이어 붙임')
            continue
        fns.append(f'[^{num}]: ' + txt)
    pages.append([n, paras, fns])
P = {p[0]: p for p in pages}

# ---- 쪽마다 손볼 곳 (인쇄된 모양 그대로) ----
for n in (1, 3):  # 속표지: 가장 큰 줄(책 제목)은 ^^, 나머지는 가운데
    ls = lines_of(n); big = max(a['sz'] for a in ls)
    P[n][1] = [('^^ ' if a['sz'] == big else ':: ') + plain(a) for a in ls]
P[2][1] = ['\n'.join(plain(a) for a in lines_of(2))]  # 판권지: 인쇄된 줄 그대로
P[4][1] = body_paras(4, lines_of(4), left=103.0, right=400.0)  # 일러두기
for n in range(10, 18):  # 차례: 인쇄된 줄 그대로 (항목 쪽)
    out = []
    for a in lines_of(n):
        t = plain(a)
        if a['head']: out.append('## ' + t); continue
        out.append(t)
    head = [x for x in out if x.startswith('## ')]
    rest = [x for x in out if not x.startswith('## ')]
    P[n][1] = head + (['\n'.join(rest)] if rest else [])
for n in OPENERS: P[n][1] = []  # 장 첫 쪽(그림으로 인쇄된 장 번호·제목) → 장 제목으로 보임
# 참고문헌 (508~511): 항목마다 한 줄, 넘친 줄은 이어 붙임
for n in range(508, 512):
    left, right = geom(n); out, block = [], []
    for a in lines_of(n):
        t = a['t']
        if a['head']:
            if block: out.append('\n'.join(block)); block = []
            out.append('## ' + t.strip()); continue
        if not block or a['x0'] <= left + 4 or t.lstrip().startswith(','):
            if t.lstrip().startswith(','): t = '———' + t.lstrip(); fixes.append(f'{n}쪽: 같은 지은이 표시(선)를 ——— 로')
            block.append(t)
        else:
            block[-1] = block[-1] + t.lstrip()
    if block: out.append('\n'.join(block))
    P[n][1] = out
# 찾아보기 (512~527): 두 단, 항목마다 한 줄, 넘친 줄은 이어 붙임
for n in range(512, 528):
    out, block = [], []
    for a in lines_of(n, True):
        t = a['t']
        if a['head']:
            if block: out.append('\n'.join(block)); block = []
            out.append('## ' + t.strip()); continue
        cl = 105.0 if a['col'] == 0 else 258.0
        if n % 2: cl += 3
        if not block or a['x0'] <= cl + 4:
            block.append(t)
        else:
            block[-1] = block[-1] + t.lstrip()
    if block: out.append('\n'.join(block))
    P[n][1] = out
# 528쪽 지은이·감수
P[528][1] = body_paras(528, lines_of(528), left=99.0, right=331.0)

body = ''
for n, ps, fns in pages:
    body += f'=== {n}쪽 ===\n' + '\n\n'.join(clean(x) for x in ps + fns if clean(x)) + '\n\n'
body = re.sub(r'\*\*( ?)\*\*', r'\1', body).rstrip() + '\n'

# ---- 목차: 차례(10~17쪽)에서 ----
nz = lambda x: re.sub(r'[^0-9A-Za-z가-힣一-龥]', '', x)
PG = {int(m.group(1)): m.group(2) for m in re.finditer(r'=== (\d+)쪽 ===\n(.*?)(?=\n=== |\Z)', body, re.S)}
items = []  # (단계, 제목, 쪽)
for n in range(10, 18):
    for a in lines_of(n):
        ss = [s for s in a['sp'] if s['text'].strip()]
        f = ss[0]['font']; t = plain(a)
        m = re.match(r'(.*?)\s+(\d+)$', t)
        if 'YDVYGOStd15' in f:  # 제N장  제목
            items.append((0, re.sub(r'\s+', ' ', t), None))
        elif 'YDVYMjOStd12' in f and ss[0]['size'] > 10 and m:  # 프롤로그_… / 에필로그_…
            items.append((0, m.group(1).replace('_', ' '), int(m.group(2))))
        elif 'NanumMyeongjo' in f and m:
            items.append((1, m.group(1), int(m.group(2))))
toc = [dict(title='속표지', page=1, sub=False), dict(title='판권지', page=2, sub=False), dict(title='속표지', page=3, sub=False),
       dict(title='일러두기', page=4, sub=False), dict(title='책을 펴내면서', page=5, sub=False), dict(title='차례', page=10, sub=False)]
ch = iter(OPENERS)
for lv, title, pg in items:
    if lv == 0 and pg is None: pg = next(ch)
    toc.append(dict(title=title, page=pg, sub=lv == 1))
toc += [dict(title='참고문헌', page=508, sub=False), dict(title='찾아보기', page=512, sub=False),
        dict(title='지은이', page=528, sub=False), dict(title='감수', page=528, sub=False)]
for e in toc:
    ps = [p for p in PG.get(e['page'], '').split('\n\n') if p.strip()]
    if not e['sub'] and e['title'] != '감수': continue  # 큰 항목은 쪽 맨 위에서 시작
    key = nz(e['title'])
    k = next((i for i, p in enumerate(ps) if p.startswith('## ') and (nz(p).startswith(key[:8]) or nz(p).endswith(key[-6:]))), None)
    if k is None and e['title'] == '감수': k = next(i for i, p in enumerate(ps) if '감수' in p)
    if k is None:
        if e['page'] > 3: print('  (소제목 없음)', e['title'], e['page'])
        continue
    if k > 0: e['at'] = re.sub(r'^## ', '', ps[k])[:12]
json.dump({'book': bk, 'edition': ED, 'toc': toc, 'images': [], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(N, '쪽', len(toc), '목차')
for f in dict.fromkeys(fixes): print('  ·', f)
if '--joins' in sys.argv:
    for j in JOINLOG: print('  이어 붙임:', j)
