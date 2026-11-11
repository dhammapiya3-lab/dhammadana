"""『법구경 : 하루를 살더라도』(DL-0021, 오원탁 엮음) 인쇄용 PDF → content/texts/DL-0021.json
  python3 tools/pdf2text_dl0021.py 책.pdf

PDF 쪽 = 인쇄 쪽 (PDF 4쪽에 '004'). 1~2쪽(반표제·빈 쪽)·510쪽(빈 쪽)·512쪽(뒤)은 뺌.
이 책의 짜임: 이야기마다 '번호 제목' 큰 제목(서울한강 17pt) + 게송(서울한강 12pt) + 배경 이야기·풀이는 각주(SM3 명조 10.8pt, '4)' 모양 번호).
각주 번호 '4)' → [^4], 각주 줄 → [^4]: …, 다음 쪽으로 넘어간 각주(번호 없이 시작)는 앞 각주에 이어 붙임.
쪽 머리글·쪽 번호(아래쪽 y>620)는 뺌. 장 표지(26장)·첨부 표지의 사진은 잘라서 public/uploads/DL-0021-*.jpg 로.
"""
import sys, re, json, fitz

pdf = sys.argv[1]
bk, ED = 'DL-0021', '개정판 (법보시 어플용)'
src = fitz.open(pdf)
FIRST, LAST = 3, 511
INVIS = re.compile('[\x07\xad\u200b\U000f0000-\U000fffff]')
SUP = re.compile(r'^\d{1,3}\)$')
CH_PAGES = [21, 43, 57, 71, 89, 107, 119, 135, 153, 169, 185, 199, 215, 233, 249, 259, 273, 289, 309, 323, 337, 355, 365, 377, 397, 417]
ATT = 459   # 첨부 표지
REF = 503   # 참고자료 시작 (아래에서 확인)


def geom(n):  # (왼쪽, 오른쪽): 짝수 쪽은 왼쪽 93.5, 홀수 쪽은 113.4
    return (93.5, 394.0) if n % 2 == 0 else (113.4, 413.7)


def spans_of(l):  # 빈칸뿐인 줄은 빼고, 글자가 있는 줄은 빈칸 조각까지 그대로
    return l['spans'] if any(INVIS.sub('', s['text']).strip() for s in l['spans']) else []


def rows(n):
    """쪽의 줄들: 같은 높이(줄 아래 y1 또는 위 y0)의 조각은 한 줄로, x 순서로."""
    p = src[n - 1]
    L = []
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']: s['text'] = ''.join(c['c'] for c in s['chars'])
            sp = spans_of(l)
            if not sp: continue
            x0, y0, x1, y1 = l['bbox']
            ink = [c['bbox'] for s in sp for c in s['chars'] if INVIS.sub('', c['c']).strip()]
            x0, x1 = min(c[0] for c in ink), max(c[2] for c in ink)  # 앞뒤 빈칸을 뺀 글자 자리
            if y0 > 620: continue  # 쪽 번호·머리글
            L.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, sp=sp))
    L.sort(key=lambda a: (round(a['y1']), a['x0']))
    M = []
    for a in L:
        if M and (abs(a['y1'] - M[-1]['y1']) < 2.5 or abs(a['y0'] - M[-1]['y0']) < 2):
            m = M[-1]; m['sp'] = m['sp'] + a['sp'] if a['x0'] >= m['x0'] else a['sp'] + m['sp']
            m['x0'] = min(m['x0'], a['x0']); m['x1'] = max(m['x1'], a['x1']); m['y0'] = min(m['y0'], a['y0']); continue
        M.append(dict(a))
    for a in M:
        a['sp'].sort(key=lambda s: s['bbox'][0])
        big = [s for s in a['sp'] if INVIS.sub('', s['text']).strip() and not SUP.match(s['text'].strip()) and not (s['size'] < 9 and re.fullmatch(r'[\d)]+', s['text'].strip()))]
        a['sz'] = max((s['size'] for s in big), default=max(s['size'] for s in a['sp']))
        a['font'] = max(big or a['sp'], key=lambda s: len(s['text']))['font']
    M.sort(key=lambda a: (a['y0'], a['x0']))
    return M


