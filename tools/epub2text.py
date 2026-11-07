#!/usr/bin/env python3
"""EPUB 전자책을 글로 읽기 본문(content/texts/<ID>.json)으로 만듭니다. (『수행과 지혜』 DL-0008 전자책 형식에 맞춤)

  python3 tools/epub2text.py 책.epub DL-0008 초판

- 쪽 번호가 없는 전자책이라 소제목마다 한 '쪽'(=== ===)으로 나눔 (쪽 이름 없음)
- 장 제목(head1)·소제목(head3)은 목차에, 소제목은 '## '
- 굵은 글(문답의 '수행자'·'사야도', 판권 글 등)은 **굵게**
- 그림은 public/uploads/<ID>-… 로 복사
"""
import html, json, os, re, shutil, sys, zipfile
from PIL import Image

epub, bk, ed = sys.argv[1], sys.argv[2], sys.argv[3]
z = zipfile.ZipFile(epub)
opf_path = [n for n in z.namelist() if n.endswith('.opf')][0]
base = os.path.dirname(opf_path)
opf = z.read(opf_path).decode('utf-8')
items = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
spine = [items[i] for i in re.findall(r'<itemref idref="([^"]+)"', opf)]

UP = 'public/uploads'
imgs = []


def image(src, alt):
    name = os.path.basename(src)
    stem, ext = os.path.splitext(name)
    data = z.read(os.path.normpath(os.path.join(base, 'Text', src)).replace('\\', '/'))
    out = f'{bk}-{stem}'
    tmp = '/tmp/_epimg' + ext
    open(tmp, 'wb').write(data)
    im = Image.open(tmp)
    if stem == 'bridge':  # 구분 장식 (투명 배경)
        path = f'{UP}/{out}.png'; im.save(path)
    else:
        im = im.convert('RGB'); path = f'{UP}/{out}.jpg'; im.save(path, quality=85)
    url = '/' + path.replace('public/', '')
    if url not in imgs:
        imgs.append(url)
    return f'![#{alt}]({url})'


