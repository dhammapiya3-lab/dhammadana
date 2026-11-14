"""『빨리어 예불과 의례집』(DL-0027, 빅쿠 까따담모 엮음, 2판 2021) PDF → content/texts/DL-0027.json
  python3 tools/pdf2text_dl0027.py 책.pdf

짜임: 1 표지, 3 예불의 공덕, 5 서문(i), 6 빨리어 한글표기 및 운율(ii), 7~10 목차(iii~vi), 장마다 표지 쪽(쪽 번호 없음),
233 판권지. 쪽 이름은 쪽 아래에 인쇄된 번호('- 9 -') 그대로, 번호가 없는 쪽은 이름 없이.
본문은 한 묶음이 세 줄: 빠알리 로마자 줄 / 한글 소리 줄(MDSol) / 한글 번역(길면 다음 줄로 넘어감).
- 묶음 하나 = 문단 하나, 로마자·소리 줄은 인쇄본 줄 그대로, 번역 줄이 넘어간 곳은 이어 붙임(줄 끝 빈칸이 있으면 띄어 씀).
- 두 단으로 나란히 인쇄된 묶음(왼쪽·오른쪽)은 왼쪽 묶음, 오른쪽 묶음 순서로 한 문단에.
- '빣'(인쇄본의 줄표 글자) → '-'. 장음 표시 '˞' 는 그대로.
- 18pt 이상 줄은 '## ' 소제목, 장 첫 쪽의 20pt 줄도 '## '(장 제목과 같아 화면에서는 숨음).
- 희미한 글자(회색 b2b2b2·c0c0c0 — 인도자가 없거나 간략히 할 때 생략하는 부분)는 {{…}} 로 감쌈.
- 각주: 위첨자 'N)' → [^N], 쪽 아래 'N) …' → [^N]: …
- 쪽 위 머리글(장 이름)·쪽 번호·모서리 꾸밈 그림은 뺌. 6쪽(ii) 표기법 표와 운율 보기는 그림으로.
"""
import sys, re, json, os, collections, unicodedata
import fitz

pdf = sys.argv[1]
BK, ED = 'DL-0027', '2판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = fitz.open(pdf)
N = src.page_count
log = collections.Counter()
FAINT = {0xb2b2b2, 0xc0c0c0}
PRON_FONTS = ('MDSol', '±½')
images = []


def fix(t):
    t = t.replace('빣', '-').replace('\ue719', '-').replace('\ue71e', '-')   # 인쇄본 줄표가 글꼴 안 다른 글자로 들어 있음
    t = re.sub(r'([āīūĀĪŪ])\u0304', r'\1', t)                                # 80쪽: 장음 표시가 두 번 들어간 글자(ā + ̄)
    t = re.sub(r'([aiuAIU])\u0304+', lambda m: unicodedata.normalize('NFC', m.group(1) + '\u0304'), t)   # 호환 한자(不 六 律)는 그대로 두려고 NFC 전체는 쓰지 않음
    return re.sub(r'(?<=[A-Za-zÀ-ɏḀ-ỿ])빨(?=[A-Za-zÀ-ɏḀ-ỿ])', '-', t)   # 몇 쪽은 줄표가 '빨' 글자로 들어 있음


def spans_of(n):
    p = src[n - 1]; S = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if not s['text'].strip(): continue
                f = s['font'].split('+')[-1]
                S.append(dict(t=s['text'], x0=s['bbox'][0], x1=s['bbox'][2], y0=s['bbox'][1], y1=s['bbox'][3], size=s['size'],
                              font=f, color=s['color'], sup=bool(s['flags'] & 1)))
    # 그림자 꾸밈: 같은 글자가 조금 비켜 회색·흰색으로 한 번 더 찍힌 것은 뺌 (더 진한 글자만 남김)
    dark = lambda c: sum((c >> k) & 255 for k in (16, 8, 0))
    out = []
    for s in S:
        t = s['t'].strip()
        tw = [o for o in S if o is not s and dark(o['color']) < dark(s['color']) and abs(o['y0'] - s['y0']) < 2.5
              and min(o['x1'], s['x1']) - max(o['x0'], s['x0']) >= 0.5 * max(1, s['x1'] - s['x0']) and t and t in o['t']]
        if tw:
            # 회색 그림자가 깔린 검은 글자 = 인쇄본의 '희미한 글자'(생략할 수 있는 부분) → 검은 글자를 희미한 글자로 표시
            if s['color'] in FAINT:
                for o in tw:
                    if dark(o['color']) < 200: o['faint'] = True
                log['희미'] += 1
            else: log['그림자'] += 1
            continue
        out.append(s)
    return out


