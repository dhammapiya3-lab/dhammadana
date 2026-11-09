#!/usr/bin/env python3
"""학습 자료실 파일 → 본문 글(.txt) + Claude 가 정보를 읽어 낼 앞·뒤 쪽 발췌.

쓰는 법:  python3 tools/study_ingest.py 파일1.pdf [파일2.epub 파일3.hwp ...] [--out tools/out/study]

파일마다 <out>/<이름>/ 에
  text.txt   : 본문 글 (PDF 는 '=== N쪽 ===' 쪽 표시 포함) → 학습 자료실 _text/<자료ID>.txt 로 올림
  head.txt   : 정보 파악용 — 앞 10쪽 + 뒤 3쪽 (속표지·판권지·차례·머리말)
  cover.jpg  : PDF 첫 쪽 그림 (표지로 쓸 수 있음)
  report.json: 쪽 수, 글자 수, OCR 한 쪽, 깨진 글자 경고
를 만든다. 이 결과는 비공개 자료이므로 GitHub 에 올리지 않는다 (tools/out 은 .gitignore).

- PDF: 글자층이 있으면 그대로, 쪽에 글자가 거의 없으면 tesseract(kor+eng) 로 글자 인식(OCR).
- EPUB: 장(xhtml)마다 글만.  HWP: hwp5txt.  HWPX·DOCX: 안의 XML 글.  TXT·MD: 그대로.
"""
import sys, os, re, json, zipfile, subprocess, unicodedata, html

def norm(t):
    t = unicodedata.normalize('NFC', t).replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'[ \t ]+\n', '\n', t)
    return re.sub(r'\n{3,}', '\n\n', t).strip()

def broken(t):
    """깨진 글자: 대체 문자(�), 사용자 정의 영역(옛 빠알리 글꼴), 제어 문자"""
    out = {}
    for ch in t:
        o = ord(ch)
        if ch == '�' or 0xE000 <= o <= 0xF8FF or (o < 32 and ch not in '\n\t'):
            out[f'U+{o:04X}'] = out.get(f'U+{o:04X}', 0) + 1
    return out

def pdf(path, d):
    import pymupdf
    doc = pymupdf.open(path); pages, ocr = [], []
    for i, pg in enumerate(doc):
        t = pg.get_text('text', sort=True)
        if len(re.sub(r'\s', '', t)) < 15 and (pg.get_images() or pg.get_drawings()):
            pix = pg.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
            img = os.path.join(d, f'_ocr_{i+1}.png'); pix.save(img)
            r = subprocess.run(['tesseract', img, '-', '-l', 'kor+eng', '--psm', '6'], capture_output=True, text=True)
            os.remove(img); t = r.stdout
            if len(re.sub(r'\s', '', t)) >= 15: ocr.append(i + 1)
        pages.append(norm(t))
    try:
        pix = doc[0].get_pixmap(dpi=110); pix.save(os.path.join(d, 'cover.jpg'))
    except Exception:
        pass
    body = '\n\n'.join(f'=== {i+1}쪽 ===\n{p}' for i, p in enumerate(pages))
    head = '\n\n'.join(f'=== {i+1}쪽 ===\n{p}' for i, p in enumerate(pages) if i < 10 or i >= len(pages) - 3)
    return body, head, {'pages': len(pages), 'ocr_pages': ocr}

def xml_text(x):
    x = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', x, flags=re.S | re.I)
    x = re.sub(r'</(p|div|h\d|li|tr|hp:p|w:p)>|<br\s*/?>', '\n', x, flags=re.I)
    return html.unescape(re.sub(r'<[^>]+>', '', x))

def epub(path):
    z = zipfile.ZipFile(path)
    opf = next(n for n in z.namelist() if n.endswith('.opf'))
    o = z.read(opf).decode('utf-8', 'ignore'); base = os.path.dirname(opf)
    man = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', o))
    man.update({a: b for b, a in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', o)})
    order = re.findall(r'<itemref[^>]*idref="([^"]+)"', o)
    parts = []
    for i in order:
        h = man.get(i)
        if not h: continue
        try: parts.append(norm(xml_text(z.read(os.path.normpath(os.path.join(base, h)).replace('\\', '/')).decode('utf-8', 'ignore'))))
        except KeyError: pass
    meta = norm(xml_text(o.split('<manifest')[0]))
    body = '\n\n'.join(p for p in parts if p)
    return body, ('[EPUB 정보]\n' + meta + '\n\n' + body[:12000] + '\n…\n' + body[-3000:]), {'chapters': len(parts)}

def hwp(path):
    r = subprocess.run(['hwp5txt', path], capture_output=True, text=True)
    body = norm(r.stdout)
    return body, body[:12000] + '\n…\n' + body[-3000:], {'hwp5txt_error': r.stderr[-300:] if r.returncode else ''}

def zipxml(path, pat):
    z = zipfile.ZipFile(path)
    names = sorted(n for n in z.namelist() if re.search(pat, n))
    body = norm('\n\n'.join(xml_text(z.read(n).decode('utf-8', 'ignore')) for n in names))
    return body, body[:12000] + '\n…\n' + body[-3000:], {'parts': len(names)}

def main():
    a = sys.argv[1:]; out = 'tools/out/study'
    if '--out' in a: i = a.index('--out'); out = a[i + 1]; del a[i:i + 2]
    for path in a:
        name = re.sub(r'[^\w가-힣.-]+', '_', os.path.splitext(os.path.basename(path))[0])
        d = os.path.join(out, name); os.makedirs(d, exist_ok=True)
        ext = path.lower().rsplit('.', 1)[-1]
        if ext == 'pdf': body, head, info = pdf(path, d)
        elif ext == 'epub': body, head, info = epub(path)
        elif ext == 'hwp': body, head, info = hwp(path)
        elif ext == 'hwpx': body, head, info = zipxml(path, r'Contents/section\d+\.xml$')
        elif ext == 'docx': body, head, info = zipxml(path, r'word/document\.xml$')
        elif ext in ('txt', 'md'): body = norm(open(path, encoding='utf-8', errors='ignore').read()); head, info = body[:12000], {}
        else: print('건너뜀(글이 없는 형식):', path); continue
        open(os.path.join(d, 'text.txt'), 'w').write(body + '\n')
        open(os.path.join(d, 'head.txt'), 'w').write(head + '\n')
        chars = len(re.sub(r'\s', '', re.sub(r'=== \d+쪽 ===', '', body)))
        rep = {'file': os.path.basename(path), 'chars': chars, 'broken_chars': broken(body), **info}
        json.dump(rep, open(os.path.join(d, 'report.json'), 'w'), ensure_ascii=False, indent=1)
        print(json.dumps(rep, ensure_ascii=False))

if __name__ == '__main__':
    main()
