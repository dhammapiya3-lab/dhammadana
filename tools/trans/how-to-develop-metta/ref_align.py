"""대조 번역본 문장 ↔ 번역 교정 줄 짝짓기 (LaBSE, 순서를 지키는 동적 계획법).
줄 하나에 대조 번역본 문장 0~4개, 대조 문장 하나가 줄 둘에 걸치면 앞 줄에 넣고 뒤 줄은 rc(위 줄에 이어짐).
뜻 비슷함 = 원서 문장(o)과 우리 번역(t0) 가운데 높은 쪽(우리 번역은 같은 한국어라 점수가 높게 나오므로 0.1 덜어 냄).
python3 ref_align.py 자료.trans.json ref_sents.json → ref_pairs.json"""
import sys, json, os, pickle, numpy as np
os.environ.setdefault('HF_HUB_OFFLINE', '1')
from sentence_transformers import SentenceTransformer
M = SentenceTransformer('/root/.cache/huggingface/hub/models--sentence-transformers--LaBSE/snapshots/836121a0533e5664b21c7aacc5d22951f2b8b25b')
DOC = json.load(open(sys.argv[1])); R = DOC['rows']; S = json.load(open(sys.argv[2]))['sents']
C = pickle.load(open('emb.pkl', 'rb')) if os.path.exists('emb.pkl') else {}
def emb(ts):
    need = [t for t in set(ts) if t and t not in C]
    if need: C.update(zip(need, M.encode(need, batch_size=64, normalize_embeddings=True, show_progress_bar=True)))
    return [C.get(t) for t in ts]
G = 4
SG = {(i, g): ' '.join(s['t'] for s in S[i:i + g]) for g in range(1, G + 1) for i in range(len(S) - g + 1)}
RO = {(j, g): ' '.join(r['o'] for r in R[j:j + g] if r['o']) for g in (1, 2) for j in range(len(R) - g + 1)}
RT = {(j, g): ' '.join((r.get('t0') or r['t']) for r in R[j:j + g] if (r.get('t0') or r['t'])) for g in (1, 2) for j in range(len(R) - g + 1)}
emb(list(SG.values()) + list(RO.values()) + list(RT.values())); pickle.dump(C, open('emb.pkl', 'wb'))
def sim(i, a, j, b):
    s = SG[(i, a)]; v = C[s]; best = -1
    if RO[(j, b)]: best = max(best, float(v @ C[RO[(j, b)]]))
    if RT[(j, b)]: best = max(best, float(v @ C[RT[(j, b)]]) - 0.1)
    return best
nS, nR = len(S), len(R); BASE = 0.35; SKIP = -0.05; NEG = -1e9
MOVES = [(1, 1), (2, 1), (3, 1), (4, 1), (1, 2), (2, 2), (1, 0), (0, 1)]
D = np.full((nS + 1, nR + 1), NEG); B = np.zeros((nS + 1, nR + 1, 2), dtype=np.int16); D[0, 0] = 0; BAND = 260
for i in range(nS + 1):
    c = int(i * nR / nS)
    for j in range(max(0, c - BAND), min(nR, c + BAND) + 1):
        if not i and not j: continue
        best, bm = NEG, (0, 0)
        for a, b in MOVES:
            if a > i or b > j or D[i - a, j - b] <= NEG / 2: continue
            if not a or not b: sc = SKIP * (a + b)
            else:
                sm = sim(i - a, a, j - b, b)
                hs = S[i - a]['h']; hr = bool(R[j - b].get('h'))
                sc = (sm - BASE) * (a + b) / 2 - 0.04 * (a + b - 2) - (0.15 if hs != hr else 0)
            v = D[i - a, j - b] + sc
            if v > best: best, bm = v, (a, b)
        D[i, j] = best; B[i, j] = bm
i, j = nS, nR; out = []
while i or j:
    a, b = (int(x) for x in B[i, j])
    out.append(dict(s=list(range(i - a, i)), r=list(range(j - b, j)), sc=round(sim(i - a, a, j - b, b), 3) if a and b else None)); i, j = i - a, j - b
out.reverse()
# 짝 없는 대조 문장: 같은 문단의 앞(없으면 뒤) 짝에 붙임
m = []
for p in out:
    if m and not p['r'] and m[-1]['r'] and m[-1]['s'] and S[p['s'][0]]['p'] == S[m[-1]['s'][-1]]['p']: m[-1]['s'] += p['s']; continue
    m.append(p)
out = m
json.dump(out, open('ref_pairs.json', 'w'), ensure_ascii=False)
sc = [p['sc'] for p in out if p['sc'] is not None]
print('pairs', len(sc), 'avg', round(sum(sc) / len(sc), 3), 'low<0.5', sum(x < .5 for x in sc), 'ref-only', sum(1 for p in out if not p['r']), 'row-only', sum(1 for p in out if not p['s']))
# ── 다듬기 ──
# ① 묶음 끝의 제목 문장은 다음 묶음 첫머리로(우리 줄은 '제목⏎첫 문장'이 한 줄인 곳이 많음)
for n in range(len(out) - 1):
    p, q = out[n], out[n + 1]
    while len(p['s']) > 1 and S[p['s'][-1]]['h'] and not S[p['s'][0]]['h'] and q['r']: q['s'].insert(0, p['s'].pop())
# ② 줄이 둘 넘는 묶음: 문장을 차례대로 줄마다 나눔(점수가 가장 높게)
def s1(ids, j):
    if not ids: return 0
    t = ' '.join(S[i]['t'] for i in ids); v = emb([t])[0]; best = -1
    for x in (R[j]['o'], R[j].get('t0') or R[j]['t']):
        if x: best = max(best, float(v @ emb([x])[0]) - (0.1 if x is not R[j]['o'] else 0))
    return best - BASE
for p in out:
    if len(p['r']) < 2 or not p['s']: continue
    ss, rr = p['s'], p['r']; best = None
    import itertools
    for cut in itertools.combinations(range(len(ss) + 1), len(rr) - 1):
        b = [0, *cut, len(ss)]
        if any(b[k] > b[k + 1] for k in range(len(b) - 1)): continue
        parts = [ss[b[k]:b[k + 1]] for k in range(len(rr))]
        v = sum(s1(pt, j) if pt else -0.05 for pt, j in zip(parts, rr))
        if best is None or v > best[0]: best = (v, parts)
    p['parts'] = best[1]
pickle.dump(C, open('emb.pkl', 'wb'))
json.dump(out, open('ref_pairs.json', 'w'), ensure_ascii=False)
print('split groups', sum(1 for p in out if 'parts' in p))
