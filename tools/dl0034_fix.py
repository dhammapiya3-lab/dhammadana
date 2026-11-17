#!/usr/bin/env python3
"""『업과 윤회의 법칙』(DL-0034) 교정 목록 적용 (운영자 요청, 2026-11-18).

교정 목록 tools/dl0034_fixes.json: [{"p": ["6쪽", …] 또는 null(책 전체), "a": 지금 글, "b": 고칠 글, "n": 고칠 곳 수(선택), "re": true(정규식)}]
- 찾을 때 °°(기울임)·**(굵게) 표시는 글자 사이에 끼어 있어도 무시하고 찾으며, 고친 뒤에도 그 표시는 제자리에 남김.
- 쪽(p)을 주면 그 쪽 안에서만 고침. 하나라도 못 찾으면 멈춤(이미 고친 것이면 '이미 고침'으로 넘어감).
- 고친 뒤 고친 곳 말고는 글자가 같은지 대조.
쓰는 법: python3 tools/dl0034_fix.py [--write]     찾기만: python3 tools/dl0034_fix.py --find 글…
pdf2text_dl0034.py 로 본문을 다시 만들면 이 도구를 다시 돌린다.
"""
import json, re, sys, difflib, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(ROOT, 'content/texts/DL-0034.json')
FIX = os.path.join(ROOT, 'tools/dl0034_fixes.json')
MK = r'(?:°°|\*\*)*'

def pages(b):
    out = []; pos = 0; name = ''
    for m in re.finditer(r'^=== ?(.*?) ?===$', b, re.M):
        out.append((pos, m.start(), name)); pos = m.start(); name = m.group(1)
    out.append((pos, len(b), name)); return out

def fuzzy(a):
    return re.compile(MK.join(re.escape(c) for c in a))

def remap(seg, a, b):
    """seg = a 에 표시(°° **)가 끼어 있는 글 → b 에 같은 표시를 같은 자리에."""
    toks = []; plain = ''; i = 0
    while i < len(seg):
        if seg.startswith('°°', i) or seg.startswith('**', i):
            toks.append((len(plain), seg[i:i+2])); i += 2
        else:
            plain += seg[i]; i += 1
    assert plain == a, (plain, a)
    if not toks: return b
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    def mp(x):
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal' and i1 <= x <= i2 and i2 > i1: return j1 + (x - i1)   # 앞 글자에 붙임
            if i1 <= x < i2 or (x == i2 and tag == 'equal' and x == len(a)):
                return j1 + (x - i1) if tag == 'equal' else (j1 if x == i1 else j2)
            if x == i2 and i2 == len(a): return j2
        return len(b)
    out = b; shift = 0
    ins = sorted(((mp(x), t, k) for k, (x, t) in enumerate(toks)), key=lambda z: (z[0], z[2]))
    for x, t, _ in ins:
        out = out[:x + shift] + t + out[x + shift:]; shift += 2
    return out

PART = set('을를이가은는의에와과로도만')
def op_fullwidth(b):
    n = len(re.findall('[．０-９（）：，？]', b))
    b = re.sub(r' ?．(?=[^\s*\[\]\)’”]|$)', '. ', b)   # 낱말 앞이면 빈칸
    b = re.sub(r' ?．', '.', b)
    b = re.sub('[０-９]', lambda m: chr(ord(m.group(0)) - 0xFEE0), b).replace('（', '(')
    b = re.sub(r'）(?=[가-힣])(?![%s])' % ''.join(PART), ') ', b).replace('）', ')')
    b = re.sub(r'：(?=\S)', ': ', b).replace('：', ':')
    b = re.sub(r'，(?=\S)', ', ', b).replace('，', ',')
    b = re.sub(r'？(?=[^\s*|])', '? ', b).replace('？', '?')
    return b, n