def lines_of(n, S):
    S = sorted(S, key=lambda s: ((s['y0'] + s['y1']) / 2, s['x0']))
    L = []
    for s in S:
        c = (s['y0'] + s['y1']) / 2
        tol = 0.5 * max(s['size'], 9)
        for l in L:
            if abs(l['c'] - c) <= max(tol, 0.5 * l['size']): l['spans'].append(s); break
        else:
            L.append(dict(c=c, size=s['size'], spans=[s]))
        if not s['sup']: L[-1]['size'] = max(L[-1]['size'], s['size']) if L[-1]['spans'][0] is not s else s['size']
    for l in L:
        l['spans'].sort(key=lambda s: s['x0'])
        l['size'] = max(s['size'] for s in l['spans'] if not s['sup']) if any(not s['sup'] for s in l['spans']) else l['size']
        l['x0'] = min(s['x0'] for s in l['spans']); l['x1'] = max(s['x1'] for s in l['spans'])
        l['y0'] = min(s['y0'] for s in l['spans'] if not s['sup']) if any(not s['sup'] for s in l['spans']) else l['spans'][0]['y0']
    L.sort(key=lambda l: l['c'])
    return L


def seg_text(spans):
    """조각들을 이어 글로 — 희미한 글자는 {{ }}, 위첨자 번호는 [^N]"""
    out = ''; prev = None; faint = False
    for s in spans:
        t = fix(s['t'])
        if s['sup'] and re.fullmatch(r'\s*\d+\)\s*', t):
            t = '[^' + re.sub(r'\D', '', t) + ']'
        if prev is not None:
            gap = s['x0'] - prev['x1']
            if gap > 0.3 * s['size'] and not out.endswith(' ') and not t.startswith(' ') and not t.startswith('[^'): out += ' '
        f = s['color'] in FAINT or s.get('faint')
        if f and not faint: out += '{{'; faint = True
        if not f and faint:
            m = re.search(r'\s+$', out); ws = m.group() if m else ''
            out = out[:len(out) - len(ws)] + '}}' + ws; faint = False
        out += t; prev = s
    if faint:
        m = re.search(r'\s+$', out); ws = m.group() if m else ''
        out = out[:len(out) - len(ws)] + '}}' + ws
    out = re.sub(r'(?<=[A-Za-zÀ-ɏḀ-ỿ])빨(?=[A-Za-zÀ-ɏḀ-ỿ])', '-', out)
    out = re.sub(r'\{\{(\s+)', r'\1{{', out)
    out = out.replace('{{}}', '')
    return out


def kind(l):
    pr = sum(len(re.sub(r'\s', '', s['t'])) for s in l['spans'] if s['font'].startswith(PRON_FONTS))
    t = ''.join(s['t'] for s in l['spans'])
    lat = len(re.findall(r'[A-Za-zÀ-ɏḀ-ỿ]', t)); han = len(re.findall(r'[가-힣]', t))
    if re.fullmatch(r'[\d\s{}]+', t) and l['size'] < 8: return 'num'
    if pr and (pr >= 0.5 * (lat + han) or l['spans'][0]['font'].startswith(PRON_FONTS)): return 'pron'
    if 13.6 <= l['size'] < 17.5: return 'sub'
    if lat > han: return 'lat'
    return 'ko'


def split_cols(l, mid):
    """가운데(mid) 근처에서 크게 벌어진 줄 → (왼쪽 조각들, 오른쪽 조각들)"""
    sp = l['spans']
    for i in range(1, len(sp)):
        if sp[i]['x0'] >= mid - 15 and sp[i - 1]['x1'] <= mid + 5 and sp[i]['x0'] - sp[i - 1]['x1'] > 1.2 * l['size']:
            return sp[:i], sp[i:]
    return None


