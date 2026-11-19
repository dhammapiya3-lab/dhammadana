#!/bin/sh
# DL-0019『보시』 원서 대조 (운영자 요청, 2026-11-19) — 원서: Bhikkhu Bodhi (ed.), DĀNA: The Practice of Giving (BPS Wheel 367–9, BPS Online Edition 2011)
#   sh tools/parallel/run_dl0019.sh [wh367_Bodhi_Dana--The-Practice-of-Giving.pdf]
#   원서 PDF 를 주면 원서 글부터 다시 뽑음 (https://buddhistuniversity.net/content/booklets/dana_bodhi-et-al)
#   한국어판 1쪽 속표지·일러두기·〈고요한소리〉 안내~판권지는 짝 없음, 3쪽 영어 원서 정보 ↔ 원서 속표지·판권, 차 례 ↔ Contents
set -e
P=tools/out/parallel/DL-0019.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0019.py "$1"; fi
set --
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0019_heads.txt
python3 tools/parallel/align.py DL-0019 en "$P" --toc "$@" \
  --title "DĀNA: The Practice of Giving" --by "Bhikkhu Bodhi (ed.)" \
  --source "wh367_Bodhi_Dana--The-Practice-of-Giving.pdf (Buddhist Publication Society, Wheel 367–9, BPS Online Edition 2011)" \
  --ko-skip '^## 〈고요한소리〉는|' \
  --pin "1:0+1:1+1:2=" --pin "2:0+2:1=" \
  --pin "3:0=@DĀNA+@Selected Essays" --pin "3:1=@Edited by+@Bhikkhu Bodhi~1" \
  --pin "3:2=@The Wheel Publication+@First published+@ISBN+@BPS Online" --pin "3:3=@Buddhist Publication Society" \
  --pin "5:0=@Contents" --pin "81:3=@Dhp 53" --pin "103:1=" \
  --pin "=@About the Contributors+@Notes" --fnpin "25=6"
