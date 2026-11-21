import fitz, json, re, unicodedata, sys
PDF='/mnt/user-data/uploads/b71119c9-______.pdf'
d=fitz.open(PDF)
import os
SRC='/tmp/dl11_moved.json' if os.path.exists('/tmp/dl11_moved.json') else '/tmp/dl11_before.json'
old=json.load(open(SRC))
b=old['body']
def nz(s):
    s=unicodedata.normalize('NFKC',s.replace('Ⅰ','I').replace('Ⅱ','II'))
    out=[]
    for ch in s:
        if ord(ch)<0x2000: ch=''.join(c for c in unicodedata.normalize('NFKD',ch) if not unicodedata.combining(c))
        for c in ch:
            if c.isalnum(): out.append(c.lower())
    return ''.join(out)
# EPUB 흐름: 화면 표시용 기호·그림 주소는 건너뜀
skip=re.compile(r'=== [^=\n]*===|!\[[^\]]*\]\([^)]*\)|\*\*|^## |^:: ',re.M)
S=[];idx=[];i=0
while i<len(b):
    m=skip.match(b,i)
    if m and m.end()>i: i=m.end(); continue
    c=nz(b[i])
    for ch in c: S.append(ch); idx.append(i)
    i+=1
S=''.join(S)
def ptext(pg):
    H=pg.rect.height; out=[]
    for bl in pg.get_text('blocks'):
        t=bl[4]
        if '.indd' in t: continue
        t='\n'.join(l for l in t.split('\n') if not (('|' in l) and re.search(r'^\s*\d+\s*\||\|\s*\d+\s*$',l)))
        if re.fullmatch(r'\s*\d+\s*',t): continue
        out.append(t)
    return nz(''.join(out))
P=[ptext(pg) for pg in d]
res={}
pos=0;last=-1
PHOTO=set(int(x) for x in re.findall(r'DL-0011-(\d+)p\.jpg',b))
for n in range(1,len(d)+1):
    if n in PHOTO: continue
    t=P[n-1]
    if len(t)<15: continue
    votes={}
    lo=max(last+1,pos-1500); hi=min(len(S),pos+6000)
    for k in range(0,min(len(t)-12,160),8):
        key=t[k:k+12]
        j=S.find(key,lo)
        while j!=-1 and j<hi:
            st=j-k; votes[st]=votes.get(st,0)+1
            j=S.find(key,j+1)
    if not votes: print('못 찾음',n,t[:30]); continue
    best=max(votes.items(),key=lambda kv:(kv[1],-abs(kv[0]-pos)))
    if best[1]<2: print('약함',n,best,t[:30]); 
    if best[1]>=2:
        res[n]=best[0]; last=best[0]; pos=int(best[0]+len(t)*0.8)
print('찾은 쪽',len(res))
json.dump({'res':res},open('/tmp/p11/res.json','w'))
# 순서 확인
prev=-1
for n in sorted(res):
    if res[n]<prev: print('역순',n,res[n],prev)
    prev=res[n]
miss=[n for n in range(1,len(d)+1) if n not in res and n not in PHOTO]
print('빠진 쪽',miss)
print({n:res.get(n) for n in range(255,264)}, len(S))
print('사진쪽',sorted(PHOTO))

# ---- 쪽 표시 넣기 ----
pos={}
for n,st in res.items(): pos[n]=idx[st]
for n in PHOTO: pos[n]=b.index(f'(/uploads/DL-0011-{n}p.jpg)'); pos[n]=b.rindex('![',0,pos[n])
pos[1]=b.index('![#속표지]')
pos[7]=b.index('## 목차')
pos[9]=b.index('이 수행은 늘 해야 하는 것', pos[8])
pos.pop(263,None)
pos[262]=b.index('**이 책은 법보시용')
def snap(p):
    ls=b.rfind('\n',0,p)+1
    if re.fullmatch(r'(## |:: |\*\*|\|\| )*', b[ls:p]): return ls
    if b.startswith('## ',ls) and p-ls<=20: return ls
    return p
