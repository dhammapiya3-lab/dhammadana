"""out/img 의 한글 그림과 covers/ 를 R2(dhammadana-files)의 storybooks/ 아래에 올리고 data/rendered.json 을 갱신.
python3 pipeline/upload_r2.py"""
import os, json, glob, boto3
from botocore.config import Config
s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"].strip(),
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
                  region_name="auto", config=Config(retries={"max_attempts": 5}))
BUCKET = "dhammadana-files"
def put(path, key):
    s3.upload_file(path, BUCKET, key, ExtraArgs={"ContentType": "image/jpeg", "CacheControl": "public, max-age=86400"})
n = 0
for f in sorted(glob.glob("out/img/**/*.jpg", recursive=True)):
    put(f, "storybooks/" + os.path.relpath(f, "out/img")); n += 1
for f in sorted(glob.glob("covers/*.jpg")):
    put(f, "storybooks/covers/" + os.path.basename(f)); n += 1
rd = json.load(open("data/rendered.json")) if os.path.exists("data/rendered.json") else {}
for d in sorted(glob.glob("out/img/*/*/big")):
    slug, sid = d.split("/")[-3], d.split("/")[-2]
    rd[f"{slug}/{sid}"] = len(glob.glob(d + "/*.jpg"))
json.dump(rd, open("data/rendered.json", "w"), ensure_ascii=False, indent=1, sort_keys=True)
import hashlib
st = json.load(open("data/rendered_stamp.json")) if os.path.exists("data/rendered_stamp.json") else {}
for d in sorted(glob.glob("out/img/*/*/big")):
    key = "/".join(d.split("/")[-3:-1])
    st[key] = hashlib.md5(open(f"ko/{key}.json", "rb").read()).hexdigest()
json.dump(st, open("data/rendered_stamp.json", "w"), indent=1, sort_keys=True)
print("R2 에 올림:", n, "개 / 한글판 이야기", len(rd), "편")
