"""『대념처경』(DL-0035, 묘원 편역, 도서출판 행복한 숲 1판 2010) PDF → content/texts/DL-0035.json
  python3 tools/pdf2text_dl0035.py 책.pdf
그 다음 python3 tools/split_chapters.py --write

PDF 364쪽 (QuarkXPress→Distiller, 2010). PDF 쪽 = 인쇄 쪽 + 2, 쪽 이름은 쪽 아래 숫자(번호 없는 쪽은 앞뒤로 채움).
PDF 1·2·364 빈 쪽, 3 속표지(쪽 그대로 그림), 4~7 목차(`%% `), 8 귀경게, 장 표지(PDF 9·95·133·207·351 — `^^`),
목차 항목마다 한 장(본문 15pt 제목 = 장 이름), 12.5pt 굵은 줄·11.5pt 굵은 제목 줄 → `## `,
예불·독송 묶음: 한글 소리 줄(윤명조130 11.5) → `**…**`, 빠알리 로마자 줄(Garamond 10) → 같은 문단 다음 줄.
문단: 줄 사이 26pt 넘음·들여쓰기(+15pt)로 새 문단, 끝까지 찬 줄은 이어 붙임(한글 조판은 낱말 가운데서도 줄을 바꿈 —
줄 끝 빈칸은 PDF 에 글자로 있음), 짧은 줄 다음은 줄 바꿈(게송·대화).
로마자 줄 끝 하이픈: 붙인 낱말이 책 안에 있으면 붙이고(sikkhāpa-|daṃ), 없으면 그대로 둠 — 목록은 실행할 때 보임.
판권지 '｜' → '|'. 다른 글자는 PDF 그대로.
"""
import sys, re, json, os, io, collections
import fitz

pdf = sys.argv[1]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BK, ED = 'DL-0035', '초판'
doc = fitz.open(pdf)
UP = os.path.join(REPO, 'public/uploads')
L0, R0 = 70.9, 316.5
log = collections.Counter(); images = []


def lines_of(n):
    p = doc[n - 1]; raw = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'] == '': continue
                raw.append(dict(t=s['text'], x0=s['bbox'][0], x1=s['bbox'][2], y=s['origin'][1], size=s['size'], font=s['font']))
    raw.sort(key=lambda s: (round(s['y'], 0), s['x0']))
    out = []
    for s in raw:
        if out and abs(out[-1]['y'] - s['y']) < 2.5:
            out[-1]['sp'].append(s)
        else:
            out.append(dict(y=s['y'], sp=[s]))
    res = []
    for g in out:
        sp = sorted(g['sp'], key=lambda s: s['x0'])
        t = ''
        for i, s in enumerate(sp):
            if i and s['x0'] - sp[i - 1]['x1'] > 2.5 and not t.endswith(' ') and not s['t'].startswith(' '): t += ' '
            t += s['t']
        if not t.strip(): continue
        main = max(sp, key=lambda s: len(s['t'].strip()))
        kor = [s for s in sp if re.search(r'[가-힣]', s['t'])]
        res.append(dict(y=g['y'], x0=sp[0]['x0'] if sp[0]['t'].strip() else sp[1]['x0'] if len(sp) > 1 else sp[0]['x0'],
                        x1=max(s['x1'] for s in sp if s['t'].strip()), t=t, size=max(s['size'] for s in sp if s['t'].strip()),
                        font=(kor[0] if kor else main)['font'], kor=bool(kor)))
    return res


def kind(l):
    if l['y'] > 478: return 'foot'
    if l['size'] >= 14.5: return 'h1'
    if 'MjO130' in l['font'] and 12.2 <= l['size'] <= 13: return 'h2'
    if 'MjO130' in l['font'] and 11.2 <= l['size'] <= 11.8: return 'pron'
    if not l['kor'] and re.search(r'[A-Za-z]', l['t']) and l['size'] < 10.5: return 'pali'
    return 'body'


def label(L):
    for l in L:
        if l['y'] > 478:
            m = re.search(r'(\d+)\s*$', l['t'])
            if m: return m.group(1)
    return None


PAL = []   # (page index, para index) of pali paras for hyphen fixing


