"""『업과 윤회의 법칙』(DL-0034) 영어 원서 PDF (개정 2판, PAMC 2018) → 원서 문단 목록 (운영자 요청, 2026-11-22)
  python3 tools/parallel/en_dl0034_2018.py "1PAS-02-The-Workings-of-Kamma-2nd-Rev-Ed-pamc-032018.pdf"
      →  tools/out/parallel/DL-0034.en.paras.json + DL-0034.en.hyph.tsv (줄 끝 하이픈 판단 목록)

원서 판본 (판권 면 그대로): The Workings of Kamma (Second Revised Edition), The Pa-Auk Tawya Sayadaw,
  © 2009, 2012, 2017 'A GIFT ― NOT FOR SALE' (public domain), PDF by PAMC (Singapore) 03/2018 — Word 2010 PDF 422쪽.
  한국어판(정명 스님 옮김)이 옮긴 판. 예전 2007 웹판 도구는 en_dl0034.py (남겨 둠).
- 쪽 이름: 쪽 위 머리글의 인쇄 쪽 번호 = PDF 쪽 − 21 (앞쪽 PDF 1~21 은 PDF 쪽 그대로 'pN').
- 글꼴: 유니코드 Tahoma — 빠알리 글자 바로잡기 필요 없음. 겹낱말 점 '∙'(U+2219)·곧은 따옴표는 PDF 그대로.
  고르게 맞춘 줄은 낱말이 따로 찍혀 빈칸 글자가 없으므로 글자 사이가 벌어진 곳(글자 크기의 0.2배 넘게)에 빈칸을 넣음.
- 본문 10pt, 빠알리 풀이 8.4pt, 굵은 인용 8.3~8.5pt. 짝수 PDF 쪽 왼쪽 여백 58 · 들여쓰기 65, 홀수 쪽 36 · 43.
- 주 번호(6.5pt 숫자)는 둘 — 쪽 아래 각주(1~990, 쪽 아래 짧은 가로줄 밑)와 뒤쪽 미주(ENDNOTES, 책 전체 1~360,
  이 판은 기울임 숫자). 쪽 아래 각주 번호와 차례대로 맞는 것은 각주 '[^N]', 아니면 미주 '[^eN]', '10/3' 은 각주 10·미주 3.
  각주 → 'fn' 문단 '[^N]: 글'(쪽을 넘어가면 이어 붙임), 미주 → 'fn' 문단 '[^eN]: 글'.
- 작은 대문자 소제목(9/7pt)·장 제목(10/8pt, 아래 가운데 '(…Suttaṁ)' 줄을 붙임) → 'h'.
- 표(선·칸 그림 자리 안의 줄, 누운 글자) → 'pq' (한국어판은 그림) — 쪽마다 모아 그 쪽 끝에.
- 앞쪽 PDF 1~7 → 'p'(표지·판권·표지 그림 설명), 8~18 차례 → 'toc', 20 예경. 401~422(참고 문헌·출처·찾아보기)는 뺌.
"""
import sys, re, json, os, collections
import pymupdf
from wordfreq import zipf_frequency as zipf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
TOC = set(range(8, 19))
NOTES = set(range(41, 50)) | {57, 58} | set(range(255, 278)) | {324, 325} | set(range(372, 382)) | set(range(396, 401))
FRONT = set(range(1, 8))
SKIP = {19, 21} | set(range(401, d.page_count + 1))


def pname(pn):
    return str(pn - 21) if pn >= 22 else f'p{pn}'


def tabregions(pg):
    """표 자리: 선·칸 그림을 겹치는 것끼리 묶은 네모 가운데 안에 칸 선이 있는 것 — 테두리만 있는 글 상자(세로선 2·가로선 1,
    한국어판은 글로 옮김)는 뺌. 표 내용 대부분은 쪽 그림이고 글로 남은 것은 표 제목·칸 글자뿐 (2026-11-22)"""
    DR = [x for x in pg.get_drawings() if x['rect'].y1 >= 35 and not (x['rect'].height < 2 and x['rect'].x0 < 62 and (140 < x['rect'].width < 150 or 350 < x['rect'].width < 358))]
    cl = []
    for x in DR:
        r = x['rect']; r = pymupdf.Rect(r.x0 - 4, r.y0 - 4, r.x1 + 4, r.y1 + 4); m = True
        while m:
            m = False
            for c in cl:
                if c.intersects(r): r |= c; cl.remove(c); m = True; break
        cl.append(r)
    out = []
    for c in cl:
        if c.width <= 60 or c.height <= 30: continue
        vx = {round(x['rect'].x0 / 3) for x in DR if c.contains(x['rect']) and x['rect'].width < 2 and x['rect'].height > 2}
        hy = {round(x['rect'].y0 / 3) for x in DR if c.contains(x['rect']) and x['rect'].height < 2 and x['rect'].width > 2}
        if len(vx) <= 3 and len(hy) <= 1: continue
        out.append(c)
    return out


