#!/usr/bin/env python3
"""온라인 읽기 manifest.json → 관리자 화면에서 고칠 수 있는 글 파일(content/texts/<자료번호>.json)

쓰는 법: python3 tools/manifest2text.py tools/out/reader/DL-0007/개정판/manifest.json [--header "쪽 머리글 글자"]
본문은 '=== 12쪽 ===' 줄로 쪽을 나누고, 문단은 빈 줄로 나눕니다.
글자는 바꾸지 않고, 읽기 좋게 문단 나눔·순서만 정리합니다.
  1) 목차 제목(소제목)이 앞뒤 문단에 붙어 있으면 따로 떼어 한 문단으로 둡니다 (읽기 화면에서 굵게 보임).
  2) 각주 문단([^번호]: …)은 그 쪽 끝으로 모읍니다 (책처럼 쪽 아래에).
  3) --header 를 주면 '머리글 쪽번호' 꼴의 쪽 머리글 문단을 뺍니다.
"""
import argparse, json, os, re
ap = argparse.ArgumentParser()
ap.add_argument('manifest'); ap.add_argument('--header', default='')
a = ap.parse_args()
m = json.load(open(a.manifest, encoding='utf-8'))
book, ed = m['book'], m['edition']
toc = [{'title': t['title'].strip(), 'page': t['page'], 'sub': t['title'].startswith(' ')} for t in m.get('toc', [])]
FN = re.compile(r'^\[\^\d+\]:')

def split_heads(paras, titles):
    out = []
    for q in paras:
        done = False
        for t in titles:
            if q.strip() == t or t not in q or len(q) <= len(t): continue
            i = q.find(t); before, after = q[:i].rstrip(), q[i + len(t):].lstrip()
            # 제목이 문단 처음/끝에 붙어 있을 때만 (문장 속 우연한 같은 말은 건드리지 않음)
            if before and not re.search(r'[.?!”’)\]]$', before): continue
            out += [x for x in (before, t, after) if x]; done = True; break
        if not done: out.append(q)
    return out

parts = []
for i, p in enumerate(m['pages']):
    label = p.get('label') or str(i + 1)
    paras = [x for x in (p.get('text') or '').strip().split('\n\n') if x.strip()]
    if a.header: paras = [x for x in paras if x.strip() != f'{a.header} {label}']
    paras = split_heads(paras, [t['title'] for t in toc if t['page'] == i + 1])
    paras = [x for x in paras if not FN.match(x)] + [x for x in paras if FN.match(x)]
    parts.append(f'=== {label}쪽 ===\n' + '\n\n'.join(paras))
out = {'book': book, 'edition': ed, 'toc': toc, 'body': '\n\n'.join(parts) + '\n'}
dst = os.path.join(os.path.dirname(__file__), '..', 'content', 'texts', f'{book}.json')
with open(dst, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2); f.write('\n')
print('만듦:', os.path.normpath(dst), f'({len(m["pages"])}쪽, 목차 {len(toc)}개)')
