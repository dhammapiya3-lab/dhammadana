set -e
# 한글 그림 만들기 → R2 올리기 (ko/ 에 번역이 있는 이야기 중 jobs/render.txt 에 적은 것)
rm -rf out
while read book story; do
  [ -n "$book" ] && python3 pipeline/render.py "$book" "$story" --src cache/orig --out out/img
done < jobs/render.txt
python3 pipeline/upload_r2.py
# 공개 주소로 잘 보이는지 확인
first=$(head -1 jobs/render.txt | tr ' ' '/')
curl -s -o /dev/null -w "공개 주소 확인: %{http_code} %{size_download}바이트\n" "https://files.dhammadana.kr/storybooks/$first/big/01.jpg"
rm -rf out
