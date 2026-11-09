#!/usr/bin/env python3
"""『사성제로 정리한 숫따니빠따』(DL-0016) 종이책 PDF → content/texts/DL-0016.json
  python3 tools/pdf2text_dl0016.py 책.pdf tools/toc_dl0016.txt

PDF 1쪽(앞표지)·394쪽(뒤표지)은 빼고 2~393쪽을 씀 → 인쇄된 쪽 번호 = PDF 쪽 - 1.
글자는 PDF 그대로 (화면에 안 보이는 조판 기호만 뺌, Wingdings 글머리 기호는 •).
- 이 책은 들여쓰기가 없고, 줄 사이가 벌어지면 새 문단(게송 묶음 등)
- 꽉 찬 줄 다음은 이어 붙이고, 짧은 줄로 끝나면 문단 끝. 짧은 줄이 이어지면(게송·목록) 줄 바꿈
- (61)·①·1)·⊙·•·[ 로 시작하는 줄은 새 문단
- SunBatang·ShinmunBatang 굵은 제목 줄은 '## ', 굵은 명조(cBd) 줄은 **굵게**, 오른쪽 맞춤 출전(SN56:11 …)은 '>> '
- 그림: 예경문 쪽의 부처님 사진(인쇄본 2~3쪽에 걸침)
"""
import fitz, json, re, sys
from PIL import Image
pdf, tocf = sys.argv[1], sys.argv[2]
bk, ED = 'DL-0016', '초판'
src = fitz.open(pdf)
OFF = 1
N = 392
images = []
INVIS = re.compile('[\x07­]')
BOLD = re.compile(r'(cBd|Bold|PB)')
HEADF = re.compile(r'(SunBatang|Shinmun|Gothic|SDGothic|Neoa)')


def norm_text(t):
    return INVIS.sub('', t).replace('', '•').replace('\t', ' ')


def spans_of(l):
    return [s for s in l['spans'] if s['text'].strip()]


def main_size(l):
    ss = spans_of(l)
    return max((s['size'] for s in ss), default=0)


def line_text(l, head=False):
    out = []
    for s in l['spans']:
        t = norm_text(s['text'])
        if not t: continue
        b = bool(BOLD.search(s['font'])) and not head and s['size'] >= 8.5 and 'Wingdings' not in s['font']
        if not re.search('[가-힣A-Za-z0-9]', t) and out: b = out[-1][1]
        out.append((t, b))
    res, cb = '', False
    for t, b in out:
        if b and not cb and t.strip():
            lead = len(t) - len(t.lstrip()); res += t[:lead] + '**'; t = t[lead:]; cb = True
        elif not b and cb and t.strip():
            tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + ' ' * tail; cb = False
        res += t
    if cb:
        tail = len(res) - len(res.rstrip()); res = res.rstrip() + '**' + ' ' * tail
    return res


def is_head(l):
    ss = [s for s in spans_of(l) if re.search('[가-힣A-Za-z]', s['text'])]
    if not ss: return False
    if re.match(r'\s*[☞•⊙\uf09f]', ''.join(x['text'] for x in spans_of(l))): return False
    return all(HEADF.search(s['font']) for s in ss if s['size'] >= 9.6) and any(HEADF.search(s['font']) for s in ss)


def lines_of(n):
    pg = src[n - 1 + OFF]
    L = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            raw = norm_text(''.join(s['text'] for s in l['spans']))
            if not raw.strip(): continue
            x0, y0, x1, y1 = l['bbox']
            if y0 > 585: continue  # 쪽 번호·머리글
            L.append(dict(l=l, x0=x0, y0=y0, x1=x1, y1=y1, sz=main_size(l), raw=raw, own=raw, head=is_head(l),
                          bold=all(BOLD.search(s['font']) or 'Wingdings' in s['font'] for s in spans_of(l))))
    L.sort(key=lambda a: (round(a['y0']), a['x0']))
    M = []
    for a in L:
        if M and abs(a['y0'] - M[-1]['y0']) < 2:
            M[-1]['parts'].append(a); M[-1]['x1'] = a['x1']; M[-1]['raw'] += a['raw']; continue
        a['parts'] = [a]; M.append(a)
    for a in M:
        a['t'] = ''.join(line_text(p['l'], head=a['head']) for p in a['parts'])
    return M


