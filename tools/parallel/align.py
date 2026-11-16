"""원서 대조 짝짓기 — 한국어 글로 읽기 본문(content/texts/<ID>.json)과 원서 문단 목록을 문장마다 짝지어
content/parallel/<ID>.<말>.json 을 만든다. (운영자 요청, 2026-11-15 — 다른 곳에도 쓸 수 있게 짝 자료를 따로 저장)

  python3 tools/parallel/align.py DL-0014 en tools/out/parallel/DL-0014.en.paras.json [--title …] [--by …] [--source …]

방법:
1. 한국어: 읽기 화면과 같은 단위(쪽 순번 n, 문단 순번 s)로 문단을 나눔. 각주([^n]:)·차례(%%)·그림 문단은 짝짓지 않음.
   원서: 원서 문단(쪽 이름 pg, 종류 k: h 제목·p 문단·sep 구분).
2. 문장 나누기: 마침표·물음표·느낌표(+닫는 따옴표) 뒤, 문단 안의 줄 바꿈.
3. LaBSE(여러 말을 함께 이해하는 문장 비교 모델)로 문장마다 뜻 벡터를 만들고,
   순서를 지키며(앞뒤가 엇갈리지 않게) 1:1·1:2·2:1·2:2·1:3·3:1 묶음과 건너뛰기를 허용하는 최적 짝짓기(동적 계획법).
4. 문장 짝으로 이어진 한국어 문단·원서 문단을 하나의 '문단 묶음'으로 모음(문단 나란히 보기에 씀).
5. 짝마다 점수(0~1, 뜻이 얼마나 같은지)를 남기고 낮은 짝은 확인 목록(report)으로.
글자는 한국어 본문도 원서도 한 자도 바꾸지 않음 — 짝 자료에는 각 문장이 문단의 몇 번째 글자부터 몇 번째까지인지만 적음.
"""
import sys, re, json, os, argparse, datetime
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('book'); ap.add_argument('lang'); ap.add_argument('orig')
ap.add_argument('--gl-start', default=None, help='용어 풀이가 시작하는 한국어 문단(정규식, 예: "^\\*\\*깜마\\[")');
ap.add_argument('--gl-end', default=None, help='용어 풀이가 끝난 뒤 첫 한국어 문단(정규식) — 그 뒤(역자 후기·판권지 등)는 짝짓지 않음')
ap.add_argument('--gl-nl', action='store_true', help="용어 풀이가 '낱말(roman)⏎풀이' 모양(DL-0011) — 쪽에서 잘린 낱말 조각('**웨**' + '**다나(vedanā)**')도 이어 읽음")
ap.add_argument('--pin', action='append', default=[], help='짝을 손으로 정함: "한국어 열쇠+…=원서 번호+…" (예 "1:0=0+1" 속표지 ↔ 원서 제목·지은이). 원서 쪽을 비우면("2:0+2:1=") 그 한국어 문단은 짝 없음');
ap.add_argument('--fnpin', action='append', default=[], help='각주 짝을 손으로: "한국어 각주 번호=원서 각주 번호" (예 "40=33")');
ap.add_argument('--title', default=''); ap.add_argument('--by', default=''); ap.add_argument('--source', default='')
A = ap.parse_args()
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(os.path.join(REPO, 'content/texts', A.book + '.json')))
ORIG = json.load(open(A.orig))

# ---------- 한국어 문단 (app.js paras 와 같은 규칙) ----------
body = T['body'].replace('\r\n', '\n')
pages = []
for m in re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M):
    pages.append([m.group(1), m.end()])
for i, p in enumerate(pages):
    end = pages[i + 1][1] - len(re.search(r'===[^\n]*===\s*$', body[:pages[i + 1][1]]).group(0)) if i + 1 < len(pages) else len(body)
    p.append(body[p[1]:end].strip())