def text(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<(b|strong)>(.*?)</\1>', r'**\2**', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return '\n'.join(l.strip() for l in s.split('\n')).strip()


SKIP = {'Text/cover.xhtml', 'Text/thanks.xhtml'}  # 표지 그림 / (전자책의 '감사의 말씀' 파일은 목차가 잘못 들어가 있음)
pages, toc = [], []
cur = []


def flush():
    global cur
    while cur and cur[-1] == '':
        cur.pop()
    if cur:
        pages.append('\n\n'.join(x for x in cur if x != ''))
    cur = []


def chapter(title, sub=False):
    flush()
    toc.append({'title': title, 'page': len(pages) + 1, 'sub': sub})


NAMES = {'Text/inner.xhtml': '속표지', 'Text/namotassa.xhtml': '예경문', 'Text/sayadaw.xhtml': '잠언',
         'Text/contents.xhtml': '목차', 'Text/copyleft.xhtml': '판권지', 'Text/epub.xhtml': '전자책 판권지'}

LINES = {'Text/inner.xhtml', 'Text/namotassa.xhtml', 'Text/sayadaw.xhtml', 'Text/contents.xhtml', 'Text/copyleft.xhtml', 'Text/epub.xhtml'}  # 줄마다 끊어 쓴 쪽
for href in spine:
    if href in SKIP:
        continue
    s = z.read(os.path.join(base, href)).decode('utf-8')
    body = re.search(r'<body[^>]*>(.*)</body>', s, re.S).group(1)
    if href in NAMES:
        chapter(NAMES[href])
    started = href in NAMES
    verse = []  # 오른쪽 맞춤 줄(body2right)·가운데 줄 묶음

    def end_verse():
        global verse
        if verse:
            cur.append('\n'.join(verse)); verse = []

    prev_head = False
    for m in re.finditer(r'<table.*?</table>|<h1[^>]*>.*?</h1>|<p[^>]*>.*?</p>|<img[^>]*>', body, re.S):
        tag = m.group(0)
        if not tag.startswith('<h1'):
            prev_head = False if re.sub(r'<[^>]+>|&#160;|\s', '', tag) or tag.startswith('<img') or tag.startswith('<table') else prev_head
        cls = (re.search(r'class="([^"]*)"', tag) or [None, ''])[1]
        if tag.startswith('<table'):  # 용어 해설: 굵은 낱말 + 풀이
            end_verse()
            term = text(re.search(r'<h1[^>]*>(.*?)</h1>', tag, re.S).group(1))
            defs = [text(x) for x in re.findall(r'<p[^>]*>(.*?)</p>', tag, re.S)]
            cur.append('**' + term + '**\n' + '\n'.join(d for d in defs if d))
            continue
        if tag.startswith('<img'):
            end_verse()
            src = re.search(r'src="([^"]+)"', tag).group(1)
            alt = {'sayadaw.jpg': '쉐우민 사야도 사진', 'author.jpg': '아신 떼자니야 사야도 사진', 'bridge.png': '구분 장식'}.get(os.path.basename(src), '사진')
            cur.append(image(src, alt))
            continue
        inner = re.sub(r'^<(h1|p)[^>]*>|</(h1|p)>$', '', tag, flags=re.S)
        t = text(inner)
        if href in LINES:  # 줄 단위: 빈 줄에서 문단을 나눔
            if not t:
                end_verse(); continue
            if href == 'Text/contents.xhtml' and t == '목차':
                cur.append('## 목차'); continue
            bold = 'weight7' in cls or ('head3' in cls and href == 'Text/sayadaw.xhtml')
            verse.append('**' + t.replace('\n', '**\n**') + '**' if bold else t)
            continue
        if tag.startswith('<h1'):
            end_verse()
            if 'head1' in cls and not started:  # 장 제목
                chapter(t); cur.append('## ' + t); started = True
                continue
            if href == 'Text/inner.xhtml' or href == 'Text/contents.xhtml' or href == 'Text/author.xhtml':
                if href == 'Text/author.xhtml' and t == '저자 소개' and not started:
                    chapter(t); cur.append('## ' + t); started = True; continue
                if href == 'Text/contents.xhtml' and t == '목차':
                    continue
                cur.append(t if href != 'Text/contents.xhtml' else t)
                continue
            if 'head3' in cls:  # 소제목 = 새 쪽 (두 줄로 나뉜 소제목은 하나로)
                if cur and cur[-1].startswith('## ') and prev_head:
                    cur[-1] += '\n' + t; toc[-1]['title'] += ' ' + t
                else:
                    chapter(t, sub=True); cur.append('## ' + t)
                prev_head = True
                continue
            if 'head1' in cls:
                chapter(t); cur.append('## ' + t); started = True; continue
            cur.append(t); continue
        if not t:
            if verse:
                end_verse()
            continue
        if 'title1' in cls:  # 문답: 앞의 말하는 이 이름이 굵게
            end_verse()
            mm = re.match(r'<p[^>]*>(.*?)<span>(.*)</span>\s*</p>$', tag, re.S)
            if mm:
                who, said = text(mm.group(1)), text(mm.group(2))
                cur.append(f'**{who}** {said}' if who else said)
            else:
                cur.append(f'**{t}**' if href not in ('Text/contents.xhtml',) else t)
            continue
        if 'title2' in cls:
            end_verse()
            if not started:
                chapter(t); cur.append('## ' + t); started = True
            else:
                cur.append('## ' + t)
            continue
        if 'weight7' in cls:
            end_verse()
            cur.append('**' + t.replace('\n', '**\n**') + '**')
            continue
        if 'body2right' in cls or 'center' in cls:
            verse.append(t)
            continue
        end_verse()
        if href == 'Text/author.xhtml' and t.startswith('아신 떼자니야 사야도') and len(t) < 20:
            cur.append(t); continue
        cur.append(t)
    end_verse()
    if href == 'Text/author.xhtml' and not started:
        chapter('저자 소개')
flush()

# 쪽 표시: 쪽 번호가 없으므로 비워 둠
body = ''.join(f'=== ===\n{p}\n\n' for p in pages).rstrip() + '\n'
toc = [t for t in toc if t['title']]
# 같은 쪽에 장 제목과 첫 소제목이 겹치면(장 첫머리 사진 다음 소제목) 그대로 둠
out = {'book': bk, 'edition': ed, 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in imgs], 'body': body}
json.dump(out, open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '쪽,', len(toc), '목차,', len(imgs), '그림')
