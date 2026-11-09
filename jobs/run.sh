set -e
save() { git add -A && git commit -q -m "작업 결과: $1 [skip ci]" && git push -q || echo "저장할 것 없음"; }
python3 pipeline/parse.py
# 표지
python3 pipeline/covers.py | tail -3
save 표지
# 시범: 자타카 01 (원본 보관)
python3 pipeline/fetch_ocr.py Jataka --keep 001-The-Waterless-Desert.htm 2>&1 | head -3 || true
save "자타카 01"
# 자타카 나머지 글 상자 읽기
time python3 pipeline/fetch_ocr.py Jataka
