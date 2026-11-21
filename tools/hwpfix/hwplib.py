import olefile, zlib, struct
def rd(o,p):
    return zlib.decompress(o.openstream(p).read(), -15)
def recs(data):
    out=[];i=0
    while i<len(data):
        h=struct.unpack_from('<I',data,i);h=h[0];i+=4
        tag=h&0x3ff; lev=(h>>10)&0x3ff; sz=h>>20
        if sz==0xfff: sz=struct.unpack_from('<I',data,i)[0]; i+=4
        out.append([tag,lev,data[i:i+sz]]); i+=sz
    return out
def pack(rs):
    b=bytearray()
    for tag,lev,d in rs:
        sz=len(d)
        if sz>=0xfff:
            b+=struct.pack('<I',tag|(lev<<10)|(0xfff<<20)); b+=struct.pack('<I',sz)
        else: b+=struct.pack('<I',tag|(lev<<10)|(sz<<20))
        b+=d
    return bytes(b)
CHAR1={0,10,13,24,25,26,27,28,29,30,31}
def tokens(d):
    """PARA_TEXT bytes -> list of (wchar_index, kind, value); kind 'c' char, 'x' control(8 wchars), 'b' single ctrl"""
    w=struct.unpack('<%dH'%(len(d)//2),d); out=[];i=0
    while i<len(w):
        c=w[i]
        if c<32:
            if c in CHAR1: out.append((i,'b',c)); i+=1
            else: out.append((i,'x',w[i:i+8])); i+=8
        else:
            # surrogate pairs
            if 0xD800<=c<0xDC00 and i+1<len(w):
                out.append((i,'c',chr(0x10000+((c-0xD800)<<10)+(w[i+1]-0xDC00)))); i+=2
            else: out.append((i,'c',chr(c))); i+=1
    return out
