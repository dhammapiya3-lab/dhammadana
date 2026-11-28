import sys, json, re, fitz
from PIL import Image
B='/home/claude/dhammadana/tools/parallel/th_dl0040.py'
s=open(B).read(); head=s.split('pages = [')[0]; tail=s.split("JOIN = ")[1]
ns={'__file__':B}; sys.argv=[B,'ocrC']; exec(head,ns)
JOIN=eval(tail.split('\n')[0].split('.split')[0]).split('|')
def post(t):
    for w in JOIN: t=t.replace(w,w.replace(' ',''))
    for (a,b) in []: pass
    t=re.sub(r'(?<=\s)\.(?=[ก-ฮเ-ไ])','',t); t=re.sub(r'(?<=[ก-๎]) \. (?=[ก-ฮเ-ไ])',' ',t)
    t=re.sub(r'(?<=[ก-ฮะ-ฺเ-ๅ็-๎])(?=[๐-๙])',' ',t); t=re.sub(r'(?<=[๐-๙])(?=[ก-ฮเ-ไ])',' ',t)
    t=re.sub(r'(?<!รำ)(?<!พัว)(?<!ติด)(?<!กี่)(?<!แปด)(?<!ดวง)(?<!ห่อ)(?<!ผูก)(?<!ร้อยละ)(?<!เป็น)(?<!จำนวน)พัน(?=ทุกข|จาก|ไป|ภัย|โทษ|เขต|แดน|กรรม|มือ|ต้อง|การ|สภาพ|ดง|กำลัง|หมู่)','พ้น',t)
    t=re.sub(r'(?:(?<=หลุด)|(?<=รอด)|(?<=ไม่)|(?<=ล้น)|(?<=ให้))พัน(?=\s|$)','พ้น',t)
    return re.sub(r'  +',' ',t)
d=fitz.open('src.pdf'); tot=0
OUT={}
for i in range(5,276):
    pdf=i+1; dd=json.load(open(f'ocrC/{i:03d}.json'))
    if pdf in ns['NOPG']: continue
    L=[l for l in dd['lines'] if 250<l['y0']<2990 and l['y1']-l['y0']>=28]
    rows=[]
    for l in L:
        t=ns['clean'](l['t'])
        t0=ns['tokfix'](t)
        for (fp,a,b) in ns['FIX']:
            if fp==pdf and a in t: t=t.replace(a,b)
        t=ns['tokfix'](t); hy,ht=ns['HEADS'].get(pdf,(False,None))
        if ht and isinstance(hy,int) and abs(l['y0']-hy)<6: rows.append((l,'제목',ht,ht)); continue
        flag=''
        if (pdf,l['y0']) in ns['SKIP'] or not t or (len(ns['THAI'].findall(t))<3 and not re.search(r'[0-9๐-๙]',t)) or ns['words_ok'](t)<.6: flag='뺌'
        else: t=post(ns['fixspace'](t))
        if flag=='' : t0=post(ns['fixspace'](t0))
        rows.append((l,flag,t,t0))
    txt=[]; ims=[]
    rows=[r for r in rows]
    keep=[(n,r) for n,r in enumerate(rows,1) if r[2]!=r[3] or (r[1]=='뺌' and (pdf,r[0]['y0']) not in ns['SKIP'] and False)]
    if not keep: continue
    for n,(l,f,t,t0) in keep:
        txt.append(f'{n}\t{f}\t{t}')
        p=d[i].get_pixmap(dpi=200,colorspace=fitz.csGRAY,clip=fitz.Rect(l['x0']*72/300-4,l['y0']*72/300-4,l['x1']*72/300+4,l['y1']*72/300+4))
        ims.append((n,Image.frombytes('L',(p.width,p.height),p.samples)))
    open(f'rev2/p{pdf:03d}.txt','w').write('\n'.join(txt)+'\n')
    from PIL import ImageDraw
    for k in range(0,len(ims),9):
        ch=ims[k:k+9]; W=max(x.width for _,x in ch)+60; H=sum(x.height+10 for _,x in ch)
        c=Image.new('L',(W,H),255); dr=ImageDraw.Draw(c); y=0
        for n,x in ch: dr.text((5,y+x.height//2-5),str(n),fill=0); c.paste(x,(55,y)); y+=x.height+10
        c.save(f'rev2/p{pdf:03d}_{k//9+1}.png')
    tot+=len(keep)
print(tot)