def fnsep(pg):
    """쪽 아래 각주 구분선: 왼쪽 여백에서 시작하는 짧은(144pt)·긴(353pt, 앞 쪽 각주가 이어질 때) 가로줄 — 그 밑 글이 모두 9pt 이하일 때"""
    dl = pg.get_text('dict')['blocks']
    for y in sorted(x['rect'].y0 for x in pg.get_drawings() if x['rect'].height < 2 and x['rect'].y0 > 60 and x['rect'].x0 < 62
                    and (140 < x['rect'].width < 150 or 350 < x['rect'].width < 358)):
        below = [s['size'] for b in dl for l in b.get('lines', []) if l['bbox'][1] > y for s in l['spans'] if s['text'].strip()]
        if below and max(below) <= 9.3: return y
    return None


def linetext(l):
    """글자 사이 자리로 빈칸을 되살리고, 6.5pt 숫자 조각은 \x01숫자\x02 로"""
    out = []; px = None; psz = 10
    for s in l['spans']:
        st = ''.join(c['c'] for c in s['chars'])
        if not st: continue
        isref = s['size'] < 7.2 and re.fullmatch(r'\s*\d+(\s*/\s*\d+)?\s*', st)
        chars = [{'c': '\x01' + st.strip() + '\x02', 'x0': s['chars'][0]['bbox'][0], 'x1': s['chars'][-1]['bbox'][2]}] if isref else \
                [{'c': c['c'], 'x0': c['bbox'][0], 'x1': c['bbox'][2]} for c in s['chars']]
        for c in chars:
            if out and not isref and c is chars[0] and out[-1][-1:] not in (' ', '(', '[', '‘', "'") and (c['c'] == '(' and re.match(r'[\w.,:;!?)\]\x02]', out[-1][-1:]) or (out[-1][-1:] == ')' and re.match(r'\w', c['c']))):
                out.append(' ')
            elif px is not None and c['x0'] - px > 0.2 * max(psz, s['size']) * (0.5 if isref else 1) and out and not out[-1].endswith(' ') and c['c'] not in ' ?.,;:!)]’' and not isref:
                out.append(' ')
            out.append(c['c']); px = c['x1']; psz = s['size'] if not isref else psz
    return ''.join(out)


W = collections.Counter(); HY = []
LET = "A-Za-zĀāĪīŪūṁṃṅñṭḍṇḷ’'"


def join(a, b, pg):
    if not a: return b
    m = re.search(r"([%s]+)-$" % LET, a)
    if m and re.match(r'[a-zāīūṁṃṅñṭḍṇḷ]', b):
        w2 = re.match(r"[%s]+" % LET, b).group(0)
        whole, hyph = (m.group(1) + w2).lower(), (m.group(1) + '-' + w2).lower()
        zw, z1, z2 = zipf(whole, 'en'), zipf(m.group(1).lower(), 'en'), zipf(w2.lower(), 'en')
        if w2.lower() in ('ness', 'ment', 'ments', 'ing', 'ed', 'ly', 'tion', 'tions', 'ful', 'less'): HY.append((pg, m.group(1) + w2, '붙임', W[hyph], W[whole])); return a[:-1] + b
        pali = bool(re.search(r'[∙āīūṁṃṅñṭḍṇḷ]', a[-12:] + w2))
        if W[hyph] > W[whole] or (not pali and W[hyph] == W[whole] == 0 and zw < 1.5 and (m.group(1).lower() in ('self', 'non', 'well', 'ill', 'co', 'semi', 'half', 'all', 'ever', 'over', 'under', 'fore', 'pre', 'post', 'anti', 're') or (z1 >= 3 and z2 >= 3))):
            HY.append((pg, m.group(1) + '-' + w2, '하이픈 남김', W[hyph], W[whole])); return a + b
        HY.append((pg, m.group(1) + w2, '붙임', W[hyph], W[whole])); return a[:-1] + b
    if a.endswith('-') and b.startswith('∙'): HY.append((pg, a.split()[-1] + b.split()[0], '붙임(∙)', 0, 0)); return a[:-1] + b
    if a.endswith(('-', '—', '―', '∙')): return a + b
    return a + ' ' + b


