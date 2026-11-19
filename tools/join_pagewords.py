"""쪽이 넘어가며 가운데가 잘린 한국어 낱말 바로잡기 (운영자 요청, 2026-11-19 — 지침)

인쇄본에서 한 낱말이 쪽 끝에서 잘려 다음 쪽으로 넘어간 곳('…바른 노력' / === 125쪽 === / '과 바른 마음챙김의…')은
사이트에서 쪽마다 따로 문단이 되므로, 원서 대조 '문장마다'·듣기·글 파일에서 '노력 과'처럼 낱말이 갈라져 보이고 들린다.
→ 잘린 뒷조각(다음 쪽 첫 낱말 '과')을 앞 쪽 마지막 문단 끝으로 옮겨 낱말을 하나로 붙인다('노력과').
  뒷조각이 다음 쪽 문단 전체라 옮기면 문단이 비게 되는 곳('…보여 준' / '다.')은 반대로 앞 조각('준')을 다음 쪽 문단 앞으로 옮긴다
  (문단 수가 바뀌지 않게 — 원서 대조 문단 열쇠·오디오북 글 따라가기·책갈피 자리가 그대로).
글자는 하나도 바꾸지 않고 쪽 경계 자리만 옮긴다(쪽 표시 === N쪽 === 는 그대로).

  python3 tools/join_pagewords.py --scan [ID…]     # 찾기: kiwipiepy(한국어 형태소 분석, pip install kiwipiepy)로 쪽 경계의
                                                   #   '앞 조각+뒷조각'이 붙은 낱말인지 판단 → tools/out/pagewords/<ID>.tsv (확인할 곳)
  python3 tools/join_pagewords.py [ID…] [--write]   # 고치기: tools/pageword_fixes.json 목록대로(미리 보기 / --write 로 적용)

목록 tools/pageword_fixes.json: {"DL-0020": [["124쪽", "125쪽", "노력", "과"], …]} — [앞 쪽 이름, 다음 쪽 이름, 앞 조각 낱말, 뒷조각 낱말].
본문을 도구(pdf2text_*.py 등)로 다시 만들면 이 도구를 다시 돌린다(이미 고친 곳은 건너뜀). 원서 대조가 있는 책은 고친 뒤
`python3 tools/parallel/shift.py <ID> <고치기 전 본문 JSON>` 로 짝 자료의 글자 자리를 맞춘다.
"""
import sys, os, re, json, glob, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(REPO, 'tools/pageword_fixes.json')
SKIP_START = ('[^', '![', '%%', '## ', '|', '>>', '::', '^^', '++', '**', '°°', '@@', '{{', '==', '§§')
MARK = r'\*\*|°°|@@|==|§§|\{\{|\}\}|\[\^[^\]]+\]'


def pages(body):
    ms = list(re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M))
    return [(m.group(1), m.end(), ms[i + 1].start() if i + 1 < len(ms) else len(body)) for i, m in enumerate(ms)]


def para_spans(body, st, en):
    """쪽 안 문단: [(시작, 끝)] (빈 줄로 나뉨, 원래 글 자리)"""
    out = []
    for m in re.finditer(r'(?:^[^\n]*\S[^\n]*(?:\n|$))+', body[st:en], flags=re.M):
        a, b = st + m.start(), st + m.end()
        while b > a and body[b - 1] in '\n ': b -= 1
        out.append((a, b))
    return out


def boundaries(body):
    """쪽 경계마다 (앞 쪽 이름, 다음 쪽 이름, 앞 문단 자리, 다음 문단 자리) — 앞 쪽의 마지막 본문 문단과 다음 쪽의 첫 문단"""
    P = pages(body)
    for i in range(len(P) - 1):
        ps = [s for s in para_spans(body, P[i][1], P[i][2]) if not body[s[0]:s[1]].lstrip().startswith(('[^', '![', '%%', '## ', '|'))]
        nx = para_spans(body, P[i + 1][1], P[i + 1][2])
        if not ps or not nx: continue
        yield P[i][0], P[i + 1][0], ps[-1], nx[0]


def toks(body, pa, na):
    a = body[pa[0]:pa[1]]; n = body[na[0]:na[1]]
    A = re.search(r'(\S+)$', a); B = re.match(r'(\S+)', n)
    return (A.group(1) if A else ''), (B.group(1) if B else ''), a, n


def scan(ids):
    from kiwipiepy import Kiwi
    k = Kiwi(); sc = lambda s: k.analyze(s)[0][1]
    od = os.path.join(REPO, 'tools/out/pagewords'); os.makedirs(od, exist_ok=True)
    for bid in ids:
        body = json.load(open(os.path.join(REPO, 'content/texts', bid + '.json')))['body']
        rows = []
        for pl, nl, pa, na in boundaries(body):
            A, B, a, n = toks(body, pa, na)
            if n.startswith(SKIP_START) or not re.search(r'[가-힣]$', A) or not re.match(r'[가-힣]', B): continue
            tail = re.sub(MARK, '', a.split('\n')[-1])[-20:]; head = re.sub(MARK, '', n.split('\n')[0])[:20]
            d = sc(tail + head) - sc(tail + ' ' + head)
            rows.append((round(d, 2), pl, nl, A, B, tail, head))
        with open(os.path.join(od, bid + '.tsv'), 'w') as f:
            f.write('점수(3 넘으면 붙은 낱말)\t앞 쪽\t다음 쪽\t앞 조각\t뒷조각\t앞 글\t다음 글\n')
            for r in sorted(rows, key=lambda r: -r[0]): f.write('\t'.join(map(str, r)) + '\n')
        print(bid, '쪽 경계에서 이어지는 한글', len(rows), '— 붙은 낱말로 보이는 곳(점수 3 넘음)', sum(1 for r in rows if r[0] > 3), '→', os.path.join(od, bid + '.tsv'))


