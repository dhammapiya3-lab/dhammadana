"""『알아차림만으로는 충분하지 않습니다』(DL-0014) 영어 원서 PDF (개정 2판, 2010) → 원서 문단 목록
  python3 tools/parallel/en_dl0014_2010.py Awareness.Alone.Is.Not.Enough.English.pdf  →  tools/out/parallel/DL-0014.en.paras.json

원서 판본 (판권 면 그대로): AWARENESS ALONE IS NOT ENOUGH, Second, revised edition May 2010,
  Copyright © Ashin Tejaniya 2008, Published with permission for free distribution by Auspicious Affinity (Malaysia),
  This printing: 2,000 copies, July 2010. (InDesign CS5, 241쪽, PDF 쪽 = 인쇄 쪽 + 1)
- 쪽 이름: 쪽 위 머리글 줄(8pt)의 숫자.
- 문단: 줄 사이가 벌어짐(줄 간격 15pt, 문단 사이 20pt 이상) · 첫 줄 들여쓰기 · 'Yogi:'/'SUT:' · 번호 항목 '12.' 에서 새 문단.
  쪽이 넘어갈 때(오른쪽이 들쭉날쭉한 조판): 앞 쪽 마지막 줄이 문장 끝으로 끝나지 않았거나 오른쪽 끝 가까이까지 찼으면, 또는 다음 쪽 첫 글자가 소문자면 이어 붙임.
- 소제목(DejaVuSansCondensed Bold 11 이상, 'Dear Reader,') → 'h', 구분 꽃무늬(Davys '3')·'* * *' → 'sep',
  본문에서 뽑아 크게 다시 실은 인용 상자(DejaVuSans 11.5~14) → 'pq' (짝짓기에서 뺌).
- 차례(10~12쪽) → 'toc' 항목마다, 빠알리 용어 풀이 → 'gl' (term + 풀이).
- 1쪽(표지)·3쪽(판권 면)·빈 쪽은 넣지 않음. 글자는 PDF 그대로 — 줄 끝 '-' 는 붙여 쓰고(non-|involvement), 탭은 빈칸, 첫 글자 장식(M)은 붙임.
"""
import sys, re, json, os
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SPK = re.compile(r'(Yogi(?: \d)?|SUT)\s*:\s*$')
SKIP_PAGES = {1, 3}
TOC_PAGES = {10, 11, 12}


def norm(t): return t.replace('\t', ' ')


def join(a, b):
    if not a: return b
    if re.search(r'[A-Za-zāīūṃṅñṭḍṇḷ]-$', a): return a + b
    return a + ' ' + b


def ltext(spans):
    o = ''
    for s in spans:
        t = norm(s['text'])
        if 'Bold' in s['font'] and s['size'] < 10 and SPK.match(t.strip() + (':' if not t.strip().endswith(':') else '')) and t.strip().rstrip(':') in ('Yogi', 'SUT', 'Yogi 1', 'Yogi 2'):
            o += '**' + t.strip().rstrip(':') + '**:'; continue
        o += t
    return re.sub(r'\s+', ' ', o).strip()


