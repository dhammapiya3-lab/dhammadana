"""『빠릿따 독송예경문』(DL-0032, 담마다야다 빅쿠 편역, 초기불교 세나니승원) PDF → content/texts/DL-0032.json
  python3 tools/pdf2text_dl0032.py 책.pdf     (다음에 python3 tools/split_chapters.py --write)

- 한글 파일을 'Microsoft: Print To PDF' 로 내보낸 PDF 375쪽. PDF 쪽 = 인쇄 쪽 + 3 (쪽 아래 '- N -').
  1쪽 속표지, 2~3쪽 차례는 쪽 번호가 없음.
- 글자는 rawdict 의 글자 자리로 줄을 다시 세움(글자층 순서가 뒤섞여 있음). 굵게 덧그린 글자(texttrace type 1)는 **…**.
- 독송 묶음: 소리 줄(굵게 15pt) + 로마자 줄(10.3pt) = 한 문단(줄은 인쇄본 그대로), 번역 줄(14.6pt)은 다음 문단.
  줄 사이가 28pt 넘게 벌어지면 새 문단.
- 산문(일러두기·보호경이 설해진 배경·마음 부수·미주): 끝까지 찬 줄은 이어 붙이고(줄 끝 빈칸이 있으면 빈칸),
  들여 쓴 줄·번호 줄('1)'·'1.'·'①'·'Ⅰ.'·'▣')에서 새 줄.
- 각주 번호(8.8~9.5pt, 줄 위에 작게)는 글자 자리에 [^n]. 미주(303쪽~)는 [^n]: 풀이 — 한 미주 안의 들여 쓴 줄은 줄 바꿈으로.
  294쪽 쪽 아래 각주 1)·2)(마음 부수)는 미주 번호와 겹치므로 [^*1]·[^*2].
- 제목: 23.4·21·15.5pt → '## ', 제목 아래 빠알리 제목(12.6pt) → ':: ', 대념처경 편 제목(13.6pt)·필수품(14pt '1. 가사…')·
  '▣'·'Ⅱ.' → '## '. 가운데로 들여 쓴 짧은 줄(앞 빈칸 8개 넘게) → ':: '. 글꼴 안 '' → '…'.
- 2~3쪽 빠알리 발음 표는 그림(DL-0032-p002·p003-table.png), 1쪽 아소카 사자상 그림.
"""
import sys, re, json, os, collections
import pymupdf

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pymupdf.open(pdf)
OFF = 3
RIGHT = 476
MAP = {'': '…'}


def page_lines(p):
    stroke = set()
    for sp in p.get_texttrace():
        if sp['type'] == 1:
            for (u, g, org, bb) in sp['chars']: stroke.add((round(org[0]), round(org[1])))
    ch = []
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                for c in s['chars']:
                    o = c['origin']
                    ch.append(dict(y=round(o[1], 1), x=o[0], x1=c['bbox'][2], c=MAP.get(c['c'], c['c']), f=s['font'], sz=round(s['size'], 1), col=s['color'],
                                   b=(round(o[0]), round(o[1])) in stroke))
    ch.sort(key=lambda c: (c['y'], c['x']))
    rows = []
    for c in ch:
        if rows and abs(c['y'] - rows[-1][-1]['y']) <= 2.0: rows[-1].append(c)
        else: rows.append([c])
    out = []
    for r in rows:
        r.sort(key=lambda c: c['x'])
        vis = [c for c in r if c['c'].strip()]
        if not vis: continue
        f = collections.Counter((c['f'], c['sz'], c['col']) for c in vis).most_common(1)[0][0]
        out.append(dict(y=r[0]['y'], x=r[0]['x'], x1=max(c['x1'] for c in r), ch=r, f=f, sz=f[1], t=''.join(c['c'] for c in r)))
    return out


def text_of(ch, refs=(), bold=True):
    """글자들 → 글. 굵은 덩어리는 **…**, 각주 번호는 자리에 [^n]"""
    ins = sorted(refs, key=lambda r: r[0])
    s = ''; inb = False; k = 0
    for i, c in enumerate(ch):
        while k < len(ins) and ins[k][0] <= c['x'] + 0.5:
            if inb: s = s.rstrip(); s += '**'; inb = False
            s += f'[^{ins[k][1]}]'; k += 1
        b = bold and c['b'] and c['c'].strip() != ''
        if b and not inb: s += '**'; inb = True
        elif not b and inb and c['c'].strip(): s = s.rstrip() + '**' + (' ' if s.endswith(' ') else ''); inb = False
        s += c['c']
    if inb: s = s.rstrip() + '**'
    while k < len(ins): s = s.rstrip() + f'[^{ins[k][1]}]'; k += 1
    s = re.sub(r'\*\*(\s*)\*\*', r'\1', s)
    s = re.sub(r'\*\*([\s.,·:;!?()\-]*)\*\*', r'\1', s)       # 문장부호만 굵은 덩어리는 풀기
    return s


