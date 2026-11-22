import json,collections
S=json.load(open('spanrows.json'))
for x in S:
  if x['page']=='': x['page']='3쪽 (삼귀의, 쪽 번호 인쇄 안 됨)' if 'Namo' in x['before'] else '차례'
CATS=['로마자','띄어쓰기','맞춤법·문장부호·한자','따옴표·괄호','한글 음역','같은 이름 통일','문장·내용','경전 출처','짜임(단락 옮기기·소제목)']
MV='단락 옮기기·소제목 (2015년 판처럼, 1회차)'
S+= [dict(cat=CATS[-1],page='157~159쪽 → 140쪽',before='사원 운영 방침 단락(‘테라와다 불교의 사원은 제대로 된 규칙…’~‘…유지 운영해 나갈 수가 있게 되는 것입니다.’)이 17장에 있음',after='15장 ‘(3) 거주처’ 끝, ‘(4) 의약품’ 앞으로 옮김 (글자는 그대로)',src=MV,n=1,para=9999,pos=0),
 dict(cat=CATS[-1],page='133쪽',before='(소제목 없음)',after='## 1) 사원 구성과 좌와구(坐臥具)',src=MV,n=1,para=9999,pos=1),
 dict(cat=CATS[-1],page='136쪽',before='(소제목 없음)',after='## 2) 사원 건립 목적과 과정',src=MV,n=1,para=9999,pos=2),
 dict(cat=CATS[-1],page='140쪽',before='(소제목 없음)',after='## 3) 테라와다 불교에서의 사원 운영 방침',src=MV,n=1,para=9999,pos=3)]
S.sort(key=lambda x:(CATS.index(x['cat']),x['para'],x['pos']))
json.dump(S,open('rows.json','w'),ensure_ascii=False,indent=0)
print(len(S),collections.Counter(x['cat'] for x in S))
