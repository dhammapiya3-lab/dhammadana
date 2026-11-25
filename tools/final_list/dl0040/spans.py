"""DL-0040 최종 교정 목록 ① — 교정 전 본문(a41edb1)에 앞의 손 교정 2줄 + 교정 목록(tools/dl0040_fixes.json)을 차례로
적용하며 문단마다 바뀐 자리를 따라가고, 한 자리를 여러 번 고친 곳은 한 곳(처음 글 → 마지막 글)으로 묶음.
결과가 사이트 본문과 한 글자도 같은지 확인. (tools/final_list/dl0041/spans.py 를 옮김, 2026-11-25)
  git show a41edb1:content/texts/DL-0040.json > /tmp/d40orig.json; python3 tools/final_list/dl0040/spans.py"""
import json, re, sys, collections, bisect
sys.path.insert(0,'tools'); sys.path.insert(0,'tools/final_list/dl0040')
import dl0040_fix as fx; from cats import cat as catf
orig=json.load(open('/tmp/d40orig.json'))['body']
PRE=[dict(p=['2쪽'],a='^^ 아짠문',b='^^ 아짠 문',g='속표지 제목 — 운영자 요청 (2026-11-22)',c='문장·내용'),
     dict(p=['7쪽'],a='재현하는데 도움이',b='재현하는 데 도움이',g='7쪽 — 운영자 지정 (2026-11-22)',c='띄어쓰기')]
FX=json.load(open('tools/dl0040_fixes.json'))
fixes=PRE+FX; NPRE=len(PRE)
# 글 모양으로 정하지 못하는 줄은 교정 목록의 찾을 글(a)로 묶음을 정함 — 줄 번호가 바뀌어도 그대로
OVR_T={**{a:"한글 음역" for a in ["아다빠(atappā", "아카니따(akaniṭṭhā", "데바 들을", "타타가타(Tathāgata) ‘여래’의 뜻으로", "데바닷다", "위수디데바", "삼마띠데바", "데바타(", "데바", "타타가타", "사리카", "아비하(", "수닷싸(", "빤수꿀로(", "앗빠나", "산디티꼬", "끼레사(", "맛가(", "빠티삼비다냐나", "앗따 빠띠삼비다", "앗꼬데나 진 꼿쌈", "마하삿띠(", "빠티목카", "상베가", "아쿠사라", "쿠사라", "칼라마", "와따 룻까 나 빱바또", "베사카", "담마짯까", "위무띠", "아나라요", "삽바라삼", "마하반야", "칼야나밋타", "아밧싸라", "삼마티 형상", "바뜨(baht)", "브라마라 한다", "브라마비하라", "아비하(", "수닷싸(", "빤수꿀로(", "담마짜카팟바따나 숫따", "짜 니붓또’", "캄마싸타 스님", "‘앗띠(뼈)’", "아누빠디셋싸", "업빠띠데와", "뿌나꿰탐 로깟사", "‘야따디뽀 짜", "마하니다나수타", "타바팀사", "티피타카"]},**{a:"문장·내용" for a in ["전설에 나오는 데와는 왕을 가리킨다. 전설에 의하면,", "사고 있다 하여도", "갖추어야 필요하다", "수명과 만큼의", "결코 그런 사람에게 다가가는 것이 결코 싫을", "쓰러져 있은 듯", "브라흐마(Brahma)의 다섯"]}}
OVR={i:OVR_T[f['a']] for i,f in enumerate(fixes) if i>=NPRE and f['a'] in OVR_T}
def cat(i):
    f=fixes[i]
    if i<NPRE: return f['c']
    return OVR.get(i) or catf(f)
def src(i):
    if i<NPRE: return fixes[i]['g']
    j=i-NPRE
    return ('교정 목록 1회차 (2026-11-22)' if j<147 else '교정 목록 2회차 (2026-11-25)' if j<512 else '교정 목록 3회차 — 운영자 결정 (2026-11-25)')+f' — 목록 {j+1}번째 줄'
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
        while e>s and rep and b[s]=='\n' and rep[0]=='\n': s+=1; rep=rep[1:]   # 문단 사이 줄 바꿈을 품은 줄(346·348~352번째)
        while e>s and rep and b[e-1]=='\n' and rep[-1]=='\n': e-=1; rep=rep[:-1]
        k=bisect.bisect_right(st,s)-1; ps=st[k]
        if '\n\n' in b[s:e] or '\n\n' in rep:   # 문단을 잇거나 나누는 고침(308쪽 판권지 줄 잇기는 '\n' 하나라 해당 없음)
            cross.append((i,b[s:e],rep)); continue
        if rep!=b[s:e]: edit(k,s-ps,e-ps,rep,i)
assert not cross, cross
cur=json.load(open('content/texts/DL-0040.json'))['body']
if '\n\n'.join(P)!=cur:
    import difflib
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
pl=lambda x:re.sub(r'(?m)^(\^\^|::|>>|##|\+\+|%%|\|\|) ','',re.sub(r'\*\*|__|°°|\[\^[^\]]+\]:? ?','',x))   # 굵게·기울임과 줄 첫머리 모양 표시(^^ ## :: 등)·각주 번호 [^n] 는 빼고 보임
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
            if len(gap)<=15 and '\n' not in gap and (not re.search(r'\s',gap) or len(re.findall(r'\s+',gap))==1 and len(gap)<=8 or ('(' in P[k][m[-1]['s']:m[-1]['e']] and ')' in P[k][r['s']:r['e']+1])):   # 바로 옆 낱말의 고침도 한 줄로(앞뒤 글이 서로 달라 보이지 않게)
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
            L=pl(T[:a]).split('\n')[-1]; R=pl(T[b_:]).split('\n')[0]
            if short: return re.search(r'(\S*\s?\S*)$',L).group(1)[-18:], re.match(r'(\S*\s?\S*)',R).group(1)[:18]
            return re.search(r'(\S*)$',L).group(1)[-12:], re.match(r'(\S*)',R).group(1)[:12]
        lm,rm=ctx(A_,os_,oe); lm2,rm2=ctx(B_,s,e)
        cs=[(catf({'a':pl(bef),'b':pl(aft)}) if fixes[x].get('re') and x not in OVR else cat(x)) for x in r['recs']]; c=min(cs,key=PRI.index)   # 정규식 줄은 실제로 바뀐 글로 묶음을 정함
        srcs=[]
        for x in r['recs']:
            sx=src(x)
            if sx not in srcs: srcs.append(sx)
        out.append(dict(page=pages[k] or '(쪽 이름 없음)',para=k,pos=os_,cat=c,before=(lm+pl(bef)+rm).replace('\n','⏎'),after=(lm2+pl(aft)+rm2).replace('\n','⏎'),src='; '.join(srcs),n=1,nrec=len(r['recs'])))
out.sort(key=lambda x:(PRI.index(x['cat']),x['para'],x['pos']))
json.dump(out,open('/tmp/d40fin/rows.json','w'),ensure_ascii=False,indent=0)
print(len(out),collections.Counter(x['cat'] for x in out), '여러 번 고친 자리',sum(1 for x in out if x['nrec']>1))
