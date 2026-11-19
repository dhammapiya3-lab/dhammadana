#!/bin/bash
# pairs.sh SID  -> /tmp/x/t*.jpg grid pairs + boxes list
B=${B:-After-Awakening}; python3 /home/claude/sb/pipeline/recheck/grid.py $B $1
rm -f /tmp/x/t*.jpg
python3 - $1 $B <<'P'
import sys,glob,json
from PIL import Image
sid=sys.argv[1]; fs=sorted(glob.glob(f'/tmp/x/{sid}/*.jpg'))
for k in range(0,len(fs),2):
  pr=[Image.open(f) for f in fs[k:k+2]];s=Image.new('RGB',(800,458*len(pr)),'white')
  for j,x in enumerate(pr): s.paste(x,(0,458*j))
  s.save(f'/tmp/x/t{k//2+1}.jpg',quality=85)
d=json.load(open(f'/home/claude/sb/data/ocr/{sys.argv[2]}/{sid}.json'))
for n,p in enumerate(d,1):
  for i,b in enumerate(p['boxes']): print(n,i,b['seed'],b['en'][:200])
P