paras = []
cur = None
pqc = None; pqy = 0
gloss = False
last_full = False      # 앞 쪽 마지막 줄이 꽉 찼는가
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP_PAGES: continue
    pg = ''
    rows = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            if not ''.join(s['text'] for s in sp).strip(): continue
            bb = l['bbox']
            if bb[1] < 55 and max(s['size'] for s in sp) <= 9.5:
                m = re.findall(r'\d+', ''.join(s['text'] for s in sp)); pg = m[0] if m else pg; continue
            rows.append([bb, sp])
    if not rows: continue
    # 같은 높이 조각('1.' + 글) 은 한 줄로
    rows.sort(key=lambda r: (round(r[0][3]), r[0][0]))
    G = []
    for bb, sp in rows:
        if G and abs(G[-1][0][3] - bb[3]) < 2 and abs(G[-1][0][1] - bb[1]) < 4 and bb[0] - G[-1][0][2] < 40 and not (pn in TOC_PAGES and (bb[0] > 250) != (G[-1][0][0] > 250)):
            g = G[-1]; g[2].append((bb, sp)); g[0] = (min(g[0][0], bb[0]), min(g[0][1], bb[1]), max(g[0][2], bb[2]), max(g[0][3], bb[3]))
        else: G.append([tuple(bb), None, [(bb, sp)]])
    L = []
    for bb, _, parts in G:
        parts.sort(key=lambda r: r[0][0])
        sp = [s for _, s2 in parts for s in s2]
        L.append({'bb': bb, 'sp': sp, 'parts': parts, 'font': next(s['font'] for s in sp if s['text'].strip()), 'size': round(max(s['size'] for s in sp if s['text'].strip()), 1)})
    L.sort(key=lambda r: ((r['bb'][0] > 250) if pn in TOC_PAGES else 0, r['bb'][1], r['bb'][0]))   # 차례 쪽은 왼쪽 단 → 오른쪽 단
    body = [r for r in L if r['font'].startswith('GentiumBasic') and r['size'] in (11.5, 12.0) or r['font'].startswith('DejaVuSansCondensed-Bold') and r['size'] == 9.0]
    lm = min((r['bb'][0] for r in body), default=54); rm = max((r['bb'][2] for r in body), default=420)
    # 첫 글자 장식(M) → 다음 줄 앞에
    for k, r in enumerate(L):
        if r['size'] > 30 and r['font'].startswith('GentiumBasic') and len(ltext(r['sp'])) == 1:
            nx = min((x for x in L if x is not r and x['bb'][1] >= r['bb'][1] - 2), key=lambda x: x['bb'][1])
            nx['drop'] = ltext(r['sp']); r['skip'] = True
    prev = None
    first = True
    for r in L:
        if r.get('skip'): continue
        bb, sp, f, sz = r['bb'], r['sp'], r['font'], r['size']
        t = (r.get('drop', '')) + ltext(sp)
        if not t: continue
        if f.startswith('Davys') or re.fullmatch(r'[\s*]+', t):
            cur = {'pg': pg, 'k': 'sep', 't': '* * *'}; paras.append(cur); prev = bb; first = False; continue
        if pn in TOC_PAGES:
            if 'Bold' in f and sz >= 12:
                cur = {'pg': pg, 'k': 'toc', 't': t, 'h': 1}; paras.append(cur)
            elif cur and cur['k'] == 'toc' and not re.search(r'\d+$', cur['t']) and not cur.get('h'):
                cur['t'] = join(cur['t'], t)
            else:
                cur = {'pg': pg, 'k': 'toc', 't': t}; paras.append(cur)
            prev = bb; first = False; continue
        ne = [s for s in sp if s['text'].strip()]
        head = all(s['font'].startswith('DejaVuSansCondensed') and 'Bold' in s['font'] and s['size'] >= 10.9 for s in ne) or t == 'Dear Reader,' or (pn == 2 and sz >= 16)
        pq = not head and all(s['font'].startswith('DejaVuSans') and s['size'] >= 11 for s in ne)
        if head:
            if 'GLOSSARY' in t: gloss = True
            if cur and cur['k'] == 'h' and prev is not None and bb[1] - prev[3] < 6 and pn == 2:
                cur['t'] = join(cur['t'], t)
            else:
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = bb; first = False; continue
        if pq:      # 인용 상자: 본문 문단의 흐름은 끊지 않음
            if pqc and pqc is paras[-1] and bb[1] - pqy < 8: pqc['t'] = join(pqc['t'], t)
            else: pqc = {'pg': pg, 'k': 'pq', 't': t}; paras.append(pqc)
            pqy = bb[3]; continue
        if gloss and sz == 12.0:
            left = [s for b2, s2 in r['parts'] if b2[0] < 140 for s in s2]
            right = [s for b2, s2 in r['parts'] if b2[0] >= 140 for s in s2]
            tm, df = ltext(left), ltext(right)
            newe = cur is None or cur['k'] != 'gl' or (prev is not None and bb[1] - prev[1] > 16.5) or first and tm and not tm.startswith('(') and cur.get('_last_left_y') is None
            if first and cur is not None and cur['k'] == 'gl': newe = bool(tm) and not tm.startswith('(') and not cur['term'].endswith('-')
            if newe:
                cur = {'pg': pg, 'k': 'gl', 'term': tm, 'def': df}; paras.append(cur)
            else:
                if tm: cur['term'] = join(cur['term'], tm) if cur['term'].endswith('-') else (cur['term'] + ' ' + tm).strip()
                if df: cur['def'] = join(cur['def'], df)
            prev = bb; first = False; continue
        spk = t.startswith('**Yogi') or t.startswith('**SUT')
        num = re.match(r'\d+\. ', t) is not None
        if first:
            newp = cur is None or cur['k'] != 'p' or spk or num or (not last_full and not t[:1].islower())
        else:
            gap = bb[1] - prev[1] if prev is not None else 99
            newp = cur is None or cur['k'] != 'p' or spk or num or gap > 17.5
        if newp:
            cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
        else:
            cur['t'] = join(cur['t'], t)
        prev = bb; first = False
        # 오른쪽이 들쭉날쭉한 조판: 마지막 줄이 문장 끝(. ? ! ” ’ :)으로 끝나고 짧으면 문단 끝으로 봄
        last_full = not re.search(r'[.?!:”’…)]$', t) or bb[2] >= rm - 50
    if L and cur is not None and cur['k'] != 'p': last_full = False
for p in paras:
    p.pop('h', None)
    if p['k'] == 'gl': p['t'] = p['term'] + '\n' + p['def']
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0014.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
import collections
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
