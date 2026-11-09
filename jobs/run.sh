set -e
# 2단계: 자타카 원본 그림 글 상자 읽기 (첫 이야기는 원본 보관)
python3 pipeline/parse.py
python3 pipeline/fetch_ocr.py Jataka --keep 001-The-Waterless-Desert.htm
