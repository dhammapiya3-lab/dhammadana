#!/usr/bin/env python3
"""『테라와다 불교의범』(DL-0026) 양쪽으로 보기 — 빠알리 줄 ↔ 번역 줄 뜻 짝 (운영자 요청, 2026-11-19)

  python3 tools/dl0026_pairs.py dump [첫 쪽 순번]   → tools/out/dl0026_pairs/NN.txt (펼친 면마다 왼쪽 항목 L·오른쪽 줄 R)
  python3 tools/dl0026_pairs.py build              → tools/dl0026_pairs/*.txt(짝 적은 것)를 읽어 content/parallel/DL-0026.spread.json

짝 적는 법 (tools/dl0026_pairs/NNN.txt, 펼친 면마다 한 줄):
  @20 1=1 2=2 3=3-4 4=5,6<깨달으신 5=6>깨달으신
  · '@<왼쪽 쪽 순번>' 다음에 '왼쪽 항목 번호=오른쪽 줄 번호' 들 (빈칸으로 나눔)
  · 오른쪽: 3-4 범위, 5,6 여럿, 6<글 = 그 줄의 '글' 앞까지, 6>글 = 그 줄의 '글'부터 끝까지, 6>글A<글B = 그 사이 (글 속 빈칸은 _)
  · 왼쪽 여럿: 1+2=3 · 쪽을 넘는 짝: 다른 펼친 면의 줄은 '118:1'(그 면의 오른쪽 1줄·왼쪽 1항목)
  · 같은 쪽 안의 짝(빠알리 줄 바로 아래 번역): 왼쪽은 'l4=l5'(왼쪽 항목끼리), 오른쪽은 'r7=r8-9'(오른쪽 줄끼리)
  · '@20 =' 은 왼쪽 항목 수와 오른쪽 줄 수가 같을 때 차례대로 1:1
  · 짝이 없는 항목은 적지 않음 (강조하지 않음)
왼쪽 항목 = 로마자 줄 하나 + 바로 뒤 한글 소리 줄(들) (소리 줄이 로마자 두 줄 뒤에 오면 뒤 줄에 딸림). 글자는 본문 그대로 — 이 도구는 자리만 적음.
"""
import json, re, sys, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TX = os.path.join(ROOT, 'content/texts/DL-0026.json')
LAT = re.compile(r'[A-Za-zĀ-ſḀ-ỿ]{2}')
HAN = re.compile(r'[가-힣]')
PAREN = re.compile(r'^[(（][^()（）]*[)）]$')

def strip(l):
    l = re.sub(r'^(##|\^\^|::|>>|\|\||\+\+|%%) ', '', l)
    return re.sub(r'\*\*|°°|@@|==|§§|\{\{|\}\}|\[\^[^\]]*\]', '', l).strip()

