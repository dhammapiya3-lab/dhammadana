"""『테라와다(Theravāda) 불교사 (법문 교재)』(DL-0038, 아짠 빤냐와로 마하테로 법문, 붓다의 길따라 선원 개정판 2022)
PDF → content/texts/DL-0038.json
  python3 tools/pdf2text_dl0038.py 책.pdf
  다음에 늘: python3 tools/split_chapters.py --write
인쇄된 '***'(204쪽) → '∗∗∗'.

한글(Hwp 2020)에서 내보낸 PDF 210쪽. 1쪽 속표지(로고 그림), 2·4쪽 빈 쪽(넣지 않음), 3쪽 삼귀의,
5쪽 차례, 6쪽 교재 목록, 7쪽부터 쪽 아래 '- N -' (PDF 쪽 = N + 6). 156쪽(150)은 번호가 인쇄되지 않아 채움.
- 본문 함초롬바탕 11pt, 왼쪽 70pt 에서 시작(들여쓰기 없음). 줄이 오른쪽 끝(463pt 넘게)까지 차면 다음 줄과
  이어 붙임(줄 끝 빈칸이 있으면 띄어 씀, 없으면 붙임 — 한글 파일의 글자 단위 줄바꿈).
- 줄 사이가 벌어진 곳(빈 줄, 25pt 넘게)에서 새 문단. 끝까지 차지 않은 줄 다음(엔터)은 같은 문단 안 줄 바꿈.
- 14pt 굵은 줄 = 장 제목(## ), 12pt 굵은 '(1) …' = 소제목(## , 읽기 목차 아랫단계).
  교재 부분(150쪽 앞)의 줄 전체가 굵은 짧은 줄 = 따로 문단 **…** (› 가 멈춤).
- 굵은 글자 **…**. 색 글자(파랑·빨강)는 표시하지 않음 — 검은 글자로 (운영자 요청, 2026-11-20).
- U+3000 → 빈칸. 쪽 번호 줄은 뺌. 글자는 PDF 그대로.
"""
import sys, re, json, os, collections
import fitz

pdf = sys.argv[1]
BK, ED = 'DL-0038', '개정판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = fitz.open(pdf)
N = src.page_count
log = collections.Counter()
FULL = 463
PART2 = 156          # 【 테라와다 불교사 법문 필사】 (PDF 쪽)
SKIP = {2, 4}        # 빈 쪽
COLORS = set()   # 색 글자(파랑·빨강)는 표시하지 않고 검은 글자로 (운영자 요청, 2026-11-20 '강조색을 사용하지 말고 검은색으로')


def norm(t):
    return t.replace('　', ' ').replace('​', '')


def lines_of(p):
    L = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text']]
            if not ''.join(s['text'] for s in sp).strip(): continue
            y0 = l['bbox'][1]
            if L and abs(L[-1]['y0'] - y0) < 3:
                L[-1]['sp'] += sp; L[-1]['x1'] = max(L[-1]['x1'], l['bbox'][2]); continue
            L.append(dict(sp=list(sp), y0=y0, x0=l['bbox'][0], x1=l['bbox'][2]))
    L.sort(key=lambda r: (round(r['y0']), r['x0']))
    for l in L:
        sp = [s for s in l['sp'] if s['text'].strip()]
        l['t'] = norm(''.join(s['text'] for s in l['sp']))
        l['size'] = max(s['size'] for s in sp)
        l['bold'] = all('Bold' in s['font'] for s in sp)
        l['font'] = sp[0]['font']
    return L


