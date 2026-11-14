"""『테라와다 불교의범』(DL-0026, 한국테라와다불교, 개정판 2019) PDF → content/texts/DL-0026.json
  python3 tools/pdf2text_dl0026.py 책.pdf

한글(HWP)에서 내보낸 PDF. PDF 쪽 = 인쇄 쪽 (PDF 4쪽에 '- 4 -').
짜임: 1 속표지, 2 테라와다 불교의 이념, 3 상징마크, 4·5 펴내며, 6 빨리어 한글표기법(표는 그림으로), 7 그림,
8~9 삼귀의, 10~15 목차, 16 그림, 17~ 제1장(장마다 홀수 쪽 표지 + 앞 짝수 쪽 그림), 509 위대한 사람의 사유, 511 그림, 512 판권지(법보시용).
빠알리(왼쪽 쪽: 로마자 줄 + 한글 소리 줄)와 번역(오른쪽 쪽)이 마주 봄.

글자는 PDF 그대로(줄 끝 빈칸도 PDF 에 있음 — 빈칸이 있으면 낱말 사이, 없으면 붙여 이음).
- 줄 사이가 글자 크기의 1.75배보다 넓으면 새 문단, 좁으면 같은 문단 안에서 줄을 바꿈(게송·독송 줄은 인쇄본 줄 그대로).
  다만 줄이 오른쪽 끝까지 찬 산문은 이어 붙임(같은 글자 종류끼리: 로마자 줄 → 한글 소리 줄은 이어 붙이지 않음).
- 15pt 이상 줄(쪽 위 상자 제목)은 '## ', 장 표지(20pt)는 '^^ '·':: ', 가운데 줄 ':: ', 오른쪽 맞춤 '>> '.
- 각주: 본문의 작은 'N)' → [^N], 쪽 아래 'N) …'(8.8pt) → [^N]: … (35개)
- 쪽 번호 '- N -' 는 뺌. 그림은 쪽 안 자리 그대로 public/uploads/DL-0026-pNNN.jpg.
"""
import sys, re, json, os, collections, difflib
import fitz

pdf = sys.argv[1]
BK, ED = 'DL-0026', '개정판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = fitz.open(pdf)
N = src.page_count
TABLE_PAGES = {6}                       # 빨리어 한글표기법 표: 그림으로 (표 아래 설명 글은 글로)
log = collections.Counter()
JL = []
# 줄 끝에 빈칸이 여러 개 채워진 줄(손으로 줄을 바꾼 곳)은 PDF 만으로는 낱말 사이인지 알 수 없어 문맥으로 정함 (24곳 중 아래만 띄어 씀)
SPACE_AFTER_PAD = {(6, '받침으로 사'), (6, 'ㅁ, ㅂ, '), (32, '바훌라- '), (44, 'buddho'), (222, '따라 몸으로'), (222, '감퇴시키는 '),
                   (223, 'samann'), (223, '없다(~ '), (224, '것(avir'), (224, '도달하고, '), (224, '먼 곳까지 '), (353, '몸치장하는 '), (453, '때이며, 성')}
AMB = []
FOOTN = [1]
NOKEY = []
# 한글 파일에서도 낱말 가운데에서 엔터로 줄을 바꾼 곳(인쇄본 줄 모양을 맞추려고) — 글로 읽기에서는 붙여 씀 (글자는 그대로)
MIDWORD = [('다듬', '고 고쳐'), ('흘러', '야 할'), ('위힝수빠', '라띠야-'), ('것의 득', '실(得失)'), ('중생들을 제도', '하려는 부처님의 의지'),
           ('나태하게 하', '는 법이'), ('감청색을 나타', '내며'), ('털구멍으로부터 미', '묘한'), ('칠흑과 같이 뛰어', '난 것'),
           ('믿음직', '하여 세상을'), ('침상을 사용', '하여 아만심'), ('해제 후 까티나', '가사와 상가에')]
# --- 한글(HWP) 원본: 인쇄본 줄 끝이 '저절로 줄바꿈(빈칸 있음/없음)'인지 '엔터(줄 바꿈)'인지 (PDF 만으로는 알 수 없음)
import xml.etree.ElementTree as ET, subprocess
HWP = sys.argv[2]
_x = '/tmp/b26h/book.xml'
if not os.path.exists(_x) or os.path.getmtime(_x) < os.path.getmtime(HWP):
    os.makedirs('/tmp/b26h', exist_ok=True)
    with open(_x, 'wb') as f: subprocess.run(['hwp5proc', 'xml', HWP], stdout=f, check=True)
