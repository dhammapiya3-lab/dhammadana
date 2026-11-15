"""『번뇌를 가볍게 여기지 마십시오』(DL-0013) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0013.py Defilements_V1.1.pdf  →  tools/out/parallel/DL-0013.en.paras.json

원서 판본 (판권 면 그대로): Don't Look Down on The Defilement(s) — They Will Laugh At You, Ashin Tejaniya,
  Copyright © Ashin Tejaniya 2006, First Printing 2006 (2,000 copies), This revised edition, Sept 2011 (3,000 copies).
  (Adobe InDesign CS5, PDF 193쪽, PDF 쪽 = 인쇄 쪽 + 1 — 쪽 아래 AmerTypewriter 8pt 숫자가 쪽 이름)
- 문단: 첫 줄 들여쓰기(왼쪽 여백 + 12pt 넘게) · 번호 항목('1.' + 탭) · 큰 첫 글자(드롭 캡) 문단에서 새 문단.
  쪽이 넘어갈 때: 다음 쪽 첫 줄이 들여쓰지 않았으면 앞 문단에 이어 붙임.
- 제목(ArialRoundedMTBold 15·18) → 'h'. 제목 글꼴의 옛 표기('Satipat.t.ha-na', 'Pa-li')는 인쇄된 모양대로 ṭ·ā 로.
- 그림 쪽의 만화 글(ComicSansMS)은 'pq' (짝짓기에서 뺌, 한국어판은 그림 안에 글이 있음). 2쪽 속표지는 'h'.
- 차례(6쪽) → 'toc' 줄마다, 빠알리 용어 풀이(186쪽~) → 'gl' (term + 풀이).
- 1쪽(빈 쪽)·3쪽(판권 면)은 넣지 않음. 글자는 PDF 그대로 — 보이지 않는 줄 나눔 표시(U+00AD)만 빼고,
  줄 끝 '-'·'­' 는 붙여 씀, 탭은 빈칸, 큰 첫 글자는 다음 글에 붙임.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP_PAGES = {1, 3}
TOC_PAGE = 6
GLOSS_FROM = 186
OLD = {'t.': 'ṭ', 'd.': 'ḍ', 'n.': 'ṇ', 'l.': 'ḷ', 'm.': 'ṃ', 'a-': 'ā', 'i-': 'ī', 'u-': 'ū'}


def oldfix(t):
    for _ in range(4): t = _oldfix(t)
    return t


def _oldfix(t): return re.sub(r'(?<=\w)([tdnlm]\.|[aiu]-)(?=[a-z])', lambda m: OLD[m.group(1)], t)


def norm(t): return t.replace('\t', ' ').replace('­', '­')


def join(a, b):
    if not a: return b
    if a.endswith('­'): return a[:-1] + b
    if re.search(r'[A-Za-zāīūṃṅñṭḍṇḷ]-$', a): return a + b
    return a + ' ' + b


def text(sp):
    t = ''.join(norm(s['text']) for s in sp)
    t = re.sub(r'[ \t]+', ' ', t).strip()
    end_soft = t.endswith('­')
    t = t.replace('­', '')
    return t + ('­' if end_soft else '')


paras = []; cur = None; gloss = False; pqc = None; pqy = 0; sepnext = False
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP_PAGES: continue
    pg = ''
    rows = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            if not ''.join(s['text'] for s in sp).strip(): continue
            ne = [s for s in sp if s['text'].strip()]
            if ne[0]['font'].startswith('AmerTypewriter') and ne[0]['size'] < 9 and l['bbox'][1] > 400:
                pg = ''.join(s['text'] for s in sp).strip(); continue
            rows.append([list(l['bbox']), sp])
    if not rows: continue
    if not pg: pg = str(pn - 1)       # 쪽 번호가 인쇄되지 않은 앞쪽: PDF 쪽 - 1
    rows.sort(key=lambda r: (round(r[0][1]), r[0][0]))
    # 같은 높이 조각('1.' + 글, 용어 + 풀이) 은 한 줄로 — 조각은 따로도 기억
    G = []
    for bb, sp in rows:
        if G and abs(G[-1]['bb'][1] - bb[1]) < 2.5 and abs(G[-1]['bb'][3] - bb[3]) < 3:
            g = G[-1]; g['parts'].append((bb, sp)); g['bb'] = [min(g['bb'][0], bb[0]), min(g['bb'][1], bb[1]), max(g['bb'][2], bb[2]), max(g['bb'][3], bb[3])]
        else: G.append({'bb': bb, 'parts': [(bb, sp)]})
    for g in G:
        g['parts'].sort(key=lambda r: r[0][0])
        g['sp'] = [s for _, s2 in g['parts'] for s in s2]
        ne = [s for s in g['sp'] if s['text'].strip()]
        g['font'] = ne[0]['font']; g['size'] = round(max(s['size'] for s in ne), 1)
    # 큰 첫 글자 → 옆 첫 줄 앞에
    for g in G:
        if g['font'].startswith('AmerTypewriter') and g['size'] > 30:
            g['skip'] = True
            nx = [x for x in G if not x.get('skip') and x['bb'][0] >= g['bb'][2] - 3 and g['bb'][1] - 2 <= x['bb'][1] <= g['bb'][3]]
            nx.sort(key=lambda x: x['bb'][1])
            if nx:
                nx[0]['drop'] = text(g['sp'])
                for x in nx[1:]: x['dropcont'] = True
    body = [g for g in G if g['font'].startswith('DejaVuSans') and 9.5 <= g['size'] <= 10.9 and not g.get('drop') and not g.get('dropcont')]
    lm = min((g['bb'][0] for g in body), default=82)
    first = True; prevh = None
    for g in G:
        if g.get('skip'): continue
        f, sz, bb = g['font'], g['size'], g['bb']
        t = g.get('drop', '') + text(g['sp'])
        if not t.strip('­'): continue
        if pn == 2:
            if cur and cur['k'] == 'h' and cur['pg'] == pg and 'ASHIN' not in t: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            continue
        if f.startswith('ComicSans'):       # 그림 속 글: 본문 문단의 흐름은 끊지 않음
            if pqc is not None and pqc is paras[-1] and pqc['pg'] == pg and bb[1] - pqy < 40: pqc['t'] = join(pqc['t'], t)
            else: pqc = {'pg': pg, 'k': 'pq', 't': t}; paras.append(pqc)
            pqy = bb[3]; continue
        if pn == TOC_PAGE:
            k = 'h' if f.startswith('ArialRounded') else 'toc'
            cur = {'pg': pg, 'k': k, 't': t}; paras.append(cur); continue
        if f.startswith('ArialRounded'):
            t = oldfix(t)
            if 'Glossary' in t: gloss = True
            if cur and cur['k'] == 'h' and prevh is not None and bb[1] - prevh < 12: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prevh = bb[3]; first = False; continue
        if gloss and sz <= 9.2:
            left = [s for b2, s2 in g['parts'] if b2[0] < 180 for s in s2]
            right = [s for b2, s2 in g['parts'] if b2[0] >= 180 for s in s2]
            tm, df = text(left), text(right)
            if tm or cur is None or cur['k'] != 'gl':
                cur = {'pg': pg, 'k': 'gl', 'term': tm, 'def': df}; paras.append(cur)
            else:
                cur['def'] = join(cur['def'], df) if not re.match(r'[a-z]\) ', df) else cur['def'] + '\n' + df
            first = False; continue
        if t == '•': sepnext = True; continue      # 63쪽 가운데 맞춤 목록의 • 줄: 다음 줄부터 새 문단
        num = re.match(r'(\d+\.|•) ', t) is not None
        ind = bb[0] > lm + 12 and not g.get('dropcont')
        if ind and not num and cur is not None and cur['k'] == 'p' and cur.get('num') and (abs(bb[0] - cur.get('hang', -99)) < 4 or lm + 20 < bb[0] < lm + 40): ind = False   # 번호 항목의 둘째 줄부터(번호 뒤 글자 자리에 맞춰 들여 씀)
        newp = cur is None or cur['k'] != 'p' or num or ind or bool(g.get('drop'))
        if first and pn != 4 and cur is not None and cur['k'] == 'p' and not ind and not num and not g.get('drop'): newp = False
        if pn == 4: newp = cur is None or cur['k'] != 'p' or cur['pg'] != pg or prevh is None or bb[1] - prevh > 12
        if sepnext: newp = True; sepnext = False
        elif pn == 64 and cur is not None and cur['k'] == 'p' and cur['pg'] == pg and not first: newp = False
        if newp:
            cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
            if num: cur['num'] = True
            if num and len(g['parts']) > 1: cur['hang'] = g['parts'][1][0][0]
        else: cur['t'] = join(cur['t'], t)
        prevh = bb[3]; first = False
for p in paras:
    if p['k'] == 'gl': p['t'] = p['term'] + '\n' + p['def']
    p['t'] = p['t'].replace('­', '')
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0013.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