def text_of(a, foot_first=False):
    """줄 글자: 작은 '4)' 는 [^4] (각주 줄 첫머리의 번호는 빼고 돌려줌)."""
    out, num = '', None
    grp = []  # 작은 글자 조각('4' + ')')을 모아서 판단
    for s in a['sp']:
        t = INVIS.sub('', s['text']).replace('\t', ' ').replace('\xa0', ' ').replace('\n', '').replace('↘', '*')  # 299쪽 '*' 가 '↘' 글자 정보로 들어 있음(인쇄본은 *)
        if grp and s['size'] < 9.5 and abs(s['size'] - grp[-1][0]) < 0.3 and t.strip(): grp[-1][1] += t; continue
        grp.append([s['size'], t])
    for k, (sz, t) in enumerate(grp):
        st = t.strip()
        if SUP.match(st) and sz < 9.5:
            if foot_first and not out.strip(): num = st[:-1]; out = ''; continue
            out += t[:len(t) - len(t.lstrip())] + f'[^{st[:-1]}]' + t[len(t.rstrip()):]; continue
        out += t
    return out, num


def rule_y(n):
    ys = [d['rect'].y0 for d in src[n - 1].get_drawings() if d['rect'].height < 1 and 120 < d['rect'].width < 160 and d['rect'].y0 > 150]
    return min(ys) if ys else None


def _sh(a): return [s['size'] for s in a['sp'] if 'SeoulHangang' in s['font'] and INVIS.sub('', s['text']).strip()]
def is_head(a): return any(z >= 13 for z in _sh(a))
def is_verse(a): return not is_head(a) and not is_sub(a) and any(11.5 <= z < 13 for z in _sh(a))
def is_sub(a):  # 첨부의 '⑴ 바른 견해', '1) 공통 반드시 - 일곱 가지' (굵은 고딕 11.3)
    f = next((x for x in a['sp'] if INVIS.sub('', x['text']).strip()), None)
    return f is not None and ('HYgsrB' in f['font'] or 'YDVYGO' in f['font']) and f['size'] >= 11


def glyfix(t):  # 나눔스퀘어 목록 글씨의 '찟'·'뿟' 은 PDF 에 글자 정보 없이 도형으로만 그려져 있음 (6곳, 인쇄본 그림으로 확인)
    return re.sub(r'(\d) 틸라 장로', r'\1 뿟틸라 장로', t.replace(' 따 장자', ' 찟따 장자').replace(' 따핫타', ' 찟따핫타'))


pages = []   # [n, 본문 문단들, 각주들]
images = []


def crop(n, bbox, name):
    return None  # 사진·로고는 넣지 않음 (운영자 요청, 2026-11-12)


def join(prev, t):
    if not prev: return t.lstrip()
    if prev.endswith(' ') or prev.endswith('\n'): return prev + t.lstrip()
    return prev + t.lstrip()


