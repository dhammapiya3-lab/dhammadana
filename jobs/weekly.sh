# 매주 원 사이트 점검 (main 의 .github/workflows/storybooks-weekly.yml 이 부름)
set -e
cp data/catalog.json /tmp/old_catalog.json
[ -f data/assets_meta.json ] && cp data/assets_meta.json /tmp/old_meta.json || echo '{}' > /tmp/old_meta.json
rm -rf /tmp/mirror_new && mkdir /tmp/mirror_new
# 1) 다시 수집 (실패하면 지난 자료를 그대로 둠)
python3 - <<'PY'
import runpy, os, sys
os.chdir("/tmp/mirror_new"); sys.argv = ["crawl"]
import importlib.util
spec = importlib.util.spec_from_file_location("crawl", os.environ["GITHUB_WORKSPACE"] + "/src/pipeline/crawl.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.main()
PY
n=$(find /tmp/mirror_new/mirror -name '*.htm*' | wc -l)
echo "받은 쪽 수: $n"
if [ "$n" -lt 500 ]; then
  echo "# 그림책 원 사이트 주간 점검 — $(date +%F)

원 사이트를 제대로 받지 못했습니다 (받은 쪽 $n개). 사이트가 잠시 멈췄거나 주소가 바뀌었을 수 있습니다. 지난 자료는 그대로 두었습니다." > reports/latest.md
  exit 0
fi
rm -rf mirror && mv /tmp/mirror_new/mirror mirror
python3 pipeline/parse.py
python3 pipeline/assets_meta.py
python3 pipeline/diff.py /tmp/old_catalog.json /tmp/old_meta.json
# 2) 새 이야기는 글 상자를 미리 찾아 둠 (이번 주 최대 20편)
head -20 data/new_stories.txt | while read book story; do
  [ -n "$book" ] && python3 pipeline/fetch_ocr.py "$book" --only "$story" || true
done
