#!/bin/sh
# DL-0013 원서 대조 다시 만들기 (운영자 요청, 2026-11-17 — DL-0006 처럼 속표지·차례·끝 부분을 손으로 바로잡음)
#   sh tools/parallel/run_dl0013.sh Defilements_V1.1.pdf
set -e
python3 tools/parallel/en_dl0013.py "$1"
python3 tools/parallel/align.py DL-0013 en tools/out/parallel/DL-0013.en.paras.json --toc \
  --title "Don’t Look Down On The Defilements — They Will Laugh At You" --by "Ashin Tejaniya" --source "Defilements_V1.1.pdf (revised edition, Sept 2011)" \
  --gl-start '^\*\*깜마\[' --gl-end '^- 이 세상에' \
  --pin "3:0=@Don’t Look Down+@ASHIN TEJANIYA" \
  --pin "5:0=@NAMO TASSA" --pin "5:1+5:2=@Homage to Him"
