"""mirror/ 의 HTML 을 읽어 data/catalog.json (홈·책·이야기 구조) 을 만든다."""
import json, os, re, html
from html.parser import HTMLParser

M = "mirror"


def clean(t):
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*", "\n", t)).strip()


def by_id(s, i):
    m = re.search(r'<(\w+)[^>]*id="%s"[^>]*>(.*?)</\1>' % i, s, re.S)
    return clean(m.group(2)) if m else ""


class Seq(HTMLParser):
    """문서 순서대로 (소제목 | 링크 | 그림) 이벤트를 모은다"""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ev, self.cls_stack, self.cur, self.href = [], [], None, None
    def handle_starttag(self, tag, a):
        a = dict(a)
        c = a.get("class", "") or ""
        if re.search(r"\bHeading[2-5]\b", c) and a.get("id") not in ("title", "art-style"):
            self.cur = ["h", c.split()[0], ""]
        if tag == "a" and a.get("href"):
            self.href = [a["href"], ""]
        if tag == "img" and a.get("src"):
            self.ev.append(["img", a["src"], a.get("alt", "")])
    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            self.ev.append(["a", self.href[0], self.href[1].strip()]); self.href = None
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "td", "th") and self.cur:
            if self.cur[2].strip():
                self.ev.append(["h", self.cur[1], re.sub(r"\s+", " ", self.cur[2]).strip()])
            self.cur = None
    def handle_data(self, d):
        if self.cur is not None: self.cur[2] += d
        if self.href is not None: self.href[1] += d


def home():
    s = open(f"{M}/index.htm", encoding="utf-8").read()
    body = s[s.find('id="StorybooksTable"'):]
    cats, cur = [], None
    for row in re.findall(r"<tr>(.*?)</tr>", body, re.S):
        h = re.search(r'class="Heading3">(.*?)</p>', row)
        if h:
            cur = {"name": clean(h.group(1)), "books": []}; cats.append(cur); continue
        a = re.search(r'<a href="([^"]+)/index.htm">(.*?)</a>(.*?)</p>', row, re.S)
        if not a: continue
        rest = re.sub(r'<span class="tag">.*?</span>', "", a.group(3), flags=re.S)
        lines = [l for l in clean(rest).split("\n") if l.strip()]
        cur["books"].append({
            "slug": a.group(1), "title": clean(a.group(2)),
            "lines": lines,
            "tags": [clean(t) for t in re.findall(r'<span class="tag">(.*?)</span>', row)],
        })
    return cats


def book(slug):
    s = open(f"{M}/{slug}/index.htm", encoding="utf-8").read()
    b = {"slug": slug, "title": by_id(s, "title"), "style": by_id(s, "art-style"),
         "summary": by_id(s, "summary"), "intro": by_id(s, "intro"),
         "keywords": (re.search(r'name="keywords" content="([^"]*)"', s) or [None, ""])[1]}
    cov = re.search(r'<img src="([^"]+)"[^>]*id="cover"', s)
    b["cover"] = cov.group(1) if cov else None
    p = Seq(); p.feed(s[s.find('id="intro"'):] if 'id="intro"' in s else s)
    toc, seen = [], set()
    for e in p.ev:
        if e[0] == "h":
            toc.append({"h": e[2], "level": e[1]})
        elif e[0] == "a":
            href = e[1]
            if href.startswith(("http", "../", "#")) or href in seen: continue
            if href.lower().endswith(".pdf"):
                toc.append({"pdf": href, "label": e[2]}); seen.add(href)
            elif href.lower().endswith((".htm", ".html")) and os.path.exists(f"{M}/{slug}/{href}"):
                toc.append({"story": href, "label": e[2]}); seen.add(href)
    b["toc"] = toc
    return b


def story(slug, f):
    s = open(f"{M}/{slug}/{f}", encoding="utf-8").read()
    st = {"file": f, "title": by_id(s, "title"), "summary": by_id(s, "summary"),
          "intro": by_id(s, "intro")}
    p = Seq(); p.feed(s)
    items = []
    for e in p.ev:
        if e[0] == "h":
            items.append({"h": e[2]})
        elif e[0] == "a" and re.search(r"-Original\.(jpe?g|png)$", e[1], re.I):
            items.append({"img": e[1]})
    st["items"] = items
    # 이야기 밖 정보(등장인물·키워드 등) — information 칸
    info = re.findall(r'class="information"[^>]*>(.*?)</div>', s, re.S)
    if info: st["info"] = [clean(x) for x in info]
    return st


def main():
    cats = home()
    out = {"home": {"title": "Dharma Storybooks", "summary": by_id(open(f"{M}/index.htm", encoding="utf-8").read(), "summary")},
           "categories": cats, "books": {}}
    n_img = 0
    for c in cats:
        for bk in c["books"]:
            b = book(bk["slug"])
            b["stories"] = {}
            for t in b["toc"]:
                if "story" in t:
                    st = story(bk["slug"], t["story"])
                    n_img += sum(1 for i in st["items"] if "img" in i)
                    b["stories"][t["story"]] = st
            out["books"][bk["slug"]] = b
    os.makedirs("data", exist_ok=True)
    json.dump(out, open("data/catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("books", len(out["books"]), "stories", sum(len(b["stories"]) for b in out["books"].values()), "images", n_img)


if __name__ == "__main__":
    main()
