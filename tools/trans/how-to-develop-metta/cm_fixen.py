import json,re
rows=json.load(open('out.trans.json'))['rows']
R=json.load(open('m2.json'))
def nn(s): return re.sub(r'[^a-z]','',s.lower())
O=[nn(r['o']) for r in rows]
ch=0
for x in R:
    if x['k']=='exact' or not x['en']: continue
    q=nn(x['en'])[:40]
    hits=[i for i,o in enumerate(O) if q and q in o]
    if not hits: print('noen',x['p'],x['a'][:30]); continue
    best=min(hits,key=lambda i:abs(i-x['r0']))
    if best!=x['r0']:
        print('MOVE',x['p'],rows[x['r0']]['id'],'->',rows[best]['id'],'|',x['a'][:30]); x['r0']=x['r1']=best; ch+=1
    else: print('ok',x['p'],rows[best]['id'],x['a'][:30])
json.dump(R,open('m2.json','w'),ensure_ascii=False,indent=0); print(ch)
