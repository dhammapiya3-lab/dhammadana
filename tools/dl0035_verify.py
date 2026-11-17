"""DL-0035 원문 대조: PDF 글자(쪽 번호·머리글 빼고, 속표지 그림 쪽 빼고)와 본문 글자 비교 (빈칸 뺌)
  python3 tools/dl0035_verify.py 책.pdf"""
import sys, re, json, os, collections, difflib
import fitz
doc = fitz.open(sys.argv[1]); REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = []
for n in range(4, 364):
    for b in doc[n - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            if l['bbox'][1] > 478: continue
            src.append(''.join(s['text'] for s in l['spans']))
a = re.sub(r'\s', '', ''.join(src))
t = json.load(open(os.path.join(REPO, 'content/texts/DL-0035.json')))['body']
t = re.sub(r'(?m)^=== .*?===$', '', t)
t = re.sub(r'(?m)^(## |:: |\^\^ |>> |%% |- |-- )', '', t).replace('**', '')
t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)
t = re.sub(r'(?m)^~$', '', t)
b = re.sub(r'\s', '', t)
# 목차의 점선·' | ' 쪽 번호 표시
a2 = re.sub(r'·{2,}', '', a); b2 = b.replace('|', '')
a2 = a2.replace('｜', '')
print('PDF', len(a2), '본문', len(b2))
sm = difflib.SequenceMatcher(None, a2, b2, autojunk=False)
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op != 'equal': print(op, repr(a2[max(0, i1 - 12):i2 + 12]), '→', repr(b2[j1:j2]))
