"""『보시』(DL-0019) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0019.py wh367_Bodhi_Dana--The-Practice-of-Giving.pdf  →  tools/out/parallel/DL-0019.en.paras.json

원서 판본 (판권 면 그대로): DĀNA — The Practice of Giving, Selected Essays, Edited by Bhikkhu Bodhi,
  Buddhist Publication Society, Kandy • Sri Lanka, The Wheel Publication No. 367–9,
  First published in 1990, Second Edition 2003, Reprinted 2005, BPS Online Edition © (2011)
  (calibre 로 만든 PDF 86쪽, PDF 쪽 = 쪽 이름 — 쪽 아래 LiberationSerif 숫자)
- 문단: 들여쓰기 없는 조판 — 줄 사이(위 끝 차이)가 22pt 넘게 벌어지면 새 문단(같은 문단 안 18.7pt, 문단 사이 25.9pt).
  왼쪽 자리가 바뀌면(18pt 본문 ↔ 46.8pt 들여 쓴 인용·게송·번호 항목) 새 문단, 번호 항목('1. ')의 둘째 줄부터는 이어 붙임.
  쪽이 넘어갈 때는 앞 문단이 문장 끝으로 끝나지 않았거나 앞 쪽 마지막 줄이 오른쪽 끝 가까이(370pt 넘게) 찼으면 이어 붙임
  (58→59쪽 'Sakka spoke…', 68→69쪽 'Invariably he gives…' — 한국어판도 한 문단).
- 장 제목(Tahoma 25.2, 두 줄이면 합침)·지은이 줄(Tahoma 21.6)·소제목(Tahoma 15.8) → 'h'.
- 본문 속 주 번호 '[1]' → '[^1]'. 뒤쪽 Notes(82~84쪽, 'N. ' 로 시작) → 'fn' 문단 '[^N]: 글' (짝짓기에서 뺌, 각주 짝으로).
- 차례(4쪽) → 'toc'. 2쪽 속표지·판권 → 'h'/'p', 3쪽 이용 조건·5쪽 약어표·80~81쪽 About the Contributors(한국어판은 장마다 [^*] 각주) → 'pq'.
  1쪽(빈 쪽)·85쪽(BPS 안내)·86쪽(calibre 차례)은 넣지 않음.
- 글자는 PDF 그대로 — 줄 끝 '-' 는 빈칸 없이 붙임(전자판이 원래 하이픈 낱말에서만 줄을 바꿈), 줄 가운데 남은 '- '(abbhug- gacchatī 등)도 그대로, 겹친 빈칸은 하나로.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP = {1, 85, 86}
PQ = {3, 5, 80, 81}
TOC_PAGE = 4


def join(a, b):
    if not a: return b
    if re.search(r'[A-Za-zĀāĪīŪūṃṁṅñṭḍṇḷ]-$', a): return a + b
    return a + ' ' + b


def ends_sentence(t): return re.search(r'[.?!:”"’)\]]\s*$', t.strip()) is not None


paras = []; cur = None
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    pg = ''; L = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            raw = ''.join(s['text'] for s in sp)
            if not raw.strip(): continue
            ne = [s for s in sp if s['text'].strip()]
            f0, s0 = ne[0]['font'], round(ne[0]['size'], 1)
            if f0.startswith('LiberationSerif') and l['bbox'][1] > 560 and re.fullmatch(r'\s*\d+\s*', raw):
                pg = raw.strip(); continue
            L.append({'bb': list(l['bbox']), 't': raw, 'font': f0, 'size': s0})
    if not pg: pg = str(pn)
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
    prev = None; first = True
    for x in M:
        t = re.sub(r'[ \t ]+', ' ', x['t']).strip()
        t = re.sub(r'\s*\[(\d+)\]', lambda m: '[^' + m.group(1) + ']', t)
        bb = x['bb']
        if pn == TOC_PAGE:
            k = 'h' if x['font'].startswith('Tahoma') else 'toc'
            cur = {'pg': pg, 'k': k, 't': t}; paras.append(cur); prev = x; first = False; continue
        if x['font'].startswith('Tahoma') or x['font'].startswith('LiberationSerif-Bold'):
            if cur and cur['k'] == 'h' and cur['pg'] == pg and prev is not None and prev['font'] == x['font'] and x['size'] >= 25 and bb[1] - prev['bb'][1] < 40:
                cur['t'] = join(cur['t'], t)
            else:
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = x; first = False; continue
        kind = 'pq' if pn in PQ else 'p'
        # 뒤쪽 Notes: 'N. ' 로 시작하는 LiberationSans 줄 = 새 주
        if x['font'].startswith('LiberationSans') and pn >= 82:
            m = re.match(r'(\d+)\.\s*(.*)', t)
            cur = {'pg': pg, 'k': 'fn', 't': f'[^{m.group(1)}]: {m.group(2)}'}; paras.append(cur); prev = x; first = False; continue
        if pn >= 82 and cur and cur['k'] == 'fn':
            cur['t'] = join(cur['t'], t); prev = x; first = False; continue
        ind = bb[0] >= 40
        if first:
            cont = (cur is not None and cur['k'] == kind and (not ends_sentence(cur['t']) or cur.get('lastx', 0) >= 370) and (cur.get('ind') == ind or (ind and re.match(r'\d+\.\s', cur['t']) is not None)))
            newp = not cont
        else:
            gap = bb[1] - prev['bb'][1]
            pind = prev['bb'][0] >= 40
            numcont = ind and not pind and cur is not None and re.match(r'\d+\.\s', cur['t'] or '') is not None
            newp = cur is None or cur['k'] != kind or gap > 22 or (ind != pind and not numcont)
        if newp:
            cur = {'pg': pg, 'k': kind, 't': t, 'ind': ind}; paras.append(cur)
        else:
            cur['t'] = join(cur['t'], t)
            if cur.get('ind') is None: cur['ind'] = ind
        cur['lastx'] = bb[2]
        prev = x; first = False
for p in paras: p.pop('ind', None); p.pop('lastx', None)
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0019.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
