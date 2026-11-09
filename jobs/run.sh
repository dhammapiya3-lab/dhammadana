set -e
# 1단계: 원 사이트 HTML 수집
python3 pipeline/crawl.py | tail -5
