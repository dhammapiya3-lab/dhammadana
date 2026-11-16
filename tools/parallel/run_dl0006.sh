#!/bin/sh
# DL-0006 원서 대조 다시 만들기 (운영자 요청, 2026-11-17): 원서 글 뽑기 → 짝짓기 + 손으로 정한 짝(--pin)
#   sh tools/parallel/run_dl0006.sh Kamma-at-death-and-rebirth.pdf
set -e
python3 tools/parallel/en_dl0006.py "$1"
P=82; C=83
python3 tools/parallel/align.py DL-0006 en tools/out/parallel/DL-0006.en.paras.json \
  --title "KAMMA AT DEATH AND REBIRTH" --by "Sayadaw Dr. Nandamālābhivaṃsa" \
  --pin "1:0=@KAMMA AT DEATH+@Sayadaw Dr. Nandamālābhivaṃsa" \
  --pin "2:0+2:1+2:2=" \
  --pin "3:0=@Note to readers" --pin "3:1=@Kamma at Death and Rebirth is" --pin "3:2=@The compiler" \
  --pin "4:0+4:1+4:2+4:3=" \
  --pin "5:0=@Contents" \
  --pin "8:1=@Because of his excellent" --pin "8:2=@Sayadaw Dr. Nandamᾱlᾱbhivaṃsa, born" \
  --pin "10:0=@Acknowledgement" \
  --pin "$P:0+$P:1+$P:2+$P:3+$P:4=" \
  --pin "$C:0+$C:4+$C:5+$C:6+$C:7+$C:8+$C:9=" \
  --fnpin "40=33" \
  --pin "$C:1=@First edition+@Published by+@© Abhidhamma" --pin "$C:2+$C:3=@For free distribution"
