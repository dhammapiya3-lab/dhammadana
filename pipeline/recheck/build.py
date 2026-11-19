"""번역 파일 만들기 + 800px 미리보기
T = {그림번호: [찾은 상자 순서대로 한국어 (None=그 상자는 건너뜀), 그리고 추가 상자 {'seed':[x,y]} 또는 {'seeds':[[..]..]} + 'ko'] }"""
import json, os, sys, glob
sys.path.insert(0, '/home/claude/sb/pipeline')
from render import render

def build(sid, T, book='Jataka', preview=True):
    ocr = json.load(open(f'/home/claude/sb/data/ocr/{book}/{sid}.json'))
    pages = []
    for n, p in enumerate(ocr, 1):
        items = T.get(n, [None]*len(p['boxes']))
        from auto import resolve
        items = resolve(f'/home/claude/rev/{book}/{sid}/{n:02d}.jpg', items)
        det = [x for x in items if not isinstance(x, dict)]
        extra = [x for x in items if isinstance(x, dict)]
        assert len(det) == len(p['boxes']), (sid, n, len(det), len(p['boxes']))
        boxes = []
        for b, k in zip(p['boxes'], det):
            if k: boxes.append({'seed': b['seed'], 'shape': b['shape'], 'en': b['en'], 'ko': k, 'align': 'center'})
        for e in extra:
            e = dict(e); e.setdefault('shape', 'box'); e.setdefault('align', 'center'); e['manual'] = True
            if 'seeds' in e: e['seed'] = e.pop('seeds')
            boxes.append(e)
        pages.append({'img': p['img'], 'boxes': boxes})
    os.makedirs(f'/home/claude/sb/ko/{book}', exist_ok=True)
    json.dump(pages, open(f'/home/claude/sb/ko/{book}/{sid}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if preview:
        out = f'/tmp/pv/{sid}'; os.makedirs(out, exist_ok=True)
        import numpy as np
        from PIL import Image
        ims = []
        for n, pg in enumerate(pages, 1):
            im = render(f'/home/claude/rev/{book}/{sid}/{n:02d}.jpg', pg['boxes'])
            ims.append(im.resize((800, round(im.height * 800 / im.width))))
        for i in range(0, len(ims), 2):
            pair = ims[i:i + 2]; H = sum(x.height for x in pair) + 8 * (len(pair) - 1)
            sh = Image.new('RGB', (800, H), 'white'); y = 0
            for x in pair: sh.paste(x, (0, y)); y += x.height + 8
            sh.save(f'{out}/{i // 2 + 1:02d}.jpg', quality=80)
    return len(pages)
