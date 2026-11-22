"""『업과 윤회의 법칙』(DL-0034) 영어 원서 PDF → 원서 문단 목록 (운영자 요청, 2026-11-22)
  python3 tools/parallel/en_dl0034.py "The Workings of Kamma.pdf"  →  tools/out/parallel/DL-0034.en.paras.json
                                                                      + DL-0034.en.hyph.tsv (줄 끝 하이픈 판단 목록)

원서 판본 (판권 면 그대로): The Workings of Kamma, The Pa-Auk Tawya Sayadaw, © 2007 (published as a gift, in the public domain),
  'A GIFT – NOT FOR SALE' — Microsoft Word 문서를 PDF 로 바꾼 웹판(Workings of Kamma Web.doc, 504쪽, 612×792pt).
  쪽 번호가 인쇄되어 있지 않고, 차례의 쪽 번호가 PDF 쪽과 같음 → 쪽 이름 = PDF 쪽.
- 글꼴: 옛 빠알리 글꼴 글자 자리 → tools/parallel/pali_dl0034.py (글꼴마다·앞뒤 글자를 보고 바로잡음, 쪽 그림으로 확인):
  기울임(CC78) 5 ṁ · 8 ṇ · ; ṭ · = ḷ · > ṅ · H ṃ · D ḍ · M(; 앞) Ṭ / 보통(C630) 낱말 가운데 큰 글자 S ṇ · X ḍ · R ṭ · P ḷ · L ṅ · ] ṁ ·
  ṇ 뒤 D ḍ, 모두 큰 글자 낱말 속 e Ṅ · g Ṭ · f Ḷ / 인용(CE88) ; ṇ · < ḍ · J ṁ. 이 책은 ṁ(위 점)을 씀(lohitaṃ 한 곳만 아래 점).
- 본문 속 주 번호(보통 글꼴 9pt 숫자) → '[^N]'. 뒤쪽 ENDNOTES(PDF 371~504) → 'fn' 문단 '[^N]: 글'.
- 문단: 첫 줄 들여쓰기(왼쪽 여백 + 5~12pt) = 새 문단, 번호 항목 '1)'·'×'·'•' 줄도 새 문단, 항목의 매달린 줄(+14pt 넘게)은 이어 붙임,
  쪽이 넘어가도 들여쓰지 않은 첫 줄은 앞 문단에 이어 붙임. 모두 큰 글자 짧은 줄 = 소제목 'h', 장 제목(11pt) 아래 가운데
  '(‘Gaddula·Baddha·Sutta’)' 줄은 장 제목에 붙임. 게송(가운데 11pt 넘게 들여 쓴 줄)은 줄마다 줄 바꿈.
- 표(왼쪽 여백보다 40pt 넘게 들여 쓴 10pt 이하 줄, 점선 줄)는 'pq'(한국어판은 그림) — 쪽마다 따로 모아 그 쪽 끝에 둠(옆 본문 문단이 끊기지 않게).
- 앞쪽: 1 표지·2 판권 면(p), 3~19 차례·표 차례·번역어 목록(toc), 21 예경. 365~370 약어·출처 표는 'pq'.
"""
import sys, re, json, os, collections
import pymupdf
from wordfreq import zipf_frequency as zipf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pali_dl0034 import fixline

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
TOC = set(range(3, 20)); NOTES = set(range(371, d.page_count + 1)); ABBR = set(range(365, 371)); SKIP = {20, 22, 364}


def isref(txt, font, size, main):
    return re.fullmatch(r'\s*\d+(\s*/\s*\d+)?\s*', txt) and 'C630' in font and size <= 9.5 and main >= 8.5


def tabregions(pg):
    """표 자리: 선·칸 그림(25pt 넘는 것)을 겹치는 것끼리 묶은 네모 — 장 제목 띠(큰 글자 제목·괄호 부제만 든 것)는 뺌 (2026-11-22)"""
    cl = []
    for x in pg.get_drawings():
        r = x['rect']
        if r.width <= 25 and r.height <= 25: continue
        r = pymupdf.Rect(r.x0 - 4, r.y0 - 4, r.x1 + 4, r.y1 + 4); m = True
        while m:
            m = False
            for c in cl:
                if c.intersects(r): r |= c; cl.remove(c); m = True; break
        cl.append(r)
    out = []
    for c in cl:
        if c.width <= 60 or c.height <= 30: continue
        ls = [l for b in pg.get_text('dict')['blocks'] for l in b.get('lines', []) if ''.join(s['text'] for s in l['spans']).strip()
              and (c & pymupdf.Rect(l['bbox'])).get_area() > 0.6 * pymupdf.Rect(l['bbox']).get_area()]
        tt = [''.join(s['text'] for s in l['spans']).strip() for l in ls]
        if tt and all(t.startswith('(') or (t.upper() == t and max(s['size'] for s in l['spans']) >= 10.9) for t, l in zip(tt, ls)): continue
        out.append(c)
    return out


