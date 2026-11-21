#!/usr/bin/env python3
"""『위빠사나 수행의 목적과 방법』(DL-0009) 전자책 → content/texts/DL-0009.json (글자는 전자책 그대로)
  python3 tools/epub2text_dl0009.py 책.epub
"""
import html, json, os, re, sys, zipfile
from PIL import Image
epub = sys.argv[1]; bk = 'DL-0009'
z = zipfile.ZipFile(epub)
opf = z.read('OEBPS/content.opf').decode()
items = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
spine = [items[i] for i in re.findall(r'<itemref idref="([^"]+)"', opf)]

def text(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<span[^>]*font-weight:\s*(?:700|800|900|bold)[^>]*>(.*?)</span>', lambda m: '**' + m.group(1).strip() + '**' if m.group(1).strip() else m.group(1), s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return '\n'.join(re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')).strip()

NAMES = {'Text/inner.xhtml': '속표지', 'Text/author.xhtml': '저자 소개', 'Text/toreader.xhtml': '읽는 분들에게', 'Text/contents.xhtml': '목차', 'Text/copyleft.xhtml': '판권지'}
pages, toc, imgs = [], [], []
for href in spine:
    if href == 'Text/cover.xhtml':
        continue
    s = z.read('OEBPS/' + href).decode()
    body = re.search(r'<body[^>]*>(.*)</body>', s, re.S).group(1)
    paras, lines = [], []
    def endl():
        global lines
        if lines: paras.append('\n'.join(lines)); lines = []
    title = NAMES.get(href)
    for m in re.finditer(r'<h\d[^>]*>.*?</h\d>|<p[^>]*>.*?</p>|<img[^>]*>', body, re.S):
        tag = m.group(0); cls = (re.search(r'class="([^"]*)"', tag) or [None, ''])[1]
        if tag.startswith('<img'):
            endl(); src = os.path.basename(re.search(r'src="([^"]+)"', tag).group(1))
            data = z.read('OEBPS/Images/' + src); stem = os.path.splitext(src)[0]
            path = f'public/uploads/{bk}-{stem}.jpg'; open('/tmp/_i', 'wb').write(data); Image.open('/tmp/_i').convert('RGB').save(path, quality=88)
            url = '/' + path.replace('public/', ''); imgs.append(url)
            paras.append(f'![#장식]({url})'); continue
        inner = re.sub(r'^<(h\d|p)[^>]*>|</(h\d|p)>$', '', tag, flags=re.S)
        t = text(inner)
        if tag.startswith('<h'):
            endl()
            t2 = re.sub(r'^(\d{2})\s*', r'\1 ', re.sub(r'\*\*', '', t).strip())
            if 'head4' in cls or ('head1' in cls and href != 'Text/contents.xhtml' and title is None):
                title = re.sub(r'\s+', ' ', t2); paras.append('## ' + title); continue
            if href == 'Text/contents.xhtml':
                lines.append(re.sub(r'\s+', ' ', t2)) if t2 != '목차' else paras.append('## 목차'); continue
            paras.append('## ' + re.sub(r'\s+', ' ', t2)); continue
        if not t:
            endl(); continue
        if href in ('Text/inner.xhtml', 'Text/copyleft.xhtml'):
            lines.append(t); continue
        if href == 'Text/toreader.xhtml' and t == '읽는 분들에게':
            endl(); paras.append('## 읽는 분들에게'); continue
        endl()
        if 'body1' in cls:  # 굵은 바탕체(HCRBatang-Bold)로 강조된 문단
            t = '**' + t.replace('**', '') + '**'
        paras.append(t)
    endl()
    toc.append({'title': title, 'page': len(pages) + 1, 'sub': False})
    pages.append('\n\n'.join(paras))
body = ''.join(f'=== ===\n{p}\n\n' for p in pages).rstrip() + '\n'
json.dump({'book': bk, 'edition': '초판', 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in dict.fromkeys(imgs)], 'body': body}, open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), [t['title'] for t in toc])
