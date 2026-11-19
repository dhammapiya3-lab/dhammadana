"""『팔정도』(DL-0020) 영어 원서 PDF → 원서 문단 목록 (『보시』 en_dl0019.py 와 같은 BPS 온라인판 calibre 조판)
  python3 tools/parallel/en_dl0020.py wh308_Bodhi_Noble-Eightfold-Path.pdf  →  tools/out/parallel/DL-0020.en.paras.json

원서 판본 (판권 면 그대로): The Noble Eightfold Path — The Way to the End of Suffering, by Bhikkhu Bodhi,
  Buddhist Publication Society, Kandy • Sri Lanka, The Wheel Publication No. 308–311,
  First edition 1984, Second edition (revised) 1994, Reprinted 1999, 2006, Copyright © 1984, 1994 by Bhikkhu Bodhi
  (calibre 로 만든 PDF 169쪽, PDF 쪽 = 쪽 이름 — 쪽 아래 LiberationSerif 숫자)
- 이 책에만 있는 것: 31~32쪽 열 가지 불선업 표 — 오른쪽 묶음 이름(Bodily action (kāyakamma) 등, '}' 는 뺌)을 'h' 로
  그 묶음 첫 항목 앞에 둠(한국어판 '## 신업身業 kāyakamma' 처럼). 154~157쪽 Appendix 표(빠알리·영어 세 칸)는 'pq'
  (한국어판 부록 1 은 표라 짝짓지 않음). Recommended Reading 의 묶음 이름(굵은 글씨)은 'h', 책 줄은 'p'.
- 문단: 들여쓰기 없는 조판 — 줄 사이(위 끝 차이)가 22pt 넘게 벌어지면 새 문단(같은 문단 안 18.7pt, 문단 사이 25.9pt).
  왼쪽 자리가 바뀌면(18pt 본문 ↔ 46.8pt 들여 쓴 인용·게송·번호 항목) 새 문단, 번호 항목('1. ')의 둘째 줄부터는 이어 붙임.
  쪽이 넘어갈 때는 앞 문단이 문장 끝으로 끝나지 않았거나 앞 쪽 마지막 줄이 오른쪽 끝 가까이(370pt 넘게) 찼으면 이어 붙임
  (Recommended Reading 쪽에서는 줄이 차도 책 한 권씩 따로).
- 장 번호·장 제목(Tahoma 25.2)·소제목(Tahoma 18·15.8)은 'h' — 이어진 Tahoma 줄(40pt 안)은 한 제목으로 합침.
- 본문 속 주 번호 '[1]' → '[^1]'. 뒤쪽 Notes('N. ' 로 시작) → 'fn' 문단 '[^N]: 글' (짝짓기에서 뺌, 각주 짝으로).
- 차례(4쪽) → 'toc'(IV 의 둘째 줄은 이어 붙임). 2쪽 속표지·판권 → 'h'/'p', 2~3쪽 이용 조건·8쪽 약어표 → 'pq'.
  1쪽(빈 쪽)·167쪽(BPS 안내)·168~169쪽(calibre 차례)은 넣지 않음.
- 글자는 PDF 그대로 — 줄 끝 '-' 는 빈칸 없이 붙임(전자판이 원래 하이픈 낱말에서만 줄을 바꿈), 줄 가운데 남은 '- '(abbhug- gacchatī 등)도 그대로, 겹친 빈칸은 하나로.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP = {1} | set(range(167, 170))
PQ = {3, 8}
TBL = {31, 32}
APP = range(154, 158)
TOC_PAGE = 4


def join(a, b):
    if not a: return b
    if re.search(r'[A-Za-zĀāĪīŪūṃṁṅñṭḍṇḷ]-$', a): return a + b
    return a + ' ' + b


def ends_sentence(t): return re.search(r'[.?!:”"’)\]]\s*$', t.strip()) is not None


paras = []; cur = None; NOTES = False; lab = None; inapp = False
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    pg = ''; L = []; LB = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            raw = ''.join(s['text'] for s in sp)
            if not raw.strip(): continue
            ne = [s for s in sp if s['text'].strip()]
            f0, s0 = ne[0]['font'], round(ne[0]['size'], 1)
            if f0.startswith('LiberationSerif') and l['bbox'][1] > 560 and re.fullmatch(r'\s*\d+\s*', raw):
                pg = raw.strip(); continue
            if pn in TBL and l['bbox'][0] >= 270 and f0.startswith('URW'):   # 불선업 표 오른쪽 묶음 이름
                LB.append({'bb': list(l['bbox']), 't': raw.replace('}', ' ').strip()}); continue
            L.append({'bb': list(l['bbox']), 't': raw, 'font': f0, 'size': s0})
    if not pg: pg = str(pn)
    if pn in TBL:   # 불선업 표: 번호 줄(41pt)과 항목 글(86pt)을 가까운 높이끼리 '1. Destroying life' 한 줄로
        NUM = [x for x in L if 38 < x['bb'][0] < 60 and re.fullmatch(r'\s*\d+\.\s*', x['t'])]
        TX = [x for x in L if 80 < x['bb'][0] < 100]
        if NUM:
            for x in NUM + TX: L.remove(x)
            items = {id(n): [n] for n in NUM}
            for x in TX:
                n = min(NUM, key=lambda n: abs(n['bb'][1] - x['bb'][1])); items[id(n)].append(x)
            for n in NUM:
                g = items[id(n)]; ts = sorted(g[1:], key=lambda x: x['bb'][1])
                y0 = min(x['bb'][1] for x in g)
                L.append({'bb': [41.0, y0, max(x['bb'][2] for x in g), max(x['bb'][3] for x in g)], 't': n['t'].strip() + ' ' + ' '.join(x['t'].strip() for x in ts), 'font': n['font'], 'size': n['size'], 'item': 1})
    L.sort(key=lambda x: x['bb'][1])
    G = []
    for x in L:   # 같은 높이 조각(번호 '1. ' + 글)은 왼쪽부터 한 줄로
        if G and abs(G[-1][0]['bb'][1] - x['bb'][1]) < 2.5: G[-1].append(x)
        else: G.append([x])
    M = []
    for g in G:
        g.sort(key=lambda x: x['bb'][0]); y = dict(g[0]); y['bb'] = list(y['bb'])
        for x in g[1:]:
            y['t'] = y['t'] + ('' if y['t'][-1:].isspace() or x['t'][:1].isspace() else ' ') + x['t']
            y['bb'] = [min(y['bb'][0], x['bb'][0]), y['bb'][1], max(y['bb'][2], x['bb'][2]), max(y['bb'][3], x['bb'][3])]
        M.append(y)
    # 묶음 이름: 줄 사이 30pt 안은 한 묶음, 묶음 위 끝에서 20pt 위까지의 첫 항목 앞에 'h' 로
    LG = []
    for x in sorted(LB, key=lambda x: x['bb'][1]):
        if LG and x['bb'][1] - LG[-1]['y1'] < 30: LG[-1]['t'] += ' ' + x['t']; LG[-1]['y1'] = x['bb'][1]
        else: LG.append({'y0': x['bb'][1], 'y1': x['bb'][1], 't': x['t']})
    prev = None; first = True
    for x in M:
        while LG and (x['bb'][1] >= LG[0]['y0'] - 20 or LG[0]['t'].split()[0] in ('action',)) and re.match(r'\d+\.', x['t'].strip()):
            g = LG.pop(0)
            if g['t'].startswith('action') and lab is not None: lab['t'] = re.sub(r'\s+', ' ', lab['t'] + ' ' + g['t']).strip()
            else: lab = {'pg': pg, 'k': 'h', 't': re.sub(r'\s+', ' ', g['t']).strip()}; paras.append(lab); cur = lab
        t = re.sub(r'[ \t ]+', ' ', x['t']).strip()
        t = re.sub(r'\s*\[(\d+)\]', lambda m: '[^' + m.group(1) + ']', t)
        bb = x['bb']
        if pn == TOC_PAGE:
            if x['font'].startswith('URW') and cur and cur['k'] == 'toc': cur['t'] = join(cur['t'], t); prev = x; continue
            k = 'h' if x['font'].startswith('Tahoma') else 'toc'
            cur = {'pg': pg, 'k': k, 't': t}; paras.append(cur); prev = x; first = False; continue
        if x['font'].startswith('Tahoma') and t == 'Notes': NOTES = True
        if x['font'].startswith('Tahoma') and t == 'Recommended Reading': inapp = False
        if pn in APP and x['font'].startswith('Tahoma') and t == 'Appendix': inapp = True; cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur); prev = x; first = False; continue
        if inapp and not (x['font'].startswith('Tahoma') and x['size'] >= 18 and cur and cur['k'] == 'h'):
            cur = {'pg': pg, 'k': 'pq', 't': t}; paras.append(cur); prev = x; first = False; continue
        hb = x['font'].startswith('Tahoma') or (x['font'].startswith('URWPalladioITU-Bold') and pn > 150)
        if hb:
            if cur and cur['k'] == 'h' and prev is not None and (prev['font'] == x['font'] or prev['font'].startswith('Tahoma')) and 0 < bb[1] - prev['bb'][1] < 40:
                cur['t'] = join(cur['t'], t)
            else:
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = x; first = False; continue
        kind = 'pq' if pn in PQ or (pn == 2 and bb[1] > 500) else 'p'
        # 뒤쪽 Notes: 'N. ' 로 시작하는 LiberationSans 줄 = 새 주
        if NOTES and x['font'].startswith('LiberationSans') and bb[0] < 25 and re.match(r'\d+\.\s', t):
            m = re.match(r'(\d+)\.\s*(.*)', t)
            cur = {'pg': pg, 'k': 'fn', 't': f'[^{m.group(1)}]: {m.group(2)}'}; paras.append(cur); prev = x; first = False; continue
        if NOTES and cur and cur['k'] == 'fn':
            cur['t'] = join(cur['t'], t); prev = x; first = False; continue
        ind = bb[0] >= 40
        if first:
            cont = (cur is not None and cur['k'] == kind and (not ends_sentence(cur['t']) or (cur.get('lastx', 0) >= 370 and pn < 157)) and (cur.get('ind') == ind or (ind and re.match(r'\d+\.\s', cur['t']) is not None)))
            newp = not cont or bool(x.get('item'))
        else:
            gap = bb[1] - prev['bb'][1]
            pind = prev['bb'][0] >= 40
            numcont = ind and not pind and cur is not None and re.match(r'\d+\.\s', cur['t'] or '') is not None
            newp = cur is None or cur['k'] != kind or gap > 22 or (ind != pind and not numcont) or x.get('item')
        if newp:
            cur = {'pg': pg, 'k': kind, 't': t, 'ind': ind}; paras.append(cur)
        else:
            cur['t'] = join(cur['t'], t)
            if cur.get('ind') is None: cur['ind'] = ind
        cur['lastx'] = bb[2]
        prev = x; first = False
for p in paras: p.pop('ind', None); p.pop('lastx', None)
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0020.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
