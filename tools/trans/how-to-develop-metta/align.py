"""한국어 번역 문장 ↔ 영어 원서 문장 짝짓기 (LaBSE 뜻 비교 + 순서를 지키는 동적 계획법).
묶음: 1:1 1:2 2:1 2:2 1:3 3:1, 건너뛰기 0:1 1:0.
결과 pairs.json = [{"k":[한국어 문장 번호…], "e":[영어 문장 번호…], "sc": 뜻 비슷함}]
"""
import json, sys, numpy as np, os
os.environ.setdefault('HF_HUB_OFFLINE', '1')
from sentence_transformers import SentenceTransformer
M = SentenceTransformer('/root/.cache/huggingface/hub/models--sentence-transformers--LaBSE/snapshots/836121a0533e5664b21c7aacc5d22951f2b8b25b')
K = json.load(open('ko_sents.json'))['sents']; E = json.load(open('en_sents.json'))['sents']
pins = json.load(open('pins.json')) if os.path.exists('pins.json') else {}
SKIP_K = {i for i, s in enumerate(K) if any(s['t'].startswith(x) for x in pins.get('skip_ko', []))}; SKIP_E = {i for i, s in enumerate(E) if any(s['t'].startswith(x) for x in pins.get('skip_en', []))}
nK, nE, G = len(K), len(E), 3

import pickle
CACHE = pickle.load(open('emb_cache.pkl', 'rb')) if os.path.exists('emb_cache.pkl') else {}
def embs(S):
    out = {}
    for g in range(1, G + 1):
        txt = [' '.join(s['t'] for s in S[i:i + g]) for i in range(len(S) - g + 1)]
        need = [t for t in set(txt) if t not in CACHE]
        if need:
            v = M.encode(need, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
            CACHE.update(zip(need, v))
        for i, t in enumerate(txt): out[(i, g)] = CACHE[t]
    return out
EK, EE = embs(K), embs(E)
pickle.dump(CACHE, open('emb_cache.pkl', 'wb'))
MOVES = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1), (1, 0), (0, 1)]
SKIP = -0.05  # 건너뛰기 점수(한 문장에)
BASE = 0.35   # 짝 점수 = 뜻 비슷함 - BASE (관계없는 문장도 0.3쯤 나옴)
NEG = -1e9
D = np.full((nK + 1, nE + 1), NEG); B = np.zeros((nK + 1, nE + 1, 2), dtype=np.int16)
D[0, 0] = 0
# 대각선 띠 안에서만 (두 글 길이 비율을 따라)
BAND = 160
for i in range(nK + 1):
    c = int(i * nE / max(nK, 1)); lo = max(0, c - BAND); hi = min(nE, c + BAND)
    for j in range(lo, hi + 1):
        if i == 0 and j == 0: continue
        best = NEG; bm = (0, 0)
        for a, b in MOVES:
            if a > i or b > j: continue
            prev = D[i - a, j - b]
            if prev <= NEG / 2: continue
            if a == 0 or b == 0:
                sc = SKIP * (a + b)
                if a and (i - 1) in SKIP_K: sc = 0.5
                if b and (j - 1) in SKIP_E: sc = 0.5
            else:
                if any(x in SKIP_K for x in range(i - a, i)) or any(x in SKIP_E for x in range(j - b, j)): continue
                sim = float(EK[(i - a, a)] @ EE[(j - b, b)])
                # 제목은 제목끼리
                hk = K[i - a]['h']; he = E[j - b]['h']
                sc = (sim - BASE) * (a + b) / 2 - (0.05 * (a + b - 2)) - (0.15 if hk != he else 0)
            v = prev + sc
            if v > best: best, bm = v, (a, b)
        D[i, j] = best; B[i, j] = bm
i, j = nK, nE; out = []
while i or j:
    a, b = B[i, j]
    ks = list(range(i - a, i)); es = list(range(j - b, j))
    sim = float(EK[(i - a, a)] @ EE[(j - b, b)]) if a and b else None
    out.append(dict(k=ks, e=es, sc=None if sim is None else round(sim, 3)))
    i, j = i - a, j - b
out.reverse()
# 손으로 정한 짝(순서를 바꿔 옮긴 곳 등): 문장 첫머리로 찾음
def find(S, pre):
    r = [i for i, s in enumerate(S) if s['t'].startswith(pre)]
    assert len(r) == 1, (pre, r); return r[0]
for fx in pins.get('fix', []):
    ks = [find(K, x) for x in fx['k']]; es = [find(E, x) for x in fx['e']]
    for p in out:
        p['k'] = [x for x in p['k'] if x not in ks]; p['e'] = [x for x in p['e'] if x not in es]
    out = [p for p in out if p['k'] or p['e']]
    pos = next((n for n, p in enumerate(out) if p['k'] and p['k'][0] > max(ks)), len(out))
    sim = float(np.mean([CACHE[K[i]['t']] for i in ks], 0) @ np.mean([CACHE[E[i]['t']] for i in es], 0)) if ks and es else None
    out.insert(pos, dict(k=ks, e=es, sc=None if sim is None else round(sim, 3), hand=1))
for p in out:
    if p['k'] and p['e'] and len(p['k']) + len(p['e']) > 2 and 'hand' not in p:
        pass
# 한쪽만 있는 줄: (일부러 뺀 문장은 그대로 두고) 같은 문단 안이면 앞(없으면 뒤) 짝에 붙임
def para(S, i): return S[i]['p']
m = []
for p in out:
    if m and (not p['k'] or not p['e']) and not (set(p['k']) & SKIP_K):
        q = m[-1]
        if not p['k'] and q['e'] and q['k'] and para(E, p['e'][0]) == para(E, q['e'][-1]): q['e'] += p['e']; continue
        if not p['e'] and q['k'] and q['e'] and para(K, p['k'][0]) == para(K, q['k'][-1]): q['k'] += p['k']; continue
    m.append(p)
out = m
json.dump(out, open('pairs.json', 'w'), ensure_ascii=False)
sc = [p['sc'] for p in out if p['sc'] is not None]
print('pairs', len(sc), 'avg', round(sum(sc) / len(sc), 3), 'low<0.5', sum(s < 0.5 for s in sc),
      'ko-only', sum(1 for p in out if not p['e']), 'en-only', sum(1 for p in out if not p['k']))
