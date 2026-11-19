# tesseract 로 그림 속 글 덩어리(글 영역·영어) 찾기: python3 tx.py SID [쪽...]
import sys,subprocess,csv,io,os,re
book='Vinaya-Stories'; sid=sys.argv[1]; only=set(map(int,sys.argv[2:]))
d=f'/home/claude/rev/{book}/{sid}'
for f in sorted(os.listdir(d)):
    n=int(f[:2])
    if only and n not in only: continue
    out=subprocess.run(['tesseract',f'{d}/{f}','-','-l','eng','--psm','3','tsv'],capture_output=True,text=True).stdout
    R=list(csv.DictReader(io.StringIO(out),delimiter='\t',quoting=csv.QUOTE_NONE))
    bl={}
    for r in R:
        if r['level']!='5' or not r['text'].strip() or float(r['conf'])<30: continue
        k=(r['block_num'],r['par_num'])
        x,y,w,h=map(int,(r['left'],r['top'],r['width'],r['height']))
        b=bl.setdefault(k,{'x0':x,'y0':y,'x1':x+w,'y1':y+h,'lines':{},'hs':[]})
        b['x0']=min(b['x0'],x);b['y0']=min(b['y0'],y);b['x1']=max(b['x1'],x+w);b['y1']=max(b['y1'],y+h)
        b['lines'].setdefault(r['line_num'],[]).append(r['text']); b['hs'].append(h)
    for k,b in bl.items():
        t=' / '.join(' '.join(v) for v in b['lines'].values())
        if len(re.sub(r'[^A-Za-z]','',t))<4: continue
        hs=sorted(b['hs']); print(n,[b['x0'],b['y0'],b['x1'],b['y1']],'h',hs[len(hs)//2],len(b['lines']),'|',t)
