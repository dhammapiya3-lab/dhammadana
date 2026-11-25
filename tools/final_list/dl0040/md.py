"""DL-0040 최종 교정 목록 ③ Docs 문서용 표 — 같은 고침(바뀐 낱말)은 한 줄로 모아 쪽을 함께 적음 (2026-11-25)"""
import json,re,collections,difflib
R=json.load(open('/tmp/d40fin/rows.json'))
CATS=['띄어쓰기','같은 표기 통일','맞춤법·문장부호·한자','한글 음역','따옴표·괄호','로마자','문장·내용']
def core(b,a,c=''):
    if re.sub(r'\s+',' ',b)==a and b!=a: return ('(빈칸 두 칸)','(한 칸)')
    x=b.split(' '); y=a.split(' ')
    ops=[o for o in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes() if o[0]!='equal']
    i1=ops[0][1]; i2=ops[-1][2]; j1=ops[0][3]; j2=ops[-1][4]
    if c=='맞춤법·문장부호·한자' and len(''.join(x[i1:i2]))<=3 and ''.join(x[i1:i2])!=''.join(y[j1:j2]) and i2<len(x) and j2<len(y) and x[i2]==y[j2]: i2+=1; j2+=1   # 짧은 낱말은 뒤 낱말 하나 더(그리고 나서)
    return (' '.join(x[i1:i2]),' '.join(y[j1:j2]))
def esc(s):
    s=s.replace('\\','\\\\').replace('|','\\|').replace('⏎',' ⏎ ')
    return re.sub(r'([*_`\[\]<>#~])',r'\\\1',s)
def pk(p):
    m=re.match(r'(\d+)',p); return int(m.group(1)) if m else 0
out={}
for c in CATS:
    xs=[x for x in R if x['cat']==c]
    g=collections.OrderedDict()
    for x in xs:
        k=core(x['before'],x['after'],c)
        g.setdefault(k,[]).append(x)
    lines=[f"## {CATS.index(c)+1}. {c} — {len(xs)}곳",'','| 쪽 | 고치기 전 | 고친 뒤 | 회차 |','| --- | --- | --- | --- |']
    for (cb,ca),ys in sorted(g.items(),key=lambda kv:pk(kv[1][0]['page'])):
        pages=[]; [pages.append(y['page']) for y in ys if y['page'] not in pages]
        pg=', '.join(pages) if len(pages)<=12 else ', '.join(pages[:12])+f' 외 {len(pages)-12}쪽'
        cnt=f" ({len(ys)}곳)" if len(ys)>1 else ''
        b,a=(ys[0]['before'],ys[0]['after']) if len(ys)==1 else (cb,ca)
        rd=sorted({('1회차' if '1회차' in s else '2회차' if '2회차' in s else '3회차' if '3회차' in s else '손 교정') for y in ys for s in y['src'].split('; ')})
        lines.append(f"| {esc(pg)}{cnt} | {esc(b)} | {esc(a)} | {'·'.join(rd)} |")
    out[c]=dict(md='\n'.join(lines),rows=len(g),n=len(xs))
    print(c,len(g),len(xs),len(out[c]['md']))
json.dump(out,open('/tmp/d40fin/md.json','w'),ensure_ascii=False)
