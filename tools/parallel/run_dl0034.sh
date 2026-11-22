#!/bin/sh
# DL-0034『업과 윤회의 법칙』 원서 대조 (운영자 요청, 2026-11-22) — 원서: The Pa-Auk Tawya Sayadaw, The Workings of Kamma (© 2007 웹판 PDF 504쪽)
#   sh tools/parallel/run_dl0034.sh [원서.pdf]   — 원서 PDF 를 주면 원서 글부터 다시 뽑음
#   한국어판 법보시 쪽·한국어 번역 허가서·약어표·일러두기·번역 후기·Source References(그림)는 짝짓기에서 뺌.
set -e
P=tools/out/parallel/DL-0034.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0034.py "$1"; fi
set --
[ -f tools/parallel/dl0034_spins.txt ] && while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --spin "$l";; esac; done < tools/parallel/dl0034_spins.txt
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0034_heads.txt
python3 tools/parallel/align.py DL-0034 en "$P" "$@" \
  --title "The Workings of Kamma" --by "The Pa-Auk Tawya Sayadaw" \
  --source "The Workings of Kamma (© 2007, published as a gift, in the public domain — web edition PDF)" \
  --ko-skip '^\*\*이 책은 미얀마 파아옥|^## 제목 차례\[요약\]' \
  --ko-skip '^## 인용 문헌/경전 약어표|^## I\. 차꼬경' \
  --ko-skip '^## 번역 후기|^## 부록 1' \
  --ko-skip '^## Source References|' \
  --pin "=@The Workings" --pin "=@of Kamma" --pin "=@Pa-Auk Logo Here" --pin "=@The Pa-Auk Tawya Sayadaw" --pin "=@A G I F T" \
  --pin "2:0=@© 2007+@The material in this book+@It is also the author’s+@Any inquiries" --pin "=@Title: The Workings" \
  --pin "3:0=@Cover Illustration:" --pin "3:1=@The Indian emperor Asoka+@(Drawn from The Edicts+@The Most Venerable Pa-Auk Sayadaw has adopted" \
  --pin "=@NAMO TASSA" --pin "=@HOMAGE TO HIM" --pin "=@BHAGAVATO" --pin "=@THE EXALTED ONE" --pin "=@ARAHATO" --pin "=@SAMMĀ-" --pin "=@SAMBUDDHASSA" --pin "=@SELF-ENLIGHTENED ONE" \
  --pin "18:0+18:1=@I —‘THE CLOG-BOUND" --seg "18:0+18:1=@I —‘THE CLOG-BOUND" \
  --fnpin 119=209 --fnpin 200=345 --fnpin 246=425 --fnpin 405=679 --fnpin 408=681 --fnpin 436=714 --fnpin 157=271 --fnpin 138=243 --fnpin 234=401 \
  --fnpin 107= --fnpin 253= --fnpin 418= --fnpin 567= --fnpin 610= --fnpin 739= --fnpin 409= \
  --gl-start '^용어 풀이 없음$' --toc --ko-short 7 $ALIGN_EXTRA