def paras(t): return [ '\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]


def plain(s):
    """화면에 보이는 글(표시 기호 뺌) — 문장 나누기·뜻 비교용"""
    s = re.sub(r'\[\^[^\]]+\]', '', s)
    s = re.sub(r'^(## |\^\^ |:: |>> |\+\+ |\|\| |%% )', '', s, flags=re.M)
    return re.sub(r'\*\*|==|°°|§§|@@|\{\{|\}\}', '', s)


KO = []   # {key:'n:s', t: 원문(본문 글 그대로), kind}
for n, (lab, _, txt) in enumerate(pages, 1):
    for s, para in enumerate(paras(txt)):
        if re.match(r'\[\^[^\]]+\]:', para) or para.startswith('%%') or para.startswith('![') or para.startswith('|'): continue
        KO.append({'key': f'{n}:{s}', 'pg': lab, 't': para, 'h': para.startswith('## ')})

# 빠알리 용어 풀이(가나다순으로 다시 늘어놓아 원서와 순서가 다름) — 차례 짝짓기에서 빼고 낱말(로마자)로 따로 짝지음
GL0 = next((i + 2 for i, p in enumerate(KO) if re.match(r'## IV\.', p['t'])), len(KO))
if A.gl_start: GL0 = next((i for i, p in enumerate(KO) if re.search(A.gl_start, p['t'])), len(KO))
GLE = len(KO)
if A.gl_end: GLE = next((i for i, p in enumerate(KO) if i > GL0 and re.search(A.gl_end, p['t'])), len(KO))
KO_GL = KO[GL0:GLE]; KO_DP = KO[:GL0]
SPL = re.compile(r'(?<=[.?!。…])(?:[”’"\')\]]*)\s+|\n')


def sents(t, lang):
    """문장 나누기: [(시작, 끝)] — 글자 자리(원래 글 기준)"""
    out = []; a = 0
    for m in SPL.finditer(t):
        b = m.start() if t[m.start()] == '\n' else m.end()
        seg = t[a:b].strip()
        if m.group(0) != '\n' and re.fullmatch(r'(## |%% )?[0-9IVXⅠ-Ⅻ]+\.', seg): continue   # '1. 제목'·'I. 제목' 의 번호 뒤에서는 나누지 않음
        if lang == 'en' and m.group(0) != '\n':
            # 'e.g. ' 'i.e. ' 'Mr. ' 'U. ' 같은 약어 뒤나 다음 글자가 소문자면 나누지 않음
            nx = t[m.end():m.end() + 1]
            if re.search(r'\b(e\.g|i\.e|etc|Mr|Mrs|Dr|cf|vs|No)\.$', t[a:m.start() + 1].strip()) or (nx and nx.islower()): continue
        if seg: out.append((a + len(t[a:b]) - len(t[a:b].lstrip()), a + len(t[a:b].rstrip())))
        a = m.end()
    if t[a:].strip(): out.append((a + len(t[a:]) - len(t[a:].lstrip()), len(t.rstrip())))
    return out


KS = []   # (para index, a, b, text)
for i, p in enumerate(KO_DP):
    for a, b in sents(p['t'], 'ko'):
        if plain(p['t'][a:b]).strip(): KS.append((i, a, b, plain(p['t'][a:b]).strip()))
ES = []
for i, p in enumerate(ORIG):
    if p['k'] in ('toc', 'gl', 'pq', 'fn', 'sep'): continue      # 원서 차례 쪽·용어 풀이·인용 상자(본문을 크게 다시 실은 것)는 차례 짝짓기에서 뺌 (한국어 차례도 %% 라 뺌)
    for a, b in sents(p['t'], 'en'):
        if plain(p['t'][a:b]).strip(): ES.append((i, a, b, plain(p['t'][a:b]).strip()))
print('한국어 문단', len(KO), '문장', len(KS), '/ 원서 문단', len(ORIG), '문장', len(ES))

# ---------- 뜻 벡터 ----------
from sentence_transformers import SentenceTransformer
cache = os.path.join(REPO, 'tools/out/parallel', f'{A.book}.{A.lang}.emb.npz')
model = SentenceTransformer('sentence-transformers/LaBSE')
def enc(xs): return model.encode(xs, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
key = str(hash(tuple(x[3] for x in KS)) ^ hash(tuple(x[3] for x in ES)))
if os.path.exists(cache) and np.load(cache)['key'] == key:
    z = np.load(cache); KE, EE = z['ko'], z['en']
else:
    KE, EE = enc([x[3] for x in KS]), enc([x[3] for x in ES])
    np.savez(cache, ko=KE, en=EE, key=key)
N, M = len(KS), len(ES)
S = KE @ EE.T

# ---------- 1단계: 대강의 길(1:1·건너뛰기)로 띠 찾기 ----------
SK = 0.05
D = np.full((N + 1, M + 1), -1e9); D[0, :] = -SK * np.arange(M + 1); D[:, 0] = -SK * np.arange(N + 1)
for i in range(1, N + 1):
    row = D[i]; prev = D[i - 1]; s = S[i - 1]
    diag = prev[:-1] + s; up = prev[1:] - SK
    best = np.maximum(diag, up)
    # 왼쪽(원서 건너뛰기)은 차례로
    for j in range(1, M + 1):
        v = best[j - 1]; l = row[j - 1] - SK
        row[j] = v if v > l else l
path = []; i, j = N, M
while i > 0 and j > 0:
    if abs(D[i, j] - (D[i - 1, j - 1] + S[i - 1, j - 1])) < 1e-9: path.append((i - 1, j - 1)); i -= 1; j -= 1
    elif abs(D[i, j] - (D[i - 1, j] - SK)) < 1e-9: i -= 1
    else: j -= 1
center = np.zeros(N, dtype=int)
pts = sorted(path)
if pts:
    pi = np.array([p[0] for p in pts]); pj = np.array([p[1] for p in pts])
    center = np.interp(np.arange(N), pi, pj).astype(int)
W = 40

# ---------- 2단계: 묶음까지 허용한 짝짓기 (띠 안에서) ----------
BEADS = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1), (1, 0), (0, 1)]
cK = np.vstack([np.zeros(KE.shape[1]), np.cumsum(KE, 0)]); cE = np.vstack([np.zeros(EE.shape[1]), np.cumsum(EE, 0)])
def sim(i0, i1, j0, j1):
    a = cK[i1] - cK[i0]; b = cE[j1] - cE[j0]
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
SKIP = -0.15; MERGE = 0.10
INF = -1e18
V = {}; B = {}
V[(0, 0)] = 0.0
def lo(i): return max(0, center[min(i, N - 1)] - W) if N else 0
def hi(i): return min(M, center[min(i, N - 1)] + W) if N else M
for i in range(0, N + 1):
    for j in range(lo(i), hi(i) + 1):
        if (i, j) == (0, 0): continue
        best = INF; bb = None
        for a, b in BEADS:
            pi, pj = i - a, j - b
            if pi < 0 or pj < 0 or (pi, pj) not in V: continue
            if a and b:
                sc = sim(pi, i, pj, j) * (a + b) / 2 - MERGE * (max(a, b) - 1 + (a > 1 and b > 1))
            else:
                sc = SKIP
            v = V[(pi, pj)] + sc
            if v > best: best, bb = v, (a, b)
        if bb is not None: V[(i, j)] = best; B[(i, j)] = bb