_N = lambda s: re.sub(r'\s|\[\^\d+\]|\*\*', '', s)
def jkey(a, b): return _N(a)[-10:] + '|' + _N(b)[:10]
HJ = {}
HT = re.sub(r'[ \t]+', ' ', ''.join(t.text or '' for t in ET.parse(_x).getroot().iter('Text')))
for _par in ET.parse(_x).getroot().iter():
    _seq = []
    for _p in [c for c in _par if c.tag == 'Paragraph']:
        for _k, _ls in enumerate(_p.findall('LineSeg')):
            _seq.append((''.join(t.text or '' for t in _ls if t.tag == 'Text'), _k > 0))
    _prev = None
    for _l, _wrap in _seq:
        if not _N(_l): _prev = None if not _wrap else _prev; continue
        if _prev is not None:
            HJ[jkey(_prev, _l)] = ((' ' if _prev.endswith(' ') or _l.startswith(' ') else '') if _wrap else 'BREAK')
        _prev = _l


def is_lat(ch): return bool(re.match(r'[A-Za-zÀ-ɏḀ-ỿ]', ch))
def is_kor(ch): return '가' <= ch <= '힣' or 'ㄱ' <= ch <= 'ㆎ'


def raw_lines(n):
    """[{y0,y1,x0,x1,size,fonts,text,fx(첫 글자 x)}] — 같은 높이의 조각은 한 줄로"""
    p = src[n - 1]; L = []
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            spans = []
            for s in l['spans']:
                t = ''.join(c['c'] for c in s['chars'])
                if not t: continue
                xs = [c['bbox'][0] for c in s['chars'] if c['c'].strip()]
                xe = [c['bbox'][2] for c in s['chars'] if c['c'].strip()]
                spans.append(dict(t=t, size=round(s['size'], 1), font=s['font'].split('+')[-1], x=xs[0] if xs else s['bbox'][0], x1=xe[-1] if xe else s['bbox'][0]))
            if not ''.join(s['t'] for s in spans).strip(): continue
            y0, y1 = l['bbox'][1], l['bbox'][3]
            L.append(dict(y0=y0, y1=y1, spans=spans))
    L.sort(key=lambda r: (round((r['y0'] + r['y1']) / 2), min(s['x'] for s in r['spans'])))
    out = []
    for r in L:
        m = (r['y0'] + r['y1']) / 2
        if out and abs((out[-1]['y0'] + out[-1]['y1']) / 2 - m) < 3.5:
            a = out[-1]; a['spans'] += r['spans']; a['y0'] = min(a['y0'], r['y0']); a['y1'] = max(a['y1'], r['y1']); a['merged'] = True
        else: out.append(r)
    for r in out:
        r['spans'].sort(key=lambda s: s['x'])
        sz = [s['size'] for s in r['spans'] if s['t'].strip()]
        r['size'] = max(sz); cc = collections.Counter()
        for s_ in r['spans']: cc[s_['size']] += len(s_['t'].strip())
        r['body'] = cc.most_common(1)[0][0]
        r['fx'] = min(s['x'] for s in r['spans'] if s['t'].strip()); r['x1'] = max(s['x1'] for s in r['spans'] if s['t'].strip())
    return out


def line_text(r, refs=True):
    o = ''
    for i, s in enumerate(r['spans']):
        t = s['t']
        if refs and s['size'] <= 10.4 and re.fullmatch(r'\s*\d{1,3}\)\s*', t) and i > 0 and r['size'] >= s['size'] + 1.5:
            num = t.strip()[:-1]
            o = o.rstrip() if not o.endswith(' ') else o
            o += f'[^{num}]' + (' ' if t.endswith(' ') else ''); log['ref'] += 1; continue
        if r.get('merged') and o and not o.endswith(' ') and not t.startswith(' ') and i > 0 and s['x'] - r['spans'][i - 1]['x1'] > 3:
            # 같은 줄의 떨어진 조각 사이: 한글 파일에 빈칸이 있을 때만 띄움
            L_, R_ = re.sub(r'\[\^\d+\]', '', o)[-5:], t.lstrip()[:5]
            if (L_ + ' ' + R_) in HT or (L_ + R_) not in HT: o += ' '; log['gap-space'] += 1
            else: log['gap-nospace'] += 1
        if 'Bold' in s['font'] and t.strip() and r['size'] < 13: o += f'**{t.strip()}**' + (' ' if t.endswith(' ') else ''); continue
        o += t
    return o


def join(a, b):
    if a.endswith(' '): return a.rstrip() + ' ' + b.strip()
    return a + b.strip()