TABBOX = {131: (195, 412), 357: (40, 130)}   # 선 없는 표: 131쪽 쓸데없는 이야기 세 단 목록, 357쪽 빠알리 철자 표 (쪽 그림으로 확인)
LINES = []
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    TR = tabregions(d[i]) if pn not in TOC and pn not in NOTES else []
    for b in d[i].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['chars']]
            raw = ''.join(c['c'] for s in sp for c in s['chars'])
            if not raw.strip(): continue
            ne = [s for s in sp if ''.join(c['c'] for c in s['chars']).strip()]
            main = max(s['size'] for s in ne)
            # 주 번호 자리 표시: 글자 목록에서 9pt 숫자 조각을 '\x01숫자\x02' 로
            chars = []; first = True
            for s in sp:
                st = ''.join(c['c'] for c in s['chars'])
                if pn not in NOTES and pn not in TOC and isref(st, s['font'], s['size'], main) and not (first and pn in NOTES):
                    chars += [('\x01', s['font'])] + [(c, s['font']) for c in st.strip()] + [('\x02', s['font'])]
                else:
                    chars += [(c['c'], s['font']) for c in s['chars']]
                if st.strip(): first = False
            t = fixline(chars)
            lead = ''.join(c['c'] for c in ne[0]['chars']).strip()
            LINES.append({'pn': pn, 'bb': list(l['bbox']), 't': t, 'font': ne[0]['font'], 'size': round(ne[0]['size'], 1), 'main': main,
                          'lead': lead, 'leadsz': ne[0]['size'], 'dots': '....' in raw, 'raw': raw,
                          'tabbox': pn in TABBOX and TABBOX[pn][0] <= l['bbox'][1] <= TABBOX[pn][1],
                          'intab': any((r & pymupdf.Rect(l['bbox'])).get_area() > 0.6 * pymupdf.Rect(l['bbox']).get_area() for r in TR) or tuple(l['dir']) != (1.0, 0.0)})

# 줄 끝 하이픈 판단용 낱말 수
W = collections.Counter()
for x in LINES:
    for w in re.findall(r"[A-Za-zĀāĪīŪūṁṃṅñṭḍṇḷṄÑṬḌṆḶ’'-]+", x['t'])[:-1]: W[w.lower().strip("’'")] += 1
PREF = ('self', 'non', 'well', 'ill', 'co', 'semi', 'half', 'all', 'ever', 'over', 'under', 'fore', 'pre', 'post', 'anti', 'quasi', 'pseudo', 'ex', 'counter', 're')
HY = []
LET = "A-Za-zĀāĪīŪūṁṃṅñṭḍṇḷ’'"


def join(a, b, pg):
    if not a: return b
    m = re.search(r"([%s]+)-$" % LET, a)
    if m and re.match(r'[a-zāīūṁṃṅñṭḍṇḷ]', b):
        w2 = re.match(r"[%s]+" % LET, b).group(0)
        whole, hyph = (m.group(1) + w2).lower(), (m.group(1) + '-' + w2).lower()
        zw, z1, z2 = zipf(whole, 'en'), zipf(m.group(1).lower(), 'en'), zipf(w2.lower(), 'en')
        if w2.lower() in ('ness', 'ment', 'ments', 'ing', 'ed', 'ly', 'tion', 'tions', 'ful', 'less'): HY.append((pg, m.group(1) + w2, '붙임', W[hyph], W[whole])); return a[:-1] + b
        pali = bool(re.search(r'[·āīūṁṃṅñṭḍṇḷ]', a[-12:] + w2))
        if W[hyph] > W[whole] or (not pali and W[hyph] == W[whole] == 0 and zw < 1.5 and (m.group(1).lower() in PREF or (z1 >= 3 and z2 >= 3))):
            HY.append((pg, m.group(1) + '-' + w2, '하이픈 남김', W[hyph], W[whole])); return a + b
        HY.append((pg, m.group(1) + w2, '붙임', W[hyph], W[whole])); return a[:-1] + b
    if a.endswith('-') and b.startswith('·'): HY.append((pg, a.split()[-1] + b.split()[0], '붙임(·)', 0, 0)); return a[:-1] + b   # 'diṭṭha-' + '·dhamma'
    if a.endswith('-') or a.endswith('—') or a.endswith('·'): return a + b
    return a + ' ' + b


