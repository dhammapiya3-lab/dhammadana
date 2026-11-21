#!/usr/bin/env python3
"""『위빠사나 명상』(DL-0012) 종이책 PDF → content/texts/DL-0012.json
  python3 tools/pdf2text_dl0012.py 책.pdf

인쇄된 줄의 위치·글꼴로 문단을 나눔 (글자는 PDF 그대로).
- 들여쓴 줄·줄 사이가 벌어진 줄은 새 문단, 꽉 찬 줄 다음 줄은 이어 붙임, 짧은 줄 다음 줄은 줄 바꿈(게송·목록)
- 큰 글씨(14pt 이상)는 '## ' 소제목, 굵은 글꼴(PB)은 **굵게**
- 위첨자 '1)' 은 [^1], 쪽 아래 각주 '1)　…' 은 그 쪽 끝 [^1]: …
- 그림(출판 허가서, 밴드 QR)은 잘라서 public/uploads 에
"""
import fitz, json, re, sys
pdf = sys.argv[1]; bk = 'DL-0012'
d = fitz.open(pdf)
toc_src = [l.rstrip('\n') for l in open(sys.argv[2] if len(sys.argv) > 2 else 'tools/toc_dl0012.txt', encoding='utf-8')]

IMGS = {3: [('permission', '#아신 자나까비왐사 사야도의 출판허가서')], 226: [('band-qr1', '#자애통찰명상원 밴드 초대 QR'), ('band-qr2', '#100일 아침명상 동참 초대 QR')]}
images = []


def crop(p, k, name):
    pg = d[p - 1]; info = pg.get_image_info()[k]; r = fitz.Rect(info['bbox'])
    pix = pg.get_pixmap(clip=r, dpi=300); path = f'public/uploads/{bk}-{name}.jpg'
    pix.save(path)
    url = '/' + path.replace('public/', ''); images.append(url)
    return r.y0, url


def is_sup(s, mx=10.5):
    return (s['size'] < 7.5 or s['size'] < mx * 0.75) and re.fullmatch(r'\s*\d+\)\s*', s['text'])


def line_text(l):
    out = []
    mx = max(s['size'] for s in l['spans'] if s['text'].strip())
    for s in l['spans']:
        t = s['text']
        if is_sup(s, mx):
            out.append(('[^%s]' % re.sub(r'\D', '', t), False)); continue
        bold = s['font'].endswith('PB') and s['size'] < 13 and not NOBOLD
        out.append((t, bold))
    # 굵게 묶기
    res, cur_b = '', False
    for t, b in out:
        if b and not cur_b and t.strip():
            lead = len(t) - len(t.lstrip()); res += t[:lead] + '**'; t = t[lead:]; cur_b = True
        elif not b and cur_b and t.strip():
            tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + (' ' * tail); cur_b = False
        res += t
    if cur_b:
        tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + (' ' * tail)
    return res


