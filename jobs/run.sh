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
python3 pipeline/upload_r2.py
# 공개 주소로 잘 보이는지 확인
first=$(ls -d out/img/*/* 2>/dev/null | head -1 | sed 's#out/img/##')
curl -s -o /dev/null -w "공개 주소 확인: %{http_code} %{size_download}바이트\n" "https://files.dhammadana.kr/storybooks/$first/big/01.jpg"
rm -rf out
# 그림책 사이트에 '한글판 준비된 이야기' 목록 반영
git clone -q --depth 1 -b storybooks "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" /tmp/site
if ! cmp -s data/rendered.json /tmp/site/storybooks/data/ready.json; then
  cp data/rendered.json /tmp/site/storybooks/data/ready.json
  cd /tmp/site && git -c user.name=storybooks-bot -c user.email=actions@users.noreply.github.com commit -qam "그림책: 한글판 이야기 목록 갱신" && git push -q && cd - >/dev/null
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
