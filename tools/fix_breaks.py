#!/usr/bin/env python3
"""본문 끊김 바로잡기 (운영자 요청, 2026-11-18) — check_breaks.py 로 찾고 인쇄본·문맥으로 확인한 곳을 고친다. 글자는 그대로.
  python3 tools/fix_breaks.py <책 ID> [--write]      고칠 목록: tools/break_fixes/<책 ID>.json
목록의 항목:
  쪽은 쪽 이름(153, 'i') 또는 쪽 이름 없는 쪽의 차례 '#3'
  {"join": [쪽, "앞 문단 끝 글", "뒤 문단 첫 글", "빈칸"]}        같은 쪽 안 끊긴 문단 잇기 ("" 또는 " ")
  {"fn": [쪽, "각주 번호", ["다음 쪽 본문 문단 첫머리", …], "빈칸"]}  다음 쪽 본문 문단들을 그 각주 끝으로 (문단끼리는 줄 바꿈)
  {"fncut": [쪽, "각주 번호", 다음 쪽 이름, "문단 안에서 각주 글이 시작하는 글", "빈칸"]}
                                                          본문 문단 속에 섞여 들어간 각주 글(그 글부터 문단 끝까지)을 각주 끝으로
본문을 도구로 다시 만들면 이 도구를 다시 돌린다. 원서 대조가 있는 책은 그 뒤 짝짓기(run_<id>.sh)도 다시."""
import json, re, sys, signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
bk = sys.argv[1]; p = f'content/texts/{bk}.json'
RAW = open(p).read(); T = json.loads(RAW); RAW_BODY = T['body']
def dump(o):   # 원래 파일 모양(들여쓰기·끝 줄 바꿈)을 그대로
    for ind in (2, 1, None, 4):
        for ea in (False, True):
            if json.dumps(json.loads(RAW), ensure_ascii=ea, indent=ind).rstrip() == RAW.rstrip():
                return json.dumps(o, ensure_ascii=ea, indent=ind) + RAW[len(RAW.rstrip()):]
    return json.dumps(o, ensure_ascii=False, indent=2) + '\n'
ops = json.load(open(f'tools/break_fixes/{bk}.json'))
parts = re.split(r'(\n?=== [^\n]*===\n?)', T['body'])
def pidx(n):
    if str(n).startswith('#'): return 1 + 2 * (int(str(n)[1:]) - 1)   # 쪽 이름이 없는 쪽: '#3' = 세 번째 쪽 표시
    k = [i for i in range(1, len(parts), 2) if parts[i].strip() == f'=== {n}쪽 ===']
    if len(k) != 1: sys.exit(f'{n}쪽: {len(k)}곳')
    return k[0]
def fn_end(t, fn, pn):
    m = re.search(rf'^\[\^{re.escape(fn)}\]:.*?(?=\n\s*\n|\n\[\^|\Z)', t, flags=re.M | re.S)
    if not m: sys.exit(f'{pn}쪽 각주 {fn} 없음')
    return m.start() + len(m.group(0).rstrip())
