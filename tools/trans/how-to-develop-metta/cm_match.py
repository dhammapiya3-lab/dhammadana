import json, re, bisect, difflib
D=json.load(open('out.trans.json')); rows=D['rows']
C=json.load(open('cm.json'))
VOC=[('메따','멧따'),('계발','개발'),('위빠사나','위빳사나')]
def n(s,alt=False):
    s=re.sub(r'\s+','',s)
    for a,b in VOC: s=s.replace(a,b if not (alt and a=='메따') else '자애')
    return s
T=[n(r.get('t0') or '') for r in rows]
stream=''; starts=[]
for t in T: starts.append(len(stream)); stream+=t
def rowof(j): return bisect.bisect_right(starts,j)-1
def finds(a):
    out=[]; s=0
    while True:
        j=stream.find(a,s)
        if j<0: return out
        out.append((j,j+len(a))); s=j+1
# pass 1 exact
loc=[None]*len(C); kind=[None]*len(C)
for i,c in enumerate(C):
    for alt in (False,True):
        h=finds(n(c['a'],alt))
        if h: loc[i]=h; kind[i]='exact'; break
# anchor position per p from unique exact hits
anch={}
for i,c in enumerate(C):
    if loc[i] and len(loc[i])==1: anch.setdefault(c['p'],[]).append(loc[i][0][0])
ps=sorted(anch); pos={p:sum(v)/len(v) for p,v in anch.items()}
def expect(p):
    k=bisect.bisect_left(ps,p)
    lo=ps[max(0,k-1)]; hi=ps[min(len(ps)-1,k)]
    if p in pos: return pos[p]
    if lo==hi: return pos[lo]
    return pos[lo]+(pos[hi]-pos[lo])*(p-lo)/(hi-lo)
final=[]
for i,c in enumerate(C):
    e=expect(c['p'])
    if loc[i]:
        best=min(loc[i],key=lambda h:abs(h[0]-e)); final.append((best,'exact',1.0)); continue
    a=n(c['a']); a2=n(c['a'],True)
    lo=max(0,int(e)-2500); hi=min(len(stream),int(e)+2500)
    bestsc=0; bestj=None
    for aa in (a,a2):
        L=len(aa)
        for j in range(lo,hi-L//2):
            w=stream[j:j+L]
            if w[:1]!=aa[:1] and w[-1:]!=aa[-1:]: continue
            sc=difflib.SequenceMatcher(None,aa,w,autojunk=False).ratio()
            if sc>bestsc: bestsc=sc; bestj=(j,j+L)
    final.append((bestj,'fuzzy' if bestsc>=0.6 else 'none',round(bestsc,2)))
res=[]
for c,(sp,k,sc) in zip(C,final):
    r0=rowof(sp[0]) if sp else None; r1=rowof(sp[1]-1) if sp else None
    res.append(dict(c,k=k,sc=sc,r0=r0,r1=r1,seen=stream[sp[0]:sp[1]] if sp else ''))
json.dump(res,open('m2.json','w'),ensure_ascii=False,indent=0)
import collections; print(collections.Counter(x['k'] for x in res))
for x in res:
    if x['k']!='exact': print(x['k'],x['sc'],x['p'],rows[x['r0']]['id'] if x['r0'] is not None else '-','|',x['a'][:40],'|',x['seen'][:40])