# ---------- 쪽마다
PAGES = []   # (이름, [문단], [각주])
LABEL = {}
for n in range(1, N + 1):
    S = spans_of(n)
    lab = ''
    keep = []
    for s in S:
        t = s['t'].strip()
        if s['font'].startswith('SandKm') or (s['y0'] > 770 and re.fullmatch(r'-\s*[ivxⅰⅱⅲⅳⅴⅵ\d]+\s*-', t)):
            m = re.fullmatch(r'-\s*(\S+)\s*-', t)
            if m: lab = m.group(1)
            continue
        if s['y1'] < 66 and s['color'] == 0x404040: continue      # 쪽 위 머리글(장 이름)
        keep.append(s)
    lab = {'ⅰ': 'i', 'ⅱ': 'ii', 'ⅲ': 'iii', 'ⅳ': 'iv', 'ⅴ': 'v', 'ⅵ': 'vi'}.get(lab, lab)
    if n == 5 and not lab: lab = 'i'
    LABEL[n] = lab
    # 각주 자리: 쪽 아래 작은 글씨 'N)' 줄부터
    fny = None
    for s in keep:
        if s['y0'] > 600 and s['size'] < 10.5 and not s['sup'] and re.match(r'^\s*\d+\)', s['t']) and s['x0'] < 120:
            fny = s['y0'] if fny is None else min(fny, s['y0'])
    body = [s for s in keep if fny is None or s['y0'] < fny - 1]
    fnS = [s for s in keep if fny is not None and s['y0'] >= fny - 1 and not set(s['t'].strip()) <= set('-')]
    BL = lines_of(n, body)
    # 점선 구분 줄(꾸밈)은 뺌 — 각주 번호가 붙은 점선('------------20)': 여기부터 생략할 수 있음)은 그대로 둠
    BL = [l for l in BL if not (re.fullmatch(r'-{4,}', ''.join(x['t'] for x in l['spans']).strip()))]
    PAGES.append(dict(n=n, lab=lab, lines=BL, fn=lines_of(n, fnS)))


def PR(t):
    # 한글 소리 줄: @@…@@ → 화면에서 원본처럼 굵은 둥근 글꼴(주아) (운영자 요청, 2026-11-15)
    t = t.strip()
    return f'@@{t}@@' if t else t


def IT(t):
    # 빠알리 로마자 줄: °°…°° → 화면에서 기울임(인쇄본 일러두기 '빨리어 표기는 이탤릭체로 통일') (운영자 요청, 2026-11-15)
    t = t.strip()
    return f'°°{t}°°' if t else t


def ko_join(a, b):
    return a + b if not a.endswith(' ') else a + b.lstrip()


JOINS = []
JUST5 = [('출간 하는', '출간하는'), ('적합하였 지만', '적합하였지만'), ('불자들 과의', '불자들과의'), ('가다 듬어지길', '가다듬어지길'), ('주관 하였다', '주관하였다'), ('선한 마음 님과', '선한 마음님과')]
TABLE_IMG = {}
def crop(n, rect, name):
    pix = src[n - 1].get_pixmap(dpi=220, clip=fitz.Rect(*rect))
    path = os.path.join(REPO, 'public/uploads', name)
    pix.save(path)
    images.append('/uploads/' + name); return '/uploads/' + name


