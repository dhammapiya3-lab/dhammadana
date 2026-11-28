# 『위빠싸나 성자 아짠 문』(DL-0040) 태국어 원서 짝 — 영어 원서를 다리로 (운영자 요청, 2026-11-28)
#   한국어판은 영어판(M. Siri Buddhasukh 영역)을 옮긴 책이라, 한국어 ↔ 태국어를 바로 짝지으면 한국어가 많이 줄인 곳에서 엉뚱한 짝이 생김.
#   그래서 ① 영어 원서 문장 ↔ 태국어 원서 문장을 뜻 벡터(LaBSE)로 순서대로 짝짓고(영어는 태국어를 옮긴 글이라 순서가 거의 같음)
#   ② 이미 검수한 한국어 ↔ 영어 짝(content/parallel/DL-0040.en.json)의 영어 문장 자리를 태국어 문장으로 바꿔 DL-0040.th.json 을 만듦.
#   한국어 문장 줄·묶음은 영어 짝과 같아서, 원서 대조에서 영어·태국어를 함께 보면 같은 한국어 줄 아래에 나란히 나옴.
#   짝 없는 태국어 문장(영어판이 줄인 곳)은 앞 묶음 끝에 '원서만 있는 줄'로 붙여 태국어 글이 빠짐없이 차례대로 보이게 함.
#   python3 tools/parallel/pivot_th.py [--band 300] [--base .32]
import json, re, os, sys, argparse, numpy as np
REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))
ap = argparse.ArgumentParser(); ap.add_argument('--band', type=int, default=200); ap.add_argument('--base', type=float, default=.32)
ap.add_argument('--title', default='ประวัติท่านพระอาจารย์มั่น ภูริทัตตเถระ'); ap.add_argument('--by', default='ท่านอาจารย์พระมหาบัว ญาณสัมปันโน'); ap.add_argument('--source', default='ประวัติท่านพระอาจารย์มั่น ภูริทัตตเถระ (PDF 287쪽, 글자 인식)')
A = ap.parse_args()
EN = json.load(open(os.path.join(REPO, 'content/parallel/DL-0040.en.json')))
TH = json.load(open(os.path.join(REPO, 'tools/out/parallel/DL-0040.th.paras.json')))
EO = EN['orig']
# ---------- 영어 단위: 한국어 짝에 쓰인 영어 글자 자리 + 그 사이 남은 글 ----------
used = {}
for g in EN['groups']:
    if g.get('toc'): continue
    for s in g['s']:
        for i, a, b in s['or']: used.setdefault(i, []).append((a, b))
EU = []   # (문단, 시작, 끝)
SKIPK = ('toc', 'fn', 'pq', 'sep', 'gl', 'cite')
for i, o in enumerate(EO):
    if o['k'] in SKIPK: continue
    rs = sorted(set(used.get(i, []))); pos = 0
    for a, b in rs:
        if a > pos and re.search(r'[A-Za-z]{3}', o['t'][pos:a]): EU.append((i, pos, a))
        if b > pos: EU.append((i, max(a, pos), b)); pos = max(pos, b)
    if pos < len(o['t']) and re.search(r'[A-Za-z]{3}', o['t'][pos:]): EU.append((i, pos, len(o['t'])))
EU.sort()
# 영어판 본문 끝('May BE 2514' 날짜 줄) 뒤의 용어 풀이·부록은 태국어판에 없으므로 짝짓지 않음
_end = next(i for i, o in enumerate(EO) if o['t'].strip().startswith('May BE 2514'))
EU = [u for u in EU if u[0] <= _end]
# ---------- 태국어 문장 ----------
from pythainlp.tokenize import sent_tokenize
def th_sents(t):
    out = []; pos = 0
    for s in sent_tokenize(t, engine='crfcut'):
        i = t.find(s, pos)
        if i < 0: continue
        a, b = i, i + len(s.rstrip()); pos = i + len(s)
        if b > a: out.append([a, b])
    m = []
    for a, b in out:
        if m and len(t[m[-1][0]:m[-1][1]]) < 25: m[-1][1] = b
        else: m.append([a, b])
    if len(m) > 1 and len(t[m[-1][0]:m[-1][1]]) < 25: m[-2][1] = m[-1][1]; m.pop()
    return m or [[0, len(t.rstrip())]]
