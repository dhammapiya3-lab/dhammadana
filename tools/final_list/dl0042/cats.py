"""교정 목록 한 줄(a→b)의 묶음 — 글자 모양으로 정하고, 손으로 정한 것은 OVR (DL-0040, 2026-11-25 → DL-0042 2026-11-28 옮김)"""
import re
Q='"\'“”‘’()[]〔〕「」『』《》〈〉'
NAME={'티베트':'티벳'}
def plain(s): return re.sub(r'\*\*|°°','',s)
def cat(f):
    a,b=plain(f['a']),plain(f['b'])
    if f.get('re') and f['a']==r'(?<=\S) {2,}(?=\S)': return '띄어쓰기'
    if re.sub(r'\s','',a)==re.sub(r'\s','',b): return '띄어쓰기'
    if a.replace('～','~')==b: return '맞춤법·문장부호·한자'
    if re.sub('['+re.escape(Q)+r'\s]','',a)==re.sub('['+re.escape(Q)+r'\s]','',b): return '따옴표·괄호'
    if any(k in a and v in b for k,v in NAME.items()): return '같은 표기 통일'
    L=r'[A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F]+'; la=re.findall(L,a); lb=re.findall(L,b)
    if la!=lb: return '로마자'
    return '맞춤법·문장부호·한자'
