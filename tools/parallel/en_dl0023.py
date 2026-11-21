"""『법구경 이야기』 1~3권(DL-0023·0024·0025) 원서 대조 — 영어 원서 글 뽑기
The Dhamma Verses Commentary (E W Burlingame, Ānandajoti Bhikkhu, August 2024, Ancient Buddhist Texts — Public Domain)
Microsoft Word 2010 PDF 1,156쪽, PDF 쪽 = 인쇄 쪽 + 8 (쪽 위 머리글의 끝 숫자가 쪽 이름).

  python3 tools/parallel/en_dl0023.py 원서.pdf
  → tools/out/parallel/DL-0023.en.paras.json (1~4장) · DL-0024 (5~14장) · DL-0025 (15~26장)

원서 문단 종류(k):
  h   장 제목(18pt)·이야기 제목(14pt)·빠알리 제목(12pt)·과거 이야기 제목('1a Story of the Past: …', 굵은 11pt)
  pq  이야기 머리 정보(Dhp N·CST4·Burlingame·Compare·줄거리·Cast·Keywords — 편자가 붙인 것, 한국어판에 없음) — 짝짓지 않음
  hv  이야기 첫머리의 게송(**** 바로 뒤, 한국어판은 '게송 N번을 설하셨다'로만 씀) — 짝짓지 않고 다음 묶음에 붙여 보임
  pv  빠알리 게송(굵은 10pt) — 짝짓지 않고 다음 묶음에 붙여 보임
  p   본문·게송(줄은 줄 바꿈으로)
  fn  각주('[^n]: …', AJ·BG)
글자는 PDF 글자 그대로 — 단, 이 PDF 의 글꼴이 작은따옴표를 다른 글자로 찍은 것(‖ → ’ 1,858곳, ― → ‘ 522곳)만 바로잡음.
"""
import sys, re, json, os
import fitz

PDF = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out', 'parallel')
d = fitz.open(PDF)
QFIX = str.maketrans({'‖': '’', '―': '‘'})
BOOKS = [('DL-0023', 1, 4), ('DL-0024', 5, 14), ('DL-0025', 15, 26)]

def seps(p):
    """각주 구분선(가로 144pt, 이어지는 각주는 375pt — 둘레에 칠한 상자가 없는 것)"""
    dr = p.get_drawings(); fills = [x['rect'] for x in dr if x['rect'].height >= 2]
    ys = []
    for x in dr:
        r = x['rect']
        if r.height < 2 and r.y0 > 250 and (140 < r.width < 150 or (365 < r.width < 380 and not any(abs(f.y0 - r.y0) < 30 or abs(f.y1 - r.y0) < 30 for f in fills))):
            ys.append(r.y0)
    return min(ys) if ys else None

paras = []   # {pg, pdf, k, t, vagga}
cur = None   # 열린 문단
vagga = 0
fn_cur = None
fn_last = None
CONT = []
meta = False; after_meta = False

def close():
    global cur
    if cur and cur['t'].strip():
        cur['t'] = re.sub(r'[ \t]+\n', '\n', cur['t']).strip()
        paras.append(cur)
    cur = None

def ltext(l, body=True):
    """줄 글자 — 본문의 작은 위첨자 숫자는 [^n]"""
    out = ''
    for s in l['spans']:
        t = s['text']
        if body and s['size'] < 8.5 and re.fullmatch(r'\s*\d+\s*', t): out += f'[^{t.strip()}]'
        else: out += t
    return out.translate(QFIX)

