import json,re,collections
R=json.load(open('/tmp/d41fin/rows.json'))
REN={'로마자':'로마자·빠알리 소리 줄'}
CATS=['로마자','띄어쓰기','맞춤법·문장부호·한자','따옴표·괄호','한글 음역','같은 이름 통일','문장·내용','경전 출처','짜임(단락 옮기기·소제목)']
fix=lambda s:re.sub('[\U000F0000-\U000FFFFF]','(깨진 따옴표 글자)',s)
def esc(s): 
    s=fix(s).replace('\\','\\\\').replace('|','\\|').replace('⏎',' ⏎ ')
    s=re.sub(r'([*_`\[\]<>#~])',r'\\\1',s)
    return s
def shortsrc(s): return s.replace(' (1회차)','').replace('교정 목록 ','목록 ')
out={}
for c in CATS:
    xs=[x for x in R if x['cat']==c]
    g=collections.OrderedDict()
    for x in xs: g.setdefault((x['before'],x['after']),[]).append(x)
    n=sum(x['n'] for x in xs)
    lines=[f"## {len(out)+1}. {REN.get(c,c)} — {n}곳",'']
    lines+=['| 쪽 | 고치기 전 | 고친 뒤 | 근거 |','| --- | --- | --- | --- |']
    for (b,a),ys in g.items():
        pages=[]; [pages.append(y['page']) for y in ys if y['page'] not in pages]
        cnt=f" ({len(ys)}곳)" if len(ys)>1 else ''
        srcs=[]; [srcs.append(shortsrc(y['src'])) for y in ys if shortsrc(y['src']) not in srcs]
        lines.append(f"| {esc(', '.join(pages))}{cnt} | {esc(b)} | {esc(a)} | {esc('; '.join(srcs))} |")
    out[c]=('\n'.join(lines),len(g),n)
    print(c,len(g),n,len(out[c][0]))
json.dump(out,open('/tmp/d41fin/md.json','w'),ensure_ascii=False)
