"""대조 번역본(워드 파일)을 문장으로 나눈다 — 글자는 바꾸지 않음.
python3 ref_build.py 대조번역본.docx → ref_sents.json [{p 문단, t 문장, h 제목}]"""
import sys, json, re, docx
sys.path.insert(0, __import__('os').path.dirname(__file__))
END = r'[.?!…](?:[’”\'"」』)\]]+)?(?=\s|$)'
def split(t):
    out = []; i = 0
    for m in re.finditer(END, t):
        j = m.end()
        if re.search(r'(?:\bMr|\bMrs|\bDr|\bSt|\bNo|\bBhd|\bSdn|\b[A-Z])\.$', t[i:j]) or re.fullmatch(r'\s*\d+\.', t[i:j]): continue
        seg = t[i:j]
        if seg.strip(): out.append(seg.strip())
        i = j
    if t[i:].strip(): out.append(t[i:].strip())
    return out
d = docx.Document(sys.argv[1]); S = []; P = []
for pi, p in enumerate(d.paragraphs):
    t = p.text
    if not t.strip(): continue
    P.append(t); h = p.style.name.startswith('Heading')
    for line in t.split('\n'):           # 줄 바꿈(주소·서명 등)은 따로
        for s in ([line.strip()] if h else split(line)):
            if s: S.append(dict(p=len(P) - 1, t=s, h=h))
# 글자 대조
a = re.sub(r'\s', '', ''.join(P)); b = re.sub(r'\s', '', ''.join(s['t'] for s in S)); assert a == b
json.dump(dict(paras=P, sents=S), open('ref_sents.json', 'w'), ensure_ascii=False)
print('paras', len(P), 'sents', len(S), 'heads', sum(s['h'] for s in S))
