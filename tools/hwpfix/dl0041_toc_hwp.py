"""『테라와다 불교의 신행생활』(DL-0041) 교정본 한글 파일의 차례 쪽 번호 고치기 (운영자 요청, 2026-11-23).
운영자가 준 PDF(교정본을 인쇄한 것)에서 장 제목 쪽을 확인: 16. 우안거 144→146, 17. 까티나 가사 법요식 151→153.
쓰는 법: python3 dl0041_toc_hwp.py 입력.hwp 출력.hwp no|blue"""
import sys,struct,zlib,olefile
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hwplib import *; from align import hwp_chars; from rebuild import apply; from cfb import write_cfb
from paras import load
src,out,blue=sys.argv[1],sys.argv[2],sys.argv[3]=='blue'
FIX=[('雨安居) … 144','144','146'),('까티나 가사 법요식 … 151','151','153')]
rs=load(src); H=hwp_chars(rs); S=''.join(c for _,_,c in H)
DEL=set(); INS={}; BLUE=set(); INSBLUE={}
for ctx,old,new in FIX:
    k=S.find(ctx); assert k>=0 and S.find(ctx,k+1)<0,ctx
    k=k+len(ctx)-len(old)
    for i,(a,b) in enumerate(zip(old,new)):
        if a!=b: DEL.add(k+i); INS[k+i]=b; INSBLUE[k+i]=True
bm=None
if blue:
    o=olefile.OleFileIO(src); di=recs(rd(o,'DocInfo')); o.close()
    idm=[i for i,r in enumerate(di) if r[0]==17][0]; n=struct.unpack('<%di'%(len(di[idm][2])//4),di[idm][2])[9]//2
    bm={k:n+k for k in range(n)}
res,ch=apply(rs,H,DEL,INS,BLUE,INSBLUE,blue_map=bm)
def comp(b):
    c=zlib.compressobj(9,zlib.DEFLATED,-15); return c.compress(b)+c.flush()
write_cfb(src,out,{'BodyText/Section0':comp(pack(res))})
print(out,'고친 문단',ch)
