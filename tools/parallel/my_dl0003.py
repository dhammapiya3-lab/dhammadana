"""DL-0003『행복을 찾아서』 미얀마어 원서 『ချမ်းသာကို ရှာဖွေခြင်း』(ဦးရွှေအောင်, ရာပြည့်စာအုပ်တိုက် 4쇄 2004) 글 → 원서 문단 목록
(운영자 요청, 2026-11-18)

원서 PDF(스캔본 109쪽, 한 PDF 쪽에 책 두 쪽, 글자층 없음)는 쪽 그림을 보며 옮겨 적은 tools/parallel/dl0003_my/ 가 원서 글이다.
스캔이 쪽 가장자리를 자른 곳은 같은 글의 1995년 초판(နှလုံးလှစာပေ) 스캔으로 채움 — 쪽마다 _notes.txt.
  NNN.txt  = 책 NNN쪽 (PDF 쪽 = (NNN+6)//2, 짝수 쪽 왼쪽·홀수 쪽 오른쪽)
  f*.txt   = 앞쪽(저자 소개·속표지·판권·차례·그림 설명) — 둘째 줄 'pdf N'
옮겨 적은 파일 모양:
  '@ N'  책 쪽 번호(빈칸이면 번호 없는 쪽),  '## ' 제목,  '>> ' 오른쪽·위 작은 글,  '❋' 구분,  '%% ' 차례 줄
  빈 줄  문단 나눔,  '+' 앞 쪽 문단에 이어짐(빈칸 하나),  '+-' 앞 쪽 문단에 낱말 가운데에서 이어짐(빈칸 없이)

  python3 tools/parallel/my_dl0003.py
  → tools/out/parallel/DL-0003.my.paras.json (align.py 입력)
  → tools/out/parallel/DL-0003_미얀마어_원서.txt (운영자에게 보내는 글 파일, 사이트에는 올리지 않음)
"""
import os, re, json, glob
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'tools/parallel/dl0003_my')
OUT = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(OUT, exist_ok=True)
MY2A = str.maketrans('၀၁၂၃၄၅၆၇၈၉', '0123456789')

front = ['f1', 'f2', 'f3', 'f4', 'f4b', 'f4c', 'f5']
files = [os.path.join(SRC, f + '.txt') for f in front] + sorted(glob.glob(os.path.join(SRC, '[0-9][0-9][0-9].txt')))
PQ = {'f3', 'f5'}   # 판권 면·그림 설명 — 한국어판에 없음, 짝짓기에서 뺌

orig, txt_out = [], []
for f in files:
    name = os.path.basename(f)[:-4]
    lines = open(f, encoding='utf-8').read().split('\n')
    pg = lines[0][1:].strip().translate(MY2A); lines = lines[1:]
    if lines and lines[0].startswith('pdf '):
        pdf = int(lines[0][4:]); lines = lines[1:]
    else:
        pdf = (int(name) + 6) // 2
    body = '\n'.join(lines).strip()
    txt_out.append(f"=== {pg + '쪽' if pg else '번호 없는 쪽'} (PDF {pdf}쪽) ===")
    for para in re.split(r'\n\s*\n', body):
        para = para.strip()
        if not para: continue
        if para.startswith('+'):
            nosp = para.startswith('+-')
            t = para[2:].strip() if nosp else para[1:].strip()
            orig[-1]['t'] += ('' if nosp else ' ') + t
            txt_out.append(('(앞 쪽에서 이어짐, 낱말 가운데) ' if nosp else '(앞 쪽에서 이어짐) ') + t)
            continue
        if para.startswith('%% '):
            for l in para.split('\n'):
                l = l[3:].strip()
                orig.append({'pg': pg, 'pdf': str(pdf), 'k': 'toc', 't': l}); txt_out.append(l)
            continue
        k, t = 'p', para
        if para.startswith('## '): k, t = 'h', para[3:].strip()
        elif para == '❋': k = 'sep'
        elif para.startswith('>> '): t = para[3:].strip()
        if name in PQ: k = 'pq'
        if name == 'f2' and k == 'p' and t != 'ဦးရွှေအောင်': k = 'pq'   # 속표지의 총서 번호·출판사 글 — 한국어 속표지에 없음
        orig.append({'pg': pg, 'pdf': str(pdf), 'k': k, 't': t}); txt_out.append(t)

json.dump(orig, open(os.path.join(OUT, 'DL-0003.my.paras.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
open(os.path.join(OUT, 'DL-0003_미얀마어_원서.txt'), 'w', encoding='utf-8').write(
    'ချမ်းသာကို ရှာဖွေခြင်း — ဦးရွှေအောင်\n'
    '미얀마어 원서 (ရာပြည့်စာအုပ်တိုက် 4쇄, 2004년 11월) — 스캔본 쪽 그림을 보며 옮겨 적은 글. '
    '스캔이 가장자리를 자른 곳은 1995년 초판(နှလုံးလှစာပေ)으로 채움. 쪽 표시: 책 쪽 (PDF 쪽)\n\n'
    + '\n\n'.join(txt_out) + '\n')
from collections import Counter
print('원서 문단', len(orig), dict(Counter(p['k'] for p in orig)))
