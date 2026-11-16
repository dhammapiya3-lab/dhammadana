"""『생각할 거리를 드립니다』(DL-0005) ↔ 미얀마어 원서 『သိစရာ၊ တွေးစရာ』 짝 자료 만들기 (운영자 요청, 2026-11-17)

원서 PDF(sagarwarmyae.net 스캔본, 50쪽, 한 쪽에 책 두 쪽)는 글자층이 없는 그림이라 글자 인식(tesseract mya)은 참고만 하고,
쪽 그림을 보며 옮겨 적은 tools/parallel/dl0005_my.txt 를 원서 글로 씀 ('@ N' = 원서 쪽, 빈 줄 = 문단, '## ' 제목, '>> ' 서명).
잠언집이라 순서를 지키는 짝짓기 대신 LaBSE 뜻 비교 + 전체 최적 짝(헝가리안)으로 짝짓고, 손으로 정한 짝(PIN)을 더함.
한국어판에서 순서를 바꿔 실은 잠언은 note '원서와 순서가 다릅니다'(가장 긴 순서 사슬 LIS 밖의 짝).
한국어 본문(쪽·문단)을 고치면 다시 돌림:  python3 tools/parallel/my_dl0005.py
"""
import json, re, os, datetime, bisect
import numpy as np
from scipy.optimize import linear_sum_assignment
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(os.path.join(REPO, 'content/texts/DL-0005.json')))

# ---------- 원서 ----------
OR = []; pg = ''
for blk in re.split(r'\n\s*\n', open(os.path.join(REPO, 'tools/parallel/dl0005_my.txt')).read().strip()):
    ls = blk.split('\n')
    if ls[0].startswith('@'): pg = ls[0][1:].strip(); ls = ls[1:]
    if not ls: continue
    s = '\n'.join(ls).strip(); k = 'p'
    if s.startswith('## '): k, s = 'h', s[3:]
    if s.startswith('>> '): s = s[3:]
    n = int(pg) if pg.isdigit() else None
    pdf = str(n // 2 + 4) if n is not None else ('2~3' if pg == '' else '50')   # 한 PDF 쪽에 책 두 쪽: 책 n쪽 = PDF n//2+4쪽, 머리말 PDF 2~3쪽, 뒤표지 PDF 50쪽
    OR.append({'pg': '' if pg == 'နောက်ကျော' else pg, 'pdf': pdf, 'k': k, 't': s, 'back': pg == 'နောက်ကျော'})

# ---------- 한국어 (app.js paras 와 같은 규칙) ----------
body = T['body']; pages = []
for m in re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M): pages.append([m.group(1), m.end()])
for i, p in enumerate(pages):
    end = pages[i + 1][1] - len(re.search(r'===[^\n]*===\s*$', body[:pages[i + 1][1]]).group(0)) if i + 1 < len(pages) else len(body)
    p.append(body[p[1]:end].strip())
