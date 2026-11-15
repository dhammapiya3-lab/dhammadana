"""『알아차림만으로는 충분하지 않습니다』(DL-0014) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0014.py Awareness-Alone-is-Not-Enough.pdf  →  tools/out/parallel/DL-0014.en.paras.json

원서: Ashin Tejaniya, AWARENESS ALONE IS NOT ENOUGH — Questions & Answers with Ashin Tejaniya (PageMaker, 212쪽).
- 쪽 이름: 쪽 아래 인쇄된 번호(8pt). PDF 쪽 = 인쇄 쪽 - 1.
- 문단: 첫 줄 들여쓰기(+21.6pt) · 'Yogi' / 'SUT' 말하는 이 · 줄 사이가 벌어짐(>20pt) 에서 새 문단, 쪽이 넘어가도 이어 붙임.
- 소제목(Bold 12·16) → kind 'h', 구분 '* * *' → kind 'sep', 말하는 이 'Yogi:'·'SUT:' 는 글 그대로(굵게만 표시 **Yogi**).
- 이 PDF 는 빠알리 장음을 위첨자 '-' 로 찍었음('sama'+위첨자 '-'+'dhi' = samādhi) → 앞 글자에 장음 부호를 얹음(ā ī ū). 그 밖의 글자는 PDF 그대로.
"""
import sys, re, json, os
import fitz

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = fitz.open(pdf)
MAC = {'a': 'ā', 'i': 'ī', 'u': 'ū', 'A': 'Ā', 'I': 'Ī', 'U': 'Ū', 'e': 'ē', 'o': 'ō'}


def line_text(spans):
    o = ''
    for s in spans:
        t = s['text']
        if s['flags'] & 1 and t.strip() == '-':      # 위첨자 '-' = 앞 글자 장음
            if o and o[-1] in MAC: o = o[:-1] + MAC[o[-1]]
            else: o += t
            continue
        if 'Bold' in s['font'] and s['size'] < 11 and t.strip() in ('Yogi', 'SUT', 'Yogi 1', 'Yogi 2'):
            o += '**' + t.strip() + '**'; continue
        o += t
    return o


paras = []   # {pg, k, t}
cur = None
gloss = False
for i in range(d.page_count):
    pg = ''
    L = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text']]
            if not ''.join(s['text'] for s in sp).strip(): continue
            if sp[0]['size'] < 9 and l['bbox'][1] > 540: pg = ''.join(s['text'] for s in sp).strip(); continue
            L.append((l['bbox'], sp))
    L.sort(key=lambda r: (round(r[0][1]), r[0][0]))
    # 같은 높이의 조각(번호 '28.' + 글)은 한 줄로, 글이 시작하는 자리(hang)를 기억
    L.sort(key=lambda r: (r[0][3], r[0][0]))
    G = []
    for bb, sp in L:
        if G and abs(G[-1][-1][0][3] - bb[3]) < 2: G[-1].append((bb, sp))
        else: G.append([(bb, sp)])
    L = []; HANG = {}; TERM = {}
    for g in G:
        g.sort(key=lambda r: r[0][0])
        bb = (g[0][0][0], min(r[0][1] for r in g), max(r[0][2] for r in g), max(r[0][3] for r in g))
        sp = []
        for k, (b2, s2) in enumerate(g): sp += ([{**s2[0], 'text': ' ' + s2[0]['text']}] + s2[1:]) if k else s2
        L.append((bb, sp)); HANG[id(sp)] = g[1][0][0] if len(g) > 1 else None
        if len(g) > 1 and g[0][0][0] < 150 and g[1][0][0] > 160: TERM[id(sp)] = (line_text(g[0][1]).strip(), line_text(sum((r[1] for r in g[1:]), [])).strip())
    if not L: continue
    lm = min(r[0][0] for r in L if r[1][0]['size'] == 10.5) if any(r[1][0]['size'] == 10.5 for r in L) else min(r[0][0] for r in L)
    prev = None
    for bb, sp in L:
        t = line_text(sp)
        big = max(s['size'] for s in sp)
        bold = all('Bold' in s['font'] for s in sp if s['text'].strip())
        if bold and big >= 12:
            if re.fullmatch(r'[\s*]+', t): k = 'sep'
            elif i + 1 in (6, 10, 11, 12, 13): k = 'toc'      # 차례 쪽 제목 ('CONTENTS', 'TOPICS IN …')
            else: k = 'h'
            if 'GLOSSARY' in t: gloss = True
            if cur and cur['k'] == k and k in ('h', 'toc') and prev is not None and bb[1] - prev[3] < 12:
                cur['t'] += ' ' + t.strip()     # 여러 줄 제목
            else:
                cur = {'pg': pg, 'k': k, 't': t.strip()}; paras.append(cur)
            prev = bb; continue
        if i + 1 in (6, 10, 11, 12, 13) and big != 10.5 or (i + 1 in (10, 11, 12, 13) and big < 10):   # 차례 쪽: 줄마다 (짝짓지 않음)
            cur = {'pg': pg, 'k': 'toc', 't': t.strip(), 'sz': big}; paras.append(cur); prev = bb; continue
        if gloss and big < 10.5:   # 빠알리 용어 풀이: 왼쪽 낱말 + 오른쪽 풀이 (짝짓기는 낱말로)
            if id(sp) in TERM: tm, df = TERM[id(sp)]
            elif bb[0] < 150: tm, df = t.strip(), ''
            else: tm, df = '', t.strip()
            if tm and not tm.startswith('(') or cur is None or cur['k'] != 'gl':
                cur = {'pg': pg, 'k': 'gl', 'term': tm, 'def': df}; paras.append(cur)
            else:
                if tm: cur['term'] += ' ' + tm      # '(also see kusala)' 처럼 낱말 아래 줄
                if df: cur['def'] += ' ' + df
            prev = bb; continue
        indent = bb[0] - lm > 12
        if cur and cur.get('hang') is not None and abs(bb[0] - lm - cur['hang']) < 3: indent = False   # 번호 목록의 둘째 줄 (번호 뒤 글 자리에 맞춰 들여 씀)
        spk = t.startswith('**Yogi') or t.startswith('**SUT')
        gap = bb[1] - prev[3] if prev is not None else None
        newp = cur is None or cur['k'] != 'p' or indent or spk or (gap is not None and gap > 8) or big != 10.5 and cur.get('sz') != big
        if prev is None and cur is not None and cur['k'] == 'p' and not indent and not spk and big == cur.get('sz'):
            newp = bool(re.match(r'\d+\.\s', t))        # 쪽을 넘어 이어지는 문단 (번호로 시작하면 새 항목)
        if newp:
            cur = {'pg': pg, 'k': 'p', 't': t.strip(), 'sz': big, 'hang': (HANG.get(id(sp)) - lm) if HANG.get(id(sp)) else None}; paras.append(cur)
        else:
            a = cur['t']
            cur['t'] = a + ('' if a.endswith('-') and not a.endswith(' -') and False else ' ') + t.strip()
        prev = bb
    # 쪽 이름이 없는 쪽(앞표지 등)
for p in paras:
    p.pop('sz', None); p.pop('hang', None)
    if p['k'] == 'gl': p['t'] = p['term'] + '\n' + p.pop('def').strip()
    p['t'] = '\n'.join(re.sub(r'\s+', ' ', x).strip() for x in p['t'].split('\n'))
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0014.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', sum(p['k'] == 'h' for p in paras), '제목')
