# 태국어 원서 쪽마다 줄 단위 글자 인식 (윗줄 성조 부호가 따로 떨어진 줄로 읽히지 않게, 부호 띠를 아래 줄에 붙여 줄마다 psm 7)
import sys, json, os, subprocess, numpy as np, fitz
from PIL import Image
d = fitz.open('src.pdf')
def page(i):
    out = f'ocrT/{i:03d}.json'
    if os.path.exists(out) and not os.environ.get('FORCE'): return
    pix = d[i].get_pixmap(dpi=300, colorspace=fitz.csGRAY)
    im = Image.frombytes('L', (pix.width, pix.height), pix.samples); a = np.array(im) < 128
    on = a.sum(1) > 2; H = len(on); b = []; k = 0
    while k < H:
        if on[k]:
            j = k
            while j < H and on[j]: j += 1
            b.append([k, j]); k = j
        else: k += 1
    # 두 글줄이 닿아 한 띠가 된 곳은 잉크가 가장 적은 줄에서 나눔
    rs = a.sum(1); b2 = []
    for s_, e_ in b:
        while e_ - s_ > 105:
            cut = s_ + 40 + int(np.argmin(rs[s_ + 40:e_ - 40])); b2.append([s_, cut]); s_ = cut + 1
        b2.append([s_, e_])
    b = b2
    # 작은 띠(윗줄 성조 부호·아랫줄 모음)는 가까운 큰 띠(글줄)에 붙임 — 큰 띠끼리는 합치지 않음
    isbig = lambda x: rs[x[0]:x[1]].max() > 80 or x[1] - x[0] >= 20   # 글자 몸통 줄(잉크가 많은 줄)이 있는 띠만 글줄
    big = [x for x in b if isbig(x)]
    m = [list(x) for x in big]
    for s_, e_ in b:
        if isbig([s_, e_]) or not m: continue
        dist = lambda q: (s_ - big[q][1]) if s_ >= big[q][1] else (big[q][0] - e_) if e_ <= big[q][0] else 0
        j = min(range(len(big)), key=lambda q: (abs(dist(q)), -q))   # 처음 글줄 자리로 거리 (같으면 아래 줄 — 윗 부호)
        if abs(dist(j)) < 25: m[j][0] = min(m[j][0], s_); m[j][1] = max(m[j][1], e_)
        else: m.append([s_, e_])
    m.sort()
    lines = []
    for s, e in m:
        cols = np.where(a[s:e].any(0))[0]
        if not len(cols): continue
        x0, x1 = int(cols[0]), int(cols[-1])
        tmp = f'/tmp/ocr_{os.getpid()}.png'
        im.crop((max(0, x0 - 20), max(0, s - 15), min(im.width, x1 + 20), min(H, e + 15))).save(tmp)
        r = subprocess.run(['tesseract', tmp, '-', '-l', 'tha', '--psm', '7', 'tsv'], capture_output=True, text=True, env={**os.environ, 'OMP_THREAD_LIMIT': '1'}).stdout
        ox = max(0, x0 - 20); segs = []
        for row in r.splitlines()[1:]:
            f = row.split('\t')
            if len(f) >= 12 and f[0] == '5' and f[11].strip(): segs.append([ox + int(f[6]), ox + int(f[6]) + int(f[8]), f[11]])
        lines.append({'y0': s, 'y1': e, 'x0': x0, 'x1': x1, 'segs': segs})
    json.dump({'pdf': i + 1, 'w': im.width, 'h': H, 'lines': lines}, open(out, 'w'), ensure_ascii=False)
for i in ([int(x) for x in sys.argv[1].split(',')] if ',' in sys.argv[1] else range(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))): page(i)
