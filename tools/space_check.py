#!/usr/bin/env python3
"""띄어쓰기 정밀 검사 (운영자 요청, 2026-11-28 — DL-0040 '필수적 이다'를 놓친 뒤)

규칙 찾기(정해 둔 꼴만 찾음)로는 놓치는 띄어쓰기를 문법으로 찾는다. 결과는 '확인할 곳' — 바로 고치지 않는다.

① 붙여야 할 곳 (정밀도 높음): 빈칸 바로 뒤에서 조사(J…)·서술격 조사 '이다'(VCP)·어미(E…)·접미사(XS…)가
   낱말을 시작하는 곳 — 우리말에서 이것들은 앞말에 붙여 쓴다. 예: '필수적 이다', '때문 이었다', '상태 이므로'.
② 같은 낱말 되풀이: '이고 이고'·'결코 결코' 처럼 바로 이어 두 번 나온 낱말.
③ kiwi 띄어쓰기 제안과 다른 곳 가운데, 책 안에서 다른 꼴(붙인 꼴/띄운 꼴)이 더 많이 쓰인 곳 — 책 안 쓰임 수와 함께.

쓰는 법: python3 tools/space_check.py content/texts/DL-0040.json [--out 결과.tsv]
꾸밈 표시(** °° @@ __ 등)·로마자·한자·각주 번호는 건너뜀. 독송 소리 줄·인용한 옛 글은 사람이 판단.
"""
import json, re, sys, collections
from kiwipiepy import Kiwi

p = sys.argv[1]
out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
d = json.load(open(p, encoding='utf-8'))
body = d['body']
kiwi = Kiwi()

MARK = re.compile(r'\*\*|°°|@@|__|==|§§|\{\{|\}\}|\[\^[^\]]*\]')
rows = []
page = ''
lines = []
for raw in body.split('\n'):
    m = re.match(r'^=== (.*) ===$', raw)
    if m: page = m.group(1); continue
    if raw.startswith('[^') or raw.startswith('![') or raw.startswith('|') or raw.startswith('%%'): continue
    t = MARK.sub('', raw)
    t = re.sub(r'^(\^\^|::|>>|\+\+|\|\||## |~)\s*', '', t)
    if re.search(r'[가-힣]', t): lines.append((page, t))

# ① 빈칸 뒤 조사·이다·어미로 시작하는 낱말
BAD = re.compile(r'^(J|VCP|E|XS)')
OK_AFTER = set('“‘"\'(「『〈《[【')
for pg, t in lines:
    toks = kiwi.tokenize(t)
    for i, tk in enumerate(toks):
        if tk.start == 0 or t[tk.start - 1] != ' ': continue
        if not BAD.match(tk.tag): continue
        # 같은 자리에서 시작하는 다른 형태소(줄어든 꼴 '건'=걸+ㄴ 등)가 있으면 조사·어미로 시작하는 낱말이 아님
        if any(o.start == tk.start and not BAD.match(o.tag) for o in toks): continue
        if i and toks[i - 1].start + toks[i - 1].len > tk.start: continue
        prev = t[:tk.start - 1]
        if not prev or not re.search(r'[가-힣0-9)\]』」]$', prev): continue   # 앞이 한글·숫자·닫는 괄호일 때만
        if tk.tag.startswith('XS') and tk.form in ('적', '들'): pass
        w0 = re.search(r'(\S+)$', prev).group(1)
        w1 = re.match(r'\S+', t[tk.start:]).group(0)
        # '문제들 이 10가지는'처럼 혼자 떨어진 '이·그·저' 뒤에 다른 말이 오면 조사가 아니라 가리키는 말(이 10가지)일 수 있음
        #   → 붙이면 뜻이 바뀌므로 문맥을 읽고 정함 (쉼표를 넣어 '문제들, 이 10가지는'이 맞는 곳이 있음, 2026-11-28)
        if w1 in ('이', '그', '저') and re.match(r'\s+\S', t[tk.start + len(w1):]):
            rows.append(('①? 가리키는 말일 수 있음 — 문맥 확인', pg, f'{w0} {w1}', f'{w0}{w1} 또는 {w0}, {w1}', f'{tk.form}/{tk.tag}', t[max(0, tk.start - 25):tk.start + 20]))
            continue
        rows.append(('① 붙여 쓸 곳', pg, f'{w0} {w1}', f'{w0}{w1}', f'{tk.form}/{tk.tag}', t[max(0, tk.start - 25):tk.start + 20]))

# ② 바로 이어 되풀이된 낱말
for pg, t in lines:
    for m in re.finditer(r'(?<![가-힣])([가-힣]{2,})\s+\1(?![가-힣])', t):
        if m.group(1) in ('점점', '새록', '하나', '때때'): continue
        rows.append(('② 되풀이', pg, m.group(0), m.group(1), '', t[max(0, m.start() - 20):m.end() + 20]))

# ③ kiwi 띄어쓰기 제안과 다른 곳 — 책 안에서 다른 꼴이 더 많을 때만
alltext = ' '.join(t for _, t in lines)
def count(s): return len(re.findall(r'(?<![가-힣])' + re.escape(s) + r'(?![가-힣])', alltext)) if ' ' in s else alltext.count(s)
for pg, t in lines:
    sp = kiwi.space(t, reset_whitespace=False)
    if sp == t: continue
    a = t.split(' '); b = sp.split(' ')
    # 빈칸 넣기 제안: 원문 한 낱말이 제안에서 두 낱말
    for w in a:
        if w and w not in sp.split(' ') and re.fullmatch(r'[가-힣]{3,}', w):
            for j in range(1, len(w)):
                cand = w[:j] + ' ' + w[j:]
                if cand in sp:
                    n1, n2 = count(w), count(cand)
                    if n2 > n1: rows.append(('③ 책 안 다른 꼴이 많음', pg, w, cand, f'붙임 {n1}·띄움 {n2}', t[max(0, t.find(w) - 20):t.find(w) + len(w) + 20]))
                    break
    # 빈칸 빼기 제안
    for m in re.finditer(r'([가-힣]+) ([가-힣]+)', t):
        j = m.group(1) + m.group(2)
        if j in sp.split(' '):
            n1, n2 = count(m.group(0)), count(j)
            if n2 > n1: rows.append(('③ 책 안 다른 꼴이 많음', pg, m.group(0), j, f'띄움 {n1}·붙임 {n2}', t[max(0, m.start() - 20):m.end() + 20]))

seen = set(); res = []
for r in rows:
    k = (r[0], r[1], r[2])
    if k in seen: continue
    seen.add(k); res.append(r)
for g in sorted(set(r[0] for r in res)):
    print(g, sum(1 for r in res if r[0] == g))
txt = '묶음\t쪽\t지금 글\t제안\t근거\t앞뒤 글\n' + '\n'.join('\t'.join(r) for r in res) + '\n'
if out: open(out, 'w', encoding='utf-8').write(txt)
else: print(txt[:6000])
