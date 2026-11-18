"""『붓다의 말씀』(DL-0015) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0015.py wordofbuddha.pdf  →  tools/out/parallel/DL-0015.en.paras.json (+ .hyph.tsv)

원서 판본 (속표지·서문 그대로): The Word of the Buddha — An Outline of the teaching of the Buddha in the words of the Pali canon,
  Compiled, translated, and explained by Nyanatiloka, Buddhist Publication Society, Kandy, Ceylon (14th edition, 1967 서문).
  전자판: 14판을 스캔·글자 인식해 FrameMaker 5.5.6 으로 다시 짠 PDF 110쪽 (PDF 정보: David & Marian Cortesi, 1999),
  출처 https://www.urbandharma.org/pdf/wordofbuddha.pdf
  PDF 쪽 = 인쇄 쪽 + 15 (본문), 앞쪽 VII~XVII = PDF 6~15 — 쪽 위 머리글의 숫자가 쪽 이름.
- 빠알리 부호: 부호 있는 글자 자리는 본문에 빈칸(자리 맞춤)만 있고, 글자와 부호('a-' 'u-' 'i-' 'A-' 장음, 't.' 'n.' 'm.' 'd.' 'l.' 아래 점)를
  따로 겹쳐 찍음 → 겹치는 자리의 본문 줄에 ā ū ī Ā ṭ ṇ ṃ ḍ ḷ 로 넣고 자리 맞춤 빈칸은 뺌.
- 줄 끝 하이픈: 이어 붙인 낱말이 원서 다른 곳에 있으면 붙이고, 하이픈 낱말이 있으면 남김, 둘 다 없으면 영어는 붙이고 부호 있는 빠알리는 남김
  (결정 목록 …hyph.tsv).
- 문단: 줄 사이가 벌어지면(14pt 넘음) 새 문단, 들여 쓴 풀이 글(이탤릭, +12pt)·번호 항목은 따로 문단. 쪽이 넘어갈 때 앞 쪽 마지막 줄이
  꽉 찼고 같은 들여쓰기면 이어 붙임.
- 편자의 풀이 글(+12pt 들여 쓴 이탤릭) → 'note' (한국어판은 그 가운데 일부만 ＊ 문단으로 옮김 — 짝짓기에서 덜 끌어당기게).
- 제목(10pt 넘는 글·가운데 맞춘 대문자 9pt 줄) → 'h', 줄이 이어지면 한 제목. 쪽 여백의 경전 출처(이탤릭 7pt, 'D.16.' 'M. 26') → 'cite'
  (다음 본문 문단 앞에 오는 출처 — 짝짓기에서 뺌). 큰 괄호(Symbol)는 뺌.
- 차례(PDF 13~15) → 'toc' ('제목, 쪽'), 1·2(표지)·3(저자 저서)·5(전자판 알림)·9(전자판 서문)·10(약어)·11·12(빠알리 발음)·
  99~110(불교 문헌·빠알리 낱말 찾아보기·빈 쪽)은 한국어판에 없어 넣지 않음.
"""
import sys, re, json, os, collections, unicodedata
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(OUT, exist_ok=True)
d = pymupdf.open(pdf)
SKIP = {1, 2, 3, 5, 9, 10, 11, 12} | set(range(99, 111))
TOC = {13, 14, 15}
LIG = {'ﬁ': 'fi', 'ﬀ': 'ff', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl'}
MARK = {'-': '̄', '.': '̣'}
ROMAN = {'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17}

stat = collections.Counter()


def page_lines(pg):
    """한 쪽의 줄: [{'bb', 'chars': [(c, x0, x1, y1, font, size)]}], 겹쳐 찍은 부호 글자를 본문 줄에 넣음"""
    lines = []; over = []
    for b in pg.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            cs = []
            for s in l['spans']:
                for c in s['chars']:
                    cs.append([c['c'], c['bbox'][0], c['bbox'][2], c['bbox'][3], s['font'], s['size'], c['bbox'][1]])
            t = ''.join(c[0] for c in cs).strip()
            if not t: continue
            if re.fullmatch(r'(?:[a-zA][-.]\s*)+', t) and cs[0][5] >= 8.5:
                # 겹쳐 찍은 글자 + 부호
                k = [c for c in cs if c[0].strip()]
                for i in range(0, len(k) - 1, 2):
                    base, mk = k[i], k[i + 1]
                    over.append([unicodedata.normalize('NFC', base[0] + MARK[mk[0]]), base[1], base[2], base[3], base[4], base[5], base[6]])
                continue
            # 같은 줄 안에 겹쳐 찍은 부호(제목 줄의 'NIBB NA' + 'A-'): 앞 글자와 거의 겹치는 '-' '.' 는 그 글자의 부호
            k = []
            for c in cs:
                if c[0] in '-.' and k and k[-1][0].isalpha() and len(k[-1][0]) == 1 and c[1] >= k[-1][1] - 0.6 and c[2] <= k[-1][2] + 1.2 \
                        and (c[0] == '-' and c[3] < k[-1][3] - 2 or c[0] == '.' and c[6] > k[-1][6] + 1):
                    k[-1] = [unicodedata.normalize('NFC', k[-1][0] + MARK[c[0]])] + k[-1][1:]; k[-1].append('ov'); continue
                k.append(c)
            cs = []
            for c in k:
                if c[-1] == 'ov':
                    c = c[:7]; cx = (c[1] + c[2]) / 2
                    sp = [j for j, q in enumerate(cs) if q[0] == ' ' and c[1] - 0.5 <= (q[1] + q[2]) / 2 <= c[2] + 0.5]
                    if sp: del cs[sp[-1]]; stat['줄 안 부호'] += 1
                    cs.append(c); cs.sort(key=lambda q: q[1]); continue
                cs.append(c)
            # 여백 출처(7pt)와 본문이 한 줄로 묶여 있으면 나눔
            sm = [c for c in cs if c[5] < 8 and 'Italic' in c[4]]; bg = [c for c in cs if not (c[5] < 8 and 'Italic' in c[4])]
            for part in (sm, bg):
                if not ''.join(c[0] for c in part).strip(): continue
                bb = [min(c[1] for c in part), min(c[6] for c in part), max(c[2] for c in part), max(c[3] for c in part)]
                if part is bg and sm: bb[0] = min(c[1] for c in part if c[0].strip())
                lines.append({'bb': bb, 'chars': [c for c in part if c[0].strip() or c[1] >= bb[0] - 0.1] if part is bg and sm else part})
    for o in over:
        cx = (o[1] + o[2]) / 2
        best = None
        for L in lines:
            ys = [c[3] for c in L['chars'] if c[0].strip() and abs(c[5] - o[5]) < 1.5]
            if not ys: continue
            y = collections.Counter(round(v, 1) for v in ys).most_common(1)[0][0]
            if abs(y - o[3]) < 1.6 and L['bb'][0] - 8 < cx < L['bb'][2] + 8:
                best = L; break
        if best is None:
            stat['부호 글자 자리 못 찾음'] += 1; print('  ! 자리 못 찾음', o); continue
        cs = best['chars']
        # 자리 맞춤 빈칸(가운데가 겹치는 빈칸) 하나를 뺌
        sp = [i for i, c in enumerate(cs) if c[0] == ' ' and o[1] - 0.5 <= (c[1] + c[2]) / 2 <= o[2] + 0.5]
        if sp: del cs[sp[0]]; stat['빈칸 자리에 넣음'] += 1
        else: stat['빈칸 없이 넣음'] += 1
        cs.append(o)
        cs.sort(key=lambda c: c[1])
        best['bb'][0] = min(best['bb'][0], o[1]); best['bb'][2] = max(best['bb'][2], o[2])
    return lines


def ltext(L):
    s = ''.join(LIG.get(c[0], c[0]) for c in L['chars'] if c[4] != 'Symbol')
    return re.sub(r'\s+', ' ', s).strip()


pages = []
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    L = page_lines(d[i])
    # 같은 높이 줄 합치기 (부호 넣은 뒤 x 순서)
    L.sort(key=lambda r: (round(r['bb'][3]), r['bb'][0]))
    R = []
    for r in L:
        small = lambda q: next((c[5] for c in q['chars'] if c[0].strip()), 9) < 8
        if R and abs(R[-1]['bb'][3] - r['bb'][3]) < 2.5 and not small(r) and not small(R[-1]) and r['bb'][0] > R[-1]['bb'][0]:
            gap = r['bb'][0] - R[-1]['bb'][2]
            if gap > 1.5: R[-1]['chars'].append([' ', R[-1]['bb'][2], r['bb'][0], r['bb'][3], 'x', 9, r['bb'][1]])
            R[-1]['chars'] += r['chars']; R[-1]['bb'][2] = max(R[-1]['bb'][2], r['bb'][2])
        else: R.append(r)
    lab = ''; body = []
    for r in R:
        t = ltext(r)
        if r['bb'][1] < 50:
            m = re.search(r'(?:^|\s)(\d+|[IVX]+)$', t) or re.match(r'(\d+|[IVX]+)(?:\s|$)', t)
            if m: lab = m.group(1)
            continue
        if not t: continue
        body.append(r)
    if not lab and pn >= 16: lab = str(pn - 15)
    pages.append((pn, lab or '', body))

ALL = ' '.join(ltext(r) for _, _, body in pages for r in body)
WORDS = collections.Counter(w.lower() for w in re.findall(r"[^\W\d_](?:[^\W\d_]|[-’'])*[^\W\d_]|[^\W\d_]", ALL))
hyph = []
ALLL = ALL.lower()


def join(a, b, pg):
    if not a: return b
    m = re.search(r"([^\W\d_]+)-$", a)
    if m and b[:1].isalpha():
        left = m.group(1); right = re.match(r"[^\W\d_]+", b).group(0)
        whole, hy = (left + right).lower(), (left + '-' + right).lower()
        if re.search(r'(?<![\w-])' + re.escape(hy) + r'(?!\w)', ALLL) or re.search(re.escape(hy) + r'-', ALLL): keep = True; why = '하이픈 낱말이 원서에 있음'
        elif WORDS.get(whole): keep = False; why = '이은 낱말이 원서에 있음'
        elif re.search(r'(?<![\w-])' + re.escape(left.lower()) + r'-\w', ALLL) and not re.fullmatch(r'[a-z]+', left.lower()) is None and left[:1].islower() and len(left) > 2 and re.search(r'(?<![\w-])' + re.escape(left.lower()) + r'-(?!\s)', ALLL.replace(left.lower() + '- ', '')): keep = True; why = '앞 낱말이 원서에서 겹낱말 앞에 쓰임 — 하이픈 남김'
        elif left.lower() in ('non', 'self', 'co', 'well', 'ill', 'all', 'ever'): keep = True; why = '앞가지 — 하이픈 남김'
        elif re.search(r'[^\x00-\x7f]', left + right): keep = True; why = '부호 있는 빠알리 낱말 — 하이픈 남김'
        elif left[:1].isupper() and right[:1].isupper(): keep = True; why = '대문자 겹낱말 — 하이픈 남김'
        else: keep = False; why = '영어 낱말 나눔'
        hyph.append((pg, left + '-' + right, (left + '-' + right) if keep else (left + right), why))
        return a + b if keep else a[:-1] + b
    if a.endswith('—') or b.startswith('—'): return a + b
    return a + ' ' + b


paras = []; cur = None; last = None; cpend = []   # last: (앞 쪽 마지막 줄이 찼는가, 들여쓰기)
for pn, pg, body in pages:
    if pn in TOC:
        pend = ''
        for r in body:
            t = ltext(r)
            if r['chars'][0][5] > 10: paras.append({'pg': pg, 'k': 'h', 't': t}); continue
            m = re.match(r'(.*?)(?:\s+\.|\s*(?:\.\s*){2,})[\s.]*\b([0-9]+|[IVXivx]+)\s*$', t)   # 제목 + 점선 + 쪽 번호
            if m:
                title = (pend + ' ' + m.group(1).rstrip(' .')).strip()
                paras.append({'pg': pg, 'k': 'toc', 't': f'{title}, {m.group(2)}'}); pend = ''
            else: pend = (pend + ' ' + t).strip()
        cur = None; last = None; continue
    lm = min((r['bb'][0] for r in body if r['chars'][0][5] > 9 and r['chars'][0][5] < 10), default=48)
    lm = 78 if lm > 70 else 48
    rm = lm + 258
    prev = None; first = True
    for r in body:
        cs = [c for c in r['chars'] if c[0].strip() and c[4] != 'Symbol']
        if not cs: continue
        f, sz = cs[0][4], round(max(c[5] for c in cs), 1)
        if cs[0][5] < 8 and 'Italic' in cs[0][4]: sz = cs[0][5]
        x0, y0, x1 = r['bb'][0], r['bb'][1], r['bb'][2]
        t = ltext(r)
        if sz < 8 and 'Italic' in f:                 # 여백의 경전 출처 — 같은 높이에서 시작한 문단 앞에 두고, 문단을 끊지 않음
            c = {'pg': pg, 'k': 'cite', 't': t}
            if cur is not None and cur['k'] in ('p', 'note') and cur.get('pg') == pg and abs(cur.get('y', -99) - r['bb'][3]) < 6: paras.insert(paras.index(cur), c)
            else: cpend.append(c)
            continue
        center = abs((x0 + x1) / 2 - (lm + rm / 1 - lm) / 2 - lm / 2) < 12 if False else abs((x0 + x1) / 2 - (lm + lm + 258) / 2) < 14
        caps = t.upper() == t and re.search(r'[A-Z]{2}', t)
        ish = sz >= 9.9 and (caps or center and len(t) < 50) or (sz <= 9.1 and center and caps and x0 > lm + 15) or ('Bold' in f and sz > 9.5)
        if ish:
            if cur is not None and cur['k'] == 'h' and prev is not None and y0 - prev[1] < 22 and cur['pg'] == pg: cur['t'] += ' ' + t
            else: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = r['bb']; first = False; last = None; continue
        if cur is not None and cur['k'] == 'h' and center and x0 > lm + 30 and t.startswith('(') and prev is not None and y0 - prev[1] < 15:
            cur['t'] += ' ' + t; prev = r['bb']; continue          # 제목 아래 (rūpa-khandha)
        ind = round(x0 - lm)
        lvl = 0 if ind < 6 else 1 if ind < 30 else 2
        item = bool(re.match(r'(\d{1,2}|[a-z]|[IVX]+)[.)]\s?(?=[A-Z‘(])', t)) and not cur is None
        if first:
            cont = last is not None and cur is not None and cur['k'] in ('p', 'note') and last[1] == lvl and not item \
                and (not re.search(r'[.?!:;’”)]$', cur['t']) or t[:1].islower())
            newp = not cont
        else:
            gap = r['bb'][3] - prev[3]
            plvl = cur.get('lvl', 0) if cur else 0
            newp = cur is None or cur['k'] not in ('p', 'note') or gap > 13.5 \
                or (lvl != plvl and not (cur.get('hang') and lvl > plvl)) or item
        if newp:
            paras.extend(cpend); cpend.clear()
            cur = {'pg': pg, 'k': 'note' if lvl == 1 and 'Italic' in f else 'p', 't': t, 'lvl': lvl, 'hang': item, 'y': r['bb'][3]}; paras.append(cur)
        else: cur['t'] = join(cur['t'], t, pg)
        prev = r['bb']; first = False
        last = (x1 >= rm - 20, cur['lvl'] if not cur.get('hang') else cur['lvl'] + 1 if lvl > cur['lvl'] else cur['lvl'])
paras.extend(cpend)
for p in paras: p.pop('lvl', None); p.pop('hang', None); p.pop('y', None)
json.dump(paras, open(os.path.join(OUT, 'DL-0015.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
with open(os.path.join(OUT, 'DL-0015.en.hyph.tsv'), 'w') as f:
    f.write('원서 쪽\t줄 끝 모양\t뽑은 글\t까닭\n'); [f.write('\t'.join(x) + '\n') for x in hyph]
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)), dict(stat), '/ 줄 끝 하이픈', len(hyph),
      dict(collections.Counter(x[3] for x in hyph)))
