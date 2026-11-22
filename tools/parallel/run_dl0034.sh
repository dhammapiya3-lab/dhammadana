#!/bin/sh
# DL-0034『업과 윤회의 법칙』 원서 대조 (운영자 요청, 2026-11-22) — 원서: The Pa-Auk Tawya Sayadaw, The Workings of Kamma (Second Revised Edition, PDF by PAMC Singapore 03/2018, 422쪽)
#   sh tools/parallel/run_dl0034.sh [원서.pdf]   — 원서 PDF 를 주면 원서 글부터 다시 뽑음
#   --move: 한국어판이 표 풀이 상자를 다른 자리에 실은 곳 — 원서 문단 번호(en_dl0034_2018.py 결과 기준, 원서 글을 다시 뽑으면 확인):
#     1176-1191 = 'Notes for Table 5a' ~ 'First Mental Process in One Life'(53~54쪽) → 'In the hells…'(51쪽) 앞,
#     4810 = 표 1e 풀이 'Even though they are the result…'(341쪽) → 'Notes for Table 5e'(339쪽) 앞
#   --fnpin: 각주 짝을 하나씩 읽고 바로잡은 것 (원서 각주 번호, e 는 미주 — 예 e18 = 미주 18)
#   한국어판 법보시 쪽·한국어 번역 허가서·약어표·일러두기·번역 후기·Source References(그림)는 짝짓기에서 뺌.
set -e
P=tools/out/parallel/DL-0034.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0034_2018.py "$1"; fi
set --
[ -f tools/parallel/dl0034_spins.txt ] && while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --spin "$l";; esac; done < tools/parallel/dl0034_spins.txt
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0034_heads.txt
python3 tools/parallel/align.py DL-0034 en "$P" "$@" \
  --title "The Workings of Kamma (Second Revised Edition)" --by "The Pa-Auk Tawya Sayadaw" \
  --source "The Workings of Kamma (Second Revised Edition), © 2009, 2012, 2017, published as a gift, in the public domain — PDF by PAMC (Singapore) 03/2018" \
  --ko-skip '^\*\*이 책은 미얀마 파아옥|^## 제목 차례\[요약\]' \
  --ko-skip '^## 인용 문헌/경전 약어표|^## I\. 차꼬경' \
  --ko-skip '^## 번역 후기|^## 부록 1' \
  --ko-skip '^## Source References|' \
  --pin "2:0=@© 2009, 2012, 2017" --pin "=@Title: The Workings" --pin "3:0+3:1=@Cover Illustration:" \
  --pin "18:0+18:1=@I ―'THE CLOG-BOUND" --seg "18:0+18:1=@I ―'THE CLOG-BOUND" \
  --fnpin 2=2 --fnpin 1= --fnpin 36=e18 --fnpin 69=66 --fnpin 70=e51 --fnpin 119=137 --fnpin 122=140 --fnpin 123=143 --fnpin 124=144 --fnpin 157=e95 --fnpin 200=e128 --fnpin 328=403 --fnpin 435=520 --fnpin 575=761 --fnpin 719=e311 --fnpin 720=e313 --fnpin 721=e315 --fnpin 722=316 --fnpin 739= --fnpin 265= --fnpin 325= --fnpin 409= --fnpin 610= --fnpin 531= --fnpin 137= --fnpin 118=e77 --fnpin 121=118 --fnpin 218=252 --fnpin 406=489 --fnpin 120= --fnpin 155= --fnpin 250= --fnpin 253= --fnpin 567= --fnpin 724= --fnpin 233=280 --fnpin 234=e140 \
  --move "1176-1191>1166" --move "4810-4810>4791" \
  --gl-start '^용어 풀이 없음$' --toc --ko-short 7 $ALIGN_EXTRA
