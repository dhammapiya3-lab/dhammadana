#!/bin/sh
# DL-0030『붓다의 일생』 원서 대조 (운영자 요청, 2026-11-22) — 원서: Bhikkhu Ñāṇamoli, The Life of the Buddha according to the Pāli Canon
#   (BPS Pariyatti Editions 2001, ©1972·1992 BPS — Pariyatti eBook PDF)
#   sh tools/parallel/run_dl0030.sh [원서.pdf]   — 원서 PDF 를 주면 원서 글부터 다시 뽑음
#   한국어판 1쪽 속표지 글·일러두기·지도·판권지는 짝 없음, 경전 출처 목록·찾아보기는 짝짓기에서 뺌(원서도 넣지 않음).
set -e
P=tools/out/parallel/DL-0030.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0030.py "$1"; fi
set --
[ -f tools/parallel/dl0030_spins.txt ] && while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --spin "$l";; esac; done < tools/parallel/dl0030_spins.txt
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0030_heads.txt
# 문단 경계만(짝은 문장마다): 70·71쪽 두 번째·세 번째 명지, 129쪽 마아라 게송 뒤
python3 tools/parallel/align.py DL-0030 en "$P" "$@" \
  --seg "71:0=@“When my concentrated mind was thus purified … I directed, I inclined my mind to the knowledge of exhaustion" \
  --seg "72:0=207" \
  --seg "129:1=412" \
  --seg "72:1=@**Narrator Two.** Now here is the description in terms of the structure" \
  --title "The Life of the Buddha according to the Pāli Canon" --by "Bhikkhu Ñāṇamoli" \
  --source "The Life of the Buddha (BPS Pariyatti Editions 2001, ©1972, 1992 Buddhist Publication Society)" \
  --ko-skip '^## ㄱ$|^E\. J\. 토마스' \
  --pin "1:0=" --pin "2:0+2:1+2:2+2:3=@The Life of the Buddha" \
  --pin "3:0=@The Life of The Buddha" --pin "3:1=@accordIng" --pin "3:2=@translation from" --pin "3:3=@selection of" \
  --pin "3:4=@and arrangement" --pin "3:5=@BhiKKhu" --pin "3:6=@Bps" --pin "3:7=@©1972+@Published by Buddhist+@First BPS" \
  --pin "=@Print ISBN" --pin "4:0+4:1+4:2+4:3=" \
  --pin "5:0=@Namo tassa" --pin "5:1=@Sabba-pāpassa" --pin "5:2=@To do no evil" --pin "5:3=@D. 14" \
  --pin "20:0=@Bhikkhu Ñ" --pin "21:0=" --pin "22:0=" --pin "309:3=" --pin "=@VOICES" --pin "=@12 THE DOCTRINE" \
  --pin "=@There are instances where the Commentaries" --pin "=@PRINCIPAL DATES" --pin "=@Event Date" --pin "712:2=@*Dates" --pin "=@BHIKKHU ÑĀṆAMOLI: A" --pin "715:0+715:1=" \
  --fnpin "170=12.20" --fnpin "181=14.2" --fnpin "28=11.7" \
  --toc --ko-short 7 --en-semi $ALIGN_EXTRA
python3 tools/parallel/dl0030_fixpairs.py   # 310쪽·90쪽 문장 짝 손질 (2026-11-28)
