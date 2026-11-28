import sys,json,struct,zlib,collections
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from hwplib import *
from align import hwp_chars
def apply(rs,H,DEL,INS,BLUE,INSBLUE,blue_map=None):
    """returns new records. blue_map: old shape id -> blue shape id (None = no coloring)"""
    # per record: deletions by wchar idx, insertions before wchar idx, blue wchar idx
    pd=collections.defaultdict(set); pi=collections.defaultdict(dict); pb=collections.defaultdict(set); pib=collections.defaultdict(set)
    for j in DEL: ri,wi,_=H[j]; pd[ri].add(wi)
    for j,t in INS.items():
        ri,wi,_=H[j]
        if wi is None: wi=[x for x,k,v in tokens(rs[ri][2]) if k=='b' and v==13][-1]
        pi[ri][wi]=t
        if j in INSBLUE: pib[ri].add(wi)
    for j in BLUE:
        ri,wi,_=H[j]
        if wi is not None: pb[ri].add(wi)
    out=[list(r) for r in rs]
    # find paragraph groups: header idx -> text idx, charshape idx, lineseg idx
    hdr=None; grp={}
    for i,(t,l,b) in enumerate(rs):
        if t==66: hdr=i; grp[i]={}
        elif t in (67,68,69,70) and hdr is not None and l==rs[hdr][1]+1: grp[hdr][t]=i
    changed=0
    for h,g in grp.items():
        if 67 not in g: continue
        ti=g[67]
        if ti not in pd and ti not in pi and not (blue_map and ti in pb): continue
        b=rs[ti][2]; w=list(struct.unpack('<%dH'%(len(b)//2),b)); n=len(w)
        toks=tokens(b)
        # char shapes
        cs=rs[g[68]][2]; runs=[struct.unpack_from('<II',cs,k*8) for k in range(len(cs)//8)]
        def shape_at(pos):
            s=runs[0][1]
            for p,sid in runs:
                if p<=pos: s=sid
            return s
        new=[]; shapes=[]; posmap={}
        for wi,k,v in toks:
            width=8 if k=='x' else (2 if k=='c' and ord(v)>0xFFFF else 1)
            posmap[wi]=len(new)
            if wi in pi[ti]:
                ins=pi[ti][wi]; sid=shape_at(wi)
                for ch in ins:
                    enc=ch.encode('utf-16-le'); u=struct.unpack('<%dH'%(len(enc)//2),enc)
                    for x in u:
                        new.append(x); shapes.append(blue_map.get(sid,sid) if (blue_map and wi in pib[ti]) else sid)
            if wi in pd[ti]: continue
            sid=shape_at(wi)
            if blue_map and wi in pb[ti]: sid=blue_map.get(sid,sid)
            for x in w[wi:wi+width]: new.append(x); shapes.append(sid)
        posmap[n]=len(new)
        # rebuild runs
        nr=[]
        for p,s in enumerate(shapes):
            if not nr or nr[-1][1]!=s: nr.append((p,s))
        if not nr: nr=[(0,runs[0][1])]
        out[ti][2]=struct.pack('<%dH'%len(new),*new)
        out[g[68]][2]=b''.join(struct.pack('<II',p,s) for p,s in nr)
        hb=bytearray(rs[h][2]); nch=struct.unpack_from('<I',hb,0)[0]
        assert (nch&0x7fffffff)==n,(nch,n)
        struct.pack_into('<I',hb,0,(nch&0x80000000)|len(new))
        struct.pack_into('<H',hb,12,len(nr))
        out[h][2]=bytes(hb)
        if 69 in g:
            ls=bytearray(rs[g[69]][2])
            for k in range(len(ls)//36):
                p=struct.unpack_from('<I',ls,k*36)[0]
                q=posmap.get(p)
                if q is None: q=min((posmap[x] for x in posmap if x>=p),default=len(new))
                struct.pack_into('<I',ls,k*36,q)
            out[g[69]][2]=bytes(ls)
        if 70 in g:  # 문단 범위 태그(시작·끝·태그 12바이트씩) 자리도 옮김 (2026-11-28 DL-0042)
            rt=bytearray(rs[g[70]][2])
            def mp(p): return posmap[p] if p in posmap else min((posmap[x] for x in posmap if x>=p),default=len(new))
            for k in range(len(rt)//12):
                a,b=struct.unpack_from('<II',rt,k*12)
                struct.pack_into('<II',rt,k*12,mp(a),mp(b))
            out[g[70]][2]=bytes(rt)
        changed+=1
    return out,changed