def pages():
    body = json.load(open(TX))['body']
    parts = re.split(r'^=== (.+?) ===$', body, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        n = (i + 1) // 2
        ps = [ '\n'.join(x.strip() for x in s.strip().split('\n')) for s in re.split(r'\n\s*\n', parts[i + 1]) ]
        ps = [p for p in ps if p]
        out.append((n, parts[i], ps))
    return out

def items(n, ps):
    """왼쪽 항목: [(번호, [(s,k)...] 줄들, 보이는 글)]"""
    res = []
    for s, p in enumerate(ps):
        if p.startswith('![') or p.startswith('|') or p.startswith('%%'): continue
        ls = p.split('\n'); k = 0
        while k < len(ls):
            t = strip(ls[k])
            if not t: k += 1; continue
            if LAT.search(t) and (not HAN.search(re.sub(r'\([^)]*\)', '', t)) or re.match(r'^[^A-Za-zĀ-ſḀ-ỿ가-힣]*[A-Za-zĀ-ſḀ-ỿ]', t)):
                grp = [(s, k)]; txt = [t]; k += 1
                while k < len(ls) and HAN.search(strip(ls[k])) and not LAT.search(re.sub(r'\([^)]*\)', '', strip(ls[k]))) and not strip(ls[k]).startswith('['):
                    grp.append((s, k)); k += 1   # 한글 소리 줄
                res.append((grp, ' / '.join(txt), True))
            else:
                if res and res[-1][2] and re.search(r'[가-힣]-', t) and not t.startswith('['):
                    res[-1][0].append((s, k))   # 다른 문단에 따로 놓인 한글 소리 줄은 앞 로마자 항목에 딸림
                elif not PAREN.match(t): res.append(([(s, k)], t, False))
                k += 1
    return [(i + 1, g, t, lat) for i, (g, t, lat) in enumerate(res)]

def rlines(n, ps):
    res = []
    for s, p in enumerate(ps):
        if p.startswith('![') or p.startswith('%%'): continue
        for k, l in enumerate(p.split('\n')):
            t = strip(l)
            if not t or PAREN.match(t) or re.fullmatch(r'[-~]+', t): continue
            res.append((s, k, t))
    return [(i + 1, s, k, t) for i, (s, k, t) in enumerate(res)]

def spreads():
    P = pages(); by = {n: (lab, ps) for n, lab, ps in P}
    for n, lab, ps in P:
        if n % 2 or n + 1 not in by: continue
        L = items(n, ps); R = rlines(n + 1, by[n + 1][1])
        if not R or (sum(1 for x in L if x[3]) < 2 and not any(LAT.search(re.sub(r'\([^)]*\)', '', r[3])) for r in R) and not any(x[3] for x in L)): continue
        yield n, lab, by[n + 1][0], L, R

def dump(start=0):
    od = os.path.join(ROOT, 'tools/out/dl0026_pairs'); os.makedirs(od, exist_ok=True)
    buf, size, part = [], 0, 1
    for n, la, lb, L, R in spreads():
        if n < start: continue
        nl = sum(1 for x in L if x[3])
        head = f'@{n}  ({la} | {lb})' + ('  [로마자 항목 수 = 오른쪽 줄 수]' if len(L) == len(R) else '')
        s = [head] + [f'L{i}{"" if lat else "·"} {t if lat or len(t) < 36 else t[:34] + "…"}' for i, g, t, lat in L] + [f'R{i} {t if len(t) < 90 else t[:88] + "…"}' for i, s_, k, t in R] + ['']
        buf += s; size += sum(len(x) for x in s)
        if size > 14000:
            open(os.path.join(od, f'{part:02d}.txt'), 'w').write('\n'.join(buf)); buf, size, part = [], 0, part + 1
    if buf: open(os.path.join(od, f'{part:02d}.txt'), 'w').write('\n'.join(buf))
    print('묶음 파일', part, '개 →', od)

def parse_r(tok, R, SP=None):
    out = []
    for x in tok.split(','):
        m = re.fullmatch(r'(\d+):(.+)', x)   # 다른 펼친 면의 오른쪽 줄: 118:1
        if m:
            n2 = int(m.group(1)); out += [[n2 + 1] + r for r in parse_r(m.group(2), SP[n2][1], SP)]; continue
        m = re.fullmatch(r'(\d+)>(.+?)<(.+)', x)   # 줄 가운데 한 토막: 4>글A<글B
        if m:
            i = int(m.group(1)); r = R[i - 1]; a = m.group(2).replace('_', ' '); b = m.group(3).replace('_', ' ')
            if a not in r[3] or b not in r[3][r[3].index(a):]: raise ValueError(f'R{i} 에 "{a}…{b}" 없음: {r[3]}')
            out.append([r[1], r[2], '>' + a + '<' + b]); continue
        m = re.fullmatch(r'(\d+)([<>])(.+)', x)
        if m:
            i = int(m.group(1)); r = R[i - 1]; w = m.group(3).replace('_', ' ')
            if w not in r[3]: raise ValueError(f'R{i} 에 "{w}" 없음: {r[3]}')
            out.append([r[1], r[2], m.group(2) + w]); continue
        x = x.lstrip('_')
        a, _, b = x.partition('-'); a = int(a); b = int(b) if b else a
        for i in range(a, b + 1): r = R[i - 1]; out.append([r[1], r[2]])
    return out

def build():
    SP = {n: (L, R) for n, la, lb, L, R in spreads()}
    units, done, errs = [], set(), []
    for f in sorted(glob.glob(os.path.join(ROOT, 'tools/dl0026_pairs/*.txt'))):
        for ln, line in enumerate(open(f), 1):
            line = line.split('#')[0].strip()
            if not line.startswith('@'): continue
            toks = line.split(); n = int(toks[0][1:])
            if n not in SP: errs.append(f'{os.path.basename(f)}:{ln} 쪽 순번 {n} 이 펼친 면이 아님'); continue
            L, R = SP[n]; done.add(n)
            if toks[1:] == ['=']:
                if len(L) != len(R): errs.append(f'@{n} 은 1:1 이 안 됨 ({len(L)}/{len(R)})'); continue
                pairs = [(str(i), str(i)) for i in range(1, len(L) + 1)]
            else:
                pairs = [t.split('=', 1) for t in toks[1:]]
            used = {lt for lt, rt in pairs}
            for i, g, t, lat in L:   # [인도자]·【첫 번째】 처럼 글이 같은 이름표 줄은 저절로 짝 (같은 이름표가 여럿이면 차례대로)
                if lat or not t.startswith(('[', '【')) or str(i) in used: continue
                ls = [y[0] for y in L if not y[3] and y[2] == t]; rs = [r[0] for r in R if r[3] == t]
                if len(ls) == len(rs): pairs.append((str(i), str(rs[ls.index(i)])))
            for lt, rt in pairs:
                try:
                    lg = []
                    for i in lt.split('+'):
                        if i[:1] == 'r': lg += [[n + 1] + r for r in parse_r(i[1:], R)]; continue   # 오른쪽 쪽 안의 짝 (r7=r8)
                        if ':' in i: n2, i2 = i.split(':'); lg += [[int(n2), s, k] for s, k in SP[int(n2)][0][int(i2) - 1][1]]   # 다른 펼친 면의 왼쪽 항목
                        else: lg += [[n, s, k] for s, k in L[int(i) - 1][1]]
                    rg = []
                    for x in rt.split(','):
                        if x[:1] == 'r': x = x[1:]
                        if x[:1] == 'l':   # 왼쪽 쪽 안의 짝 (l3=l4, 왼쪽 항목 번호)
                            a, _, b = x[1:].partition('-'); b = b or a
                            for i in range(int(a), int(b) + 1): rg += [[n, s, k] for s, k in L[i - 1][1]]
                            continue
                        if re.fullmatch(r'\d+:.+', x): rg += parse_r(x, R, SP)
                        else: rg += [[n + 1] + r for r in parse_r(x, R)]
                except Exception as e:
                    errs.append(f'@{n} {lt}={rt}: {e}'); continue
                units.append({'L': lg, 'R': rg})
    json.dump({'book': 'DL-0026', 'kind': 'spread-pairs', 'units': units}, open(os.path.join(ROOT, 'content/parallel/DL-0026.spread.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    tot = sum(1 for _ in SP)
    print(f'짝 {len(units)}개, 펼친 면 {len(done)}/{tot}')
    for e in errs: print('!', e)

if __name__ == '__main__':
    c = sys.argv[1] if len(sys.argv) > 1 else ''
    if c == 'dump': dump(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    elif c == 'build': build()
    else: print(__doc__)
