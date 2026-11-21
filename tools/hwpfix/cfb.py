import olefile, struct
SEC=512; MINI=64; CUT=4096
FREE=0xFFFFFFFF; EOC=0xFFFFFFFE; FATS=0xFFFFFFFD; NOS=0xFFFFFFFF
def keyname(n): return (len(n), n.upper())
def write_cfb(src_path, out_path, replace):
    """copy src OLE, replacing stream contents given in replace {path:bytes}"""
    o=olefile.OleFileIO(src_path)
    ents=o.direntries
    # build tree from olefile: root + children
    nodes=[]  # dict(name,type,clsid,ctime,mtime,data,children,state)
    def mk(de,path):
        n=dict(name=de.name,type=de.entry_type,clsid=de.clsid,state=de.dwUserFlags,ctime=de.createTime,mtime=de.modifyTime,children=[],data=b'')
        if de.entry_type==2:
            p='/'.join(path)
            n['data']=replace.get(p, o.openstream(p).read())
        for k in de.kids: n['children'].append(mk(k,path+[k.name]))
        return n
    root=mk(o.root,[])
    o.close()
    # flatten
    flat=[]
    def walk(n):
        n['id']=len(flat); flat.append(n)
        for c in n['children']: walk(c)
    walk(root)
    # sector data
    fat=[]; secs=[]  # list of 512-byte blocks (data sectors)
    def alloc(data):
        if not data: return EOC
        nsec=(len(data)+SEC-1)//SEC; start=len(secs)
        for k in range(nsec):
            secs.append(data[k*SEC:(k+1)*SEC].ljust(SEC,b'\0'))
            fat.append(start+k+1 if k<nsec-1 else EOC)
        return start
    # mini stream
    mini=bytearray(); minifat=[]
    for n in flat:
        if n['type']==2 and len(n['data'])<CUT:
            d=n['data']
            if not d: n['start']=EOC; continue
            nm=(len(d)+MINI-1)//MINI; st=len(mini)//MINI
            mini+=d.ljust(nm*MINI,b'\0')
            for k in range(nm): minifat.append(st+k+1 if k<nm-1 else EOC)
            n['start']=st
    for n in flat:
        if n['type']==2 and len(n['data'])>=CUT: n['start']=alloc(n['data'])
    root['start']=alloc(bytes(mini)) if mini else EOC
    root['size']=len(mini)
    mf=b''.join(struct.pack('<I',x) for x in minifat)
    mf_start=alloc(mf.ljust(((len(mf)+SEC-1)//SEC)*SEC,b'\xff')) if mf else EOC
    n_mf=(len(mf)+SEC-1)//SEC
    # directory tree: siblings balanced BST
    def bst(lst):
        if not lst: return NOS
        lst=sorted(lst,key=lambda n:keyname(n['name'])); m=len(lst)//2
        r=lst[m]; r['left']=bst(lst[:m]); r['right']=bst(lst[m+1:]); return r['id']
    for n in flat:
        n.setdefault('left',NOS); n.setdefault('right',NOS)
    for n in flat: n['child']=bst(n['children']) if n['type'] in (1,5) else NOS
    root['left']=root['right']=NOS
    def de(n):
        nm=n['name'].encode('utf-16-le')+b'\0\0'
        b=nm.ljust(64,b'\0')+struct.pack('<HBB',len(nm),n['type'],1)
        b+=struct.pack('<III',n['left'],n['right'],n['child'])
        clsid=olefile_clsid_bytes(n['clsid'])
        b+=clsid+struct.pack('<I',n['state'] or 0)
        b+=ftime(n['ctime'])+ftime(n['mtime'])
        size=root['size'] if n['type']==5 else (len(n['data']) if n['type']==2 else 0)
        st=n.get('start',0) if n['type'] in (2,5) else 0
        if n['type']==2 and not n['data']: st=EOC
        b+=struct.pack('<IQ',st,size)
        assert len(b)==128; return b
    dirb=b''.join(de(n) for n in flat)
    pad=(-len(dirb))%SEC
    empty=(b'\0'*64+struct.pack('<HBB',0,0,0)+struct.pack('<III',NOS,NOS,NOS)+b'\0'*16+b'\0'*4+b'\0'*16+struct.pack('<IQ',0,0))
    dirb+=empty*(pad//128)
    dir_start=alloc(dirb)
    # FAT sectors
    nfat=1
    while True:
        total=len(secs)+nfat
        if (total+SEC//4-1)//(SEC//4)<=nfat: break
        nfat+=1
    assert nfat<=109
    fat_start=len(secs)
    for k in range(nfat): fat.append(FATS)
    fat+= [FREE]*(nfat*(SEC//4)-len(fat))
    fatb=b''.join(struct.pack('<I',x) for x in fat)
    for k in range(nfat): secs.append(fatb[k*SEC:(k+1)*SEC])
    difat=[fat_start+k for k in range(nfat)]+[FREE]*(109-nfat)
    hdr=bytes.fromhex('D0CF11E0A1B11AE1')+b'\0'*16+struct.pack('<HHHHH',0x3E,3,0xFFFE,9,6)+b'\0'*6
    hdr+=struct.pack('<IIIIIIIIII',0,nfat,dir_start,0,CUT,mf_start,n_mf,EOC,0,0)[:-8]  # placeholder fix below
    hdr=bytes.fromhex('D0CF11E0A1B11AE1')+b'\0'*16+struct.pack('<HHHHH',0x3E,3,0xFFFE,9,6)+b'\0'*6
    hdr+=struct.pack('<IIIIIIIII',0,nfat,dir_start,0,CUT,mf_start,n_mf,EOC,0)
    hdr+=b''.join(struct.pack('<I',x) for x in difat)
    assert len(hdr)==512,len(hdr)
    open(out_path,'wb').write(hdr+b''.join(secs))
import datetime
def ftime(t):
    if not t: return b'\0'*8
    if isinstance(t,int): return struct.pack('<Q',t)
    v=int((t-datetime.datetime(1601,1,1)).total_seconds()*10**7)
    return struct.pack('<Q',v)
def olefile_clsid_bytes(s):
    if not s: return b'\0'*16
    import uuid
    return uuid.UUID(s).bytes_le
