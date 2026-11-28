# 확인할 줄 묶음 그림: python3 rv.py <목록.json> <시작> <개수>  → /tmp/rv.png + 줄 글
import json,sys,fitz
from PIL import Image
L=json.load(open(sys.argv[1])); a=int(sys.argv[2]); n=int(sys.argv[3]); d=fitz.open('src.pdf')
ims=[]
for k,(pdf,y0) in enumerate(L[a:a+n]):
  l=[x for x in json.load(open(f'ocrC/{pdf-1:03d}.json'))['lines'] if x['y0']==y0][0]
  p=d[pdf-1].get_pixmap(dpi=140,colorspace=fitz.csGRAY,clip=fitz.Rect(l['x0']*72/300-3,l['y0']*72/300-4,l['x1']*72/300+3,l['y1']*72/300+3))
  ims.append(Image.frombytes('L',(p.width,p.height),p.samples)); print(a+k,pdf,y0,l['t'])
W=max(x.width for x in ims);H=sum(x.height+5 for x in ims);c=Image.new('L',(W,H),255);y=0
for x in ims: c.paste(x,(0,y));y+=x.height+5
c.save('/tmp/rv.png')
