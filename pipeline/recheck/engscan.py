import json,subprocess,re,os,sys
from concurrent.futures import ThreadPoolExecutor
STOP=set('this that with from have were they them their there what when which will would your about into been than then also such only very more most some'.split())
jobs=[]
for book in sorted(os.listdir('/tmp/qa')):
    if not os.path.isdir(f'/tmp/qa/{book}'): continue
    for sid in sorted(os.listdir(f'/tmp/qa/{book}')):
        p=f'/home/claude/sb/data/ocr/{book}/{sid}.json'
        if not os.path.exists(p): continue
        o=json.load(open(p))
        for n,pg in enumerate(o,1):
            f=f'/tmp/qa/{book}/{sid}/{n:02d}.jpg'
            if not os.path.exists(f): continue
            src=' '.join([b['en'] for b in pg['boxes']]+pg.get('loose',[]))
            W={w.lower() for w in re.findall(r'[A-Za-z]{4,}',src)}-STOP
            jobs.append((book,sid,n,f,W))
def run(j):
    book,sid,n,f,W=j
    t=subprocess.run(['tesseract',f,'-','-l','eng','--psm','11'],capture_output=True,text=True).stdout
    hit=sorted({w for w in re.findall(r'[A-Za-z]{4,}',t) if w.lower() in W})
    return (book,sid,n,hit)
with ThreadPoolExecutor(8) as ex:
    for book,sid,n,hit in ex.map(run,jobs):
        if len(hit)>=2: print(book,sid,n,hit,flush=True)
print('DONE',len(jobs),flush=True)
