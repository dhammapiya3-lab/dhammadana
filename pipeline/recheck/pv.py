import json,sys
sys.path.insert(0,'/home/claude/sb/pipeline')
from render import render
from PIL import Image
def pv(S,ns,out='/tmp/t.jpg',book='Jataka'):
    pages=json.load(open(f'/home/claude/sb/ko/{book}/{S}.json')); ims=[]
    for n in ns:
        im=render(f'/home/claude/rev/{book}/{S}/{n:02d}.jpg', pages[n-1]['boxes']); ims.append(im.resize((800,round(im.height*800/im.width))))
    sh=Image.new('RGB',(800,sum(i.height for i in ims)),'white'); y=0
    for i in ims: sh.paste(i,(0,y)); y+=i.height
    sh.save(out,quality=80)