def build(n, lab):
    L = [l for l in lines_of(n)]
    body = [l for l in L if kind(l) != 'foot']
    paras = []; kinds = []
    i = 0
    while i < len(body):
        l = body[i]; k = kind(l)
        if k == 'h1':
            hs = [l]
            while i + 1 < len(body) and kind(body[i + 1]) == 'h1' and body[i + 1]['y'] - hs[-1]['y'] < 30: i += 1; hs.append(body[i])
            paras.append('## ' + hs[0]['t'].strip()); kinds.append('h1')
            for h in hs[1:]: paras.append(':: ' + h['t'].strip()); kinds.append('sub')
            i += 1; continue
        if k == 'body' and 11.8 <= l['size'] <= 12.2 and l['x0'] > L0 + 20:
            paras.append(':: ' + l['t'].strip()); kinds.append('sub'); i += 1; continue   # 장 제목 아래 부제 '-임산부의 …-'
        if k == 'body' and l['x0'] > 200 and l['x1'] > R0 - 14 and len(l['t'].strip()) < 12 and i == len(body) - 1:
            paras.append('>> ' + l['t'].strip()); kinds.append('sign'); i += 1; continue   # 끝 서명 '묘원 올림'
        if k == 'h2' or (k == 'pron' and not (i + 1 < len(body) and kind(body[i + 1]) in ('pali', 'pron'))):
            t = l['t']
            while k == 'h2' and i + 1 < len(body) and kind(body[i + 1]) == 'h2' and body[i + 1]['y'] - body[i]['y'] < 26:
                i += 1; t += body[i]['t']   # 두 줄로 인쇄된 소제목 ('…를 알아' + '차림')
            paras.append('## ' + t.strip()); kinds.append('h2'); i += 1; continue
        if k in ('pron', 'pali'):
            pr = []; pa = []; prev = None
            while i < len(body) and kind(body[i]) in ('pron', 'pali'):
                x = body[i]
                if prev is not None and x['y'] - prev['y'] > 26: break
                if kind(x) == 'pron' and pa: break
                (pr if kind(x) == 'pron' else pa).append(x); prev = x; i += 1
            def join(ls):
                s = ''
                for j, x in enumerate(ls):
                    t = x['t']
                    if j and not (ls[j - 1]['x1'] > R0 - 14 or x['x0'] > ls[j - 1]['x0'] + 8 or x['x0'] > L0 + 20):
                        s = s.rstrip() + '\n'
                    elif j and ls[j - 1]['t'].rstrip().endswith('-') and kind(x) == 'pali':
                        s = s.rstrip(); PAL.append(len(PAL))
                        s += '\u0001'   # 줄 끝 하이픈 자리 (뒤에서 정함)
                    s += t
                return s.strip()
            txt = []
            if pr: txt.append('**' + re.sub(r'\s+$', '', join(pr)).replace('\n', '**\n**') + '**')
            if pa: txt.append(join(pa))
            paras.append('\n'.join(txt)); kinds.append('chant'); continue
        # 보통 글
        ls = [l]; i += 1
        while i < len(body) and kind(body[i]) == 'body':
            x = body[i]; pv = ls[-1]
            if x['y'] - pv['y'] > 26: break
            hang = re.match(r'\d+\. ', ls[0]['t']) and ls[0]['x0'] > L0 + 10 and 8 < x['x0'] - ls[0]['x0'] < 18   # 번호 항목의 둘째 줄 (번호 뒤에 맞춰 들여 씀)
            if x['x0'] > L0 + 10 and pv['x1'] > R0 - 14 and abs(x['x0'] - pv['x0']) > 3 and not hang: break   # 새 문단 들여쓰기
            if x['x0'] > L0 + 10 and pv['x1'] <= R0 - 14 and abs(x['x0'] - pv['x0']) > 3 and pv['x0'] < L0 + 5: break
            ls.append(x); i += 1
        s = ''
        for j, x in enumerate(ls):
            if j:
                if ls[j - 1]['x1'] > R0 - 14: pass
                else: s = s.rstrip() + '\n'
            s += x['t']
        paras.append(s.strip()); kinds.append('p')
    return dict(lab=lab, paras=paras, kinds=kinds, n=n)


# ---------------- 쪽 이름 ----------------
labs = {}
for n in range(1, len(doc) + 1):
    lb = label(lines_of(n))
    if lb: labs[n] = lb
for n in range(1, len(doc) + 1):
    if n not in labs and n - 2 >= 1 and 3 < n < 364:
        labs[n] = str(n - 2); log['번호 없는 쪽에 번호 넣음'] += 1
bad = [(n, v) for n, v in labs.items() if int(v) != n - 2]
if bad: print('! 쪽 번호가 PDF 쪽 - 2 와 다름:', bad[:10])

PAGES = []; chapters = []

# 속표지 — 쪽 그대로 그림 (책 이름·장 이름·출판사 글자가 그림 안에 있음)
P3 = doc[2]
from PIL import Image
pix = P3.get_pixmap(dpi=220, clip=P3.rect)
from PIL import ImageChops
_im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
_bb = ImageChops.difference(_im, Image.new('RGB', _im.size, (255, 255, 255))).convert('L').point(lambda v: 255 if v > 12 else 0).getbbox()
_im.crop(_bb).save(os.path.join(UP, f'{BK}-titlepage.jpg'), quality=85, optimize=True)   # 둘레 흰 여백은 잘라 냄 (회색 속표지만 크게)
images.append(f'/uploads/{BK}-titlepage.jpg')
PAGES.append(dict(lab='', paras=[f'![#대념처경 속표지](/uploads/{BK}-titlepage.jpg)'], kinds=['img'], n=3)); chapters.append(('속표지', 0))

# 목차 PDF 4~7
rows = []; prevy = None
for n in range(4, 8):
    for l in lines_of(n):
        if l['y'] > 478: continue
        t = l['t']
        if 'MjO130' in l['font']:
            if rows: rows.append('~')
            rows.append('**' + t.strip() + '**'); continue
        m = re.match(r'^(.*?)\s*·{2,}[·\s]*(\d+)\s*$', t) or re.match(r'^(.*?)\s*[_＿]\s*(\d+)\s*$', t)
        if m: rows.append('- ' + m.group(1).strip() + ' | ' + m.group(2))
        else: rows.append('- ' + t.strip())
