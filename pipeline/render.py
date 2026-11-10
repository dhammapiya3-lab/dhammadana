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
LATIN = os.path.join(HERE, "fonts", "Inter-Italic.otf")  # 한글 없는 로마자 줄(빠알리 원문 ā ṃ ñ …)은 원작처럼 기울임 글꼴로
import re as _re


def is_latin(t):
    return bool(_re.search(r"[A-Za-zĀ-ỿ]", t)) and not _re.search(r"[가-힣]", t)


class Fonts:
    def __init__(self, size):
        self.size = size
        self.ko = ImageFont.truetype(FONT, size)
        self.la = ImageFont.truetype(LATIN, max(9, round(size * 0.92)))

    def pick(self, t):
        return self.la if is_latin(t) else self.ko
INK = (40, 30, 25)


def inner_rect(full, tb):
    x0, y0, x1, y1 = tb
    m = max(3, full.shape[1] // 300)
    er = cv2.erode(full, np.ones((m, m), np.uint8))
    def ok(a, b, c, d):
        return a >= 0 and b >= 0 and c <= er.shape[1] and d <= er.shape[0] and er[b:d, a:c].size and er[b:d, a:c].min() == 255
    # 영어 글이 있던 자리에서 너무 멀리 벗어나지 않게 (꼬리·틈으로 새는 것 막기)
    th, tw = y1 - y0, x1 - x0
    lim = (x0 - max(8, tw * .12), y0 - max(8, th * .45), x1 + max(8, tw * .12), y1 + max(8, th * .45))
    changed = True
    while changed:
        changed = False
        for d in [(-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]:
            n = (x0 + d[0], y0 + d[1], x1 + d[2], y1 + d[3])
            if n[0] >= lim[0] and n[1] >= lim[1] and n[2] <= lim[2] and n[3] <= lim[3] and ok(*n):
                x0, y0, x1, y1 = n; changed = True
    return x0, y0, x1, y1


def wrap(draw, text, fonts, maxw):
    out = []
    for para in text.split("\n"):
        font = fonts.pick(para)
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
        f = Fonts(size)
        lines = wrap(draw, text, f, w)
        lh = size * 1.25
        if all(draw.textlength(l, font=f.pick(l)) <= w for l in lines) and lh * len(lines) <= h:
            return f, lines, lh
    f = Fonts(10)
    return f, wrap(draw, text, f, w), 13


def render(src_path, boxes):
    img = cv2.imread(src_path)
    H, W = img.shape[:2]
    out = img.copy()
    layout = []
    QA = []  # 자동 검수용: 상자마다 (원래 글 자리, 상자 자리, 직접 정한 네모인지, 글자 크기)
    for b in boxes:
        if not b.get("ko") and not b.get("parts"):
            continue
        if b.get("rect"):  # 직접 정한 네모(ellipse 면 타원) — 800px 기준. 상자가 그림으로 새는 곳에 씀
            kk = W / 800
            x0_, y0_, x1_, y1_ = [round(v * kk) for v in b["rect"]]
            full = np.zeros((H, W), np.uint8)
            if b.get("ellipse"):
                cv2.ellipse(full, ((x0_ + x1_) // 2, (y0_ + y1_) // 2), ((x1_ - x0_) // 2, (y1_ - y0_) // 2), 0, 0, 360, 255, -1)
            else:
                full[y0_:y1_, x0_:x1_] = 255
            inner = full.copy()
        else:
            full, inner = region_masks(img, b["seed"])
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bg = np.median(g[inner > 0])
        dark = b.get("dark", bg < 110)  # 어두운 말풍선: 밝은 글자
        if dark:
            text_px = ((g > bg + 45) & (inner > 0)).astype(np.uint8) * 255
        else:  # 상자 안쪽에서 바탕보다 뚜렷이 어두운 픽셀 = 글자
            text_px = ((g < bg - b.get("thr", 35)) & (inner > 0)).astype(np.uint8) * 255
        # 글자 자리 재기는 테두리에서 더 떨어진 안쪽에서만 (울퉁불퉁한 테두리를 글자로 잘못 재지 않게)
        deep = cv2.erode(inner, np.ones((max(5, W // 160),) * 2, np.uint8))
        ys, xs = np.where((text_px > 0) & (deep > 0))
        if len(xs) == 0:
            ys, xs = np.where(text_px > 0)
        if len(xs) == 0:
            continue
        tb = (xs.min(), ys.min(), xs.max(), ys.max())
        k = max(3, W // 400)
        mk = cv2.dilate(text_px, np.ones((k, k), np.uint8), iterations=b.get("grow", 2))
        yy, xx = np.where(mk > 0)
        if len(xx):  # 상자 둘레만 잘라서 메움 (그림 전체를 메우면 느림)
            m_ = 24
            a0, b0, a1, b1 = max(0, xx.min() - m_), max(0, yy.min() - m_), min(W, xx.max() + m_ + 1), min(H, yy.max() + m_ + 1)
            if b.get("cover"):  # 네모 전체를 밝은 바탕색 카드로 덮음 (기울어진 딱지·지우기 어려운 글)
                px = img[inner > 0].reshape(-1, 3)
                col = np.percentile(px, 92, axis=0) if b["cover"] is True else np.array(b["cover"][::-1])
                out[inner > 0] = col
            elif b.get("fill"):  # 단색 이름표: 바탕색으로 칠함 (메우기가 번지는 작은 흰 딱지)
                col = np.median(img[(inner > 0) & (text_px == 0)], axis=0)
                out[(cv2.dilate(mk, np.ones((3, 3), np.uint8)) > 0) & (inner > 0)] = col
            else:
                out[b0:b1, a0:a1] = cv2.inpaint(out[b0:b1, a0:a1], mk[b0:b1, a0:a1], max(3, W // 300), cv2.INPAINT_TELEA)
        full = inner
        # 원래 글자 크기 재기: 글자 조각들의 높이 중앙값 (대문자 높이 ≈ 글자 크기의 0.7)
        n_, lab, st, _ = cv2.connectedComponentsWithStats(text_px)
        hs = [st[i, 3] for i in range(1, n_) if st[i, 4] > 6 and st[i, 3] < (tb[3] - tb[1] + 1)]
        if hs:
            big_ = max(hs); hs = [h_ for h_ in hs if h_ >= 0.5 * big_]  # 점·쉼표 같은 작은 조각은 빼고
        em = (np.median(hs) / 0.68) if hs else None
        if b.get("em"):  # 글자 크기 직접 지정 (800px 기준)
            em = b["em"] * W / 800
        if b.get("parts"):  # 이어 붙은 말풍선 여럿: 지우기는 한 번에, 글은 칸마다 (rect 는 800px 기준)
            kk = W / 800
            for pt in b["parts"]:
                r = [round(v * kk) for v in pt["rect"]]
                layout.append((tuple(r), pt["ko"], pt.get("align", "center"), em, dark))
            continue
        ys2, xs2 = np.where(full > 0)
        QA.append(dict(tb=tuple(int(v) for v in tb), region=(int(xs2.min()), int(ys2.min()), int(xs2.max()), int(ys2.max())),
                       area=int((full > 0).sum()), rect=bool(b.get("rect")), ko=b["ko"], em=em, seed=b.get("seed"), li=len(layout)))
        if b.get("cover"):  # 덮은 카드: 글 자리는 네모 전체
            ys3, xs3 = np.where(inner > 0); tb = (int(xs3.min()), int(ys3.min()), int(xs3.max()), int(ys3.max()))
        layout.append((inner_rect(full, tb), b["ko"], b.get("align", "left" if b.get("shape") == "box" else "center"), em, dark))
    scale = 2 if W < 1600 else 1
    pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    if scale > 1:
        pil = pil.resize((W * scale, H * scale), Image.LANCZOS)
    d = ImageDraw.Draw(pil)
    drawn = []
    for (x0, y0, x1, y1), ko, align, em, dark in layout:
        pad = max(2, W // 500)
        X0, Y0, X1, Y1 = [v * scale for v in (x0 + pad, y0 + pad, x1 - pad, y1 - pad)]
        cap = int(W * scale / 24)
        if em:
            cap = min(cap, max(10, int(em * scale * 1.05)))
        f, lines, lh = fit(d, ko, X1 - X0, Y1 - Y0, cap)
        y = Y0 + ((Y1 - Y0) - lh * len(lines)) / 2
        drawn.append(dict(size=f.size / scale, box=[(x0 + pad), y0 + pad, x1 - pad, y1 - pad], ty=(y / scale, (y + lh * len(lines)) / scale),
                          tw=max((d.textlength(l, font=f.pick(l)) for l in lines), default=0) / scale, overflow=lh * len(lines) > (Y1 - Y0) + 1))
        for l in lines:
            fl = f.pick(l)
            lw = d.textlength(l, font=fl)
            x = X0 if align == "left" else X0 + ((X1 - X0) - lw) / 2
            d.text((x, y), l, font=fl, fill=(245, 240, 230) if dark else INK)
            y += lh
    render.qa = check(img, out, QA, drawn, W, H)
    return pil


def check(img, out, QA, drawn, W, H):
    """자동 검수: 상자마다 문제를 찾아 [(상자 번호, 문제, 설명)] 로 돌려줌.
    - 자리: 한글이 영어 글이 있던 자리에서 크게 벗어남 (상자를 잘못 잡아 글이 상자 밖에 그려짐)
    - 번짐: 상자로 잡은 곳이 영어 글 자리보다 지나치게 넓음 (그림 바탕까지 상자로 잡음)
    - 넘침: 한글이 상자에 다 들어가지 않음
    - 작음: 한글 글자가 원래 글자보다 지나치게 작음
    - 남은 영어: 지운 자리에 영어 글자가 아직 읽힘"""
    import subprocess
    bad = []
    for n, q in enumerate(QA, 1):
        if q["li"] >= len(drawn):
            continue
        dr = drawn[q["li"]]
        x0, y0, x1, y1 = q["tb"]
        tw_, th_ = x1 - x0, y1 - y0
        bx = dr["box"]
        cx = (bx[0] + bx[2]) / 2
        cy = (dr["ty"][0] + dr["ty"][1]) / 2
        mx, my = max(tw_ * .25, W * .03), max(th_ * .6, H * .04)
        if not (x0 - mx <= cx <= x1 + mx and y0 - my <= cy <= y1 + my):
            bad.append((n, "자리", f"한글이 원래 글 자리({x0},{y0}-{x1},{y1})에서 벗어남 ({int(cx)},{int(cy)})"))
        if q["seed"] and not q["rect"]:  # 한글 글 덩어리 가운데가 상자를 찍은 점(seed)에서 너무 멀면 상자를 잘못 잡은 것
            sd = q["seed"][0] if isinstance(q["seed"][0], (list, tuple)) else q["seed"]
            sx, sy = sd[0] * W / 800, sd[1] * W / 800
            bh = dr["ty"][1] - dr["ty"][0]
            if abs(cy - sy) > max(0.1 * H, bh) or abs(cx - sx) > max(0.3 * W, dr["tw"]):
                bad.append((n, "자리", f"한글 글({int(cx)},{int(cy)})이 상자 점({int(sx)},{int(sy)})에서 멀리 그려짐"))
        tb_area = max(1, tw_ * th_)
        if not q["rect"] and q["area"] > 6 * tb_area and q["area"] > 0.06 * W * H:
            bad.append((n, "번짐", f"상자로 잡은 곳이 글 자리의 {q['area'] / tb_area:.0f}배 (그림 바탕까지 잡았을 수 있음)"))
        if dr["overflow"]:
            bad.append((n, "넘침", "한글이 상자에 다 들어가지 않음"))
        if q["em"] and dr["size"] < 0.5 * q["em"] and dr["size"] < W / 70:
            bad.append((n, "작음", f"글자 크기 {dr['size']:.0f} (원래 {q['em']:.0f})"))
    # 남은 영어: 지운 상자 자리를 다시 읽어 봄 (한글 그리기 전 그림 out 에서)
    for n, q in enumerate(QA, 1):
        a0, b0, a1, b1 = q["region"]
        crop = out[max(0, b0):b1 + 1, max(0, a0):a1 + 1]
        if crop.size == 0:
            continue
        ok, png = cv2.imencode(".png", crop)
        try:
            tsv = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6", "-l", "eng", "tsv"], input=png.tobytes(), capture_output=True, timeout=60).stdout.decode("utf-8", "ignore")
        except Exception:
            continue
        keep = q["ko"].lower()
        words = []
        for line in tsv.splitlines()[1:]:
            c = line.split("\t")
            if len(c) >= 12 and c[11].strip():
                w = _re.sub(r"[^A-Za-z]", "", c[11])
                if len(w) >= 3 and float(c[10]) >= 75 and w.lower() not in keep and _re.search(r"[aeiouy]", w.lower()):
                    words.append(w)
        if len(words) >= 2:
            bad.append((n, "남은 영어", " ".join(words[:8])))
    return bad


def main():
    slug, story = sys.argv[1], sys.argv[2]
    src = sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else "cache/orig"
    outd = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "out/img"
    pages = json.load(open(f"ko/{slug}/{story}.json", encoding="utf-8"))
    for i, p in enumerate(pages, 1):
        sp = os.path.join(src, slug, p["img"])
        if not os.path.exists(sp):  # 원본이 보관함에 없으면 받아 옴
            from fetch_ocr import get, BASE
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            open(sp, "wb").write(get(BASE + slug + "/" + p["img"]))
        im = render(sp, p.get("boxes", []))
        for n, kind, msg in render.qa:  # 자동 검수 결과를 모아 둠 (jobs/run.sh 가 보고서로)
            print(f"검수 {slug}/{story} {i:02d}번 그림 상자{n} [{kind}] {msg}")
            os.makedirs(outd, exist_ok=True)
            with open(os.path.join(outd, "qa.jsonl"), "a", encoding="utf-8") as q:
                q.write(json.dumps(dict(key=f"{slug}/{story}", pic=i, box=n, kind=kind, msg=msg), ensure_ascii=False) + "\n")
        # 큰 그림: 원본과 같은 크기·JPEG 고화질 / 미리보기: 800px (원 사이트와 같게)
        W0 = Image.open(os.path.join(src, slug, p["img"])).width
        for sub, w, q in (("big", W0, 92), ("s", 800, 85)):
            o = os.path.join(outd, slug, story, sub, f"{i:02d}.jpg")
            os.makedirs(os.path.dirname(o), exist_ok=True)
            im.convert("RGB").resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(o, "JPEG", quality=q, optimize=True, progressive=True)
    print(slug, story, len(pages), "장")


if __name__ == "__main__":
    main()
