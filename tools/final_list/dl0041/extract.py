import json, re, sys, importlib.util, difflib, collections
sys.path.insert(0,'tools')
spec=importlib.util.spec_from_file_location('fx','tools/dl0041_fix.py'); fx=importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
before=json.load(open('/tmp/d41orig.json'))['body']
fixes=json.load(open('tools/dl0041_fixes.json'))
MK=re.compile(r'\*\*|__|°°')
def pl(s): return MK.sub('',s)
def pagename(b,pos):
    n=''
    for m in re.finditer(r'^=== ?(.*?) ?===$', b[:pos], re.M): n=m.group(1)
    return n
recs=[]; b=before
for i,f in enumerate(fixes):
    if f.get('op'):
        b2,n=fx.op_quotes(b) if f['op']=='quotes' else fx.op_fullwidth(b)
        pgs=[]
        for k,(x,y) in enumerate(zip(b,b2)):
            if x!=y: pgs.append(pagename(b,k))
        recs.append(dict(i=i,f=f,op=f['op'],n=sum(1 for x,y in zip(b,b2) if x!=y),pages=sorted(set(pgs),key=lambda s:(len(s),s))))
        b=b2; continue
    a,nb,pg=f['a'],f['b'],f.get('p')
    rx=re.compile(a) if f.get('re') else fx.fuzzy(a)
    out=[];last=0
    for s,e,name in fx.pages(b):
        if pg and name not in pg: continue
        for m in rx.finditer(b,s,e):
            if m.start()<last: continue
            rep=m.expand(nb) if f.get('re') else fx.remap(m.group(0),a,nb)
            if rep!=m.group(0):
                L=b[max(0,m.start()-12):m.start()]; R=b[m.end():m.end()+12]
                recs.append(dict(i=i,f=f,page=name,old=m.group(0),new=rep,L=L,R=R))
            out.append(b[last:m.start()]); out.append(rep); last=m.end()
    out.append(b[last:]); b=''.join(out)
json.dump(recs,open('/tmp/d41fin/recs.json','w'),ensure_ascii=False,indent=0)
open('/tmp/d41fin/after_fix.txt','w').write(b)
print(len(recs), sum(1 for r in recs if 'old' in r))