end = (N, M) if (N, M) in V else max((k for k in V if k[0] == N), key=lambda k: V[k])
beads = []; i, j = end
while (i, j) != (0, 0):
    a, b = B[(i, j)]; beads.append((i - a, i, j - b, j)); i, j = i - a, j - b
beads.reverse()

# ---------- 문단 묶음 ----------
groups = []   # [set ko paras, set en paras, beads]
for i0, i1, j0, j1 in beads:
    kp = {KS[k][0] for k in range(i0, i1)}; ep = {ES[k][0] for k in range(j0, j1)}
    if groups and ((kp & groups[-1][0]) or (ep & groups[-1][1])):
        groups[-1][0] |= kp; groups[-1][1] |= ep; groups[-1][2].append((i0, i1, j0, j1))
    else: groups.append([set(kp), set(ep), [(i0, i1, j0, j1)]])
# 문단 사이 빈틈(짝 없는 문단)도 묶음 순서를 지키게 정리
out = []
for kp, ep, bs in groups:
    sent = []
    for i0, i1, j0, j1 in bs:
        sc = round(sim(i0, i1, j0, j1), 3) if i1 > i0 and j1 > j0 else None
        sent.append({'ko': [[KO_DP[KS[k][0]]['key'], KS[k][1], KS[k][2]] for k in range(i0, i1)],
                     'or': [[ES[k][0], ES[k][1], ES[k][2]] for k in range(j0, j1)], **({'sc': sc} if sc is not None else {})})
    out.append({'ko': [KO_DP[k]['key'] for k in sorted(kp)], 'or': sorted(ep),
                'ka': plain(KO_DP[min(kp)]['t'])[:24] if kp else '', 's': sent})
