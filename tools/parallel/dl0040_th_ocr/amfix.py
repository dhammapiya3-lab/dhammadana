# 성조 부호 + ำ 바로잡기: 글자 인식이 '้ำ'을 '้า'로 읽는 버릇 — 줄 그림에서 니칼힛(작은 동그라미) 위에 성조 부호가 얹힌 곳을 세어,
#   그만큼 줄 글의 '◌่า/◌้า/◌๊า/◌๋า' 가운데 가로 자리가 가장 가까운 것을 '◌่ำ' 꼴로 바꿈
import json, re, sys, os, numpy as np, fitz
from PIL import Image
from scipy import ndimage
d = fitz.open('src.pdf')
def rings(a, xtop):
    # a: 줄 그림(참/거짓), xtop: 글자 몸통 위쪽 줄
    up = a[:xtop - 1]
    lab, n = ndimage.label(up)
    objs = ndimage.find_objects(lab)
    comps = []
    for k, sl in enumerate(objs, 1):
        m = lab[sl] == k; h, w = m.shape
        hole = (ndimage.binary_fill_holes(m) & ~m).sum()
        comps.append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop, hole, m.sum()))
    out = []
    for y0, y1, x0, x1, hole, area in comps:
        h, w = y1 - y0, x1 - x0
        if not (5 <= w <= 12 and 5 <= h <= 12 and hole >= 3 and .6 <= h / w <= 1.6): continue
        if y1 < xtop - 8: continue   # 몸통 바로 위에 붙은 동그라미만 (높이 뜬 부호의 고리는 뺌)
        above = [c for c in comps if c[1] <= y0 + 2 and c[2] < x1 + 3 and c[3] > x0 - 3 and c[:4] != (y0, y1, x0, x1)]
        if above: out.append((x0 + x1) / 2)
    return out
TONE_A = re.compile('[่้๊๋]า'); TONE_AM = re.compile('[่้๊๋]ำ')
def fix_page(i, D):
    pix = d[i].get_pixmap(dpi=300, colorspace=fitz.csGRAY)
    im = np.array(Image.frombytes('L', (pix.width, pix.height), pix.samples)) < 128
    changes = []
    for l in D['lines']:
        t = l['t']
        if not (250 < l['y0'] < 2990) or l['y1'] - l['y0'] < 28 or not re.search('[่้๊๋][าำ]', t): continue
        a = im[l['y0']:l['y1'], :]
        rows = a.sum(1); body = np.where(rows > rows.max() * .45)[0]
        if not len(body): continue
        xtop = body[0]
        rx = rings(a, xtop)
        need = len(rx) - len(TONE_AM.findall(t))
        if need <= 0: continue
        # 글자 자리 → 가로 자리 (기본 글자 수 비율로)
        base = [k for k, ch in enumerate(t) if not ('ั' <= ch <= 'ฺ' or '็' <= ch <= '๎')]
        nb = len(base)
        def xof(k): j = sum(1 for b in base if b < k); return l['x0'] + (l['x1'] - l['x0']) * j / max(1, nb)
        cands = [m.start() for m in TONE_A.finditer(t)]
        used = set()
        for r in sorted(rx):
            if not cands: break
            k = min((c for c in cands if c not in used), key=lambda c: abs(xof(c) - r), default=None)
            if k is None or abs(xof(k) - r) > 120: continue
            if any(abs(r - (xof(c2))) < 1 for c2 in []): pass
            used.add(k)
        # 이미 ำ 인 자리와 가까운 동그라미는 빼야 하지만, 개수만큼만 바꾸므로 가장 가까운 것부터
        sc = sorted(used, key=lambda k: min(abs(xof(k) - r) for r in rx))[:need]
        nt = list(t)
        for k in sc: nt[k + 1] = 'ำ'
        nt = ''.join(nt)
        if nt != t: changes.append((i + 1, l['y0'], t, nt)); l['t'] = nt
    return changes
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True); allc = []
    for i in range(287):
        D = json.load(open(f'{src}/{i:03d}.json'))
        allc += fix_page(i, D)
        json.dump(D, open(f'{dst}/{i:03d}.json', 'w'), ensure_ascii=False)
    json.dump(allc, open('amfix.json', 'w'), ensure_ascii=False, indent=0)
    print('바꾼 줄', len(allc))