def body_and_foot(n, fn_size):
    left, right = geom(n)
    ry = rule_y(n)
    ps, fns = [], []
    cx0 = 0
    cur, kind = None, None  # kind: 'p' 문단, 'v' 게송, 'h' 제목, 'li' 목록
    fcur = None
    lastfoot = False
    fprev = None

    def flush():
        nonlocal cur, kind
        if cur is not None and cur.strip():
            t = re.sub(r'[ ]{2,}', ' ', cur).strip()
            if kind == 'h': t = '## ' + t
            elif kind == 'v': t = '++ ' + '\n'.join('**' + x.strip() + '**' if x.strip() else x for x in t.split('\n'))
            elif kind == 'r': t = '>> ' + t
            ps.append(t)
        cur, kind = None, None

    prev = None
    for a in rows(n):
        if is_head(a) or is_verse(a) or is_sub(a): foot = False
        elif a['sz'] < 9.5 and abs(a['sz'] - fn_size) > 0.35: foot = lastfoot
        else: foot = any('SM3' in x['font'] for x in a['sp'] if abs(x['size'] - a['sz']) < 0.05) and (abs(a['sz'] - fn_size) < 0.35 or (n >= ATT and abs(a['sz'] - 10.8) < 0.35))
        lastfoot = foot
        if foot:
            t, num = text_of(a, foot_first=True)
            if num:
                fcur = [num, t.lstrip()]; fns.append(fcur)
            elif fcur is None:
                fcur = [None, t.lstrip(), a['x0'] < left + 6]; fns.append(fcur)  # 앞 쪽에서 이어지는 각주
            elif a['x0'] < left + 6 or (fprev is not None and fprev['x1'] < right - 30):
                fcur[1] = fcur[1].rstrip() + '\n' + t.lstrip()  # 각주 안의 새 문단 (앞 줄이 짧게 끝나면 새 줄)
            else:
                fcur[1] = fcur[1] + t.lstrip()
            prev = None; fprev = a
            continue
        t, _ = text_of(a)
        if re.fullmatch(r'\[\^\d+\]', t.strip()) and cur:  # 제목보다 조금 높이 따로 찍힌 각주 번호
            cur = cur.rstrip() + t.strip(); continue
        if is_sub(a):
            flush(); cur, kind = t, 'h'
        elif is_head(a):
            if kind == 'h' and prev is not None and a['y0'] - prev['y0'] < 26: cur += ' ' + t.strip()
            else: flush(); cur, kind = t, 'h'
        elif is_verse(a):
            if kind == 'v' and prev is not None and a['y0'] - prev['y0'] < 30: cur += '\n' + t.strip()
            else: flush(); cur, kind = t.strip(), 'v'
        else:
            st = t.strip()
            if a['x0'] > left + 120 and a['x1'] > right - 6:  # 오른쪽 맞춤(날짜·서명)
                if kind == 'r' and prev is not None and a['y0'] - prev['y0'] < 26: cur += '\n' + st
                else: flush(); cur, kind = st, 'r'
            elif kind == 'p' and prev is not None and cur.startswith('- ') and (a['x0'] > left + 3 or t.startswith(' ')) and a['y0'] - prev['y0'] < 30:
                cur = join(cur, t)  # 참고자료 목록의 둘째 줄
            elif kind == 'p' and prev is not None and a['x0'] > cx0 + 6 and a['x0'] > left + 14 and a['y0'] - prev['y0'] < 26 and not re.match(r'(\d+\.\s|\d+\)\s|[①-⑳⑴-⒇㉮-㉻])', st):
                cur = join(cur, t)  # 목록 항목의 둘째 줄(내어쓰기)
            elif kind == 'p' and prev is not None and cx0 > left + 14 and abs(a['x0'] - cx0) < 3 and prev['x1'] > right - 16 and a['y0'] - prev['y0'] < 26 and not re.match(r'(\d+\.\s|\d+\)\s|[①-⑳⑴-⒇㉮-㉻])', st):
                cur = join(cur, t)  # 깊이 들여 쓴 묶음 안에서 꽉 찬 줄 다음 줄
            elif kind == 'p' and prev is not None and a['x0'] < left + 6 and not re.match(r'(\d+\.\s|- |[①-⑳⑴-⒇])', st) and a['y0'] - prev['y0'] < 26 and prev['x1'] > right - 16:
                cur = join(cur, t)
            elif kind == 'p' and prev is not None and a['x0'] > left + 14 and a['y0'] - prev['y0'] < 26 and re.match(r'(\d+\.|- |[①-⑳])', cur) and not re.match(r'(\d+\.\s|\d+\)\s|[①-⑳⑴-⒇㉮-㉻])', st):
                cur = join(cur, t)  # 번호·줄표 목록의 둘째 줄(내어쓰기)
            else:
                flush(); cur, kind = t, 'p'; cx0 = a['x0']
        prev = a
    flush()
    return ps, fns


# ---- 쪽마다 ----
fn_size = {}
for n in range(FIRST, LAST + 1):
    if n in (510,): continue
    fs = 9.8 if n >= ATT else 10.8
    if n in CH_PAGES or n == ATT:
        # 장·첨부 표지: 제목 + 사진 + 이야기(항목) 목록
        r = rows(n)
        info = [x for x in src[n - 1].get_image_info() if x['bbox'][2] - x['bbox'][0] > 40]
        img = crop(n, info[0]['bbox'], ('ch%02d' % (CH_PAGES.index(n) + 1)) if n in CH_PAGES else 'att')
        raw = []  # 이야기 목록: 두 단으로 인쇄된 쪽도 있으므로 줄 단위로, 왼쪽 단 → 오른쪽 단
        for b in src[n - 1].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                sp = spans_of(l)
                if sp and max(x['size'] for x in sp) < 9.5 and l['bbox'][1] > info[0]['bbox'][3] and l['bbox'][1] < 620:
                    raw.append((round(l['bbox'][0] / 40), l['bbox'][1], ''.join(x['text'] for x in sp)))
        items = [INVIS.sub('', x[2]) for x in sorted(raw)]
        items = [glyfix(re.sub(r'\s+', ' ', x).strip()) for x in items if x.strip()]
        if n in CH_PAGES:
            no = next(text_of(a)[0].strip() for a in r if re.fullmatch(r'제\d+장', text_of(a)[0].strip()))
            name = next(text_of(a)[0].strip() for a in r if a['sz'] > 30) if any(a['sz'] > 30 for a in r) else ''
            name = ' '.join(text_of(a)[0].strip() for a in r if a['sz'] > 30)
            pali = next(text_of(a)[0].strip() for a in r if text_of(a)[0].strip().startswith('('))
            ps = [':: ' + no, '^^ ' + name, ':: ' + pali, f'![#{no} {name} 장 표지 사진]({img})', '%% ' + '\n'.join(items)]
            pages.append([n, ps, [], f'{no} {name}{pali}'])
        else:
            ps = ['^^ 첨부', f'![#첨부 표지 사진]({img})', '%% ' + '\n'.join(('- ' if re.match(r'[가나]\. ', x) else '') + x for x in items)]
            pages.append([n, ps, [], '첨부'])
        continue
    if 6 <= n <= 19 or n == 511: pages.append([n, [], [], None]); continue  # 목차·판권지는 아래에서 따로
    ps, fns = body_and_foot(n, fs)
    pages.append([n, ps, fns, None])

