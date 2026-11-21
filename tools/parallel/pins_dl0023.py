"""『법구경 이야기』 1~3권 원서 대조 손 짝 — run_dl0023.sh 가 부름 (한 줄에 인자 하나).
  python3 tools/parallel/pins_dl0023.py DL-0023
이야기마다: 한국어 '## N 번째 이야기' + 제목 줄 ↔ 원서 '1.1 The Story about …' + 빠알리 제목(--pin·--seg),
장마다: 한국어 '## 제N장 …' ↔ 원서 장 제목(--pin·--seg). 이야기 첫머리 문단끼리도 --seg. 한국어 이야기와 원서 이야기는 장 안 차례대로(장마다 개수가 같음을 확인)."""
import os, re, json, sys
B = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(os.path.join(REPO, 'content/texts', B + '.json')))
O = json.load(open(os.path.join(REPO, 'tools/out/parallel', B + '.en.paras.json')))
body = T['body'].replace('\r\n', '\n')
ms = list(re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M))
KO = []
for n, m in enumerate(ms, 1):
    end = ms[n].start() if n < len(ms) else len(body)
    for s, para in enumerate([x.strip() for x in re.split(r'\n\s*\n', body[m.end():end]) if x.strip()]):
        KO.append((f'{n}:{s}', para))
kv, ks = [], {}   # 한국어 장, 장마다 이야기
v = None
for i, (k, p) in enumerate(KO):
    m = re.match(r'## 제(\d+)장', p)
    if m: v = int(m.group(1)); kv.append((v, k)); ks[v] = []; continue
    if v is not None and re.match(r'## \S+ 번째 이야기(\[\^[^\]]+\])*$', p):
        intro = KO[i + 2] if re.match(r'부처님', KO[i + 2][1]) and '게송' in KO[i + 2][1][:120] else None   # '부처님께서 … 게송 N번을 설하셨다/읊으셨다.'
        ks[v].append((k, KO[i + 1][0], intro[0] if intro else None))
ov, os_ = {}, {}
for i, o in enumerate(O):
    if o['k'] == 'h' and re.match(r'\d+\. The ', o['t']) and o['t'].split('.')[0].isdigit() and not o.get('story'):
        ov[int(o['t'].split('.')[0])] = i
    if o.get('story'):
        vv = int(o['story'].split('.')[0]); j = i + 1
        while O[j]['k'] != 'p': j += 1   # 이야기 첫 본문 문단 '“…,” this Dhamma teaching was given by the Teacher …'
        os_.setdefault(vv, []).append((i, i + 1 if O[i + 1]['k'] == 'h' and O[i + 1].get('pali') else None, j))
args = []
for v, k in kv:
    args += ['--pin', f'{k}={ov[v]}', '--seg', f'{k}={ov[v]}']
    assert len(ks[v]) == len(os_[v]), (v, len(ks[v]), len(os_[v]))
    for (k1, k2, k3), (e1, e2, e3) in zip(ks[v], os_[v]):
        e = f'{e1}+{e2}' if e2 is not None else f'{e1}'
        args += ['--pin', f'{k1}+{k2}={e}', '--seg', f'{k1}={e1}']
        if k3:
            args += ['--seg', f'{k3}={e3}']
            # 이야기 첫머리 문단끼리 따로 한 마디: 첫머리 다음 문단끼리도 경계 — 원서 첫머리는 게송 구절로 시작해 뜻 비슷함이 낮게 나와, 원서만 긴 이야기(26.29 레와따)에서 다른 문장에 끌려가지 않게
            # 한국어 첫머리 다음의 각주 풀이·'이 이야기는 …에 자세히 나온다/…에서 시작된다' 문단은 첫머리 마디에 넣음(원서 첫머리 문단에 같은 말이 있음)
            j = [x[0] for x in KO].index(k3) + 1
            while j < len(KO) and (KO[j][1].startswith('[^') or '이야기는' in KO[j][1][:25]): j += 1
            if j < len(KO) and not re.match(r'## ', KO[j][1]): args += ['--seg', f'{KO[j][0]}={e3 + 1}']   # 이야기 첫머리('부처님께서 … 게송 N번을 설하셨다' ↔ '… this Dhamma teaching was given by the Teacher …')도 경계 — 원서에만 긴 경 인용(3.1 메기야 경)이 있어도 밀리지 않게
