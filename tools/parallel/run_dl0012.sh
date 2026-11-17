#!/bin/sh
# DL-0012『위빠사나 명상』 원서 대조 (운영자 요청, 2026-11-17) — 원서: Chanmyay Sayadaw, Vipassanā Meditation – Lectures on Insight Meditation
#   sh tools/parallel/run_dl0012.sh [Chanmyay_Lectures.pdf]
#   원서 PDF 를 주면 원서 글부터 다시 뽑음
#   (2026-11-18: 한국어 본문의 넘친 각주·끊긴 • 항목을 고침 — tools/dl0012_bullet_join.py·dl0012_fn_overflow.py. 본문을 다시 만들면 핀 열쇠도 다시 맞춤)
#   145~146쪽 '명상하는 이의 다섯 기능(五根)'은 원서에 없음, 원서 84쪽 '• If you want to achieve something…' 은 한국어판에 없음
#   원서 각주 3(MN 61)은 한국어판 본문에 '(MN 61)'로 있어 각주 짝 없음
#   한국어판에만 있는 것(약어·출판 허가서·부록 2~6·역자 후기·역자에 대하여·법보시·판권지)은 짝 없음
set -e
P=tools/out/parallel/DL-0012.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0012.py "$1"; fi
python3 tools/parallel/align.py DL-0012 en "$P" --toc \
  --title "Vipassanā Meditation – Lectures on Insight Meditation" --by "Chanmyay Sayadaw (Ashin Janakābhivaṃsa)" \
  --source "Chanmyay_Lectures.pdf (Chanmyay Yeiktha Meditation Centre, 2017)" \
  --ko-skip '^## 부록 2|^## 저자에 대하여' --ko-skip '^## 역자에 대하여|' \
  --pin "1:0+1:1+1:2+1:3+1:4+1:5+1:6=" \
  --pin "2:0+2:1+2:2+2:3+2:4=" --pin "3:0+3:1=" \
  --pin "4:0=@Contents" \
  --pin "8:0+8:1+8:2=@Namo Tassa" \
  --pin "9:0=12" --pin "9:1=@Sudassam+@Attano+@Easily+@Hard indeed" \
  --pin "11:3=@Ashin Janakabhivamsa" \
  --pin "145:2+145:3+145:4+145:5+146:0=" --pin "143:7=@• Note sleepiness" \
  --pin "146:1=@Interview Sessions" --fnpin "=3"