def caps(t):
    t2 = re.sub(r'\x01[^\x02]*\x02|\x03[^\x04]*\x04', '', t)
    letters = re.sub(r'[^A-Za-zĀĪŪÑṄṬḌṆḶṀāīūñṅṭḍṇḷṁ]', '', t2)
    return len(letters) >= 3 and not any(c.islower() for c in letters)


LINES = []
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    pg = d[i]
    TR = tabregions(pg) if pn not in TOC | NOTES | FRONT else []
    sep = fnsep(pg) if pn not in NOTES else None
    for b in pg.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            raw = ''.join(c['c'] for s in l['spans'] for c in s['chars'])
            if not raw.strip() or l['bbox'][1] < 33: continue
            ne = [s for s in l['spans'] if ''.join(c['c'] for c in s['chars']).strip()]
            nonref = [s for s in ne if s['size'] >= 7.2] or ne
            t = linetext(l)
            bb = list(l['bbox'])
            rect = pymupdf.Rect(bb)
            LINES.append({'pn': pn, 'bb': bb, 't': t, 'raw': raw, 'main': max(s['size'] for s in nonref),
                          'bold': sum(len(s['chars']) for s in nonref if 'Bold' in s['font']) > sum(len(s['chars']) for s in nonref if 'Bold' not in s['font']),
                          'lead': ''.join(c['c'] for c in ne[0]['chars']).strip(), 'leadsz': ne[0]['size'],
                          'fn': sep is not None and bb[1] > sep - 2,
                          'intab': any((r & rect).get_area() > 0.6 * rect.get_area() for r in TR) or tuple(l['dir']) != (1.0, 0.0)})
for x in LINES:
    for w in re.findall(r"[A-Za-zĀāĪīŪūṁṃṅñṭḍṇḷ'-]+", x['t'])[:-1]: W[w.lower().strip("'")] += 1

