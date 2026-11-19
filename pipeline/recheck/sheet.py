"""이야기 하나의 확인용 화면: 찾은 상자에 번호(초록), 상자 밖 글자 위치(빨강 점)"""
import sys, json, glob, os
sys.path.insert(0, '/home/claude/sb/pipeline')
import cv2, numpy as np
from boxes import flood
sid = sys.argv[1]; book = sys.argv[2] if len(sys.argv) > 2 else 'Jataka'
ocr = json.load(open(f'/home/claude/sb/data/ocr/{book}/{sid}.json'))
out = f'/tmp/sh/{sid}'; os.makedirs(out, exist_ok=True)
for f in glob.glob(out + '/*'): os.remove(f)
ims = []
for n, p in enumerate(ocr, 1):
    im = cv2.imread(f'/home/claude/rev/{book}/{sid}/{n:02d}.jpg')
    vis = im.copy()
    for j, b in enumerate(p['boxes'], 1):
        fl, full = flood(im, b['seed'])
        cs, _ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cs, -1, (0, 200, 0), 2)
        x, y = b['seed']; cv2.circle(vis, (x, y), 9, (0, 160, 0), -1)
        cv2.putText(vis, str(j), (x - 5, y + 5), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1)
    cv2.putText(vis, f'#{n}', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
    ims.append(vis)
for i in range(0, len(ims), 2):
    pair = ims[i:i + 2]
    sheet = np.vstack([np.vstack([a, np.full((8, 800, 3), 255, np.uint8)]) for a in pair])
    cv2.imwrite(f'{out}/{i // 2 + 1:02d}.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
for n, p in enumerate(ocr, 1):
    for j, b in enumerate(p['boxes'], 1): print(f'{n}.{j} {b["en"]}')
    if p['loose']: print(f'{n}.loose', ' '.join(p['loose'])[:160])
