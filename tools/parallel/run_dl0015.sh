#!/bin/sh
# DL-0015『붓다의 말씀』 원서 대조 (운영자 요청, 2026-11-19) — 원서: Nyanatiloka, The Word of the Buddha (BPS 14판 전자판)
#   sh tools/parallel/run_dl0015.sh [wordofbuddha.pdf]
#   원서 PDF 를 주면 원서 글부터 다시 뽑음 (https://www.urbandharma.org/pdf/wordofbuddha.pdf)
#   한국어판에만 있는 것(속표지 시·추천의 글·일러두기·빠알리 문헌 약어·역자 후기~판권지)은 짝 없음,
#   한국어판 4쪽 영어 속표지 ↔ 원서 속표지, 차 례 ↔ CONTENTS
set -e
P=tools/out/parallel/DL-0015.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0015.py "$1"; fi
# 제목 짝(dl0015_heads.txt) → 줄마다 --pin(제목끼리)·--seg(그 앞뒤 문장은 서로 짝짓지 않음)
set --
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0015_heads.txt
python3 tools/parallel/align.py DL-0015 en "$P" --toc "$@" \
  --title "The Word of the Buddha" --by "Nyanatiloka" \
  --source "wordofbuddha.pdf (Buddhist Publication Society, 14th ed. 1967 — electronic edition)" \
  --ko-skip '^## 추천의 글|^## 차 례' --ko-skip '^## 초판 역자후기|' \
  --pin "3:0+3:1=" --pin "5:0=" \
  --pin "4:0=@THE WORD OF+@THE BUDDHA" --pin "4:1=@An Outline" --pin "4:2=@Compiled" --pin "4:3=@BUDDHIST PUBLICATION" \
  --pin "17:0=@CONTENTS" --base 0.25 --ko-none '^>> 《' --kind-base note=0.15 \
  --pin "=@In Visuddhi Magga XIII, 2+@When a butcher rears" \
  --pin "=@Self-Illusion (sakkāya-diṭṭhi) may reveal+@1. ‘Eternalism’+@2. ‘Annihilationism’+@For further details about Satipaṭṭhāna+@These four contemplations of Satipaṭṭhāna"
