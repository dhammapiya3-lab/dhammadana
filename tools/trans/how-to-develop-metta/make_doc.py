"""번역 교정 도구에 넣을 자료 파일(JSON)을 만든다.
줄(row) 하나 = 짝지은 문장 묶음: o 원서, r 대조 번역본(없으면 ''), t 우리 번역(고칠 글), t0 처음 번역.
kp: 우리 번역의 문단 번호(번역본만 보기에서 문단을 나눌 때), h: 제목 줄.
"""
import json, re, hashlib, datetime
K = json.load(open('ko_sents.json')); E = json.load(open('en_sents.json')); P = json.load(open('pairs.json'))
KS, ES, EP = K['sents'], E['sents'], E['paras']

def pglabel(pg):
    return f'원서 {pg - 10}쪽' if pg >= 11 else f'원서 앞쪽 (PDF {pg}쪽)'

def join(S, idx, para_key):
    out = ''; last = None
    for i in idx:
        s = S[i]
        if last is not None:
            out += '\n' if s['p'] != last else ' '
        out += s['t']; last = s['p']
    return out

rows = []; kp = 0
for n, p in enumerate(P):
    if p['k']: kp = KS[p['k'][0]]['p']
    o = join(ES, p['e'], 'p'); t = join(KS, p['k'], 'p')
    def spg(i):
        P_ = EP[ES[i]['p']]; s, e = ES[i]['s'], ES[i]['e']
        if 'brk' not in P_: return {P_['pg']}
        return ({P_['pg']} if s < P_['brk'] else set()) | ({P_['pg2']} if e > P_['brk'] else set())
    pgs = sorted(set().union(*[spg(i) for i in p['e']])) if p['e'] else []
    h = int(bool(p['k']) and all(KS[i]['h'] for i in p['k']) or (not p['k'] and all(ES[i]['h'] for i in p['e'])))
    # 우리 번역 문단이 새로 시작하는 줄인지 (번역본만 보기)
    k0 = p['k'][0] if p['k'] else None
    newp = int(k0 is not None and (k0 == 0 or KS[k0 - 1]['p'] != KS[k0]['p']))
    rows.append(dict(id=f'r{n + 1}', o=o, op=' · '.join(pglabel(g) for g in pgs), r='', t=t, t0=t, kp=kp, np=newp, h=h,
                     sc=p['sc']))
doc = dict(v=1, id='how-to-develop-metta', title='자애를 개발하는 방법 (How to Develop Metta)',
           cols=dict(o='영어 원서', r='대조 번역본', t='우리 번역'),
           info=dict(o='How to Develop Metta (Loving-Kindness), Chanmyay Myaing Sayadaw, Translated from Burmese by May Myint Oo (Mimmi), Edited by Judy Witheford, First Printing May 2008 (ISBN 978-983-41633-2-7) — 스캔본 PDF 를 글자 인식으로 옮김',
                     t='한국어 번역 원고(한글 파일)'),
           made=datetime.date.today().isoformat(), rows=rows)
json.dump(doc, open('how-to-develop-metta.trans.json', 'w'), ensure_ascii=False)
# 글자 대조: 우리 번역 줄을 모두 이으면(빈칸·줄바꿈 빼고) 한글 파일 글과 같아야 함
a = re.sub(r'\s', '', ''.join(K['paras'])); b = re.sub(r'\s', '', ''.join(r['t'] for r in rows))
assert a == b, 'ko mismatch'
ke = sorted(i for p in P for i in p['e']); kk = sorted(i for p in P for i in p['k'])
assert ke == list(range(len(ES))) and kk == list(range(len(KS))), 'cover'
a = re.sub(r'\s', '', ''.join(p['t'] for p in EP)); b = re.sub(r'\s', '', ''.join(ES[i]['t'] for i in ke))
assert a == b, 'en mismatch'
print(len(rows), 'rows', sum(1 for r in rows if r['t'] and r['o']), 'both', sum(1 for r in rows if not r['t']), 'en-only', sum(1 for r in rows if not r['o']), 'ko-only')