def build_paras(P, prose=False, each=False):
    n, L = P['n'], P['lines']
    if not L: return []
    kL = [l for l in L if kind(l) == 'ko']
    R = max([l['x1'] for l in kL] or [520])
    mid = 297.6
    paras = []; cur = None
    prev = None
    for l in L:
        k = kind(l); sz = l['size']
        if prose and k != 'num' and sz < 17.5: k = 'ko'
        if each and sz < 17.5: k = 'sub'
        txt = seg_text(l['spans']).rstrip()
        t0 = seg_text(l['spans'])
        if sz >= 17.5 and k != 'pron':
            if cur and cur.get('h') and prev is not None and l['c'] - prev['c'] < 1.6 * sz:
                cur['lines'][-1] += (' ' if not cur['lines'][-1].endswith(' ') else '') + txt.strip(); prev = l; continue
            cur = dict(h=True, lines=[txt.strip()], src=[l]); paras.append(cur); prev = l; continue
        new = cur is None or cur.get('h')
        if not new:
            pk = prev['_k']
            gap = l['y0'] - prev['y0']
            if k == 'num' or k == 'sub' or pk == 'sub': new = True
            elif k == 'lat' and pk not in ('lat', 'num'): new = True
            elif k == 'pron' and pk == 'ko': new = True
            elif k == 'ko' and pk == 'ko':
                wrap = prev['x1'] > R - 30 and l['x0'] <= prev['x0'] + 1.5 and gap < 2.3 * sz
                if re.match(r'^\s*(\d+\)|[①-⑳]|\(예\)|\(보기\)|<|\[|\*|[∰∭~～『]|[가-힣]\.\s)', t0): wrap = False
                new = not wrap
                if wrap: l['_wrap'] = True
            elif gap > 2.6 * max(sz, 11): new = True
        l['_k'] = k
        if new:
            cur = dict(h=False, lines=[], src=[]); paras.append(cur)
        if l.get('_wrap'):
            JOINS.append((n, cur['lines'][-1][-12:], t0[:10], cur['lines'][-1].endswith(' ')))
            cur['lines'][-1] = ko_join(cur['lines'][-1], t0.rstrip() if not t0.endswith(' ') else t0)
            cur['_raw_end'] = t0
        else:
            cur['lines'].append(PR(t0) if k == 'pron' else IT(t0) if k == 'lat' else t0)
        cur['src'].append(l)
        prev = l
    out = []
    for p in paras:
        if p['h']:
            out.append('## ' + re.sub(r'\s+', ' ', p['lines'][0]).strip()); continue
        # 두 단: 문단의 모든 줄이 가운데에서 갈라지면 왼쪽 묶음 → 오른쪽 묶음
        src_lines = p['src']
        cols = [split_cols(l, mid) for l in src_lines]
        if len(src_lines) >= 2 and all(cols) and not any(l.get('_wrap') for l in src_lines):
            F = lambda l: PR if l['_k'] == 'pron' else IT if l['_k'] == 'lat' else str.strip
            left = [F(l)(seg_text(c[0])) for c, l in zip(cols, src_lines)]
            right = [F(l)(seg_text(c[1])) for c, l in zip(cols, src_lines)]
            out.append('\n'.join(left + right)); log['2단'] += 1; continue
        ls = [x.strip() for x in p['lines'] if x.strip()]
        out.append('\n'.join(ls))
    return out


def fn_paras(P):
    out = []
    for l in P['fn']:
        t = seg_text(l['spans']).strip()
        m = re.match(r'^(\d+)\)\s*(.*)$', t)
        if m: out.append(f'[^{m.group(1)}]: {m.group(2)}')
        elif out: out[-1] = ko_join(out[-1] + ('' if out[-1].endswith(' ') else ' '), t)
        else: print('각주 앞 글', P['n'], t)
    return out


# ---------- 목차 쪽(7~10)
def toc_lines(P):
    rows = []
    for l in P['lines']:
        t = seg_text(l['spans']).strip()
        if l['size'] >= 17: continue
        m = re.match(r'^(.*?)\s*[·.…]{3,}\s*(\S+)$', t)
        title, pg = (m.group(1).strip(), m.group(2)) if m else (t, None)
        pg = {'ⅰ': 'i', 'ⅱ': 'ii'}.get(pg, pg)
        rows.append((l['x0'] > 90, l['size'] > 14, title, pg))
    return rows


