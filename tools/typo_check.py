"""교정용 — 한글 오자 후보 찾기 (운영자 요청, 2026-11-25: DL-0040 136쪽 '최사의 행복'을 놓친 뒤)
kiwi 가 낯선 한 글자 고유명사·모르는 말(UN)로 가르는 낱말마다 한 글자의 초성·중성·받침을 바꿔 보아 훨씬 자연스러운 꼴이 되면 '확인할 곳'으로 보임.
제안 꼴(최사 → 회사)은 틀릴 수 있음 — 앞뒤 글을 읽고 사람이 판단. 바른 음역 목록(tools/out/translit/set.json)에 있는 낱말은 뺌.
쓰는 법: node tools/translit_set.mjs <ID>; python3 tools/typo_check.py content/texts/<ID>.json"""
import json,re,sys,collections
from kiwipiepy import Kiwi
kw=Kiwi()
S=set(json.load(open('/home/claude/dhammadana/tools/out/translit/set.json')))
body=json.load(open(sys.argv[1]))['body']
pages=re.split(r'^=== (.*?) ===$',body,flags=re.M)
def dec(c): o=ord(c)-0xAC00; return o//588,(o%588)//28,o%28
def comp(i,v,j): return chr(0xAC00+i*588+v*28+j)
def variants(w):
    out=set()
    for p,c in enumerate(w):
        i,v,j=dec(c)
        for jj in range(28):
            if jj!=j: out.add(w[:p]+comp(i,v,jj)+w[p+1:])
        for vv in range(21):
            if vv!=v: out.add(w[:p]+comp(i,vv,j)+w[p+1:])
        for ii in range(19):
            if ii!=i: out.add(w[:p]+comp(ii,v,j)+w[p+1:])
    return out
cache={}
def score(x):
    if x not in cache: cache[x]=kw.analyze(x)[0][1]
    return cache[x]
seen={}
for i in range(1,len(pages),2):
    t=re.sub(r'\*\*|°°|==|\[\^[^\]]*\]:?','',pages[i+1])
    for m in re.finditer(r'[가-힣]{2,}',t):
        w=m.group()
        if w in seen: seen[w][1].append(pages[i]); continue
        tk=kw.tokenize(w)
        bad=[x for x in tk if x.tag in('NNP','UN') and x.len==1] or [x for x in tk if x.tag=='UN']
        if not bad: seen[w]=(None,[pages[i]]); continue
        if w in S: seen[w]=(None,[pages[i]]); continue
        s0=score(w); best=None
        for v in variants(w):
            sv=score(v)
            if sv>s0+6 and (best is None or sv>best[1]): best=(v,sv)
        seen[w]=(best and (best[0],round(best[1]-s0,1)),[pages[i]])
c=0
for w,(b,pg) in seen.items():
    if b: c+=1; print(w,'→',b[0],b[1],'|',','.join(dict.fromkeys(pg))[:60])
print(c)
