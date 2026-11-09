"""dharma-storybooks.net 의 HTML 페이지를 모두 받아 mirror/ 에 저장한다.
그림·PDF 는 받지 않고 주소 목록(mirror/_assets.txt)만 남긴다."""
import os, re, time, urllib.request, urllib.parse
from html.parser import HTMLParser

BASE = "https://dharma-storybooks.net/"
OUT = "mirror"
UA = "dhammadana-korean-translation (CC BY-SA)"


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.links.append(v)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def local_path(url):
    p = urllib.parse.urlparse(url).path
    if p.endswith("/") or p == "":
        p += "index.htm"
    return os.path.join(OUT, p.lstrip("/"))


def main():
    seen, queue, assets = set(), [BASE], set()
    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            data = get(url)
        except Exception as e:
            print("FAIL", url, e); continue
        lp = local_path(url)
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        open(lp, "wb").write(data)
        p = Links(); p.feed(data.decode("utf-8", "replace"))
        for l in p.links:
            u = urllib.parse.urljoin(url, l).split("#")[0]
            if not u.startswith(BASE):
                continue
            path = urllib.parse.urlparse(u).path.lower()
            if path.endswith((".htm", ".html", "/")):
                if u not in seen:
                    queue.append(u)
            else:
                assets.add(u)
        print(len(seen), url, flush=True)
        time.sleep(0.15)
    open(os.path.join(OUT, "_assets.txt"), "w").write("\n".join(sorted(assets)) + "\n")
    print("pages", len(seen), "assets", len(assets))


if __name__ == "__main__":
    main()
