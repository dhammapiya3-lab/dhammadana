#!/usr/bin/env python3
"""『번뇌를 가볍게 여기지 마십시오』(DL-0013) 전자책 → content/texts/DL-0013.json (글자는 전자책 그대로)
  python3 tools/epub2text_dl0013.py 책.epub

- 전자책 파일 하나 = 한 화면(=== ===). 표지는 뺌. 장 이름은 전자책 목차(toc.ncx) 그대로.
- title2·head2 = 장 제목('## '), body1 = 소제목('## ' + 목차 아래 단계)
- 굵게: 전자책에서 굵은 글꼴(HCRBatang-Bold: title1·body12·body13·emphasis)과 판권(weight7), 용어 해설 낱말
- 가운데 글(text-align:center) = ':: ', 빈 줄(<p>&#160;</p>)로 묶음을 나눔
- 그림(삽화)은 전자책 자리 그대로. 각주는 각주 번호가 있는 화면 끝에 [^n]: 로 (전자책의 '각주' 장은 따로 두지 않음)
"""
import html, json, os, re, sys, zipfile
from PIL import Image

epub = sys.argv[1]; bk = 'DL-0013'
z = zipfile.ZipFile(epub)
opf = z.read('OEBPS/content.opf').decode()
items = dict(re.findall(r'<item id="([^"]+)" href="([^"]+)"', opf))
spine = [items[i] for i in re.findall(r'<itemref idref="([^"]+)"', opf)]
ncx = z.read('OEBPS/toc.ncx').decode()
NAMES = {src: t for t, src in re.findall(r'<text>(.*?)</text>\s*</navLabel>\s*<content src="([^"#]+)', ncx)}


def text(s):
    s = re.sub(r'\s*\n\s*', ' ', s)
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<sup>\s*<a[^>]*class="s_no"[^>]*>(\d+)</a>\s*</sup>', r'[^\1]', s)
    s = re.sub(r'<span class="emphasis">(.*?)</span>', lambda m: '**' + m.group(1).strip() + '**', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return '\n'.join(re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n')).strip()


# 각주 내용
FN = {}
fs = z.read('OEBPS/Text/footnotes.xhtml').decode()
for n, t in re.findall(r'<a id="q(\d+)" class="q_no"[^>]*>\d+</a>(.*?)</p>', fs, re.S):
    FN[n] = text(t)

saved, imgs = set(), []


def image(name):
    stem = os.path.splitext(name)[0]
    path = f'public/uploads/{bk}-{stem}.jpg'
    if path not in saved:
        open('/tmp/_i', 'wb').write(z.read('OEBPS/Images/' + name))
        im = Image.open('/tmp/_i').convert('RGB')
        im.thumbnail((1000, 1000))
        im.save(path, quality=78, optimize=True); saved.add(path)
    url = '/' + path.replace('public/', ''); imgs.append(url)
    return f'![#{"속표지" if name == "1.jpg" else "그림"}]({url})'


BOLD = ('title1', 'body12', 'body13', 'emphasis', 'weight7')
TAG = re.compile(r'<table.*?</table>|<h\d[^>]*>.*?</h\d>|<p[^>]*>.*?</p>|<p[^>]*/>|<image[^>]*>|<img[^>]*>', re.S)
pages, toc = [], []
for href in spine:
    if href in ('Text/cover.xhtml', 'Text/footnotes.xhtml'):
        continue
    s = z.read('OEBPS/' + href).decode()
    body = re.search(r'<body[^>]*>(.*)</body>', s, re.S).group(1)
    paras, group, gcenter = [], [], False
    subs, refs = [], []

    def flush():
        global group
        if group: paras.append((':: ' if gcenter else '') + '\n'.join(group)); group = []

    for m in TAG.finditer(body):
        tag = m.group(0); cls = (re.search(r'class="([^"]*)"', tag) or [None, ''])[1]
        if tag.startswith('<table'):  # 빨리어 용어 해설: 낱말 + 풀이
            flush()
            term = text(re.search(r'<h\d[^>]*>(.*?)</h\d>', tag, re.S).group(1))
            defs = [l for x in re.findall(r'<p[^>]*>(.*?)</p>', tag, re.S) for l in text(x).split('\n') if l.strip()]
            paras.append('**' + term + '**\n' + '\n'.join(defs)); continue
        if tag.startswith('<im'):
            flush(); paras.append(image(os.path.basename(re.search(r'(?:xlink:href|src)="([^"]+)"', tag).group(1)))); continue
        t = '' if tag.endswith('/>') else text(re.sub(r'^<(h\d|p)[^>]*>|</(h\d|p)>$', '', tag, flags=re.S))
        refs += re.findall(r'\[\^(\d+)\]', t)
        if not t:  # 빈 줄: 묶음 끝
            flush(); continue
        if tag.startswith('<h') or 'title2' in cls:
            flush()
            if paras and paras[-1].startswith('## ') and 'title2' in cls and t.startswith('('):
                paras[-1] += ' ' + t; continue  # '1. 사띠빳타나 수행' + '(Satipaṭṭhāna)'
            paras.append('## ' + t)
            if href == 'Text/attitude.xhtml': subs.append(t)
            continue
        if 'body1' == cls:
            flush(); paras.append('## ' + t); subs.append(t); continue
        bold = any(c in cls.split() for c in BOLD) and '**' not in t
        line = '**' + t.replace('\n', '**\n**') + '**' if bold else t
        center = 'text-align: center' in tag[:200]
        lined = cls.split()[0] in ('title1', 'body12', 'body13', 'size08') if cls else False
        if lined:  # 줄마다: 빈 줄이 나올 때까지 한 묶음
            if group and gcenter != center: flush()
            gcenter = center; group.append(line); continue
        flush(); paras.append(line)
    flush()
    for n in refs:
        paras.append(f'[^{n}]: ' + FN.pop(n))
    if href in NAMES:
        toc.append({'title': NAMES[href], 'page': len(pages) + 1, 'sub': False})
    elif not pages:
        raise SystemExit('첫 화면 장 이름 없음')
    for t in subs:
        toc.append({'title': t, 'page': len(pages) + 1, 'sub': True, 'at': t[:12]})
    pages.append('\n\n'.join(paras))

if FN: raise SystemExit('본문에 없는 각주: ' + ', '.join(FN))
body = ''.join(f'=== ===\n{p}\n\n' for p in pages).rstrip() + '\n'
json.dump({'book': bk, 'edition': '초판', 'toc': toc, 'images': [{'image': u, 'caption': ''} for u in dict.fromkeys(imgs)], 'body': body},
          open(f'content/texts/{bk}.json', 'w'), ensure_ascii=False, indent=2)
open(f'content/texts/{bk}.json', 'a').write('\n')
print(len(pages), '화면', len(set(imgs)), '그림', [t['title'] for t in toc if not t['sub']])
