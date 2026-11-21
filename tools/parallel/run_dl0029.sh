#!/bin/sh
# DL-0029『부처님, 그분 – 생애와 가르침』 원서 대조 (운영자 요청, 2026-11-21) — 원서: Piyadassi Thera, The Buddha: His Life and Teaching
#   (BPS Wheel No. 05, 1958·1961·1970·1990, BPS Online Edition 2008)
#   sh tools/parallel/run_dl0029.sh [원서.pdf]   — 원서 PDF 를 주면 원서 글부터 다시 뽑음
#   한국어판 속표지·일러두기·차례·예경문·장 번호 제목(Ⅰ~Ⅴ)은 짝 없음, 원서 속표지 ↔ 한국어 원서 속표지(2쪽),
#   원서 4쪽 맨 위 'The Buddha'(책 제목)는 짝 없음, 저자 소개~판권지·부록 지도·가계도는 짝짓기에서 뺌. 원서에는 차례가 없음.
set -e
P=tools/out/parallel/DL-0029.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0029.py "$1"; fi
set --
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --spin "$l";; esac; done < tools/parallel/dl0029_spins.txt
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0029_heads.txt
python3 tools/parallel/align.py DL-0029 en "$P" "$@" \
  --title "The Buddha: His Life and Teaching" --by "Piyadassi Thera" \
  --source "The Buddha His Life and Teaching (Buddhist Publication Society, The Wheel Publication No. 05, BPS Online Edition 2008)" \
  --ko-skip '^삐야닷시 스님 Piyadassi' \
  --pin "1:0+1:1+1:2+1:3+1:4=" --pin "3:0+3:1+3:2+3:3=" --pin "5:0+5:1=" \
  --pin "10:0=" --pin "42:0=" --pin "67:0=" --pin "103:0=" --pin "130:0=" \
  --pin "2:0+2:1=@The Buddha+@His Life and Teaching" --pin "2:2=@by+@Piyadassi Thera" --pin "2:3=@The Wheel Publication" \
  --pin "2:4+2:5+2:6=@Copyright+@BPS Online+@Digital Transcription" \
  --pin "=@The Buddha~2" --pin "=@Notes" \
  --fnpin "14=13" --fnpin "28=16" --fnpin "29=" --fnpin "46=29" --fnpin "95=50" --fnpin "100=56" --fnpin "107=" --fnpin "=61" --ko-short 7 $ALIGN_EXTRA