def paras(t): return ['\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]
def plain(s):
    s = re.sub(r'^(## |\^\^ |:: |>> |\+\+ |\|\| |%% )', '', s, flags=re.M); return re.sub(r'\*\*|==', '', s)
KO = []
for n, (lab, _, txt) in enumerate(pages, 1):
    for s, para in enumerate(paras(txt)):
        if para.strip() == '❦' or para.startswith('!['): continue
        KO.append({'key': f'{n}:{s}', 'pg': lab, 't': para})
KI = {k['key']: i for i, k in enumerate(KO)}

from sentence_transformers import SentenceTransformer
mdl = SentenceTransformer('sentence-transformers/LaBSE')
enc = lambda xs: mdl.encode(xs, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
KE = enc([plain(x['t']).replace('\n', ' ') for x in KO]); OE = enc([x['t'].replace('\n', ' ') for x in OR])
S = KE @ OE.T

def kidx(pfx): return next(i for i, k in enumerate(KO) if (plain(k['t']) == pfx[1:] if pfx[0] == '=' else plain(k['t']).startswith(pfx)))   # '=' 로 시작하면 글 전체가 같은 문단
def oidx(pfx): return next(j for j, o in enumerate(OR) if o['t'].startswith(pfx) and not o['back'])
# 손으로 정한 짝 (한국어 문단 첫머리들 → 원서 문단 첫머리들, 빈 목록 = 짝 없음)
PIN = [
    (['Thoughts rule', '생각이 세계를', 'Ideas have', '사상과 철학에는 그들'], ['Thoughts rule']),
    (['사상과 철학에는 생명이'], ['အယူအဆ အတွေးအခေါ်တွေမှာ အသက်']),
    (['올바른 사상은', '이 책에 담은'], ['ဒီအယူအဆက', 'ဒါကြောင့် အယူအဆတွေကို', 'တိုတိုနဲ့လိုရင်း']),
    (['=우 조띠까 사야도'], ['ဆရာတော်ဦးဇောတိက']),
    (['우 조띠까 사야도\nU Jotika'], []),
    (['껍데기를 벗기지'], ['မြေပဲဆံကို']),
    (['Honesty takes'], ['Honesty takes', 'ရိုးသားမှုရှိဖို့ဟာ']),
    (['Honesty is the best'], ['"Honesty is the best', '“ရိုးသားမှုဟာ']),
    (['어려움이 없다면 성공할'], ['ဘာအခက်အခဲမှ မရှိရင်']),
    (['목적이 없으면 도착도'], []),
    (['내실이 꽉 차지'], ['အတွင်းမှာ အနှစ်သာရ']),
    (['날이 갈수록 마음과 지혜가'], ['အရင်တုန်းကထက်']),
    (['인류 역사의 원초적인'], ['လူ့သမိုင်းတစ်လျှောက်လုံးမှာ']),
    (['사람들은 자신을\n가치', '그러나 정말 존경받고'], ['လူတွေဟာ ကိုယ့်ကိုယ်ကိုကိုယ်တန်ဖိုး']),
    (['유사 이래로'], ['လူ့သမိုင်းတစ်လျှောက်လုံးမှာ']),
]
FRONT_BACK = re.compile(r'^(:: |## 일러두기|• |이에 따라|역자 :|한국테라와다|미얀마인들이|## 생각할 거리|전자책 발행|지은이 /|편집 /|펴낸곳|연락처|\* 본 도서|상업적 목적)')
groups = []; usedK = set(); usedO = set()
for ks, os_ in PIN:
    ki = [kidx(k) for k in ks]; oi = [oidx(o) for o in os_]
    usedK.update(ki); usedO.update(oi)
    if oi: groups.append((ki, oi, True))
skipK = {i for i, k in enumerate(KO) if FRONT_BACK.match(k['t'])}
freeK = [i for i in range(len(KO)) if i not in usedK and i not in skipK]
freeO = [j for j in range(len(OR)) if j not in usedO and not OR[j]['back'] and OR[j]['t'] != 'အမှာစာ']
sub = S[np.ix_(freeK, freeO)]
r, c = linear_sum_assignment(-sub)
TH = 0.55   # 이보다 낮으면 짝짓지 않음 (역자가 다른 책에서 더한 잠언 등)
for a, b in zip(r, c):
    if sub[a, b] >= TH: groups.append(([freeK[a]], [freeO[b]], False))
groups.sort(key=lambda g: g[0][0])

# ---------- 순서가 다른 짝: 원서 번호의 가장 긴 오름차순 사슬(LIS) 밖 ----------
js = [g[1][0] for g in groups]; tails = []; ti = []; P = [-1] * len(js)
for k, x in enumerate(js):
    p = bisect.bisect_left(tails, x)
    if p == len(tails): tails.append(x); ti.append(k)
    else: tails[p] = x; ti[p] = k
    P[k] = ti[p - 1] if p else -1
lis = set(); k = ti[-1] if ti else -1
while k >= 0: lis.add(k); k = P[k]

out = []
for gi, (ki, oi, pin) in enumerate(groups):
    sc = round(float(np.mean([S[a, b] for a in ki for b in oi])), 3)
    g = {'ko': [KO[i]['key'] for i in ki], 'or': oi,
         's': [{'ko': [[KO[i]['key'], 0, len(KO[i]['t'])] for i in ki], 'or': [[j, 0, len(OR[j]['t'])] for j in oi], 'sc': sc}]}
    if pin: g['pin'] = 1
    if gi not in lis:
        g['note'] = f"원서와 순서가 다릅니다 — 원서 {OR[oi[0]]['pg']}쪽(PDF {OR[oi[0]]['pdf']}쪽)에 있는 글입니다." if OR[oi[0]]['pg'] else '원서와 순서가 다릅니다.'
    out.append(g)

res = {'book': 'DL-0005', 'lang': 'my', 'title': 'သိစရာ၊ တွေးစရာ', 'by': 'ဆရာတော်ဦးဇောတိက', 'source': '',
       'made': datetime.date.today().isoformat(),
       'method': 'LaBSE 뜻 비교 + 전체 최적 짝(잠언집이라 순서를 강제하지 않음), 앞뒤 부분은 손으로. 미얀마어 원서는 스캔본이라 쪽 그림을 보며 옮겨 적음',
       'note': '짝 자료: groups[].ko = 한국어 문단 열쇠 "쪽 순번:문단 순번"(content/texts 본문 기준), or = 원서 문단 번호, s = 문장 짝, sc = 뜻 비슷함(0~1), note = 원서와 순서가 다른 짝',
       'orig': [{'pg': o['pg'], 'pdf': o['pdf'], 'k': o['k'], 't': o['t']} for o in OR], 'groups': out}
json.dump(res, open(os.path.join(REPO, 'content/parallel/DL-0005.my.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
pairedK = {i for g in groups for i in g[0]}; pairedO = {j for g in groups for j in g[1]}
print('짝 묶음', len(out), '평균 뜻 비슷함', round(float(np.mean([g['s'][0]['sc'] for g in out])), 3))
print('순서가 다른 짝:'); [print('  ', g['ko'], plain(KO[KI[g['ko'][0]]]['t'])[:30].replace('\n', ' '), '→', g['note']) for g in out if g.get('note')]
print('짝 없는 한국어 잠언:'); [print('  ', k['pg'], plain(k['t'])[:40].replace('\n', ' ')) for i, k in enumerate(KO) if i not in pairedK and i not in skipK]
print('짝 없는 원서:'); [print('  ', o['pg'] or ('뒤표지' if o['back'] else '앞'), o['t'][:30].replace('\n', ' ')) for j, o in enumerate(OR) if j not in pairedO]

# ---------- 미얀마어 원서 글 파일 (운영자 요청, 2026-11-17): 쪽마다 '=== 책 N쪽 (PDF M쪽) ===' ----------
lines = ['သိစရာ၊ တွေးစရာ — ဆရာတော်ဦးဇောတိက', '(『생각할 거리를 드립니다』 미얀마어 원서. ရေတံခွန်စာပေ 초판 2001, 스캔 PDF 를 보며 옮겨 적음. 쪽 표시: 책에 인쇄된 쪽 (PDF 파일 쪽))', '']
last = None
for o in OR:
    lab = ('뒤표지 (PDF 50쪽)' if o['back'] else f"머리말 (PDF {o['pdf']}쪽)" if not o['pg'] else f"{o['pg']}쪽 (PDF {o['pdf']}쪽)")
    if lab != last: lines += [f'=== {lab} ===', '']; last = lab
    lines += [o['t'], '']
os.makedirs(os.path.join(REPO, 'tools/out/parallel'), exist_ok=True)
open(os.path.join(REPO, 'tools/out/parallel/DL-0005_미얀마어_원서.txt'), 'w').write('\n'.join(lines))
print('글 파일 → tools/out/parallel/DL-0005_미얀마어_원서.txt')