paras = []; cur = None; prev = None; curfn = None
bypage = collections.defaultdict(list)
for x in LINES: bypage[x['pn']].append(x)
for pn in sorted(bypage):
    L0 = sorted(bypage[pn], key=lambda x: x['bb'][1]); L = []
    for x in L0:     # 같은 높이(3pt 안)에 있는 줄은 왼쪽부터 ('xxx5)' 번호 줄이 글 줄보다 2pt 낮게 찍힌 곳, 360쪽)
        if L and abs(x['bb'][1] - L[-1][-1]['bb'][1]) <= 3: L[-1].append(x)
        else: L.append([x])
    L = [y for g in L for y in sorted(g, key=lambda z: z['bb'][0])]
    margin = 58 if pn % 2 == 0 else 36
    pg = pname(pn)
    tables = []
    # 이 쪽 각주 번호들 (각주 줄 첫머리 6.5pt 숫자) — 본문 번호가 이 쪽에 있어도 각주 글은 다음 쪽에 찍힌 것이 있어(27→28쪽 각주 32) 다음 쪽 것도 함께
    def fnnums(q): return [int(x['lead']) for x in bypage.get(q, []) if x['fn'] and x['leadsz'] < 7.2 and re.fullmatch(r'\d+', x['lead'])]
    REM = set(fnnums(pn)) | set(fnnums(pn + 1)[:3])

    def refsub(t):
        def one(n):
            if n in REM or n > 360: REM.discard(n); return f'\x03^{n}\x04'   # 미주는 360 까지
            return f'\x03^e{n}\x04'
        def r(m):
            out = []
            for part in m.group(1).replace(' ', '').split('/'):
                n = int(part)
                if n not in REM and len(part) > 2:      # '8160' = 각주 81 + 미주 60 (빗금 없이 붙어 찍힘, 54쪽)
                    for k in range(1, len(part)):
                        if int(part[:k]) in REM: out.append(one(int(part[:k]))); n = int(part[k:]); break
                out.append(one(n))
            return ''.join(out)
        return re.sub(r'\x01([^\x02]*)\x02', r, t)

    pend = ''
    for x in L:
        t = re.sub(r'[ \t ]+', ' ', x['t']).strip()
        if re.fullmatch(r'xxx[\d-]+\)', t): pend = t + ' '; continue      # 표 풀이 상자의 번호 'xxx5)' 만 따로 찍힌 줄 → 다음 줄 앞에 (360쪽)
        if pend: t = pend + t; pend = ''; x = dict(x, bb=[x['bb'][0] - 32] + x['bb'][1:])
        bb = x['bb']; x0 = bb[0]
        newpage = prev is None or prev['pn'] != pn
        jump = prev is not None and pn - prev['pn'] > 1      # 사이에 그림만 있는 쪽이 끼면 문단이 이어지지 않음 (361쪽 표 1e 풀이)
        gap = bb[1] - prev['bb'][1] if prev is not None and not newpage else 0
        if pn in TOC:
            t = re.sub(r'\x01[^\x02]*\x02', '', t)
            if t.lower() in ('page', 'contents'): continue
            if t == '(Contents in Detail)': t = 'CONTENTS IN DETAIL'
            if t == 'Tables' and x['bb'][1] < 45: t = 'TABLES'
            has = bool(re.search(r'\.\s?\.\s?\.', t)) or bool(re.search(r'\s\d+\s*$', t))
            t = re.sub(r'(\s*\.\s?){3,}.*$', '', t).strip()
            t = re.sub(r'\s+\d+\s*$', '', t).strip(); t = re.sub(r'\s+\.$', '', t)
            if cur is not None and cur['k'] == 'toc' and cur.get('open'): cur['t'] += ' ' + t
            else: cur = {'pg': pg, 'k': 'toc', 't': t}; paras.append(cur)
            cur['open'] = not has and not caps(t) and not t in ('TABLES', 'CONTENTS IN DETAIL')
            prev = x; continue
        if pn in NOTES or x['fn']:
            t = re.sub(r'\x01([^\x02]*)\x02', r'\1 ', t, count=1).strip(); t = re.sub(r'\x01([^\x02]*)\x02', r'[^e\1]', t)
        if pn in NOTES:
            if 'NDNOTES' in t or t.startswith('(SUTTA REFERENCES') or t.startswith('(S'):
                if caps(t): prev = x; continue
            m = re.match(r'(\d+)\s*(.*)', t)
            if m and x['leadsz'] < 7.2 and x0 < margin + 5 and x['lead'] == m.group(1):
                n = int(m.group(1))
                if cur is not None and cur['k'] == 'fn' and cur['t'].startswith(f'[^e{n}]:'): n += 1   # 원서 오식: 미주 287 이 '286' 으로 두 번 찍힘 (PDF 375쪽) — 본문 번호 287 에 맞춤
                cur = {'pg': pg, 'k': 'fn', 't': f'[^e{n}]: {m.group(2)}'}; paras.append(cur)
            elif cur is not None and cur['k'] == 'fn': cur['t'] = join(cur['t'], t, pg)
            else: cur = {'pg': pg, 'k': 'pq', 't': t}; paras.append(cur)
            prev = x; continue
        if x['fn']:
            m = re.match(r'(\d+)\s*(.*)', t)
            if m and x['leadsz'] < 7.2 and x['lead'] == m.group(1):
                curfn = {'pg': pg, 'k': 'fn', 't': f'[^{m.group(1)}]: {m.group(2)}'}; paras.append(curfn)
            elif curfn is not None: curfn['t'] = join(curfn['t'], t, pg)
            continue                                            # prev 는 그대로 — 다음 쪽 본문이 이어지게
        t = refsub(t)
        if pn in (1, 2, 3, 4, 5, 6, 20) or 'G I F T' in t: tables.append(t); continue   # 표지·책 소개·인용 모음·후원금 알림·예경(한국어판에 없음) → pq
        if pn in FRONT or pn == 20:
            if cur is not None and cur['k'] == 'p' and cur['pg'] == pg and gap < 16 and pn != 20 and not t.startswith('•'): cur['t'] = join(cur['t'], t, pg)
            else: cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
            prev = x; continue
        if x['intab'] or re.match(r'^(Table )?\d+[a-g]?: [A-Z]', t) and x['main'] <= 9.5:
            tables.append(t); continue
        # 장 제목 아래 가운데 빠알리 부제
        if cur is not None and cur.get('big') and t.startswith('(') and gap < 20 and not newpage:
            cur['t'] += ' ' + t; prev = x; continue
        if caps(t) and len(t) < 110 and x['main'] <= 10.5:
            big = x['main'] >= 9.9 and x0 > margin + 30
            if cur is not None and cur['k'] == 'h' and not newpage and gap < 15 and not cur.get('big'): cur['t'] += ' ' + t
            else:
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
                if big: cur['big'] = 1
            prev = x; continue
        listy = bool(re.match(r'(xxx[\d-]+\)|\d+(-\d+)?\)\.?|\[\d+\]|[×•→✓]|\([a-z]\)|[a-z]\)|[ivx]+\))\s', t)) or t[:1] in '×•'
        indent = margin + 4 < x0 <= margin + 10
        hang = x0 > margin + 10
        if cur is not None and cur.get('lx') is not None and not listy and x0 - margin > cur['lx'] + 4 and gap <= 18 and not jump:   # 쪽이 넘어가도 (여백 기준)
            indent = False; hang = False                      # 번호 항목의 매달린 줄
        verse = hang and not (cur is not None and cur.get('lx') is not None and x0 - margin > cur['lx'] + 4 and not jump)
        if verse:
            if cur is not None and cur.get('v') and not jump and (gap <= 15 or newpage) and abs(x0 - margin - cur['vx']) < 40: cur['t'] += '\n' + t
            else: cur = {'pg': pg, 'k': 'p', 't': t, 'v': 1, 'vx': x0 - margin}; paras.append(cur)
            prev = x; continue
        boldchg = cur is not None and cur['k'] == 'p' and prev is not None and prev['bold'] != x['bold'] and not newpage and re.search(r'[.:;?!\'’"…]\s*$', prev['raw']) is not None and not (cur.get('lx') is not None and x0 - margin > cur['lx'] + 4)
        if cur is None or cur['k'] != 'p' or cur.get('v') or listy or indent or gap > 18 or boldchg or jump or (pn in (382, 383) and prev is not None and prev['bb'][2] - prev['bb'][0] < 320):   # 부록 1 목록은 줄마다
            cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
            if listy: cur['lx'] = x0 - margin
        else:
            cur['t'] = join(cur['t'], t, pg)
        prev = x
    for t in tables:
        if t: paras.append({'pg': pg, 'k': 'pq', 't': t, 'tab': 1})

