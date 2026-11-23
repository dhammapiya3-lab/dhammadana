"""글상자에 자리가 넉넉한데 글씨가 작은 곳 찾기 (4회차 뒤 운영자 지적: 자따까 4번 12쪽).
seed 상자: 한글 그림에서 seed 점부터 바탕을 채워 상자 영역을 잡고, 그 안 글줄 높이를 잰다.
rect 상자: rect 안에서 잰다.
글자 크기(줄높이/0.966) < 14 이고, 글 덩어리 높이가 상자 높이의 55% 아래면 출력.
출력: 책 이야기 쪽 상자 크기 채움 글"""
import json, glob, os, sys
import numpy as np, cv2
QA = '/tmp/qa'
ONLY = set(sys.argv[1:])

def lines(g):
    med = float(np.median(g))
    fg = (g < med - 50) if med >= 110 else (g > med + 50)
    cols = fg.mean(0) > 0.6; rows = fg.mean(1) > 0.6
    fg[:, cols] = False; fg[rows, :] = False
    prof = fg.sum(1) >= max(2, fg.shape[1] * 0.004)
    runs = []; cur = 0; start = None; first = last = None
    for y, v in enumerate(prof):
        if v:
            if not cur: start = y
            cur += 1
        elif cur:
            if cur >= 5: runs.append(cur); first = start if first is None else first; last = y
            cur = 0
    if cur >= 5: runs.append(cur); first = start if first is None else first; last = len(prof)
    if not runs: return None, 0
    return float(np.median(runs)), (last - first)

for f in sorted(glob.glob('/home/claude/sb/ko/*/*.json')):
    book = f.split('/')[-2]; sid = os.path.basename(f)[:-5]
    if ONLY and book not in ONLY: continue
    for i, p in enumerate(json.load(open(f)), 1):
        im = f'{QA}/{book}/{sid}/{i:02d}.jpg'
        if not os.path.exists(im): continue
        a = cv2.imread(im); H, W = a.shape[:2]; s = W / 800
        g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
        for k, b in enumerate(p['boxes']):
            t = (b.get('ko') or '').strip()
            if len(t) < 12: continue
            if b.get('rect'):
                x0, y0, x1, y1 = [int(round(v * s)) for v in b['rect']]
            elif b.get('seed'):
                sd = b['seed'][0] if isinstance(b['seed'][0], (list, tuple)) else b['seed']
                sx, sy = [int(round(v * s)) for v in sd]
                if not (0 <= sx < W and 0 <= sy < H): continue
                blur = cv2.medianBlur(a, 5); m = np.zeros((H + 2, W + 2), np.uint8)
                cv2.floodFill(blur.copy(), m, (sx, sy), 0, (14,) * 3, (14,) * 3, cv2.FLOODFILL_MASK_ONLY | 8 | (255 << 8))
                m = m[1:-1, 1:-1]
                k5 = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
                ys, xs = np.nonzero(k5)
                if len(xs) < 100: continue
                x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
                if (x1 - x0) > 0.6 * W and (y1 - y0) > 0.6 * H:  # 바탕이 새어 상자를 못 잡음 → seed 둘레만 재고 'leak' 표시
                    x0, y0, x1, y1 = max(0, sx - int(40*s)), max(0, sy - int(22*s)), min(W, sx + int(440*s)), min(H, sy + int(60*s))
                    lh, block = lines(g[y0:y1, x0:x1])
                    if lh and lh / 0.966 / s < 15:
                        print(f'{book}\t{sid}\t{i}\t{k}\t{lh/0.966/s:.1f}\tleak\t{t[:30]}'.replace('\n', '/'))
                    continue
            else: continue
            crop = g[y0:y1, x0:x1]
            lh, block = lines(crop)
            if not lh: continue
            size = lh / 0.966 / s; fill = block / max(1, y1 - y0)
            if size < 14 and fill < 0.55 and (y1 - y0) / s > 40:
                print(f'{book}\t{sid}\t{i}\t{k}\t{size:.1f}\t{fill:.2f}\t{t[:30]}'.replace('\n', '/'))