def bratio(l):
    v = [c for c in l['ch'] if c['c'].strip()]
    return sum(c['b'] for c in v) / max(1, len(v))


def kind(l, pn=0):
    f, sz, col = l['f']
    t = l['t'].strip(); lead = len(l['t']) - len(l['t'].lstrip(' '))
    if re.fullmatch(r'-\s*\d+\s*-', t): return 'foot'
    if sz in (23.4, 21.0) or (sz == 15.5 and f.endswith('F6')) or t == '끝맺음': return 'head'
    # 굵은 소제목: 필수품·대념처경 편·'서언'·'연기 분석'·보호경 배경의 경 이름·'▣'·'Ⅱ.' (마음 부수 장의 굵은 줄은 제목 아닌 굵은 글)
    if t.startswith('⚜'): return 'head2'
    if re.match(r'(\d+\.|\d+\)|\(\d+\)|▣|Ⅱ\.|서언|연기 분석|바자니야)', t) and bratio(l) >= 0.6 and sz >= 12.0 and sz != 15.0 and l['x'] < 92 and lead < 8 and not t.startswith('-') and not re.fullmatch(r'\d+\.', t) \
            and (pn < 289 + 3 or sz >= 13.0): return 'head2'
    if bratio(l) >= 0.6 and sz in (13.6, 14.0) and l['x'] < 92 and lead < 8 and not t.startswith('-'): return 'head2c'
    if f.endswith('F10'): return 'ptitle'
    if f.endswith('F8') or (sz == 10.6 and re.search(r'[a-zāīūṁṃñ]{3}', t) and not re.search(r'[가-힣]', t)): return 'roman'
    if sz in (15.0, 15.5): return 'pron'
    if sz in (14.6, 14.2, 14.0, 13.6, 13.0, 12.6) and pn < 289 + 3: return 'tr'
    return 'prose'


