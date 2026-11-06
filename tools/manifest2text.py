#!/usr/bin/env python3
"""온라인 읽기 manifest.json → 관리자 화면에서 고칠 수 있는 글 파일(content/texts/<자료번호>.json)

쓰는 법: python3 tools/manifest2text.py tools/out/reader/DL-0007/개정판/manifest.json
본문은 '=== 12쪽 ===' 줄로 쪽을 나누고, 문단은 빈 줄로 나눕니다.
"""
import json, os, sys
src = sys.argv[1]
m = json.load(open(src, encoding='utf-8'))
book, ed = m['book'], m['edition']
parts = []
for i, p in enumerate(m['pages']):
    label = p.get('label') or str(i + 1)
    parts.append(f'=== {label}쪽 ===\n' + (p.get('text') or '').strip())
out = {
    'book': book,
    'edition': ed,
    'toc': [{'title': t['title'].strip(), 'page': t['page'], 'sub': t['title'].startswith(' ')} for t in m.get('toc', [])],
    'body': '\n\n'.join(parts) + '\n',
}
dst = os.path.join(os.path.dirname(__file__), '..', 'content', 'texts', f'{book}.json')
with open(dst, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2); f.write('\n')
print('만듦:', os.path.normpath(dst), f'({len(m["pages"])}쪽, 목차 {len(out["toc"])}개)')