def op_quotes(b):
    out = []; n = 0
    OPEN = set(' \t\n([{‘“-—/·')
    for i, ch in enumerate(b):
        if ch in '"\'`':
            j = len(out)
            while j > 0 and ''.join(out[max(0, j-2):j]) in ('°°', '**'): j -= 2
            prev = out[j-1] if j else '\n'
            op = ch == '`' or prev in OPEN
            out.append(('“' if op else '”') if ch == '"' else ('‘' if op else '’')); n += 1
        else:
            out.append(ch)
    return ''.join(out), n

def apply(b, fixes, log):
    for f in fixes:
        if f.get('op'):
            b, n = (op_fullwidth if f['op'] == 'fullwidth' else op_quotes)(b)
            log.append(('고침', f, n)); continue
        a, nb, pg = f['a'], f['b'], f.get('p')
        rx = re.compile(a) if f.get('re') else fuzzy(a)
        segs = pages(b); total = 0; newb = []; last = 0; found_pages = set()
        for s, e, name in segs:
            if pg and name not in pg: continue
            for m in rx.finditer(b, s, e):
                if m.start() < last: continue
                rep = m.expand(nb) if f.get('re') else remap(m.group(0), a, nb)
                newb.append(b[last:m.start()]); newb.append(rep); last = m.end(); total += 1; found_pages.add(name)
        newb.append(b[last:]); b2 = ''.join(newb)
        miss = [p for p in (pg or []) if p not in found_pages]
        if total == 0:
            done = fuzzy(nb).search(b) if not f.get('re') else True
            log.append(('이미 고침' if done else '못 찾음', f, 0)); continue
        if f.get('n') is not None and total != f['n']:
            log.append(('수가 다름', f, total))
        elif miss:
            log.append(('일부 쪽 없음:' + ','.join(miss), f, total))
        else:
            log.append(('고침', f, total))
        b = b2
    return b

def main():
    if '--find' in sys.argv:
        b = json.load(open(TXT))['body']; segs = pages(b)
        for q in sys.argv[sys.argv.index('--find') + 1:]:
            hs = [(n, b[max(0, m.start()-30):m.end()+30].replace('\n', '⏎')) for s, e, n in segs for m in fuzzy(q).finditer(b, s, e)]
            print(f'## {q} : {len(hs)}')
            for n, c in hs[:15]: print('  ', n, '|', c)
        return
    d = json.load(open(TXT)); b0 = d['body']; fixes = json.load(open(FIX)); log = []
    b1 = apply(b0, fixes, log)
    # 읽기 목차의 제목·at 도 같은 목록으로 (쪽 구분 없이)
    tl = [dict(f, p=None, n=None) for f in fixes]
    toc2 = []
    for t in d['toc']:
        t = dict(t)
        for k in ('title', 'at'):
            if t.get(k): t[k] = apply(t[k], tl, [])
        toc2.append(t)
    plain = lambda x: x.replace('°°', '').replace('**', '')
    pb = plain(b1)
    miss = [t for t in toc2 if t.get('at') and plain(t['at']) not in pb]
    for t in miss: print('목차 at 못 찾음:', t)
    tch = sum(1 for a, c in zip(d['toc'], toc2) if a != c)
    bad = 0
    for st, f, n in log:
        if st != '고침' and st != '이미 고침': bad += 1
        if st != '고침' or '-v' in sys.argv: print(f'{st:10} {n:3}  {f.get("p") or "전체"}  {f["a"]!r} → {f["b"]!r}')
    bad += len(miss)
    print(f'목록 {len(fixes)}줄 · 고친 곳 {sum(n for st,f,n in log)} · 읽기 목차 {tch}줄 · 확인할 것 {bad}')
    if '--write' in sys.argv:
        if bad and '--force' not in sys.argv: sys.exit('확인할 것이 있어 쓰지 않음 (--force)')
        d['body'] = b1; d['toc'] = toc2; open(TXT, 'w').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        print('썼음:', TXT)
    else:
        open('/tmp/dl0034_fixed.txt', 'w').write(b1)

if __name__ == '__main__': main()
