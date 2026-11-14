#!/usr/bin/env python3
"""『테라와다 불교의범』(DL-0026) 양쪽으로 보기에서 왼쪽 빠알리와 오른쪽 번역을 줄 높이에 맞추기 위한 자료.

인쇄본 PDF 에서 쪽마다 줄의 세로 자리(pt)를 읽어, 글로 읽기 본문의 문단·줄마다 그 높이를 찾아
content/texts/DL-0026.json 의 `ly` 에 넣는다 — {"쪽 순번": [[문단 0 의 줄 높이…], [문단 1 …], …]}.
본문 글자는 바꾸지 않는다. 찾지 못한 줄은 null.

쓰는 법: python3 tools/dl0026_lineys.py 책.pdf
"""
import json, re, sys, difflib
import fitz

ID = 'DL-0026'
TXT = f'content/texts/{ID}.json'


def norm(s):
    s = re.sub(r'\[\^[\w-]+\]', '', s)
    s = re.sub(r'^(## |\^\^ |:: |>> |\+\+ |\|\| |%% |-+ )', '', s)
    s = s.replace('**', '').replace('==', '')
    return re.sub(r'[\s　.,;:!?“”‘’"\'()\[\]「」『』·․ㆍ\-–—~]', '', s)


def pdf_lines(page):
    L = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans'])
            if not t.strip(): continue
            L.append([(l['bbox'][1] + l['bbox'][3]) / 2, l['bbox'][0], t])
    L.sort(key=lambda r: (round(r[0]), r[1]))
    out = []
    for y, x, t in L:
        if out and abs(out[-1][0] - y) < 3.5: out[-1][2] += ' ' + t
        else: out.append([y, x, t])
    return [(round(y, 1), norm(t)) for y, x, t in out if norm(t)]


def paras(t):
    return [s for s in ('\n'.join(l.strip() for l in p.strip().split('\n')) for p in re.split(r'\n\s*\n', t or '')) if s]


def match(a, b):
    if not a or not b: return False
    k = min(6, len(a), len(b))
    if a[:k] == b[:k]: return True
    return difflib.SequenceMatcher(None, a[:20], b[:20]).ratio() > 0.72


def main(pdf):
    doc = fitz.open(pdf)
    d = json.load(open(TXT))
    parts = re.split(r'^=== *(.*?) *===$', d['body'], flags=re.M)
    pages = [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]
    ly, found, total = {}, 0, 0
    for n, (label, text) in enumerate(pages, 1):
        m = re.match(r'(\d+)쪽', label)
        if not m: continue
        pn = int(m.group(1))
        if pn < 1 or pn > len(doc): continue
        P = pdf_lines(doc[pn - 1]); ptr = 0; res = []
        for p in paras(text):
            ys = []
            for line in p.split('\n'):
                if line.startswith('![') or line == '~':
                    ys.append(None); continue
                a = norm(line); total += 1; hit = None
                for j in range(ptr, min(len(P), ptr + 10)):
                    if match(a, P[j][1]): hit = j; break
                if hit is None: ys.append(None); continue
                ys.append(P[hit][0]); ptr = hit + 1; found += 1
            res.append(ys)
        if any(y is not None for ys in res for y in ys): ly[str(n)] = res
    d['ly'] = ly
    json.dump(d, open(TXT, 'w'), ensure_ascii=False, indent=1)
    print(f'줄 높이 찾음 {found}/{total} 줄, {len(ly)} 쪽')


if __name__ == '__main__':
    main(sys.argv[1])