def markup(l, bold_ok=True):
    """줄의 글자 조각을 굵게(**)·색(==) 표시로. 빈칸은 표시 밖으로."""
    runs = []
    for s in l['sp']:
        t = norm(s['text'])
        if not t: continue
        st = (bold_ok and 'Bold' in s['font'] and bool(t.strip()), s['color'] in COLORS and bool(t.strip()))
        if runs and runs[-1][0] == st: runs[-1][1] += t
        elif runs and not t.strip(): runs[-1][1] += t
        else: runs.append([st, t])
    out = ''
    for (b, c), t in runs:
        if not (b or c): out += t; continue
        m = re.match(r'^(\s*)(.*?)(\s*)$', t, re.S)
        a, core, z = m.groups()
        if c: core = '==' + core + '=='; log['색'] += 1
        if b: core = '**' + core + '**'; log['굵게'] += 1
        out += a + core + z
    return out


def join(a, b):
    """앞 줄 a 와 다음 줄 b 이어 붙임 — 줄 끝·줄 첫머리 굵게/색 표시가 맞닿으면 하나로."""
    sep = ' ' if a.endswith(' ') or b.startswith(' ') else ''
    a2, b2 = a.rstrip(), b.lstrip()
    for mk in ('**', '=='):
        if a2.endswith(mk) and b2.startswith(mk) and not a2.endswith(mk * 2):
            a2, b2 = a2[:-2], b2[2:]
    return a2 + sep + b2


PAGES = []
images = []
for n in range(1, N + 1):
    if n in SKIP: continue
    L = lines_of(src[n - 1])
    lab = ''
    keep = []
    for l in L:
        m = re.fullmatch(r'\s*-\s*(\d+)\s*-\s*', l['t'])
        if m and l['y0'] > 600: lab = m.group(1); continue
        keep.append(l)
    if n == PART2: lab = '150'   # 번호가 인쇄되지 않은 쪽 (149·151 사이)
    P = dict(n=n, lab=lab, lines=keep, paras=[])
    PAGES.append(P)
    if n < 7: continue
    paras = []; prev = None
    for l in keep:
        t = l['t']
        if l['bold'] and l['size'] >= 13.5:          # 장 제목
            paras.append('## ' + t.strip()); prev = dict(l, h=1); continue
        if l['bold'] and l['size'] >= 11.8 and n != 145:   # (1)… 소제목
            paras.append('## ' + t.strip()); prev = dict(l, h=1); continue
        if l['font'].startswith('YJ'):                # 필사 부분 표지 줄 【 … 】 = 장
            paras.append('## ' + t.strip()); prev = dict(l, h=1); continue
        mt = markup(l)
        gap = l['y0'] - prev['y0'] if prev else 99
        head = n < PART2 and l['bold'] and l['x1'] < FULL     # 교재 부분 굵은 한 줄 = 소제목처럼 따로
        if prev is not None and not prev.get('h') and not head and not prev.get('hd') and gap < 25:
            if prev['x1'] > FULL and not re.match(r'\s*\(\d+\)\s', l['t']):   # '(3) 출가는…' 번호 항목은 앞 줄이 차도 줄 바꿈 (13쪽)
                paras[-1] = join(paras[-1], mt); log['이음'] += 1
            else:
                paras[-1] = paras[-1].rstrip() + '\n' + mt.lstrip(); log['줄 바꿈'] += 1   # 줄 끝 빈칸은 남김 — 다음 줄을 이어 붙일 때 띄어 씀(2026-11-20 고침: 지우면 '수|있습니다' 가 붙었음)
        else:
            paras.append(mt)
        prev = dict(l, hd=head)
    P['paras'] = [re.sub(r'[ \t]+$', '', p, flags=re.M).strip() for p in paras if p.strip()]

pg = {P['n']: P for P in PAGES}


def raw(n):
    return [l for l in pg[n]['lines']]


# 1쪽 속표지: 제목·법문·로고·단체 이름
L = raw(1)
os.makedirs(os.path.join(REPO, 'public/uploads'), exist_ok=True)
from PIL import Image
import io
im = Image.open(io.BytesIO(src.extract_image(src[0].get_images(full=True)[0][0])['image']))
im.thumbnail((600, 600)); logo = f'/uploads/{BK}-logo.jpg'
im.save(os.path.join(REPO, 'public' + logo), quality=90)
images.append(logo)
tl = [l['t'].strip() for l in L]
log['속표지 줄 ' + ' / '.join(tl)] += 1
pg[1]['paras'] = ['^^ ' + tl[0], '>> ' + tl[1], f'![#로고]({logo})', ':: ' + tl[2], ':: ' + tl[3], ':: ' + tl[4]]

