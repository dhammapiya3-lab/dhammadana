import sys,struct,olefile
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hwplib import *
def load(f):
    o=olefile.OleFileIO(f); rs=recs(rd(o,'BodyText/Section0')); o.close(); return rs
def paras(rs):
    out=[]; cur=None
    for i,(t,l,b) in enumerate(rs):
        if t==66 and l==0:
            if cur: out.append(cur)
            cur=[i,i+1]
        elif cur: cur[1]=i+1
    out.append(cur); return out
def ptext(rs,s,e):
    for i in range(s,e):
        t,l,b=rs[i]
        if t==67 and l==1:
            return ''.join(v if k=='c' else ('⏎' if k=='b' and v==10 else ('·' if k=='b' and v in (24,30,31) else ('[%s]'%k if k!='c' else ''))) for _,k,v in tokens(b))
    return ''
def hdr(rs,s):
    b=rs[s][2]; n,mask,ps,st,brk=struct.unpack_from('<IIHBB',b,0); return dict(n=n,ps=ps,st=st,brk=brk)