def build():
    pages = []          # (label, [para])
    notes_mode = False
    allrefs = []
    for i in range(d.page_count):
        pn = i + 1
        L = page_lines(d[i])
        lab = ''
        for l in L:
            if kind(l, pn) == 'foot' and l['y'] > 700: lab = re.sub(r'\D', '', l['t'])
        if pn > 3 and lab and int(lab) != pn - OFF: print('! 쪽 번호', pn, lab)
        lab = f'{lab}쪽' if lab else ''
        # 각주 번호 줄 → 아래 줄 글자 자리에
        refs = collections.defaultdict(list); body = []
        for l in L:
            if l['sz'] <= 9.6 and re.fullmatch(r'(\s*\d+\)\s*)+', l['t']):
                tgt = sorted([m for m in L if m is not l and 0 < m['y'] - l['y'] <= 10 and m['sz'] > 9.6], key=lambda m: m['y'])
                if tgt:
                    grp = []; cur = None
                    for c in l['ch']:
                        if c['c'].isdigit():
                            if cur is None: cur = [c['x'], '']
                            cur[1] += c['c']
                        elif c['c'] == ')' and cur: grp.append(tuple(cur)); cur = None
                    for x, n in grp:
                        if pn == 297: n = '*' + n
                        refs[id(tgt[0])].append((x, n)); allrefs.append(n)
                    continue
            if kind(l, pn) == 'foot': continue
            body.append(l)
        if pn == 1:
            pages.append(('', ['^^ 빠릿따 독송예경문', '![#아소카 석주 사자상](/uploads/DL-0032-lion.png)', ':: 초기불교 세나니승원', ':: 파욱 국제승원 한국분원'])); continue
        if pn in (2, 3):
            pages.append(('', toc_block(body) if pn == 2 else None)); continue
        if pn in (5, 6):
            first = text_of(body[0]['ch']).strip() if pn == 5 else ''
            ps = []
            if first: ps.append(first.replace('빠알리 발음: ', '## 빠알리 발음\n\n', 1) if False else first)
            ps.append(f'![#빠알리 발음 표](/uploads/DL-0032-p00{pn - 3}-table.png)')
            pages.append((lab, ps)); continue
        ps = []; prev = None; pk = None
        for l in body:
            k = kind(l, pn)
            if l['t'].strip() == '미주' and pn >= 300: notes_mode = True; ps.append('## 미주'); prev = l; pk = 'head'; continue
            t = text_of(l['ch'], refs.get(id(l), []), bold=k not in ('head', 'head2', 'head2c'))
            lead = len(t) - len(t.lstrip(' '))
            t0 = t.strip()
            if not t0: continue
            if pn == 297 and l['sz'] == 9.0 and re.match(r'\d+\)', t0):   # 294쪽 아래 각주 (미주 번호와 겹쳐 *1·*2)
                m = re.match(r'(\d+)\)\s*', t0); ps.append(f'[^*{m.group(1)}]: ' + t0[m.end():]); prev = l; pk = 'fn'; continue
            if notes_mode:
                m = re.match(r'(\d+)\)\s*', t0)
                if m and l['x'] < 72:
                    ps.append(f'[^{m.group(1)}]: ' + t0[m.end():]); prev = l; pk = 'note'; continue
                if pk == 'note' and ps:
                    if l['x'] < 72 and lead >= 3: ps[-1] += '\n' + t0
                    else: ps[-1] = joinp(ps[-1], prev, t0)
                    prev = l; continue
            if k == 'head':
                if ps and pk == 'head' and l['y'] - prev['y'] < 40 and l['sz'] == prev['sz']: ps[-1] += ' ' + t0
                else: ps.append('## ' + t0)
                prev = l; pk = 'head'; continue
            if k == 'head2c':
                if pk == 'head2' and l['y'] - prev['y'] < 45: ps[-1] += ' ' + t0; prev = l; continue
                k = 'tr'
            if k == 'head2':
                if ps and pk == 'head2' and l['y'] - prev['y'] < 30 and not re.match(r'(\d+\.|\d+\)|\(\d+\)|▣|바자니야)', t0): ps[-1] += ' ' + t0
                else: ps.append('## ' + t0.lstrip('⚜'))
                prev = l; pk = 'head2'; continue
            if k == 'ptitle':
                ps.append(':: ' + t0); prev = l; pk = 'ptitle'; continue
            if lead >= 8 and l['x1'] < RIGHT - 30 and k in ('tr', 'prose', 'roman'):
                ps.append(':: ' + t0); prev = l; pk = 'center'; continue
            chant = k in ('pron', 'roman', 'tr')
            gap = l['y'] - prev['y'] if prev is not None else 999
            if chant:
                same = prev is not None and pk in ('pron', 'roman', 'tr') and gap <= 28 and not (pk == 'roman' and k == 'tr') and not (pk == 'tr' and k == 'pron')
                if same: ps[-1] += '\n' + t0
                else: ps.append(t0)
            else:
                numstart = re.match(r'(\d+\)|\d+\.|\(\d+\)|[①-⑳]|[ⅠⅡⅢⅣ]\.|▣|\d+-\d+\.)\s', t0)
                cont = prev is not None and pk == 'prose' and gap <= 24 and not numstart and lead < 3 and prev['x1'] >= RIGHT - 30
                if cont: ps[-1] = joinp(ps[-1], prev, t0)
                # ①② 를 글 속에 이어 쓴 풀이(미주 등): 앞 줄이 끝까지 찼으면 줄이 넘어간 것 — 이어 붙임
                elif numstart and re.match(r'[①-⑳]', t0) and prev is not None and pk == 'prose' and gap <= 19 and lead < 3 and prev['x1'] >= RIGHT - 30: ps[-1] = joinp(ps[-1], prev, t0)
                elif prev is not None and pk == 'prose' and gap <= 24 and not numstart and lead < 3: ps[-1] += '\n' + t0
                # 번호 항목이 앞 줄과 간격 없이 이어 인쇄된 곳(마음 부수·일러두기 목록)은 줄만 바꿈 — 인쇄본 줄 간격 그대로 (운영자 요청, 2026-11-16)
                elif numstart and prev is not None and pk == 'prose' and gap <= 19 and lead < 3 and ps and not re.fullmatch(r'\*\*[^*]+\*\*', ps[-1].split('\n')[-1]): ps[-1] += '\n' + t0
                else: ps.append(t0)
            prev = l; pk = 'prose' if not chant else k
        pages.append((lab, ps))
    return pages, allrefs


def joinp(acc, prevl, t):
    pt = prevl['t']
    return acc + (' ' if pt.endswith(' ') or re.search(r'[.,?!:;]$', acc) else '') + t if not acc.endswith(' ') else acc + t


TOCX = []


def toc_block(body):
    return []


