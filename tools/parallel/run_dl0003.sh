#!/bin/sh
# DL-0003 원서 대조 다시 만들기 (운영자 요청, 2026-11-18): 미얀마어 원서 글(옮겨 적은 tools/parallel/dl0003_my/) → 짝짓기 + 손으로 정한 짝
#   sh tools/parallel/run_dl0003.sh
set -e
python3 tools/parallel/my_dl0003.py
python3 tools/parallel/align.py DL-0003 my tools/out/parallel/DL-0003.my.paras.json --toc \
  --title "ချမ်းသာကို ရှာဖွေခြင်း" --by "ဦးရွှေအောင်" \
  --pin "1:0+1:1+1:2=" --pin "2:0+2:1=" --pin "2:2=@ဦးရွှေအောင် [" \
  --pin "2:3=@ပဲခူးတိုင်း+@ဖလေးရွာ အလယ်တန်း+@၁၉၃၁ တွင်" --pin "2:4=@ထင်ရှားသော စာအုပ်+@၁၉၉၄ ခု" \
  --pin "3:0+3:1=" --pin "4:0=7" --pin "4:1=8" --pin "4:2=" \
  --pin "5:0=@မာတိကာ" --pin "6:0+7:0+8:0+9:0+10:0=" \
  --pin "12:0+12:1+12:2+12:3+12:4=" --pin "14:0+14:1=" \
  --ko-skip '^## 행복을 찾아서 \(우 쉐아웅|'
