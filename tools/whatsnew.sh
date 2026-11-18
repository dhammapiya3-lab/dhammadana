#!/bin/sh
# 새 요청을 받으면 맨 먼저 돌리는 확인 (운영자 요청, 2026-11-18)
#   sh tools/whatsnew.sh          최신본을 받고, 마지막으로 확인한 뒤 올라온 변경을 보여 줌
#                                 (특히 지침 파일 CLAUDE.md 에서 바뀐 줄)
#   sh tools/whatsnew.sh --mark   지금 상태를 '확인함'으로 적어 둠 (내가 올린 뒤에 돌려, 내 변경을 다음에 다시 보이지 않게)
# 마지막으로 확인한 곳은 .git/dd-last-seen (저장소에 올라가지 않음). 없으면(새 작업 공간) 지난 24시간을 보여 줌.
cd "$(dirname "$0")/.." || exit 1
M=.git/dd-last-seen
if [ "$1" = "--mark" ]; then git rev-parse HEAD > "$M"; echo "확인한 곳을 $(git log -1 --format='%h %s' | cut -c1-70) 로 적었습니다."; exit 0; fi
git pull -q --rebase origin main 2>&1 | tail -2
NEW=$(git rev-parse HEAD)
if [ -s "$M" ] && git cat-file -e "$(cat "$M")" 2>/dev/null; then
  OLD=$(cat "$M"); RANGE="$OLD..$NEW"; echo "== 마지막 확인($(git log -1 --format='%h %ci' "$OLD")) 뒤에 올라온 변경 =="
else
  OLD=$(git rev-list -1 --before='24 hours ago' HEAD)
  [ -n "$OLD" ] || OLD=$(git rev-list --since='24 hours ago' HEAD | tail -1)^   # 짧게 받은 저장소면 24시간 안의 가장 오래된 것 앞
  git cat-file -e "$OLD" 2>/dev/null || OLD=$(git rev-list --max-parents=0 HEAD | tail -1)
  RANGE="$OLD..$NEW"; echo "== (처음 확인) 지난 24시간 동안 올라온 변경 =="
fi
N=$(git rev-list --count "$RANGE")
if [ "$N" = 0 ]; then echo "새로 올라온 변경 없음."; else
  git log --format='- %h %ci %s' "$RANGE" | cut -c1-160
  if git diff --quiet "$RANGE" -- CLAUDE.md; then echo "== 지침(CLAUDE.md): 바뀐 곳 없음 =="
  else echo "== 지침(CLAUDE.md)에서 바뀐 줄 (+ 새로 들어간 글, - 빠진 글) =="
    git diff -U0 --word-diff=plain --word-diff-regex='[^[:space:]]+' "$RANGE" -- CLAUDE.md | grep -v '^@@\|^diff\|^index\|^---\|^+++' | grep -o '{+[^}]*+}\|\[-[^]]*-\]' | sed 's/^{+/+ /;s/+}$//;s/^\[-/- /;s/-\]$//' | cut -c1-400
  fi
fi
echo "$NEW" > "$M"
