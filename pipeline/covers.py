"""책 표지 46장을 받아 covers/<책>.jpg (가로 960px) 로 저장"""
import json, os, io, urllib.request
from PIL import Image
cat = json.load(open("data/catalog.json", encoding="utf-8"))
os.makedirs("covers", exist_ok=True)
for slug, b in cat["books"].items():
    if not b.get("cover") or os.path.exists(f"covers/{slug}.jpg"):
        continue
    req = urllib.request.Request(f"https://dharma-storybooks.net/{slug}/{b['cover']}", headers={"User-Agent": "dhammadana-korean-translation (CC BY-SA)"})
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=120).read())).convert("RGB")
    except Exception as e:
        print("표지 실패", slug, e); continue
    if im.width > 960:
        im = im.resize((960, round(im.height * 960 / im.width)), Image.LANCZOS)
    im.save(f"covers/{slug}.jpg", "JPEG", quality=86, optimize=True, progressive=True)
    print("표지", slug, im.size)
