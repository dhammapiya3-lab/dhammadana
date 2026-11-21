"""DL-0040 원문 대조 — 본문 JSON 글자(빈칸·표시 빼고)가 PDF 글자와 같은지
  python3 tools/dl0040_verify.py 책.pdf
PDF 쪽 2~310(1쪽 앞표지 그림 빼고)의 글자를 위에서 아래 차례로, 본문은 쪽 표시·꾸밈 표시(^^ :: ++ >> ## %% ~ -)를 빼고
각주 번호 [^N]·[^*N] → 'N)' 또는 'N', 각주 풀이는 쪽 아래로 모아 견줌. 쪽을 넘어 이어 붙인 문단 때문에 쪽 경계는 보지 않고 책 전체를 한 줄로 견줌.
"""
import sys, re, json, os, difflib
import fitz
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = fitz.open(sys.argv[1])


def k(s):
    return re.sub(r'\s', '', s)


pdf = []
for n in range(2, d.page_count + 1):
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(c['c'] for s in l['spans'] for c in s['chars'])
            if re.fullmatch(r'\s*-\s*\d+\s*-\s*', t) or re.fullmatch(r'\s*_+\s*', t): continue
            pdf.append(t)
P = k(''.join(pdf))
P = re.sub(r'\d+\)|\d+', '', P)   # 번호는 견주지 않음 (각주 번호 모양이 다름)

body = json.load(open(os.path.join(REPO, 'content/texts/DL-0040.json')))['body']
B = re.sub(r'^=== .*? ===$', '', body, flags=re.M)
B = re.sub(r'^\[\^\*?\d+\]:', '', B, flags=re.M)
B = re.sub(r'\[\^\*?\d+\]', '', B)
B = re.sub(r'^(\^\^|::|\+\+|>>|##|%%) ?', '', B, flags=re.M)
B = re.sub(r'^(- |~$)', '', B, flags=re.M)
B = re.sub(r'\d+\)|\d+', '', k(B))
print('PDF 글자', len(P), '본문 글자', len(B))
# 글자 모음이 같은지(차례는 각주 자리·차례 쪽 자리 때문에 다를 수 있음)
from collections import Counter
cp, cb = Counter(P), Counter(B)
diff = {c: (cp[c], cb[c]) for c in set(cp) | set(cb) if cp[c] != cb[c]}
print('글자별 개수가 다른 것:', diff or '없음')

# 차례까지 견줌 — 각주 풀이는 양쪽에서 빼고 (PDF: T 글꼴 줄과 '____' 아래 줄)
pdf2 = []
for n in range(2, d.page_count + 1):
    infn = False
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if ''.join(c['c'] for c in s['chars']).strip()]
            t = ''.join(c['c'] for s in l['spans'] for c in s['chars'])
            if re.fullmatch(r'\s*-\s*\d+\s*-\s*', t): continue
            if re.fullmatch(r'\s*_+\s*', t): infn = True; continue
            if (infn and max(x['size'] for x in sp) < 11) or (sp and re.fullmatch(r'T\d+', sp[0]['font'])): continue
            pdf2.append((l['bbox'][1], t))
    # (같은 쪽 안 차례는 rawdict 차례 그대로)
P2 = re.sub(r'\d+\)|\d+', '', k(''.join(t for _, t in pdf2)))
B2 = re.sub(r'^\[\^\*?\d+\]:.*?(?=\n\n|\Z)', '', body, flags=re.M | re.S)
B2 = re.sub(r'^=== .*? ===$', '', B2, flags=re.M)
B2 = re.sub(r'\[\^\*?\d+\]', '', B2)
B2 = re.sub(r'^(\^\^|::|\+\+|>>|##|%%) ?', '', B2, flags=re.M)
B2 = re.sub(r'^(- |~$)', '', B2, flags=re.M)
B2 = re.sub(r'\d+\)|\d+', '', k(B2))
sm = difflib.SequenceMatcher(None, P2, B2, autojunk=False)
bad = [(op, P2[i1 - 10:i2 + 10], B2[j1 - 10:j2 + 10]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal']
print('차례대로 견줌(각주 뺌) — 다른 곳', len(bad))
for x in bad[:20]: print(x)

# 각주만 견줌 — PDF 쪽 차례의 각주 줄 ↔ 본문 각주 풀이(번호 차례, *번호는 그 쪽 차례에)
fpdf = []
for n in range(2, d.page_count + 1):
    infn = False
    for b in d[n - 1].get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if ''.join(c['c'] for c in s['chars']).strip()]
            t = ''.join(c['c'] for s in l['spans'] for c in s['chars'])
            if re.fullmatch(r'\s*-\s*\d+\s*-\s*', t): continue
            if re.fullmatch(r'\s*_+\s*', t): infn = True; continue
            if (infn and max(x['size'] for x in sp) < 11) or (sp and re.fullmatch(r'T\d+', sp[0]['font'])): fpdf.append(t)
FP = re.sub(r'\d+\)|\d+', '', k(''.join(fpdf)))
defs = re.findall(r'^\[\^(\*?\d+)\]:(.*?)(?=\n\n|\Z)', body, flags=re.M | re.S)
order = sorted(defs, key=lambda x: (int(x[0].lstrip('*')) + (0.5 if x[0].startswith('*') else 0) if not x[0].startswith('*') else 40.6 + int(x[0][1:]) * 0 + {'40': 50.5, '41': 52.5, '42': 52.6}[x[0][1:]]))
FB = re.sub(r'\d+\)|\d+', '', k(''.join(t for _, t in order)))
sm = difflib.SequenceMatcher(None, FP, FB, autojunk=False)
bad = [(op, FP[i1 - 10:i2 + 10], FB[j1 - 10:j2 + 10]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal']
print('각주 견줌 — 다른 곳', len(bad))
for x in bad[:10]: print(x)
