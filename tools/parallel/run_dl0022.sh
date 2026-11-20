#!/bin/sh
# DL-0022『붓다의 깨달음』 원서 대조 (운영자 요청, 2026-11-20) — 원서: Bhikkhu Bodhi (Ñāṇamoli 옮김 바탕),
#   The Middle Length Discourses of the Buddha — 한국어판에 실린 26개 경만.
#   본문: SuttaCentral 에 공개된 보디 스님 번역(CC BY-NC-ND 3.0) 19개 경 + (허락 확인 뒤) 인쇄본에서 옮겨 적은 7개 경.
#   sh tools/parallel/run_dl0022.sh            → 26개 경 모두(tools/parallel/dl0022_en 의 7개 경 포함)
#   ONLY_SC=1 sh tools/parallel/run_dl0022.sh  → 숫따센트럴 19개 경만 (나머지 7개 경은 한국어만)
#   한국어판 속표지·서문(보디 스님이 한국어판에 쓴 글 — 영어 원문 없음)·차례, 옮긴이의 말~판권지는 짝짓지 않음
set -e
P=tools/out/parallel/DL-0022.en.paras.json
python3 tools/parallel/en_dl0022.py
set --
while IFS= read -r l; do set -- "$@" "$l"; done <<EOT
$(python3 tools/parallel/pins_dl0022.py)
EOT
python3 tools/parallel/align.py DL-0022 en "$P" "$@" \
  --title "The Middle Length Discourses of the Buddha" --by "Bhikkhu Ñāṇamoli & Bhikkhu Bodhi" \
  --source "SuttaCentral (Bhikkhu Bodhi, MN, © Wisdom Publications, CC BY-NC-ND 3.0)" \
  --en-semi --ko-dots --ko-skip '^\^\^ 붓다의 깨달음$|^## 1 성스러운 구도' \
  --ko-skip '^## 옮긴이의 말$|'
