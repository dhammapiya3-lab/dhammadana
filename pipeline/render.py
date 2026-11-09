"""번역문(ko/<책>/<이야기>.json)으로 한글 그림을 만든다.
python3 pipeline/render.py <책> <이야기id> [--src 원본폴더] [--out 출력폴더]
ko 파일 형식: [{"img": "images/...-01-Original.jpg", "boxes": [{"seed":[x,y], "ko":"...", "align":"left|center"}]}]
출력: <out>/<책>/<이야기id>/big/01.jpg (원본 크기), s/01.jpg (800px)
"""
import cv2, numpy as np, json, os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from boxes import region_masks

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "GowunDodum-Regular.ttf")
INK = (40, 30, 25)


def inner_rect(full, tb):
    x0, y0, x1, y1 = tb
    m = max(3, full.shape[1] // 300)
    er = cv2.erode(full, np.ones((m, m), np.uint8))
    def ok(a, b, c, d):
        return a >= 0 and b >= 0 and c <= er.shape[1] and d <= er.shape[0] and er[b:d, a:c].size and er[b:d, a:c].min() == 255
    changed = True
    while changed:
        changed = False
        for d in [(-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]:
            n = (x0 + d[0], y0 + d[1], x1 + d[2], y1 + d[3])
            if ok(*n):
                x0, y0, x1, y1 = n; changed = True
    return x0, y0, x1, y1


def wrap(draw, text, font, maxw):
    out = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            t = (cur + " " + word).strip()
            if draw.textlength(t, font=font) <= maxw or not cur:
                cur = t
            else:
                out.append(cur); cur = word
        out.append(cur)
    return out


def fit(draw, text, w, h, maxsize):
    for size in range(maxsize, 9, -1):
        f = ImageFont.truetype(FONT, size)
        lines = wrap(draw, text, f, w)
        lh = size * 1.25
        if all(draw.textlength(l, font=f) <= w for l in lines) and lh * len(lines) <= h:
            return f, lines, lh
    f = ImageFont.truetype(FONT, 10)
    return f, wrap(draw, text, f, w), 13


def render(src_path, boxes):
    img = cv2.imread(src_path)
    H, W = img.shape[:2]
    out = img.copy()
    layout = []
    for b in boxes:
        if not b.get("ko"):
            continue
        full, inner = region_masks(img, b["seed"])
        # 상자 안쪽에서 바탕보다 뚜렷이 어두운 픽셀 = 글자
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bg = np.median(g[inner > 0])
        text_px = ((g < bg - 35) & (inner > 0)).astype(np.uint8) * 255
        ys, xs = np.where(text_px > 0)
        if len(xs) == 0:
            continue
        tb = (xs.min(), ys.min(), xs.max(), ys.max())
        k = max(3, W // 400)
        out = cv2.inpaint(out, cv2.dilate(text_px, np.ones((k, k), np.uint8), iterations=2), max(3, W // 300), cv2.INPAINT_TELEA)
        full = inner
        layout.append((inner_rect(full, tb), b["ko"], b.get("align", "left" if b.get("shape") == "box" else "center")))
    scale = 2 if W < 1600 else 1
    pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    if scale > 1:
        pil = pil.resize((W * scale, H * scale), Image.LANCZOS)
    d = ImageDraw.Draw(pil)
    for (x0, y0, x1, y1), ko, align in layout:
        pad = max(2, W // 500)
        X0, Y0, X1, Y1 = [v * scale for v in (x0 + pad, y0 + pad, x1 - pad, y1 - pad)]
        f, lines, lh = fit(d, ko, X1 - X0, Y1 - Y0, int(W * scale / 24))
        y = Y0 + ((Y1 - Y0) - lh * len(lines)) / 2
        for l in lines:
            lw = d.textlength(l, font=f)
            x = X0 if align == "left" else X0 + ((X1 - X0) - lw) / 2
            d.text((x, y), l, font=f, fill=INK)
            y += lh
    return pil


def main():
    slug, story = sys.argv[1], sys.argv[2]
    src = sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "cache/orig"
    outd = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "out/img"
    pages = json.load(open(f"ko/{slug}/{story}.json", encoding="utf-8"))
    for i, p in enumerate(pages, 1):
        im = render(os.path.join(src, slug, p["img"]), p.get("boxes", []))
        # 큰 그림: 원본과 같은 크기·JPEG 고화질 / 미리보기: 800px (원 사이트와 같게)
        W0 = Image.open(os.path.join(src, slug, p["img"])).width
        for sub, w, q in (("big", W0, 92), ("s", 800, 85)):
            o = os.path.join(outd, slug, story, sub, f"{i:02d}.jpg")
            os.makedirs(os.path.dirname(o), exist_ok=True)
            im.convert("RGB").resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(o, "JPEG", quality=q, optimize=True, progressive=True)
    print(slug, story, len(pages), "장")


if __name__ == "__main__":
    main()
