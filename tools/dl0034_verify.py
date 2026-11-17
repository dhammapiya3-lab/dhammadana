"""DL-0034 원문 대조: PDF 글자(머리글·쪽 번호·그림으로 넣은 표 글자 빼고)와 content/texts/DL-0034.json 본문 글자가 같은지 (빈칸 빼고 글자 수 비교)
  python3 tools/dl0034_verify.py 책.pdf"""
import sys, os, re, json, collections
import fitz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dl0034_lib import Page, refy
doc = fitz.open(sys.argv[1])
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t = json.load(open(os.path.join(REPO, 'content/texts/DL-0034.json')))
src = collections.Counter()
for n in list(range(3, 10)) + list(range(29, 721)):
    P = Page(doc, n); L = P.lines(); img, cols = P.tables(L)
    if P.fy and any(r.y1 > P.fy + 5 for r in img): P.fy = refy(P, img, L); L = P.lines(); img, cols = P.tables(L)
    for l in L:
        if l['zone'] in ('head', 'foot'): continue
        if l['zone'] == 'body' and any(r.x0 - 1 <= l['x0'] and l['x1'] <= r.x1 + 1 and r.y0 - 2 <= l['y'] <= r.y1 + 3 for r in img): continue
        s = ''.join(c['c'] for c in l['cs'] if not c.get('sup') or not re.match(r'[\d)]', c['c']))
        if l['zone'] == 'fn': s = re.sub(r'^\s*\d+\)', '', s)
        for ch in s:
            if ch.strip(): src[ch] += 1
body = t['body']
# 차례·표 차례·속표지는 따로 만든 것이라 뺌
segs = re.split(r'(?m)^===.*?===$', body)
out = collections.Counter()
for seg in segs:
    for p in seg.split('\n\n'):
        p = p.strip()
        if not p or p.startswith('%% ') or p.startswith('![') or p.startswith('^^ '): continue
        p = re.sub(r'^\[\^[^\]]+\]:\s*', '', p)
        p = re.sub(r'\[\^[^\]]+\]', '', p)
        p = re.sub(r'^## ', '', p, flags=re.M)
        p = p.replace('**', '').replace('°°', '')
        for ch in p:
            if ch.strip(): out[ch] += 1
# 차례 제목 '## 제목 차례…' 등 만든 제목 글자
for extra in ['제목차례[요약]', '제목차례[자세한]', '<표차례>']:
    for ch in extra: out[ch] -= 1
d1 = src - out; d2 = out - src
print('PDF 글자', sum(src.values()), '본문 글자', sum(out.values()))
print('PDF 에만:', d1.most_common(30)); print('본문에만:', d2.most_common(30))
