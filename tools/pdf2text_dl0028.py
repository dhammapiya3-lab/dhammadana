"""『붓다』(DL-0028, 아짠 빤냐와로(진용) 스님 법문, 담마마-마까 옮김) PDF → content/texts/DL-0028.json
  python3 tools/pdf2text_dl0028.py 책.pdf

한글(HWP 2020)에서 내보낸 A4 PDF 113쪽. 1쪽 = 차례(쪽 번호 없음), 2쪽부터 쪽 아래 '- N -' (PDF 쪽 = N + 1).
본문 함초롬바탕 11pt, 과 제목 '제 N과 …' 굵게 12pt → 장 제목. 113쪽(112) 맺음말.
- 줄이 오른쪽 끝(500pt 넘게)까지 차면 다음 줄과 이어 붙임(줄 끝 빈칸이 있으면 띄어 씀, 없으면 붙임 — 한글 파일의 글자 단위 줄바꿈).
- 끝까지 차지 않은 줄에서 문단이 끝남. 줄 사이가 벌어진 곳(빈 줄)도 새 문단.
- 게송(짧은 빠알리 줄 + 들여 쓴 번역 줄)은 두 줄을 한 문단으로(줄 바꿈 그대로).
- 쪽 번호 '- N -' 는 뺌. 글자는 PDF 그대로.
  다음에 늘: python3 tools/split_chapters.py --write  (과가 쪽 중간에서 시작하면 새 쪽에서)
"""
import sys, re, json, os, collections
import fitz

pdf = sys.argv[1]
BK, ED = 'DL-0028', '초판'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = fitz.open(pdf)
N = src.page_count
log = collections.Counter()
FULL = 500


def lines_of(p):
    L = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'].strip()]
            if not sp: continue
            t = ''.join(s['text'] for s in l['spans'])
            y0 = l['bbox'][1]
            if L and abs(L[-1]['y0'] - y0) < 3:
                L[-1]['t'] += t; L[-1]['x1'] = max(L[-1]['x1'], l['bbox'][2]); L[-1]['bold'] |= any('Bold' in s['font'] for s in sp); continue
            L.append(dict(t=t, y0=y0, x0=l['bbox'][0], x1=l['bbox'][2], size=max(s['size'] for s in sp), bold=any('Bold' in s['font'] for s in sp), font=sp[0]['font']))
    L.sort(key=lambda r: (round(r['y0']), r['x0']))
    return L


PAGES = []
for n in range(1, N + 1):
    L = lines_of(src[n - 1])
    lab = ''
    keep = []
    for l in L:
        m = re.fullmatch(r'\s*-\s*(\d+)\s*-\s*', l['t'])
        if m and l['y0'] > 760: lab = m.group(1); continue
        keep.append(l)
    paras = []; cur = None; prev = None
    for l in keep:
        t = l['t']
        if l['bold'] and re.match(r'\s*제\s*\d+\s*과', t):
            paras.append('## ' + t.strip()); cur = None; prev = l; continue
        gap = l['y0'] - prev['y0'] if prev else 0
        indented = t[:1] in (' ', '\xa0')   # 게송 번역 줄은 빈칸(줄바꿈 없는 빈칸)으로 들여 씀
        if cur is not None and prev is not None and gap < 24 and prev['x1'] > FULL and not prev.get('h'):
            # 줄이 끝까지 찼음 → 이어 붙임
            a = paras[-1]
            paras[-1] = a + t if a.endswith(' ') else a + t.lstrip() if t.startswith(' ') else a + t
            log['이음'] += 1
        elif cur is not None and prev is not None and gap < 24 and indented and prev['x1'] < 300:
            paras[-1] = paras[-1].rstrip() + '\n' + t.strip(); log['게송'] += 1
        else:
            paras.append(t); cur = True
        prev = l
    paras = [re.sub(r'[ \t]+$', '', p, flags=re.M).strip() if not p.startswith('## ') else p for p in paras]
    PAGES.append(dict(n=n, lab=lab, paras=[p for p in paras if p]))

# 1쪽: 차례 — 제목 줄과 차례 줄들
toc_lines = []
body1 = []
for l in lines_of(src[0]):   # 차례 줄은 인쇄된 줄 그대로(이어 붙이지 않음)
    line = l['t'].strip()
    if re.match(r'^\d+p', line): toc_lines.append(line)
    else: body1.append(line)
print('1쪽 차례 아닌 줄', body1)
PAGES[0]['paras'] = [':: ' + body1[0], '^^ ' + body1[1], '## ' + body1[2].strip('* ').strip()] + ['\n'.join(toc_lines)] + body1[3:]

chapters = [('차례', 1)]
for P in PAGES:
    for k, p in enumerate(P['paras']):
        if p.startswith('## 제'):
            chapters.append((p[3:].strip(), P['n'], k))
toc = [dict(title='차례 (내용)', page=1, sub=False)]
for t, n, k in chapters[1:]:
    toc.append(dict(title=re.sub(r'[\s\xa0]+', ' ', t), page=n, sub=False, **({'at': t[:20]} if k > 0 else {})))
last = PAGES[-1]
last['paras'] = ['^^ ' + last['paras'][0]] + last['paras'][1:]
toc.append(dict(title='맺음말', page=last['n'], sub=False))
body = ''
for P in PAGES:
    body += f"=== {P['lab'] + '쪽' if P['lab'] else ''} ===\n".replace('===  ===', '=== ===') + '\n\n'.join(P['paras']) + '\n\n'
body = body.rstrip() + '\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [], 'body': body}, open(out, 'w'), ensure_ascii=False, indent=1)
print(log, '장', len(toc), '→', out)
