"""내려받기 파일 만들기 (운영자 요청, 2026-11-14)
이야기마다: PDF(원본 크기 그림) · ZIP(원본 크기 그림 낱장)
책마다:     인쇄용 PDF(원본 크기) · 보기용 PDF(작은 그림) · ZIP(이야기별 폴더)
모두 맨 끝에 출처 쪽(CC BY-SA 4.0)을 넣는다. 그림을 고쳐 다시 만들면(번역 파일이 바뀌면) 그 이야기와 그 책의 파일을 다시 만든다.
R2 키: storybooks/dl/<책>/<이야기>.pdf|.zip, storybooks/dl/<책>/_book.pdf|_book_s.pdf|_book.zip
결과 크기: <사이트>/storybooks/data/dl.json, 만든 판: data/bundles.json
python3 pipeline/bundles.py <사이트 폴더(/tmp/site)>"""
import os, sys, io, json, zipfile, hashlib, tempfile, boto3, img2pdf
from botocore.config import Config
from PIL import Image, ImageDraw, ImageFont

SITE = sys.argv[1]
s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"].strip(),
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
                  region_name="auto", config=Config(retries={"max_attempts": 5}))
BUCKET = "dhammadana-files"
KO = json.load(open(f"{SITE}/storybooks/data/ko.json", encoding="utf-8"))
CAT = json.load(open(f"{SITE}/storybooks/data/catalog.json", encoding="utf-8"))
READY = json.load(open("data/rendered.json"))
STAMP = json.load(open("data/rendered_stamp.json"))
DONE = json.load(open("data/bundles.json")) if os.path.exists("data/bundles.json") else {}
DLF = f"{SITE}/storybooks/data/dl.json"
DL = json.load(open(DLF)) if os.path.exists(DLF) else {}
FONT = "pipeline/fonts/GowunDodum-Regular.ttf"
S = KO["site"]

sid = lambda f: f.rsplit(".", 1)[0]
def stories(book):  # 차례 순서대로, 한글 그림이 있는 이야기만
    out = []
    for s in CAT["books"][book]["stories"].values():
        k = f"{book}/{sid(s['file'])}"
        if READY.get(k):
            t = KO.get("book_detail", {}).get(book, {}).get("stories", {}).get(s["file"], {}).get("title") or s["title"]
            out.append((k, t, READY[k]))
    return out
btitle = lambda b: KO.get("books", {}).get(b, {}).get("title") or CAT["books"][b]["title"]

cache = {}
def get(key):
    if key not in cache:
        cache[key] = s3.get_object(Bucket=BUCKET, Key="storybooks/" + key)["Body"].read()
    return cache[key]

def credit(size, lines):  # 출처 쪽 (그림과 같은 크기)
    W, H = size
    im = Image.new("RGB", (W, H), (247, 241, 229)); d = ImageDraw.Draw(im)
    big, small = ImageFont.truetype(FONT, max(18, W // 32)), ImageFont.truetype(FONT, max(14, W // 52))
    y = H // 6
    for i, l in enumerate(lines):
        f = big if i == 0 else small
        w = d.textlength(l, font=f); d.text(((W - w) / 2, y), l, font=f, fill=(60, 40, 25))
        y += int((f.size) * (2.0 if i == 0 else 1.7))
    b = io.BytesIO(); im.save(b, "JPEG", quality=90); return b.getvalue()

def credit_lines(title):
    return [title, "", "원작: Dharma Storybooks (dharma-storybooks.net)", "기획·지도: 아난다조띠 스님 (Bhante Ānandajoti)",
            "한국어판: 붓다담마 그림책 (storybooks.dhammadana.kr) — 붓다담마 법보시 도서관 옮김",
            "번역: Anthropic의 AI Claude를 사용해 옮기고 검수함", "",
            "크리에이티브 커먼즈 저작자표시-동일조건변경허락 4.0 (CC BY-SA 4.0)",
            "출처를 밝히면 누구나 자유롭게 나누고 고쳐 쓸 수 있으며, 고친 것도 같은 라이선스로 나누어야 합니다.",
            "https://creativecommons.org/licenses/by-sa/4.0/deed.ko", "", "이 법보시의 공덕을 모든 존재와 함께 나눕니다."]

README = lambda title: "\n".join(credit_lines(title)) + "\n"

def put(path, key, ctype):
    s3.upload_file(path, BUCKET, "storybooks/dl/" + key, ExtraArgs={"ContentType": ctype, "CacheControl": "public, max-age=3600"})
    return os.path.getsize(path)

def pdf(imgs, path):
    with open(path, "wb") as f: f.write(img2pdf.convert(imgs))

def size_of(jpg):
    return Image.open(io.BytesIO(jpg)).size

tmp = tempfile.mkdtemp()
books = sorted({k.split("/")[0] for k in READY})
n = 0
for book in books:
    sts = stories(book)
    if not sts: continue
    bt = btitle(book)
    changed = False
    for k, t, cnt in sts:
        if DONE.get(k) == STAMP.get(k) and k in DL: continue
        _, st = k.split("/")
        big = [get(f"{k}/big/{i:02d}.jpg") for i in range(1, cnt + 1)]
        cred = credit(size_of(big[0]), credit_lines(f"{bt} — {t}"))
        p, z = f"{tmp}/a.pdf", f"{tmp}/a.zip"
        pdf(big + [cred], p)
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            for i, b in enumerate(big, 1): zf.writestr(f"{i:02d}.jpg", b)
            zf.writestr("출처_라이선스.txt", README(f"{bt} — {t}"))
        DL[k] = {"pdf": put(p, f"{book}/{st}.pdf", "application/pdf"), "zip": put(z, f"{book}/{st}.zip", "application/zip"), "n": cnt}
        DONE[k] = STAMP.get(k); changed = True; n += 1
        print("이야기", k, DL[k])
    have = {k for k, _, _ in sts}
    if changed or book not in DL or DL[book].get("stories") != len(sts):
        big, small = [], []
        z = f"{tmp}/b.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            for j, (k, t, cnt) in enumerate(sts, 1):
                folder = t.replace("/", "·")
                for i in range(1, cnt + 1):
                    b = get(f"{k}/big/{i:02d}.jpg"); big.append(b); zf.writestr(f"{folder}/{i:02d}.jpg", b)
                    small.append(get(f"{k}/s/{i:02d}.jpg"))
            zf.writestr("출처_라이선스.txt", README(bt))
        p1, p2 = f"{tmp}/b1.pdf", f"{tmp}/b2.pdf"
        pdf(big + [credit(size_of(big[0]), credit_lines(bt))], p1)
        pdf(small + [credit(size_of(small[0]), credit_lines(bt))], p2)
        DL[book] = {"pdf": put(p1, f"{book}/_book.pdf", "application/pdf"), "pdfs": put(p2, f"{book}/_book_s.pdf", "application/pdf"),
                    "zip": put(z, f"{book}/_book.zip", "application/zip"), "stories": len(sts), "n": len(big)}
        print("책", book, DL[book]); n += 1
    cache.clear()
json.dump(DONE, open("data/bundles.json", "w"), indent=1, sort_keys=True)
json.dump(DL, open(DLF, "w"), ensure_ascii=False, indent=0, sort_keys=True)
print("내려받기 파일:", n, "묶음 새로 만듦")
