import json,re,sys
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hwplib import *
import olefile
def hwp_chars(rs):
    """list of (recidx, wchar_idx, ch) for text chars; paragraph end -> '\n' with wchar_idx=None
    각주(fn)·미주(en) 안의 문단 기록 번호는 hwp_chars.fnrec 에 모아 둠 — align 이 본문·각주를 따로 맞댐(2026-11-25 DL-0040)"""
    H=[]; st=[]; fnrec=set()
    for ri,(t,l,b) in enumerate(rs):
        while st and st[-1][0]>=l: st.pop()
        if t==71: st.append((l,b[:4][::-1].decode('latin1')))
        if t==67 and any(c in ('fn  ','en  ') for _,c in st): fnrec.add(ri)
        if t!=67: continue
        for wi,k,v in tokens(b):
            if k=='c': H.append((ri,wi,v))
            elif k=='b' and v==10: H.append((ri,wi,'\n'))
            elif k=='b' and v in (24,30,31): H.append((ri,wi,' '))
        H.append((ri,None,'\n'))
    hwp_chars.fnrec=fnrec
    return H
MARK=re.compile(r'^=== [^\n]*===$|^(\^\^|::|>>|##|\+\+|%%|\|\|) |\*\*|°°|==|__|!\[[^\]]*\]\([^)]*\)|\[\^[^\]]+\]:?|^~$',re.M)
def body_mask(B):
    m=[True]*len(B)
    for x in MARK.finditer(B):
        for i in range(x.start(),x.end()): m[i]=False
    return m
FNDEF=re.compile(r'^\[\^\d+\]:[^\n]*(?:\n(?!\n)[^\n]*)*',re.M)   # 숫자 각주 풀이(빈 줄 앞까지) — [^*N] 은 한글 파일에서 본문일 수 있어 뺌
def align(B,H):
    """본문 글자와 한글 파일 글자를 차례대로 맞댐. 한글 파일에 각주가 있으면(hwp_chars.fnrec) 본문↔본문, 각주 풀이↔각주를 따로."""
    m=body_mask(B)
    fr=getattr(hwp_chars,'fnrec',set())
    if fr:
        fb=[False]*len(B)
        for x in FNDEF.finditer(B):
            for i in range(x.start(),x.end()): fb[i]=True
        A={};miss=[]
        for want in (False,True):
            bi=[i for i,c in enumerate(B) if m[i] and not c.isspace() and fb[i]==want]
            hi=[j for j,(r,_,c) in enumerate(H) if not c.isspace() and (r in fr)==want]
            a,ms=_align(B,H,bi,hi); A.update(a); miss+=ms
        return A,miss
    bi=[i for i,c in enumerate(B) if m[i] and not c.isspace()]
    hi=[j for j,(_,_,c) in enumerate(H) if not c.isspace()]
    return _align(B,H,bi,hi)
def _align(B,H,bi,hi):
    bs=''.join(B[i] for i in bi); hs=''.join(H[j][2] for j in hi)
    A={}; p=q=0; miss=[]
    K=10
    while p<len(bs) and q<len(hs):
        if bs[p]==hs[q]: A[bi[p]]=hi[q]; p+=1; q+=1; continue
        # resync
        best=None
        for dp in range(0,300):
            key=bs[p+dp:p+dp+K]
            if len(key)<K: break
            f=hs.find(key,q,q+3000)
            if f>=0:
                best=(dp,f-q); break
        if best is None: miss.append(('fail',p,bs[p:p+30])); break
        miss.append((bs[p:p+best[0]],hs[q:q+best[1]]))
        p+=best[0]; q+=best[1]
    return A,miss