# 3쪽 삼귀의: 네모 상자 제목 두 개는 소제목, 빠알리·소리·번역 줄은 인쇄본 줄 그대로
paras = []; prev = None
for l in raw(3):
    t = l['t'].strip()
    if l['size'] >= 14.5:
        paras.append('## ' + t); prev = None; continue
    if prev is not None and l['y0'] - prev['y0'] < 25: paras[-1] += '\n' + t
    else: paras.append(t)
    prev = l
pg[3]['paras'] = paras

# 5쪽 차례: 인쇄된 줄 그대로(쪽 번호가 앞에 'Np.'), 묶음 사이 간격은 ~
L = raw(5)
paras = [L[0]['t'].strip(), ':: ' + L[1]['t'].strip(), L[2]['t'].strip()]
toc_lines = []; prev = None
for l in L[3:]:
    if prev is not None and l['y0'] - prev['y0'] > 25 and toc_lines: toc_lines.append('~')
    toc_lines.append(l['t'].strip()); prev = l
paras.append('%% ' + '\n'.join(toc_lines))
pg[5]['paras'] = paras

# 6쪽 교재 목록: 제목 줄 + 목록(인쇄된 줄 그대로)
L = raw(6)
pg[6]['paras'] = ['## ' + L[0]['t'].strip(), '\n'.join(l['t'].strip() for l in L[1:])]

# 마지막 쪽(204) 옮긴이의 글 — 줄 그대로 두지 않고 위 규칙대로 (빈 줄로 문단)
# 장 목록
chapters = [('속표지', 1, 0), ('Tisaraṇa (띠사라나)', 3, 0), ('차례', 5, 0), ('【 테라와다 불교사 교재】', 6, 0)]
idx = {P['n']: i + 1 for i, P in enumerate(PAGES)}
toc = []
for t, n, k in chapters: toc.append(dict(title=t, page=idx[n], sub=False, **({'bold': True} if t.startswith('【') else {})))
for P in PAGES:
    if P['n'] < 7: continue
    for k, p in enumerate(P['paras']):
        if p.startswith('## '):
            t = p[3:].strip()
            sub = bool(re.match(r'\(\d\)', t))
            title = re.sub(r'^\*\s*', '', t)
            e = dict(title=re.sub(r'\s+', ' ', title), page=idx[P['n']], sub=sub)
            if title.startswith('【'): e['bold'] = True   # 묶음 제목은 목차에서 굵게 (운영자 요청, 2026-11-20)
            if k: e['at'] = t[:20]
            toc.append(e)
last = PAGES[-1]
toc.append(dict(title='옮긴이의 글', page=idx[last['n']], sub=False))

body = ''
for P in PAGES:
    body += f"=== {P['lab'] + '쪽' if P['lab'] else ''} ===\n".replace('===  ===', '=== ===') + '\n\n'.join(P['paras']) + '\n\n'
body = body.rstrip() + '\n'
# 마지막 쪽 첫 줄에 인쇄된 '***' 는 굵게 표시와 헷갈리지 않게 '∗∗∗'(U+2217) — DL-0034 와 같은 방식
body = re.sub(r'^\*\*\*\s*$', '∗∗∗', body, flags=re.M)
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [{'image': x, 'caption': ''} for x in images], 'body': body},
          open(out, 'w'), ensure_ascii=False, indent=1)
for k, v in log.items(): print(v, k)
print('장', len([t for t in toc if not t['sub']]), '소제목', len([t for t in toc if t['sub']]), '쪽', len(PAGES), '→', out)
