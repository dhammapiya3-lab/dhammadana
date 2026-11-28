import docx, json, re
d=docx.Document('in.docx')
# section headings order: paragraphs 5-12 part1 chapters, 15-22 part2; tables in order
heads=[p.text for p in d.paragraphs if p.style.name=='Heading 2']
out=[]
for ti,t in enumerate(d.tables):
    part=1 if ti<8 else 2
    sec=re.sub(r'\s*\(\d+건\)','',heads[ti]).strip()
    for r in t.rows[1:]:
        c=[x.text for x in r.cells]
        m=re.match(r'(\d+)\s*\n?\s*(.*)',c[0].strip(),re.S)
        num=int(m.group(1)); tag=m.group(2).strip()
        star='★' in tag; tag=tag.replace('★','').strip()
        why=c[3]; orig=''
        if '원문:' in why:
            why,orig=why.split('원문:',1); why=why.strip(); orig=orig.strip()
        out.append(dict(part=part,sec=sec,p=num,tag=tag,star=star,a=c[1],b=c[2],why=why,en=orig))
json.dump(out,open('cm.json','w'),ensure_ascii=False,indent=0)
print(len(out))
import collections; print(collections.Counter(x['tag'] for x in out))