# ---------- 짓기
BODY = []
chapters = []
cover_of = {}
for P in PAGES:
    n = P['n']; name = P['lab']
    paras = []
    if n == 1:
        paras = ['^^ 빨리어 Pālī', '^^ 예불과 의례집', ':: 태국 담마윳 전통에 따름', ':: 붓다의 고귀한 제자들']
        # 표지의 글: '빨리어Pālī' '예불과 의례집' '태국 담마윳 전통에 따름' '붓다의 고귀한 제자들'
    elif n == 3:
        ps = build_paras(P)
        paras = ['## ' + re.sub(r'^## ', '', ps[0])] + ps[1:]
    elif 7 <= n <= 10:
        rows = toc_lines(P)
        head = ['## 목  차'] if n == 7 else []
        ls = []
        for ind, big, t, pg in rows:
            if big and ls: ls.append('~')
            ls.append(('- ' if ind else '') + (f'**{t}**' if big else t) + (f' | {pg}' if pg else ''))
        paras = head + ['%% ' + '\n'.join(ls)]
    elif n == 5:
        L = [l for l in P['lines'] if not any(s['color'] == 0x585743 for s in l['spans'])]
        L2 = []
        for l in L:
            sp = [s for s in l['spans'] if s['t'].strip() != '서  문']
            if len(sp) != len(l['spans']):
                l = dict(l, spans=sp); l['x0'] = min(s['x0'] for s in sp)
            L2.append(l)
        paras = ['## 서  문'] + build_paras(dict(P, lines=L2))
        for a, b in JUST5: paras = [x.replace(a, b) for x in paras]
    elif n == 6:
        # 표기법 표·운율 보기·반복 기호 보기는 인쇄본 그대로 그림으로, 나머지 설명은 글로
        cuts = [((112, 264), 'table', '빨리어 한글표기 표'), ((526, 566), 'rhythm', '담마윳의 전통적인 운율 보기'), ((655, 676), 'repeat', '∰ ∰ 기호 보기')]
        paras = []; rest = P['lines']
        for (a, b), nm, cap in cuts:
            before = [l for l in rest if l['c'] < a]; rest = [l for l in rest if l['c'] > b]
            paras += build_paras(dict(P, lines=before), prose=True)
            paras.append(f'![#{cap}]({crop(6, (36, a, 560, b), f"{BK}-p006-{nm}.png")})')
        paras += build_paras(dict(P, lines=rest), prose=True)
        paras[0] = '## ' + paras[0]
        paras = [('>> ' + x if x.startswith('<‘테라와다') else x) for x in paras]   # 오른쪽 맞춤 출처 표시
    elif any(s['color'] == 0x4d4d4f for l in P['lines'] for s in l['spans']) and n != 5:
        # 장 표지
        T = [(seg_text(l['spans']).strip(), l['size']) for l in P['lines']]
        num = re.sub(r'\D', '', ''.join(t for t, s in T if s > 35))
        title = [t for t, s in T if 25 < s < 35]
        sub = [t for t, s in T if s < 13 and t not in ('빨리어',)]
        paras = [':: 빨리어 예불과 의례집', f'^^ 제{num}장', *[f'^^ {t}' for t in title], *[f':: {t}' for t in sub]]
        cover_of[n] = (num, ' '.join(title), ' '.join(sub))
    elif n == N:
        paras = [(':: ' + x if k < 2 else x) for k, x in enumerate(build_paras(P, each=True))]
    else:
        paras = build_paras(P)
    paras = paras + fn_paras(P)
    BODY.append((name, paras))

json.dump(BODY, open('/tmp/b27/body_raw.json', 'w'), ensure_ascii=False, indent=0)

# ---------- 목차(읽기 화면 장·소제목)
chapters = [('표지', 1), ('빨리어(Pālī) 예불(Chanting)의 공덕', 3), ('서문', 5), ('빨리어 한글표기 및 운율', 6), ('목차', 7)]
for n, (num, title, sub) in sorted(cover_of.items()):
    nxt = next((p[3:] for m in range(n, min(n + 4, N)) for p in BODY[m][1] if p.startswith('## ') and re.match(r'^제\s*\d+\s*장', p[3:])), '')
    chapters.append((re.sub(r'^제\s*(\d+)\s*장', r'제\1장', nxt) if nxt else f'제{num}장 {title}' + (f'({sub})' if sub else ''), n))
chapters.append(('판권지', N))
CH = set(n for _, n in chapters)
subs = []
for i, (name, ps) in enumerate(BODY):
    n = i + 1
    if n < 11 or n in CH: pass
    for k, p in enumerate(ps):
        if p.startswith('## ') and re.match(r'^\d+\.\s', p[3:]):
            subs.append(dict(title=p[3:], page=n, sub=True, at=(p[3:][:20] if k > 0 else '')))
toc = [dict(title=t, page=n, sub=False) for t, n in chapters] + subs
toc.sort(key=lambda x: (x['page'], x.get('sub', False)))
body = ''
for name, ps in BODY:
    body += f'=== {name + "쪽" if name else ""} ===\n'.replace('===  ===', '=== ===') + '\n\n'.join(p for p in ps if p.strip()) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': sorted(set(images)), 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
json.dump(JOINS, open('/tmp/b27/joins.json', 'w'), ensure_ascii=False)
print(log)
print(f'쪽 {len(BODY)} · 장 {len(chapters)} · 소제목 {len(subs)} · 그림 {len(set(images))} → {out}')
