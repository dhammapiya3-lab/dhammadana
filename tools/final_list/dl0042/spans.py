"""DL-0042 최종 교정 목록 ① (tools/final_list/dl0040/spans.py 를 옮김, 2026-11-28)
교정 전 본문(19be502)에 교정 목록(tools/dl0042_fixes.json)을 차례로 적용하며 문단마다 바뀐 자리를 따라가고,
한 자리를 여러 번 고친 곳은 한 곳(처음 글 → 마지막 글)으로 묶음. 결과가 사이트 본문과 한 글자도 같은지 확인.
  git show 19be502:content/texts/DL-0042.json > /tmp/d42orig.json; mkdir -p /tmp/d42fin/out; python3 tools/final_list/dl0042/spans.py"""
import json, re, sys, collections, bisect
sys.path.insert(0,'tools'); sys.path.insert(0,'tools/final_list/dl0042')
import dl0042_fix as fx; from cats import cat as catf
orig=json.load(open('/tmp/d42orig.json'))['body']
fixes=json.load(open('tools/dl0042_fixes.json'))
R=lambda a,b:set(range(a,b+1))
YM=R(206,218)|R(229,232)|{234,235,238,388,538,600,667,839,877,878}|R(890,901)-{892}
NAEYONG=R(201,204)|{278,279}|R(824,831)|R(880,889)|{892}|R(902,967)|{971,972}   # '-을라고·-어라는' 줄(968~970·973~983)은 맞춤법
def cat(i):
    f=fixes[i]
    if 'op' in f: return '따옴표·괄호'
    if i in YM: return '한글 음역'
    if i in NAEYONG and catf(f) not in ('띄어쓰기',): return '문장·내용'
    return catf(f)
def src(i):
    r=('1회차' if i<242 else '2회차' if i<280 else '3회차 쪽마다 읽기 (가)' if i<693 else '3회차 — 운영자 결정' if i<976 else '4회차')
    return f'교정 목록 {r} (2026-11-28) — 목록 {i+1}번째 줄'
OP=orig.split('\n\n'); P=list(OP)
rows=collections.defaultdict(list); hist=collections.defaultdict(list)
def edit(k,s,e,new,i):
    old=P[k]; d=len(new)-(e-s); hist[k].append((s,e-s,len(new)))
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
cross=[]
for i,f in enumerate(fixes):
    b='\n\n'.join(P)
    if f.get('op'):
        nb2,_=(fx.op_fullwidth if f['op']=='fullwidth' else fx.op_quotes)(b); assert len(nb2)==len(b)
        ms=[]; j=0
        while j<len(b):
            if b[j]!=nb2[j]:
                k2=j
                while k2<len(b) and b[k2]!=nb2[k2]: k2+=1
                ms.append((j,k2,nb2[j:k2])); j=k2
            else: j+=1
    else:
        a,nb,pg=f['a'],f['b'],f.get('p'); rx=re.compile(a) if f.get('re') else fx.fuzzy(a)
        ms=[];last=0
        for s,e,name in fx.pages(b):
            if pg and name not in pg: continue
            for m in rx.finditer(b,s,e):
                if m.start()<last: continue
                rep=m.expand(nb) if f.get('re') else fx.remap(m.group(0),a,nb)
                ms.append((m.start(),m.end(),rep)); last=m.end()
    st=starts()
    for s,e,rep in reversed(ms):
        while e>s and rep and b[s]=='\n' and rep[0]=='\n': s+=1; rep=rep[1:]
        while e>s and rep and b[e-1]=='\n' and rep[-1]=='\n': e-=1; rep=rep[:-1]
        k=bisect.bisect_right(st,s)-1; ps=st[k]
        if '\n\n' in b[s:e] or '\n\n' in rep: cross.append((i,b[s:e],rep)); continue
        if rep!=b[s:e]: edit(k,s-ps,e-ps,rep,i)
assert not cross, cross
cur=json.load(open('content/texts/DL-0042.json'))['body']
if '\n\n'.join(P)!=cur:
    for x,y in zip('\n\n'.join(P).split('\n'),cur.split('\n')):
        if x!=y: print(repr(x[:300]));print(repr(y[:300]));break
    raise SystemExit('사이트 본문과 다름')
