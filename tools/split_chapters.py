#!/usr/bin/env python3
"""장(챕터)이 바뀌면 늘 새 쪽에서 시작하게 합니다 (운영자 요청, 2026-11). 글자는 바꾸지 않습니다.
  python3 tools/split_chapters.py            # 모든 책 검사만
  python3 tools/split_chapters.py --write    # 고치기

- 목차의 큰 항목(sub 아님)이 쪽 중간(at)에서 시작하면, 그 자리에 같은 쪽 이름의 쪽 표시(=== N쪽 ===)를 하나 더 넣어
  앞 장의 글과 화면이 나뉘게 합니다. 뒤 목차 항목들의 쪽 차례는 하나씩 뒤로.
- 쪽 표시가 '## 소제목' 줄을 가른 곳(## 빤 / === 247쪽 === / 냣띠)이 있으면 알려 줍니다.
- 각주 내용([^n]:)은 각주 번호가 있는 쪽으로 따라갑니다.
"""
import glob, json, re, sys

MARK = re.compile(r'(?m)^===\s*(.*?)\s*===\s*$')
plain = lambda s: re.sub(r'^(?:## |\^\^ |:: |\|\| |\+\+ )+', '', s.strip()).replace('**', '').replace('==', '')


def parse(body):
    ms = list(MARK.finditer(body)); segs = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(body)
        segs.append([m.group(1), body[m.end():end].strip('\n')])
    return segs


def para_index(text, at):
    ps = [p for p in text.split('\n\n') if p.strip()]
    a = plain(at)
    for k, p in enumerate(ps):
        if plain(p).startswith(a) or p.strip().startswith(at): return k, ps
    return None, ps


def fix(d, write):
    segs = parse(d['body']); toc = d['toc']; changed = []
    while True:
        cand = None
        for t in toc:
            if t.get('sub') or not t.get('at'): continue
            k, ps = para_index(segs[t['page'] - 1][1], t['at'])
            if k is None: print('  ! at 을 못 찾음:', t); continue
            if k == 0: t.pop('at'); changed.append(t['title'] + ' (at 정리)'); continue
            cand = (t, k, ps); break
        if not cand: break
        t, k, ps = cand; p = t['page']
        label = segs[p - 1][0]
        a, b = ps[:k], ps[k:]
        # 각주 내용은 번호가 있는 쪽으로
        fa = [x for x in b if re.match(r'\[\^(\d+)\]:', x) and f'[^{re.match(r"[[]\^(\d+)", x).group(1)}]' in '\n\n'.join(a)]
        b = [x for x in b if x not in fa]; a = a + fa
        fb = [x for x in a if re.match(r'\[\^(\d+)\]:', x) and f'[^{re.match(r"[[]\^(\d+)", x).group(1)}]' not in '\n\n'.join(y for y in a if y != x) and f'[^{re.match(r"[[]\^(\d+)", x).group(1)}]' in '\n\n'.join(b)]
        a = [x for x in a if x not in fb]; b = b + fb
        segs[p - 1][1] = '\n\n'.join(a); segs.insert(p, [label, '\n\n'.join(b)])
        for u in toc:
            if u is t: continue
            if u['page'] > p: u['page'] += 1
            elif u['page'] == p and u.get('at'):
                kk, _ = para_index('\n\n'.join(ps), u['at'])
                if kk is not None and kk >= k:
                    u['page'] += 1
                    if kk == k: u.pop('at')
        t['page'] = p + 1; t.pop('at')
        changed.append(f"{t['title']} → {label or '(이름 없는)'} 쪽을 둘로 나눠 새 쪽에서 시작")
    body = ''.join(f'=== {l} ===\n{x}\n\n' if l else f'=== ===\n{x}\n\n' for l, x in segs).rstrip('\n') + '\n'
    # 쪽 표시가 짧은 소제목 줄을 가른 곳
    for m in re.finditer(r'(?m)^## [^\n]{1,8}\n\n=== [^\n]*===\n(?!## )[^\n]{0,20}', body):
        print('  ! 쪽 표시가 소제목을 가름:', repr(m.group()))
    return body, changed


for f in sorted(glob.glob('content/texts/*.json')):
    d = json.load(open(f)); old = d['body']
    if not MARK.search(old): continue
    body, changed = fix(d, '--write' in sys.argv)
    st = lambda s: re.sub(r'\s', '', MARK.sub('', s))
    assert sorted(st(body)) == sorted(st(old)), f + ' 글자가 달라짐'
    if changed: print(f, changed)
    if changed and '--write' in sys.argv:
        d['body'] = body; json.dump(d, open(f, 'w'), ensure_ascii=False, indent=2); open(f, 'a').write('\n')
