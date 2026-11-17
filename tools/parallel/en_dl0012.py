"""『위빠사나 명상』(DL-0012) 영어 원서 PDF → 원서 문단 목록
  python3 tools/parallel/en_dl0012.py Chanmyay_Lectures.pdf  →  tools/out/parallel/DL-0012.en.paras.json

원서 판본 (판권 면 그대로): Vipassanā Meditation — Lectures on Insight Meditation, Venerable Chanmyay Sayadaw,
  Published for free distribution by Chanmyay Yeiktha Meditation Centre (Yangon), ©2017 Chanmyay Yeiktha Sodality,
  Creative Commons BY-NC-SA 4.0, Printed by Swel Taw Color Offset Printing (Yangon).
  (LaTeX 로 짠 PDF 95쪽, PDF 쪽 = 인쇄 쪽 + 6 — 쪽 아래 숫자가 쪽 이름)
- 글자: LaTeX PDF 라 빠알리 부호가 따로 찍혀 있음 — 글자 위 '¯'(장음) → ā ī ū, 글자 아래 '.'(+ 빈칸 조각) → ṇ ṭ ḍ ṃ ḷ,
  위 '˙' → ṁ ṅ (찍힌 자리가 겹치는 글자에 붙임, 'ı'+'¯' → ī). 합자 ﬁ ﬀ ﬂ ﬃ 는 fi ff fl ffi 로.
- 줄 끝 하이픈(LaTeX 낱말 나눔): 이어 붙인 낱말이 원서 다른 곳에 있으면 붙이고, 하이픈 낱말이 다른 곳에 있으면 하이픈을 남김,
  둘 다 없으면 영어 낱말은 붙이고 부호 있는 빠알리 낱말은 하이픈을 남김 — 결정 목록은 …hyph.tsv
- 문단: LaTeX 양쪽 맞춤이라 줄이 짧게 끝나면 문단 끝, 첫 줄 들여쓰기(85pt)·글머리표(•)·큰 줄 사이도 새 문단.
  쪽이 넘어갈 때는 앞 쪽 마지막 줄이 꽉 찼으면 이어 붙임.
- 제목: 장 제목(Bold 24.8) · 소제목(Bold 14.3) → 'h'. 'Namo Tassa …'(BoldItalic 14.3) → 'p'.
- 각주: 본문 속 작은 숫자 → [^n], 쪽 아래 각주 → 'fn' 문단 '[^n]: …' (짝짓기에서 뺌).
- 차례(5쪽) → 'toc' ('제목, 쪽'), 1~4쪽(표지·빈 쪽·판권 면·다운로드 목록)·6쪽(빈 쪽)은 넣지 않음.
"""
import sys, re, json, os, collections, unicodedata
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(OUT, exist_ok=True)
d = pymupdf.open(pdf)
SKIP = {1, 2, 3, 4, 6}
TOC = {5}
LM, IND, RM = 68.0, 84.0, 351.5
LIG = {'ﬁ': 'fi', 'ﬀ': 'ff', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl'}
MAC = '̄'; UDOT = '̣'; ODOT = '̇'


def compose(chars):
    """한 줄의 글자(rawdict, 찍힌 순서 그대로) → [글자, 크기, x0, x1, y0], 따로 찍힌 부호를 겹치는 글자에 붙임"""
    cs = [c for c in chars]
    base_y = collections.Counter(round(c['bbox'][1], 1) for c in cs if c['c'].isalpha()).most_common(1)
    base_y = base_y[0][0] if base_y else 0
    isdot = lambda c: c['c'] == '.' and c['bbox'][1] > base_y + 1.5
    out = []; pend = None; drop_y = None
    for i, c in enumerate(cs):
        ch = c['c']; x0, y0, x1, y1 = c['bbox']
        if ch == ' ' and drop_y is not None and abs(y0 - drop_y) < 0.3: drop_y = None; continue   # 아래 점과 함께 찍힌 빈칸 조각
        if ch == ' ' and out and i + 1 < len(cs) and cs[i + 1]['bbox'][0] - out[-1][3] < 0.8: continue   # 앞뒤 글자 사이가 붙어 있는 빈칸 조각
        if ch == ' ' and any(n['c'].isalpha() and n['bbox'][0] < x0 + 0.5 for n in cs[i + 1:i + 3]): continue   # 뒤 글자가 빈칸 자리에 겹쳐 찍힘('sa ˙nkapp')
        if ch in ('¯', '˙') or isdot(c):
            mark = MAC if ch == '¯' else ODOT if ch == '˙' else UDOT
            if mark == UDOT: drop_y = y0
            ov = lambda a0, a1: max(0, min(x1, a1) - max(x0, a0))
            prev = out[-1] if out else None
            nxt = next((n for n in cs[i + 1:] if n['c'] != ' ' or abs(n['bbox'][1] - y0) > 0.3), None)
            po = ov(prev[2], prev[3]) if prev else -1
            no = ov(nxt['bbox'][0], nxt['bbox'][2]) if nxt is not None and nxt['c'].isalpha() else -1
            if no > po: pend = mark
            elif prev is not None: prev[0] = unicodedata.normalize('NFC', ('i' if prev[0] == 'ı' else prev[0]) + mark)
            continue
        if pend and ch.isalpha():
            ch = unicodedata.normalize('NFC', ('i' if ch == 'ı' else ch) + pend); pend = None
        ch = LIG.get(ch, ch)
        out.append([ch, c.get('size', 0), x0, x1, y0])
    return out


QX, QRM = 92, 324.2   # 인용 묶음 왼쪽 자리·오른쪽 끝
paras = []; cur = None; last_full = False; hyph = []; lastbody = None
# 1단계: 쪽마다 줄을 모음
pages = []
for i in range(d.page_count):
    pn = i + 1
    if pn in SKIP: continue
    rows = []
    for b in d[i].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            chars = []
            for s in l['spans']:
                for c in s['chars']:
                    c = dict(c); c['size'] = s['size']; c['font'] = s['font']; chars.append(c)
            if not ''.join(c['c'] for c in chars).strip(): continue
            rows.append({'bb': list(l['bbox']), 'chars': chars})
    # 같은 높이 줄 합치기
    rows.sort(key=lambda r: (round(r['bb'][1]), r['bb'][0]))
    R = []
    for r in rows:
        if R and abs(R[-1]['bb'][1] - r['bb'][1]) < 3 and r['chars'][0]['size'] > 7:
            R[-1]['chars'] = (R[-1]['chars'] + r['chars']) if r['bb'][0] >= R[-1]['bb'][0] else (r['chars'] + R[-1]['chars']); R[-1]['bb'][2] = max(R[-1]['bb'][2], r['bb'][2]); R[-1]['bb'][0] = min(R[-1]['bb'][0], r['bb'][0])
        else: R.append(r)
    lab = ''
    body = []
    for r in R:
        t = ''.join(c['c'] for c in r['chars']).strip()
        if r['bb'][1] > 550 and re.fullmatch(r'\d+', t): lab = t; continue
        body.append(r)
    pages.append((pn, lab or (str(pn - 6) if pn > 6 else ''), body))

# 낱말 사전(줄 끝 하이픈 판단용): 원서 전체 낱말
def rowtext(r):
    cs = compose(r['chars']); s = ''; px = None
    for ch, sz, x0, x1, y0 in cs:
        if px is not None and x0 - px > 1.6 and not s.endswith(' ') and ch != ' ': s += ' '
        s += ch; px = x1
    return re.sub(r'\s+', ' ', s).strip()

ALL = ' '.join(rowtext(r) for _, _, body in pages for r in body)
WORDS = collections.Counter(w.lower() for w in re.findall(r"[^\W\d_](?:[^\W\d_]|[-’'])*[^\W\d_]|[^\W\d_]", ALL))


def join(a, b, pg):
    if not a: return b
    m = re.search(r"([^\W\d_]+)-$", a)
    if m and b[:1].isalpha():
        left = m.group(1); right = re.match(r"[^\W\d_]+", b).group(0)
        whole, hy = (left + right).lower(), (left + '-' + right).lower()
        if WORDS.get(whole): keep = False; why = '이은 낱말이 원서에 있음'
        elif left.lower() in ('non', 'self', 'pre'): keep = True; why = '앞가지(non·self·pre) — 하이픈 남김'
        elif WORDS.get(hy): keep = True; why = '하이픈 낱말이 원서에 있음'
        elif re.search(r'[^\x00-\x7f]', left + right): keep = True; why = '부호 있는 빠알리 낱말 — 하이픈 남김'
        else: keep = False; why = '영어 낱말 나눔'
        hyph.append((pg, left + '-' + right, (left + '-' + right) if keep else (left + right), why))
        return a + b if keep else a[:-1] + b
    return a + ' ' + b


fnn = 0
for pn, pg, body in pages:
    if pn in TOC:
        rows = [r for r in body if r['chars'][0]['size'] < 20]
        if any(r['chars'][0]['size'] > 20 for r in body): paras.append({'pg': pg, 'k': 'h', 't': rowtext([r for r in body if r['chars'][0]['size'] > 20][0])})
        for r in rows:
            t = rowtext(r); t = re.sub(r'\s+(\d+)$', r', \1', t)
            paras.append({'pg': pg, 'k': 'toc', 't': t})
        cur = None; last_full = False; continue
    prev = None; first = True
    for r in body:
        c0 = next(c for c in r['chars'] if c['c'].strip())
        f, sz = c0['font'], round(c0['size'], 1); x0, y0, x1 = r['bb'][0], r['bb'][1], r['bb'][2]
        t = rowtext(r)
        # 각주(쪽 아래 작은 글씨)
        if y0 > 500 and sz <= 9.5 and re.match(r'\d', t):
            m = re.match(r'(\d+)\s*(.*)', t); fnn = m.group(1)
            cur = {'pg': pg, 'k': 'fn', 't': f'[^{m.group(1)}]: {m.group(2)}'}; paras.append(cur); continue
        # 본문 속 위첨자 각주 번호 → [^n]
        cs = compose(r['chars'])
        if any(c[1] < 9 and c[0].isdigit() for c in cs) and sz > 9:
            s = ''; px = None; prev_small = False
            for ch, sz0, cx0, cx1, cy0 in cs:
                small = sz0 < 9 and ch.isdigit()
                if px is not None and cx0 - px > 1.6 and not s.endswith(' ') and ch != ' ' and not small: s += ' '
                if small and not prev_small: s += '[^'
                if prev_small and not small: s += ']'
                s += ch; px = cx1; prev_small = small
            if prev_small: s += ']'
            t = re.sub(r'\s+', ' ', s).strip()
        if 'Bold' in f and 'Itali' not in f and sz > 12:      # 제목
            if cur is not None and cur['k'] == 'h' and prev is not None and y0 - prev[1] < 35 and cur['pg'] == pg: cur['t'] = cur['t'] + ' ' + t
            else: cur = {'pg': pg, 'k': 'h', 't': t}; paras.append(cur)
            prev = r['bb']; first = False; last_full = False; continue
        if 'BoldItal' in f and sz > 12:      # Namo Tassa … (가운데 두 줄)
            if cur is not None and cur['k'] == 'p' and cur.get('namo') and cur['pg'] == pg: cur['t'] = cur['t'] + ' ' + t
            else: cur = {'pg': pg, 'k': 'p', 't': t, 'namo': 1}; paras.append(cur)
            prev = r['bb']; first = False; last_full = False; continue
        bullet = c0['font'].startswith('CMSY') and c0['c'] == '•'
        if first:
            if cur is not None and cur['k'] == 'fn' and lastbody is not None: cur = lastbody   # 앞 쪽 각주 너머로 문단이 이어짐
            newp = cur is None or cur['k'] != 'p' or cur.get('namo') or bullet or not last_full or (IND - 2 < x0 < QX) \
                or (x0 > QX) != cur.get('q', False) and not (x0 > QX and cur.get('hang'))
        else:
            gap = y0 - prev[1]
            # 인용 묶음(첫 줄부터 왼쪽 95·오른쪽 324 — 본문보다 좁게 조판)은 그 오른쪽 끝을 기준으로, 번호·글머리표 항목의 둘째 줄(95)은 매달린 들여쓰기라 이어 붙임 (2026-11-17 검수)
            cq = cur is not None and cur.get('q', False)
            newp = cur is None or cur['k'] != 'p' or cur.get('namo') or bullet or cq != (x0 > QX) and not (x0 > QX and cur.get('hang')) \
                or gap > (15.5 if cq else 18) or prev[2] < (QRM if cq else RM) - 15 \
                or (x0 > IND - 2 and not cur.get('bul') and x0 < IND + 5)
        if newp: cur = {'pg': pg, 'k': 'p', 't': t}; paras.append(cur); cur['bul'] = bullet; cur['q'] = x0 > QX; cur['hang'] = 78 < x0 < QX and (bullet or bool(re.match(r'\d+\.\s', t)))
        else: cur['t'] = join(cur['t'], t, pg)
        prev = r['bb']; first = False
        last_full = x1 >= (QRM if cur.get('q') else RM) - 15; lastbody = cur
for p in paras: p.pop('namo', None); p.pop('bul', None); p.pop('q', None); p.pop('hang', None)
json.dump(paras, open(os.path.join(OUT, 'DL-0012.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
with open(os.path.join(OUT, 'DL-0012.en.hyph.tsv'), 'w') as f:
    f.write('원서 쪽\t줄 끝 모양\t뽑은 글\t까닭\n'); [f.write('\t'.join(x) + '\n') for x in hyph]
print(len(paras), '문단', dict(collections.Counter(p['k'] for p in paras)), '/ 줄 끝 하이픈', len(hyph),
      dict(collections.Counter(x[3] for x in hyph)))
