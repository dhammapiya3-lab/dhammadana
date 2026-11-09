"""원 사이트 그림(원본·표지)의 파일 정보(크기·ETag·수정 날짜)를 모은다 — 다시 만든 그림 찾기용.
그림 자체는 받지 않고 HEAD 요청만 한다.
python3 pipeline/assets_meta.py  → data/assets_meta.json
"""
import json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://dharma-storybooks.net/"
UA = "dhammadana-korean-translation (CC BY-SA)"
cat = json.load(open("data/catalog.json", encoding="utf-8"))

urls = []
for slug, b in cat["books"].items():
    if b.get("cover"):
        urls.append(f"{slug}/{b['cover']}")
    for st in b["stories"].values():
        urls += [f"{slug}/{i['img']}" for i in st["items"] if "img" in i]


def head(u):
    req = urllib.request.Request(BASE + u, method="HEAD", headers={"User-Agent": UA})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                h = r.headers
                return u, [h.get("Content-Length"), h.get("ETag"), h.get("Last-Modified")]
        except Exception as e:
            err = str(e)
    return u, ["error", err, None]


with ThreadPoolExecutor(12) as ex:
    meta = dict(ex.map(head, urls))
json.dump(meta, open("data/assets_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
print("그림 파일 정보", len(meta), "개, 오류", sum(1 for v in meta.values() if v[0] == "error"))
