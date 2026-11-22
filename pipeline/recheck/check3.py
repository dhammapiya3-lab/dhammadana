"""3회차 검수 묶음 검사 (한글 그림 storybooks-qa + 번역 파일 ko).
대비[대비] · 글자 크기[크기] · 줄바꿈[줄] · 표기[표기] · 빠진 내용[짧음]
python3 check3.py > /tmp/c3.tsv   (책 이야기 쪽 상자 종류 값 글)"""
import sys, json, glob, os, re
import numpy as np, cv2
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/claude/sb/pipeline')
import render

QA = '/home/claude/qa'
SKIP = {'Four-Rich-Men', 'Jatakamala', 'Light-of-Asia', 'Rasavahini', 'Way-Beyond'}
JANGNO = {'Foremost-Monks', 'Foremost-Nuns', 'Foremost-Laymen'}  # 장로/장로니 쓰는 책
BAD = ['사리불', '목건련', '목련존자', '가섭', '수보리', '부루나', '우바리', '아나율', '가전연', '교진여', '라후라', '정반왕', '마야부인',
       '급고독', '예류', '일래', '불환', '풋타', '푸트라', '카사파', '베살리', '바이샬리', '왕사성', '사위성', '사밧티', '코살라', '비사카']
dr = ImageDraw.Draw(Image.new('RGB', (10, 10)))


def lum(c):
    c = np.asarray(c, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


exec(open('/home/claude/tools/measure.py').read().split('rows = []')[0])

for book in sorted(os.listdir('/home/claude/sb/ko')):
    if book in SKIP: continue
    for f in sorted(glob.glob(f'/home/claude/sb/ko/{book}/*.json')):
        sid = os.path.basename(f)[:-5]
        pages = json.load(open(f))
        for i, p in enumerate(pages, 1):
            im = f'{QA}/{book}/{sid}/{i:02d}.jpg'
            img = cv2.imread(im) if os.path.exists(im) else None
            for k, b in enumerate(p['boxes']):
                ko = (b.get('ko') or '').strip()
                if not ko: continue
                out = lambda kind, val: print(book, sid, i, k + 1, kind, val, ko[:28].replace('\n', '/'), sep='\t', flush=True)
                # 표기
                for w in BAD:
                    if w in ko: out('표기', w)
                if book in JANGNO and '존자' in ko: out('표기', '존자(이 책은 장로)')
                if book not in JANGNO and re.search(r'장로(?!니)', ko) and book != 'Foremost-Laywomen': out('표기', '장로(이 책은 존자?)')
                # 빠진 내용
                en = b.get('en') or ''
                if len(en) >= 80 and len(re.sub(r'\s', '', ko)) / len(en) < 0.22: out('짧음', f'{len(re.sub(chr(92)+"s","",ko))}/{len(en)}')
                if img is None: continue
                H, W = img.shape[:2]
                # 상자 영역
                try:
                    if b.get('rect'):
                        x0, y0, x1, y1 = [round(v * W / 800) for v in b['rect']]
                        m = np.zeros((H, W), np.uint8)
                        if b.get('ellipse'): cv2.ellipse(m, ((x0 + x1) // 2, (y0 + y1) // 2), ((x1 - x0) // 2, (y1 - y0) // 2), 0, 0, 360, 1, -1)
                        else: m[max(0, y0):y1, max(0, x0):x1] = 1
                    elif b.get('seed'):
                        full, _ = render.region_masks(img, b['seed']); m = render.solid(full).astype(np.uint8)
                    else: continue
                except Exception:
                    continue
                if m.sum() < 300 or m.mean() > 0.35: continue
                inner = cv2.erode(m, np.ones((max(5, W // 120),) * 2, np.uint8)) > 0
                if inner.sum() < 200: continue
                g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                bg = np.median(g[inner]); dark = bg < 110
                tp = ((g > bg + 50) if dark else (g < bg - 50)) & inner
                # 대비: 글자가 거의 안 잡히거나(글자와 바탕이 비슷), 잡힌 글자의 명암비가 낮음
                px = img[inner][:, ::-1]
                L = lum(px); Lb = np.median(L)
                Lt = np.percentile(L, 97 if dark else 3)
                cr = (max(Lb, Lt) + 0.05) / (min(Lb, Lt) + 0.05)
                if cr < 3.0: out('대비', round(float(cr), 1))
                # 크기 (글줄 높이)
                ys, xs = np.where(inner)
                sub = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                h, n = measure(sub)
                if h and n >= 2 and h / 0.966 * 800 / W < 12: out('크기', round(h / 0.966 * 800 / W, 1))
                # 줄바꿈 (직접 정한 네모만: 같은 방법으로 줄을 나눠 봄)
                if b.get('rect') and '\n' not in ko:
                    x0, y0, x1, y1 = b['rect']; pad = 6
                    try:
                        fnt, lines, lh = render.fit(dr, ko, x1 - x0 - 2 * pad, y1 - y0 - 2 * pad, 17)
                    except Exception:
                        lines = []
                    if len(lines) >= 2:
                        last = lines[-1].strip()
                        if len(last.replace(' ', '')) <= 2 or (len(last) <= 4 and len(lines[-2]) >= 12):
                            out('줄', '/'.join(l.strip() for l in lines)[-40:])