def caps(t):
    t2 = re.sub(r'\x01[^\x02]*\x02', '', t).replace('KAhhAMUhiA', 'KAṆṆAMUṆḌA')
    letters = re.sub(r'[^A-Za-zĀĪŪÑṄṬḌṆḶṀāīūñṅṭḍṇḷṁ]', '', t2)
    return len(letters) >= 3 and not any(c.islower() for c in letters)


paras = []; cur = None; prev = None
bypage = collections.defaultdict(list)
for x in LINES: bypage[x['pn']].append(x)
for pn in sorted(bypage):
    L = sorted(bypage[pn], key=lambda x: (round(x['bb'][1]), x['bb'][0]))
    body = [x for x in L if x['main'] >= 11 and x['bb'][2] - x['bb'][0] > 250]
    margin = (140 if pn % 2 else 119) if pn >= 23 else min((x['bb'][0] for x in body), default=140)   # 본문 왼쪽 여백: 홀수 쪽 140 · 짝수 쪽 119 (목록만 있는 쪽에서 여백을 잘못 잡던 것)
    pg = str(pn)
    tables = []
    for x in L:
        t = re.sub(r'[ \t ]+', ' ', x['t']).strip()
        bb, sz = x['bb'], x['size']
        x0 = bb[0]; x['m'] = margin
        newpage = prev is None or prev['pn'] != pn
        gap = bb[1] - prev['bb'][1] if prev is not None and not newpage else 0   # 쪽이 바뀌면 줄 사이는 보지 않음 (들여쓰기로 판단)
        if pn in TOC:
            t = re.sub(r'\s*\.{3,}\s*\S*\s*$', '', t).strip()
            if t and t.lower() != 'page': cur = {'pg': pg, 'k': 'toc', 't': t}; paras.append(cur)
            prev = x; continue
        if pn in NOTES:
            if t == 'ENDNOTES': prev = x; continue
            m = re.match(r'(\d+)\s*(.*)', t)
            nexp = int(re.match(r'\[\^(\d+)', cur['t']).group(1)) + 1 if cur is not None and cur['k'] == 'fn' else 1
            if m and x0 < margin + 5 and (x['leadsz'] <= 9.5 or int(m.group(1)) == nexp) and re.fullmatch(r'\d+', x['lead'][:len(m.group(1))]):
                cur = {'pg': pg, 'k': 'fn', 't': f'[^{m.group(1)}]: {m.group(2)}'}; paras.append(cur)
            elif cur is not None: cur['t'] = join(cur['t'], t, pg)
            prev = x; continue
        if pn in ABBR:
            tables.append(t); prev = x; continue
        # 장 제목 아래 가운데 빠알리 부제
        if cur is not None and cur.get('big') and x0 > margin + 40 and t.startswith('(') and gap < 25 and not newpage:
            cur['t'] += ' ' + t; prev = x; continue
        is_table = (x['dots'] or (x['main'] <= 10.5 and x0 > margin + 40)) and not caps(t) and pn not in (1, 2, 21)
        if x['intab'] and not (caps(t) and x['main'] >= 10.9) and pn not in (1, 2, 21): is_table = True
        if x['tabbox']: is_table = True
        if (re.match(r'^\d[a-g]?: [A-Z]', t) and x['main'] <= 10.5) or re.search(r'[⇓⇒]', t): is_table = True   # 표 제목 줄 ('5a: Death & Rebirth', '4: The Twenty-Eight…')
        if is_table or (x['main'] <= 10.5 and x0 > margin + 40 and caps(t) and x['dots']):
            tables.append(t); continue                       # prev 는 그대로 — 옆 본문 문단이 이어지게
        if caps(t) and len(t) < 90 and pn not in (1, 21) and (x['main'] <= 11.5):
            big = x['main'] >= 10.9 and x0 > margin + 40
            if cur is not None and cur['k'] == 'h' and not newpage and gap < 16 and not cur.get('big'):
                cur['t'] += ' ' + t
            else:
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
                if big: cur['big'] = 1
            prev = x; continue
        verse = x0 > margin + 40 and x['main'] >= 10.9 and not (cur is not None and cur.get('lx') is not None and x0 > cur['lx'] + 4 and not newpage)
        if verse:
            if cur is not None and cur.get('v') and not newpage and gap <= 16: cur['t'] += '\n' + t
            else: cur = {'pg': pg, 'k': 'p', 't': t, 'v': 1}; paras.append(cur)
            prev = x; continue
        listy = bool(re.match(r'(\d+(-\d+)?\)|\[\d+\]|[×•→]|\([a-z]\)|[a-z]\)|[ivx]+\))\s', t)) or t[:1] in '×•'
        indent = margin + 4 < x0 <= margin + 12.5
        if prev is not None and cur is not None and cur['k'] == 'p' and abs((prev['bb'][0] - prev.get('m', margin)) - (x0 - margin)) < 2 and x0 > margin + 4 and x['main'] <= 11.4 and prev['main'] <= 11.4:
            indent = prev['bb'][2] - prev['bb'][0] < 290      # 11pt 로 들여 쓴 인용 묶음(64쪽 126pt) 안 — 앞 줄과 같은 자리면 이어짐, 앞 줄이 짧게 끝났으면 새 문단
        elif prev is not None and not newpage and cur is not None and cur['k'] == 'p' and abs(prev['bb'][0] - x0) < 1.5 and prev['bb'][2] - prev['bb'][0] > 290:
            indent = False      # 앞 줄과 같은 자리에서 시작하고 앞 줄이 끝까지 찼으면 이어짐 (53쪽 '…(kusala' / 'cetanā)')
        hang = x0 > margin + 12.5
        if cur is not None and cur.get('lx') is not None and not listy and x0 > cur['lx'] + 4 and gap <= 22 and not newpage:
            indent = False      # 번호 항목의 매달린 줄 (항목 글자 자리에 맞춰 들여 씀 — 87·101·146·148쪽)
        if cur is None or cur['k'] != 'p' or cur.get('v') or listy or (indent and not hang) or gap > 22 or (newpage and indent):
            cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
            if listy: cur['lx'] = x0
        elif prev is not None and prev['bb'][2] - prev['bb'][0] < 25 and not newpage and not prev['raw'].rstrip().endswith('-'):
            cur['t'] += ('' if not prev['raw'].endswith(' ') else ' ') + t   # 표 옆 좁은 단에 한두 글자씩 찍힌 본문 (75쪽 'T/h/e /re/s/ul…', 78쪽)
        else:
            cur['t'] = join(cur['t'], t, pg)
        prev = x
    for t in tables:
        if t: paras.append({'pg': pg, 'k': 'pq', 't': t, 'tab': 1})
