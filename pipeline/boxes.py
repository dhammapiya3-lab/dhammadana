"""그림 속 글 상자(말풍선·설명 상자)를 자동으로 찾고 영어 글을 읽는다.
python3 pipeline/boxes.py 그림.jpg  → JSON 출력
"""
import cv2, numpy as np, json, sys, subprocess, re

TOL = 9  # 이웃 픽셀 색 차이 허용치 (상자 바탕 질감·그라데이션 따라가기)


def _tess(im, psm, scale):
    ok, buf = cv2.imencode(".png", im)
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", psm, "tsv"],
                         input=buf.tobytes(), capture_output=True).stdout.decode("utf-8", "replace")
    words = []
    for line in out.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        conf, t = float(f[10]), f[11].strip()
        if conf < 30 or not re.search(r"[A-Za-z]{2}|\d", t) or (conf < 45 and not re.search(r"[A-Za-z]{3}", t)):
            continue
        x, y, ww, hh = [int(v) / scale for v in f[6:10]]
        words.append({"x": x, "y": y, "w": ww, "h": hh, "t": t, "c": conf})
    return words


def ocr_words(img):
    """흑백 원본(11·3)과 절반 크기(3)로 세 번 읽어 합친다 — 작은 글자를 놓치지 않게"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if g.shape[1] < 1600:
        g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC); base = 2
    else:
        base = 1
    half = cv2.resize(g, None, fx=.5, fy=.5, interpolation=cv2.INTER_AREA)
    col = img if base == 1 else cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    words = []
    for im, psm, sc in ((g, "11", base), (g, "3", base), (half, "3", base / 2), (col, "11", base)):
        for q in _tess(im, psm, sc):
            if not any(abs(q["x"] - o["x"]) < o["h"] * .6 and abs(q["y"] - o["y"]) < o["h"] * .6 for o in words):
                words.append(q)
    return words


def frame_mask(img):
    """그림 둘레의 흰 여백을 막아 둔 floodFill 마스크"""
    h, w = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    rows = np.where((g < 235).mean(1) > 0.5)[0]; cols = np.where((g < 235).mean(0) > 0.5)[0]
    mask = np.ones((h + 2, w + 2), np.uint8)
    if len(rows) and len(cols):
        y0, y1, x0, x1 = rows.min(), rows.max(), cols.min(), cols.max()
        mask[y0 + 2:y1 + 1, x0 + 2:x1 + 1] = 0  # 테두리 한 줄 안쪽만 열어 둠
    else:
        mask[1:-1, 1:-1] = 0
    return mask


def flood(img, seed):
    h, w = img.shape[:2]
    mask = frame_mask(img)
    cv2.floodFill(img.copy(), mask, (int(seed[0]), int(seed[1])), 0, (TOL,) * 3, (TOL,) * 3,
                  8 | cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    fl = (mask[1:-1, 1:-1] == 255).astype(np.uint8) * 255
    cs, _ = cv2.findContours(fl, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    full = np.zeros_like(fl)
    if cs:
        cv2.drawContours(full, [max(cs, key=cv2.contourArea)], -1, 255, -1)
    return fl, full


def seed_for(img, gray, wd):
    """글자 바로 옆의 밝은 바탕 픽셀"""
    h, w = gray.shape
    x0, y0 = int(max(0, wd["x"] - 6)), int(max(0, wd["y"] - 6))
    x1, y1 = int(min(w - 1, wd["x"] + wd["w"] + 6)), int(min(h - 1, wd["y"] + wd["h"] + 6))
    patch = gray[y0:y1, x0:x1]
    if patch.size == 0:
        return None
    thr = np.percentile(patch, 85)
    ys, xs = np.where(patch >= thr)
    # 가장자리 쪽 밝은 점을 고른다 (글자 획 사이 말고)
    k = np.argmin(np.minimum.reduce([xs, ys, patch.shape[1] - xs, patch.shape[0] - ys]))
    return (x0 + xs[k], y0 + ys[k])


REF = 800  # 상자 찾기는 이 너비로 줄인 그림에서 (큰 그림은 테두리가 번져 채우기가 새어 나감)


def small_of(img):
    H, W = img.shape[:2]
    k = REF / W
    return cv2.resize(img, (REF, round(H * k)), interpolation=cv2.INTER_AREA), k


def region_masks(img, seed800):
    """원본 크기의 (상자 전체, 상자 안쪽) 마스크"""
    H, W = img.shape[:2]
    sm, k = small_of(img)
    fl, full = flood(sm, seed800)
    full = cv2.resize(full, (W, H), interpolation=cv2.INTER_LINEAR)
    full = (full > 127).astype(np.uint8) * 255
    band = max(5, int(3.5 / k))  # 테두리 선 두께만큼 안쪽으로
    inner = cv2.erode(full, np.ones((band, band), np.uint8))
    return full, inner


def detect(img):
    big = img
    img, kk = small_of(big)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    words = []
    for q in ocr_words(big):  # 글자 읽기는 원본 크기로 (더 정확)
        words.append({**q, "x": q["x"] * kk, "y": q["y"] * kk, "w": q["w"] * kk, "h": q["h"] * kk})
    regions = []  # {full, fl, words}
    for wd in words:
        cx, cy = int(wd["x"] + wd["w"] / 2), int(wd["y"] + wd["h"] / 2)
        hit = next((r for r in regions if r["full"][min(cy, h - 1), min(cx, w - 1)]), None)
        if hit:
            hit["words"].append(wd); continue
        s = seed_for(img, gray, wd)
        if s is None or gray[s[1], s[0]] < 150:
            continue
        fl, full = flood(img, s)
        area = int((full > 0).sum())
        if area == 0:
            continue
        ys, xs = np.where(full > 0)
        bw, bh = xs.max() - xs.min(), ys.max() - ys.min()
        if area > 0.25 * h * w or area < 0.004 * h * w or bw > 0.85 * w:
            continue  # 상자가 아님 (그림 배경으로 새어 나감)
        if not full[min(cy, h - 1), min(cx, w - 1)]:
            continue
        cs, _ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        if cv2.contourArea(c) / max(1, cv2.contourArea(cv2.convexHull(c))) < 0.62:
            continue  # 모양이 들쭉날쭉하면 상자·말풍선이 아님
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        fl_, _ = flood(img, s)
        if np.median(hsv[..., 1][fl_ > 0]) > 90 or np.median(hsv[..., 2][fl_ > 0]) < 170:
            continue  # 바탕이 흰색·양피지색이 아님 (하늘 등)
        regions.append({"full": full, "seed": [int(s[0]), int(s[1])], "words": [wd],
                        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
    out = []
    for r in regions:
        if not any(q["c"] >= 60 and re.search(r"[A-Za-z]{3}", q["t"]) for q in r["words"]):
            continue
        ws = sorted(r["words"], key=lambda q: q["y"] + q["h"] / 2)
        # 줄 단위로 묶어 읽는 순서 맞추기 (글자 높이의 절반 안이면 같은 줄)
        lines = []
        for q in ws:
            yc = q["y"] + q["h"] / 2
            if lines and abs(lines[-1][1] - yc) < max(q["h"], lines[-1][2]) * 0.5:
                L = lines[-1]; L[0].append(q); L[1] = sum(z["y"] + z["h"] / 2 for z in L[0]) / len(L[0])
            else:
                lines.append([[q], yc, q["h"]])
        lines = [L[0] for L in lines]
        text = " ".join(" ".join(x["t"] for x in sorted(l, key=lambda q: q["x"])) for l in lines)
        text = re.sub(r"\b(\w+) \1\b", r"\1", text, flags=re.I)
        fill = float((r["full"] > 0).sum()) / ((r["bbox"][2] - r["bbox"][0] + 1) * (r["bbox"][3] - r["bbox"][1] + 1))
        out.append({"seed": r["seed"], "bbox": [round(v / kk) for v in r["bbox"]], "shape": "box" if fill > 0.9 else "bubble",
                    "en": text, "conf": round(min(q["c"] for q in ws))})
    out.sort(key=lambda b: (b["bbox"][1] // 200, b["bbox"][0]))
    # 상자 밖에 남은 글자(못 지운 글)
    loose = [q["t"] for q in words if not any(
        b["bbox"][0] * kk <= q["x"] + q["w"] / 2 <= b["bbox"][2] * kk and b["bbox"][1] * kk <= q["y"] + q["h"] / 2 <= b["bbox"][3] * kk for b in out)
        and q["c"] > 80 and len(q["t"]) > 2]
    return {"size": [big.shape[1], big.shape[0]], "ref": REF, "boxes": out, "loose": loose}


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(json.dumps({"file": f, **detect(cv2.imread(f))}, ensure_ascii=False))
