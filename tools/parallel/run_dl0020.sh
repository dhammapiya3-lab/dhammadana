#!/bin/sh
# DL-0020『팔정도』 원서 대조 (운영자 요청, 2026-11-19) — 원서: Bhikkhu Bodhi, The Noble Eightfold Path (BPS Wheel 308–311, 2판 1994, 재인쇄 2006)
#   sh tools/parallel/run_dl0020.sh [wh308_Bodhi_Noble-Eightfold-Path.pdf]
#   원서 PDF 를 주면 원서 글부터 다시 뽑음 (https://buddhistuniversity.net/content/booklets/noble-eightfold-path_bodhi)
#   한국어판 1쪽 속표지·일러두기·저자 소개·〈고요한소리〉 안내~판권지는 짝 없음, 3쪽 영어 원서 정보 ↔ 원서 속표지·판권, 차례 ↔ Contents
set -e
P=tools/out/parallel/DL-0020.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0020.py "$1"; fi
set --
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0020_heads.txt
python3 tools/parallel/align.py DL-0020 en "$P" --toc "$@" \
  --title "The Noble Eightfold Path: The Way to the End of Suffering" --by "Bhikkhu Bodhi" \
  --source "wh308_Bodhi_Noble-Eightfold-Path.pdf (Buddhist Publication Society, Wheel 308–311, 2nd ed. 1994, reprinted 2006)" \
  --ko-skip '^## 〈고요한소리〉는|' \
  --pin "1:0+1:1+1:2+1:3=" --pin "4:0+4:1=" --pin "233:0+233:1=" \
  --pin "3:0=@The Noble Eightfold Path+@The Way to the End~1" --pin "3:1=@by+@Bhikkhu Bodhi~1" \
  --pin "3:2=@Buddhist Publication Society+@The Wheel Publication+@First edition+@Copyright+@ISBN" \
  --pin "5:0=@Contents" --pin "10:1=@Bhikkhu Bodhi~2" \
  --pin "236:1=@I. General" --pin "236:5=@II. Right View" --pin "237:0=@III. Right Intention" --pin "237:4=@IV. Right Speech" \
  --pin "237:8=@V. Right Effort" --pin "238:0=@VI. Right Mindfulness" --pin "238:5=@VII. Right Concentration" \
  --move "473-473>472" --move "476-476>479" --move "481-481>483" \
  --pin "236:2=@Nyanatiloka Thera. The Word" --pin "236:3=@Ledi Sayadaw. The Noble" --pin "236:4=@Piyadassi Thera. The Buddha’s Ancient" \
  --pin "236:6=@Nyanatiloka Thera. Karma" --pin "236:7=@Story, Francis" --pin "236:8=@Ñāṇamoli, Bhikkhu. The Discourse" --pin "236:9=@Wijesekera" \
  --pin "237:1=@Nyanaponika Thera. The Four Sublime" --pin "237:2=@Ñāṇamoli Thera. The Practice" --pin "237:3=@Prince, T." \
  --pin "237:5=@Bodhi, Bhikkhu. Going" --pin "237:6=@Nārada Thera" --pin "237:7=@Vajirañāṇavarorasa" \
  --pin "237:9=@Nyanaponika Thera. The Five Mental" --pin "237:10=@Piyadassi Thera. The Seven" --pin "237:11=@Soma Thera. The Removal" \
  --pin "238:1=@Nyanaponika Thera. The Heart" --pin "238:2=@Nyanaponika Thera. The Power" --pin "238:3=@Nyanasatta Thera" --pin "238:4=@Soma Thera. The Way" \
  --pin "238:6=@Buddhaghosa" --pin "238:7=@Khantipālo" --pin "238:8=@Ledi Sayadaw. A Manual" --pin "238:9=@Nyanatiloka Thera. The Buddha’s Path" \
  --pin "238:10=@Solé-Leris" --pin "238:11=@Vajirañāṇa, Paravahera"