# 표 줄은 쪽마다 하나로
out = []
for p in paras:
    if p.get('tab') and out and out[-1].get('tab') and out[-1]['pg'] == p['pg']: out[-1]['t'] += '\n' + p['t']; continue
    out.append(p)
paras = out
for p in paras:
    p['t'] = re.sub(r'\x01\s*([\d/ ]+?)\s*\x02', lambda m: ''.join(f'[^{n.strip()}]' for n in m.group(1).split('/')), p['t'])
    p['t'] = re.sub(r'[\x01\x02]', '', p['t'])
    p['t'] = re.sub(r' {2,}', ' ', p['t']).strip()
    # 글꼴 글자 바로잡기 규칙이 놓친 곳 (쪽 그림으로 확인, 2026-11-22): Aṅgulimāla·Aṅga, Āḷāra, ḍḍ, 제목 KAṆṆAMUṆḌA, 굵은 인용 글꼴의 Saṅgha
    for a, b in (('ALg', 'Aṅg'), ('ĀPār', 'Āḷār'), ('DDh', 'ḍḍh'), ('iDDa', 'iḍḍa'), ('KAhhAMUhiA', 'KAṆṆAMUṆḌA'), ('SaKgha', 'Saṅgha')): p['t'] = p['t'].replace(a, b)
    for k in ('big', 'v', 'tab', 'lx'): p.pop(k, None)
paras = [p for p in paras if p['t']]
o = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(o, exist_ok=True)
json.dump(paras, open(os.path.join(o, 'DL-0034.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
with open(os.path.join(o, 'DL-0034.en.hyph.tsv'), 'w') as f:
    f.write('쪽\t낱말\t판단\t하이픈 꼴 수\t붙인 꼴 수\n')
    for r in HY: f.write('\t'.join(map(str, r)) + '\n')
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)), '하이픈', collections.Counter(r[2] for r in HY))
