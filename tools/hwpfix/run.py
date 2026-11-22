"""한글(HWP) 파일에 사이트 본문 교정을 그대로 옮기는 도구 (운영자 요청, 2026-11-21 — DL-0038 에서 처음 씀)

  python3 tools/hwpfix/run.py 원본.hwp 교정전본문.json 교정후본문.json 결과이름
  → 결과이름.hwp (교정본) + 결과이름_파란색.hwp (고친 곳을 파란 글자로)

교정 전 본문 = 본문 만드는 도구(pdf2text_<id>.py 등)를 교정 도구(<id>_fix.py) 앞까지만 돌린 content/texts/<ID>.json
(작업용 git worktree 에서), 교정 후 본문 = 지금 content/texts/<ID>.json.
① 교정 전 본문의 글자(빈칸·표시 빼고)를 한글 파일 글자와 맞대고(align.py) ② 교정 전→후 바뀐 곳(ops.py)을
한글 파일 자리로 옮겨 문단 글자·글자 모양 자리·줄 자리·문단 글자 수를 함께 고침(rebuild.py)
③ 파란색 판은 DocInfo 에 글자 모양마다 파란 글자 쌍둥이를 더해 고친 글자(빈칸만 고친 곳은 앞뒤 글자)에 씀
④ OLE(복합 파일)는 새로 짬(cfb.py — 다른 스트림·이름·CLSID·시각은 그대로, 크기가 바뀌어도 됨).
한글 파일 줄이 '엔터'로 나뉜 곳에 빈칸을 넣는 교정은 건너뜀(보고). 끝나면 고친 한글 파일 글자를 교정 후 본문과
다시 맞대어 글자·띄어쓰기가 모두 같은지 확인함. 한글 파일은 저장소에 올리지 않음."""
import sys,json,collections,bisect,zlib,struct,os
sys.path.insert(0,os.path.dirname(__file__))
from hwplib import *; from align import *; from ops import get_ops; from rebuild import apply; from cfb import write_cfb
src,b0,b1,outp=sys.argv[1:5]
B0=json.load(open(b0))['body']; B1=json.load(open(b1))['body']
ops=get_ops(B0,B1)
o=olefile.OleFileIO(src); rs=recs(rd(o,'BodyText/Section0')); di=recs(rd(o,'DocInfo')); o.close()
H=hwp_chars(rs)
A,miss=align(B0,H); print('맞대기에서 다른 곳:',miss)
keys=sorted(A)
DEL=set(); INS=collections.defaultdict(str); BLUE=set(); INSBLUE=collections.defaultdict(bool)
skipped=[]
def isspace_entry(j): return H[j][1] is not None and H[j][2]==' '
for s,e,r in ops:
    old=B0[s:e]
    mapped=[i for i in range(s,e) if i in A]
    li=bisect.bisect_left(keys,s); L=keys[li-1] if li>0 else None
    R=keys[bisect.bisect_left(keys,e)]
    gap=list(range(A[L]+1,A[R])) if L is not None else []
    rc=r.replace('**','').replace('°°','').replace('==','').replace('__','')
    if mapped:
        lo=A[mapped[0]]; hi=A[mapped[-1]]
        if old[:1].isspace():
            j=lo-1
            while j>(A[L] if L is not None else -1) and isspace_entry(j): j-=1
            lo=j+1
        if old[-1:].isspace():
            j=hi+1
            while j<A[R] and isspace_entry(j): j+=1
            hi=j-1
        span=range(lo,hi+1)
        brk=[j for j in span if H[j][1] is None or H[j][2]=='\n']
        if brk: skipped.append(('break in span',B0[max(0,s-10):e+10],''.join(H[j][2] for j in span))); continue
        for j in span: DEL.add(j)
        INS[lo]+=rc
        if not rc.strip(): BLUE.update(([A[L]] if L is not None else [])+[A[R]])
        else: INSBLUE[lo]=True
    else:
        o_ws=old.replace('**','').replace('°°','').replace('__','')
        if o_ws.strip()=='' and rc.strip()=='':
            if len(rc)>len(o_ws):   # insert space
                if not gap: INS[A[R]]+=rc; BLUE.update([A[L],A[R]])
                else: skipped.append(('space-ins, HWP has gap',B0[max(0,s-12):e+12],''.join(H[j][2] for j in gap)))
            else:                   # delete space
                sp=[j for j in gap if isspace_entry(j)]
                if sp and len(sp)==len(gap):
                    k=len(o_ws)-len(rc)
                    for j in sp[:k]: DEL.add(j)
                    BLUE.update([A[L],A[R]])
                elif not gap: pass
                else: skipped.append(('space-del, HWP gap',B0[max(0,s-12):e+12],''.join(H[j][2] for j in gap)))
        else:
            # insertion of content (or markup-only change)
            if not rc.strip(): skipped.append(('markup?',repr(old),repr(r))); continue
            # delete whitespace in gap if old had ws and new doesn't
            pos=A[R] if any(c.isspace() for c in B0[L+1:s]) else A[L]+1
            INS[pos]+=rc; INSBLUE[pos]=True
            if o_ws.strip()=='' and o_ws and not any(c.isspace() for c in rc):
                for j in gap:
                    if isspace_entry(j): DEL.add(j)
print('바뀐 곳',len(ops),'건너뜀',len(skipped))
for x in skipped: print('  건너뜀',x)
def comp(b):
    c=zlib.compressobj(9,zlib.DEFLATED,-15); return c.compress(b)+c.flush()
nrs,ch=apply(rs,H,DEL,INS,BLUE,INSBLUE)
write_cfb(src,outp+'.hwp',{'BodyText/Section0':comp(pack(nrs))})
idm=[i for i,r in enumerate(di) if r[0]==17][0]
cnt=list(struct.unpack('<%di'%(len(di[idm][2])//4),di[idm][2])); n=cnt[9]
csi=[i for i,r in enumerate(di) if r[0]==21]; assert len(csi)==n
twins=[]
for i in csi:
    b=bytearray(di[i][2]); struct.pack_into('<I',b,52,0x00FF0000); twins.append([21,di[i][1],bytes(b)])
cnt[9]=2*n
di2=[list(r) for r in di]; di2[idm][2]=struct.pack('<%di'%len(cnt),*cnt)
di2=di2[:csi[-1]+1]+twins+di2[csi[-1]+1:]
brs,_=apply(rs,H,DEL,INS,BLUE,INSBLUE,blue_map={k:n+k for k in range(n)})
write_cfb(src,outp+'_파란색.hwp',{'BodyText/Section0':comp(pack(brs)),'DocInfo':comp(pack(di2))})
# 확인
for f in (outp+'.hwp',outp+'_파란색.hwp'):
    o=olefile.OleFileIO(f); r2=recs(rd(o,'BodyText/Section0')); H2=hwp_chars(r2)
    A2,m2=align(B1,H2); k2=sorted(A2); dif=0
    for a,b in zip(k2,k2[1:]):
        if any(c.isspace() for c in B1[a+1:b])!=any(c[2].isspace() for c in H2[A2[a]+1:A2[b]]): dif+=1
    print(f,'고친 문단',ch,'교정 후 본문과 다른 글자',m2,'띄어쓰기 다른 곳',dif)