# 손으로 정한 짝(--pin): 그 문단들을 다른 묶음에서 빼고 따로 한 묶음으로
for pin in A.pin:
    kk, oo = pin.split('=')
    kk = [x for x in kk.split('+') if x]
    def oidx(x):   # 원서 문단: 번호 또는 '@글 첫머리'
        if x.startswith('@'): return next(i for i, p in enumerate(ORIG) if p['t'].startswith(x[1:]))
        return int(x)
    oo = [oidx(x) for x in oo.split('+') if x]
    for g in out:
        g['ko'] = [k for k in g['ko'] if k not in kk]; g['or'] = [o for o in g['or'] if o not in oo]
        for st in g['s']:
            st['ko'] = [x for x in st['ko'] if x[0] not in kk]; st['or'] = [x for x in st['or'] if x[0] not in oo]
        g['s'] = [st for st in g['s'] if st['ko'] or st['or']]
    out[:] = [g for g in out if g['ko']]   # 한국어 문단이 빠진 묶음의 원서 문단은 짝 없음
    if kk and oo:
        KOT = {x['key']: x['t'] for x in KO_DP}
        out.append({'ko': kk, 'or': oo, 'ka': plain(KOT[kk[0]])[:24], 'pin': 1,
                    's': [{'ko': [[k, 0, len(KOT[k])] for k in kk], 'or': [[o, 0, len(ORIG[o]['t'])] for o in oo]}]})
kord = {x['key']: i for i, x in enumerate(KO_DP)}
out.sort(key=lambda g: (kord.get(g['ko'][0], 1e9) if g['ko'] else 1e9))
# 용어 풀이: 한국어 '낱말(roman) : 풀이' ↔ 원서 낱말
import unicodedata
def rk(x): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFD', x).encode('ascii', 'ignore').decode().lower())
EG = {}
for i, p in enumerate(ORIG):
    if p['k'] == 'gl': EG.setdefault(rk(re.sub(r'\(also see[^)]*\)', '', p['term'])), i)
