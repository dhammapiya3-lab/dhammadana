set -e
save() { git add -A && git commit -q -m "작업 결과: $1 [skip ci]" && git push -q || echo "저장할 것 없음"; }
python3 pipeline/parse.py
# 자타카 전체 글 상자 다시 읽기 (고친 상자 찾기, 이야기 6편마다 저장)
python3 - <<'PY'
import json, subprocess, os
b = json.load(open("data/catalog.json"))["books"]["Jataka"]
fs = [f for f in b["stories"] if f != "001-The-Waterless-Desert.htm"]
for i in range(0, len(fs), 6):
    subprocess.run(["python3", "pipeline/fetch_ocr.py", "Jataka", "--only", *fs[i:i+6]], env={**os.environ, "REDO": "1"}, check=False)
    subprocess.run(["bash", "-c", f'git add -A && git commit -q -m "작업 결과: 자타카 {i+1}~{i+len(fs[i:i+6])} [skip ci]" && git push -q'], check=False)
PY
