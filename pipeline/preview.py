"""원본 그림을 800px 로 줄여 review/<책>/<이야기>/NN.jpg 로 (번역할 때 보는 용도)
python3 pipeline/preview.py <책> [이야기파일 ...]"""
import json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from fetch_ocr import get, BASE
cat = json.load(open("data/catalog.json", encoding="utf-8"))
slug = sys.argv[1]; only = set(sys.argv[2:])
for sf, st in cat["books"][slug]["stories"].items():
    if only and sf not in only: continue
    sid = sf.rsplit(".", 1)[0]
    for n, it in enumerate([i for i in st["items"] if "img" in i], 1):
        c = os.path.join("cache/orig", slug, it["img"])
        try:
            if not os.path.exists(c):
                os.makedirs(os.path.dirname(c), exist_ok=True); open(c, "wb").write(get(BASE + slug + "/" + it["img"]))
            try:
                im = Image.open(c).convert("RGB")
            except Exception:
                open(c, "wb").write(get(BASE + slug + "/" + it["img"]))
                im = Image.open(c).convert("RGB")
        except Exception as e:
            # 한 장을 못 받아도 다른 책·이야기 미리보기는 계속 만든다
            print("그림을 못 받음:", it["img"], e, flush=True); continue
        im = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
        o = f"review/{slug}/{sid}/{n:02d}.jpg"; os.makedirs(os.path.dirname(o), exist_ok=True); im.save(o, quality=80)
    print(sid, flush=True)
