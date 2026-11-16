#!/bin/sh
# DL-0014 원서 대조 다시 만들기 (운영자 요청, 2026-11-17 — DL-0006 처럼 속표지·예경문·차례·끝 부분을 손으로 바로잡음)
#   sh tools/parallel/run_dl0014.sh Awareness.Alone.Is.Not.Enough.English.pdf   (개정 2판 2010)
set -e
python3 tools/parallel/en_dl0014_2010.py "$1"
python3 tools/parallel/align.py DL-0014 en tools/out/parallel/DL-0014.en.paras.json \
  --title "Awareness Alone Is Not Enough — Questions & Answers with Ashin Tejaniya" --by "Ashin Tejaniya" \
  --source "Second, revised edition May 2010 · Auspicious Affinity (Malaysia) · https://ashintejaniya.org/books-awareness-is-not-enough" \
  --gl-end '^옮긴이 \|' \
  --pin "1:0=" --pin "1:1=@AWARENESS ALONE IS NOT ENOUGH+@Questions & Answers" --pin "1:2=" \
  --pin "2:0=@Namo Tassa" --pin "2:1=@Homage to Him" \
  --pin "3:1+3:2+3:3=" \
  --pin "4:0=@Acknowledgements" --pin "4:4=@Ashin Tejaniya" --pin "5:0=@We Practise Because" \
  --pin "6:0=@Table of Contents"
