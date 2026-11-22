#!/usr/bin/env python3
"""『테라와다 불교의 신행생활』(DL-0041) 한글 파일 — 단락 옮기기·소제목 셋·남은 빈칸 3곳 (2026-11-23).
  python3 tools/hwpfix/dl0041_move_hwp.py <run.py 로 고친 교정본.hwp> <결과.hwp> no|blue   (blue: 파란색 판에 — 옮긴 문단·새 소제목을 파란 글자로)
run.py 는 글자 고침만 옮기고 단락 옮기기(dl0041_move.py)는 못 하므로, 문단 기록(PARA_HEADER 묶음)을 통째로 옮기고 (3) 거주처 제목 문단을 복제해 소제목을 만듦."""
import sys,struct,zlib,copy,olefile,json
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hwplib import *; from align import hwp_chars; from rebuild import apply; from cfb import write_cfb
from paras import paras, ptext
src,out,blue=sys.argv[1],sys.argv[2],sys.argv[3]=='blue'
o=olefile.OleFileIO(src); rs=recs(rd(o,'BodyText/Section0')); o.close()
P=paras(rs); T=[ptext(rs,s,e) for s,e in P]
def find(k,start=0):
    r=[i for i,t in enumerate(T) if k in t and i>=start]; assert r,k; return r[0]
hA=find('(3) 거주처(rukkhamūlasenāsana)'); hB=find('이제 사원을 건설한 목적에 대해서')
h4=find('(4) 의약품(pūtimuttabhesajja)'); ms=find('테라와다 불교의 사원은 제대로 된 규칙'); me=find('사원이 유지 운영해 나갈 수가 있게 되는 것입니다.',ms)
assert T[h4-1]=='' and T[hA-1]=='' and T[me].rstrip('[b]').endswith('것입니다.'),(T[h4-1],T[me][-30:])
assert hA<hB<h4<ms<=me
def grp(i): s,e=P[i]; return [list(r) for r in rs[s:e]]
for i in range(ms,me+1):
    n=struct.unpack_from('<I',rs[P[i][0]][2],0)[0]; assert not n&0x80000000
head=grp(hA); blank=grp(hA-1)
NEW={'H1':'1) 사원 구성과 좌와구(坐臥具)','H2':'2) 사원 건립 목적과 과정','H3':'3) 테라와다 불교에서의 사원 운영 방침'}
order=[]; tags=[]
def add(g,tag=None): order.append(g); tags.append(tag)
for i in range(len(P)):
    if ms<=i<=me: continue
    if i==hB: add(copy.deepcopy(blank)); add(copy.deepcopy(head),'H2')
    if i==h4:
        add(copy.deepcopy(head),'H3')
        for j in range(ms,me+1): add(grp(j),'MV')
        add(copy.deepcopy(blank))
    add(grp(i))
    if i==hA: add(copy.deepcopy(head),'H1')
pre=[list(r) for r in rs[:P[0][0]]]
nrs=pre[:]; starts=[]
for g in order: starts.append(len(nrs)); nrs.extend(g)
nrs=[tuple(r) for r in nrs]
H=hwp_chars(nrs)
DEL=set(); INS={}; BLUE=set(); INSBLUE={}
byrec={}
for j,(ri,wi,ch) in enumerate(H): byrec.setdefault(ri,[]).append(j)
for st,tag in zip(starts,tags):
    if tag in NEW:
        ti=st+1; assert nrs[ti][0]==67
        cs=[j for j in byrec[ti] if H[j][1] is not None and H[j][2]!='\n']
        for j in cs: DEL.add(j)
        INS[cs[0]]=NEW[tag]; INSBLUE[cs[0]]=True
# small fixes by string search over H text
S=''.join(c for _,_,c in H)
def at(sub,off):
    k=S.find(sub); assert k>=0 and S.find(sub,k+1)<0,sub; return k+off
k=at('saṭṭhivihāre',6); INS[k]=' '; INSBLUE[k]=True
k=at('부처님들이)　 vadanti',6); DEL.add(k); BLUE.add(k+1)
k=at('그들이\xa0 행복하기를',3); DEL.add(k); BLUE.add(k+1)
bm=None
if blue:
    o=olefile.OleFileIO(src); di=recs(rd(o,'DocInfo')); o.close()   # 파란색 판은 글자 모양이 두 배(원래 n + 파란 쌍둥이 n)
    idm=[i for i,r in enumerate(di) if r[0]==17][0]; n=struct.unpack('<%di'%(len(di[idm][2])//4),di[idm][2])[9]//2
    bm={k:n+k for k in range(n)}
res,ch=apply(nrs,H,DEL,INS,BLUE,INSBLUE,blue_map=bm)
if blue:   # 옮긴 문단은 통째로 파란 글자
    for st,tag in zip(starts,tags):
        if tag=='MV':
            ci=st+2; assert res[ci][0]==68
            cs=res[ci][2]; runs=[struct.unpack_from('<II',cs,k*8) for k in range(len(cs)//8)]
            res[ci][2]=b''.join(struct.pack('<II',p,bm.get(s,s)) for p,s in runs)
def comp(b):
    c=zlib.compressobj(9,zlib.DEFLATED,-15); return c.compress(b)+c.flush()
write_cfb(src,out,{'BodyText/Section0':comp(pack(res))})
print(out,'문단',len(P),'→',len(order),'고친 문단',ch)