TU = []
for i, p in enumerate(TH):
    if p['k'] == 'toc' or p['pdf'] < 6 or p['pdf'] > 276: continue   # 본문(PDF 6~276쪽)만 — คำนำ(PDF 4)와 부록 17~19(PDF 278~)는 영어판·한국어판에 없음
    for a, b in th_sents(p['t']): TU.append((i, a, b))
print('영어 단위', len(EU), '태국어 문장', len(TU))
# ---------- 뜻 벡터 ----------
cache = os.path.join(REPO, 'tools/out/parallel/DL-0040.pivot.emb.pkl')   # 문장 글 → 뜻 벡터 (글자를 고친 문장만 다시 계산)
import pickle
et = [EO[i]['t'][a:b] for i, a, b in EU]; tt = [TH[i]['t'][a:b] for i, a, b in TU]
C = pickle.load(open(cache, 'rb')) if os.path.exists(cache) else {}
need = [x for x in dict.fromkeys(et + tt) if x not in C]
if need:
    model = SentenceTransformer('sentence-transformers/LaBSE') if 'SentenceTransformer' in globals() else None
    from sentence_transformers import SentenceTransformer as _ST
    model = _ST('sentence-transformers/LaBSE')
    for x, v in zip(need, model.encode(need, batch_size=64, normalize_embeddings=True, show_progress_bar=False)): C[x] = v
    pickle.dump(C, open(cache, 'wb'))
EE = np.array([C[x] for x in et]); TE = np.array([C[x] for x in tt])
print('새로 계산한 문장', len(need), flush=True)
N, M = len(EU), len(TU)
# ---------- 대강의 길: 영어 단위 64개씩 · 태국어 문장 묶음 평균으로 ----------
S = EE @ TE.T
# 띠의 가운데 선: 영어 20단위·태국어 30문장씩 묶은 평균 벡터로 먼저 순서 있는 큰 길(DTW)을 찾음
BE, BT = 20, 30
def blocks(X, n):
    k = (len(X) + n - 1) // n; Y = np.array([X[q * n:(q + 1) * n].mean(0) for q in range(k)]); return Y / np.linalg.norm(Y, axis=1, keepdims=True)
Eb, Tb = blocks(EE, BE), blocks(TE, BT); Sb = Eb @ Tb.T
nb, mb = Sb.shape; D2 = np.full((nb + 1, mb + 1), -1e9); D2[0, :] = 0; D2[:, 0] = 0; P2 = np.zeros((nb + 1, mb + 1), int)
for x in range(1, nb + 1):
    for y in range(1, mb + 1):
        c = [D2[x - 1, y - 1] + Sb[x - 1, y - 1], D2[x - 1, y] + Sb[x - 1, y - 1] - .05, D2[x, y - 1] - .02]
        k = int(np.argmax(c)); D2[x, y] = c[k]; P2[x, y] = k
x, y = nb, int(np.argmax(D2[nb])); bmap = {}
while x > 0 and y > 0:
    bmap.setdefault(x - 1, []).append(y - 1)
    k = P2[x, y]
    if k == 0: x, y = x - 1, y - 1
    elif k == 1: x -= 1
    else: y -= 1
ctr = np.zeros(N)
for i in range(N):
    q = i // BE; ys = bmap.get(q) or bmap.get(min(bmap, key=lambda z: abs(z - q)))
    ctr[i] = (np.mean(ys) + .5) * BT
