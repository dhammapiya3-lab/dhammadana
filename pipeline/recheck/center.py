"""3회차 새 검사: 글 덩어리가 상자(말풍선) 가운데에서 많이 벗어난 곳 찾기 — 한글 그림(storybooks-qa)에서.
상자 영역: rect 가 있으면 그 네모, 없으면 seed 로 한글 그림에서 영역을 다시 찾음(구멍 메움).
글 덩어리: 영역 안에서 바탕보다 뚜렷이 어둡거나(밝은 상자) 밝은(어두운 상자) 픽셀의 범위.
위·아래 빈칸 차이가 영역 높이의 25% 이상이고 18px 이상이면 [위아래], 가운데 맞춤 글의 왼쪽·오른쪽 차이가 너비의 25% 이상이고 30px 이상이면 [좌우].
출력: 책 이야기 쪽 상자 종류 위 아래 왼 오 글"""
import sys, json, glob, os
import numpy as np, cv2
sys.path.insert(0, '/home/claude/sb/pipeline')
import render

QA = '/home/claude/qa'
books = sys.argv[1:] or sorted(os.listdir('/home/claude/sb/ko'))
for book in books:
    for f in sorted(glob.glob(f'/home/claude/sb/ko/{book}/*.json')):
        sid = os.path.basename(f)[:-5]
        for i, p in enumerate(json.load(open(f)), 1):
            im = f'{QA}/{book}/{sid}/{i:02d}.jpg'
            if not os.path.exists(im): continue
            img = cv2.imread(im); H, W = img.shape[:2]; g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            for k, b in enumerate(p['boxes']):
                if not (b.get('ko') or '').strip(): continue
                try:
                    if b.get('rect'):
                        kk = W / 800; x0, y0, x1, y1 = [round(v * kk) for v in b['rect']]
                        m = np.zeros((H, W), np.uint8)
                        if b.get('ellipse'): cv2.ellipse(m, ((x0 + x1) // 2, (y0 + y1) // 2), ((x1 - x0) // 2, (y1 - y0) // 2), 0, 0, 360, 1, -1)
                        else: m[y0:y1, x0:x1] = 1
                    elif b.get('seed'):
                        kk = W / 800; sx, sy = [round(v * kk) for v in b['seed']]
                        full, _ = render.region_masks(img, [sx, sy] if False else b['seed'])
                        m = render.solid(full).astype(np.uint8)
                    else:
                        continue
                except Exception:
                    continue
                if m.sum() < 300 or m.mean() > 0.35: continue
                inner = cv2.erode(m, np.ones((max(5, W // 120),) * 2, np.uint8))
                if inner.sum() < 200: continue
                # 본체만: 너비(높이)가 가장 넓은 줄의 60% 이상인 줄·칸 (꼬리·아래 딱지 빼기)
                rs, cs = inner.sum(1), inner.sum(0)
                ry, cx = np.where(rs >= 0.6 * rs.max())[0], np.where(cs >= 0.6 * cs.max())[0]
                Y0, Y1, X0, X1 = ry.min(), ry.max(), cx.min(), cx.max()
                bg = np.median(g[inner > 0])
                dark = bg < 110
                tp = ((g > bg + 60) if dark else (g < bg - 60)) & (inner > 0)
                ty, tx = np.where(tp)
                if len(tx) < 30: continue
                # 띄엄띄엄한 점(무늬)은 빼고 글 덩어리 범위: 5~95 백분위
                t0, t1 = np.percentile(ty, 1), np.percentile(ty, 99)
                l0, l1 = np.percentile(tx, 1), np.percentile(tx, 99)
                top, bot = t0 - Y0, Y1 - t1
                lef, rig = l0 - X0, X1 - l1
                hh, ww = Y1 - Y0, X1 - X0
                flag = []
                if abs(top - bot) > max(6 * W / 800, 0.22 * hh) and min(top, bot) >= 0: flag.append('위아래')
                if b.get('align', 'left' if b.get('shape') == 'box' else 'center') == 'center' and abs(lef - rig) > max(30 * W / 800, 0.25 * ww) and min(lef, rig) >= 0: flag.append('좌우')
                if flag:
                    s = 800 / W
                    print(book, sid, i, k + 1, '+'.join(flag), int(top * s), int(bot * s), int(lef * s), int(rig * s), b['ko'][:24].replace('\n', '/'), sep='\t', flush=True)
