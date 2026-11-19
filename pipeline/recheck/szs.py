import sys,json; sys.path.insert(0,'/home/claude/sb/pipeline')
import render
sid,book=sys.argv[1],sys.argv[2]
pages=json.load(open(f'/home/claude/sb/ko/{book}/{sid}.json'))
for i,p in enumerate(pages,1):
    render.render(f'/home/claude/rev/{book}/{sid}/{i:02d}.jpg',p['boxes'])
    d=getattr(render.render,'drawn',None) or []
    s=[x['size'] for x in d]; q=[f'{n}:{k}:{m}' for n,k,m in render.render.qa]
    if (s and min(s)<14) or q or any(x.get('overflow') for x in d): print(i,s,q)
print('checked',len(pages))
