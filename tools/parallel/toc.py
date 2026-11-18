"""원서 대조 — 차례 줄마다 짝 (운영자 요청, 2026-11-17)
한국어 차례(%% 문단)의 제목 줄 ↔ 원서 차례(orig k='toc') 항목을 쪽 번호는 빼고 제목끼리, 순서를 지키며 짝지음 → 묶음 하나(toc: 1).
  s[].ko = [[한국어 차례 문단 열쇠, 제목 시작 글자, 끝 글자]], s[].or = [[원서 차례 항목 번호, 0, 쪽 번호 앞 글자]], sc = 뜻 비슷함
  한국어 차례에 없는 원서 항목은 {ko: [], or: [...], after: [앞 한국어 줄]} — 화면에 원서만 한 줄
본문의 소제목 짝(본문 '## 팔정도' ↔ 원서 제목 The Noble Eightfold Path)이 있으면 그 줄끼리는 짝으로 봄 — LaBSE 는 '팔정도'·'좌선' 같은 짧은 낱말을 잘 못 알아봄.

이미 만든 짝 자료에 차례만 더하거나 다시 만들 때 (원서 PDF 없이):
  python3 tools/parallel/toc.py DL-0013 en
align.py 에 --toc 를 주면 짝짓기 끝에 이것을 함께 부름.
"""
import re, os, sys, json
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _paras(t): return ['\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]


def _plain(s):
    s = re.sub(r'\[\^[^\]]+\]', '', s)
    s = re.sub(r'^(## |\^\^ |:: |>> |\+\+ |\|\| |%% )', '', s, flags=re.M)
    return re.sub(r'\*\*|==|°°|§§|@@|\{\{|\}\}', '', s)


def _pages(body):
    body = body.replace('\r\n', '\n'); parts = re.split(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M)[1:]
    return [parts[i + 1] for i in range(0, len(parts), 2)]


def toc_group(body, orig, groups, enc, log=print, book=None):
    P = _pages(body)
    KT = []   # (열쇠, 시작, 끝, 제목)
    for n, txt in enumerate(P, 1):
        for si, para in enumerate(_paras(txt)):
            if not para.startswith('%%'): continue
            pos = 0
            for line in para.split('\n'):
                st = pos; pos += len(line) + 1
                m = re.match(r'^(%% )?(-*)\s*(.*?)(?:\s+\|\s*\S+)?\s*$', line)
                if not line.strip() or line.strip() == '~' or not m.group(3).strip(): continue
                KT.append((f'{n}:{si}', st + m.start(3), st + m.end(3), _plain(line[m.start(3):m.end(3)]).strip()))
    ET = []
    for i, p in enumerate(orig):
        if p['k'] != 'toc': continue
        m = re.match(r'^(.*?)(?:,?\s*[0-9ivxlc၀-၉]+)?\s*$', p['t'])   # ၀-၉: 미얀마 숫자 쪽 번호 (DL-0010)
        ET.append((i, 0, m.end(1), m.group(1)))
    if not KT or not ET: log('차례: 한국어 차례', len(KT), '원서 차례', len(ET), '— 짝지을 것 없음'); return None
    ET = [x for x in ET if not re.fullmatch(r'(Table of )?Contents', x[3].strip(), flags=re.I)]   # 원서 차례 쪽 자기 제목
    # 뜻 비교는 앞 번호('1.' '4)' 'I.' '●' '6 ')를 떼고
    core = lambda t: re.sub(r'^\s*(?:[●•]\s*)?(?:[0-9]+[.)]?|[၀-၉]+။|[IVXⅠ-Ⅻ]+\.)\s+', '', t).strip() or t
    TK, TE = enc([core(x[3]) for x in KT]), enc([core(x[3]) for x in ET]); TS = TK @ TE.T
    # 본문 소제목 짝으로 이어진 줄
    nz = lambda t: re.sub(r'[\W_]+', '', _plain(t).lower())
    para_t = {}
    for n, txt in enumerate(P, 1):
        for si, para in enumerate(_paras(txt)): para_t[f'{n}:{si}'] = para
    hl = {}
    for g in groups:
        if g.get('toc'): continue
        for st in g.get('s', []):
            kh = [para_t[k][a:b] for k, a, b in st['ko'] if para_t.get(k, '').startswith('## ')]
            eh = [orig[o]['t'][a:b] for o, a, b in st['or'] if orig[o]['k'] == 'h']
            for x in kh:
                for y in eh: hl.setdefault(nz(x), set()).add(nz(y))
    link = 0
    for i, x in enumerate(KT):
        for j, y in enumerate(ET):
            if nz(y[3]) in hl.get(nz(x[3]), ()): TS[i, j] = max(TS[i, j], 0.95); link += 1
    pins = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'toc_pins.json'))).get(book, []) if book else []
    for kp, ep in pins:   # 손으로 정한 짝(toc_pins.json)
        for i, x in enumerate(KT):
            for j, y in enumerate(ET):
                if _plain(x[3]).strip() == kp and y[3].strip() == ep: TS[i, :] = -1.0; TS[:, j] = -1.0; TS[i, j] = 1.0; log('  손으로 정한 짝:', kp, '↔', ep)
    TS[TS < 0.2] = -1.0      # 뜻이 거의 안 닮은 줄은 짝짓지 않음 (원서 'About the publisher' ↔ '다섯 행선지' 같은 것)
    # 순서를 지키는 1:1 짝짓기 (건너뛰기 −0.15)
    SKIP = -0.15; N, M = len(KT), len(ET); V = {(0, 0): 0.0}; B = {}
    for i in range(N + 1):
        for j in range(M + 1):
            if (i, j) == (0, 0): continue
            best = -1e18; bb = None
            for a, b in ((1, 1), (1, 0), (0, 1)):
                if (i - a, j - b) not in V: continue
                v = V[(i - a, j - b)] + (float(TS[i - 1, j - 1]) if a and b else SKIP)
                if v > best: best, bb = v, (a, b)
            V[(i, j)] = best; B[(i, j)] = bb
    i, j = N, M; tb = []
    while (i, j) != (0, 0):
        a, b = B[(i, j)]; tb.append((i - a, i, j - b, j)); i, j = i - a, j - b
    tb.reverse()
    ts = []; lastk = None
    for i0, i1, j0, j1 in tb:
        if i1 > i0 and j1 > j0: ts.append({'ko': [list(KT[i0][:3])], 'or': [list(ET[j0][:3])], 'sc': round(float(TS[i0, j0]), 3)})
        elif j1 > j0: ts.append({'ko': [], 'or': [list(ET[j0][:3])], **({'after': list(KT[lastk][:3])} if lastk is not None else {})})
        if i1 > i0: lastk = i0
    tkeys = sorted({x[0] for x in KT}, key=lambda k: tuple(map(int, k.split(':'))))
    sc = [x['sc'] for x in ts if 'sc' in x]
    log('차례 짝', len(sc), '/ 한국어 차례 줄', N, '원서 차례 항목', M, '(본문 제목 짝으로 이은 줄', link, ') 평균', round(float(np.mean(sc)), 3) if sc else '-')
    log('  한국어 차례에 없는 원서 항목:', [orig[x['or'][0][0]]['t'] for x in ts if not x['ko']] or '없음')
    KTD = {tuple(x[:3]): x[3] for x in KT}
    paired = {tuple(k) for x in ts for k in x['ko']}
    log('  원서 짝이 없는 한국어 줄:', [x[3] for x in KT if tuple(x[:3]) not in paired] or '없음')
    for x in ts:
        if x.get('sc', 1) < 0.55: log('  [차례 확인]', x['sc'], KTD[tuple(x['ko'][0])], '↔', orig[x['or'][0][0]]['t'])
    return {'ko': tkeys, 'or': sorted({o[0] for x in ts for o in x['or']}), 'ka': '차례', 'toc': 1, 's': ts}


def put_toc(groups, g):
    """차례 묶음을 바꿔 넣기 — 한국어 차례 첫 문단 자리 순서대로"""
    groups[:] = [x for x in groups if not x.get('toc')]
    if not g: return
    num = lambda k: tuple(map(int, k.split(':')))
    at = next((i for i, x in enumerate(groups) if x.get('ko') and not x.get('gl') and num(x['ko'][0]) > num(g['ko'][0])), len(groups))
    groups.insert(at, g)


if __name__ == '__main__':
    book, lang = sys.argv[1], sys.argv[2]
    pp = os.path.join(REPO, 'content/parallel', f'{book}.{lang}.json')
    D = json.load(open(pp)); body = json.load(open(os.path.join(REPO, 'content/texts', f'{book}.json')))['body']
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('sentence-transformers/LaBSE')
    enc = lambda xs: model.encode(xs, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    g = toc_group(body, D['orig'], D['groups'], enc, book=book)
    put_toc(D['groups'], g)
    json.dump(D, open(pp, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('→', pp)