n = 0
for op in ops:
    if 'join' in op:
        pn, a, b, sp = op['join']; i = pidx(pn); t = parts[i + 1]
        rx = re.compile(re.escape(a) + r'[ \t]*\n\s*\n[ \t]*' + re.escape(b))
        h = rx.findall(t)
        if len(h) != 1: sys.exit(f'{pn}쪽 {a!r}+{b!r}: {len(h)}곳')
        parts[i + 1] = rx.sub(lambda _: a + sp + b, t)
    elif 'fn' in op:
        pn, fn, heads, sp = op['fn']; i = pidx(pn); j = i + 2
        paras = re.split(r'(\n\s*\n)', parts[j + 1]); moved = []
        for h in heads:
            k = [x for x in range(0, len(paras), 2) if paras[x] is not None and paras[x].strip().startswith(h)]
            if len(k) != 1: sys.exit(f'{pn}쪽 다음 쪽 {h!r}: {len(k)}곳')
            moved.append(paras[k[0]].strip()); paras[k[0]] = None
            if k[0] + 1 < len(paras) and paras[k[0] + 1] is not None: paras[k[0] + 1] = None
            elif k[0] - 1 >= 0: paras[k[0] - 1] = None
        parts[j + 1] = ''.join(x for x in paras if x is not None)
        t = parts[i + 1]; e = fn_end(t, fn, pn)
        parts[i + 1] = t[:e] + sp + '\n'.join(moved) + t[e:]
    elif 'fncut' in op:
        pn, fn, npn, start, sp = op['fncut']; i = pidx(pn); j = pidx(npn)
        t2 = parts[j + 1]; k = t2.find(start)
        if k < 0 or t2.count(start) != 1: sys.exit(f'{npn}쪽 {start!r}: {t2.count(start)}곳')
        end = re.search(r'\n\s*\n|\Z', t2[k:]).start() + k
        piece = t2[k:end].strip(); parts[j + 1] = t2[:k].rstrip(' ') + t2[end:]
        t = parts[i + 1]; e = fn_end(t, fn, pn)
        parts[i + 1] = t[:e] + sp + piece + t[e:]
    n += 1
new = ''.join(parts)
st = lambda s: sorted(re.sub(r'\s', '', s))
assert st(new) == st(T['body']), '글자가 달라짐'
print(f'{bk}: {n}곳 · 빈칸·자리 말고 글자는 같음')
def pg_paras(b):
    ps = re.split(r'\n?(=== [^\n]*===)\n?', b)
    return [[x for x in re.split(r'\n\s*\n', ps[i + 1]) if x.strip()] for i in range(1, len(ps), 2)]
def remap(old, new):
    """(쪽 순번, 문단 순번) 옛 자리 → 새 자리 (오디오북 sync 등에 씀). 바뀐 쪽만, 차례대로 맞춤 — 이어 붙인 문단은 합친 문단으로, 각주로 옮긴 문단은 앞 쪽의 그 각주로"""
    O, N = pg_paras(old), pg_paras(new); m = {}
    sq = lambda t: re.sub(r'\s', '', t)
    for k, ps in enumerate(O):
        if k < len(N) and [sq(x) for x in ps] == [sq(x) for x in N[k]]: continue   # 그대로인 쪽
        jj = 0; cur = N[k] if k < len(N) else []
        for j, t in enumerate(ps):
            u = sq(t)
            while jj < len(cur) and u not in sq(cur[jj]): jj += 1
            if jj < len(cur): m[(k + 1, j)] = (k + 1, jj); continue
            jj = 0
            prev = [x for x, w in enumerate(N[k - 1]) if u in sq(w)] if k else []
            if prev: m[(k + 1, j)] = (k, prev[-1])
    return m
if '--write' in sys.argv:
    T['body'] = new; open(p, 'w').write(dump(T)); print('→', p)
    ab = f'content/audiobooks/{bk}.json'
    import os
    if os.path.exists(ab):   # 오디오북 글 따라가기(sync)의 문단 자리도 새 자리로
        A = json.load(open(ab)); M = remap(RAW_BODY, new); ch = 0
        for c in A.get('chapters', []):
            for s_ in c.get('sync', []):
                if len(s_) >= 3 and s_[2] >= 0 and (s_[1], s_[2]) in M and M[(s_[1], s_[2])] != (s_[1], s_[2]):
                    s_[1], s_[2] = M[(s_[1], s_[2])]; ch += 1
        txt = open(ab).read()
        if ch: open(ab, 'w').write(json.dumps(A, ensure_ascii=False, indent=2 if '\n  ' in txt else None) + ('\n' if txt.endswith('\n') else '')); print(f'→ {ab} 글 따라가기 자리 {ch}곳 옮김')