IMGDIR = os.path.join(REPO, 'public/uploads')
images = []


def page_images(n):
    p = src[n - 1]; out = []
    for k, info in enumerate(p.get_image_info(xrefs=True)):
        x0, y0, x1, y1 = info['bbox']
        if x1 - x0 < 30: continue
        name = f'DL-0026-p{n:03d}' + (f'-{k + 1}' if k else '') + '.jpg'
        pix = p.get_pixmap(matrix=fitz.Matrix(4, 4), clip=fitz.Rect(x0, y0, x1, y1))
        from PIL import Image
        im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        if im.width > 1400: im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
        im.save(os.path.join(IMGDIR, name), quality=88)
        images.append('/uploads/' + name)
        out.append(dict(y0=y0, y1=y1, img='/uploads/' + name))
    return out


def table_image(n, y0, y1):
    p = src[n - 1]
    pix = p.get_pixmap(matrix=fitz.Matrix(4, 4), clip=fitz.Rect(40, y0 - 6, p.rect.width - 40, y1 + 6))
    name = f'DL-0026-p{n:03d}-table.png'
    pix.save(os.path.join(IMGDIR, name)); images.append('/uploads/' + name)
    return '/uploads/' + name


ALT = {1: '한국테라와다불교 상징마크', 3: '한국테라와다불교 상징마크'}


def convert_page(n):
    R = [r for r in raw_lines(n) if not re.fullmatch(r'\s*-\s*\d+\s*-\s*', line_text(r, False))]
    W = src[n - 1].rect.width
    # 각주
    foot, body = [], []
    infoot = False
    for r in R:
        t = line_text(r, False)
        m = re.match(r'\s*(\d{1,3})\)\s*(.*)$', t)
        if r['size'] < 9.3 and m and int(m.group(1)) == FOOTN[0]:
            FOOTN[0] += 1; infoot = True; foot.append(f'[^{m.group(1)}]: ' + m.group(2).rstrip() + (' ' if t.endswith(' ') else '')); continue
        if infoot and r['size'] < 9.3:
            v = HJ.get(jkey(foot[-1], t)); foot[-1] = foot[-1].rstrip() + (v if v not in (None, 'BREAK') else ' ') + t.strip(); continue
        body.append(r)
    foot = [f.strip() for f in foot]
    items = [dict(y0=r['y0'], y1=r['y1'], r=r) for r in body] + page_images(n)
    if n in TABLE_PAGES:   # 표가 차지하는 줄 → 그림 하나
        stop = min(it['y0'] for it in items if 'r' in it and line_text(it['r']).strip().startswith('1. 주의'))
        tb = [it for it in items if 'r' in it and 95 < it['y0'] < stop]
        y0, y1 = min(it['y0'] for it in tb), max(it['y1'] for it in tb)
        items = [it for it in items if it not in tb] + [dict(y0=y0, y1=y1, img=table_image(n, y0, y1), alt='빨리어 한글표기법 표')]
    items.sort(key=lambda it: it['y0'])
    txt = [it['r'] for it in items if 'r' in it]
    left = min([r['fx'] for r in txt if r['size'] < 13] or [70])
    right = max([r['x1'] for r in txt if r['size'] < 13] or [W - 70])
    # 1) 줄마다 모양(pre)을 정하고, 2) 줄 사이가 좁은 줄끼리 묶음(문단), 3) 묶음 안에서 오른쪽 끝까지 찬 산문 줄만 이어 붙임
    recs = []
    for it in items:
        if 'img' in it: recs.append(dict(img=it)); continue
        r = it['r']; raw = line_text(r); s = raw.strip()
        if not s: continue
        mid = (r['fx'] + r['x1']) / 2
        if r['size'] >= 18.5: pre = '^^ '
        elif r['size'] >= 13.4: pre = '## '
        elif (r['fx'] > left + 40 and abs(mid - W / 2) < 30 and r['x1'] < right - 20) or s.startswith('「'): pre = ':: '
        elif r['fx'] > W / 2 - 10 and r['x1'] > right - 40: pre = '>> '
        else: pre = ''
        recs.append(dict(r=r, s=s, pre=pre, lead=len(raw) - len(raw.lstrip(' ')), trail=len(raw) - len(raw.rstrip(' '))))
    blocks = []
    for k, x in enumerate(recs):
        p = recs[k - 1] if k else None
        if 'img' in x or p is None or 'img' in p or x['pre'] != p['pre'] or x['pre'] == '^^ ' or (x['r']['y0'] - p['r']['y1']) >= x['r']['body'] * 0.75 + 4:
            blocks.append([x])
        else: blocks.append(blocks.pop() + [x]) if blocks else blocks.append([x])
    paras = []
    LET = re.compile(r'[A-Za-zÀ-ɏḀ-ỿ가-힣]')
    kind = lambda c: 'k' if '가' <= c <= '힣' else 'l'
    for bl in blocks:
        if 'img' in bl[0]:
            it = bl[0]['img']; paras.append(f'![#{it.get("alt") or ALT.get(n, "그림")}]({it["img"]})'); continue
        pre = bl[0]['pre']
        if pre == '## ':
            t = bl[0]['s']
            for b in bl[1:]:
                v = HJ.get(jkey(t, b['s'])); t += (v if v not in (None, 'BREAK') else ' ') + b['s']
            paras.append(pre + t); continue
        out = []; cur = None
        for k, x in enumerate(bl):
            if cur is None: cur = dict(lines=[x['s']], last=x); continue
            a_ = cur['lines'][-1]; b_ = x['s']
            v = HJ.get(jkey(a_, b_))
            hang = re.match(r'(\d{1,2}[.)]|[①-⑳]|\(\d+\)|\d+\)|-|•|·)', cur['lines'][0])
            if v == 'BREAK' and any(a_.endswith(x) and b_.startswith(y) for x, y in MIDWORD):
                cur['lines'][-1] = a_ + b_; log['midword'] += 1; cur['last'] = x; continue
            if v is None or v == 'BREAK':
                if v is None: log['nokey'] += 1; NOKEY.append((n, a_[-10:], b_[:10]))
                if x['lead'] >= 2 and x['lead'] > cur['last']['lead'] and not hang: out.append(cur); cur = dict(lines=[b_], last=x); continue   # 앞 줄보다 들여 쓴 줄 = 새 문단
                cur['lines'].append(b_)
            else:
                cur['lines'][-1] = a_ + v + b_; log['wrap'] += 1
            cur['last'] = x
        out.append(cur)
        for c in out: paras.append(pre + '\n'.join(c['lines']).strip())
    return paras, foot


