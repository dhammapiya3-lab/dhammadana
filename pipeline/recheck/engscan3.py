import json,subprocess,re,os,sys
from concurrent.futures import ThreadPoolExecutor
STOP=set('this that with from have were they them their there what when which will would your about into been than then also such only very more most some'.split())
jobs=[]
SKIP={'Four-Rich-Men','Light-of-Asia','Rasavahini','Way-Beyond'}
for book in sorted(os.listdir('/tmp/qa')):
    if os.environ.get('BOOK') and book!=os.environ['BOOK']: continue
    if book in SKIP: continue
    if not os.path.isdir(f'/tmp/qa/{book}'): continue
    for sid in sorted(os.listdir(f'/tmp/qa/{book}')):
        p=f'/home/claude/sb/data/ocr/{book}/{sid}.json'
        if not os.path.exists(p): continue
        if (book,sid)<=tuple(os.environ.get('START','').split('/')+[''])[:2] and os.environ.get('START'): continue
        o=json.load(open(p))
        for n,pg in enumerate(o,1):
            f=f'/tmp/qa/{book}/{sid}/{n:02d}.jpg'
            if not os.path.exists(f): continue
            src=' '.join([b['en'] for b in pg['boxes']]+pg.get('loose',[]))
            W={w.lower() for w in re.findall(r'[A-Za-z]{4,}',src)}-STOP
            jobs.append((book,sid,n,f,W))
def run(j):
    book,sid,n,f,W=j
    import cv2
    g=cv2.cvtColor(cv2.imread(f),cv2.COLOR_BGR2GRAY)
    g=cv2.createCLAHE(clipLimit=4.0,tileGridSize=(8,8)).apply(cv2.resize(g,None,fx=2,fy=2))  # 흐린 글자도 보이게: 2배 + 대비 높임
    tmp=f'/tmp/eh_{os.getpid()}_{n}_{sid}.png'; cv2.imwrite(tmp,g)
    t=subprocess.run(['tesseract',tmp,'-','-l','eng','--psm','11'],capture_output=True,text=True).stdout; os.remove(tmp)
    hit=sorted({w for w in re.findall(r'[A-Za-z]{4,}',t) if w.lower() in W})
    return (book,sid,n,hit)
with ThreadPoolExecutor(4) as ex:
    for book,sid,n,hit in ex.map(run,jobs):
        if len(hit)>=1: print(book,sid,n,hit,flush=True)
print('DONE',len(jobs),flush=True)
