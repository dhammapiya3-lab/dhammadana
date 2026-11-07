#!/usr/bin/env python3
"""『마음가짐이 바르게 되었을 때 수행하십시오』(DL-0010) 전자책 → content/texts/DL-0010.json (글자는 전자책 그대로)
  python3 tools/epub2text_dl0010.py 책.epub

- 전자책 파일 하나 = 한 장(화면). 쪽 번호는 없음(=== ===).
- 장 제목(head1 두 줄)은 한 줄로 합쳐 '## 제목', 수행하는 시간의 1.~4.(head2)는 '## ' 소제목 + 목차 아래 단계
- 전자책에서 굵은 글꼴인 곳(title1, body1 = 굵은 바탕체)은 **굵게**
- 각주: 본문의 번호는 [^n], 풀이(전자책 끝 [주해])는 각 장 끝에 [^n]: 로
- 그림: 사야도 사진, '부탁의 말씀' 끝 그림, 구분 장식(aa.png)
"""
import html, json, os, re, sys, zipfile
from PIL import Image

epub = sys.argv[1]; bk = 'DL-0010'
z = zipfile.ZipFile(epub)
opf = z.read('OEBPS/content.opf').decode()
items = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
spine = [items[i] for i in re.findall(r'<itemref idref="([^"]+)"', opf)]


def text(s):
    s = re.sub(r'<sup>\s*<a[^>]*class="s_no"[^>]*>(\d+)</a>\s*</sup>', r'[^\1]', s)
    s = re.sub(r'\s*\n\s*', ' ', s)  # 원본 파일의 줄 바꿈은 빈칸 (<br/>만 줄 바꿈)
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return '\n'.join(re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')).strip()


# 각주 풀이
fn = {}
fs = z.read('OEBPS/Text/footnotes.xhtml').decode()
for m in re.finditer(r'<p class="quarry">\s*<a id="q(\d+)"[^>]*>\d+</a>(.*?)</p>', fs, re.S):
    fn[m.group(1)] = text(m.group(2))

IMG = {'sayadaw.jpg': '아신 떼자니야 사야도 사진', 'write.png': '아신 떼자니야 사야도 서명', 'aa.png': '장식'}
NAMES = {'Text/inner.xhtml': '속표지', 'Text/namotassa.xhtml': '예경문', 'Text/author.xhtml': '저자 소개',
         'Text/contents.xhtml': '목차', 'Text/copyleft1.xhtml': '판권지', 'Text/copyleft2.xhtml': '전자책 판권지'}
LINES = {'Text/inner.xhtml', 'Text/namotassa.xhtml', 'Text/author.xhtml', 'Text/contents.xhtml', 'Text/copyleft1.xhtml', 'Text/copyleft2.xhtml'}
pages, toc, imgs = [], [], []
saved = set()


def image(src):
    name = os.path.basename(src); stem, ext = os.path.splitext(name)
    path = f'public/uploads/{bk}-{stem}{".png" if ext == ".png" else ".jpg"}'
    if path not in saved:
        open('/tmp/_i', 'wb').write(z.read('OEBPS/Images/' + name))
        im = Image.open('/tmp/_i')
        (im.save(path) if ext == '.png' else im.convert('RGB').save(path, quality=88)); saved.add(path)
    url = '/' + path.replace('public/', ''); imgs.append(url)
    return f'![#{IMG.get(name, "그림")}]({url})'


for href in spine:
    if href in ('Text/cover.xhtml', 'Text/footnotes.xhtml'):
        continue
    s = z.read('OEBPS/' + href).decode()
    body = re.search(r'<body[^>]*>(.*)</body>', s, re.S).group(1)
    paras, lines, heads, refs = [], [], [], []
    title = NAMES.get(href); subs = []

    def endl():
        global lines
        if lines: paras.append('\n'.join(lines)); lines = []

    for m in re.finditer(r'<table.*?</table>|<h\d[^>]*>.*?</h\d>|<p[^>]*>.*?</p>|<img[^>]*>', body, re.S):
        tag = m.group(0); cls = (re.search(r'class="([^"]*)"', tag) or [None, ''])[1]
        if tag.startswith('<table'):  # 용어 해설: 굵은 낱말 + 풀이
            endl()
            term = text(re.search(r'<h1[^>]*>(.*?)</h1>', tag, re.S).group(1))
            defs = [l for x in re.findall(r'<p[^>]*>(.*?)</p>', tag, re.S) for l in text(x).split('\n') if l.strip()]
            paras.append('**' + term + '**\n' + '\n'.join(d for d in defs if d)); continue
        if tag.startswith('<img'):
            endl(); paras.append(image(re.search(r'src="([^"]+)"', tag).group(1))); continue
        t = text(re.sub(r'^<(h\d|p)[^>]*>|</(h\d|p)>$', '', tag, flags=re.S))
        refs += re.findall(r'\[\^(\d+)\]', t)
        if 'head1' in cls or tag.startswith('<h'):
            if not t: continue
            if href == 'Text/inner.xhtml':  # 속표지 책 제목: 크게·가운데
                heads.append(t); continue
            if href == 'Text/contents.xhtml':
                endl(); paras.append('## 목차' if t == '목차' else t); continue
            if 'head1' in cls and tag.startswith('<p'):  # 장 제목(두 줄 → 한 줄)
                heads.append(t); continue
            endl(); title = title or t; paras.append('## ' + t); continue
        if heads and href != 'Text/inner.xhtml':
            title = ' '.join(heads); paras.append('## ' + title); heads = []
        if heads and href == 'Text/inner.xhtml' and t:
            paras.append('^^ ' + '\n'.join(heads)); heads = []
        if not t:
            endl(); continue
        if 'head2' in cls:  # 수행하는 시간의 1.~4.
            endl(); paras.append('## ' + t); subs.append(t); continue
        bold = ('title1' in cls or 'body1' in cls or 'weight7' in cls) and href != 'Text/contents.xhtml'
        if href in LINES:
            lines.append('**' + t + '**' if bold else t); continue
        endl()
        paras.append('**' + t + '**' if bold else t)
    endl()
    for n in refs:  # 이 장의 각주 풀이를 장 끝에
        paras.append(f'[^{n}]: {fn.pop(n)}')
    toc.append({'title': title, 'page': len(pages) + 1, 'sub': False})
    for t in subs:
        toc.append({'title': t, 'page': len(pages) + 1, 'sub': True, 'at': t})
    pages.append('\n\n'.join(paras))
assert not fn, fn
body = ''.join(f'=== ===\n{p}\n\n' for p in pages).rstrip() + '\n'
json.dump({'book': bk, 'edition': '초판', 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in dict.fromkeys(imgs)], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '장', [t['title'] for t in toc])