def make_toc_pages():
    """2~3쪽 차례 → %% 차례 한 덩어리 (들여쓰기는 인쇄된 자리: 75 이하 장, 80 '-', 95 '--', 110 '---')"""
    rows = []
    for i in (1, 2):
        for l in page_lines(d[i]):
            t = l['t'].strip()
            if not t or t in ('차례', 'Contents'): continue
            m = re.match(r'^(.*?)[\s·]*·{3,}\s*(\d+)\s*$', t)
            if not m: continue
            title = re.sub(r'\s+', ' ', m.group(1)).strip()
            x = l['x'] + (len(l['t']) - len(l['t'].lstrip())) * 3
            lev = 0 if l['x'] < 78 else 1 if l['x'] < 90 else 2 if l['x'] < 105 else 3
            if title in ('끝맺음', '연기 분석'): lev = 0
            rows.append((lev, title, m.group(2), l['y'], i))
    out = []; py = None; pi = None
    for lev, title, n, y, i in rows:
        if py is not None and pi == i and y - py > 30: out.append('~')
        out.append(('-' * lev + ' ' if lev else '') + f'{title} | {n}')
        py, pi = y, i
    return '%% ' + '\n'.join(out), rows


def save_pics():
    p = d[0]
    for im in p.get_image_info():
        r = pymupdf.Rect(im['bbox'])
        if r.width > 50: p.get_pixmap(dpi=300, clip=r).save(os.path.join(REPO, 'public/uploads/DL-0032-lion.png'))
    for pn in (5, 6):
        pg = d[pn - 1]; box = pymupdf.Rect(40, 60, 520, 700)
        dr = [x['rect'] for x in pg.get_drawings() if box.x0 <= x['rect'].x0 and x['rect'].x1 <= box.x1 and box.y0 <= x['rect'].y0 and x['rect'].y1 <= box.y1]   # 쪽 귀퉁이 재단 표시는 빼고
        r = pymupdf.Rect(min(x.x0 for x in dr), min(x.y0 for x in dr), max(x.x1 for x in dr), max(x.y1 for x in dr))   # 선은 넓이가 없어 | 로 합칠 수 없음
        r = r + (-4, -4, 4, 4)
        pg.get_pixmap(dpi=200, clip=r).save(os.path.join(REPO, f'public/uploads/DL-0032-p00{pn - 3}-table.png'))


if __name__ == '__main__':
    pages, allrefs = build()
    tocb, rows = make_toc_pages()
    pages[1] = ('', ['## 차례', tocb]); pages[2] = None
    pages = [x for x in pages if x is not None]
    save_pics()
    # 읽기 목차: 인쇄된 차례 + 속표지·차례·법보시 공덕·판권지
    lab2idx = {lab: k + 1 for k, (lab, ps) in enumerate(pages) if lab}
    norm = lambda s: re.sub(r'[\s*·()]', '', s)
    toc = [{'title': '속표지', 'page': 1, 'sub': False}, {'title': '차례', 'page': 2, 'sub': False}]
    extra = [('법보시 공덕', 300), ('판권지', 302)]
    items = [(lev, t, int(n)) for lev, t, n, y, i in rows] + [(0, t, n) for t, n in extra]
    items.sort(key=lambda x: x[2])
    for lev, t, n in items:
        k = lab2idx.get(f'{n}쪽')
        if not k: print('! 쪽 없음', t, n); continue
        e = {'title': ('  ' * lev + t) if lev else t, 'page': k, 'sub': bool(lev)}
        hit = None
        for kk in (k, k + 1):
            ps = pages[kk - 1][1]
            hit = next((p for p in ps if p.startswith('## ') and norm(p[3:]).startswith(norm(t)[:10])), None)
            if hit: k = kk; e['page'] = k; break
        ps = pages[k - 1][1]
        if hit and ps.index(hit) > 0: e['at'] = hit[3:][:24]
        elif not hit and t not in ('판권지',) and not (ps and ps[0].startswith('## ')): print('  ? 제목 못 찾음', t, n)
        toc.append(e)
    body = '\n\n'.join(f'=== {lab} ===\n' + '\n\n'.join(ps) for lab, ps in pages)
    defs = set(re.findall(r'(?m)^\[\^([^\]]+)\]:', body)); used = set(re.findall(r'\[\^([^\]]+)\](?!:)', body))
    print('각주 번호', len(used), '미주', len(defs), '풀이 없음', sorted(used - defs, key=lambda x: (len(x), x))[:10], '번호 없음', sorted(defs - used, key=lambda x: (len(x), x))[:10])
    out = {'book': 'DL-0032', 'edition': '개정판', 'toc': toc, 'images': ['/uploads/DL-0032-lion.png', '/uploads/DL-0032-p002-table.png', '/uploads/DL-0032-p003-table.png'], 'body': body}
    json.dump(out, open(os.path.join(REPO, 'content/texts/DL-0032.json'), 'w'), ensure_ascii=False, indent=1)
    print('쪽', len(pages), '목차', len(toc), '글자', len(body))
