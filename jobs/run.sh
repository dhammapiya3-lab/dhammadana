set -e
# 번역용 미리보기: 자타카 원본 800px → storybooks-review 가지 (기록을 쌓지 않게 매번 새로)
python3 pipeline/preview.py Jataka | tail -2
cd review && git init -q -b storybooks-review && git add -A && git -c user.name=storybooks-bot -c user.email=actions@users.noreply.github.com commit -qm "번역용 미리보기 [skip ci]"
git push -q -f "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}" storybooks-review
cd .. && rm -rf review
