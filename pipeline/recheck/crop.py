# python3 crop.py SID n:x0,y0,x1,y1 ...  -> /tmp/x/fix.jpg (렌더된 미리보기에서 잘라 보기)
import sys
from PIL import Image
sid=sys.argv[1]; ims=[]
for a in sys.argv[2:]:
    n,b=a.split(':'); n=int(n); b=list(map(int,b.split(',')))
    im=Image.open(f'/tmp/pv/{sid}/{(n+1)//2:02d}.jpg'); off=0 if n%2 else 458
    ims.append(im.crop((b[0],b[1]+off,b[2],b[3]+off)))
W=sum(i.width for i in ims)+6*len(ims);H=max(i.height for i in ims);s=Image.new('RGB',(W,H),'white');x=0
for i in ims: s.paste(i,(x,0)); x+=i.width+6
s.save('/tmp/x/fix.jpg',quality=90)
