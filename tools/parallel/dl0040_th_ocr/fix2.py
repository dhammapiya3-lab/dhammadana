# ocrM(세 인식 다수결) → 성조+ำ, 윗모음 위 성조 부호를 글자 자리(ocrT 의 조각 가로 자리)로 정확히 맞춰 고침 → ocrC
import json, re, os, difflib, numpy as np, fitz
from PIL import Image
import amfix, tonefix
from pythainlp import word_tokenize
from pythainlp.corpus import thai_words
WD = set(thai_words()) | set('ๆฯ')
def oov(x): return sum(1 for w in word_tokenize(x.replace(' ', ''), keep_whitespace=False) if re.search('[ก-๛]', w) and w not in WD and not re.fullmatch('[๐-๙]+', w))
def better(old, cands):
    # 사전 밖 낱말이 늘지 않는 첫 후보 (없으면 그대로)
    o = oov(old)
    for c in cands:
        if oov(c) <= o: return c
    return old
d = fitz.open('src.pdf'); os.makedirs('ocrC', exist_ok=True)
RULES = [(r'ํา', 'ำ'), (r'([่้๊๋])\1+', r'\1'), (r'([่้๊๋])([่้๊๋])(?=[ำา])', r'\2')]
log = []
def xmap(t, segs):
    # t 의 글자마다 가로 자리 (조각 글자를 고르게 나눔)
    st = ''; xs = []
    for x0, x1, s in segs:
        s2 = s.replace(' ', ''); n = max(1, len(s2))
        for k, ch in enumerate(s2): st += ch; xs.append(x0 + (x1 - x0) * (k + .5) / n)
    out = [None] * len(t); tt = [(k, ch) for k, ch in enumerate(t) if ch != ' ']
    sm = difflib.SequenceMatcher(None, ''.join(c for _, c in tt), st, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        for q in range(i1, i2):
            jj = j1 + (q - i1) * max(0, j2 - j1 - 1) // max(1, i2 - i1 - 1) if op != 'equal' else j1 + q - i1
            if j1 < j2 or op == 'equal': out[tt[q][0]] = xs[min(len(xs) - 1, max(0, jj))] if xs else None
    # 비어 있는 자리는 앞뒤로 채움
    last = None
    for k in range(len(out)):
        if out[k] is None: out[k] = last
        else: last = out[k]
    return out
for i in range(287):
    D = json.load(open(f'ocrM/{i:03d}.json')); T = {l['y0']: l for l in json.load(open(f'ocrT/{i:03d}.json'))['lines']}
    pix = d[i].get_pixmap(dpi=300, colorspace=fitz.csGRAY); im = np.array(Image.frombytes('L', (pix.width, pix.height), pix.samples)) < 128
    for l in D['lines']:
        t0 = t = l['t']
        for a, b in RULES: t = re.sub(a, b, t)
        if not (250 < l['y0'] < 2990) or l['y1'] - l['y0'] < 28 or l['y0'] not in T: l['t'] = t; continue
        a = im[l['y0']:l['y1'], :]; rows = a.sum(1); body = np.where(rows > rows.max() * .45)[0]
        if not len(body): l['t'] = t; continue
        xtop = body[0]
        if xtop < 4: l['t'] = t; continue
        X = xmap(t, T[l['y0']]['segs'])
        if None in X or not X: l['t'] = t; continue
        # ① 성조 + ำ
        rx = amfix.rings(a, xtop); tl = list(t)
        for r in rx:
            c = [k for k in range(len(tl) - 1) if tl[k] in '่้๊๋' and tl[k + 1] in 'าำ' and abs(X[k] - r) < 22]
            if c:
                k = min(c, key=lambda k: abs(X[k] - r))
                if tl[k + 1] == 'า':
                    t1 = tl[:]; t1[k + 1] = 'ำ'; t2 = t1[:]; t2[k] = '้' if tl[k] == '่' else '่'
                    tl = list(better(''.join(tl), [''.join(t1), ''.join(t2)]))
        # ② 윗모음 위 성조 부호
        st = [s for s in tonefix.stacked(a, xtop) if s[1] != '?']
        for x, kd, _ in st:
            if None in X: break
            c = [k for k in range(len(tl)) if tl[k] in 'ัิีึื' and abs(X[k] - x) < 18]
            if not c: continue
            k = min(c, key=lambda k: abs(X[k] - x))
            nx = tl[k + 1] if k + 1 < len(tl) else ''
            if kd not in '่้': continue
            t1 = tl[:]
            if nx and nx in '่้๊๋':
                if nx == kd: continue
                t1[k + 1] = kd
            else: t1[k] = t1[k] + kd
            nl_ = list(better(''.join(tl), [''.join(t1)]))
            if len(nl_) != len(tl): X = xmap(''.join(nl_), T[l['y0']]['segs'])
            tl = nl_
        t = ''.join(tl)
        if t != t0: log.append((i + 1, l['y0'], t0, t))
        l['t'] = t
    json.dump(D, open(f'ocrC/{i:03d}.json', 'w'), ensure_ascii=False)
json.dump(log, open('fix2.json', 'w'), ensure_ascii=False, indent=0)
print('고친 줄', len(log))