print('교정 목록을 다시 적용한 결과 = 사이트 본문 (한 글자도 같음)')
def back(k,p,end):
    for s,o,n in reversed(hist[k]):
        if p<=s: continue
        if p>=s+n: p=p-n+o
        else: p=s+o if end else s
    return p
pl=lambda x:re.sub(r'(?m)^(\^\^|::|>>|##|\+\+|%%|\|\|) ','',re.sub(r'\*\*|__|°°|\[\^[^\]]+\]:? ?','',x))
pages=[];n=''
for x in OP:
    m=re.match(r'=== ?(.*?) ?===',x)
    if m: n=m.group(1)
    pages.append(n)
for k in list(rows):
    rs=sorted(rows[k],key=lambda r:r['s']); m=[]
    for r in rs:
        if m:
            gap=P[k][m[-1]['e']:r['s']]
            if len(gap)<=15 and '\n' not in gap and (not re.search(r'\s',gap) or len(re.findall(r'\s+',gap))==1 and len(gap)<=8 or ('(' in P[k][m[-1]['s']:m[-1]['e']] and ')' in P[k][r['s']:r['e']+1])):
                m[-1]=dict(s=m[-1]['s'],e=max(m[-1]['e'],r['e']),recs=m[-1]['recs']+r['recs']); continue
        m.append(dict(r))
    rows[k]=m
PRI=['문장·내용','같은 표기 통일','한글 음역','맞춤법·문장부호·한자','로마자','띄어쓰기','따옴표·괄호']
out=[]
for k,rs in rows.items():
    for r in rs:
        s,e=r['s'],r['e']; os_,oe=back(k,s,False),back(k,e,True)
        A_=OP[k]; B_=P[k]; bef=A_[os_:oe]; aft=B_[s:e]
        if pl(bef)==pl(aft): continue
        short=len(pl(bef).strip())<4 or len(pl(aft).strip())<4
        def ctx(T,a,b_):
            L=pl(T[:a]).split('\n')[-1]; R_=pl(T[b_:]).split('\n')[0]
            if short: return re.search(r'(\S*\s?\S*)$',L).group(1)[-18:], re.match(r'(\S*\s?\S*)',R_).group(1)[:18]
            return re.search(r'(\S*)$',L).group(1)[-12:], re.match(r'(\S*)',R_).group(1)[:12]
        lm,rm=ctx(A_,os_,oe); lm2,rm2=ctx(B_,s,e)
        cs=[(catf({'a':pl(bef),'b':pl(aft)}) if fixes[x].get('re') and x not in YM|NAEYONG else cat(x)) for x in r['recs']]; c=min(cs,key=PRI.index)
        srcs=[]
        for x in r['recs']:
            sx=src(x)
            if sx not in srcs: srcs.append(sx)
        out.append(dict(page=pages[k] or '(쪽 이름 없음)',para=k,pos=os_,cat=c,before=(lm+pl(bef)+rm).replace('\n','⏎'),after=(lm2+pl(aft)+rm2).replace('\n','⏎'),src='; '.join(srcs),n=1,nrec=len(r['recs'])))
# 본문을 만들 때(pdf2text_dl0042.py) 바꾼 속표지 제목 — 운영자 요청
out.append(dict(page='1쪽',para=-1,pos=0,cat='문장·내용',before='테라와다 불교의범과 신행생활_아짠 빤냐와로 스님 법문',after='테라와다 불교의 신행생활_아짠 빤냐와로 스님 법문',src='속표지 제목 — 운영자 요청 (2026-11-28, 본문을 만들 때 바꿈)',n=1,nrec=1))
out.sort(key=lambda x:(PRI.index(x['cat']),x['para'],x['pos']))
json.dump(out,open('/tmp/d42fin/rows.json','w'),ensure_ascii=False,indent=0)
print(len(out),collections.Counter(x['cat'] for x in out), '여러 번 고친 자리',sum(1 for x in out if x['nrec']>1))
