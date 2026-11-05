#!/usr/bin/env python3
"""PDF를 도서관 '온라인 읽기' 자료로 바꿉니다.

쓰는 법 (dhammadana 폴더에서):
  python3 tools/pdf2reader.py 책.pdf DL-0007 초판
  python3 tools/pdf2reader.py 책.pdf DL-0007 초판 --offset 4     # PDF 5번째 쪽이 인쇄된 1쪽일 때
  python3 tools/pdf2reader.py 책.pdf DL-0007 초판 --toc toc.txt  # 목차를 직접 줄 때 (한 줄에 "제목<TAB>PDF쪽번호")

만들어지는 것 (tools/out/ 아래, 그대로 R2에 올리면 됩니다):
  reader/DL-0007/초판/manifest.json   쪽 목록·목차·본문 글
  reader/DL-0007/초판/p/0001.webp     보통 크기 쪽 그림 (가로 1000px)
  reader/DL-0007/초판/big/0001.webp   확대용 쪽 그림 (가로 1800px)
  pdf/DL-0007/DL-0007_초판.pdf         내려받기용 PDF 사본

필요한 것: pip install pypdfium2 pypdf pillow
"""
import argparse, json, os, re, shutil, sys, unicodedata

import pypdfium2 as pdfium
from pypdf import PdfReader

ap = argparse.ArgumentParser(description='PDF → 온라인 읽기 자료')
ap.add_argument('pdf'); ap.add_argument('book_id'); ap.add_argument('edition', nargs='?', default='초판')
ap.add_argument('--offset', type=int, default=None, help='인쇄된 1쪽 앞에 있는 PDF 쪽 수')
ap.add_argument('--toc', help='목차 파일 (제목<TAB>PDF쪽번호)')
ap.add_argument('--out', default=os.path.join(os.path.dirname(__file__), 'out'))
ap.add_argument('--width', type=int, default=1000); ap.add_argument('--big', type=int, default=1800)
ap.add_argument('--quality', type=int, default=80)
ap.add_argument('--no-text', action='store_true', help='본문 글을 넣지 않음 (그림만)')
a = ap.parse_args()

if not re.fullmatch(r'DL-\d{4}', a.book_id):
    sys.exit('자료번호는 DL-0001 처럼 써 주세요.')
base = os.path.join(a.out, 'reader', a.book_id, a.edition)
for d in ('p', 'big'):
    os.makedirs(os.path.join(base, d), exist_ok=True)

doc = pdfium.PdfDocument(a.pdf)
rd = PdfReader(a.pdf)
N = len(doc)
print(f'『{a.pdf}』 {N}쪽을 바꿉니다…')

# 인쇄 쪽 번호
labels = [''] * N
try:
    pl = list(rd.page_labels)
    if any(l and l != str(i + 1) for i, l in enumerate(pl)):
        labels = [str(l or '') for l in pl]
except Exception:
    pass
if a.offset is not None:
    labels = [str(i + 1 - a.offset) if i + 1 - a.offset > 0 else '' for i in range(N)]

ODD = re.compile(r'[�-]')
def clean(t):
    t = unicodedata.normalize('NFC', t.replace('\r', '\n'))
    t = re.sub(r'[ \t]+', ' ', t)
    lines = [l.strip() for l in t.split('\n')]
    # 빈 줄 = 문단 나눔. 줄 끝 하이픈 이음은 그대로 둠(한국어 책이 대부분)
    out, buf = [], []
    for l in lines:
        if not l:
            if buf: out.append(' '.join(buf)); buf = []
        else:
            buf.append(l)
    if buf: out.append(' '.join(buf))
    return '\n\n'.join(out)

pages, odd_pages = [], []
for i in range(N):
    pg = doc[i]
    w, h = pg.get_size()
    for d, W in (('p', a.width), ('big', a.big)):
        img = pg.render(scale=W / w).to_pil()
        img.save(os.path.join(base, d, f'{i+1:04d}.webp'), 'WEBP', quality=a.quality, method=4)
    text = ''
    if not a.no_text:
        tp = pg.get_textpage(); text = clean(tp.get_text_range()); tp.close()
        if ODD.search(text): odd_pages.append(i + 1)
    pages.append({'img': f'p/{i+1:04d}.webp', 'big': f'big/{i+1:04d}.webp', 'w': round(w), 'h': round(h), 'label': labels[i], 'text': text})
    print(f'\r  {i+1}/{N}', end='', flush=True)
print()

# 목차
toc = []
if a.toc:
    for line in open(a.toc, encoding='utf-8'):
        if '\t' in line:
            t, p = line.rstrip('\n').rsplit('\t', 1)
            if p.strip().isdigit(): toc.append({'title': t.strip(), 'page': int(p)})
else:
    def walk(items, depth=0):
        for it in items:
            if isinstance(it, list): walk(it, depth + 1); continue
            try:
                n = rd.get_destination_page_number(it) + 1
                toc.append({'title': ('  ' * depth) + it.title.strip(), 'page': n})
            except Exception: pass
    try: walk(rd.outline)
    except Exception: pass
for t in toc:
    t['label'] = labels[t['page'] - 1] if 0 < t['page'] <= N else ''

man = {'book': a.book_id, 'edition': a.edition, 'pages': pages, 'toc': toc}
with open(os.path.join(base, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(man, f, ensure_ascii=False)

pdf_dir = os.path.join(a.out, 'pdf', a.book_id); os.makedirs(pdf_dir, exist_ok=True)
shutil.copyfile(a.pdf, os.path.join(pdf_dir, f'{a.book_id}_{a.edition}.pdf'))

size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(base) for f in fs)
print(f'완료: {base}  ({size/1e6:.1f} MB)')
print(f'  목차 {len(toc)}개' + ('' if toc else ' — PDF에 목차(책갈피)가 없습니다. --toc 로 직접 줄 수 있습니다.'))
print('  인쇄 쪽 번호: ' + ('있음' if any(labels) else '없음 — 필요하면 --offset 을 쓰세요.'))
if not a.no_text and not any(p['text'] for p in pages):
    print('  ⚠ 글자를 뽑지 못했습니다. 스캔본이면 쪽 보기만 됩니다(검색·듣기·밑줄 안 됨).')
if odd_pages:
    print(f'  ⚠ 깨진 글자가 있는 쪽: {odd_pages[:20]}{" …" if len(odd_pages) > 20 else ""} — 빨리어 점 글자가 깨졌을 수 있으니 확인하세요.')
print(f'다음: 책 자료({a.book_id})의 이 판에서 "온라인 읽기"를 켜고, PDF 주소를 pdf/{a.book_id}/{a.book_id}_{a.edition}.pdf 로 적으세요.')