def geom(n):
    return (70.9, 379.7) if (n + OFF) % 2 == 0 else (53.9, 362.7)


MARK = re.compile(r'\s*(\d+\.\s|\(\d+\)|[①-⑳➀-➓]|\d+\)|⊙|•|\[|\*|☞|-\s|■)')
clean = lambda s: re.sub(r'[ \t ]+\n', '\n', re.sub(r'(?<=\S)[ \t ]{2,}', ' ', s)).strip()


def body_paras(n, body):
    left, right = geom(n)
    paras, cur, prev, verse, hang = [], None, None, False, None
    for a in body:
        t = a['t']
        if a['head']:
            if cur and cur.startswith('## ') and prev is not None and prev['head'] and a['y0'] - prev['y1'] < 20:
                cur = cur.rstrip() + ' ' + t.replace('**', '').strip()
            else:
                if cur: paras.append(cur)
                cur = '## ' + t.replace('**', '').strip()
            prev = a; continue
        if a['x0'] > left + 60 and a['x1'] > right - 8 and a['sz'] < 10.5:
            if cur: paras.append(cur)
            paras.append('>> ' + t.strip()); cur = None; prev = None; continue
        if cur is None or prev is None or prev['head'] or cur.startswith('>> '):
            if cur: paras.append(cur)
            cur = t; verse = False; hang = None; prev = a; continue
        gap = a['y0'] - prev['y1']
        lh = max(8.0, prev['y1'] - prev['y0'])
        pshort = prev['x1'] < right - 14
        short = a['x1'] < right - 14
        mark = MARK.match(a['raw']) is not None
        first = cur.split('\n')[-1]
        if hang is None and not pshort and MARK.match(prev['raw'].replace('**', '')) and a['x0'] > prev['x0'] + 3:
            hang = a['x0']  # 글머리 문단의 둘째 줄(내어쓰기)
        if hang is None and re.match(r' {2,}\S', prev['raw']) and a['x0'] > prev['x0'] + 3 and not pshort and not mark:
            hang = a['x0']  # 빈칸으로 들여 짠 줄의 다음 줄(같은 들여쓰기 자리에서 이어짐)
        if hang is not None and abs(a['x0'] - hang) < 2 and not mark and gap <= lh * 1.2:
            cur = (cur.rstrip() + '\n' + t) if pshort else cur + t
        elif gap > lh * 1.2 or (abs(a['sz'] - prev['sz']) > .8 and pshort) or mark or a['bold'] != prev['bold'] or abs(a['x0'] - prev['x0']) > 6:
            paras.append(cur); cur = t; verse = False; hang = None
        elif pshort:
            if verse or short or len(cur.split('\n')) == 1 and len(cur) < 60:
                cur = cur.rstrip() + '\n' + t; verse = True  # 게송·목록: 인쇄된 줄 그대로
            else:
                paras.append(cur); cur = t; verse = False  # 산문 문단 끝
        else:
            cur = cur + t
        prev = a
    if cur: paras.append(cur)
    return paras


pages = []
for n in range(1, N + 1):
    body = lines_of(n)
    pages.append([n, body_paras(n, body)])
P = {p[0]: p for p in pages}


def rows(n):
    return lines_of(n)


def plain(a):
    return re.sub(r'\s+', ' ', ' '.join(p['own'].strip() for p in a['parts'])).strip()


# 앞쪽 (인쇄된 줄 그대로)
P[1][1] = [':: ' + '\n'.join(plain(a) for a in rows(1))]
# 예경문 + 부처님 사진 (인쇄본 2~3쪽에 걸친 사진을 하나로)
ims = []
for pn in (3, 4):
    pg = src[pn - 1]; xref = pg.get_images()[0][0]; pix = fitz.Pixmap(src, xref)
    if pix.alpha: pix = fitz.Pixmap(pix, 0)
    if not pix.colorspace or pix.colorspace.n != 3: pix = fitz.Pixmap(fitz.csRGB, pix)
    ims.append(Image.frombytes('RGB', [pix.width, pix.height], pix.samples))
