#!/bin/sh
# DL-0037『사아리뿟따 이야기』 원서 대조 (운영자 요청, 2026-11-24) — 원서: Nyanaponika Thera, The Life of Sariputta
#   (BPS Wheel No. 90/92, © 1987, BPS Online Edition 2008 — https://static.sariputta.com/pdf/tipitaka/1154/wh090_nyanaponika_the-life-of-sariiputta.pdf)
#   sh tools/parallel/run_dl0037.sh [원서.pdf]   — 원서 PDF 를 주면 원서 글부터 다시 뽑음
#   한국어판은 원서와 장 짜임이 달라(인간 사아리뿟따 안의 소제목 차례, 원서 여러 곳 글을 옮겨 묶음) 원서 문단을 한국어판 차례로
#   다시 늘어놓고 짝지음 — 손 짝은 tools/parallel/pins_dl0037.py. 원서에 없는 한국어 글: 숙세의 서원·사아리뿟따의 과거생 이야기,
#   상수제자 첫머리(대전기경·상수제자의 역할·한 쌍인 까닭·불법 체계화), 판권지. 한국어판 차례(%%)는 원서에 차례 쪽이 없어 짝 없음.
set -e
P=tools/out/parallel/DL-0037.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0037.py "$1"; fi
set --
while IFS= read -r l; do set -- "$@" "$l"; done <<EOT
$(python3 tools/parallel/pins_dl0037.py)
EOT
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --spin "$l";; esac; done < tools/parallel/dl0037_spins.txt
python3 tools/parallel/align.py DL-0037 en "$P" "$@" \
  --title "The Life of Sariputta" --by "Nyanaponika Thera" \
  --source "The Life of Sariputta (Buddhist Publication Society, The Wheel Publication No. 90/92, BPS Online Edition 2008)" \
  --ko-skip '^## 숙세宿世의 서원|^## Ⅱ\. 인간' \
  --ko-skip '^부처님께서는 〈대전기경|^부처님께서는 승가의 여러 비구들에게 두 상수제자' \
  --ko-skip '^This translation was possible|' \
  --ko-short 7 --fnpin 7=38 --fnpin 17= $ALIGN_EXTRA
