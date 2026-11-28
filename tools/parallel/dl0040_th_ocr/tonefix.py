# 윗모음(ั ิ ี ึ ื) 위에 얹힌 성조 부호 바로잡기: 글자 인식이 'ดั้ง'을 'ดัง'으로, 'ลั่น'을 'ลั้น'으로 읽는 버릇 —
#   줄 그림에서 윗모음 위에 한 층 더 얹힌 부호를 찾아 모양(고리 있음 = ้, 짧은 세로 획 = ่, 십자 = ๋)으로 가리고,
#   줄 글에서 가로 자리가 가장 가까운 윗모음 뒤의 성조 부호를 그 꼴로 맞추거나(없으면 넣음)
import json, re, sys, os, numpy as np, fitz
from PIL import Image
from scipy import ndimage
d = fitz.open('src.pdf')
UPV = 'ัิีึื'; TONES = '่้๊๋'
def comps_of(a):
    lab, n = ndimage.label(a); out = []
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        m = lab[sl] == k
        hole = (ndimage.binary_fill_holes(m) & ~m).sum()
        out.append(dict(y0=sl[0].start, y1=sl[0].stop, x0=sl[1].start, x1=sl[1].stop, hole=int(hole), area=int(m.sum()), m=m))
    return out
def kind(c):
    h, w = c['y1'] - c['y0'], c['x1'] - c['x0']
    if c['hole'] >= 3: return '้'
    if w <= 7 and h >= 7: return '่'
    if w >= 9 and h >= 9: return '๋'
    return '?'
def stacked(a, xtop):
    up = a[:xtop - 1]; C = comps_of(up)
    first = [c for c in C if c['y1'] >= xtop - 14 and c['x1'] - c['x0'] >= 9]   # 몸통 바로 위 첫 층(윗모음 등)
    res = []
    for c in C:
        if c in first: continue
        under = [f for f in first if f['y0'] >= c['y1'] - 3 and f['x0'] - 4 < (c['x0'] + c['x1']) / 2 < f['x1'] + 4]
        if under: res.append(((c['x0'] + c['x1']) / 2, kind(c), c))
    return res
def fix_page(i, D):
    pix = d[i].get_pixmap(dpi=300, colorspace=fitz.csGRAY)
    im = np.array(Image.frombytes('L', (pix.width, pix.height), pix.samples)) < 128
    ch = []
    for l in D['lines']:
        if not (250 < l['y0'] < 2990) or l['y1'] - l['y0'] < 28: continue
        t = l['t']; a = im[l['y0']:l['y1'], :]
        rows = a.sum(1); body = np.where(rows > rows.max() * .45)[0]
        if not len(body): continue
        st = [s for s in stacked(a, body[0]) if s[1] != '?']
        if not st: continue
        base = [k for k, c in enumerate(t) if not ('ั' <= c <= 'ฺ' or '็' <= c <= '๎')]
        def xof(k): j = sum(1 for b in base if b < k); return l['x0'] + (l['x1'] - l['x0']) * (j - .5) / max(1, len(base))
        slots = [k for k, c in enumerate(t) if c in UPV]   # 윗모음 자리 (그 뒤가 성조 자리)
        nt = list(t); used = set()
        for x, kd, _ in sorted(st, key=lambda s: s[0]):
            cand = [k for k in slots if k not in used]
            if not cand: break
            k = min(cand, key=lambda k: abs(xof(k) - x))
            if abs(xof(k) - x) > 45: continue
            used.add(k)
            nxt = nt[k + 1] if k + 1 < len(nt) else ''
            if nxt and nxt in TONES:
                if nxt != kd: nt[k + 1] = kd
            else: nt[k] = nt[k] + kd
        nt = ''.join(nt)
        if nt != t: ch.append((i + 1, l['y0'], t, nt)); l['t'] = nt
    return ch
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True); allc = []
    pages = range(287) if len(sys.argv) < 4 else [int(x) for x in sys.argv[3].split(',')]
    for i in pages:
        D = json.load(open(f'{src}/{i:03d}.json')); allc += fix_page(i, D)
        json.dump(D, open(f'{dst}/{i:03d}.json', 'w'), ensure_ascii=False)
    json.dump(allc, open('tonefix.json', 'w'), ensure_ascii=False, indent=0)
    print('바꾼 줄', len(allc))
