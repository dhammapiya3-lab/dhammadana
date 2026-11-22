import json,re,collections
R=json.load(open('/tmp/d41fin/recs.json'))
pl=lambda s:re.sub(r'\*\*|__|°°','',s)
M={2,5,7,8,10,11,12,15,26,28,30,31,32,33,34,35}
def cat(i,g):
    if i<45:
        if i in M: return '로마자'
        if i in (37,43,44,36): return '경전 출처'
        if i in (29,6,9): return '한글 음역'
        if i in (13,17,18,24,22,42,38,39,40,41): return '문장·내용'
        return '맞춤법·문장부호·한자'
    if i>=509:
        if i<=513 or i in (514,515,526,527,530): return '맞춤법·문장부호·한자' if i not in (514,515) else '띄어쓰기'
        if i<=518: return '따옴표·괄호'
        if i<=525: return '띄어쓰기'
        if i in (528,529): return '문장·내용'
        return '로마자'
    for k,v in [('1-2번','로마자'),('1번','로마자'),('2번','로마자'),('3번','띄어쓰기'),('4번','맞춤법·문장부호·한자'),('5번','따옴표·괄호'),('6번','문장·내용'),('7번','한글 음역'),('8번','같은 이름 통일'),('10번','경전 출처'),('veramaṇī','로마자'),('-buddhā','로마자'),('로마자','로마자'),('삼귀의','로마자'),('읽기 목차','로마자'),('다듬기','문장·내용'),("'의'",'문장·내용')]:
        if k in g: return v
    raise Exception(g)
def src(i,g):
    if i<45: return '2015년 판 대조 — 반영 권장 (1회차)'
    if i>=509: return g.replace('(2026-11-22)','').strip()
    return g.replace('(2026-11-22)','').strip()+' (1회차)'
def ctx(r):
    L=pl(r['L']); Rr=pl(r['R']); o=pl(r['old']); n=pl(r['new'])
    L=L.split('\n')[-1]; Rr=Rr.split('\n')[0]
    # 낱말 경계까지 (빈칸 기준)
    lm=re.search(r'(\S*)$',L).group(1) if o and not o[0].isspace() else ''
    if len(o.strip())>=8: lm=''
    rm=re.match(r'(\S*)',Rr).group(1) if o and not o[-1].isspace() else ''
    if len(o.strip())>=8: rm=''
    if o.strip()=='' or n.strip()=='' or len(o.strip())<3:   # 빈칸만·짧은 조각은 앞뒤 낱말
        lm=re.search(r'(\S*\s?\S*)$',L).group(1)[-14:]; rm=re.match(r'(\S*\s?\S*)',Rr).group(1)[:14]
    return (lm+o+rm).replace('\n','⏎'),(lm+n+rm).replace('\n','⏎')
CATS=['로마자','띄어쓰기','맞춤법·문장부호·한자','따옴표·괄호','한글 음역','같은 이름 통일','문장·내용','경전 출처','짜임(단락 옮기기·소제목)']
rows=[]
def pk(p):
    m=re.match(r'(\d+)',p or ''); return int(m.group(1)) if m else 0
for r in R:
    i=r['i']; g=r['f'].get('g','')
    if 'op' in r:
        rows.append(dict(cat='따옴표·괄호',page=', '.join(r['pages']),before='곧은 따옴표 " \'',after='한글 따옴표 “ ” ‘ ’ ('+str(r['n'])+'개)',src=src(i,g),n=r['n'],i=i)); continue
    b,a=ctx(r)
    rows.append(dict(cat=cat(i,g),page=r['page'],before=b,after=a,src=src(i,g),n=1,i=i))
MV='단락 옮기기·소제목 (2015년 판처럼, 1회차)'
rows+= [dict(cat=CATS[-1],page='157~159쪽 → 140쪽',before='사원 운영 방침 단락(‘테라와다 불교의 사원은 제대로 된 규칙…’~‘…유지 운영해 나갈 수가 있게 되는 것입니다.’)이 17장에 있음',after='15장 ‘(3) 거주처’ 끝, ‘(4) 의약품’ 앞으로 옮김 (글자는 그대로)',src=MV,n=1,i=999),
 dict(cat=CATS[-1],page='133쪽',before='(소제목 없음)',after='## 1) 사원 구성과 좌와구(坐臥具)',src=MV,n=1,i=999),
 dict(cat=CATS[-1],page='136쪽',before='(소제목 없음)',after='## 2) 사원 건립 목적과 과정',src=MV,n=1,i=999),
 dict(cat=CATS[-1],page='140쪽',before='(소제목 없음)',after='## 3) 테라와다 불교에서의 사원 운영 방침',src=MV,n=1,i=999)]
rows.sort(key=lambda x:(CATS.index(x['cat']),pk(x['page'].split(',')[0]),x['i']))
json.dump(rows,open('/tmp/d41fin/rows.json','w'),ensure_ascii=False,indent=0)
c=collections.Counter(); 
for x in rows: c[x['cat']]+=x['n'] if x['cat']!='따옴표·괄호' or x['n']==1 else 0
print(len(rows),dict(c))
# 묶음(같은 고침)
grp=collections.OrderedDict()
for x in rows:
    k=(x['cat'],x['before'],x['after']); grp.setdefault(k,[]).append(x['page'])
print('묶은 줄',len(grp))
