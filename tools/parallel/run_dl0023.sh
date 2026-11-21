#!/bin/sh
# 『법구경 이야기』 1~3권(DL-0023·0024·0025) 원서 대조 (운영자 요청, 2026-11-21)
#   원서: The Dhamma Verses Commentary — E W Burlingame(1921, Public Domain)·Ānandajoti Bhikkhu 개정 번역(August 2024), Ancient Buddhist Texts
#   sh tools/parallel/run_dl0023.sh 원서.pdf [DL-0023 DL-0024 DL-0025]
#   원서 PDF 를 안 주면 tools/out/parallel/<ID>.en.paras.json 을 그대로 씀.
#   한국어판 앞쪽(여는 글·목차·약어·일러두기·1권 해제)과 3권 부록·찾아보기·역자후기·참고 문헌, 1·2권 판권지는 짝짓지 않음.
#   장 표지 쪽(^^ 제N장 / :: … Vagga)도 짝짓지 않음.
set -e
if [ -n "$1" ] && [ -f "$1" ]; then python3 tools/parallel/en_dl0023.py "$1"; shift; fi
BOOKS=${*:-DL-0023 DL-0024 DL-0025}
for B in $BOOKS; do
  P=tools/out/parallel/$B.en.paras.json
  set --
  while IFS= read -r l; do set -- "$@" "$l"; done <<EOT
$(python3 tools/parallel/pins_dl0023.py $B)
EOT
  case $B in
    DL-0025) BACK='^\^\^ 부록$|' ;;
    *) BACK='^\*\*법구경 이야기 [123]\*\*$|' ;;
  esac
  python3 tools/parallel/align.py $B en "$P" "$@" \
    --title "The Dhamma Verses Commentary" --by "E W Burlingame, Ānandajoti Bhikkhu" \
    --source "Ancient Buddhist Texts (2024, Public Domain)" \
    --gl-start '^NO-GLOSSARY$' --ko-join --ko-skip '.|^## 제[0-9]+장' --ko-skip "$BACK" \
    --ko-none '^\^\^ 제[0-9]+장' --ko-none '^:: [A-Za-zĀ-ž ]*[Vv]agga$' \
    --fn-cost 9 --base 0.2 $ALIGN_EXTRA
done
