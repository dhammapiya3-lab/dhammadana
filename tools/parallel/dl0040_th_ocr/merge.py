# 세 글자 인식(ocr3 300dpi·ocr4 400dpi·ocr5 360dpi 2진화)을 다수결로 합침 → ocrM/NNN.json
#   ocr3 줄을 바탕으로, 다른 두 결과가 같게 읽은 곳은 그 글로. 셋이 모두 다르면 사전 낱말이 많은 쪽, 그래도 모르면 '확인할 곳'으로.
import json, re, difflib, os
from pythainlp import word_tokenize
from pythainlp.corpus import thai_words
W = set(thai_words())
def cl(t): t = t.replace('ํา','ำ'); t = re.sub(r'[|\]\[]',' ',t); return re.sub(r'\s+',' ',t).strip()
def score(s):
    toks = [x for x in word_tokenize(s, keep_whitespace=False) if re.search('[ก-๛]', x)]
    return sum(1 for x in toks if x in W) - len(toks) * .0 - sum(1 for x in toks if x not in W) * 1.0
def near(L, ya, sc):
    c = [b for b in L if abs((b['y0'] + b['y1']) / 2 / sc - ya) < 25]
    return min(c, key=lambda b: abs((b['y0'] + b['y1']) / 2 / sc - ya)) if c else None
os.makedirs('ocrM', exist_ok=True); flags = []; nfix = 0
for i in range(287):
    D = json.load(open(f'ocr3/{i:03d}.json')); B = json.load(open(f'ocr4/{i:03d}.json'))['lines']; C = json.load(open(f'ocr5/{i:03d}.json'))['lines']
    for a in D['lines']:
        ya = (a['y0'] + a['y1']) / 2
        b = near(B, ya, 4 / 3); c = near(C, ya, 1.2)
        ta = cl(a['t']); a['t0'] = a['t']
        sa = ta.replace(' ', ''); sb = cl(b['t']).replace(' ', '') if b else sa; sc_ = cl(c['t']).replace(' ', '') if c else sa
        if sa == sb == sc_: a['t'] = ta; continue
        # sa 의 글자 자리 → sc 의 글자 자리
        mc = difflib.SequenceMatcher(None, sa, sc_, autojunk=False).get_opcodes()
        def ctext(i1, i2):
            out = ''
            for op, x1, x2, y1, y2 in mc:
                if op == 'equal':
                    lo, hi = max(i1, x1), min(i2, x2)
                    if lo < hi: out += sc_[y1 + lo - x1:y1 + hi - x1]
                else:
                    if x1 < i2 and x2 > i1 or (x1 == x2 and i1 <= x1 <= i2 and (i1 < x1 < i2 or i1 == i2 == x1)): out += sc_[y1:y2]
            return out
        res = []; pos = 0
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sa, sb, autojunk=False).get_opcodes():
            if op == 'equal': res.append(('=', sa[i1:i2])); continue
            va, vb, vc = sa[i1:i2], sb[j1:j2], ctext(i1, i2)
            if vb == vc: pick = vb; why = 'vote'
            elif va == vc: pick = va; why = 'vote'
            else:
                ctx_a = sa[max(0, i1 - 12):i1]; ctx_b = sa[i2:i2 + 12]
                cands = {v: score(ctx_a + v + ctx_b) for v in (va, vb, vc)}
                best = max(cands.values()); top = [v for v in (va, vb, vc) if cands[v] == best]
                pick = top[0]; why = 'dict' if len(top) == 1 else 'tie'
                flags.append({'pdf': i + 1, 'y0': a['y0'], 'y1': a['y1'], 'x0': a['x0'], 'x1': a['x1'], 'ctx': ctx_a + '[' + va + '|' + vb + '|' + vc + ']' + ctx_b, 'pick': pick, 'why': why})
            res.append(('x', pick, va)); nfix += pick != va
        # 빈칸을 ocr3 자리에 다시 넣음
        sp = [k for k, ch in enumerate(ta.replace(' ', '\x00', 0)) if ch == ' ']
        spos = set(); n = 0
        for ch in ta:
            if ch == ' ': spos.add(n)
            else: n += 1
        out = ''; n = 0
        for r in res:
            if r[0] == '=':
                for ch in r[1]:
                    if n in spos: out += ' '
                    out += ch; n += 1
            else:
                if n in spos: out += ' '
                out += r[1]; n += len(r[2])
        a['t'] = out
    json.dump(D, open(f'ocrM/{i:03d}.json', 'w'), ensure_ascii=False)
json.dump(flags, open('flags.json', 'w'), ensure_ascii=False, indent=0)
from collections import Counter
print('바꾼 곳', nfix, '확인할 곳', len(flags), Counter(f['why'] for f in flags))
