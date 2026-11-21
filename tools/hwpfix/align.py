import json,re,sys
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hwplib import *
import olefile
def hwp_chars(rs):
    """list of (recidx, wchar_idx, ch) for text chars; paragraph end -> '\n' with wchar_idx=None"""
    H=[]
    for ri,(t,l,b) in enumerate(rs):
        if t!=67: continue
        for wi,k,v in tokens(b):
            if k=='c': H.append((ri,wi,v))
            elif k=='b' and v==10: H.append((ri,wi,'\n'))
            elif k=='b' and v in (24,30,31): H.append((ri,wi,' '))
        H.append((ri,None,'\n'))
    return H
MARK=re.compile(r'^=== [^\n]*===$|^(\^\^|::|>>|##|\+\+|%%|\|\|) |\*\*|°°|==|!\[[^\]]*\]\([^)]*\)|\[\^[^\]]+\]:?|^~$',re.M)
def body_mask(B):
    m=[True]*len(B)
    for x in MARK.finditer(B):
        for i in range(x.start(),x.end()): m[i]=False
    return m
def align(B,H):
    m=body_mask(B)
    bi=[i for i,c in enumerate(B) if m[i] and not c.isspace()]
    hi=[j for j,(_,_,c) in enumerate(H) if not c.isspace()]
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
