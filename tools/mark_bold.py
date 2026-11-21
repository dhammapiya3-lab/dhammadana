#!/usr/bin/env python3
"""인쇄본(PDF)에서 굵게 강조된 글자를 찾아 글로 읽기 본문(content/texts/<ID>.json)에 **굵게** 표시합니다.

  python3 tools/mark_bold.py DL-0001 책.pdf            # 미리 보기 (바꾸지 않음)
  python3 tools/mark_bold.py DL-0001 책.pdf --write    # 본문에 적용

- 굵은 글꼴: 이름에 Bold·Heavy·Black·SemiBold·ExtraBold 가 있거나 PB/B 로 끝나는 글꼴 (Medium 은 뺌)
- 소제목(## 줄)·쪽 번호·머리글·각주 번호(8pt 미만)는 건드리지 않음
- 본문 쪽과 PDF 쪽의 차이(앞 속표지 등)는 저절로 맞춤
- 이미 ** 로 감싼 곳은 그대로 둠. 찾지 못한 굵은 글은 끝에 알려 줌
"""
import json, re, sys, warnings
warnings.filterwarnings('ignore')
import fitz

BOLD = re.compile(r'(Bold|Heavy|Black|SemiBold|ExtraBold|Demi|PB$|[a-z]B$|GulimB$)')
SKIP_TXT = re.compile(r'^[\d\s.,·:;()\[\]\-–—|*]+$')


def bold_runs(page, body_size):
    """쪽에서 굵은 글 덩어리들 (읽는 차례대로). 본문보다 큰 짧은 굵은 글(장 제목 등)은 뺌."""
    runs, cur, big, csz = [], '', False, 0
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text']
                if not t.strip():
                    continue
                if BOLD.search(s['font']) and 'Medium' not in s['font'] and s['size'] >= 8:
                    if cur.strip() and abs(s['size'] - csz) > 1:  # 글자 크기가 다르면 (제목·쪽 번호) 따로
                        runs.append((cur, big)); cur, big = '', False
                    if not cur.strip():
                        csz = s['size']
                    cur += t; big = big or s['size'] > body_size * 1.15
                else:
                    if cur.strip():
                        runs.append((cur, big))
                    cur, big = '', False
        # 블록이 바뀌어도 이어진 굵은 글은 한 덩어리로 둠 (줄 바꿈)
    if cur.strip():
        runs.append((cur, big))
    return [r for r, bg in runs if not SKIP_TXT.match(r) and not (bg and len(norm(r)) < 20)]


TOKEN = re.compile(r'\[\^\d+\]:?|\*\*|^## |!\[[^\]]*\]\([^)]*\)', re.M)


def index_chars(text):
    """공백·각주 표시·** 를 뺀 글자들과 그 원래 위치."""
    chars, pos, i = [], [], 0
    skip = {}
    for m in TOKEN.finditer(text):
        skip[m.start()] = m.end()
    while i < len(text):
        if i in skip:
            i = skip[i]
            continue
        if not text[i].isspace():
            chars.append(text[i]); pos.append(i)
        i += 1
    return ''.join(chars), pos


def norm(s):
    return re.sub(r'\s+', '', s)


def main():
    bk, pdf = sys.argv[1], sys.argv[2]
    write = '--write' in sys.argv
    f = f'content/texts/{bk}.json'
    d = json.load(open(f))
    body = d['body']
    parts = re.split(r'(^=== .*? ===$)', body, flags=re.M)
    # parts: [앞, 표시1, 쪽1, 표시2, 쪽2, ...]
    pages = parts[2::2]
    doc = fitz.open(pdf)
    import collections
    sz = collections.Counter()
    for p in doc:
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    sz[round(s['size'], 1)] += len(s['text'].strip())
    body_size = sz.most_common(1)[0][0]
    pdf_runs = [bold_runs(p, body_size) for p in doc]
    # 쪽 차이 맞추기: PDF 쪽 글의 앞부분이 본문 쪽에 들어 있는지로
    heads = []
    for p in doc:
        t = norm(p.get_text())[:12]
        heads.append(t)
    best = (0, -1)
    for off in range(-3, 4):
        hit = 0
        for i, pg in enumerate(pages):
            j = i + off
            if 0 <= j < len(heads) and len(heads[j]) >= 6 and heads[j][:6] in index_chars(pg)[0]:
                hit += 1
        if hit > best[1]:
            best = (off, hit)
    off = best[0]
    added, missing, examples = 0, [], []
    for i, pg in enumerate(pages):
        j = i + off
        if not (0 <= j < len(pdf_runs)) or not pdf_runs[j]:
            continue
        spans = []  # (원래 시작, 원래 끝)
        n, pos = index_chars(pg)
        start = 0
        for r in pdf_runs[j]:
            key = norm(r)
            k = n.find(key, start)
            if k < 0:
                k = n.find(key)
            if k < 0:
                missing.append((pg_label(parts, i), r.strip()[:40]))
                continue
            start = k + len(key)
            a, b = pos[k], pos[k + len(key) - 1] + 1
            spans.append((a, b))
        # 가까이 붙은 덩어리(따옴표·장음 표시 '-' 하나 사이)는 하나로 합침
        merged = []
        for a, b in sorted(set(spans)):
            if merged and 0 <= a - merged[-1][1] <= 2 and '\n' not in pg[merged[-1][1]:a]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        # 겹치지 않게, 문단·소제목 경계로 나눔
        out, last = '', 0
        for a, b in merged:
            if a < last:
                continue
            seg = pg[a:b]
            pieces, p0 = [], a
            for m in re.finditer(r'\n\s*\n|\n(?=## )|\n(?=\[\^\d+\]:)', seg):
                pieces.append((p0, a + m.start())); p0 = a + m.end()
            pieces.append((p0, b))
            out += pg[last:a]; cur = a
            for x, y in pieces:
                line_start = pg.rfind('\n', 0, x) + 1
                para_start = max(pg.rfind('\n\n', 0, x) + 2, 0) if pg.rfind('\n\n', 0, x) >= 0 else 0
                if pg.startswith('## ', line_start) or pg.startswith('## ', para_start) or pg[x:y].strip() == '':
                    out += pg[cur:y]; cur = y; continue
                # 이미 굵게면 그대로
                if pg[max(0, x - 2):x] == '**' and pg[y:y + 2] == '**':
                    out += pg[cur:y]; cur = y; continue
                inner = pg[x:y].replace('**', '')
                out += pg[cur:x] + '**' + inner + '**'; cur = y; added += 1
                if len(examples) < 400:
                    examples.append((pg_label(parts, i), inner.replace('\n', '⏎')[:60]))
            out += pg[cur:b]; last = b
        out += pg[last:]
        pages[i] = out
    parts[2::2] = pages
    new = ''.join(parts)
    print(f'{bk}: PDF 쪽 차이 {off:+d}, 굵게 {added}곳, 찾지 못함 {len(missing)}곳')
    for e in examples:
        print('  +', e[0], e[1])
    for m in missing:
        print('  ?', m[0], m[1])
    if write:
        if re.sub(r'\*\*', '', new) != re.sub(r'\*\*', '', body):
            sys.exit('글자가 달라졌습니다. 적용하지 않습니다.')
        d['body'] = new
        json.dump(d, open(f, 'w'), ensure_ascii=False, indent=2)
        open(f, 'a').write('\n') if open(f).read()[-1] != '\n' else None
        print('적용했습니다:', f)


def pg_label(parts, i):
    return parts[1 + 2 * i].strip('= ').strip()


if __name__ == '__main__':
    main()
