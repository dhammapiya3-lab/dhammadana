"""한국어 번역본(한글 파일에서 뽑은 글)과 영어 원서 문단을 문장으로 나눈다.
글자는 바꾸지 않는다 — 문단 안 문장의 처음·끝 자리만 셈.
결과: ko_sents.json, en_sents.json = [{"p": 문단 번호, "s": 시작, "e": 끝, "t": 문장, "h": 제목인지}]
"""
import json, re

END = r'[.?!…](?:[’”\'"」』)\]]+)?(?=\s|$)'

def split(t):
    out = []; i = 0
    for m in re.finditer(END, t):
        j = m.end()
        # 'Mr.' 'U.' 같은 줄임 뒤에서는 나누지 않음
        if re.search(r'(?:\bMr|\bMrs|\bDr|\bSt|\bNo|\b[A-Z])\.$', t[i:j]) or re.fullmatch(r'\s*\d+\.', t[i:j]): continue
        seg = t[i:j]
        if seg.strip(): out.append((i + len(seg) - len(seg.lstrip()), j))
        i = j
    if t[i:].strip():
        s = i + len(t[i:]) - len(t[i:].lstrip()); out.append((s, len(t.rstrip())))
    return out

def is_head(t):
    t = t.strip()
    if re.match('[‘“\'"]', t) or t.endswith(',') or t.endswith('기를'): return False
    return len(t) <= 60 and not re.search(r'[.?!…’”\'"]$', t) and not re.match(r'\d+\.\s', t)

# 한국어 문단: 빈 줄이 아닌 줄 하나가 문단 하나
ko_lines = open('ko.txt', encoding='utf-8').read().split('\n')
KP = [l for l in ko_lines if l.strip()]
EP = json.load(open('en_paras2.json'))

def sents(paras, get):
    S = []
    for pi, p in enumerate(paras):
        t = get(p)
        h = is_head(t)
        for s, e in (split(t) if not h else [(len(t) - len(t.lstrip()), len(t.rstrip()))]):
            S.append(dict(p=pi, s=s, e=e, t=t[s:e], h=h))
    return S

KS = sents(KP, lambda x: x); ES = sents(EP, lambda x: x['t'])
json.dump(dict(paras=KP, sents=KS), open('ko_sents.json', 'w'), ensure_ascii=False)
json.dump(dict(paras=EP, sents=ES), open('en_sents.json', 'w'), ensure_ascii=False)
# 글자 대조: 문장을 이어 붙이면(빈칸 빼고) 문단과 같아야 함
for P, S, g in ((KP, KS, lambda x: x), (EP, ES, lambda x: x['t'])):
    for pi, p in enumerate(P):
        a = re.sub(r'\s', '', g(p)); b = re.sub(r'\s', '', ''.join(s['t'] for s in S if s['p'] == pi))
        assert a == b, (pi, a[:80], b[:80])
print('ko', len(KP), 'paras', len(KS), 'sents, heads', sum(s['h'] for s in KS))
print('en', len(EP), 'paras', len(ES), 'sents, heads', sum(s['h'] for s in ES))