PAGES.append(dict(lab='', paras=['%% ' + '\n'.join(rows)], kinds=['toc'], n=4)); chapters.append(('목차', 1))
TOCITEMS = [(r[2:].split(' | ')[0], int(r.split(' | ')[1])) for r in rows if r.startswith('- ') and ' | ' in r]

# 본문 PDF 8 ~ 363
COVERS = {9, 95, 133, 207, 351}
for n in range(8, 364):
    lab = (labs.get(n, '') + '쪽') if labs.get(n) else ''
    if n in COVERS:
        L = [l for l in lines_of(n) if l['y'] < 478]
        t = ' '.join(l['t'].strip() for l in L)
        PAGES.append(dict(lab=lab, paras=['^^ ' + t], kinds=['cover'], n=n)); chapters.append((t, len(PAGES) - 1)); continue
    if n == 363:   # 판권지: 줄마다
        L = [l for l in lines_of(n) if l['t'].strip()]
        out = []; prev = None
        for l in L:
            t = l['t'].strip().replace('｜', '|')
            if prev is not None and l['y'] - prev['y'] > 14: out.append('')
            out.append(t); prev = l
        txt = '\n'.join(out)
        PAGES.append(dict(lab=lab, paras=[p for p in txt.split('\n\n')], kinds=['p'] * len(txt.split('\n\n')), n=n)); chapters.append(('판권지', len(PAGES) - 1)); continue
    pg = build(n, lab)
    if not pg['paras']:
        PAGES.append(pg); continue
    # 쪽이 넘어가는 문단 이어 붙이기
    prevp = next((P for P in reversed(PAGES) if P['paras']), None)
    if prevp and pg['kinds'][0] == 'p' and prevp['kinds'][-1] == 'p':
        first = lines_of(n); first = [l for l in first if kind(l) == 'body']
        lastl = [l for l in lines_of(prevp['n']) if kind(l) == 'body']
        if first and lastl and first[0]['x0'] < L0 + 5 and lastl[-1]['x1'] > R0 - 14:
            prevp['paras'][-1] = prevp['paras'][-1] + (' ' if lastl[-1]['t'].endswith(' ') else '') + pg['paras'][0]; pg['paras'].pop(0); pg['kinds'].pop(0); log['쪽을 넘어 이어 붙인 문단'] += 1
    PAGES.append(pg)
    for j, k in enumerate(pg['kinds']):
        if k == 'h1' or (k == 'h2' and pg['paras'][j] == '## 편역자 후기'):
            title = pg['paras'][j][3:]
            if n == 8: title = '귀경게'
            chapters.append((title, len(PAGES) - 1, j))

# 로마자 줄 끝 하이픈
allpali = ' '.join(p for P in PAGES for p in P['paras'])
words = set(re.findall(r'[A-Za-zĀ-ſḀ-ỿ]+', allpali.replace('\u0001', '')))
dec = []
for P in PAGES:
    for j, p in enumerate(P['paras']):
        if '\u0001' not in p: continue
        def fx(m):
            a, b = m.group(1), m.group(2)
            if (a + '-' + b) in ('vile-pana', 'vilepa-na', 'nibbu-tim') or (a + b) in words or (a + b).lower() in {w.lower() for w in words}:
                dec.append((P['lab'], a + '-|' + b, '붙임')); return a + b
            dec.append((P['lab'], a + '-|' + b, '하이픈 그대로')); return a + '-' + b
        P['paras'][j] = re.sub(r'([A-Za-zĀ-ſḀ-ỿ]+)-?\u0001([A-Za-zĀ-ſḀ-ỿ]+)', fx, p)
        P['paras'][j] = P['paras'][j].replace('\u0001', '')

for P in PAGES:
    P['paras'] = ['\n'.join(re.sub(r'(?<=\S) {2,}', ' ', x.replace('\xa0', ' ')).rstrip() for x in p.split('\n')) for p in P['paras']]

toc = []
for c in chapters:
    t, pi = c[0], c[1]; j = c[2] if len(c) > 2 else 0
    e = dict(title=re.sub(r'\s+', ' ', t).strip(), page=pi + 1, sub=False)
    if j > 0: e['at'] = PAGES[pi]['paras'][j][3:][:30]
    toc.append(e)

body = ''
for P in PAGES:
    body += (f"=== {P['lab']} ===" if P['lab'] else '=== ===') + '\n\n' + '\n\n'.join(P['paras']) + '\n\n'
out = os.path.join(REPO, 'content/texts', f'{BK}.json')
json.dump({'book': BK, 'edition': ED, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in images], 'body': body.rstrip() + '\n'}, open(out, 'w'), ensure_ascii=False, indent=2)
open(out, 'a').write('\n')
print(out, len(PAGES), '쪽', len(toc), '장', dict(log))
for d in dec: print('  하이픈', *d)