# 인쇄본의 각주 번호가 어긋난 세 곳: 링크가 맞게 바른 번호로 (앞뒤 번호로 확인, 운영자에게 보고)
FIXNO = {98: ('def', '100', '101'), 252: ('ref', '259', '264'), 286: ('ref', '302', '303')}
for pg in pages:
    if pg[0] in FIXNO:
        k, a, b = FIXNO[pg[0]]
        if k == 'def':
            hit = [f for f in pg[2] if f[0] == a]; assert len(hit) == 1; hit[0][0] = b
        else:
            hit = [i for i, x in enumerate(pg[1]) if f'[^{a}]' in x]; assert len(hit) == 1; pg[1][hit[0]] = pg[1][hit[0]].replace(f'[^{a}]', f'[^{b}]')
# 앞 쪽에서 이어지는 각주(번호 없음)는 앞 각주에 붙임
last = None
for pg in pages:
    keep = []
    for f in pg[2]:
        if f[0] is None and last is not None:
            last[1] = (last[1].rstrip() + '\n' + f[1]) if f[2] else last[1] + f[1]  # 새 문단으로 시작하면 줄 바꿈
            continue
        if f[0] is None: raise SystemExit(f'{pg[0]}쪽: 앞에 이을 각주가 없음')
        keep.append(f); last = f
    pg[2] = keep

P = {pg[0]: pg for pg in pages}
CHN = []
for n in range(6, 20):
    for a in rows(n):
        t = re.sub(r'\s+', ' ', text_of(a)[0]).strip()
        if re.match(r'제\d+장', t): CHN.append(t)
assert len(CHN) == 26, CHN
for k, n in enumerate(CH_PAGES): P[n][3] = CHN[k]
# 3쪽 속표지
im3 = [x['bbox'] for x in src[2].get_image_info() if x['bbox'][2] - x['bbox'][0] > 40]
im3.sort(key=lambda b: b[1])
P[3][1] = ['^^ 법구경 Dhammapada', f"![#하루를 살더라도]({crop(3, im3[0], 'title')})", ':: 간략한 배경 이야기와 불교용어 설명 수록', ':: 이 『법구경_하루를 살더라도』에서는 배경 이야기를 간단하게 줄여서 주해로 게재하고, 사성제, 팔정도, 사마타 수행과 위빳사나 수행 등의 불교 용어 설명도 첨부했습니다.', ':: 향원 오원탁 엮음', f"![#불교시대사]({crop(3, im3[1], 'press')})"]
# 6~19쪽 목차: 장 줄(굵게) / 이야기 줄(- 번호 제목  쪽) — 점선 없이 인쇄된 글 그대로
for n in range(6, 20):
    out = []
    for a in rows(n):
        t = re.sub(r'\s+', ' ', text_of(a)[0]).strip()
        if not t or t in ('목차', '첨부'):
            if t == '첨부': out.append('~'); out.append('**첨부**')
            continue
        m = re.match(r'(.*?)\s*(\d{3})$', t)
        if re.match(r'제\d+장', t): out += (['~'] if out else []) + ['**' + t + '**']
        elif m and m.group(1):
            nm = glyfix(m.group(1))
            out.append(('- ' if re.match(r'[\d]', nm) else '-- ' if re.match(r'[가나]\. ', nm) else '') + nm + ' | ' + m.group(2))
        elif m: out[-1] = out[-1] + '  ' + m.group(2) if out else m.group(2)
        else: out.append(('- ' if re.match(r'\d', t) else '') + t)
    P[n][1] = (['## 목차'] if n == 6 else []) + ['%% ' + '\n'.join(out)]
