"""교정용 — 한글 음역 검사 (운영자 요청, 2026-11-20: '음역만 있을 때도 바른 것인지 함께 검수')
먼저 `node tools/translit_set.mjs <ID>` 로 바른 음역 목록을 만든 뒤
`python3 tools/translit_check.py <ID>` → ① 로마자 없이 한글로만 쓴 낱말 가운데, 바른 음역 목록에 없고
된소리·거센소리(ㄲ/ㅋ/ㄱ, ㄸ/ㅌ/ㄷ, ㅃ/ㅍ/ㅂ, ㅉ/ㅊ/ㅈ)·v(바↔와)·겹자음 받침을 한두 군데 바꾸면 목록에 있는 것
(kiwi 가 낯선 낱말로 보는 것만 — 보통 우리말은 뺌) ② '한글(로마자)' 짝에서 한글이 규칙 음역과 다른 것.
③ (2026-11-25 운영자 요청) 여러 곳을 함께 바꿔야 바른 음역이 되는 낱말 — 된소리·거센소리·예사소리, 받침, 바↔와(v)를
같은 것으로 본 '뼈대'가 바른 음역 목록의 낱말과 같은 것(예: 담마짜카팟바따나 → 담마짝깝빠왓따나). 우리말이 조금 섞여 나옴.
결과는 '확인할 곳' — 사람이 원어와 규칙을 보고 판단한다(독송 소리 줄·현대 지명·산스끄리뜨는 규칙 밖).
DPD 목록은 점·막대를 뺀 꼴이라 ṅ·ñ 낱말은 '산가'처럼 틀린 후보가 섞이므로 후보 꼴을 그대로 믿지 말 것."""
import json, re, sys, difflib
from kiwipiepy import Kiwi
ROOT = __file__.rsplit('/tools/', 1)[0]
ID = sys.argv[1]
S = set(json.load(open(ROOT + '/tools/out/translit/set.json')))
body = json.load(open(f'{ROOT}/content/texts/{ID}.json'))['body']
def dec(c): o = ord(c) - 0xAC00; return o // 588, (o % 588) // 28, o % 28
def comp(i, v, j): return chr(0xAC00 + i * 588 + v * 28 + j)
TRI = {0: [1, 15], 1: [0, 15], 15: [0, 1], 3: [4, 16], 4: [3, 16], 16: [3, 4], 7: [8, 17], 8: [7, 17], 17: [7, 8], 12: [13, 14], 13: [12, 14], 14: [12, 13]}
VW = {0: 9, 20: 16, 5: 15}
def vars1(s):
    i, v, j = dec(s); out = set()
    for k in TRI.get(i, []): out.add(comp(k, v, j))
    if i == 7 and v in VW: out.add(comp(11, VW[v], j))
    if i == 11 and v in VW.values(): out.add(comp(7, {b: a for a, b in VW.items()}[v], j))
    for jj in (0, 19, 1, 17, 4, 8, 21):
        if jj != j: out.add(comp(i, v, jj))
    return out
def variants(w):
    L = list(w); res = set()
    for a in range(len(L)):
        for x in vars1(L[a]):
            w1 = L[:a] + [x] + L[a + 1:]; res.add(''.join(w1))
            for b in range(a + 1, len(L)):
                for y in vars1(L[b]): res.add(''.join(w1[:b] + [y] + w1[b + 1:]))
    return res
kw = Kiwi(); found = {}
pages = re.split(r'^=== (.*?) ===$', body, flags=re.M)
for k in range(1, len(pages), 2):
    txt = re.sub(r'\*\*|°°|==|\[\^[^\]]*\]', '', pages[k + 1])
    for line in txt.split('\n'):
        if not re.search('[가-힣]', line): continue
        for tk in kw.tokenize(line):
            f = tk.form
            if tk.tag not in ('NNG', 'NNP', 'NR') or len(f) < 3 or not re.fullmatch('[가-힣]+', f) or f in S: continue
            if kw.analyze(f)[0][1] / len(f) > -7.5: continue
            vs = [v for v in variants(f) if v in S]
            if vs: found.setdefault(f, {'v': vs, 'pg': []})['pg'].append(pages[k])
print('① 한글로만 쓴 음역 — 규칙과 다를 수 있는 곳')
for p, d in found.items(): print(' ', p, '→', ' / '.join(sorted(d['v'])[:4]), '|', ','.join(dict.fromkeys(d['pg'])))
print('② 한글(로마자) 짝 — 한글이 규칙 음역과 다른 곳')
try: pairs = json.load(open(f'{ROOT}/tools/out/translit/pairs-{ID}.json'))
except FileNotFoundError: pairs = []
for pg, ko, ro, k in pairs:
    if not k: continue
    kk = ko.replace(' ', ''); best = max((kk[i:] for i in range(len(kk))), key=lambda s: difflib.SequenceMatcher(None, s, k).ratio())
    r = difflib.SequenceMatcher(None, best, k).ratio()
    if best != k and r >= 0.5: print(' ', pg, '|', ko, f'({ro})', '규칙:', k)

print('③ 여러 곳을 함께 바꿔야 하는 음역 — 뼈대가 바른 음역과 같은 곳')
CL = {0: 0, 1: 0, 15: 0, 3: 3, 4: 3, 16: 3, 7: 7, 8: 7, 17: 7, 12: 12, 13: 12, 14: 12, 9: 9, 10: 9}
def sk(w):
    o = []
    for c in w:
        i, v, j = dec(c); i = CL.get(i, i)
        if i == 11 and v in (9, 14, 15, 16): i, v = 7, {9: 0, 14: 4, 15: 5, 16: 20}[v]
        o.append(comp(i, v, 0))
    return ''.join(o)
D = {}
for w in S:
    if len(w) >= 3: D.setdefault(sk(w), set()).add(w)
JOS = set('가 이 은 는 을 를 의 에 와 과 도 로 만 나 께 들'.split()) | {'으로', '에서', '에게', '에는', '에도', '와의', '과의', '로서', '로써', '라는', '라고', '이라', '이다', '이고', '이며', '들이', '들은', '들의', '들을', '께서', '처럼', '보다', '부터', '까지', '에게서', '으로서', '이라는', '이었다', '였다', '이나', '이든', '이란', '와는', '과는'}
plain = re.sub(r'\*\*|°°|==|\[\^[^\]]*\]', '', body); hit = {}
for pg, tx in zip(pages[1::2], pages[2::2]):
    for run in re.findall('[가-힣]{3,}', re.sub(r'\*\*|°°|==|\[\^[^\]]*\]', '', tx)):
        for cut in range(0, 4):
            w = run[:len(run) - cut]; tail = run[len(run) - cut:]
            if len(w) < 3: break
            if cut and tail not in JOS: continue
            if w in S or w in found: break
            c = D.get(sk(w))
            if c and not re.search('(하|받|갔|왔|랐|났|할|볼)$', w) and kw.analyze(w)[0][1] / len(w) <= -8.5:
                hit.setdefault(w, {'v': sorted(c)[:4], 'pg': []})['pg'].append(pg); break
for p, d in sorted(hit.items()): print(' ', p, '→', ' / '.join(d['v']), '|', ','.join(dict.fromkeys(d['pg'])))
