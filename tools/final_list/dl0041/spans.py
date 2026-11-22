import json, re, sys, importlib.util, collections
sys.path.insert(0,'tools')
spec=importlib.util.spec_from_file_location('fx','tools/dl0041_fix.py'); fx=importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
ns={}; exec(open('/tmp/d41fin/build.py').read().split("rows=[]")[0].replace("R=json.load(open('/tmp/d41fin/recs.json'))",""),ns)
cat,srcf=ns['cat'],ns['src']
orig=json.load(open('/tmp/d41orig.json'))['body']; fixes=json.load(open('tools/dl0041_fixes.json'))
OP=orig.split('\n\n'); P=list(OP)
rows=collections.defaultdict(list)   # k -> [dict(s,e,recs)]
hist=collections.defaultdict(list)   # k -> [(s,oldlen,newlen)]
def edit(k,s,e,new,i):
    old=P[k]; d=len(new)-(e-s)
    hist[k].append((s,e-s,len(new)))
    hit=[r for r in rows[k] if not (r['e']<s or r['s']>e)]
    for r in rows[k]:
        if r in hit: continue
        if r['s']>=e: r['s']+=d; r['e']+=d
    if hit:
        ns_=min([s]+[r['s'] for r in hit]); ne=max([s+len(new)]+[(r['e']+d if r['e']>=e else r['e']) for r in hit])
        recs=[x for r in hit for x in r['recs']]+[i]
        for r in hit: rows[k].remove(r)
        rows[k].append(dict(s=ns_,e=ne,recs=recs))
    else: rows[k].append(dict(s=s,e=s+len(new),recs=[i]))
    P[k]=old[:s]+new+old[e:]
def starts():
    st=[];p=0
    for x in P: st.append(p); p+=len(x)+2
    return st
for i,f in enumerate(fixes):
    b='\n\n'.join(P)
    if f.get('op'):
        b2,_=fx.op_quotes(b) if f['op']=='quotes' else fx.op_fullwidth(b)
        P2=b2.split('\n\n'); assert len(P2)==len(P)
        for k in range(len(P)):
            if P[k]!=P2[k]:
                assert len(P[k])==len(P2[k])
                for j,(x,y) in reversed(list(enumerate(zip(P[k],P2[k])))):
                    if x!=y: edit(k,j,j+1,y,i)
        continue
    a,nb,pg=f['a'],f['b'],f.get('p'); rx=re.compile(a) if f.get('re') else fx.fuzzy(a)
    ms=[];last=0
    for s,e,name in fx.pages(b):
        if pg and name not in pg: continue
        for m in rx.finditer(b,s,e):
            if m.start()<last: continue
            rep=m.expand(nb) if f.get('re') else fx.remap(m.group(0),a,nb)
            ms.append((m.start(),m.end(),rep)); last=m.end()
    st=starts()
    import bisect
    for s,e,rep in reversed(ms):
        k=bisect.bisect_right(st,s)-1; ps=st[k]
        assert '\n\n' not in b[s:e]
        if rep!=b[s:e]: edit(k,s-ps,e-ps,rep,i)
assert '\n\n'.join(P)==open('/tmp/d41fin/after_fix.txt').read()
def back(k,p,end):
    for s,o,n in reversed(hist[k]):
        if p<=s: continue
        if p>=s+n: p=p-n+o
        else: p=s+o if end else s
    return p
pl=lambda x:re.sub(r'\*\*|__|°°','',x)
pages=[];n=''
for x in OP:
    m=re.match(r'=== ?(.*?) ?===',x)
    if m: n=m.group(1)
    pages.append(n)
out=[]
for k in list(rows):
    rs=sorted(rows[k],key=lambda r:r['s']); m=[]
    for r in rs:
        if m:
            gap=P[k][m[-1]['e']:r['s']]
            if len(gap)<=15 and '\n' not in gap and (not re.search(r'\s',gap) or ('[' in P[k][m[-1]['s']:m[-1]['e']] and ']' in P[k][r['s']:r['e']+1])):
                m[-1]=dict(s=m[-1]['s'],e=max(m[-1]['e'],r['e']),recs=m[-1]['recs']+r['recs']); continue
        m.append(dict(r))
    rows[k]=m
for k,rs in rows.items():
    for r in rs:
        s,e=r['s'],r['e']; os_,oe=back(k,s,False),back(k,e,True)
        A_=OP[k]; B_=P[k]
        bef=A_[os_:oe]; aft=B_[s:e]
        if pl(bef)==pl(aft): continue
        short=len(pl(bef).strip())<4 or len(pl(aft).strip())<4 or not pl(bef).strip() or not pl(aft).strip()
        def ctx(T,a,b_):
            L=pl(T[:a]).split('\n')[-1]; R=pl(T[b_:]).split('\n')[0]
            if short: return re.search(r'(\S*\s?\S*)$',L).group(1)[-18:], re.match(r'(\S*\s?\S*)',R).group(1)[:18]
            return re.search(r'(\S*)$',L).group(1)[-12:], re.match(r'(\S*)',R).group(1)[:12]
        lm,rm=ctx(A_,os_,oe); lm2,rm2=ctx(B_,s,e)
        i=r['recs'][0]; f=fixes[i]
        # 대표 묶음: 따옴표 op 이 아닌 첫 줄
        main=next((x for x in r['recs'] if not fixes[x].get('op')),i)
        PRI=['경전 출처','문장·내용','같은 이름 통일','한글 음역','맞춤법·문장부호·한자','로마자','띄어쓰기','따옴표·괄호']
        cs=[('따옴표·괄호' if fixes[x].get('op') else cat(x,fixes[x].get('g',''))) for x in r['recs']]
        c=min(cs,key=PRI.index); main=r['recs'][cs.index(c)]
        srcs=[]
        for x in r['recs']:
            sx=srcf(x,fixes[x].get('g','')); 
            if sx not in srcs: srcs.append(sx)
        out.append(dict(page=pages[k],para=k,pos=os_,cat=c,before=(lm+pl(bef)+rm).replace('\n','⏎'),after=(lm2+pl(aft)+rm2).replace('\n','⏎'),src='; '.join(srcs),n=1,i=main,nrec=len(r['recs'])))
out.sort(key=lambda x:(x['para'],x['pos']))
json.dump(out,open('/tmp/d41fin/spanrows.json','w'),ensure_ascii=False,indent=0)
print(len(out),collections.Counter(x['cat'] for x in out), sum(1 for x in out if x['nrec']>1))
