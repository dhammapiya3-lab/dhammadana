import sys, json; sys.path.insert(0,'/home/claude/sb/pipeline/recheck')
from build import build
C=lambda r,ko=None,**k: dict({'rect':r,'ko':ko,'cover':'S','align':'center',**k})
L=lambda r,ko=None,**k: C(r,ko,**{'align':'left',**k})
import numpy as np
from PIL import Image
def samp(book,SID,n,r):
    a=np.array(Image.open(f'/home/claude/rev/{book}/{SID}/{n:02d}.jpg').convert('RGB'))[r[1]+5:r[3]-5,r[0]+5:r[2]-5].reshape(-1,3); L=a.sum(1)
    return np.median(a[L>np.percentile(L,50)],0).astype(int).tolist()
def sampd(book,SID,n,r):
    a=np.array(Image.open(f'/home/claude/rev/{book}/{SID}/{n:02d}.jpg').convert('RGB'))[r[1]+5:r[3]-5,r[0]+5:r[2]-5].reshape(-1,3); L=a.sum(1)
    return np.median(a[L<np.percentile(L,50)],0).astype(int).tolist()
def run(SID,T,book='After-Awakening'):
    for n,bs in T.items():
        for b in bs:
            if b.get('cover')=='S': b['cover']=samp(book,SID,n,b['rect'])
            if b.get('cover')=='D': b['cover']=sampd(book,SID,n,b['rect']); b.setdefault('dark',True)
    o=json.load(open(f'/home/claude/sb/data/ocr/{book}/{SID}.json')); POST={}
    for n,p in enumerate(o,1):
        items=T.get(n,[])
        base=[None]*len(p['boxes']); rest=[]
        for b in items:
            b=dict(b)
            if '_seed' in b: i=b.pop('_seed'); base[i]=b.pop('ko'); POST[(n,i)]=b
            else: rest.append(b)
        T[n]=base+rest
    build(SID,T,book=book)
    pth=f'/home/claude/sb/ko/{book}/{SID}.json'; d=json.load(open(pth))
    for (n,i),kw in POST.items():
        k=sum(1 for j in range(i) if T[n][j]); d[n-1]['boxes'][k].update(kw)
    json.dump(d,open(pth,'w'),ensure_ascii=False,indent=1)
