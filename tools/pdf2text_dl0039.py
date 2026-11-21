"""『테라와다 불교사 (녹취 법문집)』(DL-0039, 아짠 빤냐와로 마하테로 법문, 2013 담마스쿨 2학기 녹취)
PDF → content/texts/DL-0039.json
  python3 tools/pdf2text_dl0039.py 책.pdf
  다음에 늘: python3 tools/split_chapters.py --write → python3 tools/join_pagewords.py DL-0039 --write

한글(Hwp 2020)에서 Hancom PDF 로 내보낸 A4 158쪽. 쪽 번호가 인쇄되어 있지 않음 — 1쪽 차례의 '2p.' 등이
PDF 쪽 번호와 같으므로 PDF 쪽 번호를 쪽 이름으로 씀.
- 1쪽: 'Namo Buddhāya…' 한 줄(예경문) · '◈ 2013 …'·'테라와다 불교사_아짠 빤냐와로 스님법문'(속표지) · 차례 줄(인쇄된 'Np.' 그대로 %% )
- 본문 함초롬바탕 11pt, 왼쪽 85pt 에서 시작(들여쓰기 없음). 줄이 오른쪽 끝(FULL 넘게)까지 차면 다음 줄과 이어 붙임
  (줄 끝 빈칸이 있으면 띄어 씀, 없으면 붙임 — 한글 파일의 글자 단위 줄바꿈).
- 줄 사이가 벌어진 곳(빈 줄, 25pt 넘게)에서 새 문단. 끝까지 차지 않은 줄 다음(엔터)은 같은 문단 안 줄 바꿈. (DL-0038 과 같은 규칙)
- 12pt 굵은 '* … _빤냐와로 스님법문_담마스쿨_날짜' 줄 = 장 제목(## , 91쪽은 두 줄을 이어 하나로).
- 굵은 글자 **…**. 색 글자(파랑·빨강·초록)는 표시하지 않음 — 검은 글자로 (운영자 요청, 2026-11-20).
- 글자는 PDF 그대로.
"""
import sys, re, json, os, collections
import fitz

pdf = sys.argv[1]
BK, ED = 'DL-0039', '초판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = fitz.open(pdf)
N = src.page_count
log = collections.Counter()
FULL = 505


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
    return L


def markup(l):
    """줄의 글자 조각을 굵게(**) 표시로. 빈칸은 표시 밖으로."""
    runs = []
    for s in l['sp']:
        t = norm(s['text'])
        if not t: continue
        st = 'Bold' in s['font'] and bool(t.strip())
        if runs and runs[-1][0] == st: runs[-1][1] += t
        elif runs and not t.strip(): runs[-1][1] += t
        else: runs.append([st, t])
    out = ''
    for b, t in runs:
        if not b: out += t; continue
        m = re.match(r'^(\s*)(.*?)(\s*)$', t, re.S)
        a, core, z = m.groups()
        out += a + '**' + core + '**' + z; log['굵게'] += 1
    return out


def join(a, b):
    """앞 줄 a 와 다음 줄 b 이어 붙임 — 줄 끝·줄 첫머리 굵게 표시가 맞닿으면 하나로."""
    sep = ' ' if a.endswith(' ') or b.startswith(' ') else ''
    a2, b2 = a.rstrip(), b.lstrip()
    if a2.endswith('**') and b2.startswith('**') and not a2.endswith('****'):
        a2, b2 = a2[:-2], b2[2:]
    return a2 + sep + b2


PAGES = []
for n in range(1, N + 1):
    L = lines_of(src[n - 1])
    P = dict(n=n, lab=str(n), lines=L, paras=[])
    PAGES.append(P)
    if n == 1: continue
    paras = []; prev = None
    for l in L:
        t = l['t']
        if l['bold'] and l['size'] >= 11.8:            # 장 제목 (91쪽은 두 줄)
            if prev is not None and prev.get('h'):
                paras[-1] = paras[-1].rstrip() + t.strip()
            else:
                paras.append('## ' + t.strip())
            prev = dict(l, h=1); continue
        mt = markup(l)
        gap = l['y0'] - prev['y0'] if prev else 99
        if prev is not None and not prev.get('h') and gap < 25:
            if prev['x1'] > FULL:
                paras[-1] = join(paras[-1], mt); log['이음'] += 1
            else:
                paras[-1] = paras[-1].rstrip() + '\n' + mt.lstrip(); log['줄 바꿈'] += 1
        else:
            paras.append(mt)
        prev = l
    P['paras'] = [re.sub(r'[ \t]+$', '', p, flags=re.M).strip() for p in paras if p.strip()]

# 1쪽: 예경문 한 줄 · 속표지 두 줄 · 차례(인쇄된 줄 그대로)
L = PAGES[0]['lines']
tl = [l['t'].strip() for l in L]
assert tl[0].startswith('Namo') and tl[1].startswith('◈') and tl[2].startswith('테라와다'), tl[:3]
# 장마다 새 쪽에서 시작하도록 같은 쪽 이름(1쪽)의 쪽 표시를 셋으로 나눔
PAGES[0]['paras'] = [':: ' + markup(L[0]).strip()]
PAGES[1:1] = [dict(n=1, lab='1', lines=[], paras=['^^ ' + tl[1], ':: ' + tl[2]]),
              dict(n=1, lab='1', lines=[], paras=['%% ' + '\n'.join(tl[3:])])]

idx = {}
for i, P in enumerate(PAGES): idx.setdefault(P['n'], i + 1)
toc = [dict(title='예경문', page=1, sub=False), dict(title='속표지', page=2, sub=False),
       dict(title='차례', page=3, sub=False)]
for P in PAGES[3:]:
    for k, p in enumerate(P['paras']):
        if p.startswith('## '):
            t = p[3:].strip()
            e = dict(title=re.sub(r'\s+', ' ', re.sub(r'^\*\s*', '', t)), page=idx[P['n']], sub=False)
            if k: e['at'] = t[:20]
            toc.append(e)

body = ''
for P in PAGES:
    body += f"=== {P['lab']}쪽 ===\n" + '\n\n'.join(P['paras']) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [], 'body': body},
          open(out, 'w'), ensure_ascii=False, indent=1)
for k, v in log.items(): print(v, k)
print('장', len(toc), '쪽', len(PAGES), '→', out)
