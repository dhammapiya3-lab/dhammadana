# 그리지 않고 건너뛴 상자 찾기 (render 가 글자를 못 찾으면 조용히 건너뜀)
import sys,json,glob,os; sys.path.insert(0,'/home/claude/sb/pipeline')
import render
book=sys.argv[1]; sids=sys.argv[2:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(f'/home/claude/sb/ko/{book}/*.json'))
for sid in sids:
    pages=json.load(open(f'/home/claude/sb/ko/{book}/{sid}.json'))
    for i,p in enumerate(pages,1):
        f=f'/home/claude/rev/{book}/{sid}/{i:02d}.jpg'
        if not os.path.exists(f): continue
        render.render(f,p['boxes'])
        want=sum(1 for b in p['boxes'] if b.get('ko') or b.get('parts'))
        got=len(render.render.drawn or [])
        if got<want: print('SKIP',sid,i,want,got)
print('skip check done')