gl_ok = gl_no = 0; cur = None; frag = []
for p in KO_GL:
    if A.gl_nl and re.fullmatch(r'\*\*[^\n*]+\*\*', p['t']) and '(' not in p['t'].replace('(**', ''):   # 쪽 끝에서 잘린 낱말 조각 → 다음 문단과 함께
        frag.append(p); continue
    if A.gl_nl and re.fullmatch(r'\*\*[^\n*]+\(\*\*', p['t']): frag.append(p); continue      # '**실라(**' + '**sīla)**'
    pt = ''.join(plain(f['t']) for f in frag) + plain(p['t'])
    m3 = (re.match(r'[^\n(]*?\(([^)]*[a-zāīūṃṅñṭḍṇḷ][^)]*)\)\s*\n', pt) or re.match(r'[^\n(]+\n[a-z]\) ([a-zāīūṃṅñṭḍṇḷ]+)\n', pt)) if A.gl_nl else None
    m = m3 or re.match(r'[^\n(]*?\(([^)]*[a-zāīūṃṅñṭḍṇḷ][^)]*)\)\s*:', plain(p['t'])) or re.match(r'[^\n\[]*?\[([^\]]*[a-zāīūṃṅñṭḍṇḷ][^\]]*)\]\s*\n', plain(p['t']))   # '낱말(roman) : 풀이' 또는 '낱말[roman]⏎풀이'(DL-0013)
    if m:
        j = None
        for c in m.group(1).split(','):          # 'pāramī, pāramita' 처럼 여러 표기
            j = EG.get(rk(c))
            if j is not None: break
        if j is None:                             # 'satipaṭṭhāna' ↔ 'Satipatthāna Sutta', 오자 'somassna' ↔ 'somanassa'
            import difflib
            k0 = rk(m.group(1).split(',')[0])
            j = next((v for k, v in EG.items() if k.startswith(k0) and len(k0) >= 6), None)
            if j is None:
                best = max(EG, key=lambda k: difflib.SequenceMatcher(None, k, k0).ratio())
                if difflib.SequenceMatcher(None, best, k0).ratio() >= 0.8: j = EG[best]
        if j is None: gl_no += 1; print('  용어 못 찾음:', m.group(1)); cur = None; frag = []; continue
        gl_ok += 1
        ps = frag + [p]; frag = []
        cur = {'ko': [x['key'] for x in ps], 'or': [j], 'ka': pt[:24], 'gl': 1, 's': [{'ko': [[x['key'], 0, len(x['t'])] for x in ps], 'or': [[j, 0, len(ORIG[j]['t'])]]}]}
        out.append(cur)
    elif cur is not None:      # 풀이가 다음 문단(①②③, 다음 쪽)으로 이어짐
        for x in frag + [p]: cur['ko'].append(x['key']); cur['s'][0]['ko'].append([x['key'], 0, len(x['t'])])
        frag = []
print('용어 풀이 짝', gl_ok, '못 찾음', gl_no)
# ---------- 각주 짝 (운영자 요청, 2026-11-17): 한국어 각주([^n]:, [역주] 는 뺌) ↔ 원서 각주('fn' 문단) — 뜻 벡터 + 순서 지키는 짝짓기 ----------
FN = {}; fn_rep = []
KF = [(m.group(1), m.group(2).strip()) for m in re.finditer(r'^\[\^([^\]]+)\]:\s*(.*(?:\n(?!\[\^|===).*)*)', body, flags=re.M)]
YK = {n for n, t in KF if t.lstrip('*').startswith('[역주]')}   # 역자 각주: 원서 각주를 풀어 쓴 것도 있어 뜻이 아주 가까울 때만 짝
EF = [(i, re.sub(r'^\[\^[^\]]+\]:\s*', '', p['t'])) for i, p in enumerate(ORIG) if p['k'] == 'fn']
if KF and EF:
    kfe, efe = enc([plain(t)[:400] for _, t in KF]), enc([t[:400] for _, t in EF])
    FS = kfe @ efe.T
    n1, m1 = len(KF), len(EF); G = np.zeros((n1 + 1, m1 + 1)); BK = {}
    for i in range(n1 + 1):
        for j in range(m1 + 1):
            if i == 0 and j == 0: continue
            c = []
            if i and j: c.append((G[i - 1, j - 1] + FS[i - 1, j - 1] - (0.6 if KF[i - 1][0] in YK else 0.2), 'd'))
            if i: c.append((G[i - 1, j], 'u'))
            if j: c.append((G[i, j - 1], 'l'))
            G[i, j], BK[(i, j)] = max(c)
    i, j = n1, m1
    while i or j:
        b = BK[(i, j)]
        if b == 'd':
            FN[KF[i - 1][0]] = EF[j - 1][0]; fn_rep.append((KF[i - 1], EF[j - 1], float(FS[i - 1, j - 1]))); i -= 1; j -= 1
        elif b == 'u': i -= 1
        else: j -= 1
    fn_rep.reverse()
    for x in A.fnpin:   # 손으로 정한 각주 짝
        kn, en = x.split('=')
        ei = next(i for i, t in EF if ORIG[i]['t'].startswith(f'[^{en}]:'))
        FN = {k: v for k, v in FN.items() if v != ei}; FN[kn] = ei
        fn_rep = [r for r in fn_rep if r[1][0] != ei and r[0][0] != kn] + [((kn, dict(KF)[kn]), (ei, ORIG[ei]['t']), 1.0)]
    print('각주 짝', len(FN), '/ 한국어 각주', len(KF), '(역주', len(YK), ') / 원서 각주', len(EF))