ctr = np.maximum.accumulate(ctr)
# ---------- 순서 지키는 짝짓기 (띠 안에서) ----------
MOVES = [(1, 1), (1, 2), (2, 1), (1, 3), (3, 1), (2, 2), (1, 4), (2, 3), (1, 5), (0, 1), (1, 0)]
NEG = -1e9
lo_ = np.clip(ctr - A.band, 0, M).astype(int); hi_ = np.clip(ctr + A.band, 0, M).astype(int)
# 시작이 0, 끝이 M 이 되게 띠를 넓힘
lo_[0] = 0; hi_[-1] = M
PE = np.vstack([np.zeros((1, EE.shape[1])), np.cumsum(EE, 0)]); PT = np.vstack([np.zeros((1, TE.shape[1])), np.cumsum(TE, 0)])
def sim(i0, i1, j0, j1):
    if i1 - i0 == 1 and j1 - j0 == 1: return float(S[i0, j0])
    e = PE[i1] - PE[i0]; t = PT[j1] - PT[j0]
    return float(e @ t / (np.linalg.norm(e) * np.linalg.norm(t) + 1e-9))
# 줄마다 띠 [LO[i], HI[i]) 안에서 점수 배열 — (0,1) 태국어 건너뛰기는 줄 안에서 왼쪽→오른쪽으로 이어 받음
LO = np.zeros(N + 1, int); HI = np.zeros(N + 1, int)
for i in range(N + 1):
    c = ctr[min(i, N - 1)]
    LO[i] = max(0, int(c) - A.band); HI[i] = min(M, int(c) + A.band) + 1
LO[0] = 0; HI[N] = M + 1
for i in range(1, N + 1): LO[i] = min(LO[i], HI[i - 1] - 1); HI[i] = max(HI[i], LO[i] + 1)   # 띠가 끊기지 않게
for i in range(N - 1, -1, -1): HI[i] = max(HI[i], min(LO[i + 1] + 1, M + 1))
# 제목은 제목끼리: 영어 제목(소제목이 많음)이 태국어 본문 문장과 짝지어지지 않게
EH = np.concatenate([[0], np.cumsum([EO[i]['k'] == 'h' for i, a, b in EU])]); THh = np.concatenate([[0], np.cumsum([TH[i]['k'] == 'h' for i, a, b in TU])])
SC = [None] * (N + 1); BK = [None] * (N + 1)
for i in range(N + 1): SC[i] = np.full(HI[i] - LO[i], NEG); BK[i] = np.zeros((HI[i] - LO[i], 2), int)
SC[0][0] = 0.0
SKIP = -0.02
for i in range(N + 1):
    lo, hi = LO[i], HI[i]; sc = SC[i]; bk = BK[i]
    for k in range(1, hi - lo):   # (0,1) 태국어 문장 건너뛰기
        if sc[k - 1] + SKIP > sc[k]: sc[k] = sc[k - 1] + SKIP; bk[k] = (i, lo + k - 1)
    if i == N: break
    js = np.arange(lo, hi)
    ok = sc > NEG / 2
    if not ok.any(): continue
    js = js[ok]; v = sc[ok]
    for di, dj in MOVES:
        if di == 0: continue
        ni = i + di
        if ni > N: continue
        nj = js + dj; m_ = (nj >= LO[ni]) & (nj < HI[ni]) & (nj <= M)
        if not m_.any(): continue
        j0 = js[m_]; j1 = nj[m_]
        if dj == 0: g = np.full(len(j0), SKIP)
        else:
            e = PE[ni] - PE[i]; t = PT[j1] - PT[j0]
            sim_ = (t @ e) / (np.linalg.norm(t, axis=1) * np.linalg.norm(e) + 1e-9)
            g = (sim_ - A.base) * (di + dj) / 2 - .5 * ((EH[ni] - EH[i] > 0) != (THh[j1] - THh[j0] > 0))
        nv = v[m_] + g; tgt = j1 - LO[ni]
        # 같은 칸에 여러 후보가 오면 가장 큰 것
        order = np.argsort(nv); tgt_o = tgt[order]; nv_o = nv[order]; src_o = j0[order]
        better = nv_o > SC[ni][tgt_o]
        SC[ni][tgt_o[better]] = nv_o[better]; BK[ni][tgt_o[better]] = np.stack([np.full(better.sum(), i), src_o[better]], 1)
    if i % 1000 == 0: print('짝짓기', i, '/', N, flush=True)
