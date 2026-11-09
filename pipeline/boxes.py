"""그림 속 글 상자(말풍선·설명 상자)를 자동으로 찾고 영어 글을 읽는다.
python3 pipeline/boxes.py 그림.jpg  → JSON 출력
"""
import cv2, numpy as np, json, sys, subprocess, re

TOL = 9  # 이웃 픽셀 색 차이 허용치 (상자 바탕 질감·그라데이션 따라가기)


def ocr_words(img):
    h, w = img.shape[:2]
    scale = 2 if w < 1600 else 1
    big = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale > 1 else img
    ok, buf = cv2.imencode(".png", big)
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "11", "tsv"],
                         input=buf.tobytes(), capture_output=True).stdout.decode("utf-8", "replace")
    words = []
    for line in out.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        conf, t = float(f[10]), f[11].strip()
        if conf < 45 or not re.search(r"[A-Za-z]{2}|\d", t):
            continue
        x, y, ww, hh = [int(v) / scale for v in f[6:10]]
        words.append({"x": x, "y": y, "w": ww, "h": hh, "t": t, "c": conf})
    return words


def flood(img, seed):
    h, w = img.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(img.copy(), mask, (int(seed[0]), int(seed[1])), 0, (TOL,) * 3, (TOL,) * 3,
                  8 | cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    fl = mask[1:-1, 1:-1]
    cs, _ = cv2.findContours(fl, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    full = np.zeros_like(fl)
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


def detect(img):
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    words = ocr_words(img)
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
        ys, xs = np.where(full > 0)
        bw, bh = xs.max() - xs.min(), ys.max() - ys.min()
        if area > 0.25 * h * w or area < 0.004 * h * w or bw > 0.85 * w:
            continue  # 상자가 아님 (그림 배경으로 새어 나감)
        if not full[min(cy, h - 1), min(cx, w - 1)]:
            continue
        cs, _ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        if cv2.contourArea(c) / max(1, cv2.contourArea(cv2.convexHull(c))) < 0.85:
            continue  # 모양이 들쭉날쭉하면 상자·말풍선이 아님
        regions.append({"full": full, "seed": [int(s[0]), int(s[1])], "words": [wd],
                        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
    out = []
    for r in regions:
        ws = sorted(r["words"], key=lambda q: (q["y"], q["x"]))
        # 줄 단위로 묶어 읽는 순서 맞추기
        lines = []
        for q in ws:
            if lines and abs(lines[-1][0]["y"] - q["y"]) < q["h"] * 0.6:
                lines[-1].append(q)
            else:
                lines.append([q])
        text = " ".join(" ".join(x["t"] for x in sorted(l, key=lambda q: q["x"])) for l in lines)
        fill = float((r["full"] > 0).sum()) / ((r["bbox"][2] - r["bbox"][0] + 1) * (r["bbox"][3] - r["bbox"][1] + 1))
        out.append({"seed": r["seed"], "bbox": r["bbox"], "shape": "box" if fill > 0.9 else "bubble",
                    "en": text, "conf": round(min(q["c"] for q in ws))})
    out.sort(key=lambda b: (b["bbox"][1] // 80, b["bbox"][0]))
    # 상자 밖에 남은 글자(못 지운 글)
    loose = [q["t"] for q in words if not any(
        b["bbox"][0] <= q["x"] + q["w"] / 2 <= b["bbox"][2] and b["bbox"][1] <= q["y"] + q["h"] / 2 <= b["bbox"][3] for b in out)
        and q["c"] > 80 and len(q["t"]) > 2]
    return {"size": [w, h], "boxes": out, "loose": loose}


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(json.dumps({"file": f, **detect(cv2.imread(f))}, ensure_ascii=False))
