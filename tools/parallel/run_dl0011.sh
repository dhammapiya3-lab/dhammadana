#!/bin/sh
# DL-0011 원서 대조 다시 만들기 (운영자 요청, 2026-11-17 — DL-0006 처럼 속표지·예경문·저자 소개·끝 부분을 손으로 바로잡음)
#   sh tools/parallel/run_dl0011.sh [Dhamma-Everywhere-V1.0.Ilustrated.pdf]
#   원서 PDF 를 주면 원서 글부터 다시 뽑고, 없으면 지금 짝 자료(content/parallel/DL-0011.en.json)의 원서 문단을 그대로 씀
set -e
P=tools/out/parallel/DL-0011.en.paras.json
if [ -n "$1" ]; then python3 tools/parallel/en_dl0011.py "$1"
elif [ ! -f "$P" ]; then python3 -c "
import json; d = json.load(open('content/parallel/DL-0011.en.json')); o = d['orig']
for p in o:
    if p['k'] == 'gl': p['term'], _, p['def'] = p['t'].partition('\n')
json.dump(o, open('$P', 'w'), ensure_ascii=False, indent=0)"
fi
python3 tools/parallel/align.py DL-0011 en "$P" --toc \
  --title "Dhamma Everywhere: Welcoming Each Moment With Awareness+Wisdom" --by "Ashin Tejaniya" \
  --source "Dhamma-Everywhere-V1.0.Ilustrated.pdf (Auspicious Affinity edition, May 2012)" \
  --gl-start '^\*\*고짜라' --gl-end '^## 한국 독자들에게' --gl-nl \
  --pin "1:0=@Namo Tassa" --pin "1:1=@Homage to Him" \
  --pin "2:0=0+1" \
  --pin "3:0+3:2+3:3=" \
  --pin "4:0=@Acknowledgements" --pin "4:7=8"