W = sum(i.width for i in ims); H = max(i.height for i in ims)
sp = Image.new('RGB', (W, H), 'white'); x = 0
for im in ims: sp.paste(im, (x, 0)); x += im.width
sp = sp.resize((W // 2, H // 2)); path = f'public/uploads/{bk}-buddha.jpg'; sp.save(path, quality=82)
images.append('/uploads/' + path.split('/')[-1])
ls = [plain(a) for a in rows(2)]
P[2][1] = ['**' + ls[0] + '**', '\n'.join(ls[1:])]
P[3][1] = [f'![#부처님 사진](/uploads/{bk}-buddha.jpg)']
# 4쪽 저자 소개
P[4][1] = body_paras(4, rows(4))
# 5쪽 속표지
ls = [plain(a) for a in rows(5)]
P[5][1] = ['^^ ' + ls[0] + '\n' + ls[1], ':: ' + ' '.join(ls[2:])]
# 10~11쪽 목차: 인쇄된 줄 그대로 (항목 … 쪽)
for n in (10, 11):
    out = []
    for a in rows(n):
        t = plain(a)
        if t == '목차': out.append('## 목차'); continue
        out.append(t)
    P[n][1] = ([out[0], '\n'.join(out[1:])] if out and out[0].startswith('## ') else ['\n'.join(out)])
# 386~391쪽 부록 표: 인쇄된 줄 그대로
for n in range(386, 392):
    if n == 387 - 1 + 0 and False: pass
for n in range(387, 392):
    out, block = [], []
    for a in rows(n):
        t = plain(a)
        if a['head']:
            if block: out.append('\n'.join(block)); block = []
            out.append('## ' + t); continue
        if re.match(r'제\d+품', t) or a['bold']:
            if block: out.append('\n'.join(block)); block = []
            out.append('**' + t + '**'); continue
        block.append(t)
    if block: out.append('\n'.join(block))
    P[n][1] = out
# 392쪽 판권지: 인쇄된 줄 그대로
ls = [plain(a) for a in rows(392)]
P[392][1] = ['\n'.join(ls)]

# 부 표지 쪽(15·153·313·387): '사성제로 정리한 숫따니빠따┃제1부' 작은 줄 + 큰 제목
for n in (15, 153, 313, 387):
    hs = [plain(a) for a in rows(n)]
    P[n][1] = [':: ' + hs[0], '^^ ' + ' '.join(hs[1:])] if len(hs) >= 2 else P[n][1]
body = ''
for n, ps in pages:
    body += f'=== {n}쪽 ===\n' + '\n\n'.join(clean(x) for x in ps if clean(x)) + '\n\n'
body = re.sub(r'\*\*( ?)\*\*', r'\1', body).rstrip() + '\n'

nz = lambda x: re.sub(r'[^0-9A-Za-z가-힣一-龥]', '', x)
PG = {int(m.group(1)): m.group(2) for m in re.finditer(r'=== (\d+)쪽 ===\n(.*?)(?=\n=== |\Z)', body, re.S)}
toc = []
for l in open(tocf, encoding='utf-8'):
    if not l.strip(): continue
    sub = l.startswith('  '); f = l.strip().split('\t'); title, pg = f[0], int(f[1])
    e = {'title': title, 'page': pg, 'sub': sub}
    if len(f) > 2: e['toc_title'] = f[2]
    k = None
    for q in ((pg, pg + 1, pg - 1, pg + 2) if sub else (pg,)):
        ps = [p for p in PG.get(q, '').split('\n\n') if p.strip()]
        k = next((i for i, p in enumerate(ps) if p.startswith(('## ', '**')) and nz(p)[:8] == nz(title)[:8]), None)
        if k is not None:
            if q != pg: print('목차 쪽 옮김:', title, pg, '→', q); e['page'] = q
            break
    if k is None: print('  (소제목 없음)', title, pg)
    elif k > 0: e['at'] = re.sub(r'^(## |\*\*)', '', ps[k])[:10]
    toc.append(e)
json.dump({'book': bk, 'edition': ED, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '쪽', len(toc), '목차', len(images), '그림')
