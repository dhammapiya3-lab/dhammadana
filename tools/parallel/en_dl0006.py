"""『죽음과 재생 시의 업』(DL-0006) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0006.py Kamma-at-death-and-rebirth.pdf  →  tools/out/parallel/DL-0006.en.paras.json

원서 판본 (판권 면 그대로): KAMMA AT DEATH AND REBIRTH, Sayadaw Dr. Nandamālābhivaṃsa,
  First edition: February, 2016 (1000 copies), Published by Abhidhamma-Förderverein e.V., Bruckmühl, Germany,
  Printed by Full Colour, Mandalay, Myanmar. (PDF 70쪽, PDF 쪽 = 인쇄 쪽 + 1 — 쪽 아래 Times New Roman 12pt 숫자)
- 문단: 줄 사이가 20pt 넘게 벌어지면 새 문단 (들여쓰기 없는 조판). 쪽이 넘어갈 때: 앞 쪽 마지막 줄이 오른쪽 끝까지 찼거나
  (318pt 넘음) 문장이 끝나지 않았으면 앞 문단에 이어 붙임.
- 장 제목(Tahoma Bold 14)·소제목(Tahoma Bold 11·12, 한 줄) → 'h'. 장 제목 아래 밑줄('____')은 뺌. '* * * * *' → 'sep'.
- 본문 속 각주 번호(Tahoma 7pt 숫자) → '[^n]' 표시, 쪽 아래 각주(6pt 번호 + 9pt 글) → 'fn' 문단 '[^n]: 글' (짝짓기에서 뺌).
- 앞쪽 Acknowledgement 묶음은 한국어판 순서에 맞춰 Biography 묶음 뒤로 옮김(글자·쪽 이름은 그대로).
- 차례(4쪽) → 'toc' 줄마다. 1쪽(빈 쪽)·3쪽(판권 면)·70쪽(뒤표지)은 넣지 않음. 2쪽 속표지는 'h'.
- 글자는 PDF 그대로(Symbol 글꼴의 글머리표 U+F0B7 만 '•' 로, 그리스 문자 'ᾱ'(U+1FB1)로 찍힌 장음도 그대로) — 아포스트로피가 '‟'(U+201F)로 잘못 찍힌 132곳(don‟t·Buddha‟s·Please wait.‟)은 운영자 요청(2026-11-17)으로 ’ 로 교정 — 줄 끝 '-' 는 붙여 씀, 겹친 빈칸은 하나로.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = pymupdf.open(pdf)
SKIP = {1, 3, 70}
TOC_PAGE = 4
FULL = 318


def join(a, b):
    if not a: return b
    if re.search(r'[A-Za-zāīūṃṅñṭḍṇḷᾱ]-$', a): return a + b
    return a + ' ' + b


def ends_sentence(t): return re.search(r'[.?!:”"‟\'’)]\s*$', t.strip()) is not None


paras = []; cur = None; fncur = None
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    pg = ''; lines = []; fns = []
    for b in d[i].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'] != '']
            raw = ''.join(s['text'] for s in sp)
            if not raw.strip(): continue
            ne = [s for s in sp if s['text'].strip()]
            f0, s0 = ne[0]['font'], ne[0]['size']
            if f0.startswith('Times New Roman') and s0 == 12 and re.fullmatch(r'\s*\d+\s*', raw) and l['bbox'][1] > 500:
                pg = raw.strip(); continue
            if re.fullmatch(r'\s*_{5,}\s*', raw): continue
            if max(s['size'] for s in ne) <= 9.5 and pn not in (2,):   # 쪽 아래 각주 (9pt 글·6pt 번호)
                fns.append((l['bbox'], sp)); continue
            # 본문 속 각주 번호(7pt) → [^n]
            t = ''
            for s in sp:
                if s['text'].strip() and round(s['size']) == 7 and re.fullmatch(r'\d+', s['text'].strip()):
                    t += '[^' + s['text'].strip() + ']'
                else: t += s['text']
            t = re.sub(r'[ \t]+', ' ', t).replace('\uf0b7', '•').replace('‟', '’').strip()
            bold = all('Bold' in s['font'] for s in ne)
            lines.append({'bb': l['bbox'], 't': t, 'bold': bold, 'size': round(max(s['size'] for s in ne), 1), 'font': f0})
    if not pg: pg = str(pn - 1)
    lines.sort(key=lambda x: (round(x['bb'][1]), x['bb'][0]))
    # 같은 높이 조각은 한 줄로
    L = []
    for x in lines:
        if L and abs(L[-1]['bb'][1] - x['bb'][1]) < 2.5:
            y = L[-1]; y['t'] = y['t'] + ' ' + x['t']; y['bb'] = [min(y['bb'][0], x['bb'][0]), y['bb'][1], max(y['bb'][2], x['bb'][2]), max(y['bb'][3], x['bb'][3])]
        else: L.append(dict(x))
    prev = None; first = True
    for x in L:
        t, bb = x['t'], x['bb']
        if pn == 2:
            if cur and cur['k'] == 'h' and cur['pg'] == pg and prev is not None and bb[1] - prev['bb'][3] < 20: cur['t'] = join(cur['t'], t)
            else: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = x; continue
        if pn == TOC_PAGE:
            k = 'h' if x['bold'] else 'toc'
            cur = {'pg': pg, 'k': k, 't': t}; paras.append(cur); prev = x; continue
        if re.fullmatch(r'(\* ?){3,}', t):
            cur = {'pg': pg, 'k': 'sep', 't': t}; paras.append(cur); prev = x; continue
        if x['bold'] and x['size'] >= 11 and bb[2] < 372 and (prev is None or bb[1] - prev['bb'][3] > 8 or (cur and cur['k'] == 'h' and cur['pg'] == pg)):
            if cur and cur['k'] == 'h' and cur['pg'] == pg and prev is not None and prev['bold'] and bb[1] - prev['bb'][3] < 8:
                cur['t'] = join(cur['t'], t)
            elif x['size'] >= 11 and (bb[2] - bb[0] < 300 or x['size'] >= 12):
                cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
                prev = x; first = False; continue
            else: pass
            if cur and cur['k'] == 'h' and cur['t'].endswith(t): prev = x; first = False; continue
        bullet = t[:1] == '•'
        if first:
            cont = cur is not None and cur['k'] == 'p' and (cur.get('lastx', 0) >= FULL or not ends_sentence(cur['t'])) and not bullet
            newp = not cont
        else:
            gap = bb[1] - prev['bb'][3]
            newp = cur is None or cur['k'] != 'p' or gap > 8 or bullet
        if newp: cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur)
        else: cur['t'] = join(cur['t'], t)
        cur['lastx'] = bb[2]
        prev = x; first = False
    # 각주
    fns.sort(key=lambda r: (round(r[0][1]), r[0][0]))
    for bb, sp in fns:
        ne = [s for s in sp if s['text'].strip()]
        num = ne[0]['text'].strip() if round(ne[0]['size']) == 6 and re.fullmatch(r'\d+', ne[0]['text'].strip()) else None
        body = re.sub(r'[ \t]+', ' ', ''.join(s['text'] for s in sp if s is not ne[0] or num is None)).replace('‟', '’').strip()
        if num:
            fncur = {'pg': pg, 'k': 'fn', 't': f'[^{num}]: {body}'}; paras.append(fncur)
        elif fncur is not None:
            fncur['t'] = join(fncur['t'], body)
for p in paras: p.pop('lastx', None)
# 한국어판은 앞쪽 순서가 '저자 소개 → 감사의 말' (원서는 Acknowledgement(4쪽) → Biography(5~7쪽)) — 짝짓기는 순서를 지켜야 하므로
# 원서 문단 목록에서 Acknowledgement 묶음만 Biography 묶음 뒤로 옮김 (글자·쪽 이름은 그대로, 쪽 이름 pg 로 원서 쪽은 늘 바르게 보임)
ia = next(i for i, p in enumerate(paras) if p['k'] == 'h' and p['t'] == 'Acknowledgement')
ib = next(i for i, p in enumerate(paras) if p['k'] == 'h' and p['t'].startswith('Biography'))
iff = next(i for i, p in enumerate(paras) if p['k'] == 'h' and p['t'] == 'Foreword')
paras = paras[:ia] + paras[ib:iff] + paras[ia:ib] + paras[iff:]
out = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(out, exist_ok=True)
json.dump(paras, open(os.path.join(out, 'DL-0006.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)))
