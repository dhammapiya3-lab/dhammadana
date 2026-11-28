"""짝(ref_pairs.json)에 제목 자리 다듬기·손으로 정한 짝(ref_fix.txt)을 더해 줄마다 대조 번역본(r)을 넣는다.
python3 ref_make.py 자료.trans.json ref_sents.json ref_pairs.json ref_fix.txt 결과.trans.json
ref_fix.txt: '줄id = 대조 문장 첫머리 + 첫머리 …' (그 문장들을 이 줄로 옮김, '줄id =' 만 쓰면 비움)"""
import sys, json, re
D = json.load(open(sys.argv[1])); R = D['rows']; S = json.load(open(sys.argv[2]))['sents']; P = json.load(open(sys.argv[3]))
A = {j: [] for j in range(len(R))}; RC = set()
for p in P:
    if not p['r']: continue
    parts = p.get('parts') or [p['s']] + [[] for _ in p['r'][1:]]
    for k, (j, pt) in enumerate(zip(p['r'], parts)):
        A[j] = list(pt)
        if not pt and k and any(parts[:k]): RC.add(j)
headish = lambda t: t and len(t) <= 70 and not re.search(r'[.!?’\'"”]$', t.strip())
# 제목 문장: 앞 줄 원서가 제목 줄로 끝나고(또는 앞 줄이 비어 있는 제목 줄) 이 줄 원서는 제목으로 시작하지 않으면 앞 줄로
for j in range(1, len(R)):
    while A[j] and S[A[j][0]]['h']:
        prev = R[j - 1]; tail = prev['o'].split('\n')[-1].strip(); head = R[j]['o'].split('\n')[0].strip()
        if (headish(tail) and not headish(head)) or (prev.get('h') and not A[j - 1] and not headish(head)):
            A[j - 1].append(A[j].pop(0)); RC.discard(j - 1)
        else: break
# 손으로 정한 짝
ID = {r['id']: j for j, r in enumerate(R)}
for line in open(sys.argv[4], encoding='utf-8'):
    line = line.split('#', 1)[0].strip()
    if not line: continue
    rid, rhs = [x.strip() for x in line.split('=', 1)]
    ids = []
    for pre in [x.strip() for x in rhs.split('+') if x.strip()]:
        hit = [i for i, s in enumerate(S) if s['t'].startswith(pre)]
        assert len(hit) == 1, (rid, pre, len(hit)); ids.append(hit[0])
    for j in A: A[j] = [i for i in A[j] if i not in ids]
    A[ID[rid]] = ids; RC.discard(ID[rid])
used = sorted(i for v in A.values() for i in v); miss = sorted(set(range(len(S))) - set(used)); assert used == list(range(len(S))), ("빠지거나 겹친 대조 문장", miss, [S[i]["t"] for i in miss])
for j, r in enumerate(R):
    r['r'] = ' '.join(S[i]['t'] for i in A[j])
    if not r['r'] and j in RC: r['rc'] = 1
    else: r.pop('rc', None)
D['cols']['r'] = '대조 번역본'
json.dump(D, open(sys.argv[5], 'w'), ensure_ascii=False)
print('rows with r', sum(1 for r in R if r['r']), 'rc', sum(1 for r in R if r.get('rc')), 'empty', sum(1 for r in R if not r['r'] and not r.get('rc')))