scores = [s['sc'] for g in out for s in g['s'] if 'sc' in s]
res = {'book': A.book, 'lang': A.lang, 'title': A.title, 'by': A.by, 'source': A.source,
       'made': datetime.date.today().isoformat(), 'method': 'LaBSE 문장 뜻 비교 + 순서 지키는 짝짓기(1:1·1:2·2:1·2:2·1:3·3:1·건너뛰기)',
       'note': '짝 자료: groups[].ko = 한국어 문단 열쇠 "쪽 순번:문단 순번"(content/texts 본문 기준), or = 원서 문단 번호, s = 문장 짝 [문단 열쇠·번호, 시작 글자, 끝 글자], sc = 뜻 비슷함(0~1)',
       'orig': [{'pg': p['pg'], 'k': p['k'], 't': p['t']} for p in ORIG], 'groups': out, **({'fn': FN} if FN else {})}
os.makedirs(os.path.join(REPO, 'content/parallel'), exist_ok=True)
json.dump(res, open(os.path.join(REPO, 'content/parallel', f'{A.book}.{A.lang}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
low = [(g, s) for g in out for s in g['s'] if not g.get('gl') and (s.get('sc', 1) < 0.5 or 'sc' not in s)]   # 용어 풀이 짝은 점수가 없으니 확인 목록에서 뺌
print('문장 짝', sum(len(g['s']) for g in out), '문단 묶음', len(out), '평균 점수', round(float(np.mean(scores)), 3),
      '0.5 아래·건너뜀', len(low))
KOI = {x['key']: x for x in KO}
rep = os.path.join(REPO, 'tools/out/parallel', f'{A.book}.{A.lang}.report.txt')
with open(rep, 'w') as f:
    for g, s in low:
        kt = ' / '.join(KOI[k]['t'][a:b] for k, a, b in s['ko'])
        et = ' / '.join(ORIG[p]['t'][a:b] for p, a, b in s['or'])
        f.write(f"[{s.get('sc', '건너뜀')}] {g['ko'][:1]} 원서 {g['or'][:1]}\n  한: {kt[:200]}\n  원: {et[:200]}\n")
if fn_rep or (KF and EF):
    with open(rep, 'a') as f:
        f.write('\n===== 각주 짝 =====\n')
        got = {k[0] for k, _, _ in fn_rep}; gote = {e[0] for _, e, _ in fn_rep}
        for (kn, kt), (ei, et), sc in fn_rep: f.write(f"[{sc:.2f}] 한 {kn} ↔ 원 {ORIG[ei]['t'][:6]}  {plain(kt)[:60]} || {et[:60]}\n")
        for kn, kt in KF:
            if kn not in got and kn not in YK: f.write(f"[짝 없음] 한국어 각주 {kn}: {plain(kt)[:80]}\n")
        for ei, et in EF:
            if ei not in gote: f.write(f"[짝 없음] 원서 각주 {ORIG[ei]['t'][:80]}\n")
print('확인 목록 →', rep)
