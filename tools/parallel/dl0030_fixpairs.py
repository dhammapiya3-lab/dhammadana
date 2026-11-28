#!/usr/bin/env python3
"""DL-0030『붓다의 일생』 원서 대조 — 짝짓기(align.py) 뒤 문장 짝 몇 곳을 손으로 다시 나눔 (운영자 요청, 2026-11-28).
손 짝(--spin)으로 정하면 둘레 문장들이 한 칸씩 밀려 이 도구로 그 묶음 안의 한국어 조각만 옮김. 두 번 돌려도 같음.
  python3 tools/parallel/dl0030_fixpairs.py      (run_dl0030.sh 끝에서 저절로 부름)
① 310쪽 범천 바까 경: '물을 … 신들을 …' ↔ 'Having had … gods ….', '조물주를 … 승자천(무상유정)을 ….' ↔ 'Pajāpati … (Abhibhū) …'
② 90쪽 감흥어: '세존께서는 그 뜻을 아시고 감흥하여 읊으셨다.' ↔ 'Knowing the meaning …' 과 게송 첫 줄 짝을 따로"""
import json, os, re
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = os.path.join(REPO, 'content/parallel/DL-0030.en.json')
def paras(t): return ['\n'.join(l.strip() for l in s.strip().split('\n')) for s in re.split(r'\n\s*\n', t or '') if s.strip()]
def keys(body):
    pages = []
    for m in re.finditer(r'^===\s*(.*?)\s*===\s*$', body, flags=re.M): pages.append([m.group(1), m.end()])
    for i, p in enumerate(pages):
        end = pages[i + 1][1] - len(re.search(r'===[^\n]*===\s*$', body[:pages[i + 1][1]]).group(0)) if i + 1 < len(pages) else len(body)
        p.append(body[p[1]:end].strip())
    return {f'{n}:{s}': t for n, (_, _, txt) in enumerate(pages, 1) for s, t in enumerate(paras(txt))}
B = keys(json.load(open(os.path.join(REPO, 'content/texts/DL-0030.json')))['body'].replace('\r\n', '\n'))
raw = open(F).read(); D = json.loads(raw); O = D['orig']
def kt(r): return re.sub(r'^(\+\+ )?(\*\*)?', '', B[r[0]][r[1]:r[2]])
def ot(r): return O[r[0]]['t'][r[1]:r[2]]
done = []
for g in D['groups']:
    S = g.get('s', [])
    for i, s in enumerate(S):
        # ①
        if s['or'] and ot(s['or'][0]).startswith('Having had direct knowledge of water') and i + 1 < len(S) and S[i + 1]['or'] and ot(S[i + 1]['or'][0]).startswith('Pajāpati'):
            a, b = s, S[i + 1]; c = S[i + 2] if i + 2 < len(S) else None
            mv = [r for r in b['ko'] if kt(r).startswith('존재들을')]
            for r in mv: b['ko'].remove(r); a['ko'].append(r)
            if c and c['or'] and ot(c['or'][0]).startswith('Having had direct knowledge of all'):
                mv2 = [r for r in c['ko'] if kt(r).startswith('광과천을')]
                for r in mv2: c['ko'].remove(r); b['ko'].append(r)
            done.append('①')
        # ②
        if len(s['ko']) == 2 and len(s['or']) == 2 and kt(s['ko'][0]).startswith('세존께서는 그 뜻을 아시고 감흥하여') and kt(s['ko'][1]).startswith('“완전히 떠남') \
           and ot(s['or'][0]).startswith('Knowing the meaning') and ot(s['or'][1]).startswith('Seclusion is happiness'):
            S[i:i + 1] = [{**s, 'ko': [s['ko'][0]], 'or': [s['or'][0]]}, {**s, 'ko': [s['ko'][1]], 'or': [s['or'][1]]}]
            done.append('②')
ind = re.match(r'\{\n( *)"', raw); ind = len(ind.group(1)) if ind else None
open(F, 'w').write(json.dumps(D, ensure_ascii=False, indent=ind, separators=None if ind else (',', ':')) + ('\n' if raw.endswith('\n') else ''))
print('DL-0030 손으로 다시 나눈 곳:', ' '.join(done) or '없음(이미 고침)')