START = next(i for i in range(d.page_count) if '1. The Chapter about the Pairs' in d[i].get_text())
END = next(i for i in range(d.page_count) if 'Conclusion, Nigamanakath' in d[i].get_text() and i > START)
prev_line = None; JOINQ = []
for pn in range(START, END):
    p = d[pn]; sy = seps(p)
    lines = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans'])
            if not t.strip(): continue
            lines.append(l)
    lines.sort(key=lambda l: (round(l['bbox'][1]), l['bbox'][0]))
    head = [l for l in lines if l['bbox'][1] < 55]
    pg = re.findall(r'\d+', ''.join(s['text'] for l in head for s in l['spans']))
    pg = pg[-1] if pg else str(pn - 7)
    body = [l for l in lines if l['bbox'][1] >= 55 and (sy is None or l['bbox'][1] < sy)]
    foot = [l for l in lines if sy is not None and l['bbox'][1] >= sy]
    page_first = True
    for l in body:
        s0 = l['spans'][0]; size = s0['size']; bold = 'Bold' in s0['font']; x0 = l['bbox'][0]; y0 = l['bbox'][1]
        t = ltext(l); ts = t.strip()
        gap = (y0 - prev_line['bbox'][1]) if (prev_line is not None and not page_first) else None
        if size >= 17.5:   # 장 제목 (두 줄)
            m = re.match(r'(\d+)\.', ts)
            if m: vagga = int(m.group(1)); close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': 'h', 't': ts, 'v': vagga}
            else: cur['t'] += ' ' + ts
            meta = False
        elif size >= 13.5 and bold:   # 이야기 제목
            close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': 'h', 't': ts, 'v': vagga, 'story': re.match(r'(\d+\.\d+)', ts).group(1) if re.match(r'\d+\.\d+', ts) else None}
            meta = True
        elif size >= 11.5 and bold:   # 빠알리 제목
            close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': 'h', 't': ts, 'v': vagga, 'pali': 1}; close()
        elif meta and size < 10.5 and not bold:   # 이야기 머리 정보 (**** 까지 — 10pt 글, '**'·'***' 도 있음)
            if re.fullmatch(r'\*{2,}', ts):
                close(); meta = False; after_meta = True
            elif cur and cur['k'] == 'pq' and gap is not None and gap < 17.5:
                cur['t'] += ' ' + ts
            else:
                close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': 'pq', 't': ts, 'v': vagga}
        elif bold and size >= 10.5 and x0 < 85 and (re.match(r'\d+[a-z]\b', ts) or re.match(r'Story of the (Past|Present)', ts)):   # 과거 이야기 제목
            close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': 'h', 't': ts, 'v': vagga}; close()
        elif not meta and size < 10.5 and not bold and x0 < 80:   # 본문 자리의 10pt 글 — 편자(BG)의 해설(5장 앞 '5.1 The frame-story…' 등, 한국어판에 없음) → pq
            if cur and cur['k'] == 'pq' and not (gap is not None and gap > 17.5): cur['t'] = cur['t'].rstrip() + ('' if cur['t'].rstrip().endswith('-') else ' ') + ts
            else: close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': 'pq', 't': ts, 'v': vagga}
            CONT.append((pg, ts[:40]))
        else:
            if meta: close(); meta = False; after_meta = True
            kind = 'pv' if (bold and size < 10.5) else 'p'
            verse = x0 > 84 and not (x0 < 82)   # 들여 쓴 게송 줄 (과거 이야기 본문은 80.5)
            if kind == 'p' and after_meta and verse: kind = 'hv'
            if not verse and kind == 'p': after_meta = False
            # 새 문단?
            new = cur is None or cur['k'] != kind or (gap is not None and gap > 17.5) or cur.get('verse') != verse
            if page_first and cur is not None and cur['k'] == kind and cur.get('verse') == verse and kind == 'p':
                # 쪽을 넘는 문단: 앞 쪽 마지막 줄이 찼거나 문장이 안 끝났으면 이어 붙임
                lastt = cur['t'].rstrip()
                full = prev_line is not None and prev_line['bbox'][2] > 395
                ended = re.search(r'[.?!:”’)\]}]$|\[\^\d+\]$', lastt)
                if verse: new = not (full or not ended)
                else: new = not (full or not ended or ts[:1].islower())
            if new:
                close(); cur = {'pg': pg, 'pdf': pn + 1, 'k': kind, 't': ts, 'v': vagga, 'verse': verse}
            else:
                if (verse or kind in ('pv', 'hv')) and not (verse and kind == 'p' and prev_line is not None and (prev_line['bbox'][2] > 380 or abs(prev_line['bbox'][1] - y0) < 2)):   # 같은 높이 낱말(1114쪽 그림 둘레 글)도
                    cur['t'] += '\n' + ts
                elif verse and kind == 'p':   # 들여 쓴 산문 인용(경 인용·편자 글) — 줄이 오른쪽 끝(380pt 넘게)까지 찼으면 이어 붙임
                    JOINQ.append((pg, cur['t'].rstrip()[-30:] + ' | ' + ts[:30])); cur['t'] = cur['t'].rstrip() + ('' if cur['t'].rstrip().endswith('-') else ' ') + ts
                else: cur['t'] = cur['t'].rstrip() + ('' if cur['t'].rstrip().endswith('-') else ' ') + ts
        prev_line = l; page_first = False
    # 각주
    for l in foot:
        s0 = l['spans'][0]; ts = ltext(l, body=False).strip()
        m = re.match(r'(\d+)\s*(.*)', ts) if s0['size'] < 8.5 else None
        if m and fn_last is not None and int(m.group(1)) != fn_last + 1: m = None   # 각주 글 속 위첨자 줄 번호(‘279²³’)가 줄 첫머리에 온 것
        if m:
            fn_last = int(m.group(1))
            fn_cur = {'pg': pg, 'pdf': pn + 1, 'k': 'fn', 't': f'[^{m.group(1)}]: ' + m.group(2), 'v': vagga}
            paras.append(fn_cur)
        elif fn_cur is not None:
            t0 = fn_cur['t'].rstrip()
            fn_cur['t'] = t0 + ('' if t0.endswith('-') else ' ') + ts
close()
print('들여 쓴 산문 인용에서 이어 붙인 줄', len(JOINQ)); open(os.path.join(OUT, 'DL-0023.en.joinq.txt'), 'w').write('\n'.join(f'{a}\t{b}' for a, b in JOINQ))
print('본문 자리로 넘어온 각주 줄', len(CONT)); [print('  ',c) for c in CONT]

for p in paras:
    p['t'] = re.sub(r'[  ]{2,}', ' ', p['t']).strip()
    p.pop('verse', None)
os.makedirs(OUT, exist_ok=True)
for bid, a, b in BOOKS:
    L = [dict(p) for p in paras if a <= p['v'] <= b]
    for p in L: p['pg'] = str(p['pg']); p.pop('v', None)
    json.dump(L, open(os.path.join(OUT, f'{bid}.en.paras.json'), 'w'), ensure_ascii=False, indent=0)
    from collections import Counter
    print(bid, len(L), Counter(p['k'] for p in L), '이야기', sum(1 for p in L if p.get('story')))
