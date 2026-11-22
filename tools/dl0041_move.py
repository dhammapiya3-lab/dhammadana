#!/usr/bin/env python3
"""『테라와다 불교의 신행생활』(DL-0041) 단락 옮기기·소제목 더하기 (운영자 요청, 2026-11-22).

2015년 판(새 한글 파일)처럼:
- 17장 까티나 가사 법요식 157~159쪽의 사원 운영 방침 단락들('테라와다 불교의 사원은 제대로 된 규칙…'
  ~ '…사원이 유지 운영해 나갈 수가 있게 되는 것입니다.')을 15장 '(3) 거주처' 끝, '## (4) 의약품' 바로 앞으로 옮김.
  쪽 표시(=== 158쪽 === 등)는 제자리에 두고 글만 옮김(글자는 그대로).
- 소제목 셋을 더함: '1) 사원 구성과 좌와구(坐臥具)'('## (3) 거주처' 바로 뒤), '2) 사원 건립 목적과 과정'
  ('이제 사원을 건설한 목적에 대해서' 앞), '3) 테라와다 불교에서의 사원 운영 방침'(옮긴 단락 앞).
쓰는 법: python3 tools/dl0041_move.py [--write]   (두 번 돌려도 같음 — 이미 옮겼으면 '이미 옮김')
hwp2text_dl0041.py → split_chapters.py → dl0041_fix.py 다음에 돌린다.
"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(ROOT, 'content/texts/DL-0041.json')
H1 = '## 1) 사원 구성과 좌와구(坐臥具)'
H2 = '## 2) 사원 건립 목적과 과정'
H3 = '## 3) 테라와다 불교에서의 사원 운영 방침'
A = '테라와다 불교의 사원은 제대로 된 규칙'
Z = '사원이 유지 운영해 나갈 수가 있게 되는 것입니다.'

def run(b):
    if H3 in b:
        return b, '이미 옮김'
    i = b.index('\n\n' + A) + 2
    j = b.index(Z, i) + len(Z)
    seg = b[i:j]
    marks = re.findall(r'\n=== [^\n]*===\n', '\n' + seg + '\n')
    text = re.sub(r'\n*=== [^\n]*===\n*', '\n\n', seg).strip()
    keep = ''.join(m.strip() + '\n' for m in marks)          # 쪽 표시는 제자리에
    b = b[:i] + keep + b[j:].lstrip('\n')
    b = re.sub(r'\n{3,}', '\n\n', b)
    k = b.index('\n\n## (4) 의약품')
    b = b[:k] + '\n\n' + H3 + '\n\n' + text + b[k:]
    k = b.index('## (3) 거주처'); k = b.index('\n', k)
    b = b[:k] + '\n\n' + H1 + b[k:]
    k = b.index('\n\n이제 사원을 건설한 목적에 대해서')
    b = b[:k] + '\n\n' + H2 + b[k:]
    return b, '옮김'

def plain(x):
    x = re.sub(r'^=== [^\n]*===$', '', x, flags=re.M)
    return re.sub(r'\s', '', x)

if __name__ == '__main__':
    d = json.load(open(TXT)); b0 = d['body']
    b1, st = run(b0)
    print(st)
    if st == '옮김':
        add = plain(H1 + H2 + H3).replace('#', '')
        a = sorted(plain(b0).replace('#', '')); c = sorted(plain(b1).replace('#', ''))
        extra = sorted(add)
        from collections import Counter
        diff = Counter(c) - Counter(a); miss = Counter(a) - Counter(c)
        ok = diff == Counter(extra) and not miss
        print('글자 대조(더한 소제목 말고 같음):', ok)
        print('쪽 표시 수:', len(re.findall(r'^=== ', b0, re.M)), '→', len(re.findall(r'^=== ', b1, re.M)))
        if not ok: sys.exit('글자가 다름')
        if '--write' in sys.argv:
            d['body'] = b1; open(TXT, 'w').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n'); print('썼음')
