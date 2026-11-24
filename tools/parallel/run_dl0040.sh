#!/bin/sh
# DL-0040『위빠싸나 성자 아짠 문』 원서 대조 (운영자 요청, 2026-11-24) — 원서: The Venerable Phra Acharn Mun Bhuridatta Thera,
#   Meditation Master (Phra Acharn Maha Boowa Ñāṇasampanno 엮음, M. Siri Buddhasukh 영역 1976 — 2판(1982)을 옮겨 적은 전자판 2002)
#   sh tools/parallel/run_dl0040.sh [원서.pdf]   — 원서 PDF 를 주면 원서 글부터 다시 뽑음
#   한국어판에만 있는 글: 속표지 뒤 역자 소개·역자 서문·차례, 장마다 첫머리 시(^^ N장 다음 문단)·'## 제N장' 줄, 판권지·명상원 안내.
#   원서에만 있는 글: Writer's Note·Translator's Preface·Transcribers' Note·차례(Contents).
#   제목 짝은 tools/parallel/dl0040_heads.txt(--pin·--seg), 문장 손 짝은 tools/parallel/dl0040_spins.txt(--spin).
set -e
P=tools/out/parallel/DL-0040.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0040.py "$1"; fi
set --
while IFS= read -r l; do case "$l" in \#*|'') ;; *) l=${l%%	*}; set -- "$@" --pin "$l" --seg "$l";; esac; done < tools/parallel/dl0040_heads.txt
while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --pin "$l";; esac; done < tools/parallel/dl0040_none.txt
if [ -f tools/parallel/dl0040_spins.txt ]; then
  while IFS= read -r l; do case "$l" in \#*|'') ;; *) set -- "$@" --spin "$l";; esac; done < tools/parallel/dl0040_spins.txt
fi
python3 tools/parallel/align.py DL-0040 en "$P" "$@" \
  --title "The Venerable Phra Acharn Mun Bhuridatta Thera, Meditation Master" --by "Phra Acharn Maha Boowa Ñāṇasampanno (trans. M. Siri Buddhasukh)" \
  --source "The Venerable Phra Acharn Mun Bhuridatta Thera, Meditation Master (English translation 1976, 2nd printing 1982 — electronic transcription 2002)" \
  --pin "1:0+1:1=0+1" --pin "1:2=2" --pin "1:3+1:4=" --pin "=3-202" \
  --ko-skip '^역자 不遠|^프라 아짠 문\(Phra Acharn Mun, 1870' \
  --pin "13:0=203" --seg "13:0=203" --move "1198-1198>393" --move "394-412>415" --move "1404-1404>1392" --move "1405-1405>1395" --move "1449-1449>1447" --move "1450-1450>1454" --move "873-888>806" --move "432-433>889" --move "787-787>700" --move "788-788>714" --move "1278-1278>960" --pin "=1197" \
  --pin "15:0+15:1=" --pin "16:0=" --pin "45:0+45:1=" --pin "46:0=" --pin "123:0+123:1=" --pin "124:0=" \
  --pin "153:0+153:1=" --pin "264:0+264:1=" --pin "265:0=" --pin "279:0+279:1=" --pin "280:0=" \
  --pin "302:0=1596" --seg "302:0=1596" \
  --ko-skip '^:: PDF 무상 배포용|' --pin '308:0=' --ko-short 7 --fnpin 12= $ALIGN_EXTRA
