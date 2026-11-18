"""DL-0010『마음가짐이 바르게 되었을 때 수행하십시오』 미얀마어 원서 『သဘောထားမှန်မှ အားထုတ်ပါ』 글 → 원서 문단 목록
(운영자 요청, 2026-11-18)

원서 PDF(스캔본 138쪽, 글자층 없음)는 쪽 그림을 보며 옮겨 적은 tools/parallel/dl0010_my/NNN.txt 가 원서 글이다
(NNN = PDF 쪽). 옮겨 적은 파일 모양:
  '@ N'    원서 책 쪽 번호(빈칸이면 번호 없는 쪽)
  '## '    제목,  '>> ' 서명·출전,  '❋' 구분 꽃무늬,  '%% ' 차례 줄
  빈 줄    문단 나눔,  '+' 로 시작하는 줄은 앞 쪽에서 이어지는 문단
책 쪽 n = PDF 쪽 n + 6.

  python3 tools/parallel/my_dl0010.py
  → tools/out/parallel/DL-0010.my.paras.json (align.py 입력)
  → tools/out/parallel/သဘောထားမှန်မှ အားထုတ်ပါ__AI 필사.txt (운영자에게 보내는 글 파일, 사이트에는 올리지 않음)
"""
import os, re, json, glob
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'tools/parallel/dl0010_my')
OUT = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(OUT, exist_ok=True)
MYD = str.maketrans('0123456789', '၀၁၂၃၄၅၆၇၈၉')

orig = []
txt_out = []
for f in sorted(glob.glob(os.path.join(SRC, '[0-9][0-9][0-9].txt'))):
    pdf = int(os.path.basename(f)[:3])
    lines = open(f, encoding='utf-8').read().split('\n')
    pg = lines[0][1:].strip() if lines[0].startswith('@') else ''
    body = '\n'.join(lines[1:] if lines[0].startswith('@') else lines).strip()
    txt_out.append(f"=== {pg + '쪽' if pg else '번호 없는 쪽'} (PDF {pdf}쪽) ===")
    for para in re.split(r'\n\s*\n', body):
        para = para.strip()
        if not para: continue
        if para.startswith('+'):
            t = para[1:].strip()
            orig[-1]['t'] += ('' if orig[-1]['t'].endswith(('၊', '။')) is False else ' ') + t
            txt_out.append(t); continue
        if para.startswith('%% '):
            for l in para.split('\n'):
                l = l[3:].strip()
                k = 'pq' if l.startswith('စဉ် ') else 'toc'   # 차례 머리 줄(차례·내용·쪽)은 짝짓지 않음
                orig.append({'pg': pg, 'pdf': str(pdf), 'k': k, 't': l}); txt_out.append(l)
            continue
        k, t = 'p', para
        if para.startswith('## '): k, t = 'h', para[3:].strip()
        elif para == '❋': k = 'sep'
        elif para.startswith('>> '): t = para[3:].strip()
        if pdf >= 136: k = 'pq'   # 책 끝 레디 사야도 게송(한국어판에 없음) — 원서 글에는 두고 짝짓기에서는 뺌
        orig.append({'pg': pg, 'pdf': str(pdf), 'k': k, 't': t}); txt_out.append(t)

json.dump(orig, open(os.path.join(OUT, 'DL-0010.my.paras.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
open(os.path.join(OUT, 'သဘောထားမှန်မှ အားထုတ်ပါ__AI 필사.txt'), 'w', encoding='utf-8').write(
    'သဘောထားမှန်မှ အားထုတ်ပါ — အရှင်တေဇနိယ (ရွှေဥမင်)\n'
    '미얀마어 원서 (ယုံကြည်ချက်စာပေ, 2판 2009) — 스캔본 쪽 그림을 보며 옮겨 적은 글. 쪽 표시: 책 쪽 (PDF 쪽)\n\n'
    + '\n\n'.join(txt_out) + '\n')
from collections import Counter
print('원서 문단', len(orig), dict(Counter(p['k'] for p in orig)))
