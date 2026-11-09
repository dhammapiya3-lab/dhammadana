"""원본 그림을 받아 글 상자를 찾는다.
python3 pipeline/fetch_ocr.py <책 slug> [--keep 이야기파일 ...]
결과: data/ocr/<책>/<이야기>.json  (--keep 으로 준 이야기는 원본 그림을 work/orig/ 에도 저장)"""
import json, os, sys, urllib.request, cv2, numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from boxes import detect

BASE = "https://dharma-storybooks.net/"
cat = json.load(open("data/catalog.json", encoding="utf-8"))


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dhammadana-korean-translation (CC BY-SA)"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            err = e
    raise err


def one(slug, sf, img, keep):
    url = BASE + slug + "/" + img
    cache = os.path.join("cache/orig", slug, img)
    if not os.path.exists(cache):
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        open(cache, "wb").write(get(url))
    if keep:
        k = os.path.join("work/orig", slug, img)
        os.makedirs(os.path.dirname(k), exist_ok=True)
        open(k, "wb").write(open(cache, "rb").read())
    im = cv2.imread(cache)
    return {"img": img, **detect(im)}


def main():
    slug = sys.argv[1]
    keep = set(sys.argv[sys.argv.index("--keep") + 1:]) if "--keep" in sys.argv else set()
    b = cat["books"][slug]
    for sf, st in b["stories"].items():
        out = f"data/ocr/{slug}/{sf.rsplit('.', 1)[0]}.json"
        if os.path.exists(out) and sf not in keep:
            continue
        imgs = [i["img"] for i in st["items"] if "img" in i]
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(lambda i: one(slug, sf, i, sf in keep), imgs))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        nb = sum(len(r["boxes"]) for r in res); nl = sum(len(r["loose"]) for r in res)
        print(f"{sf}: 그림 {len(res)} 상자 {nb} 상자밖글 {nl}", flush=True)


if __name__ == "__main__":
    main()
