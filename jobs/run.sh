set -e
# 한글 그림 만들기 → R2 올리기 (ko/ 에 번역이 있는 이야기 중 jobs/render.txt 에 적은 것)
rm -rf out
while read book story; do
  [ -n "$book" ] && python3 pipeline/render.py "$book" "$story" --src cache/orig --out out/img
done < <(python3 - <<'PY'
import glob, json, os
# 번역이 있는데 아직 안 올렸거나, 번역 파일이 올린 뒤에 바뀐 이야기
done = json.load(open("data/rendered.json")) if os.path.exists("data/rendered.json") else {}
stamp = json.load(open("data/rendered_stamp.json")) if os.path.exists("data/rendered_stamp.json") else {}
for f in sorted(glob.glob("ko/*/*.json")):
    key = f[3:-5]; book, story = key.split("/")
    h = __import__("hashlib").md5(open(f, "rb").read()).hexdigest()
    if key not in done or stamp.get(key) != h:
        print(book, story)
PY
)
# 자동 검수 보고서 + 검수용 800px 한글 그림을 storybooks-qa 가지에 (Claude 가 눈으로 확인)
python3 - <<'PY'
import json, os, collections
rows = [json.loads(l) for l in open("out/img/qa.jsonl", encoding="utf-8")] if os.path.exists("out/img/qa.jsonl") else []
os.makedirs("reports", exist_ok=True)
with open("reports/qa.md", "w", encoding="utf-8") as f:
    f.write(f"# 자동 검수 결과\n\n이번에 만든 그림 중 문제 의심 {len(rows)}곳\n\n")
    for r in rows:
        f.write(f"- {r['key']} {r['pic']:02d}번 그림, 상자 {r['box']} [{r['kind']}] {r['msg']}\n")
print("자동 검수: 문제 의심", len(rows), "곳")
PY
rm -f out/img/qa.jsonl
rm -rf /tmp/qa && git clone -q --depth 1 -b storybooks-qa "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" /tmp/qa 2>/dev/null || (mkdir -p /tmp/qa && cd /tmp/qa && git init -q -b storybooks-qa)
for d in out/img/*/*; do [ -d "$d/s" ] || continue; k=${d#out/img/}; rm -rf "/tmp/qa/$k"; mkdir -p "/tmp/qa/$k"; cp "$d"/s/*.jpg "/tmp/qa/$k/"; done
cp reports/qa.md /tmp/qa/qa.md
(cd /tmp/qa && git add -A && git -c user.name=storybooks-bot -c user.email=actions@users.noreply.github.com commit -qm "검수용 한글 그림 [skip ci]" && git push -q -f "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" storybooks-qa) || true
python3 pipeline/upload_r2.py
# 공개 주소로 잘 보이는지 확인
first=$(ls -d out/img/*/* 2>/dev/null | head -1 | sed 's#out/img/##')
curl -s -o /dev/null -w "공개 주소 확인: %{http_code} %{size_download}바이트\n" "https://files.dhammadana.kr/storybooks/$first/big/01.jpg"
rm -rf out
# 그림책 사이트에 '한글판 준비된 이야기' 목록 반영
git clone -q --depth 1 -b storybooks "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" /tmp/site
# stamp.json: 이야기마다 그림 판 번호 — 그림을 다시 만들면 주소(?v=)가 바뀌어 예전 그림이 기기·CDN 에 남지 않음
python3 -c "import json;d=json.load(open('data/rendered_stamp.json'));json.dump({k:v[:8] for k,v in d.items()},open('/tmp/stamp.json','w'),indent=0)"
if ! cmp -s data/rendered.json /tmp/site/storybooks/data/ready.json || ! cmp -s /tmp/stamp.json /tmp/site/storybooks/data/stamp.json; then
  cp data/rendered.json /tmp/site/storybooks/data/ready.json
  cp /tmp/stamp.json /tmp/site/storybooks/data/stamp.json
  cd /tmp/site && git add storybooks/data && git -c user.name=storybooks-bot -c user.email=actions@users.noreply.github.com commit -qm "그림책: 한글판 이야기 목록·그림 판 갱신" && git push -q && cd - >/dev/null
fi
# 다음 책 글 상자 읽기 + 번역용 800px 미리보기 (jobs/next_books.txt 에 적은 책, 이미 읽은 이야기는 건너뜀)
if [ -s jobs/next_books.txt ]; then
  mkdir -p review
  for b in $(cat jobs/next_books.txt); do
    python3 pipeline/fetch_ocr.py "$b" | tail -1
    python3 pipeline/preview.py "$b" | tail -1
  done
  cd review && git init -q -b storybooks-review && git add -A && git -c user.name=storybooks-bot -c user.email=actions@users.noreply.github.com commit -qm "번역용 미리보기 [skip ci]"
  git push -q -f "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" storybooks-review
  cd .. && rm -rf review
fi