pages = []
NOBOLD = False
for pi, pg in enumerate(d):
    n = pi + 1
    NOBOLD = n == 2
    L = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans'])
            if not t.strip(): continue
            x0, y0, x1, y1 = l['bbox']
            if y0 > 495: continue  # 쪽 번호
            sz = max(s['size'] for s in l['spans'] if s['text'].strip())
            L.append(dict(x0=x0, x1=x1, y0=y0, y1=y1, sz=sz, t=line_text(l), raw=t,
                          head=sz >= 13.4, fn=(sz < 8.8 and sz > 8.2 and re.match(r'\s*\d+\)', t) is not None)))
    if 4 <= n <= 7:
        L.sort(key=lambda a: a['y0']); rows = []
        for a in L:
            if rows and abs(a['y0'] - rows[-1][0]['y0']) < 3: rows[-1].append(a)
            else: rows.append([a])
        paras, grp = [], []
        for r in rows:
            r.sort(key=lambda a: a['x0']); t = ' '.join(a['raw'].strip() for a in r)
            t = re.sub(r'\s+', ' ', t)
            if r[0]['sz'] >= 13:
                if grp: paras.append('\n'.join(grp)); grp = []
                paras.append(('## ' if r[0]['sz'] > 15 else '') + t)
            else: grp.append(t)
        if grp: paras.append('\n'.join(grp))
        pages.append((n, paras)); continue
    L.sort(key=lambda a: (round(a['y0']), a['x0']))
    # 같은 높이의 줄(탭으로 떨어진 조각)은 하나로
    M = []
    for a in L:
        if M and abs(a['y0'] - M[-1]['y0']) < 2 and not a['head']:
            M[-1]['t'] += ' ' + a['t'].strip(); M[-1]['x1'] = a['x1']; continue
        M.append(a)
    L = M
    # 각주: 첫 각주 줄부터 아래는 각주 (작은 글씨)
    fstart = next((i for i, a in enumerate(L) if a['fn']), None)
    body, foot = (L, []) if fstart is None else (L[:fstart], L[fstart:])
    imgs = []
    for k, (name, alt) in enumerate(IMGS.get(n, [])):
        y, url = crop(n, k, name); imgs.append((y, f'![{alt}]({url})'))
    left, right = (79, 321) if n % 2 else (62, 304)  # 홀수·짝수 쪽 글 상자
    GS = {}
    for a, b in zip(body, body[1:]):
        if not a['head'] and not b['head'] and abs(a['sz'] - b['sz']) < .3: GS.setdefault(round(a['sz']), []).append(b['y0'] - a['y1'])
    MED = {k: sorted(v)[len(v) // 4] for k, v in GS.items()}
    paras, cur, prev = [], None, None
    for a in body:
        while imgs and imgs[0][0] < a['y0']:
            if cur: paras.append(cur); cur = None
            paras.append(imgs.pop(0)[1]); prev = None
        t = a['t']
        if a['head']:
            if cur and cur.startswith('## ') and prev is not None and prev['head'] and a['y0'] - prev['y1'] < 12:
                cur = cur.rstrip() + ' ' + t.strip().replace('**', '')
            else:
                if cur: paras.append(cur)
                cur = '## ' + t.strip().replace('**', '')
            prev = a; continue
        if cur is None or prev is None or prev['head']:
            if cur: paras.append(cur)
            cur = t.rstrip() if False else t; prev = a; continue
        gap = a['y0'] - prev['y1']
        lh = max(4.0, prev['y1'] - prev['y0'])
        lead = re.match(r' {2,}\S', a['raw']) is not None
        plead = re.match(r' {2,}\S', prev['raw']) is not None
        indent = lead or (a['x0'] - prev['x0'] > 4.5 and not plead)
        if n == 2 and re.match(r'(AN|Dhp|DN|MN|Paṭis|SN|Vism)\s', a['raw'].strip()) and not a['raw'].startswith('    '):
            indent = False; cur = cur.rstrip() + '\n' + t; prev = a; continue
        if n == 2 and a['raw'].startswith('    '): indent = False
        if n == 228 and gap <= lh * 0.9:  # 판권지는 인쇄된 줄 그대로
            cur = cur.rstrip() + '\n' + t; prev = a; continue
        short = prev['x1'] < right - 18
        pb = prev['t'].strip().startswith('**') and prev['t'].strip().endswith('**'); cb = t.strip().startswith('**') and t.strip().endswith('**')
        if gap > lh * 0.9 or (gap > MED.get(round(a['sz']), 99) + 4.5 and abs(a['sz'] - prev['sz']) < .3) or (abs(a['sz'] - prev['sz']) > .5) or (indent and n != 2) or (n == 2 and lead and not a['raw'].startswith('    ') and not re.match(r'\s*(AN|Dhp|DN|MN|Paṭis|SN|Vism)\s', a['raw'])):
            paras.append(cur); cur = t
        elif short or (n == 2 and lead and not a['raw'].startswith('    ')) or pb != cb or re.match(r'\s*(\d+\.\s|\(\d+\)|[①-⑳])', a['raw']):
            cur = cur.rstrip() + '\n' + t
        else:
            cur = cur + t
        prev = a
    if cur: paras.append(cur)
    for _, im in imgs: paras.append(im)
    if n == 2:  # 약어: 약어 하나가 한 줄 (인쇄본에서 줄이 넘어간 것은 이어 붙임)
        paras, cur = ['## 약어'], ''
        for a_ in body[1:]:
            r = a_['raw']
            if re.match(r'\s*(AN|Dhp|DN|MN|Paṭis|SN|Vism)\s', r): cur = cur.rstrip() + '\n' + r.lstrip()
            elif re.match(r' {2}\S', r) or r.startswith('CPD'): paras.append(cur); cur = r.lstrip()
            elif cur.rstrip().endswith(':'): cur = cur.rstrip() + '\n' + r.lstrip()
            else: cur = cur + (' ' if cur.endswith(('，',)) else '') + r.lstrip()
        paras.append(cur); paras = [p for p in paras if p.strip()]
    if n == 8:  # 예경문: 가운데 맞춤, 인쇄된 묶음·줄 그대로
        ls = [x['raw'].strip() for x in body]
        paras = [':: ' + '\n'.join(ls[0:2]), ':: ' + '\n'.join(ls[2:4]), ':: ' + '\n'.join(ls[4:])]
    if n == 1:  # 속표지: 제목은 크게·가운데, 나머지는 가운데 (인쇄된 줄 그대로)
        ls = [a['raw'].strip() for a in body]
        paras = ['^^ ' + ls[0] + '\n' + ls[1], ':: ' + '\n'.join(ls[2:4]), ':: ' + '\n'.join(ls[4:6]), ':: ' + ls[6], ':: ' + ls[7], ':: ' + ls[8], ':: ' + '\n'.join(ls[9:])]
    # 각주
    fns, fc = [], None
    for a in foot:
        m = re.match(r'\s*(\d+)\)[　 ]?(.*)', a['t'])
        if m and a['fn']:
            if fc: fns.append(fc)
            fc = f'[^{m.group(1)}]: ' + m.group(2)
        elif fc is not None and a['sz'] < 9:
            fc = (fc.rstrip() + '\n' + a['t'].strip()) if re.match(r' {2,}\S', a['raw']) else fc + a['t']
        else:  # 각주 아래에 다시 본문 크기 글
            if fc: fns.append(fc); fc = None
            paras.append(a['t'])
    if fc: fns.append(fc)
    clean = lambda s: re.sub(r'[ \t ]+\n', '\n', re.sub(r'[ \t ]{2,}', ' ', s)).strip()
    pages.append((n, [clean(p) for p in paras + fns if clean(p)]))

body = ''.join(f'=== {n}쪽 ===\n' + '\n\n'.join(ps) + '\n\n' for n, ps in pages).rstrip() + '\n'
body = re.sub(r'\*\*( ?)\*\*', r'\1', body)  # 같은 줄에서만 (줄·문단을 넘는 굵게는 화면에서 깨짐)
# 서문·일러두기 끝의 서명: 인쇄된 줄 그대로 한 묶음으로
body = body.replace('![#자애통찰명상원 밴드 초대 QR](/uploads/DL-0012-band-qr1.jpg)\n\n![#100일 아침명상 동참 초대 QR](/uploads/DL-0012-band-qr2.jpg)\n\n자애통찰명상원 밴드 초대코드 100일 아침명상 동참 초대코드\n\n', '![자애통찰명상원 밴드 초대코드](/uploads/DL-0012-band-qr1.jpg)\n\n![100일 아침명상 동참 초대코드](/uploads/DL-0012-band-qr2.jpg)\n\n')  # QR 두 개: 인쇄된 설명을 그림 밑에, 화면에서 나란히
body = body.replace('**수지와 스님(Venerable Sujīva)**\n\n**1985년 6월**', '**수지와 스님(Venerable Sujīva)**\n**1985년 6월**')
body = body.replace('**1992년 11월 2일아신 자나까비왐사**\n\n**찬매 사야도**', '**1992년 11월 2일**\n**아신 자나까비왐사**\n**찬매 사야도**')  # 이어진 굵은 글은 하나로
body = body.replace('\n\n**아신 자나까비왐사 사야도의 출판허가서**\n\n', '\n\n:: **아신 자나까비왐사 사야도의 출판허가서**\n\n')  # 가운데 (운영자 요청)
# 목차 항목이 쪽 중간에서 시작하면 at
nz = lambda x: re.sub(r'[^0-9A-Za-z가-힣]', '', x)
PG = {int(m.group(1)): m.group(2) for m in re.finditer(r'=== (\d+)쪽 ===\n(.*?)(?=\n=== |\Z)', body, re.S)}
# 목차
toc = []
for l in toc_src:
    if not l.strip(): continue
    sub = l.startswith('  '); title, pg = l.strip().rsplit('\t', 1)
    e = {'title': title, 'page': int(pg), 'sub': sub}
    for q in range(int(pg), int(pg) + 3):
        ps = [p for p in PG.get(q, '').split('\n\n') if p.strip()]
        k = next((i for i, p in enumerate(ps) if p.startswith('## ') and nz(p).startswith(nz(title)[:8])), None)
        if k is not None:
            if q != int(pg): print('목차 쪽 옮김:', title, pg, '→', q); e['page'] = q
            break
    if k is None: print('목차 제목을 쪽에서 못 찾음:', title, pg)
    elif k > 0: e['at'] = ps[k][3:13]
    toc.append(e)
json.dump({'book': bk, 'edition': '초판', 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '쪽', len(toc), '목차', len(images), '그림')
