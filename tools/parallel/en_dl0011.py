"""『법은 어디에나』(DL-0011) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0011.py Dhamma-Everywhere-V1.0.Ilustrated.pdf  →  tools/out/parallel/DL-0011.en.paras.json

원서 판본 (판권 면 그대로): Dhamma Everywhere: Welcoming Each Moment With Awareness+Wisdom, Ashin Tejaniya,
  Copyright © Ashin Tejaniya 2011, First Printing 6,000 copies, Jul 2011,
  This edition (3,000 copies, May 2012) published with permission for free distribution by Auspicious Affinity (Malaysia).
  (Adobe InDesign CS5, PDF 242쪽, PDF 쪽 = 인쇄 쪽 + 1 — 쪽 위 머리글의 숫자가 쪽 이름)
- 문단: 줄 사이가 17pt 넘게 벌어지면 새 문단(보통 줄 사이 15pt, 문단 사이 19.5pt), 글머리표(•)·큰 첫 글자도 새 문단.
  쪽이 넘어갈 때(오른쪽이 들쭉날쭉한 조판): 앞 쪽 마지막 줄이 문장 끝으로 끝나지 않았거나 오른쪽 끝 가까이 찼거나
  다음 쪽 첫 글자가 소문자면 이어 붙임.
- 제목: 장 제목(DejaVuSans 16·Candara-Bold 13)·소제목(DejaVuSansCondensed-Bold 9.5) → 'h'. 2쪽 속표지 → 'pq'(한국어판 속표지는 그림).
- 본문 사이 가운데 맞춤 인용(GentiumBasic-Italic 10, 위아래 줄 사이) → 'q' — 한국어판도 글(:: )로 있어 함께 짝지음.
- 사진 쪽의 글(DejaVuSansCondensed 10, 사진 위 흰 글씨 등) → 'pq' (짝짓기에서 뺌, 한국어판은 사진 그림 안에 있음).
- 구분 꾸밈(Davys '3', Century '***') → 'sep'. 'DAY 1' 옆 큰 회색 숫자(Dickens)는 꾸밈이라 뺌.
- 차례(10~12쪽, 두 단) → 'toc' 항목마다(두 줄로 나뉜 항목은 이어 붙임), 빠알리 용어 풀이(233쪽~) → 'gl' (term + 풀이).
- 1쪽(빈 쪽)·3쪽(판권 면)·241쪽(보시자 회향 글)·242쪽(뒤표지 저자 소개)은 넣지 않음.
- 글자는 PDF 그대로 — 탭은 빈칸, 줄 끝 보이지 않는 줄 나눔 표시(U+00AD)는 빼고 붙임, 큰 첫 글자는 다음 글에 붙임,
  Wingdings 글꼴의 'J'(웃는 얼굴로 인쇄됨, 9·113쪽)는 '☺'.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP_PAGES = {1, 3, 241, 242}
TOC_PAGES = {10, 11, 12}
GLOSS_FROM = 233
LET = r'[A-Za-zāīūṃṅñṭḍṇḷ]'


def stext(s):
    t = s['text'].replace('\t', ' ')
    if s['font'].startswith('Wingdings') and t.strip() == 'J': t = t.replace('J', '☺')
    return t


def ltext(spans):
    t = ''.join(stext(s) for s in spans)
    t = re.sub(r'\s+', ' ', t).strip()
    soft = t.endswith('\xad')
    t = t.replace('\xad', '')
    return t + ('\xad' if soft else '')


def join(a, b):
    if not a: return b
    if a.endswith('\xad'): return a[:-1] + b
    if re.search(LET + r'-$', a): return a + b
    return a + ' ' + b


paras = []; cur = None; last_full = False
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP_PAGES: continue
    pg = ''
    L = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            ne = [s for s in sp if s['text'].strip()]
            if not ne: continue
            if l['bbox'][1] < 50 and ne[0]['size'] <= 9:          # 쪽 머리글: 쪽 이름만
                m = re.findall(r'\d+', ''.join(s['text'] for s in sp)); pg = (m[0] if re.match(r'\s*\d', ''.join(s['text'] for s in sp)) else m[-1]) if m else pg
                continue
            if ne[0]['font'].startswith('Dickens'): continue
            L.append({'bb': list(l['bbox']), 'sp': sp, 'font': ne[0]['font'], 'size': round(max(s['size'] for s in ne), 1)})
    if not L: continue
    if not pg: pg = str(pn - 1)
    if pn in TOC_PAGES:   # 두 단: 왼쪽 단 위→아래, 오른쪽 단 위→아래
        L.sort(key=lambda r: (r['bb'][0] > 240, r['bb'][1]))
        for r in L:
            t = ltext(r['sp']).rstrip('\xad')
            if r['font'].startswith('DejaVuSans') and r['size'] >= 15: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur); continue
            if cur is not None and cur['k'] == 'toc' and not re.search(r',\s*\d+$', cur['t']) and not re.fullmatch(r'DAY \d+', cur['t']): cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'toc', 't': t}; paras.append(cur)
        last_full = False; continue
    # 같은 높이 조각(• + 글, 큰 첫 글자 옆, 용어 + 풀이)은 한 줄로
    L.sort(key=lambda r: (round(r['bb'][1]), r['bb'][0]))
    R = []
    for r in L:
        big = r['size'] > 30
        if R and not big and not R[-1].get('big') and abs(R[-1]['bb'][1] - r['bb'][1]) < 4:
            g = R[-1]; g['parts'].append(r); g['bb'] = [min(g['bb'][0], r['bb'][0]), min(g['bb'][1], r['bb'][1]), max(g['bb'][2], r['bb'][2]), max(g['bb'][3], r['bb'][3])]
        else: R.append({'bb': list(r['bb']), 'parts': [r], 'big': big})
    for g in R:
        g['parts'].sort(key=lambda r: r['bb'][0])
        main = [p for p in g['parts'] if not p['font'].startswith('SymbolMT')] or g['parts']
        g['font'] = main[0]['font']; g['size'] = main[0]['size']
        g['bullet'] = g['parts'][0]['font'].startswith('SymbolMT')
    # 큰 첫 글자 → 옆 첫 줄 앞에
    for g in R:
        if g['font'].startswith('LilithInitials'):
            g['skip'] = True
            nx = sorted([x for x in R if not x.get('skip') and x is not g and x['bb'][0] >= g['bb'][2] - 3 and g['bb'][1] - 2 <= x['bb'][1] <= g['bb'][3]], key=lambda x: x['bb'][1])
            if nx:
                nx[0]['drop'] = ltext(g['parts'][0]['sp'])
                for x in nx[1:]: x['dropcont'] = True
    rm = max((g['bb'][2] for g in R if g['font'].startswith('GentiumBasic') and g['size'] >= 10.5), default=410)
    prev = None; first = True; qprev = None
    for g in R:
        if g.get('skip'): continue
        f, sz, bb = g['font'], g['size'], g['bb']
        t = g.get('drop', '') + ltext([s for p in g['parts'] for s in p['sp']])
        if not t.strip('\xad '): continue
        if pn == 2:      # 속표지: 한국어판은 그림이라 'pq'(짝짓기에서 뺌)
            if cur and cur['k'] == 'pq' and cur['pg'] == pg and 'Ashin' not in t: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'pq', 't': t}; paras.append(cur)
            continue
        if f.startswith('Davys') or f.startswith('Century'):
            cur = {'pg': pg, 'k': 'sep', 't': t}; paras.append(cur); prev = None; first = False; continue
        if f == 'DejaVuSansCondensed' and sz == 10.0 or (f.startswith('DejaVuSans-Oblique')):      # 사진 쪽 글
            if cur is not None and cur['k'] == 'pq' and cur['pg'] == pg and prev is not None and bb[1] - prev[1] < 22: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'pq', 't': t}; paras.append(cur)
            prev = bb; continue
        if (f.startswith('DejaVuSans') and sz >= 15) or f.startswith('Candara') or f.startswith('Verdana') or (f.startswith('DejaVuSansCondensed-Bold') and 9 <= sz <= 9.6):
            if cur is not None and cur['k'] == 'h' and prev is not None and bb[1] - prev[1] < (26 if sz >= 15 else 20) and cur['pg'] == pg: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = bb; first = False; last_full = False; continue
        if pn >= GLOSS_FROM and sz <= 10.4 and len(R) and any(p['bb'][0] >= 150 for p in g['parts']) or (pn >= GLOSS_FROM and 'Italic' in f and bb[0] < 120 and sz <= 10.4):
            left = [s for p in g['parts'] if p['bb'][0] < 150 for s in p['sp']]
            right = [s for p in g['parts'] if p['bb'][0] >= 150 for s in p['sp']]
            tm, df = ltext(left).rstrip('\xad'), ltext(right)
            if tm or cur is None or cur['k'] != 'gl':
                cur = {'pg': pg, 'k': 'gl', 'term': tm, 'def': df}; paras.append(cur)
            elif prev is not None and bb[1] - prev[1] > 15.5:      # 풀이 안의 a) b) 항목·괄호 줄은 줄 사이가 벌어짐(보통 13pt, 항목 17.5pt)
                cur['def'] = cur['def'] + '\n' + df
            else: cur['def'] = join(cur['def'], df)
            prev = bb; first = False; continue
        if 'Italic' in f and abs(sz - 10.0) < 0.2 and pn < GLOSS_FROM:      # 가운데 맞춤 인용
            if cur is not None and cur['k'] == 'q' and prev is not None and bb[1] - prev[1] < 17: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'q', 't': t}; paras.append(cur)
            prev = bb; first = False; last_full = False; continue
        bullet = g['bullet']
        if pn == 4:      # 예경문: 빠알리 한 줄 / 영어 두 줄
            if cur is not None and cur['k'] == 'p' and cur['pg'] == pg and 'Bold' not in f and 'Bold' not in cur.get('f', ''): cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'p', 't': t, 'f': f}; paras.append(cur)
            prev = bb; first = False; last_full = False; continue
        if first:
            newp = cur is None or cur['k'] != 'p' or bullet or bool(g.get('drop')) or (not last_full and not t[:1].islower())
        else:
            gap = bb[1] - prev[1] if prev is not None else 99
            newp = cur is None or cur['k'] != 'p' or bullet or bool(g.get('drop')) or (gap > 17 and not g.get('dropcont'))
        if newp: cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
        else: cur['t'] = join(cur['t'], t)
        prev = bb; first = False
        last_full = not re.search(r'[.?!:”’…)]$', t.rstrip('\xad')) or bb[2] >= rm - 30
for p in paras:
    if p['k'] == 'gl': p['t'] = p['term'] + '\n' + p['def']
    p['t'] = p['t'].replace('\xad', ''); p.pop('f', None)
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0011.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
