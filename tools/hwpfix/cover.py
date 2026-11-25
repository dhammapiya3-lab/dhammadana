import sys,io,struct,zlib
sys.path.insert(0,'/home/claude/dhammadana/tools/hwpfix')
from hwplib import *
from cfb import write_cfb
from PIL import Image
src,img,outp=sys.argv[1:4]
def comp(b):
    c=zlib.compressobj(9,zlib.DEFLATED,-15); return c.compress(b)+c.flush()
im=Image.open(img).convert('RGB'); pw,ph=im.size
buf=io.BytesIO(); im.save(buf,'JPEG',quality=95,dpi=(120,120)); jpg=buf.getvalue()
o=olefile.OleFileIO(src); rs=recs(rd(o,'BodyText/Section0'))
# page size
PW,PH=struct.unpack('<2I',rs[6][2][:8])
gi=next(i for i,(t,l,b) in enumerate(rs) if t==71 and b[:4]==b' osg')
assert rs[gi+1][0]==76 and rs[gi+2][0]==85
# bin id
pic=bytearray(rs[gi+2][2]); binid=struct.unpack('<H',pic[71:73])[0]
name=[n for n in ['BinData/BIN%04X.%s'%(binid,e) for e in ('tmp','jpg','png','bmp')] if o.exists(n)][0]
o.close()
OW,OH=pw*75,ph*75                      # 원래 크기 (그림 점 × 75)
H=PH; W=round(PH*pw/ph)                # 쪽 높이에 맞춤, 가로 비율 그대로
X=(PW-W)//2
# CTRL_HEADER
g=bytearray(rs[gi][2])
a=struct.unpack('<I',g[4:8])[0]
def setb(a,s,w,v): return (a&~(((1<<w)-1)<<s))|(v<<s)
a=setb(a,0,1,0)      # 글자처럼 취급 끔
a=setb(a,3,2,0)      # 세로 기준: 종이
a=setb(a,5,3,0)
a=setb(a,8,2,0)      # 가로 기준: 종이
a=setb(a,10,3,0)
a=setb(a,13,1,0); a=setb(a,14,1,1)
a=setb(a,15,3,4); a=setb(a,18,2,2)   # 너비·높이 절대값
a=setb(a,21,3,3)     # 글 앞으로
g[4:8]=struct.pack('<I',a); g[8:12]=struct.pack('<i',0); g[12:16]=struct.pack('<i',X)
g[16:20]=struct.pack('<I',W); g[20:24]=struct.pack('<I',H)
g[28:36]=b'\0'*8     # 바깥 여백 0
# SHAPE_COMPONENT
s=bytearray(rs[gi+1][2])
s[20:24]=struct.pack('<I',OW); s[24:28]=struct.pack('<I',OH)
s[28:32]=struct.pack('<I',W); s[32:36]=struct.pack('<I',H)
s[42:46]=struct.pack('<i',W//2); s[46:50]=struct.pack('<i',H//2)
# matrices: count(2) at 50, translation 6 doubles at 52, scale at 100, rot at 148
off=52+48
sc=list(struct.unpack('<6d',s[off:off+48])); sc[0]=W/OW; sc[4]=H/OH
s[off:off+48]=struct.pack('<6d',*sc)
# PICTURE
pic[12:44]=struct.pack('<8i',0,0,OW,0,OW,OH,0,OH)
pic[44:60]=struct.pack('<4i',0,0,pw*75,ph*75)
rs[gi]=(rs[gi][0],rs[gi][1],bytes(g)); rs[gi+1]=(rs[gi+1][0],rs[gi+1][1],bytes(s)); rs[gi+2]=(rs[gi+2][0],rs[gi+2][1],bytes(pic))
# 이 문단 줄 높이를 보통으로 (그림이 글자처럼 차지하던 높이)
for j in range(gi-1,gi-6,-1):
    if rs[j][0]==69:
        L=bytearray(rs[j][2]); L[8:12]=struct.pack('<i',1000); L[12:16]=struct.pack('<i',1000); L[16:20]=struct.pack('<i',850); rs[j]=(69,rs[j][1],bytes(L)); break
write_cfb(src,outp,{'BodyText/Section0':comp(pack(rs)),name:comp(jpg)})
print('bin',name,'page',PW,PH,'pic',W,H,'x',X,'scale',sc[0],sc[4])