# 511쪽 판권지: 이름 칸 + 내용 칸 한 줄씩
lines = []
for a in rows(511):
    t = re.sub(r'\s+', ' ', text_of(a)[0]).strip()
    if t: lines.append(t)
P[511][1] = ['**' + lines[0] + '**', '\n'.join(lines[1:])]
P[511][2] = []
P[REF][1][0] = '## ' + P[REF][1][0]  # 참고자료 제목(작은 글씨로 가운데)

# 487쪽 표(칠청정과 위빳사나 지혜): 인쇄된 칸 그대로. '→' 는 PDF 에 '≲' 글자 정보로 들어 있음(글꼴 문제, 인쇄본은 화살표)
T487 = '''|  | 칠청정 | 위빳사나 지혜 |
| I | 계청정(戒淸淨) | 재가자는 오계나 생계 제8계를 준수[^550] |
| II | 마음청정[心淸淨] | 근접삼매(찰나삼매)와 본삼매[^551] |
| III | 견해청정[見淸淨] | 정신물질 구별의 지혜 |
| IV | 의심극복청정[度疑淸淨] | 조건 파악의 지혜(작은 수다원) |
| V | 도비도지견청정 [道非道智見淸淨] | 1. 명상의 지혜 → 위빳사나 지혜의 시작 |
|  |  | 2. 생멸의 지혜(약한 단계) |
|  |  | 부수번뇌를 번뇌라고 파악함[^552] |
| VI | 실천지견청정 [行道智見淸淨] | 2. 생멸의 지혜(성숙된 단계) |
|  |  | 3. 소멸의 지혜 4. 두려움의 지혜 |
|  |  | 5. 허물의 지혜 6. 역겨움의 지혜 |
|  |  | 7. 벗어나려는 지혜 8. 재성찰의 지혜 |
|  |  | 9. 형성 평온의 지혜 10. 수순의 지혜 |
| VI 과 VII 사이 |  | 11. 종성의 지혜 |
| VII | 지견청정[智見淸淨] | 수다원도, 사다함도, 아나함도, 아라한도 |'''
assert P[487][1][0].startswith('## 13.'), P[487][1][:2]
P[487][1] = [P[487][1][0], T487]

# ---- 하나로 ----
def clean(x):
    if x.startswith('!['): return ''  # 사진·로고 줄은 뺌
    x = x.replace('****', '')
    return x.strip()

body = ''
toc = []
TOCF = {3: '속표지', 4: '들어가는 말', 5: '일러두기', 6: '목차'}
for n, ps, fns, chname in pages:
    if n in TOCF: toc.append({'title': TOCF[n], 'page': n, 'sub': False})
    if chname: toc.append({'title': chname, 'page': n, 'sub': False})
    if n == REF: toc.append({'title': '참고자료', 'page': n, 'sub': False})
    if n == 511: toc.append({'title': '판권지', 'page': n, 'sub': False})
    if 21 <= n < 511 and not chname:
        for x in ps:
            if x.startswith('## ') and re.match(r'## \d', x):
                toc.append({'title': re.sub(r'\[\^[^\]]+\]', '', x[3:]).strip(), 'page': n, 'sub': True})
    body += f'=== {n}쪽 ===\n' + '\n\n'.join(clean(x) for x in ps + [f'[^{f[0]}]: ' + re.sub(r'[ ]{2,}', ' ', f[1]).strip().replace(' \n', '\n') for f in fns] if clean(x)) + '\n\n'
body = body.rstrip() + '\n'
ORD = {pg[0]: i + 1 for i, pg in enumerate(pages)}  # 목차의 page 는 인쇄 쪽 번호가 아니라 몇 번째 쪽인지(1부터)
for t in toc: t['page'] = ORD[t['page']]
json.dump({'book': bk, 'edition': ED, 'toc': toc, 'images': images, 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '쪽', len([t for t in toc if not t['sub']]), '장', len([t for t in toc if t['sub']]), '소제목', len(images), '그림')