# 끝: 마지막 영어 단위 줄에서 가장 좋은 칸 (그 뒤 태국어 — 부록 등 — 은 짝 없음)
i = N; k = int(np.argmax(SC[N])); j = LO[N] + k
pairs = []
while i > 0 or j > 0:
    pi, pj = BK[i][j - LO[i]]
    if (pi, pj) == (0, 0) and (i, j) != (0, 0) and not (i > 0 and SC[i][j - LO[i]] > NEG / 2): break
    if i > pi and j > pj: pairs.append((list(range(pi, i)), list(range(pj, j))))
    if (pi, pj) == (i, j): break
    i, j = int(pi), int(pj)
pairs.reverse()
e2t = {}
for es, ts in pairs:
    for e in es: e2t[e] = ts
print('영어↔태국어 짝', len(pairs), '태국어 짝이 있는 영어 단위', len(e2t), '/', N)
# ---------- 한국어 짝으로 옮기기 ----------
eidx = {}
for k, (i, a, b) in enumerate(EU): eidx.setdefault(i, []).append((a, b, k))
def units_of(i, a, b): return [k for (x, y, k) in eidx.get(i, []) if x < b and a < y]
# 태국어 원서 글을 묶음마다의 조각으로 (같은 태국어 문단이 여러 묶음에 나뉘어도 겹쳐 보이지 않게)
tused = set(); orig = []; groups = []; tk2o = {}
def piece(ts):
    # 태국어 문장 번호들 → 같은 문단끼리 이은 조각 [(orig 번호, 시작, 끝)]
    out = []; cur = None
    for t in sorted(ts):
        i, a, b = TU[t]
        if cur and cur[0] == i and cur[2] <= a and not re.search(r'\S', TH[i]['t'][cur[2]:a].replace(' ', '')):
            cur[2] = b
        else:
            cur = [i, a, b]; out.append(cur)
    res = []
    for i, a, b in out:
        p = TH[i]; orig.append({'pg': p['pg'], 'pdf': p['pdf'], 'k': p['k'], 't': p['t'][a:b]}); res.append(len(orig) - 1)
    return res
PST = {}   # 원서 조각 → (태국어 문단, 시작, 끝)
for g in EN['groups']:
    if g.get('toc'): continue
    rows = []
    for s in g['s']:
        ts = sorted({t for (i, a, b) in s['or'] for u in units_of(i, a, b) for t in e2t.get(u, [])} - tused)
        tused.update(ts); rows.append((s, ts))
    allt = sorted(t for _, ts in rows for t in ts)
    if not allt: continue
    # 묶음 안 태국어 문장을 같은 문단끼리 이어 하나의 조각으로 (문장마다 따로 문단이 되지 않게)
    pcs = []; cur = None
    for t in allt:
        i, a, b = TU[t]
        if cur and cur[0] == i: cur[2] = b; cur[3].append(t)
        else: cur = [i, a, b, [t]]; pcs.append(cur)
    t2 = {}
    ng = {'ko': g['ko'], 'or': [], 's': []}
    for i, a, b, tl in pcs:
        p = TH[i]; orig.append({'pg': p['pg'], 'pdf': p['pdf'], 'k': p['k'], 't': p['t'][a:b]}); o = len(orig) - 1; ng['or'].append(o); PST[o] = (i, a, b)
        for t in tl: t2[t] = (o, TU[t][1] - a, TU[t][2] - a)
    for s, ts in rows:
        if not s['ko'] and not ts: continue
        sc = float(np.mean([S[u, t] for (i, a, b) in s['or'] for u in units_of(i, a, b) for t in ts])) if ts else None
        e = {'ko': s['ko'], 'or': [list(t2[t]) for t in ts], '_t': max(ts) if ts else -1}
        if sc is not None: e['sc'] = round(sc, 3)
        ng['s'].append(e)
    if g.get('note'): ng['note'] = f"원서와 순서가 다릅니다 — 원서 {TH[TU[allt[0]][0]]['pg']}쪽에 있는 글입니다."   # 영어 짝에서 차례를 옮긴 묶음만
    groups.append(ng)
