#!/bin/sh
# DL-0010 원서 대조 다시 만들기 (운영자 요청, 2026-11-18): 미얀마어 원서 글(옮겨 적은 tools/parallel/dl0010_my/) → 짝짓기 + 손으로 정한 짝
#   sh tools/parallel/run_dl0010.sh
set -e
python3 tools/parallel/my_dl0010.py
python3 tools/parallel/align.py DL-0010 my tools/out/parallel/DL-0010.my.paras.json --toc \
  --title "သဘောထားမှန်မှ အားထုတ်ပါ" --by "အရှင်တေဇနိယ (ရွှေဥမင်)" \
  --pin "1:0+1:1+1:2=" \
  --pin "2:0+2:1+2:2=@နမောတဿ+@ဘဂဝတော+@အရဟတော+@သမ္မာသမ္ဗုဒ္ဓဿ+@နမော —" \
  --pin "3:1+4:0+4:1+4:2+4:3+5:0+5:1=" \
  --pin "7:0=@အမှာစာ" --pin "7:1=@ဤတရားစာအုပ်သည်+@အရှင်တေဇနိယ" \
  --ko-skip '^## 빨리어 용어 해설|'