pages = []
for n in range(1, N + 1):
    ps, fs = convert_page(n)
    pages.append((f'{n}쪽', ps, fs))

# --- 목차 쪽(10~15) → %% 차례 문단 (글자는 그대로, 점선만 빼고 쪽 번호는 ' | ' 뒤로, 두 줄로 인쇄된 항목은 한 줄로)
def lvl(t): return '-- ' if re.match(r'^\(\d+\)', t) else ('- ' if re.match(r'^\d+\.', t) or t.startswith('《') else '')
def toc_page(n):
    R = [r for r in raw_lines(n) if not re.fullmatch(r'\s*-\s*\d+\s*-\s*', line_text(r, False))]
    out = []   # [본문, 쪽 또는 None, 종류]
    for r in R:
        t = re.sub(r'\s+$', '', line_text(r, False)).strip()
        if not t or t.replace(' ', '') == '【목차】': continue
        m = re.match(r'^(.*?)\s*\.{3,}\s*(\d+)$', t)
        title, pg = (m.group(1).strip(), m.group(2)) if m else (t, None)
        if re.match(r'^제\d+장', title): out.append([title, pg, 'ch']); continue
        new = re.match(r'^(\d+\.|\(\d+\)|《)', title) or not out or out[-1][2] == 'front'
        if not new and out:
            last = out[-1]
            if last[2] == 'ch' or last[1] is None: last[0] += ' ' + title; last[1] = last[1] or pg; continue
            if pg is None: last[0] += ' ' + title; continue   # 쪽 번호 뒤에 인쇄된 둘째 줄
        out.append([title, pg, 'front' if not re.match(r'^(\d+\.|\(\d+\)|《)', title) and n == 10 and not any(o[2] == 'ch' for o in out) else 'item'])
    return out
TOC = []
for n in range(10, 16): TOC += [(n, *x) for x in toc_page(n)]
for n in range(10, 16):
    ls = []
    for (m, t, pg, k) in TOC:
        if m != n: continue
        if k == 'ch' and ls: ls.append('~')
        ls.append((lvl(t) if k == 'item' else '') + t + (f' | {pg}' if pg else ''))
    head = [p for p in pages[n - 1][1] if p.startswith('^^ ')]
    pages[n - 1] = (pages[n - 1][0], head + ['%% ' + '\n'.join(ls)], pages[n - 1][2])