# 짝 없는 태국어 문장: 바로 앞 태국어 문장이 들어간 묶음 끝에 원서만 있는 줄로
assigned = {}; used2 = set(); gts = []
for g in EN['groups']:
    if g.get('toc'): continue
    ts_all = []
    for s in g['s']:
        ts = sorted({t for (i, a, b) in s['or'] for u in units_of(i, a, b) for t in e2t.get(u, [])} - used2)
        used2.update(ts); ts_all += ts
    if ts_all: gts.append(ts_all)
for gi, ts in enumerate(gts):
    for t in ts: assigned[t] = gi
orphans = [t for t in range(M) if t not in assigned]
def ins(g, e):   # 태국어 차례대로 — 바로 앞 태국어 문장이 든 줄 다음에
    k = max([q for q, x in enumerate(g['s']) if x.get('_t', -1) < e['_t'] and x.get('_t', -1) >= 0] or [len(g['s']) - 1])
    g['s'].insert(k + 1, e)
lastg = 0; nadd = 0; tmin, tmax = min(assigned), max(assigned); nout = 0
for t in range(M):
    if t in assigned: lastg = assigned[t]; continue
    if t < tmin or t > tmax: nout += 1; continue   # 첫 짝 앞(คำนำ 등)·마지막 짝 뒤(부록 17~19)의 태국어는 한국어판·영어판에 없어 넣지 않음
    i, a, b = TU[t]; g = groups[lastg]; p = TH[i]; nadd += 1
    lo_ = g['or'][-1]; pi_, pa, pb = PST[lo_]
    if pi_ == i and pb <= a and not p['t'][pb:a].strip():   # 앞 조각에 바로 이어지는 문장이면 그 조각을 늘림
        orig[lo_]['t'] = p['t'][pa:b]; PST[lo_] = (i, pa, b); ins(g, {'ko': [], 'or': [[lo_, a - pa, b - pa]], '_t': t}); continue
    orig.append({'pg': p['pg'], 'pdf': p['pdf'], 'k': p['k'], 't': p['t'][a:b]}); o = len(orig) - 1; PST[o] = (i, a, b)
    g['or'].append(o); ins(g, {'ko': [], 'or': [[o, 0, b - a]], '_t': t})
for g in groups:
    for x in g['s']: x.pop('_t', None)
print('묶음', len(groups), '원서 조각', len(orig), '짝 없는 태국어 문장', nadd, '앞뒤라 뺀 태국어 문장', nout)
res = {'book': 'DL-0040', 'lang': 'th', 'title': A.title, 'by': A.by, 'source': A.source, 'orig': orig, 'groups': groups}
json.dump(res, open(os.path.join(REPO, 'content/parallel/DL-0040.th.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
# 확인 목록
rep = os.path.join(REPO, 'tools/out/parallel/DL-0040.th.pivot.tsv')
with open(rep, 'w') as f:
    for es, ts in pairs:
        f.write('\t'.join([str(round(sim(es[0], es[-1] + 1, ts[0], ts[-1] + 1), 3)), ' '.join(EO[EU[e][0]]['t'][EU[e][1]:EU[e][2]] for e in es), ' '.join(TH[TU[t][0]]['t'][TU[t][1]:TU[t][2]] for t in ts)]) + '\n')
print('영어↔태국어 짝 목록 →', rep)
