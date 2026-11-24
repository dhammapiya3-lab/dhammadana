"""『사아리뿟따 이야기』(DL-0037) 영어 원서 PDF → 원서 문단 목록 (『부처님, 그분』 en_dl0029.py 와 같은 BPS 온라인판 calibre 조판)
  python3 tools/parallel/en_dl0037.py wh090_nyanaponika_the-life-of-sariiputta.pdf  →  tools/out/parallel/DL-0037.en.paras.json

원서 판본 (판권 면 그대로): The Life of Sariputta, Compiled and translated from the Pali texts by Nyanaponika Thera,
  Buddhist Publication Society, Kandy • Sri Lanka, The Wheel Publication No, 90/92, Copyright © Kandy, Buddhist Publication Society, (1987),
  BPS Online Edition © (2008), Digital Transcription Source: BPS Transcription Project
  (calibre 2.82.0 PDF 124쪽, PDF 쪽 = 쪽 이름 — 쪽 아래 LiberationSerif 숫자). 이 전자판은 빠알리 부호를 거의 빼고 적음(Sariputta·Tipitaka) — 그대로 둠.
- 문단: 들여쓰기 없는 조판 — 줄 사이(위 끝 차이)가 22pt 넘게 벌어지면 새 문단(같은 문단 안 18.7pt, 문단 사이 26pt 안팎).
  왼쪽 자리(18 본문 · 47 들여 쓴 인용·게송 · 76 더 들여 쓴 게송·출처 · 198 '* * *')가 바뀌면 새 문단.
  쪽이 넘어갈 때는 앞 문단이 문장 끝으로 끝나지 않았거나 앞 쪽 마지막 줄이 오른쪽 끝 가까이(370pt 넘게) 찼으면 이어 붙임.
- 제목(Tahoma)은 'h' — 이어진 같은 크기 Tahoma 줄(40pt 안)은 한 제목으로('From Birth to the Attainment of' + 'Arahatship').
- 본문 속 주 번호 '[1]'(LiberationSans-Bold) → '[^1]'. 뒤쪽 Notes(116~120쪽, 'N. ' 로 시작) → 'fn' 문단 '[^N]: 글'.
  '[See also]'·'[Summary]' 는 전자판의 연결 표시 — 글자 그대로 둠('[Summary]' 만 있는 줄은 'pq').
- 들여 쓴 묶음 가운데 게송(76pt 묶음, 줄 끝 가운데값 335pt 안, VERSE)은 인쇄된 줄마다 줄 바꿈 — 긴 게송 줄이 접힌 곳은 빈칸으로.
- 2쪽 속표지·판권 → 'h'/'p', 이용 조건(For free distribution…) → 'pq', '* * *' → 'sep'. 1쪽(빈 쪽)·121~124쪽(BPS 안내·calibre 차례)은 넣지 않음.
- 글자는 PDF 그대로 — 줄 끝 '-' 는 빈칸 없이 붙임, 겹친 빈칸은 하나로.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP = {1} | set(range(121, d.page_count + 1))


def join(a, b):
    if not a: return b
    if re.search(r'[A-Za-zĀāĪīŪūṃṁṅñṭḍṇḷ]-$', a): return a + b
    return a + ' ' + b


def ends_sentence(t): return re.search(r'[.?!:”"’)\]]\s*$', t.strip()) is not None


def lvl(x):
    return 0 if x < 30 else 47 if x < 60 else 76 if x < 150 else 198


paras = []; cur = None; NOTES = False; prev = None
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
    L.sort(key=lambda x: (round(x['bb'][1]), x['bb'][0]))
    first = True
    for x in L:
        t = re.sub(r'[ \t ]+', ' ', x['t']).strip()
        t = re.sub(r'\s*\[(\d+)\]', lambda m: '[^' + m.group(1) + ']', t)
        bb = x['bb']
        if x['font'].startswith('Tahoma'):
            if t == 'Notes': NOTES = True
            if cur and cur['k'] == 'h' and prev is not None and prev['font'] == x['font'] and prev['size'] == x['size'] and 0 < bb[1] - prev['bb'][1] < 40:
                cur['t'] = join(cur['t'], t)
            else:
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = x; first = False; continue
        if pn == 2 and x['font'].startswith('URWPalladioITU-Bold'):
            cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur); prev = x; first = False; continue
        if NOTES:
            m = re.match(r'(\d+)\.\s*(.*)', t)
            if bb[0] < 25 and m:
                cur = {'pg': pg, 'k': 'fn', 't': f'[^{m.group(1)}]: {m.group(2)}'}; paras.append(cur)
            else:
                cur['t'] = join(cur['t'], t)
            prev = x; first = False; continue
        if t == '* * *':
            cur = {'pg': pg, 'k': 'sep', 't': t}; paras.append(cur); prev = x; first = False; continue
        if t == '[Summary]':
            cur = {'pg': pg, 'k': 'pq', 't': t}; paras.append(cur); prev = x; first = False; continue
        kind = 'pq' if (pn == 2 and t.startswith('For free')) or (cur is not None and cur['k'] == 'pq' and pn == 2) else 'p'
        ind = lvl(bb[0])
        if first:
            newp = not (cur is not None and cur['k'] == kind and cur.get('ind') == ind and (not ends_sentence(cur['t']) or cur.get('lastx', 0) >= 370))
        else:
            gap = bb[1] - prev['bb'][1]
            newp = cur is None or cur['k'] != kind or gap > 22 or ind != cur.get('ind')
        if newp:
            cur = {'pg': pg, 'k': kind, 't': t, 'ind': ind}; paras.append(cur)
        else:
            cur['t'] = join(cur['t'], t)
        if ind: cur.setdefault('L', []).append((t, bb[2]))
        cur['lastx'] = bb[2]
        prev = x; first = False
VERSE = ('Unresentful like the earth', 'One who this very day')   # 68·62쪽 게송 — 긴 줄이 있어 자리로는 못 가림(쪽 그림으로 확인)
PROSE = ('“In many hundred thousands of births',)                    # 91쪽 『밀린다빤하』 산문 인용
# 들여 쓴 묶음 중 게송(76pt 묶음, 또는 마지막 줄 말고 줄 끝 자리의 가운데값이 335pt 안)은 인쇄된 줄마다 줄 바꿈 —
# 단, 앞 줄이 문장 부호 없이 끝나고 다음 줄이 소문자로 시작하면(긴 게송 줄이 접힌 것) 빈칸으로 이음
for p in paras:
    L = p.pop('L', None)
    if os.environ.get('DBG') and L and len(L) > 1: print(p['pg'], p.get('ind'), [round(x) for _, x in L], p['t'][:40])
    if L and len(L) > 1 and not p['t'].startswith(PROSE) and (p.get('ind') == 76 or p['t'].startswith(VERSE) or sorted(x1 for _, x1 in L[:-1])[(len(L) - 2) // 2] < 335):
        t = L[0][0]
        for (a, _), (b, _) in zip(L, L[1:]):
            t = (join(t, b) if (not re.search(r'[,;:.!?—”’)]$', a) and re.match(r'[a-zāīū(]', b)) or a.endswith('-') or a.count('(') > a.count(')') else t + '\n' + b)
        p['t'] = t
for p in paras: p.pop('ind', None); p.pop('lastx', None)
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0037.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
