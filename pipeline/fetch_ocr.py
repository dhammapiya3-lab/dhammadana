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
    def ok(path):
        try:
            return open(path, "rb").read(3) == b"\xff\xd8\xff" or cv2.imread(path) is not None
        except OSError:
            return False
    if not os.path.exists(cache) or not ok(cache):
        # 보관함에 깨진 파일(그림이 아닌 것)이 있으면 다시 받는다
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        data = get(url)
        open(cache, "wb").write(data)
        if not ok(cache):
            print(f"그림이 아님: {url} ({len(data)}바이트, 앞부분 {data[:60]!r})", flush=True)
    if keep:
        k = os.path.join("work/orig", slug, img)
        os.makedirs(os.path.dirname(k), exist_ok=True)
        open(k, "wb").write(open(cache, "rb").read())
    im = cv2.imread(cache)
    if im is None:
        return {"img": img, "boxes": [], "loose": [], "bad": True}
    return {"img": img, **detect(im)}


def main():
    slug = sys.argv[1]
    keep = set(sys.argv[sys.argv.index("--keep") + 1:]) if "--keep" in sys.argv else set()
    only = set(sys.argv[sys.argv.index("--only") + 1:]) if "--only" in sys.argv else set()
    b = cat["books"][slug]
    for sf, st in b["stories"].items():
        if keep and sf not in keep:
            continue
        if only and sf not in only:
            continue
        out = f"data/ocr/{slug}/{sf.rsplit('.', 1)[0]}.json"
        if os.path.exists(out) and sf not in keep and not os.environ.get("REDO"):
            continue
        imgs = [i["img"] for i in st["items"] if "img" in i]
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(lambda i: one(slug, sf, i, sf in keep), imgs))
        bad = sum(1 for r in res if r.get("bad"))
        if bad:
            # 그림을 못 받은 이야기는 저장하지 않고 다음 작업 때 다시 받는다. 원 사이트의 실제 그림 주소를 보여 줌(진단용)
            import re
            try:
                page = get(BASE + slug + "/" + sf).decode("utf-8", "replace")
                srcs = re.findall(r'(?:src|href)="([^"]+\.(?:jpe?g|png|webp))"', page)[:4]
            except Exception as e:
                srcs = [f"이야기 쪽도 못 받음: {e}"]
            print(f"{sf}: 그림 {len(res)}장 중 {bad}장 못 받음 — 저장 안 함. 원 사이트 그림 주소 예: {srcs}", flush=True)
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        nb = sum(len(r["boxes"]) for r in res); nl = sum(len(r["loose"]) for r in res)
        print(f"{sf}: 그림 {len(res)} 상자 {nb} 상자밖글 {nl}", flush=True)


if __name__ == "__main__":
    main()