# 게송마다 경계: 한국어 '++ …(N)' 게송 묶음 첫 문단 ↔ 원서 빠알리 게송 'N. …'(pv) — 한국어판이 앞 이야기를 가리키며 줄여 쓴 곳(26.29 '게송 98번 이야기에서 이미 자세히 설명했다')에서도 게송 앞뒤가 밀리지 않게
def _key(k): return tuple(map(int, k.split(':')))
kvs = {}   # 게송 묶음 첫 문단: '++' 로 시작하고 앞 문단이 '++' 가 아니거나 '(N)' 으로 끝남 — 묶음 안 첫 번호('(231)'·'(246, 247)'·'(229-230)')
NUM = r'\((\d+)(?:\s*[,~\-–]\s*\d+)*\)'
for i, (k, p) in enumerate(KO):
    if not p.startswith('++'): continue
    if i and KO[i - 1][1].startswith('++') and not re.search(NUM + r'\s*$', KO[i - 1][1]): continue
    j = i
    while j < len(KO) and KO[j][1].startswith('++'):
        m = re.search(NUM, KO[j][1])
        if m: break
        j += 1
    if j < len(KO) and m and int(m.group(1)) not in kvs: kvs[int(m.group(1))] = k
evs = {}
for i, o in enumerate(O):
    m = re.match(r'(\d+)\.', o['t']) if o['k'] == 'pv' else None
    if m and int(m.group(1)) not in evs: evs[int(m.group(1))] = i
vs = [(n, kvs[n], evs[n]) for n in sorted(set(kvs) & set(evs))]
lk, le, nv = (0, 0), -1, 0
segs = [(_key(args[i + 1].split('=')[0]), int(args[i + 1].split('=')[1])) for i in range(0, len(args), 2) if args[i] == '--seg']
for n, k, e in sorted(vs, key=lambda x: _key(x[1])):
    # 다른 경계와 차례가 어긋나지 않을 때만
    if any((sk < _key(k)) != (se < e) for sk, se in segs): continue
    if _key(k) <= lk or e <= le: continue
    args += ['--seg', f'{k}={e}']; lk, le = _key(k), e; nv += 1
print('게송 경계', nv, '/ 한국어 게송', len(kvs), '원서 게송', len(evs), file=sys.stderr)
# 손으로 정한 것: tools/parallel/dl0023_hand.txt (책<TAB>종류<TAB>한국어<TAB>원서[<TAB>원서 끝])
#   seg  — 한국어 문단(글 첫머리)과 원서 문단(글 첫머리)이 함께 새 마디를 시작(같은 한국어 문단의 저절로 만든 경계는 뺌)
#   none — 원서 문단(글 첫머리, 끝 문단까지)을 짝짓지 않음: 한국어판이 줄여 옮겨 원서에만 있는 부분
#   spin — 문장 짝(align.py --spin): '한국어 문장 첫머리'·'원서 문장 첫머리', 한쪽이 비면 그 문장은 짝 없음
def _nth(t):
    m = re.match(r'(.*)~(\d+)$', t); return (m.group(1), int(m.group(2))) if m else (t, 0)
def _ki(t):
    t, n = _nth(t); L = [k for k, p in KO if p.startswith(t)]
    assert (len(L) == 1 and not n) or (n and len(L) >= n), ('한국어 문단', t, len(L)); return L[max(n, 1) - 1]
def _ei(t):
    t, n = _nth(t); L = [i for i, o in enumerate(O) if o['t'].startswith(t)]
    assert (len(L) == 1 and not n) or (n and len(L) >= n), ('원서 문단 (같은 글이 여럿이면 ~N)', t, len(L)); return L[max(n, 1) - 1]
HF = os.path.join(REPO, 'tools/parallel/dl0023_hand.txt')
for ln in open(HF, encoding='utf-8'):
    if not ln.strip() or ln.startswith('#'): continue
    c = ln.rstrip('\n').split('\t')
    if c[0] != B: continue
    kind = c[1]
    if kind == 'seg':
        k, e = _ki(c[2]), _ei(c[3])
        for i in range(len(args) - 2, -1, -2):
            if args[i] == '--seg' and args[i + 1].split('=')[0] == k: del args[i:i + 2]
        args += ['--seg', f'{k}={e}']
    elif kind == 'none':
        e0 = _ei(c[3]); e1 = next(i for i in range(e0, len(O)) if O[i]['t'].startswith(_nth(c[4])[0])) if len(c) > 4 and c[4] else e0   # 끝 문단은 첫 문단 뒤에서 처음 맞는 것
        args += ['--pin', '=' + '+'.join(str(i) for i in range(e0, e1 + 1))]
    elif kind == 'spin':
        args += ['--spin', f'{c[2]}={c[3]}']
segs = sorted(((_key(args[i + 1].split('=')[0]), int(args[i + 1].split('=')[1])) for i in range(0, len(args), 2) if args[i] == '--seg'))
bad = [(a, b) for a, b in zip(segs, segs[1:]) if b[1] < a[1]]
assert not bad, ('경계 차례가 어긋남', bad[:3])
print('\n'.join(args))