out = []
for p in paras:
    if p.get('tab') and out and out[-1].get('tab') and out[-1]['pg'] == p['pg']: out[-1]['t'] += '\n' + p['t']; continue
    out.append(p)
paras = out
for p in paras:
    p['t'] = re.sub(r'\x01\s*([\d/ ]+?)\s*\x02', lambda m: ''.join(f'[^e{n.strip()}]' for n in m.group(1).split('/')), p['t'])
    p['t'] = p['t'].replace('\x03', '[').replace('\x04', ']')
    p['t'] = re.sub(r'[\x01\x02]', '', p['t'])
    p['t'] = re.sub(r' {2,}', ' ', p['t']).strip()
    for k in ('big', 'v', 'vx', 'tab', 'lx', 'open'): p.pop(k, None)
paras = [p for p in paras if p['t']]
# 각주·미주 문단을 처음 가리키는 본문 문단 바로 뒤로 (가리키는 차례대로) — 한국어판은 미주를 그 자리 각주로 옮겼으므로 각주 짝짓기(순서 지킴)가 맞게.
# 화면에서 원서 각주는 본문의 [^n] 을 눌러 보므로 자리를 옮겨도 보이는 곳은 같음 (2026-11-22)
FNP = {re.match(r'\[\^([^\]]+)\]:', p['t']).group(1): p for p in paras if p['k'] == 'fn'}
used = set(); out = []
for p in paras:
    if p['k'] == 'fn': continue
    out.append(p)
    for r in re.findall(r'\[\^([^\]]+)\](?!:)', p['t']):
        if r in FNP and r not in used: used.add(r); out.append(FNP[r])
rest = [p for k, p in FNP.items() if k not in used]
for p in rest:      # 가리키는 곳이 없는 각주는 원래 자리(같은 쪽 끝)에
    k = max((i for i, q in enumerate(out) if q['pg'] == p['pg']), default=len(out) - 1); out.insert(k + 1, p)
print('가리키는 곳이 없는 각주·미주:', [re.match(r'\[\^([^\]]+)\]', p['t']).group(1) for p in rest])
paras = out
o = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(o, exist_ok=True)
json.dump(paras, open(os.path.join(o, 'DL-0034.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
with open(os.path.join(o, 'DL-0034.en.hyph.tsv'), 'w') as f:
    f.write('쪽\t낱말\t판단\t하이픈 꼴 수\t붙인 꼴 수\n')
    for r in HY: f.write('\t'.join(map(str, r)) + '\n')
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)), '하이픈', collections.Counter(r[2] for r in HY))
