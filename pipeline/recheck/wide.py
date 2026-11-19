import sys,glob
from PIL import Image
sid=sys.argv[1]; fs=sorted(glob.glob(f'/tmp/pv/{sid}/*.jpg'))
ims=[]
for f in fs:
  im=Image.open(f)
  for y in range(0,im.height,458): ims.append(im.crop((0,y,800,y+450)))
import os
for f in glob.glob('/tmp/x/w*.jpg'): os.remove(f)
for k in range(0,len(ims),4):
  g=ims[k:k+4]; s=Image.new('RGB',(1600,900),'white')
  for j,x in enumerate(g): s.paste(x,((j%2)*800,(j//2)*450))
  s.save(f'/tmp/x/w{k//4+1}.jpg',quality=80)
print(len(ims))
