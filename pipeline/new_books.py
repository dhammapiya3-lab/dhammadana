"""새로 그린 그림책 올리기 (운영자 요청, 2026-11-21 — 「새로 그린 자따까」 등 원작 번역이 아닌 우리 그림책)
new/<책>/<이야기>/NN.jpg (테두리·해설까지 입힌 완성본, 1920×1080) 와 captions.json 을
R2 storybooks/<책>/<이야기>/big/NN.jpg(그대로) · s/NN.jpg(800px) 로 올리고,
data/rendered.json(그림 수) · data/rendered_stamp.json(그림 파일 해시) 을 갱신한다.
그림이 바뀐 이야기만 다시 올린다. 'ko/' 번역 파일과 render.py 는 쓰지 않는다.
python3 pipeline/new_books.py"""
import os, io, json, glob, hashlib, boto3
from botocore.config import Config
from PIL import Image

s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"].strip(),
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
                  region_name="auto", config=Config(retries={"max_attempts": 5}))
BUCKET = "dhammadana-files"
rd = json.load(open("data/rendered.json")) if os.path.exists("data/rendered.json") else {}
st = json.load(open("data/rendered_stamp.json")) if os.path.exists("data/rendered_stamp.json") else {}

def put(data, key):
    s3.put_object(Bucket=BUCKET, Key="storybooks/" + key, Body=data, ContentType="image/jpeg", CacheControl="public, max-age=86400")

n = 0
for d in sorted(glob.glob("new/*/*/")):
    book, story = d.rstrip("/").split("/")[-2:]
    key = f"{book}/{story}"
    files = sorted(glob.glob(d + "[0-9][0-9].jpg"))
    if not files: continue
    cap = open(d + "captions.json", "rb").read() if os.path.exists(d + "captions.json") else b""
    h = hashlib.md5(b"".join(open(f, "rb").read() for f in files) + cap).hexdigest()
    if st.get(key) == h and rd.get(key) == len(files):
        continue
    for f in files:
        name = os.path.basename(f)
        put(open(f, "rb").read(), f"{key}/big/{name}")
        im = Image.open(f).convert("RGB"); im.thumbnail((800, 800), Image.LANCZOS)
        b = io.BytesIO(); im.save(b, "JPEG", quality=88); put(b.getvalue(), f"{key}/s/{name}")
        n += 1
    rd[key] = len(files); st[key] = h
    print("새 그림책 올림:", key, len(files), "장")
json.dump(rd, open("data/rendered.json", "w"), ensure_ascii=False, indent=1, sort_keys=True)
json.dump(st, open("data/rendered_stamp.json", "w"), indent=1, sort_keys=True)
print("새 그림책: 올린 그림", n, "장")