# 속표지·판권지의 큰 글씨는 제목이 아니므로 가운데 줄로
for n in (1, 512):
    pages[n - 1] = (pages[n - 1][0], [(':: ' + p[3:]) if p.startswith('## ') else p for p in pages[n - 1][1]], pages[n - 1][2])

# --- 목차(읽기 화면 장·소제목)
cover = {}
for n, ps, fs in pages:
    hs = [p[3:].strip() for p in ps if p.startswith('^^ ')]
    if hs and re.match(r'^제\d+장', hs[0]): cover[int(n[:-1])] = re.sub(r'\s+', ' ', ' '.join(hs))
chapters = [('속표지', 1), ('테라와다 불교의 이념', 2), ('한국테라와다불교 상징마크', 3), ('『 테라와다 불교의범 』을 펴내며', 4),
            ('『 테라와다 불교의범 』제2판을 펴내며', 5), ('빨리어 한글표기법', 6), ('삼귀의 (Tisaraṇa)', 8), ('목차', 10)]
chapters += [(t, n) for n, t in sorted(cover.items())]
chapters += [('《위대한 사람의 사유》(Mahā purisa vitakka)', 509), ('판권지', 512)]
subs = []
perpage = collections.defaultdict(list)
for (m, t, pg, k) in TOC:
    if k == 'item' and pg and not t.startswith('《') and int(pg) > 10 and int(pg) != 509: perpage[int(pg)].append(t)
# 목차의 쪽 번호가 실제와 다른 곳이 있어(예: '2. 삼귀의 · 8계 청함 … 350' 은 실제 348쪽) 본문 제목(## 줄)에서 찾음 — 앞뒤 4쪽 안, 번호와 빠알리 낱말이 맞는 제목
HEADS = [(n, k, p[3:].strip()) for n in range(1, N + 1) for k, p in enumerate([q for q in pages[n - 1][1] if q.startswith('## ')])]
used = set()
for pg, items in sorted(perpage.items()):
    for t in items:
        num = re.match(r'^(\d+\.|\(\d+\))', t).group(1)
        lat = set(w.lower() for w in re.findall(r'[A-Za-zÀ-ɏḀ-ỿ]{3,}', t))
        cands = [(abs(n - pg), n, k, h) for n, k, h in HEADS if abs(n - pg) <= 4 and (n, k) not in used and h.startswith(num)
                 and (not lat or lat & set(w.lower() for w in re.findall(r'[A-Za-zÀ-ɏḀ-ỿ]{3,}', h)))]
        if not cands and t[3:8] in ('담마의 날', '상가의 날'):   # 붓다·담마·상가의 날은 한 의식(440쪽) — 담마·상가의 날은 그 게송 자리로
            cands = [(0, n, k, h) for n, k, h in HEADS if h == t[3:8] + ' 게송']
        if not cands: print('목차 항목 제목 못 찾음', pg, t); subs.append(dict(title=re.sub(r'\s+', ' ', t), page=pg, sub=True)); continue
        d, n, k, h = min(cands, key=lambda c: (c[0] if c[1] >= pg - 4 else 99, c[1]))
        if n != pg: print('목차 쪽 번호와 다른 곳', t, pg, '→', n)
        used.add((n, k))
        subs.append(dict(title=re.sub(r'\s+', ' ', t), page=n, sub=True, at=(h[:20] if k > 0 else '')))
toc = [dict(title=t, page=n, sub=False) for t, n in chapters] + subs
toc.sort(key=lambda x: (x['page'], x.get('sub', False)))
body = ''
for name, ps, fs in pages:
    body += f'=== {name} ===\n' + '\n\n'.join(p for p in ps + fs if p.strip()) + '\n\n'
body = body.rstrip() + '\n'
import unicodedata
_ht = ''.join(t.text or '' for t in ET.parse(_x).getroot().iter('Text'))
for _m in re.finditer('[\uf900-\ufaff]', _ht):
    _l, _c, _r = _ht[max(0, _m.start() - 3):_m.start()], _m.group(), _ht[_m.end():_m.end() + 2]
    _plain = _l + unicodedata.normalize('NFKC', _c) + _r
    if _plain in body: body = body.replace(_plain, _l + _c + _r, 1); log['compat'] += 1
    else: log['compat-miss'] += 1; print('호환 한자 못 찾음', repr(_l + _c + _r))
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': sorted(set(images)), 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print(log); json.dump(NOKEY, open('/tmp/b26/nokey.json', 'w'), ensure_ascii=False)
print(f'쪽 {len(pages)} · 장 {len(chapters)} · 소제목 {len(subs)} · 그림 {len(set(images))} → {out}')