ins={n:snap(p) for n,p in pos.items()}
order=sorted(ins,key=lambda n:ins[n])
def nxt(n): return min(ins[m] for m in ins if m>n and m not in PHOTO)
bad=[n for n in PHOTO if ins[n]>nxt(n) or re.sub(r'!\[[^\]]*\]\([^)]*\)|\s','',b[ins[n]:nxt(n)]) != '']
if bad:
    nb=b; moves=[]
    for n in sorted(bad,reverse=True):
        img=re.search(r'!\[[^\]]*\]\(/uploads/DL-0011-%dp\.jpg\)'%n, nb).group(0)
        tgt=min(ins[m] for m in ins if m>n and m not in PHOTO)
        moves.append((n,tgt))
    # 뒤에서부터 옮기기: 그림을 빼고, 다음 쪽 시작 자리에 넣음
    edits=[]
    for n,tgt in moves:
        m=re.search(r'\n*!\[[^\]]*\]\(/uploads/DL-0011-%dp\.jpg\)\n*'%n, b)
        edits.append((m.start(),m.end(),'\n\n')); edits.append((tgt,tgt,'%s\n\n'%m.group(0).strip()+('' if b[tgt-1]=='\n' else '')))
    for st,en,rep in sorted(edits,key=lambda e:(e[0],e[1]),reverse=True): b=b[:st]+rep+b[en:]
    b=re.sub(r'\n{3,}','\n\n',b)
    old['body']=b; json.dump(old,open('/tmp/dl11_moved.json','w'),ensure_ascii=False)
    print('사진 옮김',moves,'— 다시 실행'); raise SystemExit
assert order==sorted(order), [ (n,ins[n]) for n in order][:20]
# 장 표시(=== ===) 중 전자책에만 있는 장 앞의 것만 남김
keep_ch=[b.index('=== ===\n:: NAMO'), b.rindex('=== ===',0,b.index('## 아신 떼자니야 사야도')), b.rindex('=== ===',0,b.index('**법은 어디에나**'))]
out=[];last=0
cuts=sorted([(p,'page',n) for n,p in ins.items()]+[(m.start(),'ch',None) for m in re.finditer(r'=== ===\n',b)])
for p,kind,n in cuts:
    out.append(b[last:p]); last=p
    if kind=='ch':
        last=p+len('=== ===\n')
        if p in keep_ch: out.append('=== ===\n')
        else: out.append('\n\n')
        continue
    # 문단 가운데면 나누기 (굵게 안이면 닫고 다시 엶)
    ps=b.rfind('\n\n',0,p); ps=0 if ps<0 else ps+2
    mid = p>ps and b[p-1]!='\n'
    bold = b[ps:p].count('**')%2==1
    out.append(('**' if bold else '')+'\n\n'+f'=== {n}쪽 ===\n'+('**' if bold else ''))
out.append(b[last:])
nb=''.join(out)
nb=re.sub(r'\n{3,}','\n\n',nb); nb=re.sub(r'\n\n(=== [^=\n]*===)\n\n',r'\n\n\1\n',nb); nb=re.sub(r'(=== [^=\n]*===)\n\n',r'\1\n',nb)
nb=nb.lstrip('\n')
keep=lambda x: re.sub(r'=== [^=\n]*===|\s|\*\*','',x)
assert keep(nb)==keep(b), '글자 다름'
D=dict(old); D['body']=nb
ms=[m.start() for m in re.finditer(r'=== [^=\n]*===',nb)]; labs=re.findall(r'=== ([^=\n]*)===',nb)
anch={'예경문':':: NAMO','속표지':'![#속표지]','저자 소개':'## 아신 떼자니야 사야도','판권지':'**이 책은 법보시용','전자책 판권지':'**법은 어디에나**'}
cur=0; toc=[]
for t in old['toc']:
    key=anch.get(t['title'],'## '+t['title']); p=nb.find(key, cur if not t['sub'] else 0)
    if t['sub']: p=nb.find(key, chpos)
    assert p>=0,t
    if not t['sub']: chpos=p; cur=p
    pg=sum(1 for x in ms if x<=p); pre=nb[ms[pg-1]:p].split('===',2)[2].strip() if pg else ''
    e={'title':t['title'],'page':pg,'sub':t['sub']}
    if pre: e['at']=t['title'] if key.startswith('## ') else key.lstrip('*:# ')[:14]
    toc.append(e)
    print(('  ' if t['sub'] else '')+t['title'][:24], labs[pg-1].strip(), '(중간)' if pre else '')
D['toc']=toc
json.dump(D,open('/home/claude/dhammadana/content/texts/DL-0011.json','w'),ensure_ascii=False,indent=2); open('/home/claude/dhammadana/content/texts/DL-0011.json','a').write('\n')
print('쪽 표시',len(ms))
