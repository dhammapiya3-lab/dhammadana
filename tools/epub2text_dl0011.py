#!/usr/bin/env python3
"""『법은 어디에나』(DL-0011) 전자책 → content/texts/DL-0011.json (글자는 전자책 그대로)
  python3 tools/epub2text_dl0011.py 책.epub

- 전자책 파일 하나 = 한 장(화면), 쪽 번호 없음(=== ===). 표지는 뺌.
- head2 = 장 제목('## ' + 목차), head3 = 소제목('## ' + 목차 아래 단계)
- 굵게 보이는 곳(용어 해설 낱말 head5·판권 weight7)만 **굵게**, 가운데 글(center·center2)은 ':: ' (줄마다 줄 바꿈)
- 사진(쪽 그림)·속표지 그림·사야도 사진·구분선(bridge)은 전자책 자리 그대로 넣음
"""
import html, json, os, re, sys, zipfile
from PIL import Image

epub = sys.argv[1]; bk = 'DL-0011'
z = zipfile.ZipFile(epub)
opf = z.read('OEBPS/content.opf').decode()
items = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
spine = [items[i] for i in re.findall(r'<itemref idref="([^"]+)"', opf)]


def text(s):
    s = re.sub(r'\s*\n\s*', ' ', s)
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return '\n'.join(re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')).strip()


saved, imgs = set(), []
ALT = {'sayadaw.jpg': '아신 떼자니야 사야도 사진', '2sayadaw.jpg': '쉐우민 사야도 사진', '1cover.jpg': '속표지', 'bridge.jpg': '구분선', 'bridge2.jpg': '구분 장식'}


def image(name):
    stem = os.path.splitext(name)[0]
    path = f'public/uploads/{bk}-{stem}.jpg'
    if path not in saved:
        open('/tmp/_i', 'wb').write(z.read('OEBPS/Images/' + name))
        im = Image.open('/tmp/_i').convert('RGB')
        if max(im.size) > 1200:
            im.thumbnail((1200, 1200))
        im.save(path, quality=80, optimize=True); saved.add(path)
    url = '/' + path.replace('public/', ''); imgs.append(url)
    return f'![#{ALT.get(name, "사진")}]({url})'


NAMES = {'Text/namotassa.xhtml': '예경문', 'Text/inner.xhtml': '속표지', 'Text/author.xhtml': '저자 소개',
         'Text/copyleft.xhtml': '판권지', 'Text/ebookcopyleft.xhtml': '전자책 판권지'}
LINES = {'Text/namotassa.xhtml', 'Text/copyleft.xhtml', 'Text/ebookcopyleft.xhtml'}
TAG = re.compile(r'<table.*?</table>|<h\d[^>]*>.*?</h\d>|<p[^>]*>.*?</p>|<p[^>]*/>|<img[^>]*>|<image[^>]*>', re.S)
pages, toc = [], []
for href in spine:
    if href == 'Text/cover.xhtml':
        continue
    s = z.read('OEBPS/' + href).decode()
    body = re.search(r'<body[^>]*>(.*)</body>', s, re.S).group(1)
    paras, lines, center = [], [], []
    title = NAMES.get(href); subs = []

    def endl():
        global lines, center
        if lines: paras.append('\n'.join(lines)); lines = []
        if center: paras.append(':: ' + '\n'.join(center)); center = []

    for m in TAG.finditer(body):
        tag = m.group(0); cls = (re.search(r'class="([^"]*)"', tag) or [None, ''])[1]
        if tag.startswith('<table'):  # 빨리어 용어 해설: 굵은 낱말 + 풀이
            endl()
            term = text(re.search(r'<h\d[^>]*>(.*?)</h\d>', tag, re.S).group(1))
            defs = [l for x in re.findall(r'<p[^>]*>(.*?)</p>', tag, re.S) for l in text(x).split('\n') if l.strip()]
            paras.append('**' + term + '**\n' + '\n'.join(defs)); continue
        if tag.startswith('<img') or tag.startswith('<image'):
            endl(); src = re.search(r'(?:xlink:href|src)="([^"]+)"', tag).group(1)
            paras.append(image(os.path.basename(src))); continue
        t = text(re.sub(r'^<(h\d|p)[^>]*>|</(h\d|p)>$', '', tag, flags=re.S)) if not tag.endswith('/>') else ''
        if tag.startswith('<h'):
            if not t: continue
            endl()
            if 'head2' in cls:
                if title is None: title = t
                paras.append('## ' + t); continue
            if 'head3' in cls:
                paras.append('## ' + t); subs.append(t); continue
            if 'head4' in cls:  # 목차의 장 이름
                lines.append('**' + t + '**'); continue
            paras.append('## ' + t); continue
        if href == 'Text/tokoreanreader.xhtml' and t == '한국 독자들에게' and title is None:
            endl(); title = t; paras.append('## ' + t); continue
        if not t:
            if href == 'Text/contents.xhtml' and lines: endl()
            if href in LINES: endl()
            if center and 'center' not in cls: endl()
            continue
        if 'center' in cls:  # 가운데 글: 줄마다 이어 한 덩어리로
            if lines: paras.append('\n'.join(lines)); lines = []
            center.append(t); continue
        if center: endl()
        bold = 'weight7' in cls  # body1·center2 의 'HCRB' 글꼴은 전자책에 등록돼 있지 않아 굵게 보이지 않음
        if href in LINES or href == 'Text/contents.xhtml':
            lines.append('**' + t.replace('\n', '**\n**') + '**' if bold else t); continue
        endl()
        paras.append('**' + t.replace('\n', '**\n**') + '**' if bold else t)
    endl()
    if title is None:
        raise SystemExit('장 이름 없음: ' + href)
    toc.append({'title': title, 'page': len(pages) + 1, 'sub': False})
    for t in subs:
        toc.append({'title': t, 'page': len(pages) + 1, 'sub': True, 'at': t})
    pages.append('\n\n'.join(paras))

body = ''.join(f'=== ===\n{p}\n\n' for p in pages).rstrip() + '\n'
json.dump({'book': bk, 'edition': '초판', 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in dict.fromkeys(imgs)], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '장', len(set(imgs)), '그림', [t['title'] for t in toc if not t['sub']])
