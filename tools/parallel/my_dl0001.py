"""DL-0001『난다말라비왐사 큰스님 가르침』 미얀마어 원서 다섯 권 글 → 원서 문단 목록
(운영자 요청, 2026-11-18)

한국어판은 다섯 권의 미얀마어 법문집을 하나로 묶은 책(일러두기). 원서는 dhammadownload.com 의 스캔 PDF 다섯 개
(한 PDF 쪽에 책 한 쪽, 글자층 없음) — 쪽 그림을 보며 옮겨 적은 tools/parallel/dl0001_my/b1~b5/ 가 원서 글이다.
  b1 = (၆၄) အကာကိုပစ်၍ အနှစ်ကိုရှာ   ↔ Ⅰ. 껍데기는 버리고 알맹이를 찾아서
  b2 = (၂၉) မဟာဒါန                   ↔ Ⅱ. 고귀한 보시
  b3 = (၁၆) မေတ္တာသုတ်အနှစ်ချုပ်       ↔ Ⅲ. 자애경
  b4 = (၁၁၆) ဉာတပရိညာ                 ↔ Ⅳ. 위빳사나 지혜의 초석
  b5 = (၇၃) ရှာဖွေခြင်းနှင့် ရရှိခြင်း   ↔ Ⅴ. 찾음과 얻음
  bN/NNN.txt = 그 권의 PDF NNN쪽 (책 쪽 번호는 첫 줄 '@ N')
옮겨 적은 파일 모양:
  '@ N'  책 쪽 번호(빈칸이면 번호 없는 쪽),  '## ' 제목,  '>> ' 작은 글(법문 기록),  ':: ' 가운데 글
  빈 줄  문단 나눔,  '+' 앞 쪽 문단에 이어짐(빈칸 하나),  '+-' 앞 쪽 문단에 낱말 가운데에서 이어짐(빈칸 없이)
법문 기록(မှတ်တမ်း — 언제 어디서 설한 법문인지)은 한국어판에 없어 짝짓기에서 뺌(pq).
화면의 원서 쪽 표시는 '미얀마어 원서 『မဟာဒါန』 12쪽 (PDF 18쪽)' 처럼 권 제목을 붙임.

  python3 tools/parallel/my_dl0001.py
  → tools/out/parallel/DL-0001.my.paras.json (align.py 입력)
  → tools/out/parallel/<원서 제목>__AI 필사.txt 권마다 다섯 파일 (운영자에게 보내는 글 파일, 사이트에는 올리지 않음)
"""
import os, re, json, glob
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'tools/parallel/dl0001_my')
OUT = os.path.join(REPO, 'tools/out/parallel'); os.makedirs(OUT, exist_ok=True)
MY2A = str.maketrans('၀၁၂၃၄၅၆၇၈၉', '0123456789')
VOLS = [('b1', 'အကာကိုပစ်၍ အနှစ်ကိုရှာ', '(၆၄)'), ('b2', 'မဟာဒါန', '(၂၉)'), ('b3', 'မေတ္တာသုတ်အနှစ်ချုပ်', '(၁၆)'),
        ('b4', 'ဉာတပရိညာ', '(၁၁၆)'), ('b5', 'ရှာဖွေခြင်းနှင့် ရရှိခြင်း', '(၇၃)')]
RECORD = {('b3', 5, 1)}   # 기록 문단인데 '>> ' 없이 적은 것: (권, PDF 쪽, 그 쪽 문단 순번)

orig, txt_out = [], []
vol_start = []
for vol, title, num in VOLS:
    vol_start.append(len(txt_out))
    txt_out.append(f'##### {num} {title} #####')
    for f in sorted(glob.glob(os.path.join(SRC, vol, '[0-9][0-9][0-9].txt'))):
        pdf = int(os.path.basename(f)[:3])
        lines = open(f, encoding='utf-8').read().split('\n')
        pg = lines[0][1:].strip().translate(MY2A); lines = lines[1:]
        label = f'『{title}』 {pg}' if pg else ''
        txt_out.append(f"=== {pg + '쪽' if pg else '번호 없는 쪽'} (PDF {pdf}쪽) ===")
        for i, para in enumerate(p.strip() for p in re.split(r'\n\s*\n', '\n'.join(lines).strip())):
            if not para: continue
            if para.startswith('+'):
                nosp = para.startswith('+-')
                t = para[2:].strip() if nosp else para[1:].strip()
                orig[-1]['t'] += ('' if nosp else ' ') + t
                txt_out.append(('(앞 쪽에서 이어짐, 낱말 가운데) ' if nosp else '(앞 쪽에서 이어짐) ') + t)
                continue
            k, t = 'p', para
            if para.startswith('## '): k, t = 'h', para[3:].strip()
            elif para.startswith(':: '): t = para[3:].strip()
            elif para.startswith('>> '):
                t = para[3:].strip()
                if t.startswith('မှတ်တမ်း'): k = 'pq'
            if (vol, pdf, i) in RECORD: k = 'pq'
            orig.append({'pg': label, 'pdf': str(pdf), 'k': k, 't': t}); txt_out.append(t)

json.dump(orig, open(os.path.join(OUT, 'DL-0001.my.paras.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
# 권마다 따로, 이름은 '원서 제목__AI 필사.txt' (운영자 요청 2026-11-18)
FN = ['အကာကိုပစ်၍ အနှစ်ကိုရှာ', 'မဟာဒါန', 'မေတ္တာသုတ် အနှစ်ချုပ်', 'ဉာတပရိညာ', 'ရှာဖွေခြင်းနှင့် ရရှိခြင်း']
KO = ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']
for n, (vol, title, num) in enumerate(VOLS):
    part = txt_out[vol_start[n]:(vol_start[n + 1] if n + 1 < len(VOLS) else len(txt_out))]
    open(os.path.join(OUT, f'{FN[n]}__AI 필사.txt'), 'w', encoding='utf-8').write(
        f'ဒေါက်တာ အရှင်နန္ဒမာလာဘိဝံသ {num} 『{title}』 — 『난다말라비왐사 큰스님 가르침』 {KO[n]}장의 미얀마어 원서\n'
        'dhammadownload.com 스캔본(PDF) 쪽 그림을 보며 옮겨 적은 글. 쪽 표시: 책 쪽 (PDF 쪽)\n\n'
        + '\n\n'.join(part) + '\n')
from collections import Counter
print('원서 문단', len(orig), dict(Counter(p['k'] for p in orig)))
