import json,difflib,subprocess
def get_ops(B0,B1):
    a=B0.split('\n'); b=B1.split('\n'); assert len(a)==len(b),(len(a),len(b))
    ops=[];pos=0
    for x,y in zip(a,b):
        if x!=y:
            for t,i1,i2,j1,j2 in difflib.SequenceMatcher(None,x,y,autojunk=False).get_opcodes():
                if t!='equal': ops.append((pos+i1,pos+i2,y[j1:j2]))
        pos+=len(x)+1
    return ops