def apply(ids, write):
    FX = json.load(open(FIX))
    for bid in ids:
        items = FX.get(bid, [])
        if not items: continue
        p = os.path.join(REPO, 'content/texts', bid + '.json'); s = open(p).read(); T = json.loads(s); body = T['body']
        todo = collections.Counter((pl, nl, A, B) for pl, nl, A, B in items)
        done = 0; back = 0; miss = []
        # 뒤에서부터 고쳐야 앞쪽 자리가 밀리지 않음
        bs = list(boundaries(body))[::-1]
        for pl, nl, pa, na in bs:
            A, B, a, n = toks(body, pa, na)
            key = (pl, nl, A, B)
            if todo[key] <= 0: continue
            todo[key] -= 1
            first = n.split('\n')[0]
            rest = n[len(B):]
            if rest.strip(' ') == '' or (first == B and '\n' not in n):
                # 뒷조각이 문단 전체 → 앞 조각을 다음 쪽 문단 앞으로
                if a.strip() == A: miss.append(key); continue
                cut = pa[1] - len(A)
                while cut > pa[0] and body[cut - 1] == ' ': cut -= 1
                odd = ''.join(mk for mk in ('**', '==') if A.count(mk) % 2 == 1)   # 굵게·색 표시가 홀수인 조각 → 앞 쪽에는 닫는 표시를 남기고 다음 쪽에서 다시 엶 (2026-11-19, 색 == 은 2026-11-20)
                body = body[:na[0]] + odd + A + body[na[0]:]
                body = body[:cut] + odd + body[pa[1]:]
                back += 1
            else:
                drop = len(B)
                if body[na[0] + drop:na[0] + drop + 1] == ' ': drop += 1
                elif body[na[0] + drop:na[0] + drop + 1] == '\n': drop += 1
                odd = ''.join(mk for mk in ('**', '==') if B.count(mk) % 2 == 1)   # 굵게·색 표시가 홀수인 조각 → 앞 쪽에서 닫고 다음 쪽에서 다시 엶 (2026-11-19, 색 == 은 2026-11-20)
                body = body[:na[0]] + odd + body[na[0] + drop:]
                body = body[:pa[1]] + B + odd + body[pa[1]:]
                done += 1
        body = body.replace('****', '')   # 굵게 낱말 두 조각을 붙이면 생기는 '**…앞****뒤…**' 는 하나로 (2026-11-19)
        body = re.sub(r'(?<=[^=\n])====(?=[^=\n])', '', body)   # 색 표시도 같게 '==…앞====뒤…==' → 하나로 (2026-11-20)
        left = [k for k, v in todo.items() if v > 0]
        already = [k for k in left if any(toks(body, pa, na)[0].endswith(k[2] + k[3]) or toks(body, pa, na)[1].startswith(k[2] + k[3]) for pl, nl, pa, na in boundaries(body) if (pl, nl) == k[:2])]
        left = [k for k in left if k not in already]
        print(bid, '뒷조각을 앞 쪽으로', done, '/ 앞 조각을 다음 쪽으로', back, ('/ 이미 고침 %d' % len(already)) if already else '', ('/ 못 찾음(본문이 바뀜 — 확인) %d' % len(left)) if left else '', ('/ 건너뜀 %d' % len(miss)) if miss else '')
        for k in left[:5]: print('   못 찾음:', k)
        # 글자 대조: 빈칸·줄바꿈 말고 같은지
        def norm(t):
            t = re.sub(r'^===.*===\s*$', '', t, flags=re.M)
            t = '\n\n'.join(x for x in re.split(r'\n\s*\n', t) if not x.strip().startswith('[^'))
            return re.sub(r'\s', '', t).replace('**', '').replace('==', '')   # 굵게·색 표시 자리만 바뀌는 것은 괜찮음
        if norm(body) != norm(T['body']): sys.exit(bid + ': 빈칸·쪽 표시·각주 말고 글자가 달라짐 — 멈춤')
        if write and body != T['body']:
            T['body'] = body
            open(p, 'w').write(json.dumps(T, ensure_ascii=False, indent=2 if '\n  "' in s else None) + ('\n' if s.endswith('\n') else ''))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    allids = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(REPO, 'content/texts/DL-*.json')))
    ids = args or allids
    if '--scan' in sys.argv: scan(ids)
    else: apply(ids, '--write' in sys.argv)
